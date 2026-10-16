#!/usr/bin/env python3
"""Verify or promote a complete candidate-bound, isolated beta.9 capture."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('communication_qualification', ROOT / 'scripts/temperature-communication-qualify.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(directory):
    root = Path(directory).resolve(strict=True)
    report = json.loads((root / 'report.json').read_text())
    if report.get('container_network') != 'none' or report.get('dependency_image') != q.accepted.IMAGE:
        raise ValueError('Native isolation identity mismatch')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', report.get('dependency_image_id', '')):
        raise ValueError('Missing executed dependency image digest')
    runtime = report.get('runtime', {})
    for key, value in {'tag': q.beta9.TAG, 'source_commit': q.beta9.SOURCE_COMMIT,
                       'binary_sha256': q.beta9.ARTIFACT_BINARY_SHA256,
                       'artifact_archive_sha256': q.beta9.ARTIFACT_ARCHIVE_SHA256,
                       'release_sha256': q.beta9.RELEASE_SHA256}.items():
        if runtime.get(key) != value:
            raise ValueError('Pinned native runtime mismatch: ' + key)
    if report.get('accepted_baseline') != q.generator.verify_baseline():
        raise ValueError('Accepted shell baseline mismatch')
    if report.get('qualification_sources') != q.qualification_source_hashes():
        raise ValueError('Capture does not match current qualification source')
    cache = q.generator.default_output().parent / 'evidence-verification'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=cache) as temp:
        fixture = q.make_fixture(Path(temp)) / 'orcacal'
        if report.get('fixture_files') != q.file_hashes(fixture):
            raise ValueError('Capture does not match generated candidate bytes')
    expected_rows = [{'assertions': list(q.EXPECTED_ASSERTIONS), 'dpi': dpi,
                      'label': label, 'layout': layout, 'result': 'PASS',
                      'viewport': f'{width}x{height}'}
                     for label, width, height, layout, dpi in q.accepted.VIEWPORTS]
    if report.get('results') != expected_rows:
        raise ValueError('Incomplete or failing native viewport matrix')
    if report.get('test_envelope') != q.VALID_ENVELOPE or report.get('test_ack') != q.VALID_ACK:
        raise ValueError('Capture fixture identity mismatch')
    expected_clock = dict(q.SYNTHETIC_CLOCK, wrapper_sha256=report['fixture_files']['main.lua'])
    if report.get('clock_fixture') != expected_clock:
        raise ValueError('Synthetic clock prerequisite must be disclosed and bound')
    labels = [entry[0] for entry in q.accepted.VIEWPORTS]
    screenshots = {f'{label}/{name}.png' for label in labels
                   for name in ['baseline-home', 'waiting', 'returned']}
    storage = {f'{label}/config/plugin-data/orcacal.json' for label in labels}
    if set(report.get('screenshots', {})) != screenshots or set(report.get('storage', {})) != storage:
        raise ValueError('Incomplete native artifact inventory')
    for kind in ['screenshots', 'storage']:
        for name, expected in report[kind].items():
            path = root / name
            if path.is_symlink() or not path.resolve().is_relative_to(root) or digest(path) != expected:
                raise ValueError('Native artifact hash/path mismatch: ' + name)
    result = dict(q.VALID_ACK, schema='helix-orca-temperature-selection/v1')
    for name in storage:
        state = json.loads((root / name).read_text()).get('session', {})
        if (state.get('request') != q.VALID_REQUEST
                or state.get('lease') != q.VALID_ENVELOPE['lease']
                or state.get('result') != result
                or state.get('acknowledged') is not True or state.get('state') != 'returned'):
            raise ValueError('Native storage does not prove the exact selected result/ACK')
    return report


def promote(source, destination):
    report = verify(source)
    target = Path(destination)
    if target.exists():
        raise ValueError('Promotion destination already exists')
    target.mkdir(parents=True)
    for name in ['report.json', *report['screenshots'], *report['storage']]:
        output = target / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(source) / name, output)
    verify(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('verify'); check.add_argument('directory', type=Path)
    promotion = sub.add_parser('promote'); promotion.add_argument('source', type=Path); promotion.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.command == 'promote':
        promote(args.source, args.destination)
        print('Complete isolated native evidence promoted and verified.')
    else:
        verify(args.directory)
        print('Candidate, runtime, eleven viewports, 33 frames and exact results verified.')


if __name__ == '__main__':
    main()
