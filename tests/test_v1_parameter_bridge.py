"""Actual offline coordinator/core with unavailable backends, not native UI proof."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from integration.v1_contract import canonical,digest,ContractError
from integration.v1_runtime import read_json
from tests.test_v1_runtime import context

PATH = Path(__file__).resolve().parents[1]/'scripts/v1-windows-parameter-bridge.py'
spec = importlib.util.spec_from_file_location('parameter_bridge',PATH)
bridge = importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)


class ParameterBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'bridge'
        self.context = context()
        self.sources = {'fixture':'source-only test metadata'}
        self.offer = self.execute('offer')['offer']

    def execute(self,op,native=None,now=100,config=None):
        return bridge.execute(op,self.root,self.context,config or {},self.sources,native,'a'*64,now=lambda:now)

    def session(self,calibration='flow_ratio_yolo',parameters=None):
        request = {key:self.offer[key] for key in ('request_id','origin_id','context_sha256','created_at','expires_at')}
        request.update(schema='helix-orca-v1-request/v1',calibration=calibration,
                       parameters=parameters or {'pass':2},not_applied=True)
        return dict(request=request,offer=copy.deepcopy(self.offer),phase='requested',sequence=0,
                    message='Synthetic native-session fixture; not operator evidence')

    def test_all_five_exact_requests_enter_real_tick_and_retain_real_capability_blockers(self):
        cases = [('temperature',dict(start=235,end=215,step=5,scale=True)),
                 ('flow_ratio_yolo',{'pass':2}),
                 ('pressure_advance_pattern',dict(start=.01,end=.09,step=.01)),
                 ('retraction',dict(start=.2,end=2.2,step=.2)),
                 ('max_volumetric_speed',dict(start=6,end=24,step=.6))]
        for kind,parameters in cases:
            session = self.session(kind,parameters)
            before = canonical(session)
            result = self.execute('consume',{'v1_session':session})
            self.assertEqual(canonical(session),before)
            self.assertEqual(result['request'],session['request'])
            self.assertEqual(result['request_sha256'],digest(session['request']))
            self.assertEqual(result['status']['phase'],'blocked')
            self.assertEqual(result['generation_state'],'not_dispatched')
            self.assertFalse(result['generator_dispatched']);self.assertFalse(result['artifact_generated'])
            self.assertFalse(result['qualified']);self.assertFalse(result['actions_adapter_present'])
            journal = read_json(self.root/'coordinator/coordinator.json')
            self.assertEqual(journal['request'],session['request'])
            self.assertIsNone(journal['prepared']);self.assertIsNone(journal['job'])
            self.offer = self.execute('offer')['offer']
        self.assertEqual(len(list((self.root/'coordinator/history').glob('*.json'))),5)

    def test_changed_offer_identity_and_default_fields_are_rejected(self):
        for key,value in [('request_id','f'*32),('printer','changed'),('nozzle_mm',.8),('defaults',{})]:
            session = self.session();session['offer'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(bridge.Refused,'offer_differs'):
                self.execute('consume',session)
        self.assertIsNone(read_json(self.root/'coordinator/coordinator.json')['request'])

    def test_expired_request_is_never_reissued_or_time_rewritten(self):
        session = self.session()
        with self.assertRaises(ContractError):
            self.execute('consume',session,now=self.offer['expires_at'])
        self.assertEqual(read_json(self.root/'coordinator/coordinator.json')['offer'],self.offer)
        self.assertFalse((self.root/'offline/native.json').exists())

    def test_terminal_duplicate_returns_same_real_status_without_new_offer_or_dispatch(self):
        session = self.session();first=self.execute('consume',session)
        second=self.execute('consume',session)
        self.assertEqual(first['request'],second['request'])
        self.assertEqual(first['status'],second['status'])
        self.assertEqual(first['offer'],second['offer'])
        self.assertFalse((self.root/'coordinator/history').exists())

    def test_forged_prepared_or_start_intent_cannot_enter_first_request(self):
        for extra in ({'prepared':{'parity':{'qualified':True}}},{'intent':{'action':'start'}}):
            session=self.session();session.update(extra)
            with self.assertRaisesRegex(bridge.Refused,'unconsumed_native'):
                self.execute('consume',session)
        self.assertIsNone(read_json(self.root/'coordinator/coordinator.json')['request'])

    def test_recipe_config_cannot_be_swapped_under_an_existing_offer(self):
        with self.assertRaisesRegex(bridge.Refused,'configuration_changed'):
            self.execute('consume',self.session(),config={'routes':{'flow_ratio_yolo':'native-engine'}})
