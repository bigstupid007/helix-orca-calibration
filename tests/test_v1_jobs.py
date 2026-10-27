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

from integration.v1_contract import (CALIBRATIONS, ORCA_ARCHIVE_SHA256_V2,
    ORCA_EXECUTABLE_SHA256_V2, ORCA_RUNTIME_V2, ORCA_SOURCE_V2,
    ORCA_UPSTREAM_JOBS_V2, ORCA_UPSTREAM_RUN_V2, V2_DEFAULTS,
    V2_QUALIFICATION_CONTEXTS, V2_QUALIFICATION_PARAMETER_CASES,
    ContractError, DEFAULTS, digest, validate_request_v2)
from integration.v1_fit import HELIXPRINT_VERSION, HELIXSCREEN_COMMIT
from integration.v1_jobs import (IDENTITY_V2, OwnedJobAdapter, PinnedMoonraker,
    current_candidate_verifier, from_config, retire_predispatch_rejection)
from integration.v1_runtime import read_json
from integration.v1_transport import NoRedirect


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def current_build_qualification():
    coverage = [dict(context=context, parameter_case=parameter_case,
                     case_sha256=sha(context + ':' + parameter_case))
                for context in V2_QUALIFICATION_CONTEXTS
                for parameter_case in V2_QUALIFICATION_PARAMETER_CASES]
    routes = {}
    for calibration in CALIBRATIONS:
        routes[calibration] = dict(qualified=True,
            route_id=('stock-cli-recipe-v2' if calibration in ('temperature', 'flow_ratio_yolo')
                      else 'native-engine-v2'),
            case_count=len(coverage), cases_sha256=digest(coverage),
            coverage=copy.deepcopy(coverage),
            final_slice_path=['Print.process', 'Print.export_gcode'])
    return dict(schema='helix-orca-v1-build-qualification/v2',
        source_commit=ORCA_SOURCE_V2, runtime=ORCA_RUNTIME_V2,
        platform='SYNTHETIC UNIT FIXTURE; NEVER QUALIFICATION',
        distribution=dict(archive_sha256=ORCA_ARCHIVE_SHA256_V2,
                          executable_sha256=ORCA_EXECUTABLE_SHA256_V2),
        upstream=dict(run_id=ORCA_UPSTREAM_RUN_V2, overall_conclusion='failure',
            sole_failed_job='build_macos_arch (arm64) / Check Cache',
            exact_jobs={name: dict(job_id=job_id, conclusion='success')
                        for name, job_id in ORCA_UPSTREAM_JOBS_V2.items()}),
        adapter=dict(sha256='a' * 64), resources_sha256='b' * 64,
        routes=routes, evidence_sha256='c' * 64, qualified=True)


class PrinterFixture:
    def __init__(self):
        self.config = {'printer': {'kinematics': 'corexy'},
                       'stepper_x': {'position_min': 0., 'position_max': 300.},
                       'stepper_y': {'position_min': 0., 'position_max': 300.},
                       'stepper_z': {'position_min': -5., 'position_max': 290.},
                       'extruder': {'max_temp': 280., 'nozzle_diameter': .4},
                       'heater_bed': {'max_temp': 110.},
                       'mcu': {'serial': 'fixture-only-mcu'},
                       'mcu toolhead': {'canbus_uuid': 'fixture-toolhead'},
                       'gcode_macro print_start': {'gcode': 'G28\nM190 S{params.BED_TEMP}\nM109 S{params.EXTRUDER_TEMP}'},
                       'gcode_macro print_end': {'gcode': 'M104 S0\nM140 S0\nM84'}}
        self.identity = sha(dict(schema='helix-orca-physical-identity/v2', mcus=[
            dict(section='mcu', kind='serial', identity='fixture-only-mcu'),
            dict(section='mcu toolhead', kind='canbus_uuid', identity='fixture-toolhead')], macs=['fixture-mac']))
        self.config_hash = sha(self.config)
        self.files = {}; self.filename = ''; self.state = 'standby'; self.event = 1
        self.job_id = 'ABC123'; self.start_time = 10; self.history_status = 'in_progress'
        self.history_override = None; self.baseline = []; self.queue = []; self.started = False
        self.posts = []; self.gets = []; self.upload_fields = None
        self.progress = .25; self.print_duration = 100; self.total_duration = 120; self.sd_path_override = None; self.sd_active = False
        self.tamper = False; self.start_error = False; self.cancel_error = False; self.auto_queue = False
        self.analysis_status = 'ready'; self.analysis_override = None; self.modified = 42.5
        self.helix_version = HELIXPRINT_VERSION; self.file_analysis_available = True
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
                if self.path == '/server/helix/status':
                    return self.response(dict(enabled=True, version=fixture.helix_version, api=2,
                        features=dict(file_analysis=dict(version=1, available=fixture.file_analysis_available,
                            enabled=fixture.file_analysis_available, reason=None if fixture.file_analysis_available else 'module_missing'))))
                if p.path == '/server/helix/analysis':
                    name = q['filename'][0]
                    if fixture.analysis_status != 'ready': return self.response(dict(filename=name, status=fixture.analysis_status))
                    if name not in fixture.files: return self.response({}, 404)
                    record = fixture.analysis_override or dict(schema=1, filename=name,
                        file_size=len(fixture.files[name]), file_mtime=fixture.modified,
                        bounds=dict(print=dict(min=[1.,1.,.2], max=[20.,20.,5.]),
                                    travel=dict(min=[0.,0.,.2], max=[50.,220.,5.]),
                                    max_hotend_temp=230., max_bed_temp=60.),
                        header=dict(printer_model='Fixture CoreXY', nozzle_diameters=[.4]),
                        tools=[dict(tool=0)])
                    return self.response(dict(filename=name, status='ready', analysis=record))
                if self.path == '/server/job_queue/status': return self.response(dict(queued_jobs=fixture.queue, queue_state='ready'))
                if self.path in ('/printer/objects/query?print_stats', '/printer/objects/query?print_stats&virtual_sdcard'):
                    fixture.event += 1
                    return self.response(dict(eventtime=fixture.event, status=dict(print_stats=dict(state=fixture.state, filename=fixture.filename, print_duration=fixture.print_duration,total_duration=fixture.total_duration),virtual_sdcard=dict(progress=fixture.progress,file_path=fixture.sd_path_override or '/fixture/gcodes/'+fixture.filename,is_active=fixture.sd_active))))
                if p.path == '/server/files/metadata':
                    name = q['filename'][0]
                    if name not in fixture.files: return self.response({}, 404)
                    return self.response(dict(job_id=fixture.job_id if fixture.started else None,
                        print_start_time=fixture.start_time if fixture.started else None,
                        size=len(fixture.files[name]), modified=fixture.modified))
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
        result = PinnedMoonraker('http://192.168.1.2', '192.168.1.2', 'fixture-version', self.identity,
            self.config_hash, identity_algorithm=IDENTITY_V2, trusted_lan=True, actions=actions)
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
        data = b'; SYNTHETIC OFFLINE HTTP FIXTURE\nG90\nM83\nPRINT_START BED_TEMP=60 EXTRUDER_TEMP=230\nM104 S230\nG1 Z0.2\nG1 X1 Y1 E1 F1200\nPRINT_END\n'; (self.directory/'fixture.gcode').write_bytes(data)
        self.prepared = {k: self.request[k] for k in ('request_id', 'origin_id', 'context_sha256', 'calibration', 'parameters')}
        self.prepared.update(schema='helix-orca-v1-prepared/v1', request_sha256=digest(self.request), artifact=dict(name='fixture.gcode', size=len(data), sha256=hashlib.sha256(data).hexdigest()),
            generator=dict(build='fixture', route='fixture'), parity=dict(qualified=True, report_sha256='4'*64, reason='Synthetic verifier injection only'), not_applied=True)
        self.machine_inputs = dict(printer=dict(saved=dict(name='Synthetic printer', config={'machine': 'fixture'}), edited=dict(name='Synthetic printer', config={'machine': 'fixture'})), nozzle_mm=0.4)
        self.machine = digest(self.machine_inputs)
        self.qualification = dict(schema='helix-orca-v1-printer-target-qualification/v2',
            target_id='fixture-voron', deployment_mode='physical', identity_algorithm=IDENTITY_V2,
            physical_identity=self.fixture.identity, configuration_sha256=self.fixture.config_hash,
            orca_machine_sha256=self.machine, moonraker_version='fixture-version',
            helixscreen_commit=HELIXSCREEN_COMMIT, helixprint_version=HELIXPRINT_VERSION,
            file_analysis_schema=1, fit_checker_version=1, printer_safety_reviewed=True,
            review_reference='SYNTHETIC HTTP FIXTURE ONLY; NOT A PHYSICAL QUALIFICATION')
        self.report = dict(synthetic_http_fixture_only=True, inputs=dict(profiles=dict(printer=self.machine_inputs['printer']), nozzle_mm=0.4), candidate_invariants=dict(
            macro_semantics=dict(accepted_abi_signature=True, hardware_abi_qualified=False, physical_readiness=False), physical_readiness=False))
        (self.directory/'parity.json').write_text(json.dumps(self.report))
        self.prepared['parity']['report_sha256'] = digest(self.report)
        self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/'journal', orca_machine_sha256=self.machine, physical_qualification=self.qualification, actions=True, now=lambda: 100)
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
        default_adapter = OwnedJobAdapter(self.fixture.transport(), self.root/'disabled', orca_machine_sha256=self.machine, physical_qualification=self.qualification, now=lambda: 100)
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
    def test_monitor_uses_fresh_same_job_stats_and_never_fabricates_progress(self):
        self.confirm();job=self.start()
        self.assertIsNone(self.adapter.monitor(job))
        self.adapter.observe(job)
        self.assertEqual(self.adapter.monitor(job),dict(elapsed_s=120.,progress=.25))
        self.assertIsNone(self.adapter.monitor(dict(job,job_id='foreign')))
        self.fixture.progress=1.1
        self.adapter.observe(job)
        self.assertEqual(self.adapter.monitor(job),dict(elapsed_s=120.,progress=None))
        self.fixture.progress=.5;self.fixture.sd_path_override='/fixture/gcodes/foreign.gcode'
        self.adapter.observe(job)
        self.assertIsNone(self.adapter.monitor(job)['progress'])
        self.fixture.total_duration=-1
        self.adapter.observe(job)
        self.assertIsNone(self.adapter.monitor(job)['elapsed_s'])
        self.fixture.filename='foreign.gcode'
        with self.assertRaises(ContractError):self.adapter.observe(job)
        self.assertIsNone(self.adapter.monitor(job))

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
    def test_completed_prior_job_is_idle_only_with_matching_terminal_history(self):
        self.confirm()
        prior = dict(job_id='ABCDEF', filename='prior.gcode', start_time=4,
                     end_time=9, status='completed')
        self.fixture.state = 'complete'; self.fixture.filename = 'prior.gcode'
        self.fixture.baseline = [prior]
        job = self.start()
        self.assertEqual(job['job_id'], 'ABC123')

    def test_completed_prior_job_requires_inactive_sd_and_exact_history(self):
        cases = (
            (dict(job_id='ABCDEF', filename='other.gcode', start_time=4,
                  end_time=9, status='completed'), False),
            (dict(job_id='ABCDEF', filename='prior.gcode', start_time=4,
                  end_time=9, status='in_progress'), False),
            (dict(job_id='ABCDEF', filename='prior.gcode', start_time=4,
                  end_time=4, status='completed'), False),
            (dict(job_id='ABCDEF', filename='prior.gcode', start_time=4,
                  end_time=9, status='completed'), True),
        )
        for index, (prior, active) in enumerate(cases):
            with self.subTest(index=index):
                adapter = OwnedJobAdapter(self.fixture.transport(),
                    self.root/('terminal-'+str(index)),
                    orca_machine_sha256=self.machine,
                    physical_qualification=self.qualification, actions=True,
                    now=lambda: 100)
                adapter.confirm(self.request, self.prepared, self.directory,
                    self.intent('confirm', '5'))
                self.fixture.state = 'complete'; self.fixture.filename = 'prior.gcode'
                self.fixture.baseline = [prior]; self.fixture.sd_active = active
                posts = list(self.fixture.posts)
                with self.assertRaises(ContractError):
                    adapter.start(self.request, self.prepared, self.directory,
                        self.intent('start', '6'))
                self.assertEqual(self.fixture.posts, posts)

    def test_predispatch_readiness_rejection_is_proven_even_after_rebind(self):
        self.confirm()
        self.fixture.state = 'complete'; self.fixture.filename = 'prior.gcode'
        self.fixture.baseline = []
        with self.assertRaises(ContractError):
            self.start()
        record = self.record()
        self.assertEqual(record['phase'], 'confirmed')
        self.assertIsNone(record['start'])
        self.assertIsNone(record['job'])
        self.assertEqual(self.fixture.posts, [])
        changed = copy.deepcopy(self.qualification)
        changed['review_reference'] += '; rebound package'
        recovered = OwnedJobAdapter(self.fixture.transport(), self.root/'journal',
            orca_machine_sha256=self.machine, physical_qualification=changed,
            actions=True, now=lambda: 100)
        self.assertTrue(recovered.predispatch_rejected(
            self.request, self.prepared, self.intent('start', '6')))
        coordinator = self.root/'coordinator.json'
        state = dict(schema='helix-orca-v1-journal/v1', phase='uncertain',
            request=self.request, prepared=self.prepared,
            pending_start_intent=self.intent('start', '6'), job=None,
            sequence=4, message='Start outcome is uncertain')
        coordinator.write_text(json.dumps(state))
        self.assertTrue(retire_predispatch_rejection(recovered, coordinator))
        retired = read_json(coordinator)
        self.assertEqual(retired['phase'], 'blocked')
        self.assertEqual(retired['sequence'], 5)
        self.assertIn('before upload', retired['message'])
    def test_upload_readback_difference_blocks_start_and_restart_replay(self):
        self.confirm(); self.fixture.tamper = True
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.posts, ['/server/files/upload']); self.assertEqual(self.record()['phase'], 'uncertain')
        recovered = OwnedJobAdapter(self.fixture.transport(), self.root/'journal', orca_machine_sha256=self.machine, physical_qualification=self.qualification, actions=True, now=lambda: 100)
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
        self.fixture.job_id = 'ABC123'; self.fixture.queue = [dict(job_id='foreign')]
        with self.assertRaises(ContractError): self.adapter.cancel(job, self.intent('cancel', '7'))
        self.assertEqual(len(self.fixture.posts), 2)
        self.fixture.queue = []
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
        (self.directory/'parity.json').write_bytes((original_directory/'parity.json').read_bytes())
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
        deployment = dict(schema='helix-orca-v1-job-deployment/v2', target_id='fixture-voron', deployment_mode='physical',
            origin='http://192.168.1.2', expected_host='192.168.1.2', identity_algorithm=IDENTITY_V2,
            expected_version='fixture-version', physical_identity=self.fixture.identity, configuration_sha256=self.fixture.config_hash, orca_machine_sha256=self.machine,
            physical_qualification=self.qualification,
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

        ad5x = dict(schema='helix-orca-v1-job-deployment/v2', target_id='flashforge-ad5x-04',
            deployment_mode='generation-only', orca_machine_sha256='a'*64, actions_enabled=False)
        self.assertIsNone(from_config({'owned_jobs': ad5x}, self.root/'ad5x', deployment_authorized=True))
        self.assertFalse((self.root/'ad5x').exists())
        with self.assertRaisesRegex(ContractError, 'never enable'):
            from_config({'owned_jobs': dict(ad5x, actions_enabled=True)}, self.root/'ad5x', deployment_authorized=True)

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

    def test_no_voron_macro_abi_is_required_for_ad5x_shaped_gcode(self):
        data = (b'; generated by OrcaSlicer\nM190 S60\nM109 S220\nG90\nM83\n'
                b'G1 Z2 F6000\nG1 X50 Y220 Z0.25 F4800\nG1 X70 E3 F900\n'
                b'G1 E-3 F3600\nG0 X50 Y50 F30000\nM104 S0\n')
        (self.directory/'fixture.gcode').write_bytes(data)
        self.prepared['artifact'].update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        self.report['candidate_invariants'] = {'physical_readiness': False}
        self.prepared['parity']['report_sha256'] = digest(self.report)
        (self.directory/'parity.json').write_text(json.dumps(self.report))
        self.confirm(); job = self.start()
        self.assertEqual(job['file_sha256'], hashlib.sha256(data).hexdigest())
        self.assertNotIn('PRINT_START', data.decode()); self.assertNotIn('PRINT_END', data.decode())

    def test_shared_v2_contract_can_inject_request_and_candidate_validation(self):
        request = dict(schema='synthetic-request-v2', request_id='a'*32,
            origin_id='b'*32, expires_at=999)
        prepared = dict(schema='synthetic-prepared-v2', request_id=request['request_id'],
            build_qualification_sha256='c'*64)
        directory = self.root/request['request_id']; directory.mkdir()
        data = b'M190 S60\nM109 S220\nG90\nG1 X2 Y2 Z.2 E1\nM104 S0\n'
        (directory/'v2.gcode').write_bytes(data)
        calls=[]
        def request_validator(value, now):
            calls.append(('request',now)); self.assertIs(value,request)
        def candidate_verifier(req, value, path, machine):
            calls.append(('candidate',machine)); self.assertIs(req,request); self.assertIs(value,prepared)
            return (path/'v2.gcode').read_bytes()
        adapter=OwnedJobAdapter(self.fixture.transport(),self.root/'v2-journal',
            orca_machine_sha256=self.machine,physical_qualification=self.qualification,
            candidate_verifier=candidate_verifier,request_validator=request_validator,
            actions=True,now=lambda:100)
        def intent(action,token):
            return dict(schema='helix-orca-v1-intent/v1',request_id=request['request_id'],
                origin_id=request['origin_id'],prepared_sha256=digest(prepared),action=action,
                intent_id=token*32)
        adapter.confirm(request,prepared,directory,intent('confirm','5'))
        job=adapter.start(request,prepared,directory,intent('start','6'))
        self.assertEqual(job['file_sha256'],hashlib.sha256(data).hexdigest())
        self.assertGreaterEqual(calls.count(('request',100)),3)
        self.assertEqual(sum(1 for kind,_ in calls if kind=='candidate'),2)

    def test_current_v2_candidate_uses_build_route_and_reviewed_machine_without_parity(self):
        build = current_build_qualification()
        request = dict(schema='helix-orca-v1-request/v2', request_id='a'*32,
            origin_id='b'*32, context_sha256='c'*64, calibration='retraction',
            parameters=copy.deepcopy(V2_DEFAULTS['retraction']), created_at=100, expires_at=200)
        directory = self.root/request['request_id']; directory.mkdir()
        data = (b'; SYNTHETIC CURRENT CANDIDATE; NOT QUALIFICATION\nG90\nM83\n'
                b'M190 S60\nM109 S220\nG1 X50 Y50 Z0.2 E1 F1200\nM104 S0\n')
        artifact = directory/'current.gcode'; artifact.write_bytes(data)
        prepared = {key: request[key] for key in
                    ('request_id','origin_id','context_sha256','calibration','parameters')}
        prepared.update(schema='helix-orca-v1-prepared/v2', request_sha256=digest(request),
            artifact=dict(name=artifact.name,size=len(data),sha256=hashlib.sha256(data).hexdigest()),
            generator=dict(source_commit=ORCA_SOURCE_V2,route='native-engine-v2',
                executable_sha256=ORCA_EXECUTABLE_SHA256_V2,
                qualification_sha256=digest(build),machine_sha256=self.machine),
            processing=dict(error_code=0,warnings=[],status='ready'))
        closure_checks=[]
        verifier = current_candidate_verifier(build, lambda: closure_checks.append(True) or build)
        adapter = OwnedJobAdapter(self.fixture.transport(),self.root/'v2-current-journal',
            orca_machine_sha256=self.machine,physical_qualification=self.qualification,
            candidate_verifier=verifier,
            request_validator=validate_request_v2,
            actions=True,now=lambda:100)
        def intent(action,token):
            return dict(schema='helix-orca-v1-intent/v2',request_id=request['request_id'],
                origin_id=request['origin_id'],prepared_sha256=digest(prepared),action=action,
                intent_id=token*32)
        adapter.confirm(request,prepared,directory,intent('confirm','5'))
        job=adapter.start(request,prepared,directory,intent('start','6'))
        self.assertEqual(job['file_sha256'],hashlib.sha256(data).hexdigest())
        self.assertFalse((directory/'parity.json').exists())
        self.assertGreaterEqual(len(closure_checks),2)

        changed=copy.deepcopy(prepared);changed['generator']['machine_sha256']='d'*64
        fresh=self.root/'wrong-machine';fresh.mkdir()
        (fresh/artifact.name).write_bytes(data)
        before=(list(self.fixture.gets),list(self.fixture.posts))
        with self.assertRaisesRegex(ContractError,'machine/nozzle'):
            verifier(request,changed,fresh,self.machine)
        self.assertEqual(before,(self.fixture.gets,self.fixture.posts))

        changed=copy.deepcopy(prepared);changed['generator']['route']='stock-cli-recipe-v2'
        with self.assertRaisesRegex(ContractError,'route'):
            verifier(request,changed,directory,self.machine)

        different=copy.deepcopy(build);different['evidence_sha256']='d'*64
        stale=current_candidate_verifier(build,lambda:different)
        with self.assertRaisesRegex(ContractError,'Executing generator closure'):
            stale(request,prepared,directory,self.machine)

    def test_changed_machine_configuration_or_nozzle_blocks_before_http(self):
        for alteration in ('nozzle', 'printer_config', 'printer_missing'):
            report = copy.deepcopy(self.report)
            if alteration == 'nozzle': report['inputs']['nozzle_mm'] = 0.6
            elif alteration == 'printer_config': report['inputs']['profiles']['printer']['edited']['config']['machine'] = 'different'
            else: del report['inputs']['profiles']['printer']
            self.prepared['parity']['report_sha256'] = digest(report)
            (self.directory/'parity.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ContractError, 'machine/nozzle'): self.confirm()
        self.assertEqual(self.fixture.gets, []); self.assertEqual(self.fixture.posts, [])

    def test_typed_target_qualification_requires_source_api_review_and_bindings(self):
        for key, bad in (('physical_identity', 'a'*64), ('configuration_sha256', 'b'*64),
                         ('orca_machine_sha256', 'c'*64), ('identity_algorithm', 'unknown/v9'),
                         ('printer_safety_reviewed', False), ('review_reference', ''),
                         ('helixscreen_commit', '0'*40), ('helixprint_version', '1.3.0'),
                         ('file_analysis_schema', 2), ('fit_checker_version', 2),
                         ('deployment_mode', 'generation-only')):
            value = copy.deepcopy(self.qualification); value[key] = bad
            with self.subTest(key=key), self.assertRaises(ContractError):
                OwnedJobAdapter(self.fixture.transport(), self.root/'invalid', orca_machine_sha256=self.machine,
                                physical_qualification=value, actions=True)
        with self.assertRaises(ContractError):
            OwnedJobAdapter(self.fixture.transport(), self.root/'missing', orca_machine_sha256=self.machine)
        self.assertFalse((self.root/'invalid').exists())
        self.assertEqual(self.fixture.gets, []); self.assertEqual(self.fixture.posts, [])

    def test_analysis_and_generic_fit_fail_closed_before_start(self):
        cases = []
        for status in ('failed', 'disabled'):
            cases.append((status, None))
        cases.extend([
            ('ready', {'bounds': {'travel': {'min': [0.,0.,0.], 'max': [301.,2.,2.]},
                                  'max_hotend_temp': 230., 'max_bed_temp': 60.}}),
            ('ready', {'bounds': {'travel': {'min': [0.,0.,0.], 'max': [2.,2.,2.]},
                                  'max_hotend_temp': 281., 'max_bed_temp': 60.}}),
            ('ready', {'header': {'printer_model': 'AD5X', 'nozzle_diameters': [.6]}}),
        ])
        for index, (status, changes) in enumerate(cases):
            self.fixture.analysis_status = status
            if changes is not None:
                base = dict(schema=1, filename='', file_size=0, file_mtime=self.fixture.modified,
                    bounds=dict(print=dict(min=[0.,0.,0.], max=[2.,2.,2.]),
                                travel=dict(min=[0.,0.,0.], max=[2.,2.,2.]),
                                max_hotend_temp=230., max_bed_temp=60.),
                    header=dict(printer_model='Fixture', nozzle_diameters=[.4]), tools=[dict(tool=0)])
                for key, value in changes.items(): base[key] = value
                self.fixture.analysis_override = base
            self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/('fit-'+str(index)),
                orca_machine_sha256=self.machine, physical_qualification=self.qualification,
                actions=True, now=lambda:100)
            self.adapter.confirm(self.request, self.prepared, self.directory, self.intent('confirm', '5'))
            filename = read_json(self.root/('fit-'+str(index))/('1'*32+'.json'))['filename']
            if self.fixture.analysis_override:
                self.fixture.analysis_override.update(filename=filename,
                    file_size=self.prepared['artifact']['size'])
            with self.subTest(status=status, changes=changes), self.assertRaises(ContractError):
                self.adapter.start(self.request, self.prepared, self.directory, self.intent('start', '6'))
            self.assertEqual(sum(path.startswith('/printer/print/start?') for path in self.fixture.posts), 0)
            self.fixture.files.clear(); self.fixture.posts.clear(); self.fixture.analysis_override = None

    def test_analysis_record_must_match_remote_filename_size_and_mtime(self):
        for field, value in (('filename', 'foreign.gcode'), ('file_size', 1), ('file_mtime', 99.)):
            self.fixture.analysis_override = dict(schema=1, filename=value if field == 'filename' else '',
                file_size=value if field == 'file_size' else self.prepared['artifact']['size'],
                file_mtime=value if field == 'file_mtime' else self.fixture.modified,
                bounds=dict(travel=dict(min=[0.,0.,0.], max=[2.,2.,2.]), print=None,
                            max_hotend_temp=230., max_bed_temp=60.),
                header=dict(nozzle_diameters=[.4], printer_model='Fixture'), tools=[dict(tool=0)])
            self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/('identity-'+field),
                orca_machine_sha256=self.machine, physical_qualification=self.qualification,
                actions=True, now=lambda:100)
            self.adapter.confirm(self.request, self.prepared, self.directory, self.intent('confirm', '5'))
            filename = read_json(self.root/('identity-'+field)/('1'*32+'.json'))['filename']
            if field != 'filename': self.fixture.analysis_override['filename'] = filename
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.adapter.start(self.request, self.prepared, self.directory, self.intent('start', '6'))
            self.assertEqual(sum(path.startswith('/printer/print/start?') for path in self.fixture.posts), 0)
            self.fixture.files.clear(); self.fixture.posts.clear()

    def test_injected_native_warning_acknowledgement_is_exactly_bound(self):
        captured = []
        def acknowledge(request, prepared, intent, binding):
            captured.append((request, prepared, intent, binding))
            return dict(binding, schema='helix-orca-v1-fit-warning-ack/v1',
                action='acknowledge-fit-warnings')
        self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/'warning-ack',
            orca_machine_sha256=self.machine, physical_qualification=self.qualification,
            warning_acknowledger=acknowledge, actions=True, now=lambda:100)
        self.adapter.confirm(self.request, self.prepared, self.directory, self.intent('confirm', '5'))
        filename = read_json(self.root/'warning-ack'/('1'*32+'.json'))['filename']
        self.fixture.analysis_override = dict(schema=1, filename=filename,
            file_size=self.prepared['artifact']['size'], file_mtime=self.fixture.modified,
            bounds=dict(print=dict(min=[1.,1.,.2], max=[20.,20.,5.]),
                        travel=dict(min=[0.,0.,.2], max=[50.,220.,5.]),
                        max_hotend_temp=230., max_bed_temp=60.),
            header=dict(printer_model='Fixture CoreXY', nozzle_diameters=[.6]),
            tools=[dict(tool=0)])
        job = self.adapter.start(self.request, self.prepared, self.directory,
            self.intent('start', '6'))
        self.assertEqual(job['file_sha256'], self.prepared['artifact']['sha256'])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][2]['action'], 'start')
        self.assertEqual(captured[0][3]['target_id'], self.qualification['target_id'])
        self.assertEqual(captured[0][3]['warning_kinds'], ['nozzle_mismatch'])
        self.assertIsNotNone(read_json(self.root/'warning-ack'/('1'*32+'.json'))
            ['fit_evidence']['warning_acknowledgement_sha256'])

    def test_helixprint_status_is_exactly_pinned_and_available(self):
        for attribute, value in (('helix_version', '1.3.0'), ('file_analysis_available', False)):
            setattr(self.fixture, attribute, value)
            self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/('status-'+attribute),
                orca_machine_sha256=self.machine, physical_qualification=self.qualification,
                actions=True, now=lambda:100)
            self.adapter.confirm(self.request, self.prepared, self.directory, self.intent('confirm', '5'))
            with self.assertRaises(ContractError):
                self.adapter.start(self.request, self.prepared, self.directory, self.intent('start', '6'))
            self.assertEqual(sum(path.startswith('/printer/print/start?') for path in self.fixture.posts), 0)
            self.fixture.files.clear(); self.fixture.posts.clear()
            setattr(self.fixture, attribute, HELIXPRINT_VERSION if attribute == 'helix_version' else True)

    def test_qualification_digest_cannot_change_between_confirm_and_start(self):
        self.confirm()
        changed = copy.deepcopy(self.qualification); changed['review_reference'] += ' changed'
        self.adapter = OwnedJobAdapter(self.fixture.transport(), self.root/'journal', orca_machine_sha256=self.machine,
            physical_qualification=changed, actions=True, now=lambda:100)
        with self.assertRaises(ContractError): self.start()
        self.assertEqual(self.fixture.gets, []); self.assertEqual(self.fixture.posts, [])

    def test_recovery_after_durable_printing_is_read_only_idempotent_and_can_observe_cancel(self):
        self.confirm(); save = self.adapter._save
        def crash(record):
            save(record)
            if record['phase'] == 'printing': raise SystemExit('synthetic process death after durable printing')
        with patch.object(self.adapter, '_save', side_effect=crash), self.assertRaises(SystemExit): self.start()
        record = self.record(); self.assertEqual(record['phase'], 'printing'); self.assertTrue(record['ownership_confirmed'])
        before = (self.root/'journal'/('1'*32+'.json')).read_bytes()
        gets, posts = list(self.fixture.gets), list(self.fixture.posts)
        recovered = OwnedJobAdapter(self.fixture.transport(), self.root/'journal', orca_machine_sha256=self.machine,
            physical_qualification=self.qualification, actions=True, now=lambda:10000)
        job = recovered.recover(self.request, self.prepared, self.intent('start', '6'))
        self.assertEqual(recovered.recover(self.request, self.prepared, self.intent('start', '6')), job)
        self.assertEqual(self.fixture.gets, gets); self.assertEqual(self.fixture.posts, posts)
        self.assertEqual((self.root/'journal'/('1'*32+'.json')).read_bytes(), before)
        self.assertEqual(recovered.observe(job)['print_state'], 'printing')
        recovered.cancel(job, self.intent('cancel', '7'))
        self.assertEqual(recovered.observe(job)['history_state'], 'cancelled')
        self.assertEqual(sum(path.startswith('/printer/print/start?') for path in self.fixture.posts), 1)
        self.assertEqual(self.fixture.posts.count('/server/files/upload'), 1)

    def test_recovery_prejob_ambiguity_or_mismatched_intents_never_dispatches(self):
        self.assertIsNone(self.adapter.recover(self.request, self.prepared, self.intent('start', '6')))
        self.confirm()
        self.assertIsNone(self.adapter.recover(self.request, self.prepared, self.intent('start', '6')))
        self.fixture.start_error = True
        with self.assertRaises(ContractError): self.start()
        gets, posts = list(self.fixture.gets), list(self.fixture.posts)
        self.assertIsNone(self.adapter.recover(self.request, self.prepared, self.intent('start', '6')))
        with self.assertRaises(ContractError): self.adapter.recover(self.request, self.prepared, self.intent('start', '7'))
        changed = dict(self.request, context_sha256='a'*64)
        with self.assertRaises(ContractError): self.adapter.recover(changed, self.prepared, self.intent('start', '6'))
        self.assertEqual(self.fixture.gets, gets); self.assertEqual(self.fixture.posts, posts)
