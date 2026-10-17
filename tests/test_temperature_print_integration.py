"""Run the physical lifecycle contract only against a fake adapter and local artifacts."""
import copy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import test_temperature_print_lifecycle as base
import test_temperature_communication_companion as original

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
controller=load('print_controller_test',ROOT/'integration/temperature-print/controller.py')
transport=load('print_transport_test',ROOT/'integration/temperature-print/transport.py')

class AdvancingFake(base.FakeAdapter):
    def snapshot(self):
        sample=replace(self.current,printer_identity=base.PHYSICAL_PRINTER_IDENTITY,configuration_sha256=base.PRINTER_CONFIG_SHA256,moonraker_version=base.MOONRAKER_VERSION)
        if self.last_snapshot_eventtime is not None:
            sample=replace(sample,eventtime=max(sample.eventtime,self.last_snapshot_eventtime+.1))
        self.last_snapshot_eventtime=sample.eventtime
        return sample

class ControllerTests(unittest.TestCase):
    def test_native_intent_through_independent_completion_to_original_not_applied_receipt(self):
        clock=base.Clock();adapter=AdvancingFake();events=[]
        with tempfile.TemporaryDirectory() as d:
            state=controller.protocol.TemperatureCommunicationState(d,now=clock.wall_time)
            target=original.target();target['printer']=target['printer'].copy()
            target['printer']['selected_saved']=dict(target['printer']['selected_saved'],name=base.PRINTER)
            state.start_new(target)
            file={'name':base.FILE,'size':len(base.FILE_DATA),'sha256':base.FILE_SHA,'bands':[210,205,200]}
            state.select_file(file,controller.protocol.validate_print_temperature_file);state.send()
            outbox=json.loads((Path(d)/'print-readiness/outbox.json').read_text());p=outbox['payload']
            qual=base.qualification(**{k:p[k] for k in ('request_id','origin_id','context_sha256')})
            def permit(c,intent):return c.issue_local_permit(intent,authorization_id='a'*32,deadline_monotonic=60)
            def write(value):controller.protocol.atomic_write_json(Path(d)/'print-readiness/inbox.json',value)
            with base.lifecycle.TemperaturePrintLifecycle(Path(d)/'journal.json',adapter,wall_time=clock.wall_time,monotonic=clock.monotonic) as c:
                ctl=controller.NativePrintController(c,outbox,qual,event_sink=lambda e,v:events.append((e,v)),write_inbox=write,authorize_intent=permit)
                ctl.offer();self.assertFalse(adapter.start_calls)
                native={'print_session':{'request':copy.deepcopy(p)}}
                ctl.step(native);self.assertFalse(adapter.start_calls)
                intent=base.start_intent(**{k:p[k] for k in ('request_id','origin_id','context_sha256')})
                intent['nonce']=p['request_id']+':100000000'
                native['print_session']['start_intent']=intent
                ctl.step(native);self.assertEqual(adapter.start_calls,[base.FILE]);self.assertFalse(c.status().result_available)
                adapter.show_printing();ctl.step(native);self.assertFalse(c.status().result_available)
                adapter.show_complete();ctl.step(native);self.assertTrue(c.status().result_available)
                native['print_session']['result']={k:p[k] for k in ('request_id','origin_id','context_sha256','file_sha256','file','file_bytes','setting','physical_calibration','not_applied')}
                native['print_session']['result'].update(schema=controller.protocol.RESULT_SCHEMA,value=205,job_id=c.status().job_id,completion_sha256=c.status().completion_proof_sha256)
                ctl.step(native);state.poll_inbox()
                self.assertEqual(state.instructions['status'],'NOT APPLIED');self.assertEqual(state.instructions['selected_value'],205)
                self.assertEqual(state.target,target)
                receipt=json.loads((Path(d)/'print-readiness/receipt.json').read_text())
                ctl.acknowledge(receipt)
                self.assertEqual(events[-1][0],'helix_orca_temperature_print.ack.v1')
                self.assertEqual(adapter.start_calls,[base.FILE])
                self.assertEqual(adapter.cancel_calls,0)
    def test_physical_actions_disabled_before_network_request(self):
        adapter=transport.MoonrakerPrintAdapter('http://192.168.2.5:7125','192.168.2.5','pinned-version','f'*64,configuration_sha256='e'*64)
        class NoNetwork:
            def open(self,*a,**k):raise AssertionError('Network call forbidden in test')
        adapter.reader.opener=NoNetwork()
        for call in (lambda:adapter.start_print('mini.gcode'),adapter.cancel_print):
            with self.assertRaisesRegex(transport.lc.SafetyViolation,'disabled'):call()
    def test_start_cannot_outlive_original_start_window_with_fresh_intent(self):
        clock=base.Clock();adapter=AdvancingFake()
        with tempfile.TemporaryDirectory() as d,base.lifecycle.TemperaturePrintLifecycle(Path(d)/'j.json',adapter,wall_time=clock.wall_time,monotonic=clock.monotonic) as c:
            c.bind_request(base.request(),base.qualification())
            clock.wall=1900
            intent=c.parse_start_intent(base.start_intent())
            permit=c.issue_local_permit(intent,authorization_id='a'*32,deadline_monotonic=60)
            with self.assertRaises(base.lifecycle.SafetyViolation):c.start(intent,permit=permit)
            self.assertFalse(adapter.start_calls)

class MoonrakerContractTests(unittest.TestCase):
    def test_recorded_source_shapes_normalize_and_changed_configuration_fails_closed(self):
        import hashlib
        config={'mcu':{'canbus_uuid':'mock-controller'}}
        network={'eth0':{'mac_address':'mock-mac','ip_addresses':[]}}
        identity=hashlib.sha256(json.dumps({'mcu_kind':'canbus_uuid','mcu_identity':'mock-controller','macs':['mock-mac']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        reader=transport.MoonrakerPrintAdapter('http://192.168.2.5:7125','192.168.2.5','pinned',identity,configuration_sha256=digest)
        samples=[100.0]
        def get(path):
            if path=='/server/info':value={'moonraker_version':'pinned','klippy_state':'ready','failed_components':[]}
            elif path=='/machine/system_info':value={'system_info':{'network':network}}
            elif path=='/printer/objects/query?configfile':value={'status':{'configfile':{'settings':config}}}
            elif path=='/server/job_queue/status':value={'queued_jobs':[],'queue_state':'paused'}
            elif path=='/printer/objects/query?print_stats':
                samples[0]+=.1;value={'eventtime':samples[0],'status':{'print_stats':{'state':'standby','filename':''}}}
            elif path.startswith('/server/history/job?'):
                value={'job':{'job_id':'000001','filename':'mini.gcode','status':'in_progress','start_time':1000,'end_time':None}}
            else:raise AssertionError('Unapproved endpoint '+path)
            return {'result':value}
        reader.reader._json_get=get
        sample=reader.snapshot()
        self.assertEqual(sample.state,'standby');self.assertEqual(sample.printer_identity,identity)
        self.assertEqual(reader.history('000001').status,'printing')
        config['printer']={'max_velocity':999}
        with self.assertRaisesRegex(transport.lc.SafetyViolation,'configuration changed'):reader.snapshot()

class ControllerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.clock=base.Clock();self.adapter=AdvancingFake();self.events=[]
        t=original.target();t['printer']['selected_saved']['name']=base.PRINTER
        self.state=controller.protocol.TemperatureCommunicationState(self.root,now=self.clock.wall_time)
        self.state.start_new(t)
        self.state.select_file({'name':base.FILE,'size':len(base.FILE_DATA),'sha256':base.FILE_SHA,'bands':[210,205,200]},controller.protocol.validate_print_temperature_file)
        self.state.send();self.outbox=json.loads((self.root/'print-readiness/outbox.json').read_text());self.p=self.outbox['payload']
        self.qual=base.qualification(**{k:self.p[k] for k in ('request_id','origin_id','context_sha256')})
        self.c=self.coordinator()
        self.ctl=self.make_controller()
        intent=base.start_intent(**{k:self.p[k] for k in ('request_id','origin_id','context_sha256')})
        intent['nonce']=self.p['request_id']+':100000000'
        self.native={'print_session':{'request':copy.deepcopy(self.p),'start_intent':intent}}
    def tearDown(self):self.c.close();self.temp.cleanup()
    def coordinator(self):
        return base.lifecycle.TemperaturePrintLifecycle(self.root/'journal.json',self.adapter,wall_time=self.clock.wall_time,monotonic=self.clock.monotonic)
    def make_controller(self):
        def permit(c,i):return c.issue_local_permit(i,authorization_id='a'*32,deadline_monotonic=60)
        return controller.NativePrintController(self.c,self.outbox,self.qual,event_sink=lambda e,d:self.events.append((e,d)),write_inbox=lambda v:None,authorize_intent=permit)
    def printing(self):
        self.ctl.step(self.native);self.adapter.show_printing();self.ctl.step(self.native)
    def test_controller_restart_preserves_exact_binding_sequence_and_one_shot_dispatch(self):
        self.printing();sequence=self.events[-1][1]['sequence'];self.c.close()
        self.c=self.coordinator();self.ctl=self.make_controller();self.ctl.step(self.native)
        self.assertEqual(self.adapter.start_calls,[base.FILE]);self.assertEqual(self.c.status().phase,'printing')
        self.assertGreater(self.events[-1][1]['sequence'],sequence)
        bad=copy.deepcopy(self.qual);bad['printer_config_sha256']='f'*64
        with self.assertRaises(controller.ControllerError):
            controller.NativePrintController(self.c,self.outbox,bad,event_sink=lambda *x:None,write_inbox=lambda x:None)
    def test_history_lag_is_nonterminal_then_same_job_success_unlocks(self):
        self.printing();self.adapter.show_complete(history_status='printing');self.ctl.step(self.native)
        self.assertEqual(self.events[-1][1]['state'],'confirming');self.assertFalse(self.c.status().result_available)
        self.adapter.show_complete();self.ctl.step(self.native)
        self.assertEqual(self.events[-1][1]['state'],'complete');self.assertTrue(self.c.status().result_available)
    def test_disconnect_publishes_terminal_status_without_reading_again(self):
        self.printing()
        def broken():raise RuntimeError('Synthetic disconnect')
        self.adapter.snapshot=broken
        self.ctl.step(self.native)
        self.assertIn(self.events[-1][1]['state'],('failed','uncertain'));self.assertFalse(self.c.status().result_available)
    def test_late_offer_never_advertises_start(self):
        self.clock.wall=1900
        with self.assertRaisesRegex(controller.ControllerError,'window'):self.ctl.offer()
        self.assertFalse(self.events);self.assertFalse(self.adapter.start_calls)

class AuthorizationTests(unittest.TestCase):
    def test_runner_accepts_only_exact_separate_scoped_founder_grant(self):
        import hashlib
        runner=load('print_runner_auth_tests',ROOT/'scripts/temperature-print-relay.py')
        p=base.request();q=base.qualification()
        fields=('request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer')
        grant={k:p[k] for k in fields}
        grant.update(schema='helix-orca-physical-test-authorization/v1',founder_authorization_reference='SYNTHETIC TEST ONLY',authorized=True,native_screen_start_only=True,
            physical_printer_identity=q['physical_printer_identity'],printer_config_sha256=q['printer_config_sha256'],moonraker_version=q['moonraker_version'],expires_at=1900,
            qualification_sha256=hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        self.assertEqual(runner.validate_grant(grant,p,q,1000),grant)
        for key,bad in [('authorized',False),('native_screen_start_only',False),('qualification_sha256','f'*64),('file_sha256','f'*64),('expires_at',999),('moonraker_version','changed')]:
            changed=dict(grant);changed[key]=bad
            with self.assertRaises(ValueError):runner.validate_grant(changed,p,q,1000)
        with self.assertRaises(ValueError):runner.validate_grant({'authorized':True},p,q,1000)

        with self.assertRaises(ValueError):runner.validate_grant(grant,p,q,2000)
        self.assertEqual(runner.validate_grant(grant,p,q,2000,allow_expired=True),grant)
        changed=dict(grant,expires_at=p['expires_at']+1)
        with self.assertRaises(ValueError):runner.validate_grant(changed,p,q,2000,allow_expired=True)
