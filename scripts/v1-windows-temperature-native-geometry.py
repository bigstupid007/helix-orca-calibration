#!/usr/bin/env python3
"""Windows-local native-Cut Temperature generation and strict native parity.

This separate helper preserves both existing qualified YOLO drivers. All full
profiles, G-code and reports stay Windows-local; stdout is fixed-key metrics.
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
from integration.v1_temperature_geometry import inspect_stl

PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
CONTEXT_SHA = '3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'
EXE_SHA = 'e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
NATIVE_SHA = '512eb13a80788bd22f928b1b073382070a7c43b5c667efd08ffcc05e550e29b7'
PARAMETERS = {'start':230, 'end':190, 'step':5, 'scale':True}
SCHEMA = 'helix-orca-v1-windows-temperature-native-geometry-summary/v1'
SOURCE_NAMES = ('integration/v1_contract.py', 'integration/v1_generation.py',
    'integration/v1_parity.py', 'integration/v1_engine.py',
    'integration/v1_temperature_geometry.py',
    'scripts/v1-windows-temperature-native-geometry.py', 'scripts/v1-windows-parity.py')


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


def digest_arg(value):
    if not isinstance(value,str) or re.fullmatch('[a-f0-9]{64}', value) is None:
        raise Refused('invalid_reference_digest')
    return value


def validate_reference(context, native, manifest, now):
    request = c.validate_request(dict(schema='helix-orca-v1-request/v1', request_id=secrets.token_hex(16),
        origin_id=context['origin_id'], context_sha256=c.digest(context), calibration='temperature',
        parameters=PARAMETERS, created_at=now, expires_at=now+3600, not_applied=True), now=now)
    inputs = p.generation_inputs(request, context, PIN)
    evidence = manifest.get('evidence', [])
    if (manifest.get('schema') != 'helix-orca-v1-native-reference/v1' or manifest.get('method') != 'native_orca_ui'
            or manifest.get('imported_candidate') is not False or manifest.get('inputs_sha256') != c.digest(inputs)
            or manifest.get('source_commit') != PIN or manifest.get('runtime') != p.PINS[PIN]
            or manifest.get('artifact') != p.file_record(native) or not 3 <= len(evidence) <= 17):
        raise Refused('independent_temperature_reference_mismatch')
    paths = set()
    for item in evidence:
        path = Path(item['path'])
        if sha(path,p.MAX_GCODE_BYTES) != item['artifact']['sha256'] or p.file_record(path) != item['artifact']:
            raise Refused('independent_native_evidence_changed')
        paths.add(str(path.resolve()))
    if len(paths) != len(evidence):
        raise Refused('distinct_native_context_and_ui_evidence_required')
    return request, inputs


def validate_geometry(context, model_path, model_sha256, receipt):
    expected = dict(schema='helix-orca-v1-native-temperature-geometry/v1', source_commit=PIN,
        calibration='temperature', context_sha256=c.digest(context), origin_id=context['origin_id'],
        parameters=PARAMETERS, nozzle_mm=context['nozzle_mm'], gcode_generated=False,
        qualified=False, not_applied=True)
    if any(c.canonical(receipt.get(k)) != c.canonical(v) for k,v in expected.items()):
        raise Refused('native_geometry_request_context_or_source_mismatch')
    if context['nozzle_mm'] != .4:
        raise Refused('retained_temperature_nozzle_mismatch')
    for key in ('request_sha256','native_metadata_sha256','build_receipt_sha256',
                'build_inputs_sha256','executable_sha256'):
        digest_arg(receipt.get(key))
    c.hex_value(receipt.get('request_id'),32)
    descriptor = receipt.get('model', {})
    if (descriptor.get('sha256') != model_sha256 or descriptor.get('source_commit') != PIN
            or descriptor.get('nozzle_mm') != context['nozzle_mm']
            or c.canonical(descriptor.get('parameters')) != c.canonical(PARAMETERS)
            or sha(model_path,32*1024**2) != model_sha256):
        raise Refused('native_geometry_model_descriptor_mismatch')
    metrics = inspect_stl(model_path)
    if receipt.get('metrics') != metrics:
        raise Refused('native_geometry_exported_metrics_mismatch')
    return dict(path=str(Path(model_path).resolve()), sha256=model_sha256,
                source_commit=PIN,nozzle_mm=context['nozzle_mm'],parameters=dict(PARAMETERS)),metrics


def run(args):
    if os.name != 'nt':
        raise Refused('windows_execution_required')
    context = c.validate_context(read_json(args.context))
    if c.digest(context) != CONTEXT_SHA or context['runtime'] != p.PINS[PIN]:
        raise Refused('immutable_original_context_or_runtime_mismatch')
    if (sha(args.executable) != EXE_SHA or args.native_sha256 != NATIVE_SHA
            or sha(args.model,32*1024**2) != args.model_sha256
            or sha(args.geometry_receipt,c.MAX_MESSAGE) != args.geometry_receipt_sha256
            or sha(args.native,p.MAX_GCODE_BYTES) != NATIVE_SHA
            or sha(args.native_manifest,c.MAX_MESSAGE) != args.native_manifest_sha256):
        raise Refused('pinned_executable_geometry_or_reference_changed')
    geometry_receipt = read_json(args.geometry_receipt)
    model,metrics = validate_geometry(context,args.model,args.model_sha256,geometry_receipt)
    now = int(time.time())
    manifest = read_json(args.native_manifest)
    request,inputs = validate_reference(context,args.native,manifest,now)
    if str(args.output_dir).startswith(('\\\\', '//')) or args.output_dir.is_symlink():
        raise Refused('new_local_output_directory_required')
    args.output_dir.mkdir(exist_ok=False)
    source_files = {name:sha(ROOT/name) for name in SOURCE_NAMES}
    config = dict(source_commit=PIN,runtime=p.PINS[PIN],now=now,timeout_seconds=45,
        executable=str(args.executable.resolve()),executable_sha256=EXE_SHA,
        temperature_model=model,
        native_reference=dict(manifest=dict(path=str(args.native_manifest.resolve()),sha256=args.native_manifest_sha256),
                              gcode=dict(path=str(args.native.resolve()),sha256=NATIVE_SHA)))
    for name,value in (('request.json',request),('generation-config.json',config),('source-files.json',source_files)):
        write_json(args.output_dir/name,value)
    try:
        prepared = g.generate(request,context,args.output_dir/'job',config)
    except Exception as error:
        write_json(args.output_dir/'generation-failure.json',dict(type=type(error).__name__,detail=str(error),
                   physical_actions=False,physical_readiness=False))
        raise
    report = read_json(args.output_dir/'job/parity.json')
    if prepared['parity']['report_sha256'] != c.digest(report) or (report.get('qualified') is True and not p.verify_report(report,prepared)):
        raise Refused('production_parity_revalidation_failed')
    spec = importlib.util.spec_from_file_location('temperature_sanitizer',ROOT/'scripts/v1-windows-parity.py')
    sanitizer = importlib.util.module_from_spec(spec);spec.loader.exec_module(sanitizer)
    summary = sanitizer.sanitized(report,prepared,manifest,source_files)
    provenance = dict(schema='helix-orca-v1-local-production-generation/v1',source_files=source_files,
        parameters=PARAMETERS,context_sha256=c.digest(context),request_sha256=c.digest(request),
        inputs_sha256=c.digest(inputs),executable_sha256=EXE_SHA,native_geometry_sha256=args.model_sha256,
        geometry_receipt_file_sha256=args.geometry_receipt_sha256,native_sha256=NATIVE_SHA,
        native_manifest_file_sha256=args.native_manifest_sha256,prepared_sha256=c.digest(prepared),
        report_sha256=c.digest(report),invocation_sha256=sha(args.output_dir/'job/invocation.json'),
        staged_model_sha256=sha(args.output_dir/'job/model.stl'),geometry_metrics=metrics,
        native_geometry_request_sha256=geometry_receipt['request_sha256'],
        native_geometry_build_receipt_sha256=geometry_receipt['build_receipt_sha256'],
        native_geometry_build_inputs_sha256=geometry_receipt['build_inputs_sha256'],
        native_geometry_executable_sha256=geometry_receipt['executable_sha256'],
        physical_actions=False,physical_readiness=False)
    write_json(args.output_dir/'generation-provenance.json',provenance)
    summary.update(schema=SCHEMA,parameters=PARAMETERS,context_sha256=c.digest(context),
        production_generator='integration.v1_generation.generate',native_geometry_sha256=args.model_sha256,
        geometry_receipt_file_sha256=args.geometry_receipt_sha256,geometry_metrics=metrics,
        executable_sha256=EXE_SHA,timeout_seconds=45,generation_provenance_sha256=c.digest(provenance),
        request_sha256=c.digest(request))
    if len(c.canonical(summary)) > 65536:
        raise Refused('summary_too_large')
    write_json(args.output_dir/'summary.json',summary)
    return summary


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise Refused('invalid_cli_arguments')


def main():
    try:
        parser = Parser(description=__doc__)
        for name in ('context','executable','model','geometry-receipt','native','native-manifest','output-dir'):
            parser.add_argument('--'+name,type=Path,required=True)
        for name in ('native-sha256','native-manifest-sha256','model-sha256','geometry-receipt-sha256'):
            parser.add_argument('--'+name,type=digest_arg,required=True)
        result = run(parser.parse_args())
        print(c.canonical(result).decode())
        return 0 if result['qualified'] else 2
    except Exception as error:
        code = str(error) if isinstance(error,Refused) else error.code if isinstance(error,g.GenerationBlocked) else 'local_production_generation_failed'
        print(json.dumps(dict(schema=SCHEMA,success=False,qualified=False,failure=code,
                              physical_actions=False,physical_readiness=False),sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
