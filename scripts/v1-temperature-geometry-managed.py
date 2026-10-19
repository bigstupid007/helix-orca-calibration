#!/usr/bin/env python3
"""Bounded offline native mesh preparation; no slicer, printer or qualification."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration import v1_contract as c, v1_engine as e, v1_temperature_geometry as geometry
HELPER=Path('/home/dev/Projects/system/100-day-development-system/scripts/resource_lifecycle.py')
HELPER_SHA='8a2cb48220f14c8f4ca5c2cc9f6fcdcdf28fa436fe4b7dd50cf6489178ba6fcc'
IMAGE='sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9'
def record(path):return dict(path=str(path),sha256=e._sha_file(path))
def closure():
 paths = sorted((ROOT/'integration').glob('v1_*.py')) + [
  ROOT/'integration/__init__.py', Path(__file__).resolve(), ROOT/'scripts/v1-engine-native.py', HELPER,
  Path(sys.executable).resolve()]
 return {str(path):record(path) for path in paths if path.is_file()}
def assert_unchanged(manifest):
 if closure()!=manifest['python_closure'] or any(record(Path(row['path']))!=row for row in manifest['inputs']):
  raise ValueError('Executed Python closure or immutable geometry input changed')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--build-run',type=Path,required=True);p.add_argument('--context',type=Path,required=True)
 p.add_argument('--parameters',type=Path);p.add_argument('--seconds',type=int,default=60)
 p.add_argument('--cache',type=Path,default=Path.home()/'.cache/helix-orca-calibration/v1-engine')
 a=p.parse_args()
 if not 15<=a.seconds<=120 or e._sha_file(HELPER)!=HELPER_SHA:raise ValueError('Reviewed helper/deadline required')
 if a.context.is_symlink() or a.context.stat().st_size>c.MAX_MESSAGE:raise ValueError('Bounded regular context required')
 context_before=record(a.context);snapshot=c.validate_context(json.loads(a.context.read_text()))
 parameters=dict(c.DEFAULTS['temperature'])
 if a.parameters:
  if a.parameters.is_symlink() or a.parameters.stat().st_size>4096:raise ValueError('Bounded parameter JSON required')
  parameters=c.validate_parameters('temperature',json.loads(a.parameters.read_text()))
 build=(a.cache/'build-6a7763f0').resolve();source=(a.cache/'source-6a7763f0').resolve();prior=(a.build_run/'artifacts').resolve()
 config=dict(build_receipt=record(prior/'native-build.json'),build_inputs=record(prior/'native-inputs.json'),
             native_executable=record(build/'engine/helix_orca_native'),native_resources=str(source/'resources'),timeout_seconds=a.seconds)
 e.require_native_generation('temperature',config)
 provenance=dict(schema='helix-orca-v1-geometry-execution-inputs/v1',python_closure=closure(),
    inputs=[context_before,config['build_receipt'],config['build_inputs'],config['native_executable']] +
           ([record(a.parameters)] if a.parameters else []),parameters=parameters,
    lifecycle_helper_sha256=HELPER_SHA,container_image=IMAGE)
 assert_unchanged(provenance)
 provenance_sha=c.digest(provenance)
 spec=importlib.util.spec_from_file_location('geometry_managed_resource',HELPER);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
 class Offline(h.DockerCLI):
  def create(self,run_id,image,command,memory,cpus,pids):
   if image!=IMAGE or json.loads(self.call('image','inspect','--format','{{json .Config.Volumes}}',image)):raise h.Refused('Pinned image without volumes required')
   return self.call('create','--label',h.LABEL+'='+run_id,'--restart=no','--user',str(os.getuid())+':'+str(os.getgid()),
       '--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
       '--memory',str(memory),'--memory-swap',str(memory),'--cpus',str(cpus),'--pids-limit',str(pids),
       '--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2',
       '--tmpfs','/tmp:rw,noexec,nosuid,size=128m',
       '--mount','type=bind,source='+str(build)+',target=/build,readonly',
       '--mount','type=bind,source='+str(source)+',target=/source,readonly',
       '--mount','type=bind,source='+str(run.artifacts)+',target=/evidence',
       '--env','OMP_NUM_THREADS=2','--env','LD_LIBRARY_PATH=/build/prefix/usr/local/lib:/build/prefix/usr/local/libpython/lib',image,*command)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 with h.ManagedRun(app='helix-orca-v1-temperature-geometry',repo=str(ROOT),issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',
      commit=commit,dirty_input=provenance_sha,paths=[str(a.cache),str(ROOT),str(a.context.parent)],
      reserve=10*1024**3,peak=2*1024**3,margin=2*1024**3,timeout=a.seconds,adapter=Offline()) as run:
  (run.artifacts/'geometry-execution-inputs.json').write_bytes(c.canonical(provenance))
  print(json.dumps(dict(run_id=run.data['run_id'],state='preparing',qualified=False,physical_actions=False)),flush=True)
  def runner(argv,destination):
   assert_unchanged(provenance)
   if len(argv)!=6 or argv[1]!='--prepare-temperature':raise ValueError('Geometry-only invocation required')
   mapped=[]
   for index,argument in enumerate(argv):
    if index==1:mapped.append(argument);continue
    path=Path(argument)
    for host,guest in ((build,'/build'),(source,'/source'),(run.artifacts,'/evidence')):
     if path.is_relative_to(host):mapped.append(str(Path(guest)/path.relative_to(host)));break
    else:raise ValueError('Invocation outside declared private mounts')
   cid=run.container(IMAGE,mapped,memory=1024**3,cpus=2,pids=128)
   run.execute([sys.executable,str(ROOT/'scripts/v1-engine-native.py'),'_follow','--container',cid],cwd=ROOT)
   return run.data.get('exit_code')
  config['runner']=runner;now=int(time.time())
  request=dict(schema='helix-orca-v1-request/v1',request_id=uuid.uuid4().hex,origin_id=snapshot['origin_id'],
               context_sha256=c.digest(snapshot),calibration='temperature',parameters=parameters,created_at=now,expires_at=now+300,not_applied=True)
  receipt=geometry.prepare(request,snapshot,run.artifacts/'geometry',config)
  assert_unchanged(provenance)
 if run.data['state']!='complete' or not run.data['verification']['runtime_clear']:raise ValueError('Incomplete geometry lifecycle')
 summary=dict(schema='helix-orca-v1-native-geometry-checkpoint/v1',run_id=run.data['run_id'],state='complete',runtime_clear=True,
              model_sha256=receipt['model']['sha256'],parameters=parameters,triangles=receipt['metrics']['triangles'],
              receipt_sha256=c.digest(receipt),execution_inputs_sha256=provenance_sha,gcode_generated=False,qualified=False,physical_actions=False)
 (run.artifacts/'geometry-summary.json').write_bytes(c.canonical(summary));print(c.canonical(summary).decode())
if __name__=='__main__':main()
