#!/usr/bin/env python3
"""Verify focused native parameter proof; retain the old matrix as historical only."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.v1_contract import CALIBRATIONS,digest,validate_request,validate_prepared
from integration.v1_runtime import read_json
spec=importlib.util.spec_from_file_location('parameter_review_evidence',ROOT/'scripts/v1-native-review.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
SCHEMA='helix-orca-v1-parameter-evidence/v1'
HISTORICAL_SHA='178dc0551495db1322f2d64ab37429eff02e91ad8240ec5a1902d27156b813c5'
def require(value,message):
    if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def safe(root,name):
    item=Path(name);path=root/item
    require(not item.is_absolute() and '..' not in item.parts and root.resolve() in path.resolve().parents and not path.is_symlink() and path.is_file(),'Missing/unsafe evidence file')
    return path
def historical():
    root=ROOT/'docs/evidence/issue-14/native'
    require(sha(root/'report.json')==HISTORICAL_SHA,'Historical complete matrix changed')
    report=read_json(root/'report.json')
    require(len(report['screenshots'])==396,'Historical frame inventory changed')
    for name,value in report['screenshots'].items():require(sha(safe(root,name))==value,'Historical frame changed')
    return dict(report_sha256=HISTORICAL_SHA,frames=396,scope='Historical synthetic matrix; does not qualify current parameter controls')
def operator(root,report,traces,private_frames=False):
    require(report['schema']=='helix-orca-v1-windows-parameter-operator/v1' and report['passed'] is True and report['viewport']=='800x480','Focused operator proof did not pass')
    require(report['driver_sha256']==sha(ROOT/'scripts/v1-windows-parameter-operator.cjs'),'Operator driver changed')
    for key in ('physical_actions','profile_writeback','prepared_fixtures'):require(report[key] is False,'Proof crossed safeguard')
    require(report['page_errors']==[],'Browser error in operator proof')
    require(report['browser_version']=='140.0.7339.186','Pinned operator browser differs')
    require({p['kind'] for p in report['proofs']}==set(CALIBRATIONS) and len(report['proofs'])==5,'Incomplete calibration proof')
    require(len({p['request_id'] for p in report['proofs']})==5,'Reused request nonce')
    require(set(traces)==set(CALIBRATIONS),'Incomplete exact-request trace set')
    for proof in report['proofs']:
        trace=traces[proof['kind']];request=trace['native_request'];validate_request(request,now=request['created_at'])
        require(proof['request_id']==request['request_id'],'Operator request nonce differs')
        for key in ('native_request','transport_request','coordinator_request','native_sha256','transport_sha256','coordinator_sha256'):
            require(proof[key]==trace[key],'Operator proof differs from retained trace: '+key)
        require(request['calibration']==proof['kind'] and request['parameters']==proof['parameters']==report['values'][proof['kind']],'Selected values differ')
        require(trace['transport_request']==request==trace['coordinator_request'],'Native/transport/coordinator request differs')
        require(trace['native_sha256']==trace['transport_sha256']==trace['coordinator_sha256']==proof['request_sha256']==digest(request),'Independent request digests differ')
        require(trace['physical_adapter_enabled'] is False,'Physical adapter enabled')
        require(trace['actual_windows_coordinator'] is True and trace['actual_windows_transport']=='DirectoryEvents','Actual Windows coordinator missing')
        require(trace['actual_windows_context_sha256']==request['context_sha256']=='3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c','Windows original context differs')
        names=('scripts/v1-windows-parameter-bridge.py','scripts/v1-runtime.py','integration/v1_contract.py','integration/v1_runtime.py','integration/v1_transport.py','integration/v1_routing.py','integration/v1_generation.py','integration/v1_parity.py','integration/v1_engine.py')
        require(trace['actual_windows_source_files']=={name:sha(ROOT/name) for name in names},'Windows source closure differs')
        require(trace['actual_windows_bridge_sha256']==sha(ROOT/names[0]),'Windows bridge differs')
        require(trace['actual_windows_event_sha256']==digest(dict(request=request)),'Windows event differs')
        for key in ('actual_windows_metadata_sha256','actual_windows_config_file_sha256','actual_windows_offer_sha256','actual_native_session_sha256','native_status_readback_sha256','native_frame_sha256'):
            require(re.fullmatch('[a-f0-9]{64}',trace[key]) is not None,'Windows provenance missing')
        for key in proof:
            if key in trace:require(proof[key]==trace[key],'Operator/retained trace differs: '+key)
        flow=request['calibration']=='flow_ratio_yolo'
        expected='review' if flow else 'blocked'
        require(trace['phase']==proof['phase']==expected and trace['message']==proof['message'] and bool(trace['message']),'Actual preparation status differs')
        require(trace['generator_dispatched'] is flow and trace['artifact_generated'] is flow and trace['actual_windows_qualified'] is flow and trace['qualified'] is flow,'Actual generation/qualification disposition differs')
        require(trace['parameter_trial_completion']==('final-qualified-review-no-start' if flow else 'terminal'),'Parameter trial did not complete')
        if flow:
            validate_prepared(trace['prepared'],request)
            require(trace['prepared']['parity']['qualified'] is True,'Flow native parity did not pass')
        else:require(trace['prepared'] is None,'Unavailable generator retained a prepared object')
    require(len({t['actual_windows_config_file_sha256'] for t in traces.values()})==1,'Windows configuration changed between trials')
    require(len({t['actual_windows_offer_sha256'] for t in traces.values()})==5,'Windows offer identity reused')
    require(report['values']['temperature']==dict(start=235,end=195,step=5,scale=False),'Temperature control changes missing')
    require(report['values']['flow_ratio_yolo']=={'pass':2},'Changed YOLO selection missing')
    expected_values=dict(pressure_advance_pattern=dict(start=.01,end=.09,step=.01),retraction=dict(start=.2,end=2.2,step=.2),max_volumetric_speed=dict(start=6,end=21,step=.75))
    for kind,value in expected_values.items():require(report['values'][kind]==value,'Changed numeric values missing')
    actions=report['actions']
    require(all(a['type'] in ('browser-native-tap','browser-native-drag','browser-native-navigation','browser-native-navigation-retry','invalid-input-preserved','pa-defaults') for a in actions),'Unknown operator action')
    require(not any(a.get('widget') in ('orcacal__v1_confirm','orcacal__v1_start','orcacal__v1_cancel') for a in actions),'Parameter proof entered Confirm/Start/Cancel')
    retries=[a for a in actions if a['type']=='browser-native-navigation-retry']
    require(len(retries)<=5 and len({a.get('reason') for a in retries})==len(retries) and all(a.get('reason') in {kind+' setup remained closed after first stabilized tap' for kind in CALIBRATIONS} for a in retries),'Unbounded/unknown navigation retry')
    require(type(report.get('read_retries')) is list and len(report['read_retries'])<=12,'Read retry provenance missing or excessive')
    for retry in report['read_retries']:
        route=retry.get('route','')
        require(type(retry.get('attempt')) is int and 1<=retry['attempt']<=3 and type(retry.get('error')) is str and 0<len(retry['error'])<=300,'Malformed read retry')
        require(route in ('/health','/api/status','/api/parameter-state') or re.fullmatch(r'/api/(geometry|subject)\?name=orcacal__[a-z0-9_]+',route) is not None,'Read retry crossed bounded API')

    require(any(a['type']=='invalid-input-preserved' and a.get('field')=='retraction.start' and a.get('attempt')=='99' and str(a.get('prior'))=='0' and bool(a.get('error')) for a in actions),'Invalid-input operator proof missing')
    defaults={a['selected']:a['values'] for a in actions if a['type']=='pa-defaults'}
    require(defaults==dict(direct_drive=dict(start=0,end=.08,step=.005),bowden=dict(start=0,end=1,step=.05)),'PA defaults operator proof missing')
    for widget in ('orcacal__v1_temperature_scale','orcacal__v1_flow_perfectionist'):
        require(any(a.get('widget')==widget and a['type']=='browser-native-tap' for a in actions),'Selection control not operated')
    for kind in CALIBRATIONS:
        required=['pass'] if kind=='flow_ratio_yolo' else ['start','end'] if kind=='temperature' else ['start','end','step']
        if kind=='flow_ratio_yolo':required=[]
        for key in required:require(any(a.get('widget')==f'orcacal__v1_{kind}_{key}' and a['type']=='browser-native-tap' for a in actions),'Parameter control not operated')
    screenshots={p['name']:p['sha256'] for p in report['screenshots']}
    expected={kind+'-configured.png' for kind in CALIBRATIONS}|{kind+('-review.png' if kind=='flow_ratio_yolo' else '-blocked.png') for kind in CALIBRATIONS}
    expected.update(('pressure_advance_pattern-direct-defaults.png','pressure_advance_pattern-bowden-defaults.png','retraction-start-invalid.png'))
    expected.add('00-chooser.png')
    require(set(screenshots)==expected and len(report['screenshots'])==14,'Missing/duplicate/unexpected focused native capture')
    for name,value in screenshots.items():
        require(re.fullmatch(r'[a-z0-9_-]+\.png',name) is not None and re.fullmatch('[a-f0-9]{64}',value) is not None,'Invalid private-frame provenance')
        if private_frames:require(sha(safe(root,name))==value,'Focused private browser frame changed')
def check_lifecycle(value):
    require(value['state']=='complete' and value['runtime_clear'] is True and type(value['exit_code']) is int and value['exit_code']==0 and value['errors']==[],'Managed runtime was not cleared')
    limits=value['limits']
    require(set(limits)=={'reserve','peak','margin','timeout','grace','log_bytes'} and all(type(v) is int for v in limits.values()),'Malformed managed bounds')
    require(limits['reserve']==5*1024**3 and limits['peak']==2*1024**3 and limits['margin']==512*1024**2 and 60<=limits['timeout']<=900 and limits['grace']==1 and limits['log_bytes']==1024**2,'Managed bounds differ')
def verify(root):
    report=read_json(root/'report.json')
    require(report['schema']==SCHEMA and report['sources']==r.sources(),'Focused proof sources differ')
    require(report['verifier_sha256']==sha(__file__),'Focused verifier changed')
    require(report['historical']==historical(),'Historical scope differs')
    check_lifecycle(report['lifecycle'])
    require(report['operator_sha256']==sha(root/'operator.json'),'Operator record changed')
    require(report['privacy']=='Windows/native frames and raw metadata retained privately; exact hashes verified at promotion','Private evidence boundary differs')
    require(report['relay_sha256']==sha(ROOT/'scripts/v1-windows-parameter-relay.py'),'Relay changed')
    require(report['relay_result']['completed_trials']==5 and report['relay_result']['result_completion']=='final-qualified-review-no-start' and report['relay_result']['physical_actions'] is False,'Windows relay did not finish all five trials safely')
    proof=read_json(root/'operator.json')
    require(proof['health']==dict(status='ok',synthetic_only=True,run_id=report['lifecycle']['run_id']),'Operator/managed health binding differs')
    operator(root,proof,report['traces'])
    flow=report['traces']['flow_ratio_yolo'];summary=read_json(root/'windows-parity.json')
    require(sha(root/'windows-parity.json')==report['windows_parity_sha256'],'Windows parity summary changed')
    require(summary['qualified'] is True and summary['policy']=='exact-executable-v1' and summary['disposition']=='exact_executable_and_invariants_match','Strict Windows parity failed')
    require(summary['request_sha256']==flow['native_sha256'] and summary['prepared_sha256']==digest(flow['prepared']) and summary['report_sha256']==flow['prepared']['parity']['report_sha256'],'Native-selected request parity binding differs')
    require(summary['candidate']['sha256']==flow['prepared']['artifact']['sha256'] and summary['parameters']=={'pass':2} and summary['unclassified_setting_difference_count']==0,'Generated artifact or parity policy differs')
    print('PASS: focused native800x480 parameter/actual-coordinator proof;396 earlier frames verified as historical only')
def build(session,operator_root,output,windows_parity):
    record,manifest=r.session(session);directory=Path(record['work']).parent.parent
    require(record['sources']==r.sources() and manifest['dirty_input']==digest(record['sources']),'Captured sources differ')
    require(manifest['run_id']==record['run_id'] and manifest['app']==r.APP and manifest['repo']==str(ROOT),'Unrelated managed run')
    require(manifest['verification']['errors']==[] and manifest['errors']==[],'Managed verification failed')
    lifecycle=dict(run_id=manifest['run_id'],manifest_sha256=sha(directory/'manifest.json'),state=manifest['state'],exit_code=manifest['exit_code'],runtime_clear=manifest['verification']['runtime_clear'],errors=[],limits=manifest['limits'])
    check_lifecycle(lifecycle)
    proof=read_json(operator_root/'report.json');traces={}
    require(proof['health']==dict(status='ok',synthetic_only=True,run_id=manifest['run_id']),'Operator/managed health binding differs')
    for item in proof['proofs']:traces[item['kind']]=read_json(Path(record['work'])/'parameter-traces'/(item['request_id']+'.json'))
    operator(operator_root,proof,traces,private_frames=True)
    for trace in traces.values():
        native=trace['native_status_readback'];require(native['request']==trace['native_request'] and native['phase']==trace['phase'] and native.get('prepared')==trace['prepared'],'Actual native readback differs')
        require(digest(native)==trace['native_status_readback_sha256'],'Actual native status hash differs')
        require(digest(native['offer'])==trace['actual_windows_offer_sha256'],'Actual native offer differs from Windows offer')
        require(not any(native.get(k) for k in ('intent','job','job_id','result','receipt')),'Physical/downstream action entered parameter proof')
        frame=Path(record['work'])/('windows-parameter-'+native['request']['request_id']+'.png')
        require(sha(frame)==trace['native_frame_sha256'],'Actual Windows status native frame differs')
    relay=read_json(Path(record['work'])/'windows-parameter-relay/result.json')
    provenance=read_json(Path(record['work'])/'windows-parameter-relay/provenance.json')
    require(provenance['run_id']==manifest['run_id'] and provenance['review_source_sha256']==record['source_sha256'] and provenance['relay_sha256']==sha(ROOT/'scripts/v1-windows-parameter-relay.py'),'Relay source/managed-run binding differs')
    # Publish only UI request/prepared/scalar provenance. Full native saved state
    # contains profile display names and remains private with all screenshots.
    traces={kind:{key:value for key,value in trace.items() if key not in ('native_status_readback','native_visible_geometry')} for kind,trace in traces.items()}
    require(not output.exists(),'Refusing evidence overwrite')
    output.mkdir(parents=True)
    shutil.copyfile(operator_root/'report.json',output/'operator.json')
    shutil.copyfile(windows_parity,output/'windows-parity.json')
    report=dict(schema=SCHEMA,privacy='Windows/native frames and raw metadata retained privately; exact hashes verified at promotion',relay_sha256=provenance['relay_sha256'],relay_result={key:value for key,value in relay.items() if key!='retained_metadata'},windows_parity_sha256=sha(output/'windows-parity.json'),sources=record['sources'],verifier_sha256=sha(__file__),historical=historical(),lifecycle=lifecycle,operator_sha256=sha(output/'operator.json'),traces=traces)
    (output/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    verify(output)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('op',choices=['build','verify']);p.add_argument('root',type=Path);p.add_argument('--session',type=Path);p.add_argument('--operator',type=Path);p.add_argument('--windows-parity',type=Path);a=p.parse_args()
    if a.op=='verify':verify(a.root)
    else:
        require(a.session is not None and a.operator is not None and a.windows_parity is not None,'Build requires retained session and operator paths');build(a.session,a.operator,a.root,a.windows_parity)
