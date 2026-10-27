#!/usr/bin/env python3
"""Windows-local Perfectionist production generation and exact native parity.

Source-only staging is safe elsewhere; execution requires Windows. Native
reference bytes/context stay local. Stdout is fixed-key sanitized metrics.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v1_contract as c, v1_generation as g, v1_parity as p

PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
CONTEXT_SHA = '3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'
EXE_SHA = 'e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
ASSET_SHA = '15f3e750122e466389932c0c4242299ef26d8a416dc4ac0673b8864960c151dd'
SCHEMA = 'helix-orca-v1-windows-yolo-perfectionist-summary/v1'


class Refused(ValueError):
    pass


def sha(path, maximum=2*1024**3):
    path = Path(path)
    if str(path).startswith(('\\\\', '//')) or path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise Refused('local_file_missing_unsafe_or_oversized')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    sha(path, c.MAX_MESSAGE)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    with Path(path).open('xb') as stream:
        stream.write(c.canonical(value))


def validate_reference(context, native, manifest, now):
    request = c.validate_request(dict(schema='helix-orca-v1-request/v1', request_id=secrets.token_hex(16),
        origin_id=context['origin_id'], context_sha256=c.digest(context), calibration='flow_ratio_yolo',
        parameters={'pass':2}, created_at=now, expires_at=now+3600, not_applied=True), now=now)
    inputs = p.generation_inputs(request, context, PIN)
    evidence = manifest.get('evidence', [])
    if (manifest.get('schema') != 'helix-orca-v1-native-reference/v1' or manifest.get('method') != 'native_orca_ui'
            or manifest.get('imported_candidate') is not False or manifest.get('inputs_sha256') != c.digest(inputs)
            or manifest.get('source_commit') != PIN or manifest.get('runtime') != p.PINS[PIN]
            or manifest.get('artifact') != p.file_record(native) or not 3 <= len(evidence) <= 17):
        raise Refused('independent_perfectionist_reference_mismatch')
    paths = set()
    for item in evidence:
        path = Path(item['path'])
        if sha(path, p.MAX_GCODE_BYTES) != item['artifact']['sha256'] or p.file_record(path) != item['artifact']:
            raise Refused('independent_native_evidence_changed')
        paths.add(str(path.resolve()))
    if len(paths) != len(evidence):
        raise Refused('distinct_native_context_and_ui_evidence_required')
    return request, inputs


def run(args):
    if os.name != 'nt':
        raise Refused('windows_execution_required')
    context = c.validate_context(read_json(args.context))
    if c.digest(context) != CONTEXT_SHA or context['runtime'] != p.PINS[PIN]:
        raise Refused('immutable_original_context_or_runtime_mismatch')
    if (sha(args.executable) != EXE_SHA or sha(args.asset) != ASSET_SHA
            or sha(args.native, p.MAX_GCODE_BYTES) != args.native_sha256
            or sha(args.native_manifest, c.MAX_MESSAGE) != args.native_manifest_sha256):
        raise Refused('pinned_executable_asset_or_reference_changed')
    now = int(time.time())
    manifest = read_json(args.native_manifest)
    request, inputs = validate_reference(context, args.native, manifest, now)
    if str(args.output_dir).startswith(('\\\\', '//')) or args.output_dir.is_symlink():
        raise Refused('new_local_output_directory_required')
    args.output_dir.mkdir(exist_ok=False)
    source_names = ('integration/v1_contract.py', 'integration/v1_generation.py', 'integration/v1_parity.py',
                    'scripts/v1-windows-yolo-perfectionist.py', 'scripts/v1-windows-parity.py')
    source_files = {name:sha(ROOT/name) for name in source_names}
    config = dict(source_commit=PIN, runtime=p.PINS[PIN], now=now, timeout_seconds=45,
        executable=str(args.executable.resolve()), executable_sha256=EXE_SHA,
        flow_fine_asset=dict(path=str(args.asset.resolve()), sha256=ASSET_SHA, source_commit=PIN),
        native_reference=dict(manifest=dict(path=str(args.native_manifest.resolve()), sha256=args.native_manifest_sha256),
                              gcode=dict(path=str(args.native.resolve()), sha256=args.native_sha256)))
    for name, value in (('request.json', request), ('generation-config.json', config), ('source-files.json', source_files)):
        write_json(args.output_dir/name, value)
    try:
        prepared = g.generate(request, context, args.output_dir/'job', config)
    except Exception as error:
        write_json(args.output_dir/'generation-failure.json', dict(type=type(error).__name__, detail=str(error),
                   physical_actions=False, physical_readiness=False))
        raise
    report = read_json(args.output_dir/'job/parity.json')
    if prepared['parity']['report_sha256'] != c.digest(report) or (report.get('qualified') is True and not p.verify_report(report, prepared)):
        raise Refused('production_parity_revalidation_failed')
    spec = importlib.util.spec_from_file_location('perfectionist_sanitizer', ROOT/'scripts/v1-windows-parity.py')
    sanitizer = importlib.util.module_from_spec(spec); spec.loader.exec_module(sanitizer)
    summary = sanitizer.sanitized(report, prepared, manifest, source_files)
    provenance = dict(schema='helix-orca-v1-local-production-generation/v1', source_files=source_files,
        parameters={'pass':2}, context_sha256=c.digest(context), request_sha256=c.digest(request),
        inputs_sha256=c.digest(inputs), executable_sha256=EXE_SHA, public_asset_sha256=ASSET_SHA,
        native_sha256=args.native_sha256, native_manifest_file_sha256=args.native_manifest_sha256,
        prepared_sha256=c.digest(prepared), report_sha256=c.digest(report),
        invocation_sha256=sha(args.output_dir/'job/invocation.json'),
        flow_layout_sha256=sha(args.output_dir/'job/flow-layout.json'), model_3mf_sha256=sha(args.output_dir/'job/model.3mf'),
        physical_actions=False, physical_readiness=False)
    write_json(args.output_dir/'generation-provenance.json', provenance)
    summary.update(schema=SCHEMA, parameters={'pass':2}, context_sha256=c.digest(context),
                   production_generator='integration.v1_generation.generate', public_asset_sha256=ASSET_SHA,
                   executable_sha256=EXE_SHA, timeout_seconds=45, generation_provenance_sha256=c.digest(provenance))
    if len(c.canonical(summary)) > 65536:
        raise Refused('summary_too_large')
    write_json(args.output_dir/'summary.json', summary)
    return summary


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('invalid_cli_arguments')


def digest_arg(value):
    if re.fullmatch('[a-f0-9]{64}', value) is None:
        raise Refused('invalid_reference_digest')
    return value


def main():
    try:
        parser = Parser(description=__doc__)
        for name in ('context','executable','asset','native','native-manifest','output-dir'):
            parser.add_argument('--'+name, type=Path, required=True)
        for name in ('native-sha256','native-manifest-sha256'):
            parser.add_argument('--'+name, type=digest_arg, required=True)
        result = run(parser.parse_args())
        print(c.canonical(result).decode())
        return 0 if result['qualified'] else 2
    except Exception as error:
        code = str(error) if isinstance(error, Refused) else error.code if isinstance(error, g.GenerationBlocked) else 'local_production_generation_failed'
        print(json.dumps(dict(schema=SCHEMA, success=False, qualified=False, failure=code,
                              physical_actions=False, physical_readiness=False), sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
