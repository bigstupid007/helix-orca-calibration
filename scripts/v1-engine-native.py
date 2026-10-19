#!/usr/bin/env python3
"""Owned offline native dependency/static-engine build; not a qualified generator."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9'
HELPER = Path('/home/dev/Projects/system/100-day-development-system/scripts/resource_lifecycle.py')
HELPER_HASH = '8a2cb48220f14c8f4ca5c2cc9f6fcdcdf28fa436fe4b7dd50cf6489178ba6fcc'
LOCK = ROOT / 'integration/v1-native-dependencies.json'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bounded_command(command, evidence, label, cwd=None):
    """Keep capped first output and diagnostic tail independently of log volume."""
    print(json.dumps({'stage':label,'state':'started'}),flush=True)
    start = time.monotonic()
    tail, kept, total = b'', 0, 0
    with (evidence / (label + '.log')).open('wb') as log:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
        while chunk := child.stdout.read1(65536):
            total += len(chunk)
            if kept < 1024**2:
                block = chunk[:1024**2-kept]
                log.write(block)
                kept += len(block)
            tail = (tail + chunk)[-65536:]
        code = child.wait()
    (evidence / (label + '-tail.log')).write_bytes(tail)
    row = dict(command=command, exit_code=code, elapsed_seconds=round(time.monotonic()-start, 3),
               output_bytes=total, log_bytes=kept, truncated=total > kept)
    (evidence / (label + '.json')).write_text(json.dumps(row, indent=2)+'\n')
    print(json.dumps(dict(stage=label, **row)), flush=True)
    if code:
        print(tail.decode('utf-8', 'replace'), flush=True)
        raise RuntimeError('Native build stage failed: '+label)


def compile_offline():
    evidence = Path('/evidence')
    lock = json.loads(LOCK.read_text())
    owned_inputs = ('integration/v1-native-dependencies.json',
                    'integration/v1-native-engine/main.cpp',
                    'integration/v1-native-engine/add-target.cmake',
                    'integration/v1-native-build-tools.py',
                    'scripts/v1-engine-native.py')
    audit = load('native_source_provenance', ROOT/'integration/v1_engine.py')
    source_report = audit.verify_source_bytes({name:(Path('/source')/name).read_bytes()
                                               for name in audit.SOURCE_HASHES})
    (evidence/'native-inputs.json').write_text(json.dumps(dict(
        source=source_report, builder_image=IMAGE, lifecycle_helper_sha256=HELPER_HASH,
        owned_inputs={name:sha(ROOT/name) for name in owned_inputs},
        network='none', memory_bytes=12*1024**3, cpus=6, compiler_slots=4,
        dependency_top_level_jobs=1, qualified=False),indent=2)+'\n')
    tools = Path('/build/tools')
    tools.mkdir(mode=0o700,exist_ok=True)
    for tool in ('make','cc','c++','gcc','g++'):
        link = tools / tool
        expected = '/app/integration/v1-native-build-tools.py'
        if not link.exists(): link.symlink_to(expected)
        elif not link.is_symlink() or str(link.readlink()) != expected:
            raise ValueError('Build tool gate path differs')
    os.environ['PATH'] = str(tools) + ':' + os.environ['PATH']
    os.environ['CC'] = str(tools/'cc')
    os.environ['CXX'] = str(tools/'c++')
    os.environ['CMAKE_BUILD_PARALLEL_LEVEL'] = '4'
    # FFmpeg configure executes its compiler probes. Keep /tmp noexec and use
    # the already declared executable build root for those owned probe files.
    temporary = Path('/build/configure-tmp')
    temporary.mkdir(mode=0o700,exist_ok=True)
    os.environ['TMPDIR'] = str(temporary)
    os.environ['PATH'] = '/build/bootstrap-prefix/bin:' + os.environ['PATH']
    for item in lock.get('bootstrap_sources', []):
        name = item['target'].removeprefix('dep_')
        binary = {'m4':'m4','autoconf':'autoreconf','automake':'automake','libtool':'libtoolize','texinfo':'makeinfo','nasm':'nasm'}[name]
        installed = Path('/build/bootstrap-prefix/bin')/binary
        if installed.exists(): continue
        work = Path('/build/bootstrap')
        work.mkdir(mode=0o700,exist_ok=True)
        filename = item['url'].rsplit('/',1)[1]
        archive = Path('/downloads')/name/filename
        source = work/filename.removesuffix('.tar.xz')
        if not source.exists():
            bounded_command(['cmake','-E','tar','xf',str(archive)],evidence,'bootstrap-'+name+'-extract',cwd=work)
        bounded_command([str(source/'configure'),'--prefix=/build/bootstrap-prefix','--disable-nls'],evidence,'bootstrap-'+name+'-configure',cwd=source)
        bounded_command(['/build/tools/make','-j4'],evidence,'bootstrap-'+name+'-build',cwd=source)
        bounded_command(['/build/tools/make','install','-j1'],evidence,'bootstrap-'+name+'-install',cwd=source)
    bounded_command(['cmake','-S','/source/deps','-B','/build/deps','-DSLIC3R_CAD=OFF',
                     '-DDEP_DOWNLOAD_DIR=/downloads','-DDESTDIR=/build/prefix',
                     '-DCMAKE_C_COMPILER=/build/tools/cc','-DCMAKE_CXX_COMPILER=/build/tools/c++',
                     '-DCMAKE_MAKE_PROGRAM=/build/tools/make'], evidence, 'deps-configure')
    for item in lock['sources']:
        bounded_command(['cmake','--build','/build/deps','--target',item['target'],'-j1'],
                        evidence, item['target'])
    bounded_command(['cmake','-S','/source','-B','/build/engine','-DCMAKE_BUILD_TYPE=Release',
                     '-DCMAKE_PREFIX_PATH=/build/prefix/usr/local','-DSLIC3R_GUI=OFF',
                     '-DSLIC3R_CAD=OFF','-DSLIC3R_STATIC=ON','-DSLIC3R_BUILD_TESTS=OFF',
                     '-DORCA_TOOLS=OFF','-DSLIC3R_PCH=OFF',
                     '-DCMAKE_C_COMPILER=/build/tools/cc','-DCMAKE_CXX_COMPILER=/build/tools/c++',
                     '-DCMAKE_MAKE_PROGRAM=/build/tools/make',
                     '-DCMAKE_PROJECT_OrcaSlicer_INCLUDE=/app/integration/v1-native-engine/add-target.cmake'], evidence, 'engine-configure')
    bounded_command(['cmake','--build','/build/engine','--target','libslic3r','-j4'], evidence, 'engine-static')
    bounded_command(['cmake','--build','/build/engine','--target','helix_orca_native','-j4'],evidence,'native-adapter')
    executable = Path('/build/engine/helix_orca_native')
    if not executable.exists(): raise RuntimeError('Native adapter output missing')
    libraries = [{'path':str(p),'size':p.stat().st_size,'sha256':sha(p)}
                 for p in Path('/build/engine').rglob('*libslic3r*.a')]
    if not libraries:
        raise RuntimeError('No native static library after successful build')
    bounded_command([str(executable),'--capabilities'],evidence,'native-capabilities')
    capabilities=json.loads((evidence/'native-capabilities.log').read_text())
    assets=('calib/temperature_tower/temperature_tower.drc',
            'calib/retraction/retraction_tower.drc','calib/volumetric_speed/SpeedTestStructure.drc')
    (evidence/'native-build.json').write_text(json.dumps(dict(
        schema='helix-orca-v1-native-build/v1',source_commit=lock['source_commit'],
        built=True,qualified=False,libraries=libraries,capabilities=capabilities,target=capabilities['target'],
        native_inputs_sha256=sha(evidence/'native-inputs.json'),
        resources={name:sha(Path('/source/resources')/name) for name in assets},
        adapter={'path':str(executable),'size':executable.stat().st_size,'sha256':sha(executable)}),indent=2)+'\n')


def stage_download_tree(cache, downloads):
    lock = json.loads(LOCK.read_text())
    tree = cache / 'download-tree'
    tree.mkdir(mode=0o700,parents=True,exist_ok=True)
    for item in lock['sources'] + lock.get('bootstrap_sources', []):
        name = item['url'].split(';')[0].rsplit('/',1)[1]
        archive = downloads / (item['sha256']+'-'+name)
        if archive.is_symlink() or sha(archive) != item['sha256']:
            raise ValueError('Dependency download absent or unverified: '+item['target'])
        directory = tree / item['target'].removeprefix('dep_')
        directory.mkdir(mode=0o700,exist_ok=True)
        target = directory / name
        if target.exists():
            if target.is_symlink() or sha(target) != item['sha256']:
                raise ValueError('Projected dependency input differs')
        else:
            os.link(archive,target)
    return tree


def build(args):
    if sha(HELPER) != HELPER_HASH:
        raise ValueError('Shared lifecycle helper differs')
    engine = load('native_engine_audit', ROOT/'integration/v1_engine.py')
    engine.verify_source_bytes({name:(args.source/name).read_bytes() for name in engine.SOURCE_HASHES})
    resource = load('native_engine_resource', HELPER)
    args.cache.mkdir(mode=0o700,parents=True,exist_ok=True)
    tree = args.cache / 'download-tree'
    build_dir = args.cache/'build-6a7763f0'
    build_dir.mkdir(mode=0o700,exist_ok=True)
    class NativeDocker(resource.DockerCLI):
        def create(self, run_id, image, command, memory, cpus, pids):
            if image != IMAGE or json.loads(self.call('image','inspect','--format','{{json .Config.Volumes}}',image)):
                raise resource.Refused('Native build immutable image/volume mismatch')
            return self.call('create','--label',resource.LABEL+'='+run_id,'--restart=no',
                '--user',str(os.getuid())+':'+str(os.getgid()),'--network','none','--read-only',
                '--cap-drop','ALL','--security-opt','no-new-privileges','--memory',str(memory),
                '--memory-swap',str(memory),'--cpus',str(cpus),'--pids-limit',str(pids),
                '--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2',
                '--tmpfs','/tmp:rw,noexec,nosuid,size=256m',
                '--mount','type=bind,source='+str(args.source.resolve())+',target=/source,readonly',
                '--mount','type=bind,source='+str(ROOT)+',target=/app,readonly',
                '--mount','type=bind,source='+str(tree)+',target=/downloads,readonly',
                '--mount','type=bind,source='+str(build_dir)+',target=/build',
                '--mount','type=bind,source='+str(run.artifacts)+',target=/evidence',
                image,'python3','-B','/app/scripts/v1-engine-native.py','_compile')
    adapter = NativeDocker()
    commit = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    with resource.ManagedRun(app='helix-orca-v1-native-build',repo=str(ROOT),
            issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',commit=commit,
            dirty_input=sha(LOCK),paths=[str(args.cache),str(args.source),str(args.downloads),str(ROOT)],
            reserve=10*1024**3,peak=16*1024**3,margin=2*1024**3,timeout=7200,adapter=adapter) as run:
        stage_download_tree(args.cache,args.downloads)
        # ExternalProject configure creates download dirs for optional targets too.
        for directory in (args.source/'deps').iterdir():
            if directory.is_dir():
                (tree/directory.name).mkdir(mode=0o700,exist_ok=True)
        print('Managed native build: '+str(run.directory),flush=True)
        cid=run.container(IMAGE,[],memory=12*1024**3,cpus=6,pids=512)
        run.execute([sys.executable,str(Path(__file__).resolve()),'_follow','--container',cid],cwd=ROOT)
        if run.data.get('exit_code') != 0:
            raise RuntimeError('Native build failed; retained '+str(run.directory))
    if run.data['state'] != 'complete':
        raise RuntimeError('Native build lifecycle incomplete: '+str(run.directory))
    print('COMPLETE '+str(run.directory))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['build','_compile','_follow'])
    parser.add_argument('--source',type=Path,default=Path.home()/'.cache/helix-orca-calibration/v1-engine/source-6a7763f0')
    parser.add_argument('--cache',type=Path,default=Path.home()/'.cache/helix-orca-calibration/v1-engine')
    parser.add_argument('--downloads',type=Path,default=Path.home()/'.cache/helix-orca-calibration/v1-engine/downloads')
    parser.add_argument('--container')
    args=parser.parse_args()
    if args.operation=='_compile':
        try:
            compile_offline()
        finally:
            usage = {}
            for key in ('memory.peak', 'memory.events', 'pids.peak', 'cpu.stat'):
                path = Path('/sys/fs/cgroup') / key
                if path.exists(): usage[key] = path.read_text()
            Path('/evidence/resource-usage.json').write_text(json.dumps(usage, indent=2)+'\n')
    elif args.operation=='_follow':
        subprocess.run(['docker','logs','--follow',args.container],check=True)
        code=int(subprocess.check_output(['docker','wait',args.container],text=True).strip())
        raise SystemExit(code)
    else:build(args)


if __name__=='__main__':main()
