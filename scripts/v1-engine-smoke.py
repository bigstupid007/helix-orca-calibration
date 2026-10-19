#!/usr/bin/env python3
"""Private, offline, managed generation checkpoint; never printer execution."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v1_contract as contract
from integration import v1_engine as engine

HELPER = Path('/home/dev/Projects/system/100-day-development-system/scripts/resource_lifecycle.py')
HELPER_HASH = '8a2cb48220f14c8f4ca5c2cc9f6fcdcdf28fa436fe4b7dd50cf6489178ba6fcc'
IMAGE = 'sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9'
PARAMETERS = {'temperature': {'start':230,'end':190,'step':5,'scale':True},
              'pressure_advance_pattern': {'start':0,'end':.08,'step':.005},
              'retraction': {'start':0,'end':2,'step':.1},
              'max_volumetric_speed': {'start':5,'end':20,'step':.5}}


def record(path):
    return {'path':str(path),'sha256':engine._sha_file(path)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-run',type=Path,required=True)
    parser.add_argument('--context',type=Path,required=True)
    parser.add_argument('--calibration',choices=['all',*PARAMETERS],default='all')
    parser.add_argument('--cache',type=Path,default=Path.home()/'.cache/helix-orca-calibration/v1-engine')
    args=parser.parse_args()
    if engine._sha_file(HELPER)!=HELPER_HASH: raise ValueError('Lifecycle helper pin differs')
    spec=importlib.util.spec_from_file_location('native_smoke_resource',HELPER)
    resource=importlib.util.module_from_spec(spec);spec.loader.exec_module(resource)
    build=(args.cache/'build-6a7763f0').resolve()
    source=(args.cache/'source-6a7763f0').resolve()
    evidence=(args.build_run/'artifacts').resolve()
    config={'build_receipt':record(evidence/'native-build.json'),
            'build_inputs':record(evidence/'native-inputs.json'),
            'native_executable':record(build/'engine/helix_orca_native'),
            'native_resources':str(source/'resources')}
    before=record(args.context)
    if args.context.stat().st_size>1048576 or args.context.is_symlink(): raise ValueError('Bounded context required')
    snapshot=contract.validate_context(json.loads(args.context.read_text()))
    # Verify actual source-bound receipt/host/resources before creating a job.
    engine.require_native_generation('pressure_advance_pattern',config)
    class OfflineDocker(resource.DockerCLI):
        def create(self,run_id,image,command,memory,cpus,pids):
            if image!=IMAGE or json.loads(self.call('image','inspect','--format','{{json .Config.Volumes}}',image)):
                raise resource.Refused('Immutable smoke image/volume differs')
            return self.call('create','--label',resource.LABEL+'='+run_id,'--restart=no',
                '--user',str(os.getuid())+':'+str(os.getgid()),'--network','none','--read-only',
                '--cap-drop','ALL','--security-opt','no-new-privileges','--memory',str(memory),
                '--memory-swap',str(memory),'--cpus',str(cpus),'--pids-limit',str(pids),
                '--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2',
                '--tmpfs','/tmp:rw,noexec,nosuid,size=128m',
                '--mount','type=bind,source='+str(build)+',target=/build,readonly',
                '--mount','type=bind,source='+str(source)+',target=/source,readonly',
                '--mount','type=bind,source='+str(run.artifacts)+',target=/evidence',
                '--env','OMP_NUM_THREADS=2',
                '--env','HELIX_NATIVE_DIAGNOSTICS=1',
                '--env','LD_LIBRARY_PATH=/build/prefix/usr/local/lib:/build/prefix/usr/local/libpython/lib',
                image,*command)
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    rows=[]
    for name in PARAMETERS if args.calibration=='all' else [args.calibration]:
        with resource.ManagedRun(app='helix-orca-v1-native-generation',repo=str(ROOT),
                issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',commit=commit,
                dirty_input=engine._sha_file(Path(__file__)),paths=[str(args.cache),str(ROOT),str(args.context.parent)],
                reserve=10*1024**3,peak=2*1024**3,margin=2*1024**3,timeout=300,adapter=OfflineDocker()) as run:
            print('Managed native generation: '+str(run.directory),flush=True)
            def runner(argv,destination):
                mapped=[]
                for argument in argv:
                    path=Path(argument)
                    for host,guest in [(build,'/build'),(source,'/source'),(run.artifacts,'/evidence')]:
                        if path.is_relative_to(host):
                            argument=str(Path(guest)/path.relative_to(host));break
                    else: raise ValueError('Native invocation path outside declared smoke mounts')
                    mapped.append(argument)
                cid=run.container(IMAGE,mapped,memory=4*1024**3,cpus=2,pids=128)
                run.execute([sys.executable,str(ROOT/'scripts/v1-engine-native.py'),'_follow','--container',cid],cwd=ROOT)
                shutil.copyfile(run.artifacts/'run.log',destination/'native.log')
                # The context manager removes this exact owned container before
                # the next calibration gets a separate ManagedRun.
                return run.data.get('exit_code')
            config['runner']=runner
            now=int(time.time())
            request={'schema':'helix-orca-v1-request/v1','request_id':uuid.uuid4().hex,
                'origin_id':snapshot['origin_id'],'context_sha256':contract.digest(snapshot),
                'calibration':name,'parameters':PARAMETERS[name],'created_at':now,'expires_at':now+600,'not_applied':True}
            try:
                prepared=engine.generate(request,snapshot,run.artifacts/name,config)
                rows.append({'calibration':name,'run_id':run.data['run_id'],'generated':True,'artifact':prepared['artifact'],
                             'qualified':prepared['parity']['qualified'],'reason':prepared['parity']['reason']})
            except (engine.NativeEngineBlocked,OSError,ValueError,KeyError,TypeError) as exc:
                rows.append({'calibration':name,'run_id':run.data['run_id'],'generated':False,'qualified':False,'reason':str(exc)})
            print(json.dumps(rows[-1]),flush=True)
            if record(args.context)!=before: raise ValueError('Retained context changed during smoke')
            (run.artifacts/'native-grouped-checkpoint.json').write_text(json.dumps({
                'source_commit':engine.ORCA_SOURCE,'context_sha256':contract.digest(snapshot),
                'context_file_sha256':before['sha256'],'smoke_source_sha256':engine._sha_file(Path(__file__)),
                'build_receipt_sha256':config['build_receipt']['sha256'],'not_applied':True,
                'physical_test':False,'results':rows},indent=2)+'\n')
        print('CHECKPOINT '+str(run.directory),flush=True)
        if not rows[-1]['generated']:
            # Native startup/configuration is shared. Preserve the first exact
            # failure and clear its runtime before investigating it; never spend
            # four deadlines repeating a blocked common pipeline.
            print('GROUP STOPPED: shared native generation gate requires diagnosis',flush=True)
            break


if __name__=='__main__':main()
