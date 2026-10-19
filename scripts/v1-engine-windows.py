#!/usr/bin/env python3
"""Owned public-source Windows CI build/package. Capabilities are not qualification."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v1_engine as engine
from integration import v1_pe as pe
from integration import v1_windows_dependencies as dependencies

GIB = 1024**3
RESERVE, PEAK, MARGIN = 3*GIB, 16*GIB, 512*1024**2


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    return {'size': Path(path).stat().st_size, 'sha256': sha(path)}


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')


class SourceMaterialsUnavailable(ValueError):
    pass


def retain_source_supplements(lock, directory, guard):
    """Retain at most 8 MiB of hash-bound public sources; execute/extract none."""
    directory.mkdir()
    rows, total = [], 0
    for item in lock['source_supplements']:
        if not item['url'].startswith('https://') or not 0 < item['size'] <= 4*1024**2:
            raise SourceMaterialsUnavailable('invalid_source_supplement_lock')
        path = directory/item['url'].rsplit('/', 1)[1]
        try:
            with urlopen(item['url'], timeout=20) as response, path.open('xb') as stream:
                if not response.geturl().startswith('https://'):
                    raise SourceMaterialsUnavailable('source_redirect_is_not_https')
                digest, count = hashlib.sha256(), 0
                while True:
                    guard()
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    count, total = count+len(chunk), total+len(chunk)
                    if count > item['size'] or total > 8*1024**2:
                        raise SourceMaterialsUnavailable('source_supplement_exceeds_bound')
                    stream.write(chunk)
                    digest.update(chunk)
        except (OSError, URLError) as exc:
            raise SourceMaterialsUnavailable('source_supplement_download_failed') from exc
        if count != item['size'] or digest.hexdigest() != item['sha256']:
            raise SourceMaterialsUnavailable('source_supplement_digest_differs')
        rows.append(dict(item, archive=path.name, verified=True, executed=False))
    return rows


def inventory_source_archives(lock, roots, guard):
    """Select only exact locked archive bytes, rejecting missing or duplicates."""
    excluded = set(lock['binary_only_downloads'])
    wanted = [row for row in lock['sources']+lock.get('transitive_sources', [])+lock['source_supplements']
              if row['url'].rsplit('/', 1)[1] not in excluded]
    expected = {row['sha256']:row for row in wanted}
    if len(expected) != len(wanted):
        raise SourceMaterialsUnavailable('duplicate_source_digest_in_lock')
    selected, ignored, seen = [], [], {}
    for label, directory in roots.items():
        for path in sorted(directory.rglob('*')):
            guard()
            if path.is_symlink():
                raise SourceMaterialsUnavailable('linked_source_archive')
            if not path.is_file():
                continue
            if path.stat().st_size > 512*1024**2:
                raise SourceMaterialsUnavailable('source_archive_exceeds_bound')
            row = dict(root=label, path=path.relative_to(directory).as_posix(), **record(path))
            if path.name in excluded:
                row['reason'] = 'excluded_binary_build_input'
                ignored.append(row)
                continue
            if row['sha256'] not in expected:
                raise SourceMaterialsUnavailable('unrecognized_source_archive')
            selected.append(row)
            seen[row['sha256']] = seen.get(row['sha256'], 0)+1
    incorrect = [digest+'='+str(seen.get(digest, 0)) for digest in sorted(expected) if seen.get(digest, 0) != 1]
    if incorrect:
        raise SourceMaterialsUnavailable('source_archive_digest_count_must_be_one:'+','.join(incorrect))
    return {'schema':'helix-orca-v1-windows-source-archive-inventory/v1',
            'archives':selected, 'ignored':ignored, 'expected_sha256':sorted(expected),
            'excluded_binary_basenames':sorted(excluded)}


def write_verified_archives(archive, inventory, roots, guard):
    """Rehash the same open file stream copied into the unpromoted ZIP."""
    for row in inventory['archives']:
        path = roots[row['root']]/row['path']
        guard()
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row['size']:
            raise SourceMaterialsUnavailable('source_archive_changed_after_inventory')
        digest, count = hashlib.sha256(), 0
        with path.open('rb') as source, archive.open(row['root']+'/'+row['path'], 'w', force_zip64=True) as target:
            while chunk := source.read(65536):
                guard()
                count += len(chunk)
                if count > row['size']:
                    raise SourceMaterialsUnavailable('source_archive_changed_after_inventory')
                digest.update(chunk)
                target.write(chunk)
        if count != row['size'] or digest.hexdigest() != row['sha256']:
            raise SourceMaterialsUnavailable('source_archive_changed_after_inventory')
    if any(Path(name).name in inventory['excluded_binary_basenames'] for name in archive.namelist()):
        raise SourceMaterialsUnavailable('excluded_binary_archive_was_packaged')


def cmake_path(name, path):
    # CMake cache values can later be interpolated into generated CMake code.
    # A native Windows backslash (for example \a) is then an invalid escape.
    return '-D'+name+'='+path.as_posix()


def audit_source(source, evidence):
    """Retain exact public byte diagnostics before the unchanged strict audit."""
    sources, inventory = {}, {}
    for name, expected in engine.SOURCE_HASHES.items():
        try:
            data = (source/name).read_bytes()
        except OSError:
            inventory[name] = {'expected_sha256': expected, 'state': 'unavailable'}
            continue
        sources[name] = data
        inventory[name] = {'expected_sha256': expected, 'actual_sha256': hashlib.sha256(data).hexdigest(),
                           'size': len(data), 'lf_count': data.count(b'\n'),
                           'crlf_count': data.count(b'\r\n'), 'cr_count': data.count(b'\r')}
    save(evidence/'source-byte-inventory.json', {
        'schema': 'helix-orca-v1-windows-source-bytes/v1', 'source_commit': engine.ORCA_SOURCE,
        'files': inventory})
    return engine.verify_source_bytes(sources)


def dependency_input(args):
    values=(args.dependency_bundle,args.dependency_bundle_sha256,args.dependency_run_id,
            args.dependency_application_commit)
    if all(value is None for value in values):
        if args.dependency_run_attempt is not None:
            raise ValueError('Dependency producer attempt requires all checkpoint pins')
        return None
    if any(value is None for value in values):
        raise ValueError('Dependency reuse requires bundle, SHA, producer run and producer commit')
    if (re.fullmatch('[a-f0-9]{64}',args.dependency_bundle_sha256) is None
            or re.fullmatch('[a-f0-9]{40}',args.dependency_application_commit) is None
            or re.fullmatch('[1-9][0-9]{0,31}',args.dependency_run_id) is None
            or re.fullmatch('[1-9][0-9]{0,31}',args.dependency_run_attempt or '1') is None):
        raise ValueError('Exact dependency checkpoint pins required')
    return dict(path=args.dependency_bundle,sha256=args.dependency_bundle_sha256,
        run_id=args.dependency_run_id,application_commit=args.dependency_application_commit,
        run_attempt=args.dependency_run_attempt or '1')


def dependency_environment(environment):
    """Bind named compiler inputs with Windows case-insensitive semantics."""
    names = ('CMAKE_BUILD_PARALLEL_LEVEL', 'CL_MPCOUNT', 'CL', '_CL_',
        'MSBUILDDISABLENODEREUSE', 'DEP_PYTHON_HOST', 'CFLAGS', 'CXXFLAGS',
        'CPPFLAGS', 'LDFLAGS', 'INCLUDE', 'LIB', 'LIBPATH', 'PATH',
        'VCTOOLSVERSION', 'WINDOWSSDKVERSION', 'VCTOOLSINSTALLDIR',
        'WINDOWSSDKDIR', 'WINDOWSSDKBINPATH', 'WINDOWSSDKVERBINPATH',
        'UNIVERSALCRTSDKDIR', 'UCRTVERSION', 'VSINSTALLDIR', 'VCINSTALLDIR',
        'VSCMD_ARG_TGT_ARCH', 'VSCMD_ARG_HOST_ARCH')
    selected = {}
    for key, value in environment.items():
        folded = key.upper()
        if folded in names:
            if folded in selected:
                raise ValueError('Ambiguous case-insensitive dependency environment: '+folded)
            selected[folded] = value
    return {name: selected.get(name, '') for name in names}


class Build:
    def __init__(self, source, work):
        if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true'
                or os.environ.get('RUNNER_OS') != 'Windows' or os.environ.get('RUNNER_ARCH') != 'X64'
                or os.environ.get('ImageOS') != 'win22' or not 1 <= (os.cpu_count() or 0) <= 4):
            raise ValueError('Registered Windows 2022 AMD64 four-CPU-or-smaller CI runner required')
        if work.exists() or work.is_symlink() or source.is_symlink():
            raise ValueError('Fresh owned work directory and plain source directory required')
        work.mkdir()
        self.source, self.work = source.resolve(), work.resolve()
        self.evidence = work/'evidence'
        self.evidence.mkdir()
        self.start, self.free = time.monotonic(), shutil.disk_usage(work).free
        save(self.evidence/'disk-budget.json', dict(reserve_bytes=RESERVE,peak_bytes=PEAK,
            margin_bytes=MARGIN,initial_free_bytes=self.free,
            measured_previous_dependency_peak_bytes=8434524160,
            rationale='Completed dependencies nearly filled the former 8 GiB bound; allow native build and checkpoint/source archives.'))
        if self.free < RESERVE + PEAK + MARGIN:
            raise ValueError('Windows build lacks declared disk headroom')
        self.guard()
        self.environment = self.msvc_environment()
        self.environment.update(CMAKE_BUILD_PARALLEL_LEVEL='2', CL_MPCOUNT='1', _CL_='/MP1',
                                MSBUILDDISABLENODEREUSE='1', DEP_PYTHON_HOST=sys.executable)
        self.children = []
        self.tools = {name: record(shutil.which(name, path=self.environment['PATH']))
                      for name in ('cl', 'link', 'cmake', 'ninja', 'perl')}
        self.tools['msbuild'] = record(self.environment['MSBUILD'])

    def guard(self):
        free = shutil.disk_usage(self.work).free
        self.min_free = min(getattr(self, 'min_free', self.free), free)
        if free < RESERVE + MARGIN or self.free - free > PEAK:
            raise RuntimeError('Windows build disk reserve/peak guard reached')
        if time.monotonic() - self.start > 7200:
            raise RuntimeError('Windows build 120-minute watchdog reached')

    def prepare_dependencies(self,lock,submodules,builder):
        deps,prefix,downloads=(self.work/name for name in ('deps','prefix','downloads'))
        configure=['cmake','-S',self.source/'deps','-B',deps,'-G','Ninja',
            '-DCMAKE_BUILD_TYPE=Release','-DSLIC3R_CAD=OFF','-DDEP_DEBUG=OFF',
            cmake_path('DESTDIR',prefix),cmake_path('DEP_DOWNLOAD_DIR',downloads),
            cmake_path('DEP_PYTHON_HOST',Path(sys.executable)),
            '-DCMAKE_C_COMPILER=cl','-DCMAKE_CXX_COMPILER=cl']
        targets=[item['target']for item in lock['sources']]
        targets[5:5]=lock['in_tree_targets']
        environment=dependency_environment(self.environment)
        target_environments={'dep_OCCT':{'CMAKE_BUILD_PARALLEL_LEVEL':'4'}}
        environment.update(DEPENDENCY_TARGET_ENVIRONMENTS=json.dumps(target_environments,sort_keys=True,separators=(',',':')),
            HOST_PYTHON_SHA256=sha(Path(sys.executable)),
            DEPENDENCY_CONFIGURE_ARGV=json.dumps([str(arg)for arg in configure],separators=(',',':')),
            DEPENDENCY_TARGETS=json.dumps(targets,separators=(',',':')))
        contract=dict(schema=dependencies.CONTRACT_SCHEMA,source_commit=engine.ORCA_SOURCE,
            submodules=submodules,dependencies_lock_sha256=sha(ROOT/'integration/v1-native-windows-dependencies.json'),
            builder_sha256=sha(Path(__file__)),workflow_sha256=sha(ROOT/'.github/workflows/v1-windows-engine.yml'),
            module_sha256=sha(ROOT/'integration/v1_windows_dependencies.py'),toolchain=self.tools,
            environment=environment,prefix=str(prefix.absolute()),downloads=str(downloads.absolute()))
        save(self.evidence/'dependency-contract.json',contract)
        # Validate real source/tool/environment provenance before any expensive
        # command; an exact empty submodule inventory is valid for this source.
        dependencies.validate_provenance(contract,builder,prefix,downloads,self.guard)
        supplied=getattr(self,'dependency_input',None)
        if supplied is not None:
            expected=dict(builder,application_commit=supplied['application_commit'],
                run_id=supplied['run_id'],run_attempt=supplied['run_attempt'],
                run_url='https://github.com/'+builder['repository']+'/actions/runs/'+supplied['run_id'])
            receipt=dependencies.restore_bundle(supplied['path'],supplied['sha256'],prefix,downloads,
                contract,expected,self.guard)
            save(self.evidence/'dependency-checkpoint.json',receipt)
            return receipt
        self.run('deps-configure',configure)
        for target in targets:
            # OCCT alone uses the already declared four-compiler upper bound;
            # the outer build stays serial and each compiler keeps /MP1.
            override=target_environments.get(target)
            self.run(target,['cmake','--build',deps,'--target',target,'--parallel','1'],
                environment=dict(self.environment,**override)if override else None)
        # Optional retained progress cannot qualify or replace an engine build.
        # Resource guards and provenance failures propagate; optional checkpoint
        # size/count limits stay explicit without qualifying a partial archive.
        try:
            receipt=dependencies.create_bundle(self.work/'native-windows-dependencies.zip',
                prefix,downloads,contract,builder,self.guard)
        except dependencies.BundleError as error:
            if str(error) not in {'dependency_inventory_bound_exceeded','directory_count_bound_exceeded',
                    'archive_size_bound_exceeded','manifest_size_bound_exceeded','file_size_bound_exceeded'}:
                raise
            self.guard()
            save(self.evidence/'dependency-checkpoint-failure.json',dict(
                available=False,qualified=False,reason=str(error)))
            return None
        save(self.evidence/'dependency-checkpoint.json',receipt)
        # Retain the completed dependency tree through native compilation for
        # installed-prefix compatibility and diagnosis; the disposable VM owns
        # final cleanup. The same declared disk guard covers this retained tree.
        return receipt

    def msvc_environment(self):
        vswhere = Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
        vs = Path(subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-requires',
            'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
            text=True, timeout=30).strip())
        developer = vs/'Common7/Tools/VsDevCmd.bat'
        if not vs.is_dir() or not developer.is_file() or any(char in str(vs) for char in ('"', '\r', '\n')):
            raise ValueError('Preinstalled MSVC environment unavailable')
        # cmd's command-string quoting differs from Windows argv quoting. Keep
        # CALL's quoted path in an owned batch file, never inside list2cmdline.
        batch = self.work/'native-msvc-environment.cmd'
        with batch.open('x', encoding='utf-8', newline='\r\n') as stream:
            stream.write('@echo off\ncall "'+str(developer)+'" -arch=x64 -host_arch=x64 >nul\n'
                         'if errorlevel 1 exit /b %errorlevel%\nset\n')
        output = subprocess.check_output([os.environ['COMSPEC'], '/d', '/c', str(batch)],
                                         text=True, timeout=30)
        environment = {}
        for line in output.splitlines():
            if '=' in line and not line.startswith('='):
                key, value = line.split('=', 1)
                if key.upper() in environment:
                    raise ValueError('Ambiguous case-insensitive MSVC environment')
                environment[key.upper()] = value
        environment['MSBUILD'] = str(vs/'MSBuild/Current/Bin/amd64/MSBuild.exe')
        if environment.get('VSCMD_ARG_TGT_ARCH') != 'x64' or not Path(environment['MSBUILD']).is_file():
            raise ValueError('64-bit-hosted MSVC/MSBuild unavailable')
        return environment

    def run(self, label, command, cwd=None, environment=None):
        self.guard()
        print(json.dumps({'stage': label, 'state': 'started'}), flush=True)
        child = subprocess.Popen([str(arg) for arg in command], cwd=cwd or self.work,
            env=environment or self.environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.children.append(child)
        output = queue.Queue(maxsize=16)
        def reader():
            try:
                while chunk := child.stdout.read(65536):
                    output.put(chunk)
            finally:
                output.put(None)
        threading.Thread(target=reader, daemon=True).start()
        kept = total = 0
        tail = b''
        started = time.monotonic()
        try:
            with (self.evidence/(label+'.log')).open('wb') as log:
                while True:
                    self.guard()
                    try:
                        chunk = output.get(timeout=1)
                    except queue.Empty:
                        continue
                    if chunk is None:
                        break
                    total += len(chunk)
                    block = chunk[:max(0, 1024**2-kept)]
                    log.write(block)
                    kept += len(block)
                    tail = (tail+chunk)[-65536:]
                code = child.wait(timeout=10)
        except BaseException:
            if child.poll() is None:
                subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                               capture_output=True, timeout=30, check=False)
                child.wait(timeout=30)
            raise
        finally:
            (self.evidence/(label+'-tail.log')).write_bytes(tail)
        save(self.evidence/(label+'.json'), {'exit_code': code, 'output_bytes': total,
            'log_bytes': kept, 'elapsed_seconds': round(time.monotonic()-started, 3)})
        if code:
            print(tail.decode('utf-8', 'replace'), flush=True)
            raise RuntimeError('Native Windows stage failed: '+label)

    def package(self):
        source = self.source
        if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != engine.ORCA_SOURCE:
            raise ValueError('Exact upstream source commit required')
        if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
            raise ValueError('Upstream checkout is modified')
        modules = subprocess.check_output(['git', '-C', str(source), 'submodule', 'status', '--recursive'], text=True)
        if any(not row.startswith(' ') for row in modules.splitlines()):
            raise ValueError('Exact initialized recursive submodules required')
        source_report = audit_source(source, self.evidence)
        lock = json.loads((ROOT/'integration/v1-native-windows-dependencies.json').read_text())
        for name, expected in lock['in_tree_files'].items():
            if sha(source/name) != expected:
                raise ValueError('Windows in-tree dependency differs')
        commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        builder = {'schema': 'helix-orca-v1-windows-builder/v1',
            'repository': os.environ['GITHUB_REPOSITORY'], 'workflow': '.github/workflows/v1-windows-engine.yml',
            'application_commit': commit, 'run_id': os.environ['GITHUB_RUN_ID'],
            'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'], 'runner_image': 'windows-2022',
            'image_version': os.environ['ImageVersion'], 'toolchain': self.tools,
            'run_url': os.environ['GITHUB_SERVER_URL']+'/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID']}
        if not engine._windows_builder_valid(builder, {'application_commit': commit}):
            raise ValueError('Registered Windows CI provenance required')
        inputs = {'source': source_report, 'builder': builder, 'submodules': modules.splitlines(),
            'owned_inputs': {name:sha(ROOT/name) for name in engine._WINDOWS_OWNED_INPUTS},
            'compiler_slots': 4, 'cmake_jobs': 2, 'occt_jobs': 4, 'dependency_top_level_jobs': 1,
            'reserve_bytes': RESERVE, 'peak_bytes': PEAK, 'margin_bytes': MARGIN,
            'timeout_seconds': 7200, 'qualified': False}
        save(self.evidence/'native-inputs.json', inputs)
        checkpoint=self.prepare_dependencies(lock,modules.splitlines(),builder)
        inputs['dependency_checkpoint']=checkpoint
        save(self.evidence/'native-inputs.json',inputs)
        prefix,build=self.work/'prefix',self.work/'engine'
        actual_prefix = prefix/'usr/local'
        self.run('engine-configure', ['cmake', '-S', source, '-B', build, '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=Release', cmake_path('CMAKE_PREFIX_PATH', actual_prefix),
            cmake_path('CMAKE_MODULE_PATH', ROOT/'integration/v1-native-engine/windows-cmake'),
            '-DSLIC3R_GUI=OFF', '-DSLIC3R_CAD=OFF', '-DSLIC3R_STATIC=ON',
            '-DSLIC3R_BUILD_TESTS=OFF', '-DORCA_TOOLS=OFF', '-DSLIC3R_PCH=OFF',
            '-DSLIC3R_MSVC_COMPILE_PARALLEL=OFF', '-DSLIC3R_MSVC_PDB=OFF',
            '-DCMAKE_C_COMPILER=cl', '-DCMAKE_CXX_COMPILER=cl',
            cmake_path('CMAKE_PROJECT_OrcaSlicer_INCLUDE', ROOT/'integration/v1-native-engine/windows-target.cmake')])
        self.run('native-adapter', ['cmake', '--build', build, '--target', 'helix_orca_native', '--parallel', '2'])
        package = self.work/'package'
        package.mkdir()
        executable = package/'helix_orca_native.exe'
        shutil.copy2(build/executable.name, executable)
        search = [actual_prefix, Path(self.environment['VCTOOLSREDISTDIR'])/'x64']
        candidates = {}
        for directory in search:
            for path in directory.rglob('*.dll'):
                candidates.setdefault(path.name.lower(), []).append(path)
        dlls, closure, systems, pending = {}, {}, set(), [executable]
        while pending:
            current = pending.pop()
            imports = pe.inspect(current, dll=current.suffix.lower()=='.dll')
            closure[current.name.lower()] = imports
            for name in imports:
                if pe.system_dll(name):
                    systems.add(name)
                elif name not in dlls:
                    options = candidates.get(name, [])
                    if not options or len({sha(path) for path in options}) != 1:
                        raise ValueError('Missing or ambiguous non-system DLL: '+name)
                    target = package/name
                    shutil.copy2(options[0], target)
                    dlls[name] = record(target)
                    pending.append(target)
        resources = package/'resources'
        for name in engine._NATIVE_ASSETS:
            target = resources/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source/'resources'/name, target)
        runtime_env = dict(self.environment, PATH=str(package)+';'+os.environ['SystemRoot']+'\\System32;'+os.environ['SystemRoot'])
        self.run('native-capabilities', [executable, '--capabilities'], cwd=package, environment=runtime_env)
        caps = json.loads((self.evidence/'native-capabilities.log').read_text())
        if caps.get('target') != engine._WINDOWS_TARGET or caps.get('max_parallelism') != 2:
            raise ValueError('Actual Windows native capabilities differ')
        libraries = [{'name':str(path.relative_to(build)), **record(path)} for path in build.rglob('*libslic3r*.lib')]
        if not libraries:
            raise ValueError('Actual native static library unavailable')
        receipt = {'schema': 'helix-orca-v1-native-build/v1', 'source_commit': engine.ORCA_SOURCE,
            'application_commit': commit, 'built': True, 'qualified': False, 'target': caps['target'],
            'capabilities': caps, 'libraries': libraries, 'native_inputs_sha256': sha(self.evidence/'native-inputs.json'),
            'adapter': dict(path=executable.name, **record(executable)), 'runtime_dlls': dlls,
            'import_closure': closure, 'system_imports': sorted(systems),
            'resources': {name:sha(resources/name) for name in engine._NATIVE_ASSETS}}
        engine._windows_closure(executable, receipt)
        for name in ('native-inputs.json',):
            shutil.copy2(self.evidence/name, package/name)
        save(package/'native-build.json', receipt)
        save(self.evidence/'native-build.json', receipt)
        shutil.copy2(source/'LICENSE.txt', package/'LICENSE-OrcaSlicer-AGPL-3.0.txt')
        licenses = package/'licenses'
        licenses.mkdir()
        for name in ('deps/GMP/gmp/gmp.COPYING', 'deps/GMP/gmp/gmp.README',
                     'deps/MPFR/mpfr/mpfr.COPYING', 'deps/MPFR/mpfr/mpfr.COPYING.LESSER',
                     'deps/MPFR/mpfr/mpfr.README'):
            shutil.copy2(source/name, licenses/Path(name).name)
        source_cache = self.work/'corresponding-sources'
        supplements, source_failure = [], None
        try:
            supplements = retain_source_supplements(lock, source_cache, self.guard)
        except SourceMaterialsUnavailable as error:
            source_failure = str(error)
        unresolved = [name for name in dlls if name.startswith((
            'avcodec-', 'avformat-', 'avutil-', 'swscale-', 'swresample-',
            'libssl-3', 'libcrypto-3', 'libffi-', 'python3'))]
        roots = {'dependency-archives':self.work/'downloads', 'matching-upstream-versions':source_cache}
        inventory_sha = None
        try:
            inventory = inventory_source_archives(lock, roots, self.guard)
            save(package/'source-archive-inventory.json', inventory)
            shutil.copy2(package/'source-archive-inventory.json', self.evidence/'source-archive-inventory.json')
            inventory_sha = sha(package/'source-archive-inventory.json')
            if not source_failure:
                partial = self.work/'native-windows-source.partial.zip'
                with zipfile.ZipFile(partial, 'x', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
                    for path in source.rglob('*'):
                        self.guard()
                        relative = path.relative_to(source)
                        if (not path.is_file() or '.git' in relative.parts or path.name in lock['binary_only_downloads']
                                or path.suffix.lower() in ('.dll', '.lib', '.exe', '.pdb')
                                   and relative.as_posix() not in lock['in_tree_files']):
                            continue
                        archive.write(path, 'OrcaSlicer/'+relative.as_posix())
                    for name in engine._WINDOWS_OWNED_INPUTS + ('integration/v1_engine.py', 'integration/v1_contract.py'):
                        archive.write(ROOT/name, 'helix-orca-calibration/'+name)
                    archive.write(package/'source-archive-inventory.json', 'source-materials/source-archive-inventory.json')
                    write_verified_archives(archive, inventory, roots, self.guard)
                partial.replace(self.work/'native-windows-source.zip')
        except SourceMaterialsUnavailable as error:
            source_failure = source_failure or str(error)
        source_status = {'schema': 'helix-orca-v1-windows-source-materials/v1',
            'source_supplements': supplements, 'source_failure': source_failure,
            'source_archive_inventory_sha256': inventory_sha,
            'source_archive_created': (self.work/'native-windows-source.zip').is_file(),
            'unresolved_prebuilt_runtime_components': sorted(unresolved),
            'opaque_static_components': ['OpenCV Intel IPP-ICV enabled by upstream Windows recipe; vendor build/source provenance unverified'],
            'source_materials_state': 'matching-upstream-sources-retained' if not source_failure and not unresolved else 'incomplete',
            'exact_historical_vendor_build_reproduced': False, 'complete_corresponding_source_claim': False,
            'vendor_limitation': 'Pinned GMP/MPFR binaries match upstream versions; historical vendor compiler, flags and patches are unverified.',
            'production_source_acceptance_required': True, 'excluded_binary_build_inputs': lock['binary_only_downloads']}
        save(package/'source-materials.json', source_status)
        save(self.evidence/'source-materials.json', source_status)
        receipt.update(source_archive_inventory_sha256=inventory_sha,
                       source_materials_sha256=sha(package/'source-materials.json'))
        save(package/'native-build.json', receipt)
        save(self.evidence/'native-build.json', receipt)
        (package/'SOURCE-OFFER.txt').write_text('Source materials, when verified, accompany this artifact as native-windows-source.zip.\n'
            'The archive includes source-archive-inventory.json; every locked source archive must match exactly once and is rehashed during ZIP writing.\n'
            'Read source-materials.json: historical GNU vendor builds and Windows OpenCV Intel IPP-ICV provenance remain unverified; complete corresponding source is not claimed.\n'
            'Missing or substituted source materials block production source acceptance while preserving the built code-only candidate.\n'
            'Microsoft runtime DLLs, if present, are from the preinstalled Visual Studio 2022 redistributable.\n'
            'https://learn.microsoft.com/visualstudio/releases/2022/redistribution\n'
            'No calibration is qualified by this build; native parity and all processor checks remain mandatory.\n', encoding='utf-8')
        self.guard()
        shutil.make_archive(str(self.work/'native-windows-package'), 'zip', package)
        save(self.evidence/'package-summary.json', {'schema': 'helix-orca-v1-windows-package/v1',
            'built': True, 'qualified': False, 'physical_actions': False,
            'package': record(self.work/'native-windows-package.zip'),
            'source_archive': record(self.work/'native-windows-source.zip') if (self.work/'native-windows-source.zip').is_file() else None,
            'source_archive_inventory_sha256': inventory_sha,
            'source_materials_sha256': sha(package/'source-materials.json'),
            'elapsed_seconds': round(time.monotonic()-self.start, 3),
            'peak_filesystem_loss_bytes': self.free-self.min_free,
            'stage_processes_exited': all(child.poll() is not None for child in self.children)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--dependency-bundle',type=Path)
    parser.add_argument('--dependency-bundle-sha256')
    parser.add_argument('--dependency-run-id')
    parser.add_argument('--dependency-application-commit')
    parser.add_argument('--dependency-run-attempt')
    args = parser.parse_args()
    supplied=dependency_input(args)
    run = None
    try:
        run = Build(args.source, args.work)
        run.dependency_input=supplied
        run.package()
    finally:
        if run is None and (args.work/'evidence').is_dir():
            save(args.work/'evidence/build-lifecycle.json', {
                'schema': 'helix-orca-v1-windows-build-lifecycle/v1', 'state': 'failed',
                'stage': 'constructor', 'stage_processes_exited': None,
                'runtime_cleanup': 'GitHub-hosted disposable job teardown',
                'owned_runner_vm': True, 'physical_actions': False})
        if run is not None:
            save(run.evidence/'build-lifecycle.json', {
                'schema': 'helix-orca-v1-windows-build-lifecycle/v1',
                'state': 'complete' if (run.evidence/'package-summary.json').exists() else 'failed',
                'stage_processes_exited': all(child.poll() is not None for child in run.children),
                'runtime_cleanup': 'GitHub-hosted disposable job teardown',
                'owned_runner_vm': True, 'physical_actions': False,
                'elapsed_seconds': round(time.monotonic()-run.start, 3),
                'peak_filesystem_loss_bytes': run.free-run.min_free})


if __name__ == '__main__':
    main()
