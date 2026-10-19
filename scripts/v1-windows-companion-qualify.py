"""Isolated native companion qualification, never a product worker.

Preparation calls the actual offline coordinator and stock generator. Returned
result is an explicitly synthetic UI fixture; it cannot contact a printer.
"""
import argparse,hashlib,importlib.util,json,subprocess,sys,time
from pathlib import Path
from decimal import Decimal
p=argparse.ArgumentParser();p.add_argument('op',choices=['prepare','result-simulation','readback']);p.add_argument('--checkout',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.checkout))
from integration.v1_contract import canonical,digest,validate_context
from integration.v1_runtime import atomic_json,read_json
S=a.root;storage=S/'data/orca_plugins/plugin_data/helix_calibration/v1';work=S/'companion-workflow-r8';original_sha='3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'
assert (S/'data/.helix-orca-v1-qualification').is_file()
assert storage.is_dir() and not storage.is_symlink()
def out(value):
    value.update(physical_actions=False,physical_readiness=False)
    print(canonical(value).decode())
def tick():
    r=subprocess.run([sys.executable,'-I','-S',str(a.checkout/'scripts/v1-runtime.py'),'--storage',str(storage),'--config',str(work/'generator.json'),'--state',str(work/'coordinator'),'--offline-channel',str(work/'offline'),'--once'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    (work/('tick-'+str(time.time_ns())+'.log')).write_bytes(r.stdout+b'\n'+r.stderr)
    assert r.returncode==0,'offline_coordinator_failed'
if a.op=='prepare':
    ctx=validate_context(read_json(storage/'context.json'));assert digest(ctx)==original_sha
    assert not any((storage/n).exists() for n in ('view.json','inbox.json','committed.json')),'unexpected_prior_job'
    work.mkdir(exist_ok=False);atomic_json(work/'original.json',ctx)
    config=read_json(S/'actual-flow-yolo-production-r8/generation-config.json');config.pop('now',None);atomic_json(work/'generator.json',config)
    tick();offer=read_json(work/'offline/context.json');request={k:offer[k] for k in ('request_id','origin_id','context_sha256','created_at','expires_at')};request.update(schema='helix-orca-v1-request/v1',calibration='flow_ratio_yolo',parameters={'pass':1},not_applied=True);atomic_json(work/'offline/native.json',{'request':request});tick()
    view=read_json(storage/'view.json');assert view['status']['phase']=='review' and view['status']['prepared']['parity']['qualified'] is True
    atomic_json(work/'prepared-view.json',view);atomic_json(work/'request.json',request)
    prep=view['status']['prepared'];out(dict(schema='helix-orca-v1-windows-companion-preparation/v1',actual_offline_coordinator=True,phase='review',qualified=True,context_sha256=original_sha,request_sha256=digest(request),prepared_sha256=digest(prep),parity_report_sha256=prep['parity']['report_sha256'],artifact_sha256=prep['artifact']['sha256']))
elif a.op=='result-simulation':
    original=read_json(work/'original.json');request=read_json(work/'request.json');view=read_json(work/'prepared-view.json');prepared=view['status']['prepared'];current=validate_context(read_json(storage/'context.json'));assert digest(current)!=original_sha,'perform_actual_isolated_profile_switch_first'
    job='synthetic-ui-review-no-printer';proof=dict(job_id=job,file_sha256=prepared['artifact']['sha256'],print_state='complete',history_state='completed',history_job_id=job,history_file_sha256=prepared['artifact']['sha256']);value=float(Decimal(original['effective']['filament_flow_ratio']));result=dict(schema='helix-orca-v1-result/v1',request_id=request['request_id'],origin_id=request['origin_id'],context_sha256=request['context_sha256'],prepared_sha256=digest(prepared),job_id=job,completion_sha256=digest(proof),setting='filament_flow_ratio',value=value,not_applied=True)
    view['status'].update(phase='delivered',message='UI review simulation only. No printer was contacted; this retained result is NOT APPLIED.',job_id=job);view['result']=None
    atomic_json(storage/'view.json',view);atomic_json(storage/'inbox.json',dict(result=result,request=request,prepared=prepared,completion=proof));atomic_json(work/'synthetic-result.json',result)
    out(dict(schema='helix-orca-v1-windows-companion-result-simulation/v1',synthetic_completion=True,original_context_sha256=original_sha,current_context_sha256=digest(current),expected_result_sha256=digest(result),not_applied=True))
else:
    committed=read_json(storage/'committed.json');receipt=read_json(storage/'receipt.json');expected=read_json(work/'synthetic-result.json');current=validate_context(read_json(storage/'context.json'));assert committed['result']==expected and receipt['result']==expected and receipt['result_sha256']==digest(expected);assert digest(committed['original'])==original_sha and digest(current)!=original_sha
    out(dict(schema='helix-orca-v1-windows-companion-readback/v1',synthetic_completion=True,origin_bound=True,committed_before_receipt=True,result_sha256=digest(expected),original_context_sha256=digest(committed['original']),current_context_sha256=digest(current),not_applied=True))
