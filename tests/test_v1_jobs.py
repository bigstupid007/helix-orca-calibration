"""Owned-job safety under loopback-only HTTP fixtures; no printer is contacted.

Parity verification is independently tested by test_v1_parity. These fixtures
patch only that verifier so synthetic G-code can exercise the dispatch boundary;
they never create native reference or claim calibration qualification.
"""
import copy
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, build_opener, ProxyHandler

from integration.v1_contract import ContractError, DEFAULTS, digest
from integration.v1_jobs import OwnedJobAdapter, PinnedMoonraker, from_config
from integration.v1_runtime import read_json
from integration.v1_transport import NoRedirect


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class PrinterFixture:
    def __init__(self):
        self.config = {'mcu': {'serial': 'fixture-only-mcu'}}
        self.identity = sha(dict(mcu_kind='serial', mcu_identity='fixture-only-mcu', macs=['fixture-mac']))
        self.config_hash = sha(self.config)
        self.files = {}; self.filename = ''; self.state = 'standby'; self.event = 1
        self.job_id = 'ABC123'; self.start_time = 10; self.history_status = 'in_progress'
        self.history_override = None; self.baseline = []; self.queue = []; self.started = False
        self.posts = []; self.gets = []; self.upload_fields = None
        self.tamper = False; self.start_error = False; self.cancel_error = False; self.auto_queue = False
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def response(self, value, code=200, raw=False):
                data = value if raw else json.dumps({'result': value}).encode()
                self.send_response(code); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
            def do_GET(self):
                fixture.gets.append(self.path)
                p = urlsplit(self.path); q = parse_qs(p.query)
                if self.path == '/server/info': return self.response(dict(moonraker_version='fixture-version', klippy_state='ready', failed_components=[]))
                if self.path == '/machine/system_info': return self.response(dict(system_info=dict(network=dict(eth0=dict(mac_address='fixture-mac')))))
                if self.path == '/printer/objects/query?configfile': return self.response(dict(status=dict(configfile=dict(settings=fixture.config))))
                if self.path == '/server/job_queue/status': return self.response(dict(queued_jobs=fixture.queue, queue_state='ready'))
                if self.path == '/printer/objects/query?print_stats':
                    fixture.event += 1
                    return self.response(dict(eventtime=fixture.event, status=dict(print_stats=dict(state=fixture.state, filename=fixture.filename, print_duration=fixture.event))))
                if p.path == '/server/files/metadata':
                    name = q['filename'][0]
                    if name not in fixture.files: return self.response({}, 404)
                    return self.response(dict(job_id=fixture.job_id if fixture.started else None, print_start_time=fixture.start_time if fixture.started else None))
                if p.path.startswith('/server/files/gcodes/'):
                    name = p.path.rsplit('/', 1)[1]
                    if name not in fixture.files: return self.response({}, 404)
                    return self.response(b'changed bytes' if fixture.tamper else fixture.files[name], raw=True)
                if p.path == '/server/history/list': return self.response(dict(jobs=fixture.baseline))
                if p.path == '/server/history/job':
                    history = fixture.history_override or dict(job_id=fixture.job_id, filename=fixture.filename, start_time=fixture.start_time, end_time=20 if fixture.history_status != 'in_progress' else None, status=fixture.history_status)
                    return self.response(dict(job=history))
                self.response({}, 404)
            def do_POST(self):
                fixture.posts.append(self.path)
                data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                p = urlsplit(self.path); q = parse_qs(p.query)
                if self.path == '/server/files/upload':
                    message = BytesParser(policy=default).parsebytes(('Content-Type: ' + self.headers['Content-Type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + data)
                    parts = {part.get_param('name', header='content-disposition'): part for part in message.iter_parts()}
                    fixture.upload_fields = {k: parts[k].get_payload(decode=True).decode() for k in ('root', 'print')}
                    filename = parts['file'].get_filename(); fixture.files[filename] = parts['file'].get_payload(decode=True)
                    return self.response(dict(item=dict(root='gcodes', path=filename), print_started=False, print_queued=fixture.auto_queue))
                if p.path == '/printer/print/start':
                    fixture.filename = q['filename'][0]; fixture.state = 'printing'; fixture.started = True
                    return self.response('ok', 500 if fixture.start_error else 200)
                if self.path == '/printer/print/cancel':
                    fixture.state = 'cancelled'; fixture.history_status = 'cancelled'
                    return self.response('ok', 500 if fixture.cancel_error else 200)
                self.response({}, 404)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
    def transport(self, actions=True):
        result = PinnedMoonraker('http://192.168.1.2', '192.168.1.2', 'fixture-version', self.identity, self.config_hash, trusted_lan=True, actions=actions)
        local = 'http://127.0.0.1:' + str(self.server.server_port)
        opener = build_opener(ProxyHandler({}), NoRedirect())
        class LoopbackOnly:
            def open(self, request, timeout):
                # Test-only redirect to this exact fixture, never physical origin.
                parsed = urlsplit(request.full_url)
                target = local + parsed.path + ('?' + parsed.query if parsed.query else '')
                return opener.open(Request(target, data=request.data, headers=dict(request.header_items()), method=request.method), timeout=timeout)
        result.opener = LoopbackOnly()
        return result


class OwnedJobsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.fixture = PrinterFixture()
        self.verifier = patch('integration.v1_jobs.Coordinator.verify_parity', return_value=None); self.parity = self.verifier.start()
        self.request = dict(schema='helix-orca-v1-request/v1', request_id='1'*32, origin_id='2'*32, context_sha256='3'*64,
            calibration='temperature', parameters=DEFAULTS['temperature'], created_at=100, expires_at=3700, not_applied=True)
        self.directory = self.root / self.request['request_id']; self.directory.mkdir()
        data = b'; SYNTHETIC OFFLINE HTTP FIXTURE\nG1 X1 Y1\n'; (self.directory/'fixture.gcode').write_bytes(data)
        self.prepared = {k: self.request[k] for k in ('request_id', 'origin_id', 'context_sha256', 'calibration', 'parameters')}
        self.prepared.update(schema='helix-orca-v1-prepared/v1', request_sha256=digest(self.request), artifact=dict(name='fixture.gcode', size=len(data), sha256=hashlib.sha256(data).hexdigest()),
            generator=dict(build='fixture', route='fixture'), parity=dict(qualified=True, report_sha256='4'*64, reason='Synthetic verifier injection only'), not_applied=True)
        self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/'journal', actions=True, now=lambda: 100)
    def tearDown(self):
        self.verifier.stop(); self.fixture.close(); self.temp.cleanup()
    def intent(self, action, token):
        return dict(schema='helix-orca-v1-intent/v1', request_id=self.request['request_id'], origin_id=self.request['origin_id'], prepared_sha256=digest(self.prepared), action=action, intent_id=token*32)
    def confirm(self):
        self.adapter.confirm(self.request, self.prepared, self.directory, self.intent('confirm', '5'))
    def start(self):
        return self.adapter.start(self.request, self.prepared, self.directory, self.intent('start', '6'))
    def record(self):
        return read_json(self.root/'journal'/('1'*32+'.json'))
    def test_disabled_default_and_missing_confirmation_do_not_contact_http(self):
        default_adapter = OwnedJobAdapter(self.fixture.transport(), self.root/'disabled', now=lambda: 100)
        default_adapter.confirm(self.request, self.prepared, self.directory, self.intent('confirm', '5'))
        with self.assertRaises(ContractError): default_adapter.start(self.request, self.prepared, self.directory, self.intent('start', '6'))
        self.assertEqual(self.fixture.gets, []); self.assertEqual(self.fixture.posts, [])
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, [])
    def test_confirm_start_are_distinct_and_artifact_reverified(self):
        self.confirm()
        with self.assertRaises(ContractError): self.adapter.start(self.request, self.prepared, self.directory, self.intent('start', '5'))
        (self.directory/'fixture.gcode').write_bytes(b'tampered')
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, [])
    def test_http_upload_is_owned_no_print_and_completion_requires_history(self):
        self.confirm(); job = self.start()
        self.assertEqual(self.fixture.upload_fields, {'root': 'gcodes', 'print': 'false'})
        self.assertEqual(self.fixture.posts[0], '/server/files/upload')
        self.assertTrue(self.fixture.posts[1].startswith('/printer/print/start?filename=helix-orca-v1-'))
        self.assertEqual(job['job_id'], 'ABC123'); self.assertEqual(self.record()['phase'], 'printing')
        proof = self.adapter.observe(job); self.assertEqual(proof['print_state'], 'printing')
        self.fixture.state = 'complete'
        waiting = self.adapter.observe(job)
        self.assertEqual(waiting['print_state'], 'complete'); self.assertIsNone(waiting['history_job_id'])
        self.fixture.history_status = 'completed'
        done = self.adapter.observe(job)
        self.assertEqual(done['history_state'], 'completed'); self.assertEqual(done['history_job_id'], job['job_id'])
        self.assertEqual(done['history_file_sha256'], job['file_sha256'])
    def test_configuration_queue_and_existing_filename_refuse_upload(self):
        self.confirm()
        self.fixture.config['unapproved'] = {}
        with self.assertRaises(ContractError): self.start()
        del self.fixture.config['unapproved']; self.fixture.queue = [dict(job_id='foreign')]
        with self.assertRaises(ContractError): self.start()
        self.fixture.queue = []; self.fixture.files[self.record()['filename']] = b'preserve'
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, [])
    def test_upload_readback_difference_blocks_start_and_restart_replay(self):
        self.confirm(); self.fixture.tamper = True
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, ['/server/files/upload']); self.assertEqual(self.record()['phase'], 'uncertain')
        recovered = OwnedJobAdapter(self.fixture.transport(), self.root/'journal', actions=True, now=lambda: 100)
        with self.assertRaises(ContractError): recovered.start(self.request, self.prepared, self.directory, self.intent('start', '7'))
        self.assertEqual(self.fixture.posts, ['/server/files/upload'])
    def test_ambiguous_start_is_durable_and_never_retried(self):
        self.confirm(); self.fixture.start_error = True
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.record()['phase'], 'uncertain')
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(len(self.fixture.posts), 2)
    def test_upload_queue_ack_is_rejected_without_start(self):
        self.confirm(); self.fixture.auto_queue = True
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, ['/server/files/upload'])
    def test_replacement_job_and_changed_remote_file_cannot_complete(self):
        self.confirm(); job = self.start(); self.fixture.job_id = 'ABCDEF'
        with self.assertRaises(ContractError): self.adapter.observe(job)
        self.fixture.job_id = 'ABC123'; self.fixture.state = 'complete'; self.fixture.history_status = 'completed'; self.fixture.tamper = True
        with self.assertRaises(ContractError): self.adapter.observe(job)
    def test_cancel_is_owned_independent_one_shot_and_confirmed(self):
        self.confirm(); job = self.start()
        self.fixture.job_id = 'ABCDEF'
        with self.assertRaises(ContractError): self.adapter.cancel(job, self.intent('cancel', '7'))
        self.assertEqual(len(self.fixture.posts), 2)
        self.fixture.job_id = 'ABC123'
        self.adapter.cancel(job, self.intent('cancel', '7'))
        with self.assertRaises(ContractError): self.adapter.cancel(job, self.intent('cancel', '8'))
        proof = self.adapter.observe(job)
        self.assertEqual(proof['print_state'], 'cancelled'); self.assertEqual(proof['history_state'], 'cancelled')
        self.assertEqual(self.fixture.posts.count('/printer/print/cancel'), 1)
    def test_mutation_gates_and_private_origin_are_required(self):
        transport = self.fixture.transport(actions=False)
        for operation in (lambda: transport.upload('helix-orca-v1-'+'a'*32+'-'+'b'*32+'.gcode', b'fixture'), lambda: transport.start('bad'), transport.cancel):
            with self.assertRaises(ContractError): operation()
        self.assertEqual(self.fixture.posts, [])
        for origin, host in (('http://127.0.0.1', '127.0.0.1'), ('https://192.168.1.2', '192.168.1.2'), ('http://192.168.1.2/foreign', '192.168.1.2')):
            with self.assertRaises(ContractError): PinnedMoonraker(origin, host, 'fixture', 'a'*64, 'b'*64, trusted_lan=True)

    def test_parity_and_expired_request_remain_closed_before_http(self):
        self.prepared['parity']['qualified'] = False
        with self.assertRaises(ContractError): self.confirm()
        self.prepared['parity']['qualified'] = True
        self.confirm(); self.adapter.now = lambda: 3700
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.gets, []); self.assertEqual(self.fixture.posts, [])
    def test_unresolved_other_request_cannot_dispatch_after_crash(self):
        self.confirm(); self.fixture.start_error = True
        with self.assertRaises(ContractError): self.start()
        original_posts = list(self.fixture.posts)
        original_directory = self.directory
        self.request = dict(self.request, request_id='9'*32)
        self.directory = self.root/self.request['request_id']; self.directory.mkdir()
        (self.directory/'fixture.gcode').write_bytes((original_directory/'fixture.gcode').read_bytes())
        self.prepared = copy.deepcopy(self.prepared)
        self.prepared['request_id'] = self.request['request_id']; self.prepared['request_sha256'] = digest(self.request)
        self.confirm()
        self.fixture.state = 'standby'; self.fixture.filename = ''; self.fixture.started = False
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, original_posts)
    def test_cancel_ambiguity_never_replays_or_unlocks_racing_completion(self):
        self.confirm(); job = self.start(); self.fixture.cancel_error = True
        with self.assertRaises(ContractError): self.adapter.cancel(job, self.intent('cancel', '7'))
        self.assertEqual(self.record()['phase'], 'cancel-uncertain')
        with self.assertRaises(ContractError): self.adapter.cancel(job, self.intent('cancel', '8'))
        self.fixture.state = 'complete'; self.fixture.history_status = 'completed'
        proof = self.adapter.observe(job)
        self.assertEqual(proof['print_state'], 'unknown'); self.assertIsNone(proof['history_job_id'])
        self.assertEqual(self.fixture.posts.count('/printer/print/cancel'), 1)
    def test_start_history_timeout_is_bounded_and_one_shot(self):
        self.confirm()
        self.fixture.history_override = dict(job_id='ABC123', filename='unrelated.gcode', start_time=10, status='in_progress')
        clock = [0]
        def mono(): clock[0] += 10; return clock[0]
        self.adapter.monotonic = mono; self.adapter.sleep = lambda _: None
        with self.assertRaisesRegex(ContractError, '30 seconds'): self.start()
        self.assertEqual(self.record()['phase'], 'uncertain')
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(len(self.fixture.posts), 2)
    def test_factory_is_default_off_and_requires_separate_typed_local_gate(self):
        deployment = dict(schema='helix-orca-v1-job-deployment/v1', origin='http://192.168.1.2', expected_host='192.168.1.2',
            expected_version='fixture-version', physical_identity=self.fixture.identity, configuration_sha256=self.fixture.config_hash,
            existing_trusted_lan_ack=True, actions_enabled=True)
        target = self.root/'factory'
        self.assertIsNone(from_config({}, target))
        self.assertIsNone(from_config({'owned_jobs': deployment}, target))
        self.assertIsNone(from_config({'owned_jobs': dict(deployment, actions_enabled=False)}, target, deployment_authorized=True))
        self.assertFalse(target.exists()); self.assertEqual(self.fixture.gets, [])
        active = from_config({'owned_jobs': deployment}, target, deployment_authorized=True)
        self.assertTrue(active.actions); self.assertTrue(active.transport.actions)
        self.assertEqual(self.fixture.gets, []); self.assertEqual(self.fixture.posts, [])
        with self.assertRaises(ContractError): from_config({'owned_jobs': deployment}, target, deployment_authorized='true')
        with self.assertRaises(ContractError): from_config({'owned_jobs': dict(deployment, injected_command='no')}, target)

    def test_malformed_baseline_and_corrupt_confirm_fail_before_upload(self):
        self.confirm()
        self.fixture.baseline = [dict(job_id='ABCDEF', filename='old.gcode', start_time=True, status='completed')]
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, [])
        self.fixture.baseline = []
        record = self.record(); record['confirm']['action'] = 'cancel'
        (self.root/'journal'/('1'*32+'.json')).write_text(json.dumps(record))
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, [])
