"""Artifact-verifier fixtures are synthetic; these tests make no native UI claim."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'communication_evidence_tests', ROOT / 'scripts/temperature-communication-evidence.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
q = e.q


class CommunicationEvidenceVerifierTests(unittest.TestCase):
    def fixture(self, root):
        generated = root / 'fixture'
        generated.mkdir()
        plugin = q.make_fixture(generated) / 'orcacal'
        report = {
            'container_network': 'none', 'dependency_image': q.accepted.IMAGE,
            'dependency_image_id': 'sha256:' + '1' * 64,
            'runtime': {
                'tag': q.beta9.TAG, 'source_commit': q.beta9.SOURCE_COMMIT,
                'binary_sha256': q.beta9.ARTIFACT_BINARY_SHA256,
                'artifact_archive_sha256': q.beta9.ARTIFACT_ARCHIVE_SHA256,
                'release_sha256': q.beta9.RELEASE_SHA256,
            },
            'accepted_baseline': q.generator.verify_baseline(),
            'qualification_sources': q.qualification_source_hashes(),
            'fixture_files': q.file_hashes(plugin),
            'clock_fixture': dict(q.SYNTHETIC_CLOCK, wrapper_sha256=q.file_hashes(plugin)['main.lua']),
            'test_request': q.VALID_REQUEST, 'test_envelope': q.VALID_ENVELOPE,
            'test_ack': q.VALID_ACK,
            'results': [
                {'assertions': list(q.EXPECTED_ASSERTIONS), 'dpi': dpi,
                 'label': label, 'layout': layout, 'result': 'PASS',
                 'viewport': f'{width}x{height}'}
                for label, width, height, layout, dpi in q.accepted.VIEWPORTS],
            'screenshots': {}, 'storage': {},
        }
        for label, *_ in q.accepted.VIEWPORTS:
            for name in ('baseline-home', 'waiting', 'returned'):
                relative = f'{label}/{name}.png'
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'synthetic verifier fixture; not native evidence')
                report['screenshots'][relative] = e.digest(path)
            relative = f'{label}/config/plugin-data/orcacal.json'
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'session': {
                'request': q.VALID_REQUEST, 'lease': q.VALID_ENVELOPE['lease'],
                'result': dict(q.VALID_ACK, schema='helix-orca-temperature-selection/v1'),
                'acknowledged': True, 'state': 'returned',
            }}))
            report['storage'][relative] = e.digest(path)
        self.write(root, report)
        return report

    def write(self, root, report):
        (root / 'report.json').write_text(json.dumps(report))

    def test_complete_bound_inventory_and_lease_pass_verifier(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertEqual(e.verify(root)['results'][0]['result'], 'PASS')

    def test_source_mutation_fails_snapshot_guard(self):
        original = q.qualification_source_hashes()
        changed = dict(original)
        changed['scripts/temperature-communication-qualify.py'] = '0' * 64
        with patch.object(q, 'qualification_source_hashes', return_value=changed):
            with self.assertRaises(q.QualificationError):
                q.verify_source_snapshot(original)

    def test_stale_sources_synthetic_clock_omission_and_partial_matrix_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = self.fixture(root)
            mutations = []
            report = copy.deepcopy(original)
            report['qualification_sources']['scripts/helix_dev.py'] = '0' * 64
            mutations.append(report)
            report = copy.deepcopy(original)
            report.pop('clock_fixture')
            mutations.append(report)
            report = copy.deepcopy(original)
            report['results'].pop()
            mutations.append(report)
            report = copy.deepcopy(original)
            report['test_envelope']['lease']['expires_eventtime'] += 1
            mutations.append(report)
            for report in mutations:
                with self.subTest(fields=set(report)):
                    self.write(root, report)
                    with self.assertRaises(ValueError):
                        e.verify(root)

    def test_tampered_frame_and_correlated_storage_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.fixture(root)
            name = next(iter(report['screenshots']))
            (root / name).write_bytes(b'changed')
            with self.assertRaises(ValueError):
                e.verify(root)
            report['screenshots'][name] = e.digest(root / name)
            storage = next(iter(report['storage']))
            state = json.loads((root / storage).read_text())
            state['session']['result']['value'] = 200
            (root / storage).write_text(json.dumps(state))
            report['storage'][storage] = e.digest(root / storage)
            self.write(root, report)
            with self.assertRaises(ValueError):
                e.verify(root)
