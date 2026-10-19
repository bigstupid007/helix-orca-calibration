#!/usr/bin/env python3
"""Owned public-source Windows CI build/package. Capabilities are not qualification."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v1_engine as engine
from integration import v1_pe as pe

GIB = 1024**3
RESERVE, PEAK, MARGIN = 3*GIB, 8*GIB, 512*1024**2


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    return {'size': Path(path).stat().st_size, 'sha256': sha(path)}


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')


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
        if self.free < RESERVE + PEAK + MARGIN:
            raise ValueError('Windows build lacks declared disk headroom')
        self.guard()
        self.environment = self.msvc_environment()
        self.environment.update(CMAKE_BUILD_PARALLEL_LEVEL='2', CL_MPCount='1', _CL_='/MP1',
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

    def msvc_environment(self):
        vswhere = Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
        vs = Path(subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-requires',
            'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
            text=True, timeout=30).strip())
        if not vs.is_dir() or '"' in str(vs):
            raise ValueError('Preinstalled MSVC environment unavailable')
        command = 'call "'+str(vs/'Common7/Tools/VsDevCmd.bat')+'" -arch=x64 -host_arch=x64 >nul && set'
        output = subprocess.check_output([os.environ['COMSPEC'], '/d', '/s', '/c', command],
                                         text=True, timeout=30)
        environment = dict(os.environ)
        for line in output.splitlines():
            if '=' in line and not line.startswith('='):
                key, value = line.split('=', 1)
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
        source_report = engine.verify_source_bytes({name:(source/name).read_bytes() for name in engine.SOURCE_HASHES})
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
            'compiler_slots': 4, 'cmake_jobs': 2, 'dependency_top_level_jobs': 1,
            'reserve_bytes': RESERVE, 'peak_bytes': PEAK, 'margin_bytes': MARGIN,
            'timeout_seconds': 7200, 'qualified': False}
        save(self.evidence/'native-inputs.json', inputs)
        deps, prefix, build = (self.work/name for name in ('deps', 'prefix', 'engine'))
        self.run('deps-configure', ['cmake', '-S', source/'deps', '-B', deps, '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=Release', '-DSLIC3R_CAD=OFF', '-DDEP_DEBUG=OFF',
            '-DDESTDIR='+str(prefix), '-DDEP_DOWNLOAD_DIR='+str(self.work/'downloads'),
            '-DDEP_PYTHON_HOST='+sys.executable, '-DCMAKE_C_COMPILER=cl', '-DCMAKE_CXX_COMPILER=cl'])
        targets = [item['target'] for item in lock['sources']]
        targets[5:5] = lock['in_tree_targets']
        for target in targets:
            self.run(target, ['cmake', '--build', deps, '--target', target, '--parallel', '1'])
        actual_prefix = prefix/'usr/local'
        self.run('engine-configure', ['cmake', '-S', source, '-B', build, '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_PREFIX_PATH='+str(actual_prefix),
            '-DSLIC3R_GUI=OFF', '-DSLIC3R_CAD=OFF', '-DSLIC3R_STATIC=ON',
            '-DSLIC3R_BUILD_TESTS=OFF', '-DORCA_TOOLS=OFF', '-DSLIC3R_PCH=OFF',
            '-DSLIC3R_MSVC_COMPILE_PARALLEL=OFF', '-DSLIC3R_MSVC_PDB=OFF',
            '-DCMAKE_C_COMPILER=cl', '-DCMAKE_CXX_COMPILER=cl',
            '-DCMAKE_PROJECT_OrcaSlicer_INCLUDE='+str(ROOT/'integration/v1-native-engine/add-target.cmake')])
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
        (package/'SOURCE-OFFER.txt').write_text('Corresponding source accompanies this artifact as native-windows-source.zip.\n'
            'It includes exact recursive Orca source, downloaded dependency archives and owned build source.\n'
            'Microsoft runtime DLLs, if present, are from the preinstalled Visual Studio 2022 redistributable.\n'
            'https://learn.microsoft.com/visualstudio/releases/2022/redistribution\n'
            'No calibration is qualified by this build; native parity and all processor checks remain mandatory.\n', encoding='utf-8')
        with zipfile.ZipFile(self.work/'native-windows-source.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for label, directory in (('OrcaSlicer', source), ('dependency-archives', self.work/'downloads')):
                for path in directory.rglob('*'):
                    self.guard()
                    if path.is_file() and '.git' not in path.relative_to(directory).parts:
                        archive.write(path, label+'/'+path.relative_to(directory).as_posix())
            for name in engine._WINDOWS_OWNED_INPUTS + ('integration/v1_engine.py', 'integration/v1_contract.py'):
                archive.write(ROOT/name, 'helix-orca-calibration/'+name)
        self.guard()
        shutil.make_archive(str(self.work/'native-windows-package'), 'zip', package)
        save(self.evidence/'package-summary.json', {'schema': 'helix-orca-v1-windows-package/v1',
            'built': True, 'qualified': False, 'physical_actions': False,
            'package': record(self.work/'native-windows-package.zip'),
            'source_archive': record(self.work/'native-windows-source.zip'),
            'elapsed_seconds': round(time.monotonic()-self.start, 3),
            'peak_filesystem_loss_bytes': self.free-self.min_free,
            'stage_processes_exited': all(child.poll() is not None for child in self.children)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    run = None
    try:
        run = Build(args.source, args.work)
        run.package()
    finally:
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
