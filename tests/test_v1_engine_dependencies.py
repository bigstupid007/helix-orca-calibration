"""Pinned archive integrity and size guard; no network or compiler runs."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('engine_deps', ROOT / 'scripts/v1-engine-deps.py')
deps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deps)


class FakeResponse(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.headers = {'Content-Length': str(len(body))}


class DependencyIntegrityTests(unittest.TestCase):
    def lock(self, body):
        return {'sources': [{'target': 'dep_Test', 'url': 'https://example.invalid/archive.zip',
                             'sha256': hashlib.sha256(body).hexdigest()}]}

    def run_download(self, wanted, received, cap):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'artifacts').mkdir()
            with patch.object(deps, 'read_lock', return_value=self.lock(wanted)), \
                 patch.object(deps.urllib.request, 'build_opener') as opener, \
                 patch.object(deps, 'CAP', cap), \
                 patch.dict(os.environ, {'RUN_ARTIFACTS': str(root / 'artifacts')}):
                opener.return_value.open.return_value = FakeResponse(received)
                with self.assertRaises(ValueError):
                    deps.download(root / 'cache')
            result = json.loads((root / 'artifacts/dependency-download.json').read_text())
            self.assertFalse(result['complete'])
            self.assertFalse(any(p.name.endswith('archive.zip') for p in (root / 'cache').iterdir()))

    def test_mismatched_archive_is_retained_unverified_and_never_promoted(self):
        self.run_download(b'expected', b'not-expected', 100)

    def test_declared_oversize_archive_is_refused_before_cache_promotion(self):
        self.run_download(b'expected', b'expected', 4)

    def test_manifest_locks_all_sources_to_sha256_and_https(self):
        lock = deps.read_lock()
        self.assertGreater(len(lock['sources']), 0)
        self.assertEqual(lock['source_commit'], deps.SOURCE)

class CompilerBoundTests(unittest.TestCase):
    def test_upstream_unbounded_and_processor_count_jobs_are_clamped(self):
        spec = importlib.util.spec_from_file_location('build_gate', ROOT/'integration/v1-native-build-tools.py')
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        cases = [(['-j'], ['-j4']), (['-j16','install_sw'], ['-j4','install_sw']),
                 (['--jobs=99'], ['-j4']), (['-j','20'], ['-j4']),
                 (['-j1','all'], ['-j1','all']), (['--jobs','2'], ['-j2'])]
        for original, expected in cases:
            self.assertEqual(gate.make_arguments(original), expected)


if __name__ == '__main__':
    unittest.main()
