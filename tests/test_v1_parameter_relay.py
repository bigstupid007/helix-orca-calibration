"""Metadata-only relay guard tests; no Windows, native runtime or bridge calls."""
import argparse
import copy
import importlib.util
from pathlib import Path
import time
import unittest
from integration.v1_contract import digest

PATH=Path(__file__).resolve().parents[1]/'scripts/v1-windows-parameter-relay.py'
spec=importlib.util.spec_from_file_location('parameter_relay',PATH)
relay=importlib.util.module_from_spec(spec);spec.loader.exec_module(relay)


class ParameterRelay(unittest.TestCase):
    def setUp(self):
        now=int(time.time())
        self.request=dict(schema='helix-orca-v1-request/v1',request_id='a'*32,origin_id='b'*32,
            context_sha256='c'*64,calibration='flow_ratio_yolo',parameters={'pass':2},
            created_at=now,expires_at=now+3600,not_applied=True)
        self.session=dict(request=self.request,offer={'synthetic':'metadata fixture, not UI evidence'},
                          phase='requested',sequence=0,message='fixture')
        self.args=argparse.Namespace(windows_python=r'C:\Python\python.exe',windows_source=r'C:\Q\source',
            windows_root=r'C:\Q\bridge',windows_context=r'C:\Q\original.json',windows_config=r'C:\Q\config.json',
            bridge_sha256='d'*64)

    def test_guarded_ps_contains_only_bounded_base64_input_and_exact_source_guard(self):
        command=relay.powershell(self.args,'consume',self.session)
        self.assertLessEqual(len(command),8192)
        self.assertIn('FromBase64String',command);self.assertIn('CreateNew',command)
        self.assertIn(' -I -S ',command);self.assertIn('Get-FileHash',command)
        self.assertNotIn('flow_ratio_yolo',command)
        self.assertNotIn('Start-Process',command)
        self.assertIn(' --op consume ',command)

    def test_oversized_metadata_or_unc_destination_is_refused(self):
        bad=copy.deepcopy(self.session);bad['message']='x'*6000
        with self.assertRaisesRegex(ValueError,'oversized'):
            relay.powershell(self.args,'consume',bad)
        self.args.windows_root=r'\\untrusted\share'
        with self.assertRaisesRegex(ValueError,'local_windows_path'):
            relay.powershell(self.args,'offer')

    def result(self):
        event={'request':self.request}
        return dict(request=self.request,transport_request=copy.deepcopy(self.request),coordinator_request=copy.deepcopy(self.request),
            request_sha256=digest(self.request),transport_request_sha256=digest(self.request),
            coordinator_request_sha256=digest(self.request),native_event_sha256=digest(event),transport_event_sha256=digest(event),
            status=dict(request_id=self.request['request_id'],origin_id=self.request['origin_id']),
            actions_adapter_present=False,physical_actions=False)

    def test_independent_transport_journal_and_event_readbacks_all_bind_exact_request(self):
        good=self.result()
        self.assertEqual(relay.independent_bindings(self.session,good),self.request)
        for key in ('request','transport_request','coordinator_request'):
            bad=copy.deepcopy(good);bad[key]['parameters']={'pass':1}
            with self.subTest(key=key),self.assertRaises(ValueError):relay.independent_bindings(self.session,bad)
        bad=copy.deepcopy(good);bad['transport_event_sha256']='f'*64
        with self.assertRaises(ValueError):relay.independent_bindings(self.session,bad)

    def test_native_status_readback_requires_actual_phase_sequence_and_preparation(self):
        status=dict(phase='blocked',sequence=2,prepared=None,prepared_sha256=None)
        saved=dict(request=self.request,phase='blocked',sequence=2)
        self.assertTrue(relay.native_bound(saved,self.request,status))
        for key,value in (('phase','requested'),('sequence',1),('prepared',{'forged':True})):
            with self.subTest(key=key):self.assertFalse(relay.native_bound(dict(saved,**{key:value}),self.request,status))

    def test_only_final_qualified_review_can_complete_without_terminal_or_cancel(self):
        self.assertEqual(relay.trial_completion({'phase':'review'},True,4,5),
                         'final-qualified-review-no-start')
        for qualified,count,trials in ((False,4,5),(True,3,5),(True,4,0),(1,4,5)):
            with self.subTest(qualified=qualified,count=count,trials=trials):
                self.assertIsNone(relay.trial_completion({'phase':'review'},qualified,count,trials))
        self.assertIsNone(relay.trial_completion({'phase':'confirmed'},True,4,5))
        self.assertEqual(relay.trial_completion({'phase':'blocked'},False,0,5),'terminal')
