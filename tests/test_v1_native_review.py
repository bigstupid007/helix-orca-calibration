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
            self.assertIn('SYNTHETIC ONLY',module.html('local-token'))
            with self.assertRaises(FileNotFoundError):module.get_resource()
    def test_shared_helper_is_verified_before_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'helper.py';path.write_text("raise AssertionError('must not execute')")
            with self.assertRaisesRegex(r.ContractError,'Shared ManagedRun helper differs'):r.load_helper(path)
        self.assertEqual(r.sources()['shared/resource_lifecycle.py'],r.HELPER_SHA256)
    def test_fixture_emits_initial_offer_at_native_initialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=r.q.fixture(Path(tmp)/'plugins')
            self.assertTrue((root/'orcacal/main.lua').read_text().rstrip().endswith('fixture_offer()'))
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
        self.assertIn('SYNTHETIC ONLY',r.html('test-token'))
        self.assertIn("'X-Helix-Review':\"test-token\"",r.html('test-token'))
    def test_duration_cannot_escape_bound(self):
        self.assertEqual(r.duration(60),60);self.assertEqual(r.duration(900),900)
        for value in (0,59,901):
            with self.assertRaises(Exception):r.duration(value)
    def test_simulation_follows_native_intent_and_never_finishes_early(self):
        fixture=r.Fixture('owned-cid',Path('/not-used'))
        states=[('requested',None,2),('preparing',None,3),('review','confirm',4),('starting','start',5),('printing','cancel',11),('returning',None,7)]
        with patch.object(r.q,'signal') as signal:
            for phase,action,code in states:
                saved=dict(phase=phase,request=dict(request_id='a'*32),intent=dict(action=action))
                with patch.object(fixture,'saved',return_value=saved):fixture.pump()
                self.assertEqual(signal.call_args.args,('owned-cid',code))
            signal.reset_mock()
            for phase in ('review','confirmed','complete'):
                with patch.object(fixture,'saved',return_value=dict(phase=phase,intent=None)):
                    fixture.pump()
                    with self.assertRaises(r.ContractError):fixture.finish()
            signal.assert_not_called()
            with patch.object(fixture,'saved',return_value=dict(phase='printing')):fixture.finish()
            signal.assert_called_once_with('owned-cid',6)
    def test_terminal_offer_exactly_once_without_replacing_retained_context(self):
        fixture=r.Fixture('owned-cid',Path('/not-used'))
        saved=dict(phase='delivered',request=dict(request_id='a'*32),intent=None)
        with patch.object(fixture,'saved',return_value=saved),patch.object(r.q,'signal') as signal:
            fixture.pump();fixture.pump();signal.assert_called_once_with('owned-cid',1)
        self.assertEqual(saved['request']['request_id'],'a'*32)
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
