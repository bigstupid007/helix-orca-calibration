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
        sample=replace(self.current,printer_identity=base.PHYSICAL_PRINTER_IDENTITY)
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
        adapter=transport.MoonrakerPrintAdapter('http://192.168.2.5:7125','192.168.2.5','pinned-version','f'*64)
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
