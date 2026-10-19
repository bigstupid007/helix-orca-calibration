"""Bounded isolated companion qualification; never a product worker.

Preparation uses the actual offline coordinator and stock generator. Completion
is an explicitly synthetic UI fixture. No printer transport is constructed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
from decimal import Decimal

MARKER_SHA256 = '5bc7b6c9412068f0bf1b536376c319fb7c572ce29912aa6983b1c24d1496e2fa'
ORIGINAL_SHA256 = '3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def ordinary(path, exists=True):
    path = Path(path)
    require(path.is_absolute() and not str(path).startswith(('\\\\', '//')), 'local_absolute_path_required')
    for parent in (path, *path.parents):
        if parent.exists() or parent.is_symlink():
            info = parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'linked_or_reparse_path_refused')
    return path.resolve(strict=exists)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('op', choices=['prepare', 'result-simulation', 'readback'])
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = ordinary(args.root)
    local = os.environ.get('LOCALAPPDATA')
    require(local is not None, 'local_appdata_unavailable')
    expected = ordinary(Path(local) / 'HelixOrcaCalibration/v1-qualification')
    require(root == expected, 'wrong_qualification_root')
    marker = ordinary(root / 'data/.helix-orca-v1-qualification')
    require(marker.is_file() and marker.stat().st_size <= 4096
            and hashlib.sha256(marker.read_bytes()).hexdigest() == MARKER_SHA256, 'marker_identity_mismatch')
    storage = ordinary(root / 'data/orca_plugins/plugin_data/helix_calibration/v1')
    require(storage.is_dir() and storage.is_relative_to(root), 'wrong_companion_storage')
    checkout = ordinary(args.checkout)
    require(checkout.is_dir() and checkout.is_relative_to(root / 'runtime-lifecycle')
            and checkout.name == 'checkout', 'wrong_reviewed_checkout')
    manifest_path = ordinary(checkout / 'bundle-manifest.json')
    require(manifest_path.stat().st_size <= 1048576, 'source_manifest_oversized')
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get('schema') == 'helix-orca-v1-windows-lifecycle-input/v1'
            and isinstance(manifest.get('files'), dict), 'source_manifest_invalid')
    for name, expected_hash in manifest['files'].items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'source_path_invalid')
        path = ordinary(checkout / relative)
        require(path.is_relative_to(checkout) and path.is_file() and path.stat().st_size <= 1048576
                and hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash, 'reviewed_source_changed')
    sys.path.insert(0, str(checkout))
    from integration.v1_contract import canonical, digest, validate_context
    from integration.v1_runtime import atomic_json, read_json
    work = root / 'companion-workflow-r8'

    def load(path):
        path = ordinary(path)
        require(path.is_relative_to(root), 'read_outside_qualification_root')
        return read_json(path)

    def write(path, value):
        path = ordinary(path, exists=False)
        require(path.is_relative_to(root), 'write_outside_qualification_root')
        atomic_json(path, value)

    def output(value):
        value.update(physical_actions=False, physical_readiness=False)
        print(canonical(value).decode())

    def tick():
        result = subprocess.run([sys.executable, '-I', '-S', str(checkout / 'scripts/v1-runtime.py'),
            '--storage', str(storage), '--config', str(work / 'generator.json'), '--state', str(work / 'coordinator'),
            '--offline-channel', str(work / 'offline'), '--once'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        log = ordinary(work / ('tick-' + str(time.time_ns()) + '.log'), exists=False)
        log.write_bytes(result.stdout + b'\n' + result.stderr)
        require(result.returncode == 0, 'offline_coordinator_failed')

    if args.op == 'prepare':
        context = validate_context(load(storage / 'context.json'))
        require(digest(context) == ORIGINAL_SHA256, 'immutable_original_context_mismatch')
        require(not any((storage / name).exists() for name in ('view.json', 'inbox.json', 'committed.json')),
                'unexpected_prior_job')
        ordinary(work, exists=False).mkdir(exist_ok=False)
        write(work / 'original.json', context)
        config = load(root / 'actual-flow-yolo-production-r8/generation-config.json')
        config.pop('now', None)
        write(work / 'generator.json', config)
        tick()
        offer = load(work / 'offline/context.json')
        request = {key: offer[key] for key in ('request_id', 'origin_id', 'context_sha256', 'created_at', 'expires_at')}
        request.update(schema='helix-orca-v1-request/v1', calibration='flow_ratio_yolo', parameters={'pass': 1}, not_applied=True)
        write(work / 'offline/native.json', {'request': request})
        tick()
        view = load(storage / 'view.json')
        require(view['status']['phase'] == 'review' and view['status']['prepared']['parity']['qualified'] is True,
                'production_preparation_not_qualified')
        write(work / 'prepared-view.json', view)
        write(work / 'request.json', request)
        prepared = view['status']['prepared']
        output(dict(schema='helix-orca-v1-windows-companion-preparation/v1', actual_offline_coordinator=True,
            phase='review', qualified=True, context_sha256=ORIGINAL_SHA256, request_sha256=digest(request),
            prepared_sha256=digest(prepared), parity_report_sha256=prepared['parity']['report_sha256'],
            artifact_sha256=prepared['artifact']['sha256']))
    elif args.op == 'result-simulation':
        original = load(work / 'original.json')
        require(digest(validate_context(original)) == ORIGINAL_SHA256, 'immutable_original_context_mismatch')
        request, view = load(work / 'request.json'), load(work / 'prepared-view.json')
        prepared = view['status']['prepared']
        current = validate_context(load(storage / 'context.json'))
        require(digest(current) != ORIGINAL_SHA256, 'perform_actual_isolated_profile_switch_first')
        require(not any((storage / name).exists() for name in ('inbox.json', 'committed.json', 'receipt.json')),
                'existing_result_refused')
        job = 'synthetic-ui-review-no-printer'
        proof = dict(job_id=job, file_sha256=prepared['artifact']['sha256'], print_state='complete', history_state='completed',
                     history_job_id=job, history_file_sha256=prepared['artifact']['sha256'])
        value = float(Decimal(original['effective']['filament_flow_ratio']))
        result = dict(schema='helix-orca-v1-result/v1', request_id=request['request_id'], origin_id=request['origin_id'],
            context_sha256=request['context_sha256'], prepared_sha256=digest(prepared), job_id=job,
            completion_sha256=digest(proof), setting='filament_flow_ratio', value=value, not_applied=True)
        view['status'].update(phase='delivered', message='UI review simulation only. No printer was contacted; this retained result is NOT APPLIED.', job_id=job)
        view['result'] = None
        write(storage / 'view.json', view)
        write(storage / 'inbox.json', dict(result=result, request=request, prepared=prepared, completion=proof))
        write(work / 'synthetic-result.json', result)
        output(dict(schema='helix-orca-v1-windows-companion-result-simulation/v1', synthetic_completion=True,
            original_context_sha256=ORIGINAL_SHA256, current_context_sha256=digest(current),
            expected_result_sha256=digest(result), not_applied=True))
    else:
        committed, receipt = load(storage / 'committed.json'), load(storage / 'receipt.json')
        expected_result = load(work / 'synthetic-result.json')
        current = validate_context(load(storage / 'context.json'))
        require(committed['result'] == expected_result and receipt['result'] == expected_result
                and receipt['result_sha256'] == digest(expected_result), 'result_or_receipt_mismatch')
        require(digest(committed['original']) == ORIGINAL_SHA256 and digest(current) != ORIGINAL_SHA256,
                'original_or_current_binding_mismatch')
        output(dict(schema='helix-orca-v1-windows-companion-readback/v1', synthetic_completion=True, origin_bound=True,
            committed_before_receipt=True, result_sha256=digest(expected_result),
            original_context_sha256=digest(committed['original']), current_context_sha256=digest(current), not_applied=True))


if __name__ == '__main__':
    main()
