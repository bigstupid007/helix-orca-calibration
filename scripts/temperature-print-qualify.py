#!/usr/bin/env python3
"""Network-none beta.9 native qualification; all job/status/clock inputs synthetic."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=load('print_accepted_qualification',ROOT/'scripts/temperature-communication-qualify.py')
a=q.accepted
pgen=load('print_native_generator',ROOT/'scripts/temperature-print-plugin.py')
REQUEST=dict(q.VALID_REQUEST)
REQUEST.pop('simulation_only')
REQUEST.update(schema='helix-orca-temperature-print-session/v1',physical_calibration=True,
               choices=[210,205,200],file='miniature-temperature-210-200.gcode',ttl_seconds=3600,
               file_bytes=200000,file_sha256='a'*64,context_sha256='b'*64)
LEASE={'issued_eventtime':1000.0,'expires_eventtime':4600.0}
ASSERTIONS=['accepted-shell-loads','receive-never-starts','picker-locked-before-success',
    'authorized-ready-needs-native-start','native-start-persists-once','rpc-ack-does-not-unlock',
    'matching-printing-keeps-picker-locked','restart-never-redispatches-and-recovers-verified-state','history-lag-stays-nonterminal','independent-success-enables-three-choices',
    'native-205-result-has-completion-proof','original-context-preserved','native-back-and-horizontal-fit','terminal-session-retires-with-replay-tombstone']
SOURCES=['scripts/temperature-print-plugin.py','scripts/temperature-print-qualify.py',
'integration/temperature-print/native.lua','integration/temperature-print/ui/orcacal__temperature.xml',
'integration/temperature-print/ui/orcacal__wizard.xml','scripts/temperature-print-companion.py',
'scripts/temperature-communication-qualify.py','scripts/temperature-communication-plugin.py','scripts/helix-beta9-qualify.py','scripts/helix_dev.py']
def hashes():return {s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}

def fixture(directory):
    root=directory/'plugins';target=root/'orcacal';pgen.generate(target)
    request=json.dumps(REQUEST,separators=(',',':'));lease=json.dumps(LEASE,separators=(',',':'))
    hook='''
-- TEST-ONLY inputs below; absent from generated product. No hardware route exists.
local fixture_state="standby"
local fixture_filename=""
local fixture_eventtime=1000.25
local original_call=helix.moonraker.call
helix.moonraker.call=function(method,params)
    if method=="printer.objects.query" then
        return {result={eventtime=fixture_eventtime,status={print_stats={state=fixture_state,filename=fixture_filename}}}}
    end
    return original_call(method,params)
end
local fixture_request=helix.json.decode([==[REQUEST]==])
local fixture_lease=helix.json.decode([==[LEASE]==])
helix.ui.on("qualify_request",function()
    if not session then
        query_busy=true; receive("fixture",{session=fixture_request,lease=fixture_lease}); query_busy=false
        if session then error("Busy receive committed a session") end
    end
    receive("fixture",{session=fixture_request,lease=fixture_lease})
end)
local function fixture_status(state,n)
    n=math.max(n,(session.status_sequence or 0)+1)
    local d={schema="helix-orca-temperature-print-status/v1",state=state,sequence=n,eventtime=fixture_eventtime,
        authorized=true,estimated_duration_s=900,job_id="000001",completion_sha256=string.rep("c",64)}
    for _,k in ipairs(identity_keys) do d[k]=fixture_request[k] end
    update("fixture",d)
end
helix.ui.on("qualify_ready",function() fixture_status("ready",1) end)
helix.ui.on("qualify_printing",function()
    fixture_state="printing"; fixture_filename=fixture_request.file; fixture_status("printing",2)
end)
helix.ui.on("qualify_confirming",function()
    fixture_state="complete"; fixture_status("confirming",3)
end)
helix.ui.on("qualify_complete",function()
    fixture_state="complete"; fixture_status("complete",4)
end)
helix.ui.on("qualify_ack",function()
    local result=session.result
    if not result then return end
    local ack={}
    for k,v in pairs(result) do ack[k]=v end
    ack.schema="helix-orca-temperature-print-ack/v1"
    acknowledgement("fixture",ack)
end)
helix.ui.on("qualify_fresh",function()
    local fresh=helix.json.decode([==[REQUEST]==])
    fresh.request_id=string.rep("3",32); fresh.origin_id=string.rep("4",32)
    receive("fixture",{session=fresh,lease=fixture_lease})
end)
'''.replace('REQUEST',request).replace('LEASE',lease)
    with (target/'main.lua').open('a') as f:f.write(hook)
    manifest=json.loads((target/'manifest.json').read_text())
    for action,label in [('request','Receive request'),('ready','Qualify ready'),('printing','Observe printing'),('confirming','Wait for history'),('complete','Confirm completion'),('ack','Confirm Orca receipt'),('fresh','Receive next request')]:
        component='orcacal__qualify-'+action
        manifest['widgets'].append({'id':component,'name':label,'icon':'download','description':'Synthetic isolated qualification input','component':component,'colspan':3,'rowspan':2})
        (target/'ui'/f'{component}.xml').write_text(q.TILE_XML.format(component=component,action='qualify_'+action,label=label))
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return root

def settings(path):
    q.seed_settings(path)
    s=json.loads((path/'settings-test.json').read_text())
    s['plugins']['enabled']['orcacal']['version']='0.4.0-issue12-readiness'
    widgets=s['printers']['default']['panel_widgets']['home']['pages'][0]['widgets']
    keep=[w for w in widgets if w['id']=='orcacal__tile' or not w['enabled']]
    for i,action in enumerate(('request','ready','printing','confirming','complete','ack','fresh')):
        keep.append({'col':(i%3)*4,'row':2+(i//3)*2,'colspan':4,'rowspan':2,'enabled':True,'id':'orcacal__qualify-'+action})
    s['printers']['default']['panel_widgets']['home']['pages'][0]['widgets']=keep
    a.json_write(path/'settings-test.json',s)

def value(name,subject):return a.ctl(name,'get','orcacal__'+subject).get('value')
def require(ok,message):
    if not ok:raise ValueError(message)
def trigger(name,action,w,h):
    q.back_to_home(name);q.tap(name,'orcacal__qualify-'+action,w,h);a.ctl(name,'wait_idle')
def open_detail(name,w,h):
    if not a.ctl(name,'current').get('overlays'):q.open_temperature(name,w,h)
def read_storage(work):
    time.sleep(.7)
    return json.loads((work/'config/plugin-data/orcacal.json').read_text())['print_session']

def viewport(entry,output,plugins):
    label,w,h,layout,dpi=entry;work=output/label;work.mkdir();(work/'home').mkdir();settings(work/'config')
    name='temperature-print-'+str(os.getpid())+'-'+label.replace('_','-')
    a.PLUGIN_ROOT=plugins;a._remove_container(name)
    a.run(a._container_args(name,work,w,h,layout,dpi),capture=True)
    try:
        q.wait_ready(name)
        trigger(name,'request',w,h)
        require(value(name,'tp_start_on')==0 and value(name,'tc_choice_on')==0,'Receipt unlocked an action')
        s=read_storage(work);require('start_intent' not in s and 'result' not in s,'Receipt started or returned')
        a.ctl(name,'scroll','orcacal__request_status');a._screenshot(name,work,'received.png')
        trigger(name,'ready',w,h);open_detail(name,w,h)
        require(value(name,'tp_start_on')==1 and value(name,'tc_choice_on')==0,'Ready controls invalid')
        a.ctl(name,'scroll','orcacal__print_start');a._screenshot(name,work,'ready.png')
        q.tap(name,'orcacal__print_start',w,h)
        require(value(name,'tp_start_on')==0 and value(name,'tc_choice_on')==0,'Start was repeated or unlocked result')
        intent=read_storage(work)['start_intent']
        require(intent['schema']=='helix-orca-temperature-start/v1' and intent['request_id']==REQUEST['request_id'],'Unbound native Start intent')
        trigger(name,'ready',w,h);require(read_storage(work)['start_intent']==intent,'Duplicate ready reset Start')
        trigger(name,'printing',w,h);open_detail(name,w,h)
        require(value(name,'tc_choice_on')==0 and value(name,'tp_cancel_on')==1,'Printing unlocked results or omitted cancellation')
        a.ctl(name,'scroll','orcacal__request_status');a._screenshot(name,work,'printing.png')
        a._remove_container(name)
        a.run(a._container_args(name,work,w,h,layout,dpi),capture=True);q.wait_ready(name)
        open_detail(name,w,h)
        require(value(name,'tp_start_on')==0 and value(name,'tc_choice_on')==0,'Restart restored an unverified action')
        trigger(name,'printing',w,h);open_detail(name,w,h)
        require(value(name,'tp_cancel_on')==1 and read_storage(work)['start_intent']==intent,'Verified recovery lost cancellation or changed Start')
        trigger(name,'confirming',w,h);open_detail(name,w,h)
        require(value(name,'tc_choice_on')==0 and read_storage(work)['state']=='confirming','History lag became terminal or unlocked result')
        trigger(name,'complete',w,h);open_detail(name,w,h)
        require(value(name,'tc_choice_on')==1 and value(name,'tp_cancel_on')==0,'Confirmed success did not unlock result')
        a._assert_horizontal_fit(a.ctl(name,'geom','orcacal__temperature_content','8'),w)
        a.ctl(name,'scroll','orcacal__temperature_selector');a.ctl(name,'set_value','orcacal__temperature_selector','1')
        a._screenshot(name,work,'completed.png')
        q.tap(name,'orcacal__return_selection',w,h)
        s=read_storage(work)
        require(s['result']['value']==205 and s['result']['job_id']=='000001' and s['result']['completion_sha256']=='c'*64,'Result proof invalid')
        require(s['request']==REQUEST,'Original context changed')
        a._screenshot(name,work,'returning.png')
        a.ctl(name,'go_back');a.ctl(name,'wait_idle')
        a._assert_overlay(a.ctl(name,'current'),['orcacal__wizard'])
        a._assert_horizontal_fit(a.ctl(name,'geom','orcacal__chooser_content','8'),w)
        trigger(name,'ack',w,h);require(read_storage(work)['state']=='returned','Exact Orca acknowledgement not retained')
        trigger(name,'fresh',w,h)
        fresh=read_storage(work)
        require(fresh['request']['request_id']=='3'*32 and 'start_intent' not in fresh,'Terminal session did not retire')
        require(REQUEST['origin_id']+':'+REQUEST['request_id'] in fresh['tombstones'],'Retirement lost replay tombstone')
        trigger(name,'request',w,h)
        require(read_storage(work)['request']['request_id']=='3'*32,'Old request replay replaced the fresh session')
        return {'label':label,'viewport':f'{w}x{h}','dpi':dpi,'layout':layout,'result':'PASS','assertions':ASSERTIONS}
    finally:
        logs=a.run(['docker','logs',name],capture=True,check=False)
        (work/'runtime.log').write_text(logs.stdout+logs.stderr)
        a._remove_container(name)

def capture(output,only=None):
    before=hashes();runtime=q.beta9.verify_cache();q.beta9.configure_accepted_harness()
    if output.exists():raise ValueError('Refusing to replace native evidence')
    output.mkdir(parents=True)
    cache=q.generator.default_output().parent/'print-qualification';cache.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fixture-',dir=cache) as temp:
        plugins=fixture(Path(temp));fixture_hashes=q.file_hashes(plugins/'orcacal')
        rows=[]
        for entry in a.VIEWPORTS:
            if only and only!=entry[0]:continue
            rows.append(viewport(entry,output,plugins));print('PASS '+entry[0],flush=True)
        require(hashes()==before,'Candidate changed during capture')
        require(q.file_hashes(plugins/'orcacal')==fixture_hashes,'Fixture changed during capture')
        report={'schema':'helix-orca-temperature-print-native-evidence/v1','sources':before,'runtime':runtime,
          'container_network':'none','dependency_image_id':a.image_metadata()['id'],'fixture_files':fixture_hashes,
          'synthetic_inputs':['request','authorization','Moonraker clock and state','job identity','independent completion proof'],
          'physical_actions':0,'request':REQUEST,'lease':LEASE,'results':rows,
          'screenshots':{str(p.relative_to(output)):q.sha256(p) for p in sorted(output.rglob('*.png'))},
          'storage':{str(p.relative_to(output)):q.sha256(p) for p in sorted(output.glob('*/config/plugin-data/orcacal.json'))}}
        a.json_write(output/'report.json',report)

def verify(root):
    report=json.loads((root/'report.json').read_text())
    require(report['sources']==hashes(),'Native evidence sources differ')
    with tempfile.TemporaryDirectory(prefix='print-evidence-') as temp:
        expected=q.file_hashes(fixture(Path(temp))/'orcacal')
        require(report['fixture_files']==expected,'Generated native fixture differs')
    require(report['container_network']=='none' and report['physical_actions']==0,'Isolation evidence differs')
    require(report['request']==REQUEST and report['lease']==LEASE,'Fixture identities differ')
    require(report['runtime']['binary_sha256']==q.beta9.ARTIFACT_BINARY_SHA256,'Runtime differs')
    require([r['label'] for r in report['results']]==[r[0] for r in a.VIEWPORTS],'Complete eleven-target capture required')
    for row,entry in zip(report['results'],a.VIEWPORTS):
        label,w,h,layout,dpi=entry
        require(row=={'label':label,'viewport':f'{w}x{h}','dpi':dpi,'layout':layout,'result':'PASS','assertions':ASSERTIONS},'Matrix assertions differ')
    require(len(report['screenshots'])==55 and len(report['storage'])==11,'Incomplete frame/storage set')
    for group in ('screenshots','storage'):
        for path,digest in report[group].items():
            require((root/path).resolve().is_relative_to(root.resolve()) and q.sha256(root/path)==digest,'Evidence hash mismatch')
    print('PASS: source-bound complete beta.9 print readiness matrix')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('op',choices=['capture','verify']);p.add_argument('output',type=Path);p.add_argument('--viewport')
    x=p.parse_args()
    if x.op=='capture':capture(x.output,x.viewport)
    else:verify(x.output)
