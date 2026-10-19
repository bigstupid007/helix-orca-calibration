"""Fault injection at durable intent boundaries; all adapter effects are local fixtures."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integration.v1_contract import digest, ContractError
from integration.v1_runtime import Coordinator
import test_v1_runtime as fixtures
from test_v1_runtime import context, request, prepared


class Crash(BaseException):
    pass


class RecoveryTests(unittest.TestCase):
    def make(self, root, phase):
        r=fixtures.RuntimeTests().make(root)
        req=request(r.offer(context()))
        value=prepared(req)
        value['artifact']=dict(name='fixture.gcode',size=1,sha256='a'*64)
        r.state.update(request=req,prepared=value,phase=phase)
        if phase=='printing':
            r.state['job']=dict(job_id='fixture-job',file_sha256='a'*64,request_id=req['request_id'],origin_id=req['origin_id'])
        r._persist()
        return r

    def test_recovery_advances_equal_status_once_without_actions(self):
        for phase in ('review','confirmed','complete'):
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as root:
                r=self.make(root,phase)
                if phase=='complete':
                    r.state['job']=dict(job_id='fixture-job')
                    r.state['completion']=dict(job_id='fixture-job')
                    r._persist()
                old=r.status()
                native=dict(request=copy.deepcopy(r.state['request']),sequence=old['sequence'],phase='uncertain',
                    recovery_required=True,prepared=old['prepared'],prepared_sha256=old['prepared_sha256'],
                    job_id=old['job_id'],completion_sha256=old['completion_sha256'])
                for key,value in (('sequence',True),('sequence',old['sequence']+1),('request',{}),('prepared_sha256','f'*64),('job_id','wrong'),('completion_sha256','e'*64)):
                    self.assertFalse(r.reconcile_native(dict(native,**{key:value})))
                    self.assertEqual(r.status(),old)
                for key in ('prepared','prepared_sha256','job_id','completion_sha256'):
                    if native[key] is not None:
                        missing=dict(native);missing.pop(key)
                        self.assertFalse(r.reconcile_native(missing))
                        self.assertEqual(r.status(),old)
                self.assertTrue(r.reconcile_native(native))
                self.assertEqual(r.status()['sequence'],old['sequence']+1)
                self.assertEqual(r.status()['phase'],phase)
                current=r.status()
                self.assertTrue(r.reconcile_native(native))
                self.assertEqual(r.status(),current)
                self.assertEqual(fixtures.RuntimeTests().make(root).status(),current)

    def test_intent_crashes_cannot_consume_without_recording_outcome(self):
        for action,phase in (('confirm','review'),('start','confirmed'),('cancel','printing')):
            for after in (False,True):
                with self.subTest(action=action,after=after),tempfile.TemporaryDirectory() as root:
                    r=self.make(root,phase)
                    class Adapter:
                        confirmed=set()
                        starts=0
                        cancels=0
                        def confirm(self,*args): self.confirmed.add(args[-1]['intent_id'])
                        def start(self,req,p,*_):
                            self.starts+=1
                            return dict(job_id='fixture-job',file_sha256='a'*64,request_id=req['request_id'],origin_id=req['origin_id'])
                        def cancel(self,*_): self.cancels+=1
                    adapter=Adapter();r.job_adapter=adapter
                    intent=dict(schema='helix-orca-v1-intent/v1',request_id=r.state['request']['request_id'],
                        origin_id=r.state['request']['origin_id'],prepared_sha256=digest(r.state['prepared']),action=action,intent_id='3'*32)
                    persist=r._persist
                    def crash():
                        if after: persist()
                        raise Crash()
                    with patch.object(Coordinator,'verify_artifact'),patch.object(Coordinator,'verify_parity'),patch.object(r,'_persist',side_effect=crash):
                        with self.assertRaises(Crash): r.intent(intent)
                    recovered=fixtures.RuntimeTests().make(root);recovered.job_adapter=adapter
                    if after:
                        self.assertIn(intent['intent_id'],recovered.state['consumed_intents'])
                        self.assertEqual(recovered.state['phase'],'confirmed' if action=='confirm' else 'uncertain')
                    else:
                        self.assertNotIn(intent['intent_id'],recovered.state['consumed_intents'])
                        self.assertEqual(recovered.state['phase'],phase if phase!='printing' else 'uncertain')
                    # Dispatch has not happened before the atomic intent/phase boundary.
                    self.assertEqual(adapter.starts,0);self.assertEqual(adapter.cancels,0)
                    with patch.object(Coordinator,'verify_artifact'),patch.object(Coordinator,'verify_parity'):
                        recovered.intent(intent)
                    self.assertEqual(adapter.starts,0 if after or action!='start' else 1)
                    self.assertEqual(adapter.cancels,0 if after or action!='cancel' else 1)
                    self.assertLessEqual(len(adapter.confirmed),1)

    def test_restart_adopts_durable_adapter_job_without_start_replay(self):
        for after in (False,True):
            with self.subTest(after=after),tempfile.TemporaryDirectory() as root:
                r=self.make(root,'confirmed')
                class Adapter:
                    starts=0
                    retained=None
                    def start(self,req,prepared,directory,intent):
                        self.starts+=1
                        self.retained=(copy.deepcopy(req),copy.deepcopy(prepared),copy.deepcopy(intent),
                            dict(job_id='fixture-job',file_sha256='a'*64,request_id=req['request_id'],origin_id=req['origin_id']))
                        return self.retained[-1]
                    def recover(self,req,prepared,intent):
                        if self.retained[:3]!=(req,prepared,intent): raise ContractError('Foreign recovery')
                        return copy.deepcopy(self.retained[-1])
                    def observe(self,job):
                        return dict(job_id=job['job_id'],file_sha256=job['file_sha256'],print_state='complete',history_state='completed',
                            history_job_id=job['job_id'],history_file_sha256=job['file_sha256'])
                adapter=Adapter();r.job_adapter=adapter
                req=r.state['request']
                intent=dict(schema='helix-orca-v1-intent/v1',request_id=req['request_id'],origin_id=req['origin_id'],
                    prepared_sha256=digest(r.state['prepared']),action='start',intent_id='4'*32)
                persist=r._persist;calls=0
                def crash_after_adapter():
                    nonlocal calls
                    calls+=1
                    if calls==2:
                        if after:persist()
                        raise Crash()
                    persist()
                with patch.object(Coordinator,'verify_artifact'),patch.object(Coordinator,'verify_parity'),patch.object(r,'_persist',side_effect=crash_after_adapter):
                    with self.assertRaises(Crash):r.intent(intent)
                recovered=fixtures.RuntimeTests().make(root);recovered.job_adapter=adapter
                self.assertEqual(recovered.state['pending_start_intent'],intent)
                recovered.intent(intent)
                self.assertEqual(adapter.starts,1)
                recovered.poll_job()
                self.assertEqual(recovered.status()['phase'],'complete')
                self.assertEqual(recovered.status()['job_id'],'fixture-job')
                self.assertEqual(adapter.starts,1)

    def test_invalid_phase_does_not_consume_an_intent(self):
        with tempfile.TemporaryDirectory() as root:
            r=self.make(root,'review')
            intent=dict(schema='helix-orca-v1-intent/v1',request_id=r.state['request']['request_id'],origin_id=r.state['request']['origin_id'],
                prepared_sha256=digest(r.state['prepared']),action='start',intent_id='3'*32)
            with self.assertRaises(ContractError):r.intent(intent)
            self.assertEqual(r.state['consumed_intents'],[])
