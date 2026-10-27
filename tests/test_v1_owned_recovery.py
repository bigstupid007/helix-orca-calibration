"""True Coordinator/OwnedJobAdapter crash recovery through loopback HTTP only."""
import copy
import json
import unittest
from unittest.mock import patch

from integration.v1_contract import DEFAULTS, digest
from integration.v1_jobs import OwnedJobAdapter
from integration.v1_runtime import Coordinator, read_json
import test_v1_jobs as http_fixtures
import test_v1_runtime as runtime_fixtures


class CoordinatedOwnedRecovery(unittest.TestCase):
    def setUp(self):
        # Only parity is injected for this explicitly synthetic artifact; real
        # contract/artifact checks, coordinator, adapter, journal and HTTP run.
        self.h = http_fixtures.OwnedJobsTests()
        self.h.setUp()
        self.addCleanup(self.h.tearDown)
        h = self.h
        data = (h.directory/'fixture.gcode').read_bytes()
        def generate(req, snapshot, directory, config):
            h.request = copy.deepcopy(req); h.directory = directory
            value = copy.deepcopy(h.prepared)
            value.update({key:req[key] for key in ('request_id','origin_id','context_sha256','calibration','parameters')})
            value['request_sha256'] = digest(req)
            (directory/'fixture.gcode').write_bytes(data)
            (directory/'parity.json').write_text(json.dumps(h.report))
            h.prepared = value
            return value
        self.generator = generate
        self.caps = [dict(id=kind, available=True, reason='Synthetic HTTP fixture only') for kind in DEFAULTS]
        self.path = h.root/'coordinator'
        self.runtime = Coordinator(self.path, generate, {}, self.caps, now=lambda:100, job_adapter=h.adapter)
        context = runtime_fixtures.context()
        context['printer'] = copy.deepcopy(h.machine_inputs['printer'])
        self.runtime.request(runtime_fixtures.request(self.runtime.offer(context)))
        self.assertEqual(self.runtime.state['phase'], 'review')
        self.runtime.intent(h.intent('confirm','5'))
        self.assertEqual(self.runtime.state['phase'], 'confirmed')

    def crash_after_adapter_durable_printing(self):
        original = self.h.adapter.start
        def process_dies(*args):
            original(*args)  # HTTP Start and independent owned history confirmed.
            raise SystemExit('synthetic death before coordinator job save')
        with patch.object(self.h.adapter, 'start', side_effect=process_dies), self.assertRaises(SystemExit):
            self.runtime.intent(self.h.intent('start','6'))
        coordinator = read_json(self.path/'coordinator.json')
        self.assertIsNone(coordinator['job'])
        self.assertEqual(coordinator['pending_start_intent'], self.h.intent('start','6'))
        record = read_json(self.h.root/'journal'/(self.h.request['request_id']+'.json'))
        self.assertEqual(record['phase'], 'printing'); self.assertTrue(record['ownership_confirmed'])

    def restart(self):
        self.h.adapter = OwnedJobAdapter(self.h.fixture.transport(), self.h.root/'journal',
            orca_machine_sha256=self.h.machine, physical_qualification=self.h.qualification,
            actions=True, now=lambda:10000)
        return Coordinator(self.path, self.generator, {}, self.caps, now=lambda:10000, job_adapter=self.h.adapter)

    def assert_one_dispatch(self):
        self.assertEqual(self.h.fixture.posts.count('/server/files/upload'), 1)
        self.assertEqual(sum(path.startswith('/printer/print/start?') for path in self.h.fixture.posts), 1)

    def test_restart_adopts_confirmed_owned_job_then_fresh_history_unlocks_result(self):
        self.crash_after_adapter_durable_printing()
        runtime = self.restart()
        self.assertEqual(runtime.state['phase'], 'uncertain')
        self.assertIsNone(runtime.state['job'])
        gets = len(self.h.fixture.gets)
        runtime.poll_job()
        self.assertGreater(len(self.h.fixture.gets), gets)  # Fresh observe, not cached proof.
        self.assertEqual(runtime.state['phase'], 'printing')
        self.assertEqual(runtime.state['job']['job_id'], 'ABC123')
        self.assert_one_dispatch()
        self.h.fixture.state = 'complete'; self.h.fixture.history_status = 'completed'
        runtime.poll_job()
        self.assertEqual(runtime.state['phase'], 'complete')
        self.assertIsNotNone(runtime.state['completion'])
        value = {key:self.h.request[key] for key in ('request_id','origin_id','context_sha256')}
        value.update(schema='helix-orca-v1-result/v1', prepared_sha256=digest(self.h.prepared),
                     job_id=runtime.state['job']['job_id'], completion_sha256=digest(runtime.state['completion']),
                     setting=runtime.evaluation()['setting'], value=runtime.evaluation()['options'][0], not_applied=True)
        self.assertEqual(runtime.result(value), value)
        runtime.acknowledge(dict(schema='helix-orca-v1-ack/v1', request_id=value['request_id'], origin_id=value['origin_id'],
                                 result_sha256=digest(value), result=value, not_applied=True))
        self.assertEqual(runtime.state['phase'], 'delivered')
        self.assert_one_dispatch()

    def test_recovered_job_can_cancel_exact_owned_job_without_replaying_start(self):
        self.crash_after_adapter_durable_printing()
        runtime = self.restart(); runtime.poll_job()
        runtime.intent(self.h.intent('cancel','7'))
        runtime.poll_job()
        self.assertEqual(runtime.state['phase'], 'cancelled')
        self.assertEqual(self.h.fixture.posts.count('/printer/print/cancel'), 1)
        self.assert_one_dispatch()


if __name__ == '__main__':
    unittest.main()
