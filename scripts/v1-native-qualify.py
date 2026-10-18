#!/usr/bin/env python3
"""Source-bound synthetic V1 beta.9 matrix. No hardware or generator parity claims."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
q=load('v1_native_q',ROOT/'scripts/temperature-communication-qualify.py')
a=q.accepted
builder=load('v1_native_builder',ROOT/'scripts/v1-native-plugin.py')
contract=load('v1_native_contract',ROOT/'integration/v1_contract.py')
ASSERTIONS=['native-five-calibration-chooser','native-bounded-parameter-configuration','generate-only-request-no-start','unqualified-and-mismatched-preparation-locks-controls','separate-confirm-then-explicit-start','monotonic-status-and-exact-job','independent-completion-gates-evaluation','immutable-original-context-result','exact-originating-receipt-only','native-back-and-horizontal-fit','physical-adapter-absent','fresh-nonce-next-calibration-after-delivery-and-block']
def hashes():
    paths=[ROOT/'scripts/v1-native-plugin.py',ROOT/'scripts/v1-native-qualify.py',ROOT/'integration/v1_contract.py',ROOT/'scripts/temperature-communication-plugin.py',ROOT/'scripts/temperature-communication-qualify.py',ROOT/'scripts/helix-beta9-qualify.py',ROOT/'scripts/helix_dev.py']+list((ROOT/'integration/v1-native').rglob('*'))
    return {str(p.relative_to(ROOT)):q.sha256(p) for p in sorted(paths) if p.is_file()}
def require(value,message):
    if not value:raise ValueError(message)
def fixture(root):
    target=root/'orcacal';builder.generate(target)
    defaults=json.dumps(contract.DEFAULTS,separators=(',',':'))
    hook='''
-- SYNTHETIC UI TEST FIXTURE ONLY; never included by the product builder.
local fixture_serial=0
local fixture_signal=helix.subject.int('v1_fixture_signal',0)
local fixture_defaults=helix.json.decode([==[DEFAULTS]==])
local function fixture_offer()
 fixture_serial=fixture_serial+1
 local capabilities={}
 for id,_ in pairs(V1_CATALOG) do capabilities[#capabilities+1]={id=id,available=true,reason='Synthetic UI fixture only'} end
 v1_receive_offer('fixture',{schema='helix-orca-v1-offer/v1',request_id=string.format('%032x',fixture_serial),origin_id=string.rep('a',32),context_sha256=string.rep('b',64),printer='Synthetic printer',process='Synthetic process',filament='Synthetic PLA',nozzle_mm=0.4,capabilities=capabilities,defaults=fixture_defaults,created_at=1000,expires_at=4600})
end
local function fixture_status(phase)
 local r=v1_session.request
 local p={schema='helix-orca-v1-prepared/v1',request_id=r.request_id,origin_id=r.origin_id,context_sha256=r.context_sha256,request_sha256=string.rep('c',64),calibration=r.calibration,parameters=r.parameters,artifact={name='synthetic-calibration.gcode',size=12345,sha256=string.rep('d',64)},generator={build='synthetic-only',route='synthetic-ui'},parity={qualified=true,report_sha256=string.rep('e',64),reason='SYNTHETIC UI parity fixture · not generator qualification'},not_applied=true}
 local d={schema='helix-orca-v1-status/v1',request_id=r.request_id,origin_id=r.origin_id,sequence=v1_session.sequence+1,phase=phase,message='Synthetic UI fixture · '..phase,prepared=p,prepared_sha256=string.rep('f',64)}
 if phase=='printing' or phase=='verifying' or phase=='complete' then d.job_id='synthetic-job-'..r.request_id end
 if phase=='complete' then
  local settings={temperature='nozzle_temperature',flow_ratio_yolo='filament_flow_ratio',pressure_advance_pattern='pressure_advance',retraction='filament_retraction_length',max_volumetric_speed='filament_max_volumetric_speed'}
  local values={temperature={230,225,220},flow_ratio_yolo={0.98,1,1.02},pressure_advance_pattern={0.02,0.025,0.03},retraction={0.5,0.6,0.7},max_volumetric_speed={15,16,17}}
  d.completion_sha256=string.rep('1',64);d.evaluation={setting=settings[r.calibration],options=values[r.calibration],unit=''}
 end
 return d
end
fixture_signal:observe(function(value)
 local code=value%100
 if code==1 then fixture_offer()
 elseif code==2 then v1_receive_status('fixture',fixture_status('preparing'))
 elseif code==3 then
  local d=fixture_status('review');d.prepared.parity.qualified=false;v1_receive_status('fixture',d)
  if v1_session.phase=='review' then error('Unqualified review accepted') end
  d.prepared.parity.qualified=true;d.prepared.request_id=string.rep('9',32);v1_receive_status('fixture',d)
  if v1_session.phase=='review' then error('Mismatched preparation accepted') end
  v1_receive_status('fixture',fixture_status('review'))
 elseif code==4 then v1_receive_status('fixture',fixture_status('confirmed'))
 elseif code==5 then v1_receive_status('fixture',fixture_status('printing'))
 elseif code==6 then
  local d=fixture_status('complete');d.completion_sha256=nil;v1_receive_status('fixture',d)
  if v1_session.phase=='complete' then error('Unverified completion accepted') end
  v1_receive_status('fixture',fixture_status('complete'))
 elseif code==7 then
  local result=v1_session.result
  local wrong=helix.json.decode(helix.json.encode(result));wrong.value=999
  local ack={schema='helix-orca-v1-ack/v1',request_id=result.request_id,origin_id=result.origin_id,result_sha256=string.rep('2',64),result=wrong,not_applied=true}
  v1_receive_ack('fixture',ack)
  if v1_session.receipt then error('Wrong result acknowledged') end
  ack.result=result;v1_receive_ack('fixture',ack);v1_receive_ack('fixture',ack)
 elseif code==8 then
  local before=helix.json.encode(v1_session.result)
  v1_receive_status('fixture',fixture_status('failed'))
  if helix.json.encode(v1_session.result)~=before then error('Late status replaced committed result') end
 elseif code==9 then
  local before=v1_session.sequence
  local d=fixture_status('preparing');d.sequence=0;v1_receive_status('fixture',d)
  if v1_session.sequence~=before then error('Stale status changed sequence') end
 elseif code==10 then
  local d=fixture_status('blocked');d.prepared.parity.qualified=false;d.prepared.artifact=nil;d.message='Synthetic blocked generator: native parity unavailable';v1_receive_status('fixture',d)
 end
end)
fixture_offer()
'''.replace('DEFAULTS',defaults)
    with (target/'main.lua').open('a') as f:f.write(hook)
    return root

def settings(path):
    q.seed_settings(path)
    s=json.loads((path/'settings-test.json').read_text())
    s['plugins']['enabled']['orcacal']['version']='1.0.0-v1-candidate'
    widgets=s['printers']['default']['panel_widgets']['home']['pages'][0]['widgets']
    widgets[:]=[w for w in widgets if w['id']=='orcacal__tile' or not w['enabled']]
    widgets[0].update(colspan=2,rowspan=2)
    a.json_write(path/'settings-test.json',s)
def ctl(name,*args):return a.ctl(name,*args)
def value(name,key):return ctl(name,'get','orcacal__v1_'+key).get('value')
def signal(name,code):
    previous=value(name,'fixture_signal');ctl(name,'set','orcacal__v1_fixture_signal',str((previous//100+1)*100+code));ctl(name,'wait_idle');time.sleep(.4)
def tap(name,widget,w,h,work):
    ctl(name,'scroll',widget);ctl(name,'wait_idle')
    g=a._visible_widget_geometry(ctl(name,'geom',widget,'0'),widget,w,h)
    coords={'x':int(g['x'])+int(g['w'])//2,'y':int(g['y'])+int(g['h'])//2}
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(3)
        directory=os.open(work,os.O_RDONLY|os.O_DIRECTORY)
        try:client.connect(f'/proc/self/fd/{directory}/control.sock')
        finally:os.close(directory)
        stream=client.makefile('rwb',buffering=0)
        try:
            for n,method in enumerate(('pointer_press','pointer_release'),1):
                stream.write((json.dumps(dict(jsonrpc='2.0',id=n,method=method,params=coords))+'\n').encode())
                reply=json.loads(stream.readline(65537));require(reply.get('id')==n and 'error' not in reply,'Native pointer failed')
        finally:stream.close()
    ctl(name,'wait_idle');time.sleep(.35)
def storage(work):
    path=work/'config/plugin-data/orcacal.json';deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        if path.exists():
            try:return json.loads(path.read_text())['v1_session']
            except (KeyError,json.JSONDecodeError):pass
        time.sleep(.05)
    raise ValueError('Native storage missing')
def drive(entry,name,work):
    label,w,h,layout,dpi=entry
    q.wait_ready(name)
    a._screenshot(name,work,'home.png')
    tap(name,'orcacal__tile',w,h,work)
    a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_wizard_content','8'),w)
    a._screenshot(name,work,'chooser.png')
    for i,id in enumerate(contract.CALIBRATIONS):
        if i:
            q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
        tap(name,'orcacal__v1_choose_'+id,w,h,work)
        a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_v1_'+id+'_content','8'),w)
        a._screenshot(name,work,id+'-configure.png')
        parameter='start' if id=='temperature' else 'end'
        if id!='flow_ratio_yolo':
            ctl(name,'set_value','orcacal__v1_'+id+'_'+parameter,'1')
            require(value(name,id+'_'+parameter+'_idx')==1,'Native parameter binding failed')
        tap(name,'orcacal__v1_generate_'+id,w,h,work)
        require(value(name,'confirm_on')==0 and value(name,'start_on')==0,'Generate unlocked execution')
        signal(name,2);signal(name,9);signal(name,3)
        require(value(name,'confirm_on')==1 and value(name,'start_on')==0,'Review controls invalid')
        a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_v1_job_content','8'),w)
        ctl(name,'scroll','orcacal__v1_confirm');a._screenshot(name,work,id+'-review.png')
        tap(name,'orcacal__v1_confirm',w,h,work)
        require(value(name,'start_on')==0,'Confirm started printing')
        signal(name,4);require(value(name,'start_on')==1,'Confirmed job lacks deliberate Start')
        tap(name,'orcacal__v1_start',w,h,work);require(value(name,'start_on')==0,'Start repeated')
        signal(name,5);require(value(name,'evaluate_on')==0,'Printing unlocked evaluation')
        ctl(name,'scroll','orcacal__v1_job_message');a._screenshot(name,work,id+'-monitor.png')
        signal(name,6);require(value(name,'evaluate_on')==1,'Successful exact-job completion did not unlock evaluation')
        ctl(name,'scroll','orcacal__v1_evaluation');a._screenshot(name,work,id+'-evaluate.png')
        # Select through the actual native dropdown widget's two-way binding.
        # Every workflow action uses native pointer input.
        ctl(name,'set_value','orcacal__v1_evaluation','1')
        tap(name,'orcacal__v1_return',w,h,work);require(value(name,'evaluate_on')==0,'Returned result editable')
        signal(name,8);signal(name,7)
        require('Returned to original Orca' in value(name,'returned'),'Exact receipt not shown')
        ctl(name,'scroll','orcacal__v1_returned_status');a._screenshot(name,work,id+'-returned.png')
        deadline=time.monotonic()+5
        while True:
            saved=storage(work)
            if saved.get('receipt') and saved['request']['calibration']==id:break
            if time.monotonic()>deadline:raise ValueError('Receipt not durable')
            time.sleep(.1)
        contract.validate_request(saved['request'],now=1001)
        require(saved['result']['value']==saved['evaluation']['options'][1],'Wrong native selection returned')
        require(saved['result']['context_sha256']=='b'*64,'Original context changed')
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_temperature',w,h,work);tap(name,'orcacal__v1_generate_temperature',w,h,work);signal(name,10)
    require(value(name,'confirm_on')==0 and value(name,'start_on')==0,'Blocked generation unlocked execution')
    a._screenshot(name,work,'blocked.png')
    blocked_request=storage(work)['request']['request_id']
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_flow_ratio_yolo',w,h,work);tap(name,'orcacal__v1_generate_flow_ratio_yolo',w,h,work)
    signal(name,2)
    require(value(name,'phase')=='preparing','Fresh nonce did not retire blocked work')
    deadline=time.monotonic()+5
    while True:
        next_request=storage(work)['request']
        if next_request['request_id']!=blocked_request:break
        if time.monotonic()>deadline:raise ValueError('Fresh request was not durable')
        time.sleep(.1)
    require(next_request['calibration']=='flow_ratio_yolo' and next_request['context_sha256']=='b'*64,'Next calibration retargeted context')
    logs=a.run(['docker','logs',name],capture=True,check=False)
    (work/'runtime.log').write_text(logs.stdout+logs.stderr)
    require('[plugin orcacal]' not in logs.stdout+logs.stderr,'Native runtime error')
    q.back_to_home(name)
    return {'label':label,'viewport':f'{w}x{h}','layout':layout,'dpi':dpi,'result':'PASS','calibrations':list(contract.CALIBRATIONS),'assertions':ASSERTIONS}

def capture(output,only=None):
    before=hashes();runtime=q.beta9.verify_cache();q.beta9.configure_accepted_harness()
    require(not output.exists(),'Refusing to overwrite evidence');output.mkdir(parents=True)
    resource=load('v1_resource_lifecycle',Path('/home/dev/Projects/system/100-day-development-system/scripts/resource_lifecycle.py'))
    cache=builder.default_output().parent;cache.mkdir(parents=True,exist_ok=True)
    plugins=fixture(cache/('fixture-'+uuid.uuid4().hex));fixture_hashes=q.file_hashes(plugins/'orcacal')
    rows=[];runs=[]
    class NativeDocker(resource.DockerCLI):
        def create(self,run_id,image,command,memory,cpus,pids):
            require(image.startswith('sha256:'),'Immutable dependency required')
            require(not json.loads(self.call('image','inspect','--format','{{json .Config.Volumes}}',image)),'Image volumes forbidden')
            args=a._container_args('v1-native-'+run_id,work,w,h,layout,dpi)
            args[1]='create';args.remove('--detach');args[args.index(a.IMAGE)]=image
            args[2:2]=['--label',resource.LABEL+'='+run_id,'--restart=no','--memory',str(memory),'--memory-swap',str(memory),'--cpus',str(cpus),'--pids-limit',str(pids),'--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2']
            return self.call(*args[1:])
    for entry in a.VIEWPORTS:
        label,w,h,layout,dpi=entry
        if only and label!=only:continue
        adapter=NativeDocker()
        a.PLUGIN_ROOT=plugins
        image_id=a.image_metadata()['id']
        commit=a.run(['git','rev-parse','HEAD'],capture=True,cwd=ROOT).stdout.strip()
        with resource.ManagedRun(app='helix-orca-v1-native',repo=str(ROOT),issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',commit=commit,dirty_input=contract.digest(before),paths=[str(output.parent),str(cache),str(ROOT)],reserve=5*1024**3,peak=512*1024**2,margin=512*1024**2,timeout=240,adapter=adapter) as run:
            work=run.artifacts/label;work.mkdir();(work/'home').mkdir();settings(work/'config')
            cid=run.container(image_id,[],memory=512*1024**2,cpus=2,pids=128)
            result=run.execute([sys.executable,str(Path(__file__).resolve()),'_drive',str(work),'--viewport',label,'--container',cid],cwd=ROOT)
            require(run.data.get('exit_code')==0,'Native workload failed; inspect '+str(run.directory))
        require(run.data['state']=='complete','Managed native lifecycle incomplete')
        require(hashes()==before,'Candidate sources changed during native capture')
        shutil.copytree(work,output/label,ignore=shutil.ignore_patterns("control.sock"))
        rows.append(json.loads((work/'row.json').read_text()));runs.append({'run_id':run.data['run_id'],'manifest':str(run.directory/'manifest.json'),'containers':list(run.data['containers']),'runtime_clear':run.data['verification']['runtime_clear']})
        print('PASS '+label,flush=True)
    require(q.file_hashes(plugins/'orcacal')==fixture_hashes,'Fixture changed')
    report={'schema':'helix-orca-v1-native-evidence/v1','sources':before,'runtime':runtime,'container_network':'none','physical_actions':0,'synthetic_only':True,'synthetic_inputs':['context','generator availability','prepared artifact','parity','print status','completion proof','receipt'],'fixture_files':fixture_hashes,'results':rows,'managed_runs':runs,'screenshots':{str(p.relative_to(output)):q.sha256(p) for p in sorted(output.rglob('*.png'))}}
    a.json_write(output/'report.json',report)

def verify(output):
    r=json.loads((output/'report.json').read_text())
    require(r['sources']==hashes(),'Sources differ');require(r['runtime']==q.beta9.verify_cache(),'Runtime differs')
    require(r['synthetic_only'] and r['physical_actions']==0 and r['container_network']=='none','Isolation differs')
    require([v['label'] for v in r['results']]==[v[0] for v in a.VIEWPORTS],'All eleven viewports required')
    for row in r['results']:require(row['assertions']==ASSERTIONS and row['calibrations']==list(contract.CALIBRATIONS) and row['result']=='PASS','Incomplete workflow proof')
    require(len(r['screenshots'])==11*28,'Incomplete screenshots')
    for name,digest in r['screenshots'].items():require(q.sha256(output/name)==digest,'Screenshot differs')
    for item in r['managed_runs']:
        manifest=json.loads(Path(item['manifest']).read_text());require(manifest['state']=='complete' and manifest['verification']['runtime_clear'],'Managed run incomplete')
    print('PASS: source-bound synthetic V1 beta.9 eleven-target/five-calibration matrix')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('op',choices=['capture','verify','_drive']);p.add_argument('output',type=Path,nargs='?');p.add_argument('--viewport');p.add_argument('--container');x=p.parse_args()
    output=x.output or q.state_root().parent/'v1-native'/time.strftime('%Y%m%d-%H%M%S')
    if x.op=='capture':capture(output,x.viewport)
    elif x.op=='verify':verify(output)
    else:
        q.beta9.configure_accepted_harness();entry=next(e for e in a.VIEWPORTS if e[0]==x.viewport)
        row=drive(entry,x.container,output);a.json_write(output/'row.json',row)
