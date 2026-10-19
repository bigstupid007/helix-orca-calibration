#!/usr/bin/env python3
"""Bounded native parameter review using the actual offline V1 coordinator."""
from __future__ import annotations
import argparse
import hashlib
import http.server
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import secrets
import re
from urllib.parse import urlparse, parse_qs
import socket
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.v1_contract import ContractError, digest
from integration.v1_runtime import Coordinator, atomic_json, read_json
from integration.v1_transport import DirectoryEvents
from integration.v1_routing import generate, capabilities
from integration.v1_private_file import private_file

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
q=load('v1_native_review_capture',ROOT/'scripts/v1-native-qualify.py')
HELPER=Path('/home/dev/Projects/system/100-day-development-system/scripts/resource_lifecycle.py')
HELPER_SHA256='8a2cb48220f14c8f4ca5c2cc9f6fcdcdf28fa436fe4b7dd50cf6489178ba6fcc'
def load_helper(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=HELPER_SHA256:
        raise ContractError('Shared ManagedRun helper differs from reviewed4a42a94')
    return load('v1_native_review_resources',path)
resource=None
def get_resource():
    global resource
    if resource is None:resource=load_helper(HELPER)
    return resource
LAN='192.168.1.114'
PORT=8540
DEFAULT_SECONDS=900
APP='helix-orca-v1-native-review'
SCHEMA='helix-orca-v1-native-review-session/v1'
STOP_SCHEMA='helix-orca-v1-native-review-stop/v1'
CURRENT=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'helix-orca-calibration/v1-native-review/current.json'

def require(value,message):
    if not value:raise ContractError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sources():
    return {**q.hashes(),**{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'integration').glob('v1_*.py')},'scripts/v1-native-review.py':sha(__file__),'scripts/v1-runtime.py':sha(ROOT/'scripts/v1-runtime.py'),'scripts/temperature-viewer.html':sha(ROOT/'scripts/temperature-viewer.html'),'shared/resource_lifecycle.py':HELPER_SHA256,'integration/v1_private_file.py':sha(ROOT/'integration/v1_private_file.py')}
def session(path=CURRENT):
    resource=get_resource()
    record=read_json(private_file(Path(path).absolute()))
    require(record.get('schema')==SCHEMA and record.get('app')==APP,'Not a V1 review session')
    run_id=record.get('run_id','')
    require(len(run_id)==32 and all(c in '0123456789abcdef' for c in run_id),'Invalid owned run ID')
    directory=Path(resource.ROOT)/'runs'/run_id
    require(Path(record['work'])==directory/'artifacts/view' and Path(record['stop_file'])==directory/'artifacts/review-stop.json','Unexpected owned review paths')
    manifest=read_json(directory/'manifest.json')
    require(manifest['run_id']==run_id and manifest['app']==APP and manifest['repo']==str(ROOT.resolve())
            and manifest['owner']==os.getuid(),'Review ownership differs')
    require(resource.identity(directory/'artifacts')==manifest['artifacts'],'Review artifacts substituted')
    require(set(manifest['containers'])=={record['container']} and manifest['containers'][record['container']]['labels'][resource.LABEL]==run_id,'Owned container differs')
    return record,manifest

def stop(path=CURRENT):
    record,manifest=session(path)
    if manifest['state']!='running':return {'state':'stopped','run_id':record['run_id'],'runtime_clear':manifest.get('verification',{}).get('runtime_clear',False)}
    atomic_json(Path(record['stop_file']),dict(schema=STOP_SCHEMA,run_id=record['run_id']))
    return {'state':'stopping','run_id':record['run_id']}

def payload(route,body):
    allowed={'/api/tap':('x','y'),'/api/drag':('x0','y0','x1','y1'),'/api/home':(),'/api/back':(),'/api/capture':()}
    require(route in allowed and isinstance(body,dict) and set(body)==set(allowed[route]),'Unsupported review action')
    if route in ('/api/tap','/api/drag'):
        for key in allowed[route]:
            limit=800 if key.startswith('x') else 480
            require(type(body[key]) is int and 0<=body[key]<limit,'Native pointer outside 800x480')
    return body

def _pointer_send(work,events,attempt=lambda *_:None,ack=lambda *_:None):
    directory=os.open(work,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(3);client.connect(f'/proc/self/fd/{directory}/control.sock')
            stream=client.makefile('rwb',buffering=0)
            try:
                for index,(method,x,y) in enumerate(events,1):
                    attempt(method,x,y)
                    stream.write((json.dumps(dict(jsonrpc='2.0',id=index,method=method,params=dict(x=x,y=y)))+'\n').encode())
                    reply=json.loads(stream.readline(65537));require(reply.get('id')==index and 'error' not in reply,'Native pointer rejected')
                    ack(method,x,y)
            finally:stream.close()
    finally:os.close(directory)

def pointer(work,events):
    # A socket disconnect does not release beta.9's process-wide pointer state.
    state=dict(held=False,x=0,y=0)
    def attempted(method,x,y):
        state.update(x=x,y=y)
        if method=='pointer_press':state['held']=True
    def acknowledged(method,*_):
        if method=='pointer_release':state['held']=False
    try:_pointer_send(work,events,attempted,acknowledged)
    finally:
        if state['held']:
            try:_pointer_send(work,[('pointer_release',state['x'],state['y'])])
            except Exception:pass  # Preserve the original error; exact bounded best effort.

def points(body):
    if 'x' in body:return [('pointer_press',body['x'],body['y']),('pointer_release',body['x'],body['y'])]
    x0,y0,x1,y1=(body[k] for k in ('x0','y0','x1','y1'))
    return [('pointer_press',x0,y0)]+[('pointer_move',round(x0+(x1-x0)*i/8),round(y0+(y1-y0)*i/8)) for i in range(1,9)]+[('pointer_release',x1,y1)]

def transport_fixture(root):
    """Only delivers real coordinator events; contains no request or job fixtures."""
    target=root/'orcacal';q.builder.generate(target)
    with (target/'main.lua').open('a') as stream:
        stream.write("""
-- OFFLINE REVIEW TRANSPORT ONLY; omitted by the installable product builder.
-- Values are the actual DirectoryEvents payloads; no business action is seeded.
helix.subject.string('v1_review_delivery',''):observe(function(raw)
 local ok,value=pcall(helix.json.decode,raw)
 if not ok or type(value)~='table' then return end
 if value.event=='helix_orca_v1.context.v1' then v1_receive_offer('offline-review',value.data)
 elseif value.event=='helix_orca_v1.status.v1' then v1_receive_status('offline-review',value.data)
 elseif value.event=='helix_orca_v1.ack.v1' then v1_receive_ack('offline-review',value.data) end
end)
""")
    return root


def review_context():
    value=dict(schema='helix-orca-v1-context/v1',origin_id='a'*32,
        runtime=dict(version='2.5.0-dev',build='PUBLIC SYNTHETIC PROFILE CONTEXT'),nozzle_mm=.4,
        effective=dict(filament_flow_ratio='1',extruder_type='Direct Drive',nozzle_temperature='217'))
    for role in ('printer','process','filament'):
        value[role]={kind:dict(name='Review '+role,config=dict(identity=kind)) for kind in ('saved','edited')}
    return value


class CoordinatorReview:
    """Real routing/journal, no job adapter. The container's network stays disabled."""
    def __init__(self,container,work):
        self.container=container;self.work=Path(work);self.delivered={}
        self.storage=self.work.parent/'coordinator-storage'
        self.channel=DirectoryEvents(self.work.parent/'offline-events')
        self.runtime=Coordinator(self.work.parent/'coordinator',generate,{},capabilities({}))
        self.tick=load('v1_parameter_review_tick',ROOT/'scripts/v1-runtime.py').tick
        if not (self.storage/'context.json').exists():atomic_json(self.storage/'context.json',review_context())
        self.last_trace=None
    def saved(self):
        path=self.work/'config/plugin-data/orcacal.json'
        return read_json(path).get('v1_session') if path.exists() else None
    def pump(self):
        saved=self.saved() or {}
        # Preserve native event bytes semantically; never synthesize a request.
        atomic_json(self.channel.directory/'native.json',saved)
        self.tick(self.runtime,self.storage,self.channel)
        for event in ('context','status','ack'):
            path=self.channel.directory/(event+'.json')
            if not path.exists():continue
            data=read_json(path);fingerprint=digest(data)
            if self.delivered.get(event)==fingerprint:continue
            q.ctl(self.container,'set','orcacal__v1_review_delivery',json.dumps(dict(event='helix_orca_v1.'+event+'.v1',data=data),separators=(',',':')))
            self.delivered[event]=fingerprint
        state=self.runtime.state;request=state.get('request')
        # tick archives terminal requests before offering a fresh nonce. Bind the
        # independent trace to its archived real coordinator journal as well.
        request=(saved.get('request') if saved else None)
        if request:
            journal=self.runtime.path
            if state.get('request')!=request:journal=self.runtime.root/'history'/(request['request_id']+'.json')
            if journal.exists():
                retained=read_json(journal)
                trace=dict(schema='helix-orca-v1-parameter-trace/v1',native_request=request,
                    transport_request=saved.get('request'),coordinator_request=retained.get('request'),
                    native_sha256=digest(request),coordinator_sha256=digest(retained.get('request')),
                    phase=retained['phase'],message=retained['message'],prepared=retained['prepared'],
                    generator_dispatched=(self.runtime.root/'jobs'/request['request_id']).exists(),
                    physical_adapter_enabled=False)
                atomic_json(self.work/'parameter-traces'/(request['request_id']+'.json'),trace)
        return self.saved()

def html(token):
    text=(ROOT/'scripts/temperature-viewer.html').read_text()
    text=text.replace('__REVIEW_VERSION__',digest(sources()))
    text=text.replace('Mock Temperature review','V1 native parameter review')
    text=text.replace('Choose a temperature in native Helix, then Next.','Evaluate the simulated calibration in native Helix, then Return result.')
    text=text.replace('Mock Temperature · no printer connected','V1 parameter review · NO PRINTER · OFFLINE CONTEXT')
    text=text.replace('tap <b>Mock Temperature</b>','tap <b>Orca Calibration</b>')
    text=text.replace("'Content-Type':'application/json'", "'Content-Type':'application/json','X-Helix-Review':"+json.dumps(token))
    text=text.replace('<button id="finish" data-action="finish-mock" disabled>Finish simulated print</button>', '<button id="finish" hidden disabled>No printer connected</button>')
    text=text.replace("finish.disabled=v.state!==2;", "finish.disabled=true;")
    text=text.replace("'Use native Start, then finish the simulation here.'", "'Edit native parameters and request preparation. The actual coordinator reports unavailable generators.'")
    text=text.replace('Use native Start, then finish the simulation here.', 'Native controls → actual offline coordinator. Physical execution disabled.')
    return text

def authorized_http(headers,post=False,token=None):
    require(headers.get('Host')==f'{LAN}:{PORT}','Unexpected review host')
    require(headers.get('Origin') in (None,f'http://{LAN}:{PORT}'),'Unexpected review origin')
    if post:require(secrets.compare_digest(headers.get('X-Helix-Review',''),token),'Review token missing')

def review_headers(handler,status,content_type,length):
    # Keep accepted pixel-viewer CSP and prohibit embedding its native controls.
    handler.send_response(status)
    for name,value in (
        ('Content-Type',content_type),('Content-Length',str(length)),
        ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),
        ('X-Frame-Options','DENY'),
        ('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self'; frame-ancestors 'none'")):
        handler.send_header(name,value)
    handler.end_headers()

def duration(value):
    number=int(value)
    if not 60<=number<=900:raise argparse.ArgumentTypeError('Review duration must be 60..900 seconds')
    return number

def serve(record_path,seconds):
    record,manifest=session(record_path)
    work=Path(record['work']);container=record['container']
    require(manifest['state']=='running' and os.environ.get('MANAGED_RUN_ID')==record['run_id']
            and os.environ.get('RUN_ARTIFACTS')==str(work.parent),'Only the active managed owner may serve')
    require(record['sources']==sources(),'Review sources changed')
    require(q.q.file_hashes(Path(record['fixture_root'])/'orcacal')==record['fixture_files'],'Review fixture changed')
    q.q.beta9.configure_accepted_harness();a=q.a
    a.CONTAINER=container;a.state_root=lambda:work
    q.q.wait_ready(container)
    version=digest(record['sources']);token=secrets.token_hex(32);document=html(token)
    fixture=CoordinatorReview(container,work);captures=0
    class Handler(a.ViewerHandler):
        def _headers(self,status,content_type,length):review_headers(self,status,content_type,length)
        def setup(self):
            super().setup();self.connection.settimeout(5)
        def log_message(self,*_):pass
        def do_GET(self):
            try:
                authorized_http(self.headers)
                route=self.path.split('?',1)[0]
                if route=='/':self._send(document.encode(),'text/html; charset=utf-8')
                elif route=='/api/review-state':
                    saved=fixture.saved() or {};phase=saved.get('phase','idle')
                    self._json(dict(version=version,state={'printing':2,'complete':3,'delivered':4}.get(phase,0),phase=phase,synthetic_only=True))
                elif route=='/api/geometry':
                    query=parse_qs(urlparse(self.path).query)
                    name=query.get('name',[''])[0]
                    require(set(query)=={'name'} and len(query['name'])==1 and len(name)<=128 and re.fullmatch(r'orcacal__[a-zA-Z0-9_]+',name),'Native calibration widget required')
                    self._json(q.ctl(container,'geom',name,'0'))
                elif route=='/api/parameter-state':
                    saved=fixture.saved() or {};request=saved.get('request');trace=None
                    if request:
                        path=work/'parameter-traces'/(request['request_id']+'.json')
                        if path.exists():trace=read_json(path)
                    self._json(dict(native=saved,trace=trace))
                elif route=='/api/subject':
                    query=parse_qs(urlparse(self.path).query);name=query.get('name',[''])[0]
                    require(set(query)=={'name'} and len(query['name'])==1 and len(name)<=128 and re.fullmatch(r'orcacal__v1_[a-zA-Z0-9_]+',name),'Native calibration subject required')
                    self._json(q.ctl(container,'get',name))
                elif route=='/frame.png':
                    q.ctl(container,'screenshot','/state/viewer-frame.png')
                    self._send((work/'viewer-frame.png').read_bytes(),'image/png')
                elif route=='/health':self._json(dict(status='ok',synthetic_only=True,run_id=record['run_id']))
                else:self._json(dict(error='Not found'),404)
            except Exception as exc:self._json(dict(error=str(exc)),400)
        def do_POST(self):
            nonlocal captures
            try:
                authorized_http(self.headers,True,token)
                require(self.headers.get('Transfer-Encoding') is None,'Chunked requests refused')
                length=int(self.headers.get('Content-Length','0'));require(0<length<=4096,'Invalid request size')
                route=self.path;body=payload(route,json.loads(self.rfile.read(length)))
                if route in ('/api/tap','/api/drag'):pointer(work,points(body))
                elif route=='/api/home':q.ctl(container,'navigate','home')
                elif route=='/api/back':q.ctl(container,'go_back')
                elif route=='/api/capture':
                    require(captures<32,'Capture limit reached (32)');captures+=1
                    target=work/'manual-captures';target.mkdir(exist_ok=True)
                    q.ctl(container,'screenshot',f'/state/manual-captures/manual-{captures:02d}.png')
                q.ctl(container,'wait_idle')
                self._json(dict(message='Native review action complete; actual coordinator; no printer connected'))
            except Exception as exc:self._json(dict(error=str(exc)),400)
    require(ipaddress.ip_address(LAN).is_private and LAN!='0.0.0.0' and PORT==8540,'Reserved LAN viewer only')
    server=http.server.HTTPServer((LAN,PORT),Handler);server.timeout=.2
    end=time.monotonic()+seconds
    try:
        while time.monotonic()<end:
            require(sources()==record['sources'],'Review sources changed; stop and relaunch')
            stop_path=Path(record['stop_file'])
            if stop_path.exists():
                require(read_json(private_file(stop_path))==dict(schema=STOP_SCHEMA,run_id=record['run_id']),'Invalid owned stop request')
                break
            fixture.pump();server.handle_request()
    finally:server.server_close()

def launch(seconds,context=None):
    resource=get_resource()
    seconds=duration(seconds);before=sources()
    resource.private_dir(CURRENT.parent)
    q.q.beta9.verify_cache();q.q.beta9.configure_accepted_harness();a=q.a
    cache=q.builder.default_output().parent;cache.mkdir(parents=True,exist_ok=True)
    plugins=transport_fixture(cache/('review-fixture-'+uuid.uuid4().hex));fixture_files=q.q.file_hashes(plugins/'orcacal')
    a.PLUGIN_ROOT=plugins
    class NativeDocker(resource.DockerCLI):
        def create(self,run_id,image,command,memory,cpus,pids):
            require(image.startswith('sha256:'),'Immutable dependency required')
            require(not json.loads(self.call('image','inspect','--format','{{json .Config.Volumes}}',image)),'Image volumes forbidden')
            args=a._container_args('v1-review-'+run_id,work,800,480,'standard',160)
            args[1]='create';args.remove('--detach');args[args.index(a.IMAGE)]=image
            args[2:2]=['--label',resource.LABEL+'='+run_id,'--restart=no','--memory',str(memory),'--memory-swap',str(memory),'--cpus',str(cpus),'--pids-limit',str(pids),'--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2']
            return self.call(*args[1:])
    image=a.image_metadata()['id'];commit=a.run(['git','rev-parse','HEAD'],capture=True,cwd=ROOT).stdout.strip()
    with resource.ManagedRun(app=APP,repo=str(ROOT),issue='https://github.com/bigstupid007/helix-orca-calibration/issues/14',commit=commit,dirty_input=digest(before),paths=[str(CURRENT.parent),str(cache),str(ROOT)],reserve=5*1024**3,peak=512*1024**2,margin=512*1024**2,timeout=seconds,adapter=NativeDocker()) as run:
        work=run.artifacts/'view';work.mkdir();(work/'home').mkdir();q.settings(work/'config')
        if context is not None:
            from integration.v1_contract import validate_context
            atomic_json(run.artifacts/'coordinator-storage/context.json',validate_context(read_json(private_file(Path(context).absolute()))))
        cid=run.container(image,[],memory=512*1024**2,cpus=2,pids=128)
        require(sources()==before,'Sources changed while preparing review')
        record=dict(schema=SCHEMA,app=APP,run_id=run.data['run_id'],container=cid,work=str(work),stop_file=str(run.artifacts/'review-stop.json'),sources=before,source_sha256=digest(before),fixture_root=str(plugins),fixture_files=fixture_files,url=f'http://{LAN}:{PORT}',synthetic_only=True)
        record_path=run.artifacts/'review-session.json';atomic_json(record_path,record);atomic_json(CURRENT,record)
        print(json.dumps(dict(url=record['url'],run_id=record['run_id'],stop='python3 scripts/v1-native-review.py stop',synthetic_only=True)),flush=True)
        run.execute([sys.executable,str(Path(__file__).resolve()),'_serve',str(record_path),'--seconds',str(max(1,seconds-20))],cwd=ROOT)
        require(run.data.get('exit_code')==0,'Native review failed; inspect '+str(run.directory))
    require(run.data['state']=='complete' and run.data['verification']['runtime_clear'],'Native review lifecycle incomplete')
    print(json.dumps(dict(state='stopped',run_id=run.data['run_id'],runtime_clear=True)),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='op',required=True)
    start=sub.add_parser('launch');start.add_argument('--seconds',type=duration,default=DEFAULT_SECONDS);start.add_argument('--context',type=Path,help='Existing private local captured Orca context; absent uses explicit synthetic profiles')
    sub.add_parser('status');sub.add_parser('stop')
    internal=sub.add_parser('_serve');internal.add_argument('record',type=Path);internal.add_argument('--seconds',type=int,required=True)
    x=p.parse_args()
    if x.op=='launch':launch(x.seconds,x.context)
    elif x.op=='stop':print(json.dumps(stop()))
    elif x.op=='status':
        record,manifest=session();print(json.dumps(dict(run_id=record['run_id'],state=manifest['state'],runtime_clear=manifest.get('verification',{}).get('runtime_clear',False),url=record['url'],synthetic_only=True)))
    else:
        require(1<=x.seconds<=880,'Invalid managed review duration');serve(x.record,x.seconds)
if __name__=='__main__':main()
