#!/usr/bin/env python3
"""Founder-approved bounded metadata-only qualification relay; no listener.

Uses the existing Windows test bridge and live native review transport only.
Never writes native plugin storage or invents requests/prepared/status/results.
"""
from __future__ import annotations
import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.v1_contract import canonical,digest,validate_request
from integration.v1_runtime import atomic_json,read_json

SCHEMA='helix-orca-v1-windows-parameter-relay/v1'
TERMINAL=('blocked','failed','cancelled','delivered')
SOURCE_NAMES=('scripts/v1-windows-parameter-bridge.py','scripts/v1-runtime.py',
 'integration/v1_contract.py','integration/v1_runtime.py','integration/v1_transport.py',
 'integration/v1_routing.py','integration/v1_generation.py','integration/v1_parity.py','integration/v1_engine.py')


def require(value,code):
    if not value:raise ValueError(code)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quote(value):return "'"+str(value).replace("'","''")+"'"


def windows_path(value):
    require(isinstance(value,str) and re.fullmatch(r'[A-Za-z]:[\\/][^\x00-\x1f]*',value) is not None,
            'explicit_local_windows_path_required')
    return value


def powershell(args,op,session=None):
    fields={key:windows_path(getattr(args,key)) for key in ('windows_python','windows_source','windows_root','windows_context','windows_config')}
    declarations=';'.join('$'+key+'='+quote(value) for key,value in fields.items())
    script="$ErrorActionPreference='Stop';"+declarations+';'
    script+="$Bridge=Join-Path $windows_source 'scripts\\v1-windows-parameter-bridge.py';"
    script+="$BridgeSha=(Get-FileHash -LiteralPath $Bridge -Algorithm SHA256).Hash.ToLowerInvariant();if($BridgeSha-ne"+quote(args.bridge_sha256)+"){throw 'Public bridge source changed'};"
    script+="$ConfigSha=(Get-FileHash -LiteralPath $windows_config -Algorithm SHA256).Hash.ToLowerInvariant();"
    input_argument=''
    if session is not None:
        data=canonical({'v1_session':session});require(len(data)<=5000,'native_metadata_input_oversized')
        request=session['request'];require(re.fullmatch('[a-f0-9]{32}',request['request_id']) is not None,'invalid_native_request_id')
        encoded=base64.b64encode(data).decode('ascii')
        filename=request['request_id']+'-'+str(time.time_ns())+'.json'
        script+="$D=Join-Path $windows_root 'native-inputs';if(-not(Test-Path -LiteralPath $D)){New-Item -ItemType Directory -Path $D|Out-Null};"
        script+='$F=Join-Path $D '+quote(filename)+';'
        script+="$B=[Convert]::FromBase64String("+quote(encoded)+");$H=[IO.File]::Open($F,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$H.Write($B,0,$B.Length)}finally{$H.Dispose()};"
        input_argument=' --native-session $F'
    script+='$Out=@(& $windows_python -I -S $Bridge --op '+op+' --root $windows_root --context $windows_context --config $windows_config'+input_argument+');'
    script+="if($LASTEXITCODE-ne0){throw 'Windows parameter bridge refused metadata'};$Text=$Out-join [Environment]::NewLine;if($Text.Length-gt64000){throw 'Metadata result oversized'};"
    script+="if((Get-FileHash -LiteralPath $windows_config -Algorithm SHA256).Hash.ToLowerInvariant()-ne$ConfigSha-or(Get-FileHash -LiteralPath $Bridge -Algorithm SHA256).Hash.ToLowerInvariant()-ne$BridgeSha){throw 'Metadata source changed during operation'};"
    script+="Write-Output ('{\"bridge\":'+$Text+',\"config_file_sha256\":\"'+$ConfigSha+'\",\"bridge_file_sha256\":\"'+$BridgeSha+'\"}')"
    require(len(script)<=8192,'guarded_windows_command_oversized')
    return script


def independent_bindings(session,result):
    request=validate_request(session['request'])
    expected=digest(request)
    require(result.get('actual_offline_coordinator') is True and result.get('test_transport') is True,
            'actual_windows_coordinator_required')
    require(canonical(result.get('offer'))==canonical(session.get('offer'))
            and result.get('context_sha256')==request['context_sha256'],'windows_offer_or_context_binding_differs')
    for key in ('request','transport_request','coordinator_request'):
        require(canonical(result.get(key))==canonical(request),'independent_request_readback_differs')
    for key in ('request_sha256','transport_request_sha256','coordinator_request_sha256'):
        require(result.get(key)==expected,'independent_request_digest_differs')
    event={'request':request}
    if session.get('intent') is not None:event['intent']=session['intent']
    require(result.get('native_event_sha256')==digest(event) and result.get('transport_event_sha256')==digest(event),
            'independent_native_event_readback_differs')
    status=result['status']
    require(status.get('request_id')==request['request_id'] and status.get('origin_id')==request['origin_id'],
            'actual_status_identity_differs')
    require(result.get('actions_adapter_present') is False and result.get('physical_actions') is False,
            'physical_adapter_refused')
    return request


def native_bound(saved,request,status):
    return (isinstance(saved,dict) and canonical(saved.get('request'))==canonical(request)
            and saved.get('phase')==status['phase'] and saved.get('sequence')==status['sequence']
            and saved.get('prepared')==status.get('prepared')
            and saved.get('prepared_sha256')==status.get('prepared_sha256'))


def trial_completion(status,qualified,count,trials):
    if status['phase'] in TERMINAL:return 'terminal'
    if trials>0 and count+1==trials and qualified is True and status['phase']=='review':
        return 'final-qualified-review-no-start'
    return None


def run(args):
    require(30<=args.seconds<=900,'relay_deadline_must_be_30_to_900_seconds')
    require(re.fullmatch('[a-f0-9]{64}',args.bridge_sha256) is not None,'exact_bridge_digest_required')
    r=load('parameter_relay_native_review',ROOT/'scripts/v1-native-review.py')
    w=load('parameter_relay_windows_review',ROOT/'scripts/orca-windows-review.py')
    record,manifest=r.session(args.review_session or r.CURRENT)
    work=Path(record['work']);container=record['container'];local=work.parent/'coordinator/coordinator.json'
    initial=read_json(local);local_offer=initial.get('offer')
    require(initial.get('request') is None and initial.get('phase')=='requested' and isinstance(local_offer,dict),
            'local_review_coordinator_must_be_idle')
    require(local_offer['created_at']<=time.time()<local_offer['expires_at'],'local_review_offer_not_fresh')
    local_fingerprint=digest(local_offer)
    expected_sources={name:sha(ROOT/name) for name in SOURCE_NAMES}
    require(expected_sources['scripts/v1-windows-parameter-bridge.py']==args.bridge_sha256,'local_bridge_source_mismatch')
    deadline=time.monotonic()+args.seconds
    manifest_deadline=datetime.datetime.fromisoformat(manifest['deadline'].replace('Z','+00:00')).timestamp()
    deadline=min(deadline,time.monotonic()+manifest_deadline-time.time()-5)
    evidence=work/'windows-parameter-relay';evidence.mkdir(exist_ok=False)
    provenance=dict(schema=SCHEMA,run_id=record['run_id'],container=container,
        relay_sha256=sha(__file__),review_source_sha256=record['source_sha256'],
        windows_source_files=expected_sources,physical_actions=False,test_transport=True)
    atomic_json(evidence/'provenance.json',provenance)

    def active():
        current,data=r.session(args.review_session or r.CURRENT)
        require(current==record and data['state']=='running','owned_native_review_not_active')
        require(record['sources']==r.sources(),'live_review_source_changed')
        require(r.q.q.file_hashes(Path(record['fixture_root'])/'orcacal')==record['fixture_files'],'native_fixture_changed')
        resource=r.get_resource();inspected=resource.DockerCLI().inspect(container)
        require(resource.container_owned(data,inspected) and inspected['running'],'exact_owned_container_not_running')
        state=read_json(local)
        require(state.get('request') is None and digest(state.get('offer'))==local_fingerprint,
                'local_coordinator_must_not_consume_windows_requests')
        require(time.time()<local_offer['expires_at'],'local_review_offer_expired')
        return time.monotonic()<deadline

    def call(op,session=None):
        require(active() and deadline-time.monotonic()>65,'relay_deadline_before_windows_call')
        command=powershell(args,op,session)
        atomic_json(evidence/('command-'+str(time.time_ns())+'.json'),dict(op=op,sha256=hashlib.sha256(command.encode()).hexdigest(),characters=len(command)))
        response=w.invoke(command,'v1-parameter-relay-'+op)
        require(set(response)=={'bridge','config_file_sha256','bridge_file_sha256'}
                and response['bridge_file_sha256']==args.bridge_sha256
                and re.fullmatch('[a-f0-9]{64}',response['config_file_sha256']) is not None,
                'windows_configuration_or_bridge_binding_failed')
        result=response['bridge']
        require(len(canonical(response))<=65536 and result.get('source_files')==expected_sources,'windows_source_or_metadata_binding_failed')
        atomic_json(evidence/('windows-'+op+'-'+str(time.time_ns())+'.json'),response)
        return response

    def saved():
        path=work/'config/plugin-data/orcacal.json'
        return read_json(path).get('v1_session') if path.exists() else None

    def new_offer():
        response=call('offer');result=response['bridge'];offer=result['offer']
        require(result.get('op')=='offer' and result.get('actual_offline_coordinator') is True,'actual_windows_offer_required')
        require(active(),'review_ended_before_offer_delivery')
        r.deliver(container,'helix_orca_v1.context.v1',offer)
        atomic_json(evidence/('offered-'+offer['request_id']+'.json'),response)
        return offer

    offer=new_offer();last_input=None;pending=None;completed=set();count=0;last_readback=None;completion='bounded-stop'
    while active():
        current=saved()
        if pending and native_bound(current,pending['request'],pending['status']):
            status=pending['status'];request=pending['request']
            if digest(current)!=last_readback:
                path=work/'parameter-traces'/(request['request_id']+'.json')
                trace=read_json(path);trace.update(native_status_readback=current,native_status_readback_sha256=digest(current))
                atomic_json(path,trace);last_readback=digest(current)
            mode=trial_completion(status,pending['qualified'],count,args.trials)
            if mode:
                try:
                    geometry=r.q.ctl(container,'geom','orcacal__v1_job','0')
                    r.q.a._visible_widget_geometry(geometry,'orcacal__v1_job',800,480)
                except (ValueError,RuntimeError,KeyError):
                    time.sleep(.5);continue
                filename='windows-parameter-'+request['request_id']+'.png'
                r.q.ctl(container,'screenshot','/state/'+filename)
                trace=read_json(work/'parameter-traces'/(request['request_id']+'.json'))
                trace.update(native_status_readback=current,native_visible_geometry=geometry,
                             native_frame_sha256=sha(work/filename),parameter_trial_completion=mode)
                atomic_json(work/'parameter-traces'/(request['request_id']+'.json'),trace)
                completed.add(request['request_id']);count+=1;pending=None
                if args.trials and count>=args.trials:
                    completion=mode if mode=='final-qualified-review-no-start' else 'completed-terminal-trials'
                    break
                if deadline-time.monotonic()<=65:break
                offer=new_offer();last_input=None
        if isinstance(current,dict) and isinstance(current.get('request'),dict) and current['request']['request_id']==offer['request_id']:
            request=current['request'];validate_request(request)
            require(canonical(current.get('offer'))==canonical(offer),'native_saved_offer_differs_from_windows')
            require(current.get('result') is None and current.get('receipt') is None,'result_return_outside_parameter_relay')
            intent=current.get('intent')
            require(intent is None or (isinstance(intent,dict) and intent.get('action')=='cancel'),'confirm_or_start_relay_refused')
            # Native phase/sequence changes after delivery are readback, not new input.
            fingerprint=digest(dict(request=request,intent=intent))
            if fingerprint!=last_input and request['request_id'] not in completed:
                response=call('consume',current);result=response['bridge'];request=independent_bindings(current,result)
                require(active(),'review_ended_before_status_delivery')
                r.deliver(container,'helix_orca_v1.status.v1',result['status'])
                trace=dict(schema='helix-orca-v1-parameter-trace/v1',native_request=request,
                    transport_request=result['transport_request'],coordinator_request=result['coordinator_request'],
                    native_sha256=digest(request),transport_sha256=result['transport_request_sha256'],
                    coordinator_sha256=result['coordinator_request_sha256'],phase=result['status']['phase'],
                    message=result['status']['message'],prepared=result['status']['prepared'],
                    generator_dispatched=result['generator_dispatched'],artifact_generated=result['artifact_generated'],
                    actual_windows_source_files=result['source_files'],actual_windows_metadata_sha256=digest(response),
                    actual_windows_coordinator=True,actual_windows_transport='DirectoryEvents',
                    actual_windows_bridge_sha256=response['bridge_file_sha256'],
                    actual_windows_config_file_sha256=response['config_file_sha256'],
                    actual_windows_offer_sha256=digest(result['offer']),actual_windows_context_sha256=result['context_sha256'],
                    actual_windows_qualified=result['qualified'],qualified=result['qualified'],
                    actual_native_session_sha256=digest(current),actual_windows_event_sha256=result['transport_event_sha256'],
                    physical_adapter_enabled=False)
                atomic_json(work/'parameter-traces'/(request['request_id']+'.json'),trace)
                pending=result;last_input=fingerprint
        time.sleep(.5)
    result=dict(schema=SCHEMA,completed_trials=count,run_id=record['run_id'],physical_actions=False,
                new_listener=False,relay_stopped=True,result_completion=completion,retained_metadata=str(evidence))
    atomic_json(evidence/'result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('windows-python','windows-source','windows-root','windows-context','windows-config','bridge-sha256'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--review-session',type=Path)
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--trials',type=int,default=5)
    args=parser.parse_args();require(0<=args.trials<=10,'bounded_trial_count_required')
    try:print(json.dumps(run(args),sort_keys=True))
    except Exception as error:
        code=str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z_]{1,100}',str(error)) else type(error).__name__
        print(json.dumps(dict(schema=SCHEMA,relay_stopped=True,success=False,failure=code,physical_actions=False),sort_keys=True))
        return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
