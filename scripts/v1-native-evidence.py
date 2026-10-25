#!/usr/bin/env python3
"""Prepare/verify portable synthetic native evidence; private Docker inventories stay private."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
def load():
    spec=importlib.util.spec_from_file_location('portable_v1_native_capture',ROOT/'scripts/v1-native-qualify.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module
q=load()
SCHEMA='helix-orca-v1-native-portable-evidence/v2'
HEX32=re.compile(r'[a-f0-9]{32}')
HEX64=re.compile(r'[a-f0-9]{64}')
FRAMES=q.FRAMES
def require(ok,message):
    if not ok:raise ValueError(message)
def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def safe_file(root,name):
    path=Path(name)
    require(not path.is_absolute() and '..' not in path.parts,'Unsafe evidence path')
    target=root/path
    require(root.resolve() in target.resolve().parents and not target.is_symlink() and target.is_file(),'Evidence file missing or substituted')
    return target

def lifecycle_summary(item,sources):
    path=Path(item['manifest']);record=read(path)
    require(record['run_id']==item['run_id'] and HEX32.fullmatch(record['run_id']),'Managed run identity differs')
    require(record['app']=='helix-orca-v1-native' and record['issue'].endswith('/issues/14'),'Unrelated managed run')
    require(record['dirty_input']==q.contract.digest(sources),'Managed run source identity differs')
    require(record['docker'] is True and record['state']=='complete' and record['exit_code']==0,'Managed workload incomplete')
    require(record['verification']['runtime_clear'] is True and record['verification']['errors']==[] and record['errors']==[],'Managed teardown/verification failed')
    require(set(record['containers'])==set(item['containers']) and len(record['containers'])==1,'Owned container inventory differs')
    for cid,container in record['containers'].items():
        require(container['id']==cid and container['labels'].get('io.100day.lifecycle.run')==record['run_id'],'Unowned container recorded')
    require(record.get('scratch_retained') is False,'Successful managed scratch not retired')
    return {'run_id':record['run_id'],'manifest_sha256':file_hash(path),'state':record['state'],
            'runtime_clear':record['verification']['runtime_clear'],'command_exit':record['exit_code'],
            'limits':record['limits'],'errors':[]}

def check_summary(item):
    require(set(item)=={'run_id','manifest_sha256','state','runtime_clear','command_exit','limits','errors'},'Malformed lifecycle summary')
    require(HEX32.fullmatch(item['run_id']) and HEX64.fullmatch(item['manifest_sha256']),'Malformed lifecycle identity')
    require(item['state']=='complete' and item['runtime_clear'] is True and type(item['command_exit']) is int and item['command_exit']==0 and item['errors']==[],'Incomplete lifecycle summary')
    limits=item['limits']
    require(set(limits)=={'reserve','peak','margin','timeout','grace','log_bytes'} and all(type(v) is int for v in limits.values()),'Malformed lifecycle limits')
    require(limits['reserve']==5*1024**3 and limits['peak']==512*1024**2 and limits['margin']==512*1024**2,'Unrecognized disk envelope')
    require(limits['timeout']==240 and limits['grace']==1 and limits['log_bytes']==1024**2,'Unrecognized execution envelope')

def verify_content(root,report):
    require(report['sources']==q.hashes(),'Captured native sources differ from candidate')
    require(report['synthetic_only'] is True and type(report['physical_actions']) is int and report['physical_actions']==0 and report['container_network']=='none','Isolation claim differs')
    require(report['synthetic_inputs']==['context','generator availability','prepared artifact','build qualification','processor warning','print status','completion proof','result application','receipt'],'Synthetic fixture disclosure differs')
    beta=q.beta12
    pins={'tag':beta.TAG,'source_commit':beta.SOURCE_COMMIT,'tag_object':beta.TAG_OBJECT,
          'release_asset_id':beta.RELEASE_ASSET_ID,'release_name':beta.RELEASE_NAME,
          'release_sha256':beta.RELEASE_SHA256,
          'release_binary_sha256':beta.RELEASE_BINARY_SHA256}
    for key,value in pins.items():require(report['runtime'][key]==value,'Pinned native runtime differs: '+key)
    beta.validate_metadata(report['runtime'])
    expected=[]
    for label,w,h,layout,dpi in q.a.VIEWPORTS:
        expected.append(dict(label=label,viewport=f'{w}x{h}',layout=layout,dpi=dpi,result='PASS',calibrations=list(q.contract.CALIBRATIONS),assertions=q.ASSERTIONS))
    require(report['results']==expected,'Incomplete geometry/workflow matrix')
    expected_frames={label+'/'+frame for label,*_ in q.a.VIEWPORTS for frame in FRAMES}
    require(set(report['screenshots'])==expected_frames,'Incomplete or unexpected native frames')
    for name,digest in report['screenshots'].items():
        require(HEX64.fullmatch(digest) and file_hash(safe_file(root,name))==digest,'Native screenshot differs: '+name)
    with tempfile.TemporaryDirectory(prefix='v1-native-portable-fixture-') as tmp:
        generated=q.fixture(Path(tmp)/'plugins')
        require(q.q.file_hashes(generated/'orcacal')==report['fixture_files'],'Generated native fixture differs')

def build(capture,output):
    original=read(capture/'report.json')
    require(original['schema']=='helix-orca-v1-native-evidence/v2','Not a beta.12 native capture report')
    verify_content(capture,original)
    require(len(original['managed_runs'])==11,'Incomplete private lifecycle proof')
    summaries=[lifecycle_summary(item,original['sources']) for item in original['managed_runs']]
    for item in summaries:check_summary(item)
    portable=dict(original)
    portable.update(schema=SCHEMA,capture_schema=original['schema'],capture_report_sha256=file_hash(capture/'report.json'),
                    verifier_sha256=file_hash(__file__),managed_runs=summaries,
                    lifecycle_provenance='Sanitized summaries verified against complete private ManagedRun records; full Docker/host inventories retained privately.')
    require(not output.exists(),'Refusing to overwrite portable manifest')
    write(output,portable)
    print('PASS: portable manifest prepared; full private inventories were excluded')

def verify(root,private_capture=None):
    report=read(root/'report.json')
    require(report['schema']==SCHEMA and report['capture_schema']=='helix-orca-v1-native-evidence/v2','Unknown portable evidence schema')
    require(HEX64.fullmatch(report['capture_report_sha256']) and report['verifier_sha256']==file_hash(__file__),'Portable verifier/provenance differs')
    verify_content(root,report)
    require(len(report['managed_runs'])==11 and len({i['run_id'] for i in report['managed_runs']})==11,'Incomplete lifecycle summaries')
    for item in report['managed_runs']:check_summary(item)
    if private_capture:
        original=read(private_capture/'report.json')
        require(file_hash(private_capture/'report.json')==report['capture_report_sha256'],'Private capture report differs')
        expected=[lifecycle_summary(i,original['sources']) for i in original['managed_runs']]
        require(expected==report['managed_runs'],'Private lifecycle records differ')
    print('PASS: portable source-bound synthetic beta.12 native matrix (11 targets, 5 calibrations)'+('; private lifecycle records verified' if private_capture else '; private inventories not required'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('op',choices=['build','verify']);p.add_argument('root',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-managed',type=Path);x=p.parse_args()
    if x.op=='build':
        require(x.output is not None,'build requires --output for the portable manifest');build(x.root,x.output)
    else:verify(x.root,x.verify_managed)
