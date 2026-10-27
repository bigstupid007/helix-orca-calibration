#!/usr/bin/env python3
"""Source-bound synthetic V1 beta.12 matrix. No hardware or generator parity claims."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time
import tempfile
from unittest.mock import patch
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.v1_runtime import Coordinator, atomic_json, read_json
from integration.v1_transport import DirectoryEvents
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
q=load('v1_native_q',ROOT/'scripts/temperature-communication-qualify.py')
a=q.accepted
beta12=load('v1_native_beta12',ROOT/'scripts/helix-beta12-qualify.py')
builder=load('v1_native_builder',ROOT/'scripts/v1-native-plugin.py')
contract=load('v1_native_contract',ROOT/'integration/v1_contract.py')
def configure_harness():
    """Bind the qualifier's accepted harness instance to the beta.12 cache."""
    beta12.configure_accepted_harness()
    root=beta12.cache_root()
    # temperature-communication-qualify and the beta.12 adapter load separate
    # module instances.  Bind this qualifier's instance explicitly so image
    # labels/manifests cannot retain the historical beta.4 provenance while
    # executing a beta.12 binary.
    a.HELIX_SOURCE_COMMIT=beta12.SOURCE_COMMIT
    a.DOCKERFILE=beta12.RUNTIME_DOCKERFILE
    a.IMAGE=beta12.RUNTIME_IMAGE
    a.binary_path=lambda:root/'binary/helix-screen'
    a.runtime_path=lambda:root/'runtime/helixscreen'
ASSERTIONS=['native-five-calibration-chooser','native-bounded-parameter-configuration','beta12-native-number-editor-and-precise-fallback','generate-only-request-no-start','unqualified-and-mismatched-preparation-locks-controls','separate-confirm-then-explicit-start','monotonic-status-and-exact-job','independent-completion-gates-evaluation','immutable-original-context-result','exact-originating-receipt-only','native-back-and-horizontal-fit','physical-adapter-absent','fresh-nonce-next-calibration-after-delivery-and-block','beta12-queued-owned-job-cancellation','logical-one-cell-home-tile-child-bounds-and-nonoverlap','verified-result-automatic-all-five-calibrations','automatic-dismiss-preserves-native-page-and-does-not-repeat','beta12-dialog-result-uses-original-return-handler','conservative-restart-and-lost-claim-manual-recovery','actual-coordinator-republishes-review-confirmed-complete-after-native-restart','same-job-progress-is-read-only-and-nullable','terminal-outcomes-hide-evaluation','application-pending-success-failure-retry-states','next-offer-display-is-distinct-from-immutable-job-context','beta12-native-v2-storage-to-coordinator-tick','native-compact-range-rejects-off-step-and-returns-exact-step']
FRAMES={'home.png','chooser.png','blocked.png','warning.png','application-failed.png','application-applied.png','cancel-confirm.png','cancel-kept.png','cancelled.png'}|{id+'-'+phase+'.png' for id in contract.CALIBRATIONS for phase in ('configure','review','confirmed','monitor','evaluate','returned')}
def hashes():
    paths=[ROOT/'scripts/v1-native-plugin.py',ROOT/'scripts/v1-native-qualify.py',ROOT/'integration/v1_contract.py',ROOT/'integration/v1_runtime.py',ROOT/'scripts/temperature-communication-plugin.py',ROOT/'scripts/temperature-communication-qualify.py',ROOT/'scripts/helix-beta12-qualify.py',ROOT/'scripts/helix-beta9-qualify.py',ROOT/'scripts/helix_dev.py',builder.ACCEPTED_TILE]+list((ROOT/'integration/v1-native').rglob('*'))
    return {str(p.relative_to(ROOT)):q.sha256(p) for p in sorted(paths) if p.is_file()}
def require(value,message):
    if not value:raise ValueError(message)

def current_context():
    value=dict(schema='helix-orca-v1-context/v2',origin_id='1'*32,
        runtime=dict(contract.ORCA_RUNTIME_V2,source_commit=contract.ORCA_SOURCE_V2,
                     executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2),
        nozzle_mm=.4,effective={'curr_bed_type':'Textured PEI Plate','extruder_type':'Direct Drive',
            'filament_flow_ratio':'1','nozzle_diameter':'0.4'},
        filament_slots=[dict(slot_number=1,preset_name='Synthetic PLA')],
        origin_filament=dict(slot_number=1,preset_name='Synthetic PLA',shared_slots=[1]))
    for role in ('printer','process','filament'):
        name='Synthetic PLA' if role=='filament' else 'Synthetic '+role
        value[role]={kind:dict(name=name,config={'fixture':kind}) for kind in ('saved','edited')}
    return contract.validate_context_v2(value)

def synthetic_build_qualification():
    """Schema-valid UI/transport fixture; explicitly not Windows qualification."""
    coverage=[dict(context=context_name,parameter_case=parameter_case,
                   case_sha256=hashlib.sha256((context_name+':'+parameter_case).encode()).hexdigest())
              for context_name in contract.V2_QUALIFICATION_CONTEXTS
              for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES]
    def route(calibration):
        return dict(qualified=True,
            route_id='stock-cli-recipe-v2' if calibration in ('temperature','flow_ratio_yolo') else 'native-engine-v2',
            case_count=len(coverage),cases_sha256=contract.digest(coverage),coverage=coverage,
            final_slice_path=list(contract.V2_FINAL_SLICE_PATH))
    return contract.validate_build_qualification_v2(dict(schema='helix-orca-v1-build-qualification/v2',
        source_commit=contract.ORCA_SOURCE_V2,runtime=contract.ORCA_RUNTIME_V2,
        platform='SYNTHETIC native-storage transport fixture; not Windows qualification',
        distribution=dict(archive_sha256=contract.ORCA_ARCHIVE_SHA256_V2,
                          executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2),
        upstream=dict(run_id=contract.ORCA_UPSTREAM_RUN_V2,overall_conclusion='failure',
            sole_failed_job='build_macos_arch (arm64) / Check Cache',
            exact_jobs={name:dict(job_id=job_id,conclusion='success')
                        for name,job_id in contract.ORCA_UPSTREAM_JOBS_V2.items()}),
        adapter=dict(sha256='4'*64),resources_sha256='5'*64,
        routes={calibration:route(calibration) for calibration in contract.CALIBRATIONS},
        evidence_sha256='6'*64,qualified=True))

def current_offer():
    context=current_context()
    value=dict(schema='helix-orca-v1-offer/v2',request_id='3'*32,
        origin_id=context['origin_id'],context_sha256=contract.digest(context),created_at=1000,expires_at=4600,
        nozzle_mm=context['nozzle_mm'],capabilities=[dict(id=key,available=True,reason='Synthetic UI transport fixture only') for key in contract.CALIBRATIONS],
        defaults=contract.default_parameters_v2(context),extruder_type=contract.context_extruder_type(context),
        origin_filament=context['origin_filament'],filament_slots=context['filament_slots'])
    for role in ('printer','process','filament'):value[role]=context[role]['saved']['name']
    return value

def current_storage_roundtrip(saved,work):
    """Feed beta.12's actual persisted V2 session through the real runtime tick."""
    require(saved.get('v2',{}).get('schema')=='helix-orca-v1-native-adapter/v2',
            'Native current request omitted its V2 adapter envelope')
    request=contract.validate_request_v2(saved.get('request'),now=1000)
    expected_offer=current_offer()
    require(saved.get('offer')==expected_offer,'Native persisted offer differs from the exact current context')
    build=synthetic_build_qualification();context=current_context()
    def generate(candidate,snapshot,directory,_config):
        require(candidate==request and snapshot==context,'Runtime tick changed the native request/context')
        artifact=directory/'synthetic-current-roundtrip.gcode';data=b'; SYNTHETIC NATIVE STORAGE ROUND TRIP ONLY\n';artifact.write_bytes(data)
        value={key:candidate[key] for key in ('request_id','origin_id','context_sha256','calibration','parameters')}
        value.update(schema='helix-orca-v1-prepared/v2',request_sha256=contract.digest(candidate),
            artifact=dict(name=artifact.name,size=len(data),sha256=hashlib.sha256(data).hexdigest()),
            generator=dict(source_commit=contract.ORCA_SOURCE_V2,route='stock-cli-recipe-v2',
                executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2,
                qualification_sha256=contract.digest(build),machine_sha256=contract.machine_sha256_v2(snapshot)),
            processing=dict(error_code=0,warnings=[],status='ready'))
        return contract.validate_prepared_v2(value,candidate)
    storage=work/'current-roundtrip-companion';channel=DirectoryEvents(work/'current-roundtrip-events')
    atomic_json(storage/'context.json',context);atomic_json(channel.directory/'native.json',saved)
    with patch('integration.v1_runtime.secrets.token_hex',return_value='3'*32):
        runtime=Coordinator(work/'current-roundtrip-runtime',generate,dict(build_qualification=build),
            [dict(id=key,available=True,reason='Synthetic UI transport fixture only') for key in contract.CALIBRATIONS],now=lambda:1000)
        spec=importlib.util.spec_from_file_location('v1_native_roundtrip_runtime',ROOT/'scripts/v1-runtime.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        cli.tick(runtime,storage,channel)
    status=read_json(channel.directory/'status.json')
    require(runtime.state['request']==request and status['schema']=='helix-orca-v1-status/v2'
            and status['phase']=='review' and status['qualification_sha256']==contract.digest(build),
            'Real runtime tick did not accept the exact beta.12 persisted V2 request')
    proof=dict(schema='helix-orca-v1-native-storage-roundtrip/v2',synthetic_only=True,physical_actions=0,
        native_session_sha256=contract.digest(saved),request_sha256=contract.digest(request),
        coordinator_request_sha256=contract.digest(runtime.state['request']),status_sha256=contract.digest(status),
        status_phase=status['phase'],qualification_fixture_sha256=contract.digest(build))
    atomic_json(work/'current-storage-roundtrip.json',proof)
    return proof
def recovery_fixtures():
    """Actual coordinator transitions with an explicitly synthetic parity/job boundary.

    Fixture generation and readback remain real; only parity qualification and the
    physical adapter are replaced. No physical adapter/network/engine is invoked.
    Fixed nonce and time make regenerated native fixture bytes source-verifiable.
    """
    result={}
    class SyntheticJobs:
        done=False
        def confirm(self,*_):pass
        def start(self,request,prepared,*_):
            return dict(job_id='synthetic-recovery-job',file_sha256=prepared['artifact']['sha256'],
                        request_id=request['request_id'],origin_id=request['origin_id'])
        def monitor(self,*_):return dict(elapsed_s=120,progress=.25)
        def observe(self,job):
            return dict(job_id=job['job_id'],file_sha256=job['file_sha256'],
                        print_state='complete' if self.done else 'printing',history_state='completed' if self.done else None,
                        history_job_id=job['job_id'] if self.done else None,history_file_sha256=job['file_sha256'] if self.done else None)
    context=dict(schema='helix-orca-v1-context/v1',origin_id='a'*32,
                 runtime=dict(version='2.5.0-dev',build='synthetic-ui-only'),
                 effective=dict(nozzle_temperature='217'),nozzle_mm=0.4)
    for role in ('printer','process','filament'):
        context[role]=dict(saved=dict(name='Synthetic '+role,config=dict(value='saved')),
                           edited=dict(name='Synthetic edited '+role,config=dict(value='edited')))
    def generate(request,context,directory,config):
        data=b'; SYNTHETIC UI RECOVERY FIXTURE ONLY\n'
        (directory/'synthetic-recovery.gcode').write_bytes(data)
        prepared={key:copy.deepcopy(request[key]) for key in ('request_id','origin_id','context_sha256','calibration','parameters')}
        prepared.update(schema='helix-orca-v1-prepared/v1',request_sha256=contract.digest(request),
            artifact=dict(name='synthetic-recovery.gcode',size=len(data),sha256=hashlib.sha256(data).hexdigest()),
            generator=dict(build='synthetic-only',route='synthetic-ui-recovery'),
            parity=dict(qualified=True,report_sha256='e'*64,reason='SYNTHETIC UI parity boundary only; not qualification'),not_applied=True)
        return prepared
    for serial,phase in enumerate(('review','confirmed','complete'),4097):
        jobs=SyntheticJobs()
        with tempfile.TemporaryDirectory() as root,patch('integration.v1_runtime.secrets.token_hex',return_value=f'{serial:032x}'),patch.object(Coordinator,'verify_parity'):
            runtime=Coordinator(root,generate,{},[dict(id=k,available=True,reason='Synthetic UI fixture only') for k in contract.CALIBRATIONS],now=lambda:1000,job_adapter=jobs)
            offer=runtime.offer(copy.deepcopy(context))
            request={key:offer[key] for key in ('request_id','origin_id','context_sha256','created_at','expires_at')}
            request.update(schema='helix-orca-v1-request/v1',calibration='temperature',parameters=copy.deepcopy(contract.DEFAULTS['temperature']),not_applied=True)
            runtime.request(request)
            intent=None
            for action in (() if phase=='review' else ('confirm',) if phase=='confirmed' else ('confirm','start')):
                intent=dict(schema='helix-orca-v1-intent/v1',request_id=request['request_id'],origin_id=request['origin_id'],
                            prepared_sha256=contract.digest(runtime.state['prepared']),action=action,
                            intent_id=request['request_id'][:24]+f'{1 if action=="confirm" else 2:08x}')
                runtime.intent(intent)
            if phase=='complete':
                runtime.poll_job();jobs.done=True;runtime.poll_job()
            before=runtime.status();require(before['phase']==phase,'Coordinator fixture did not reach '+phase)
            retained=dict(request=request,offer=offer,phase=phase,sequence=before['sequence'],message=before['message'],
                          prepared=before['prepared'],prepared_sha256=before['prepared_sha256'])
            if intent:retained['intent']=intent
            for key in ('job_id','completion_sha256','evaluation'):
                if before[key] is not None:retained[key]=before[key]
            marker=dict(copy.deepcopy(retained),phase='uncertain',recovery_required=True)
            marker.pop('evaluation',None)
            # Negative cases use the real reconciler, not a copied implementation.
            for key,value in (('request',dict(request,origin_id='9'*32)),('sequence',True),('sequence',before['sequence']+1),
                              ('prepared_sha256','9'*64),('job_id','unrelated'),('completion_sha256','9'*64),('recovery_required',False)):
                require(not runtime.reconcile_native(dict(copy.deepcopy(marker),**{key:value})),'Coordinator accepted unrelated recovery marker')
                require(runtime.status()==before,'Rejected marker changed authoritative status')
            require(runtime.reconcile_native(marker),'Coordinator rejected exact retained marker')
            fresh=runtime.status()
            require(fresh['sequence']==before['sequence']+1 and fresh['phase']==phase,'Coordinator failed durable republish')
            require(runtime.reconcile_native(marker) and runtime.status()==fresh,'Repeated marker advanced status again')
            require(runtime.reconcile_native(dict(marker,sequence=fresh['sequence'])),'Coordinator refused second actual restart')
            again=runtime.status()
            require(again['sequence']==fresh['sequence']+1,'Second restart was not durably republished')
            result[phase]=dict(retained=retained,same_sequence=before,fresh=fresh,again=again)
    return result

def fixture(root):
    target=root/'orcacal';builder.generate(target)
    defaults=json.dumps(contract.DEFAULTS,separators=(',',':'))
    recovery=json.dumps(recovery_fixtures(),separators=(',',':'),ensure_ascii=False)
    current=json.dumps(current_offer(),separators=(',',':'),ensure_ascii=False)
    hook='''
-- SYNTHETIC UI TEST FIXTURE ONLY; never included by the product builder.
local fixture_serial=v1_session and tonumber(v1_session.request.request_id:sub(-8),16) or 0
local fixture_signal=helix.subject.int('v1_fixture_signal',0)
local fixture_defaults=helix.json.decode([==[DEFAULTS]==])
local fixture_recovery=helix.json.decode([==[RECOVERY]==])
local fixture_current_offer=helix.json.decode([==[CURRENT_OFFER]==])
local function fixture_offer(changed)
 fixture_serial=fixture_serial+1
 local capabilities={}
 for id,_ in pairs(V1_CATALOG) do capabilities[#capabilities+1]={id=id,available=true,reason='Synthetic UI fixture only'} end
 v1_receive_offer('fixture',{schema='helix-orca-v1-offer/v1',request_id=string.format('%032x',fixture_serial),origin_id=string.rep('a',32),context_sha256=string.rep(changed and '8' or 'b',64),printer=changed and 'Synthetic next printer' or 'Synthetic printer',process='Synthetic process',filament='Synthetic PLA',nozzle_mm=0.4,capabilities=capabilities,defaults=fixture_defaults,created_at=1000,expires_at=4600})
end
local function fixture_status(phase)
 local r=v1_session.request
 local p={schema='helix-orca-v1-prepared/v1',request_id=r.request_id,origin_id=r.origin_id,context_sha256=r.context_sha256,request_sha256=string.rep('c',64),calibration=r.calibration,parameters=r.parameters,artifact={name='synthetic-calibration.gcode',size=12345,sha256=string.rep('d',64)},generator={build='synthetic-only',route='synthetic-ui'},parity={qualified=true,report_sha256=string.rep('e',64),reason='SYNTHETIC UI parity fixture · not generator qualification'},not_applied=true}
 local d={schema='helix-orca-v1-status/v1',request_id=r.request_id,origin_id=r.origin_id,sequence=v1_session.sequence+1,phase=phase,message='Synthetic UI fixture · '..phase,prepared=p,prepared_sha256=string.rep('f',64),monitor=nil}
 if phase=='printing' or phase=='verifying' or phase=='complete' then d.job_id='synthetic-job-'..r.request_id end
 if phase=='printing' then d.monitor={elapsed_s=120,progress=0.25} end
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
 elseif code==5 then
  local sequence=v1_session.sequence
  for _,monitor in ipairs({{elapsed_s=-1,progress=0.25},{elapsed_s=2678401,progress=0.25},{elapsed_s=120,progress=1.1},{elapsed_s=120,progress=0/0},{elapsed_s='120',progress=0.25},{elapsed_s=120,progress=0.25,unexpected=true}}) do
   local d=fixture_status('printing');d.monitor=monitor;v1_receive_status('fixture',d)
   if v1_session.sequence~=sequence then error('Malformed monitor accepted') end
  end
  local d=fixture_status('printing');d.monitor=nil;v1_receive_status('fixture',d)
  if v1_subjects.monitor:get()~='Progress unavailable' then error('Missing monitor invented progress') end
  d=fixture_status('printing');d.monitor={elapsed_s=120};v1_receive_status('fixture',d)
  if v1_subjects.monitor:get()~='Progress unavailable · 2m elapsed' then error('Elapsed-only monitor misrepresented') end
  d=fixture_status('printing');d.monitor={progress=0.25};v1_receive_status('fixture',d)
  if v1_subjects.monitor:get()~='25% · Elapsed unavailable' then error('Progress-only monitor misrepresented') end
  d=fixture_status('printing');d.monitor={elapsed_s=120,progress=1};v1_receive_status('fixture',d)
  if v1_subjects.evaluate_on:get()~=0 then error('100 percent progress unlocked evaluation') end
  v1_receive_status('fixture',fixture_status('printing'))
  if v1_subjects.monitor:get()~='25% · 2m elapsed' or v1_subjects.evaluate_on:get()~=0 then error('Monitor changed authority or formatting') end
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
 elseif code==21 or code==22 then
  local case=nil
  for _,candidate in pairs(fixture_recovery) do
   if candidate.retained.request.request_id==v1_session.request.request_id then case=candidate end
  end
  if not case then error('No actual coordinator recovery case') end
  local second=v1_session.recovery_required==true and v1_session.sequence==case.fresh.sequence
  if code==21 then v1_receive_status('fixture',second and case.fresh or case.same_sequence)
  else
   local sequence=v1_session.sequence
   local fresh=second and case.again or case.fresh
   -- Fresh sequence with unrelated retained proof must remain locked too.
   for _,key in ipairs({'prepared_sha256','job_id','completion_sha256'}) do
    if v1_session[key] then
     local wrong=helix.json.decode(helix.json.encode(fresh));wrong[key]='unrelated'
     v1_receive_status('fixture',wrong)
     if v1_session.sequence~=sequence then error('Mismatched recovery token accepted') end
    end
   end
   local changed=helix.json.decode(helix.json.encode(fresh));changed.prepared.generator.build='unrelated-build'
   v1_receive_status('fixture',changed)
   if v1_session.sequence~=sequence then error('Changed retained preparation accepted during recovery') end
   v1_receive_status('fixture',fresh)
  end
 elseif code==12 then v1_receive_status('fixture',fixture_status('complete'))
 elseif code==11 then v1_receive_status('fixture',fixture_status('cancelled'))
 elseif code==14 then v1_receive_status('fixture',fixture_status('failed'))
 elseif code==15 then fixture_offer(true)
 elseif code==30 then v1_receive_offer('fixture',fixture_current_offer)
 elseif code==31 then
  local d=fixture_status('complete')
  d.evaluation={setting='filament_retraction_length',range={start=0,['end']=1,step=0.0000001},unit='mm'}
  v1_receive_status('fixture',d)
 elseif code==32 then v1_completion_presentation.close()
 elseif code==16 then
  local adapter=v1_v2(v1_session)
  adapter.warning={schema='helix-orca-v1-native-warning/v2',request_id=v1_session.request.request_id,
   origin_id=v1_session.request.origin_id,prepared_sha256=v1_session.prepared_sha256,
   warning_codes={'1000C001'},title='Orca material warning',
   message='Bed temperature is above the filament vitrification temperature.'}
  v1_persist();v1_render();v1_open_warning()
 elseif code==17 or code==18 or code==19 then
  local states={[17]='failed',[18]='applying',[19]='applied'};local state=states[code]
  local adapter=v1_v2(v1_session)
  v1_receive_application_v2('fixture',{schema='helix-orca-v1-application/v2',request_id=v1_session.request.request_id,
   origin_id=v1_session.request.origin_id,sequence=(adapter.application_sequence or 0)+1,state=state,
   message=state=='failed' and 'Synthetic transaction refused; nothing applied.' or state=='applied' and 'Synthetic official preset transaction applied; unsaved.' or 'Synthetic official preset transaction in progress.',
   result_sha256=string.rep('2',64),result=v1_session.result,transaction_id=state=='applied' and 'synthetic-transaction' or '',
   dirty=state=='applied',unsaved=state=='applied',
   retry_authorization=state=='failed' and {schema='helix-orca-v1-application-retry/v2',request_id=v1_session.request.request_id,
    origin_id=v1_session.request.origin_id,result_sha256=string.rep('2',64),failed_application_sha256=string.rep('4',64),
    attempt=2,token=string.rep('5',32),authorized_at=1001} or nil})
  if code==19 then
   adapter.application.state='applied';adapter.application.dirty=true;adapter.application.unsaved=true
   v1_persist();v1_render()
  end
 elseif code==10 then
  local d=fixture_status('blocked');d.prepared.parity.qualified=false;d.prepared.artifact=nil;d.message='Synthetic blocked generator: native parity unavailable';v1_receive_status('fixture',d)
 end
end)
fixture_offer()
'''.replace('DEFAULTS',defaults).replace('RECOVERY',recovery).replace('CURRENT_OFFER',current)
    with (target/'main.lua').open('a') as f:f.write(hook)
    return root

def settings(path):
    with patch.object(q.beta9,'cache_root',beta12.cache_root):q.seed_settings(path)
    s=json.loads((path/'settings-test.json').read_text())
    s['plugins']['enabled']['orcacal']['version']='1.1.0-v1-beta12'
    home=s['printers']['default']['panel_widgets']['home']
    # New synthetic layout: a stamped landscape grid would make native
    # switch_to_grid reproject 1x1 to 1x2 on portrait. Adopt measured grid.
    home.pop('grid',None);home.pop('parked_grids',None)
    widgets=home['pages'][0]['widgets']
    widgets[:]=[w for w in widgets if w['id']=='orcacal__tile' or not w['enabled']]
    for widget in widgets:
        if widget['id']=='orcacal__tile':
            # Persisted spans are half-cell tracks, unlike manifest/home API
            # spans. Omit overrides so the actual manifest1x1 default is tested.
            widget.pop('colspan',None);widget.pop('rowspan',None)
            # Without a grid stamp, positioned coordinates are intentionally
            # rejected by the host's load guard. This fresh synthetic layout
            # must request native auto-placement, not pretend to know a grid.
            widget['col']=-1;widget['row']=-1
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
def edit_parameter(name,ident,key,new_value,w,h,work,native):
    """Exercise the operator-facing editor and verify its retained subject."""
    button='orcacal__v1_'+ident+'_'+key
    tap(name,button,w,h,work)
    if native:
        # edit_number queues the application keypad. Clear its existing value,
        # type the replacement through native keys, then use the keypad's Set.
        for _ in range(16):tap(name,'btn_backspace',w,h,work)
        for char in new_value:
            tap(name,'btn_dot' if char=='.' else 'btn_'+char,w,h,work)
        tap(name,'action_button',w,h,work)
    else:
        # Source-faithful unbounded Orca domains use the owned precise fallback.
        tap(name,'orcacal__v1_key_clear',w,h,work)
        for char in new_value:
            widget={'.':'dot',',':'comma'}.get(char,char)
            tap(name,'orcacal__v1_key_'+widget,w,h,work)
        tap(name,'orcacal__v1_key_set',w,h,work)
    require(value(name,ident+'_'+key+'_value')==new_value,
            'Operator editor did not retain '+ident+'.'+key)
def storage(work):
    path=work/'config/plugin-data/orcacal.json';deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        if path.exists():
            try:return json.loads(path.read_text())['v1_session']
            except (KeyError,json.JSONDecodeError):pass
        time.sleep(.05)
    raise ValueError('Native storage missing')
def stored_when(work,predicate,message):
    deadline=time.monotonic()+5
    while True:
        saved=storage(work)
        if predicate(saved):return saved
        if time.monotonic()>deadline:raise ValueError(message)
        time.sleep(.05)
def navigation(name):
    state=ctl(name,'current')
    return {key:state[key] for key in ('panel','overlays')}
def visible_widget(name,widget,w,h):
    geometry=a.ctl(name,'geom',widget,'0',check=False)
    if geometry is None:return False
    try:a._visible_widget_geometry(geometry,widget,w,h);return True
    except Exception:return False
def native_hidden(name,widget):
    state=ctl(name,'state',widget)
    # Native state may descend to a control. Assert the named section's flag,
    # not only its picker's flag, so heading/explanation cannot remain visible.
    return state.get('target',state)['flags']['hidden'] is True
def evaluation_hidden(name):
    return all(native_hidden(name,'orcacal__v1_'+key) for key in ('evaluation_heading','evaluation_note','evaluation','return'))
def compact_tile_proof(name,work,w,h):
    a._wait_visible_landing(name,w,h)
    home=ctl(name,'home','list')
    placed=[item for page in home['pages'] for item in page['widgets'] if item['id']=='orcacal__tile']
    geometry=ctl(name,'geom','orcacal__tile','8')
    a.json_write(work/'tile-geometry.json',dict(home=home,geometry=geometry))
    require(len(placed)==1 and placed[0]['w']==1 and placed[0]['h']==1,'Home tile is not logical1x1')
    assert_compact_bounds(geometry,w,h)
    require(value(name,'tile')=='Ready','Compact tile lacks initial status')
    a.json_write(work/'tile-geometry.json',dict(home=home,geometry=geometry))
def assert_compact_bounds(geometry,w,h):
    root=a._visible_widget_geometry(geometry,'orcacal__tile',w,h)
    children={}
    for child in ('orcacal__tile_icon','orcacal__tile_identity','orcacal__tile_status'):
        item=a._visible_widget_geometry(geometry,child,w,h);children[child]=item
        require(root['x']<=item['x'] and root['y']<=item['y'] and item['x']+item['w']<=root['x']+root['w']
                and item['y']+item['h']<=root['y']+root['h'],'Compact tile clips '+child)
    icon,identity,status=(children[k] for k in ('orcacal__tile_icon','orcacal__tile_identity','orcacal__tile_status'))
    require(icon['y']+icon['h']<=identity['y'] and identity['y']+identity['h']<=status['y'],'Compact tile children overlap')
def reopen_job(name,w,h,work,result=False):
    # Accepted helper only pops overlays; a preserved native panel is still
    # selected. Follow the accepted Temperature proof's deliberate Home action.
    q.back_to_home(name);ctl(name,'navigate','home');ctl(name,'wait_idle')
    require(not navigation(name)['overlays'],'Native Home navigation left overlays')
    tap(name,'orcacal__tile',w,h,work);tap(name,'orcacal__v1_resume',w,h,work)
    a._assert_overlay(navigation(name),['orcacal__wizard','orcacal__v1_result' if result else 'orcacal__v1_job'])
def restart_owned(name,work,snapshot=None):
    # Restart the exact ManagedRun-owned container, never create/remove another.
    a.run(['docker','stop','--time','2',name],capture=True)
    if snapshot is not None:
        path=work/'config/plugin-data/orcacal.json';data=json.loads(path.read_text());data['v1_session']=snapshot;a.json_write(path,data)
    a.run(['docker','start',name],capture=True);q.wait_ready(name)
def temperature_native_page_proof(name,w,h,work,page):
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_temperature',w,h,work);tap(name,'orcacal__v1_generate_temperature',w,h,work)
    signal(name,2);signal(name,3);tap(name,'orcacal__v1_confirm',w,h,work);signal(name,4)
    tap(name,'orcacal__v1_start',w,h,work);signal(name,5)
    if page=='print-status':ctl(name,'demo','print-status')
    else:q.back_to_home(name);ctl(name,'navigate','controls')
    ctl(name,'wait_idle');before=navigation(name)
    if page=='print-status':require(any('print_status' in str(item) for item in before['overlays']),'Actual Print Status is not open')
    else:require('controls' in str(before['panel']),'Actual Controls is not open')
    signal(name,6);after=navigation(name)
    # beta.12 dialogs use ModalStack rather than NavigationManager. Assert the
    # modal widget and the unchanged underlying page independently.
    require(after==before and visible_widget(name,'orcacal__v1_pick_use',w,h),'Queued result dialog did not preserve the native page and owned flow')
    tap(name,'orcacal__v1_pick_later',w,h,work);dismissed=before
    require(navigation(name)==dismissed and not visible_widget(name,'orcacal__v1_pick_use',w,h),'Dismiss did not restore underlying native page')
    signal(name,12);require(navigation(name)==dismissed and not visible_widget(name,'orcacal__v1_pick_use',w,h),'Duplicate reopened dismissed Temperature result')
    proof=dict(page=page,before=before,presented=after,dismissed=dismissed)
    a.json_write(work/('native-page-'+page+'-navigation.json'),proof)
    reopen_job(name,w,h,work);require(value(name,'evaluate_on')==1,'Pending Temperature result cannot be manually reopened')
    proof['manual_reopened']=navigation(name)
    ctl(name,'set_value','orcacal__v1_evaluation','1');tap(name,'orcacal__v1_return',w,h,work)
    if page=='controls':
        ctl(name,'go_back');ctl(name,'navigate','controls');ctl(name,'wait_idle');ack_before=navigation(name)
        signal(name,7)
        require(navigation(name)==ack_before,'Receipt covered an unrelated native page')
        proof['receipt_preserved_native_page']=ack_before
        reopen_job(name,w,h,work,result=True)
        require(value(name,'result_heading')=='Returned','Manual receipt recovery missing')
        a._visible_widget_geometry(ctl(name,'geom','orcacal__v1_result_heading','0'),'orcacal__v1_result_heading',w,h)
        tap(name,'orcacal__v1_result_done',w,h,work)
    else:signal(name,7)
    proof.update(manual_return=True)
    a.json_write(work/('native-page-'+page+'-navigation.json'),proof)
    return proof
def pending_temperature_recovery(name,w,h,work):
    cases=recovery_fixtures();evidence={}
    for phase,case in cases.items():
        restart_owned(name,work,case['retained'])
        require(not navigation(name)['overlays'] and value(name,'confirm_on')==0 and value(name,'start_on')==0
                and value(name,'evaluate_on')==0,'Restart restored an action or popup')
        marker=stored_when(work,lambda s:s.get('recovery_required') is True,'Restart recovery marker not retained')
        require(marker['phase']=='uncertain' and marker['sequence']==case['same_sequence']['sequence'],'Restart reset authoritative sequence')
        signal(name,21)
        require(storage(work)['phase']=='uncertain' and value(name,'confirm_on')==0 and value(name,'start_on')==0
                and value(name,'evaluate_on')==0,'Unchanged coordinator retransmission unlocked recovery')
        signal(name,22)
        saved=stored_when(work,lambda s:s.get('phase')==phase and not s.get('recovery_required'),'Fresh real coordinator status did not recover '+phase)
        expected={'review':'confirm_on','confirmed':'start_on','complete':'evaluate_on'}[phase]
        require(value(name,expected)==1 and not navigation(name)['overlays'],'Recovery controls or automatic suppression invalid')
        signal(name,21);signal(name,22)
        require(storage(work)['sequence']==saved['sequence'] and not navigation(name)['overlays'],'Recovery replay changed sequence/navigation')
        evidence[phase]=dict(before_sequence=case['same_sequence']['sequence'],after_sequence=saved['sequence'],
                             unchanged_rejected=True,exact_republish_accepted=True,replay_rejected=True)
    # A deferred automatic claim can be lost. The actual complete coordinator
    # case has no claim: native must add recovery-suppressed, then manual-only.
    complete=cases['complete'];saved=storage(work)
    require(saved['auto_presentation_claim']['reason']=='recovery-suppressed','Lost claim rearmed automatic presentation')
    claim=copy.deepcopy(saved['auto_presentation_claim'])
    restart_owned(name,work,saved);signal(name,21);signal(name,22)
    require(value(name,'evaluate_on')==1 and not navigation(name)['overlays'],'Retained claim failed manual-only recovery')
    require(storage(work)['auto_presentation_claim']==claim,'Restart replaced retained automatic claim')
    reopen_job(name,w,h,work);ctl(name,'set_value','orcacal__v1_evaluation','1');tap(name,'orcacal__v1_return',w,h,work);signal(name,7)
    returned=stored_when(work,lambda s:s.get('result') and s.get('receipt'),'Manual recovery return was not retained')
    require(returned['result']['context_sha256']==complete['retained']['request']['context_sha256'],'Manual recovery changed original context')
    evidence['manual_original_return']=True;evidence['lost_claim_suppressed']=True;evidence['retained_claim_suppressed']=True
    return evidence
def compact_range_result_proof(name,w,h,work):
    """Drive the real native range editor without increasing frame inventory."""
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_retraction',w,h,work)
    tap(name,'orcacal__v1_generate_retraction',w,h,work)
    signal(name,2);signal(name,3);tap(name,'orcacal__v1_confirm',w,h,work);signal(name,4)
    tap(name,'orcacal__v1_start',w,h,work);signal(name,5);signal(name,31)
    require(value(name,'evaluation_options_on')==0 and value(name,'evaluation_range_on')==1,
            'Compact evaluation range did not replace the dropdown')
    # The ordinary five-workflow matrix already proves beta.12's Later button.
    # Close any retained test-fixture modal deterministically, then exercise
    # every compact-range action through the real owned job and keypad.
    signal(name,32)
    tap(name,'orcacal__v1_evaluation_range',w,h,work)
    tap(name,'orcacal__v1_key_clear',w,h,work)
    for char in '0.84750005':
        tap(name,'orcacal__v1_key_'+({'.':'dot'}.get(char,char)),w,h,work)
    tap(name,'orcacal__v1_key_set',w,h,work)
    require('exact printed increment' in value(name,'keypad_error'),
            'Off-step compact result was accepted')
    tap(name,'orcacal__v1_key_clear',w,h,work)
    for char in '0.8475':
        tap(name,'orcacal__v1_key_'+({'.':'dot'}.get(char,char)),w,h,work)
    tap(name,'orcacal__v1_key_set',w,h,work)
    require(value(name,'evaluation_value')=='0.8475 mm','Exact compact result was not retained')
    tap(name,'orcacal__v1_return',w,h,work)
    saved=stored_when(work,lambda s:s.get('result',{}).get('value')==0.8475,
                      'Exact compact result was not committed')
    signal(name,7)
    tap(name,'orcacal__v1_result_done',w,h,work)
    return dict(start=0,end=1,step=0.0000001,count=10000001,rejected=0.84750005,
                returned=saved['result']['value'])
def drive(entry,name,work):
    label,w,h,layout,dpi=entry
    q.wait_ready(name)
    compact_tile_proof(name,work,w,h)
    presentation={'contexts':[]}
    a._screenshot(name,work,'home.png')
    tap(name,'orcacal__tile',w,h,work)
    a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_wizard_content','8'),w)
    a._screenshot(name,work,'chooser.png')
    for i,id in enumerate(contract.CALIBRATIONS):
        if i:
            q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
        tap(name,'orcacal__v1_choose_'+id,w,h,work)
        a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_v1_'+id+'_content','8'),w)
        edits={
            'temperature':('start','225',True),
            'pressure_advance_pattern':('end','0.09',False),
            'retraction':('end','2.1',False),
            'max_volumetric_speed':('end','21',False),
        }
        if id in edits:
            parameter,replacement,native=edits[id]
            edit_parameter(name,id,parameter,replacement,w,h,work,native)
        # Capture the exact values that the following Generate action submits.
        # Taking this frame before the scripted edit made an otherwise-correct
        # workflow look like several unrelated jobs to a cold reviewer.
        a._screenshot(name,work,id+'-configure.png')
        tap(name,'orcacal__v1_generate_'+id,w,h,work)
        require(value(name,'confirm_on')==0 and value(name,'start_on')==0,'Generate unlocked execution')
        signal(name,2);signal(name,9);signal(name,3)
        require(value(name,'confirm_on')==1 and value(name,'start_on')==0,'Review controls invalid')
        if i==0:
            signal(name,16);require(value(name,'confirm_on')==0 and value(name,'warning_on')==1,'Warning did not lock confirmation')
            a._visible_widget_geometry(ctl(name,'geom','orcacal__v1_warning_continue','0'),'orcacal__v1_warning_continue',w,h)
            a._screenshot(name,work,'warning.png')
            tap(name,'orcacal__v1_warning_continue',w,h,work)
            require(value(name,'confirm_on')==1 and storage(work)['v2']['warning']['decision']['action']=='continue','Warning continuation was not retained')
        a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_v1_job_content','8'),w)
        ctl(name,'scroll','orcacal__v1_confirm');a._screenshot(name,work,id+'-review.png')
        tap(name,'orcacal__v1_confirm',w,h,work)
        require(value(name,'start_on')==0,'Confirm started printing')
        signal(name,4);require(value(name,'start_on')==1,'Confirmed job lacks deliberate Start')
        ctl(name,'scroll','orcacal__v1_start')
        a._visible_widget_geometry(ctl(name,'geom','orcacal__v1_start','0'),'orcacal__v1_start',w,h)
        a._screenshot(name,work,id+'-confirmed.png')
        tap(name,'orcacal__v1_start',w,h,work);require(value(name,'start_on')==0,'Start repeated')
        signal(name,5);require(value(name,'evaluate_on')==0,'Printing unlocked evaluation')
        require(value(name,'monitor')=='25% · 2m elapsed','Same-job monitor not rendered')
        ctl(name,'scroll','orcacal__v1_job_monitor');a._screenshot(name,work,id+'-monitor.png')
        if id=='temperature':q.back_to_home(name)
        before=navigation(name)
        signal(name,6);require(value(name,'evaluate_on')==1,'Successful exact-job completion did not unlock evaluation')
        after=navigation(name)
        require(after==before and visible_widget(name,'orcacal__v1_pick_use',w,h),'Automatic result dialog did not preserve native navigation')
        claim=stored_when(work,lambda s:s.get('phase')=='complete' and s.get('auto_presentation_claim'),'Automatic result claim not retained')['auto_presentation_claim']
        require(claim['reason']=='beta12-queued-automatic-attempt' and claim['calibration']==id and claim['job_id']==storage(work)['job_id'] and claim['prepared_sha256']=='f'*64
                and claim['completion_sha256']=='1'*64,'Automatic attempt lost exact prepared/job/completion identity')
        selector='orcacal__v1_pick';return_button='orcacal__v1_pick_use';returned='orcacal__v1_returned_status'
        ctl(name,'scroll',selector)
        a._visible_widget_geometry(ctl(name,'geom',selector,'0'),selector,w,h)
        # Select first, then capture and return that same immutable option so
        # evaluation and result evidence visibly describe one exact job.
        ctl(name,'set_value',selector,'1')
        a._screenshot(name,work,id+'-evaluate.png')
        signal(name,12);require(navigation(name)==after and visible_widget(name,'orcacal__v1_pick_use',w,h),'Duplicate completion changed presentation')
        # Every queued picker shares the same immutable result/application path.
        tap(name,return_button,w,h,work);require(value(name,'evaluate_on')==0,'Returned result editable')
        a._assert_overlay(navigation(name),['orcacal__v1_result'])
        require(value(name,'result_heading')=='Ready for Orca' and 'APPLICATION PENDING' in value(name,'returned'),'Result did not enter pending application')
        a._visible_widget_geometry(ctl(name,'geom','orcacal__v1_result_heading','0'),'orcacal__v1_result_heading',w,h)
        a._assert_horizontal_fit(ctl(name,'geom','orcacal__v1_result_content','8'),w)
        signal(name,8);signal(name,7)
        require(value(name,'result_heading')=='Returned' and 'NOT APPLIED' in value(name,'returned'),'Exact receipt not shown')
        if i==0:
            signal(name,17);require(value(name,'retry_on')==1 and value(name,'result_heading')=='Application needs attention','Application failure not shown')
            a._screenshot(name,work,'application-failed.png')
            tap(name,'orcacal__v1_application_retry',w,h,work)
            require(value(name,'retry_on')==0 and storage(work)['v2']['application_retry']['schema']=='helix-orca-v1-application-retry/v2','Application retry was not retained')
            signal(name,18);signal(name,19)
            require(value(name,'result_heading')=='Applied in Orca' and 'APPLIED · UNSAVED' in value(name,'returned'),'Application success was not shown as unsaved')
            a._screenshot(name,work,'application-applied.png')
        a._screenshot(name,work,id+'-returned.png')
        tap(name,'orcacal__v1_result_done',w,h,work)
        require(not navigation(name)['overlays'],'Done did not dismiss owned completion view')
        presentation['contexts'].append(dict(calibration=id,before=before,presented=after))
        deadline=time.monotonic()+5
        while True:
            saved=storage(work)
            if saved.get('receipt') and saved['request']['calibration']==id:break
            if time.monotonic()>deadline:raise ValueError('Receipt not durable')
            time.sleep(.1)
        contract.validate_request(saved['request'],now=1001)
        require(saved['result']['value']==saved['evaluation']['options'][1],'Wrong native selection returned')
        require(saved['result']['context_sha256']=='b'*64,'Original context changed')
    signal(name,15)
    require(value(name,'offer_printer').startswith('Synthetic next printer') and value(name,'printer').startswith('Synthetic printer'),'Next offer mislabeled immutable job context')
    q.back_to_home(name);tap(name,'orcacal__tile',w,h,work);tap(name,'orcacal__v1_choose_temperature',w,h,work)
    require(storage(work)['result']['context_sha256']=='b'*64,'Next configuration replaced original returned result')
    reopen_job(name,w,h,work,result=True)
    require(value(name,'result_heading')=='Returned' and value(name,'printer').startswith('Synthetic printer'),'Retained result lost original context')
    tap(name,'orcacal__v1_result_done',w,h,work)
    presentation['distinct_offer_original_context']=True
    presentation['pending_temperature_recovery']=pending_temperature_recovery(name,w,h,work)
    presentation['native_temperature_pages']=[temperature_native_page_proof(name,w,h,work,page) for page in ('print-status','controls')]
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_temperature',w,h,work);tap(name,'orcacal__v1_generate_temperature',w,h,work)
    signal(name,2);signal(name,3);tap(name,'orcacal__v1_confirm',w,h,work);signal(name,4)
    tap(name,'orcacal__v1_start',w,h,work);signal(name,5)
    tap(name,'orcacal__v1_cancel',w,h,work)
    require(storage(work)['intent']['action']=='start','Opening cancellation dispatched an intent')
    a._visible_widget_geometry(ctl(name,'geom','btn_primary','0'),'btn_primary',w,h)
    a._screenshot(name,work,'cancel-confirm.png')
    tap(name,'btn_secondary',w,h,work)
    require(storage(work)['intent']['action']=='start','Keep printing dispatched cancellation')
    a._screenshot(name,work,'cancel-kept.png')
    tap(name,'orcacal__v1_cancel',w,h,work);tap(name,'btn_primary',w,h,work)
    deadline=time.monotonic()+5
    while storage(work)['intent']['action']!='cancel':
        if time.monotonic()>deadline:raise ValueError('Confirmed cancellation was not durable')
        time.sleep(.05)
    signal(name,11);require(value(name,'evaluate_on')==0,'Cancelled print unlocked evaluation')
    require(evaluation_hidden(name),'Cancelled print still shows evaluation')
    cancelled=navigation(name);signal(name,12);require(navigation(name)==cancelled and not storage(work).get('auto_presentation_claim'),'Cancelled print presented a result')
    a._screenshot(name,work,'cancelled.png')
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_temperature',w,h,work);tap(name,'orcacal__v1_generate_temperature',w,h,work);signal(name,10)
    require(value(name,'confirm_on')==0 and value(name,'start_on')==0,'Blocked generation unlocked execution')
    a._screenshot(name,work,'blocked.png')

    blocked_request=storage(work)['request']['request_id']
    q.back_to_home(name);signal(name,1);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_flow_ratio_yolo',w,h,work);tap(name,'orcacal__v1_generate_flow_ratio_yolo',w,h,work)
    signal(name,2)
    require(value(name,'phase')=='Preparing print','Fresh nonce did not retire blocked work')
    deadline=time.monotonic()+5
    while True:
        next_request=storage(work)['request']
        if next_request['request_id']!=blocked_request:break
        if time.monotonic()>deadline:raise ValueError('Fresh request was not durable')
        time.sleep(.1)
    require(next_request['calibration']=='flow_ratio_yolo' and next_request['context_sha256']=='b'*64,'Next calibration retargeted context')
    signal(name,14)
    stored_when(work,lambda s:s.get('phase')=='failed','Failed calibration was not retained')
    require(value(name,'evaluate_on')==0 and evaluation_hidden(name),'Failed calibration still shows evaluation')
    presentation['compact_range_result']=compact_range_result_proof(name,w,h,work)
    q.back_to_home(name);signal(name,30);tap(name,'orcacal__tile',w,h,work)
    tap(name,'orcacal__v1_choose_temperature',w,h,work);tap(name,'orcacal__v1_generate_temperature',w,h,work)
    current_saved=stored_when(work,lambda s:s.get('request',{}).get('schema')=='helix-orca-v1-request/v2',
                              'Native beta.12 did not persist the current V2 request')
    presentation['current_storage_roundtrip']=current_storage_roundtrip(current_saved,work)
    logs=a.run(['docker','logs',name],capture=True,check=False)
    (work/'runtime.log').write_text(logs.stdout+logs.stderr)
    require('[plugin orcacal]' not in logs.stdout+logs.stderr,'Native runtime error')
    q.back_to_home(name)
    a.json_write(work/'presentation.json',presentation)
    return {'label':label,'viewport':f'{w}x{h}','layout':layout,'dpi':dpi,'result':'PASS','calibrations':list(contract.CALIBRATIONS),'assertions':ASSERTIONS}

def selected_viewports(only=None):
    labels={entry[0] for entry in a.VIEWPORTS}
    require(only is None or only in labels,'Unknown native viewport: '+str(only))
    return [entry for entry in a.VIEWPORTS if only is None or entry[0]==only]

def capture(output,only=None):
    before=hashes();runtime=beta12.verify_cache();configure_harness()
    selected=selected_viewports(only)
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
    for entry in selected:
        label,w,h,layout,dpi=entry
        adapter=NativeDocker()
        a.PLUGIN_ROOT=plugins
        image_id=a.image_metadata()['id']
        commit=a.run(['git','rev-parse','HEAD'],capture=True,cwd=ROOT).stdout.strip()
        with resource.ManagedRun(app='helix-orca-v1-native',repo=str(ROOT),issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',commit=commit,dirty_input=contract.digest(before),paths=[str(output.parent),str(cache),str(ROOT)],reserve=5*1024**3,peak=512*1024**2,margin=512*1024**2,timeout=360,adapter=adapter) as run:
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
    report={'schema':'helix-orca-v1-native-evidence/v2','sources':before,'runtime':runtime,'container_network':'none','physical_actions':0,'synthetic_only':True,'synthetic_inputs':['context','generator availability','prepared artifact','build qualification','processor warning','print status','completion proof','result application','receipt'],'fixture_files':fixture_hashes,'results':rows,'managed_runs':runs,'screenshots':{str(p.relative_to(output)):q.sha256(p) for p in sorted(output.rglob('*.png'))}}
    a.json_write(output/'report.json',report)

def verify(output):
    r=json.loads((output/'report.json').read_text())
    require(r['sources']==hashes(),'Sources differ');require(r['runtime']==beta12.verify_cache(),'Runtime differs')
    require(r['synthetic_only'] and r['physical_actions']==0 and r['container_network']=='none','Isolation differs')
    require([v['label'] for v in r['results']]==[v[0] for v in a.VIEWPORTS],'All eleven viewports required')
    for row in r['results']:require(row['assertions']==ASSERTIONS and row['calibrations']==list(contract.CALIBRATIONS) and row['result']=='PASS','Incomplete workflow proof')
    require(set(r['screenshots'])=={label+'/'+frame for label,*_ in a.VIEWPORTS for frame in FRAMES},'Incomplete or unexpected screenshots')
    for name,digest in r['screenshots'].items():require(q.sha256(output/name)==digest,'Screenshot differs')
    for item in r['managed_runs']:
        manifest=json.loads(Path(item['manifest']).read_text());require(manifest['state']=='complete' and manifest['verification']['runtime_clear'],'Managed run incomplete')
    print('PASS: source-bound synthetic V1 beta.12 eleven-target/five-calibration matrix')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('op',choices=['capture','verify','_drive']);p.add_argument('output',type=Path,nargs='?');p.add_argument('--viewport');p.add_argument('--container');x=p.parse_args()
    output=x.output or q.state_root().parent/'v1-native'/time.strftime('%Y%m%d-%H%M%S')
    if x.op=='capture':capture(output,x.viewport)
    elif x.op=='verify':verify(output)
    else:
        configure_harness();entry=next(e for e in a.VIEWPORTS if e[0]==x.viewport)
        row=drive(entry,x.container,output);a.json_write(output/'row.json',row)
