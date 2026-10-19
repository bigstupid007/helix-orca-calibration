import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v1_native_review_test',ROOT/'scripts/v1-native-review.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class NativeReviewTests(unittest.TestCase):
    def test_lost_press_reply_uses_fresh_socket_release_and_keeps_original_error(self):
        writes=[];connections=[]
        class Stream:
            def __init__(self,fail):self.fail=fail
            def write(self,data):writes.append(json.loads(data))
            def readline(self,_):
                if self.fail:raise OSError('original lost press reply')
                return b'{"id":1,"result":true}\n'
            def close(self):pass
        class Client:
            def __init__(self,fail):self.stream=Stream(fail)
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def settimeout(self,value):self.timeout=value
            def connect(self,path):connections.append(path)
            def makefile(self,*_,**__):return self.stream
        with tempfile.TemporaryDirectory() as tmp,patch.object(r.socket,'socket',side_effect=[Client(True),Client(False)]):
            with self.assertRaisesRegex(OSError,'original lost press reply'):
                r.pointer(Path(tmp),r.points(dict(x=21,y=34)))
        self.assertEqual(len(connections),2)
        self.assertEqual([v['method'] for v in writes],['pointer_press','pointer_release'])
        self.assertEqual(writes[1]['params'],dict(x=21,y=34))
    def test_every_response_refuses_foreign_framing(self):
        for status,content in ((200,'text/html'),(200,'image/png'),(400,'application/json')):
            stored={}
            fake=SimpleNamespace(send_response=lambda value:stored.update(status=value),send_header=lambda key,value:stored.update({key:value}),end_headers=lambda:stored.update(ended=True))
            r.review_headers(fake,status,content,32)
            self.assertEqual(stored['status'],status)
            self.assertEqual(stored['X-Frame-Options'],'DENY')
            self.assertIn("frame-ancestors 'none'",stored['Content-Security-Policy'])
            self.assertIn("default-src 'self'",stored['Content-Security-Policy'])
            self.assertEqual(stored['Cache-Control'],'no-store')
            self.assertTrue(stored['ended'])
    def test_security_file_is_bound_in_source_inventory(self):
        key='integration/v1_private_file.py'
        self.assertEqual(r.sources()[key],r.sha(ROOT/key))
        original=r.sha
        def changed(path):return '0'*64 if Path(path)==ROOT/key else original(path)
        with patch.object(r,'sha',changed):self.assertEqual(r.sources()[key],'0'*64)
    def test_import_and_pure_controls_without_devbox_helper(self):
        original=Path.read_bytes
        def unavailable(path):
            if str(path)==str(r.HELPER):raise FileNotFoundError('No devbox on CI')
            return original(path)
        with patch.object(Path,'read_bytes',unavailable):
            spec=importlib.util.spec_from_file_location('portable_review_import',ROOT/'scripts/v1-native-review.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.assertIsNone(module.resource)
            self.assertEqual(module.duration(60),60)
            self.assertEqual(module.payload('/api/back',{}),{})
            self.assertIn('NO PRINTER · OFFLINE CONTEXT',module.html('local-token'))
            with self.assertRaises(FileNotFoundError):module.get_resource()
    def test_shared_helper_is_verified_before_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'helper.py';path.write_text("raise AssertionError('must not execute')")
            with self.assertRaisesRegex(r.ContractError,'Shared ManagedRun helper differs'):r.load_helper(path)
        self.assertEqual(r.sources()['shared/resource_lifecycle.py'],r.HELPER_SHA256)
    def test_review_fixture_delivers_only_actual_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=r.transport_fixture(Path(tmp)/'plugins')
            source=(root/'orcacal/main.lua').read_text()
            self.assertIn("v1_review_delivery",source)
            self.assertNotIn('fixture_offer()',source)
            self.assertNotIn('fixture_status',source)
            self.assertNotIn('qualified=true',source)
        self.assertNotIn('data-action="finish-mock"',r.html('token'))
        with self.assertRaises(r.ContractError):r.payload('/api/finish-mock',{})

    def test_native_input_is_bounded_and_typed(self):
        for body in ({'x':0,'y':0},{'x':799,'y':479}):self.assertEqual(r.payload('/api/tap',body),body)
        for body in ({'x':True,'y':1},{'x':800,'y':1},{'x':1,'y':480},{'x':1,'y':1,'rpc':'start'},{'x':'1','y':1}):
            with self.assertRaises(r.ContractError):r.payload('/api/tap',body)
        for route in ('/api/rpc','/api/gcode','/api/start','/api/stop','/api/config'):
            with self.assertRaises(r.ContractError):r.payload(route,{})
        self.assertEqual(r.points({'x':2,'y':3}),[('pointer_press',2,3),('pointer_release',2,3)])
        drag=r.points(dict(x0=0,y0=0,x1=799,y1=479))
        self.assertEqual(drag[0],('pointer_press',0,0));self.assertEqual(drag[-1],('pointer_release',799,479));self.assertEqual(len(drag),10)
    def test_fixed_host_origin_and_token(self):
        good=dict(Host=f'{r.LAN}:{r.PORT}',Origin=f'http://{r.LAN}:{r.PORT}')
        r.authorized_http(good)
        for headers in ({'Host':'evil:8540'},{**good,'Origin':'http://evil'},good):
            with self.assertRaises(r.ContractError):r.authorized_http(headers,True,'owner-secret')
        r.authorized_http({**good,'X-Helix-Review':'owner-secret'},True,'owner-secret')
        self.assertIn('NO PRINTER · OFFLINE CONTEXT',r.html('test-token'))
        self.assertIn("'X-Helix-Review':\"test-token\"",r.html('test-token'))
    def test_duration_cannot_escape_bound(self):
        self.assertEqual(r.duration(60),60);self.assertEqual(r.duration(900),900)
        for value in (0,59,901):
            with self.assertRaises(Exception):r.duration(value)
    def test_real_event_fragmentation_preserves_payload_under_native_subject_limit(self):
        data=dict(message='°'*512,values=list(range(1000)))
        with patch.object(r.q,'ctl') as native:
            r.deliver('owned','helix_orca_v1.context.v1',data)
        frames=[json.loads(call.args[-1]) for call in native.call_args_list]
        self.assertGreater(len(frames),1)
        self.assertTrue(all(len(call.args[-1].encode())<1023 for call in native.call_args_list))
        self.assertEqual([f['index'] for f in frames],list(range(1,len(frames)+1)))
        self.assertEqual(len({f['id'] for f in frames}),1)
        self.assertEqual(json.loads(''.join(f['part'] for f in frames)),dict(event='helix_orca_v1.context.v1',data=data))

    def test_actual_coordinator_retains_unavailable_request_and_archives_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)/'view';work.mkdir()
            fixture=r.CoordinatorReview('owned-cid',work)
            with patch.object(r.q,'ctl'):
                fixture.pump()
                offer=fixture.runtime.state['offer']
                request={key:offer[key] for key in ('request_id','origin_id','context_sha256','created_at','expires_at')}
                request.update(schema='helix-orca-v1-request/v1',calibration='retraction',parameters=dict(start=.2,end=2.2,step=.2),not_applied=True)
                r.atomic_json(work/'config/plugin-data/orcacal.json',dict(v1_session=dict(request=request,phase='requested')))
                fixture.pump()
                trace=r.read_json(work/'parameter-traces'/(request['request_id']+'.json'))
                self.assertEqual(trace['native_request'],request)
                self.assertEqual(trace['transport_request'],request)
                self.assertEqual(trace['coordinator_request'],request)
                self.assertEqual(trace['phase'],'blocked')
                self.assertFalse(trace['generator_dispatched'])
                self.assertIsNone(trace['prepared'])
                self.assertFalse(trace['physical_adapter_enabled'])
                fixture.pump()
                self.assertEqual(trace,r.read_json(work/'parameter-traces'/(request['request_id']+'.json')))
                self.assertEqual(r.read_json(fixture.runtime.root/'history'/(request['request_id']+'.json'))['request'],request)

    def test_stop_only_writes_exact_owned_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'stop.json';record=dict(run_id='a'*32,stop_file=str(path))
            with patch.object(r,'session',return_value=(record,dict(state='running'))):
                self.assertEqual(r.stop()['state'],'stopping')
            self.assertEqual(json.loads(path.read_text()),dict(schema=r.STOP_SCHEMA,run_id='a'*32))
            self.assertEqual(path.stat().st_mode&0o077,0)
            path.unlink()
            with patch.object(r,'session',return_value=(record,dict(state='complete',verification=dict(runtime_clear=True)))):
                self.assertTrue(r.stop()['runtime_clear'])
            self.assertFalse(path.exists())
    def test_session_rejects_other_app_or_substituted_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run_id='b'*32;directory=root/'runs'/run_id
            artifacts=directory/'artifacts';artifacts.mkdir(parents=True)
            record=dict(schema=r.SCHEMA,app=r.APP,run_id=run_id,container='c'*64,work=str(artifacts/'view'),stop_file=str(artifacts/'review-stop.json'))
            helper=SimpleNamespace(ROOT=root,identity=lambda path:[Path(path).stat().st_dev,Path(path).stat().st_ino],LABEL='io.100day.lifecycle.run')
            manifest=dict(run_id=run_id,app=r.APP,repo=str(r.ROOT.resolve()),owner=r.os.getuid(),artifacts=helper.identity(artifacts),containers={'c'*64:dict(labels={helper.LABEL:run_id})})
            r.atomic_json(directory/'manifest.json',manifest);r.atomic_json(root/'current.json',record)
            with patch.dict(r.os.environ,{'XDG_STATE_HOME':str(root/'other-xdg')}),patch.object(r,'resource',helper):
                self.assertEqual(r.session(root/'current.json')[0],record)
                manifest['app']='different';r.atomic_json(directory/'manifest.json',manifest)
                with self.assertRaises(r.ContractError):r.session(root/'current.json')
                manifest['app']=r.APP;manifest['artifacts']=[-1,-1];r.atomic_json(directory/'manifest.json',manifest)
                with self.assertRaises(r.ContractError):r.session(root/'current.json')

if __name__=='__main__':unittest.main()
