#!/usr/bin/env python3
"""Generate YOLO locally through the real production function; sanitize stdout.

Existing Windows-local context/native artifacts never leave this machine.
No printer transport, physical action, private bundle transfer or profile write.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import sys
import time

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from integration import v1_contract as c, v1_generation as g, v1_parity as p

PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
CONTEXT_SHA = '3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'
EXE_SHA = 'e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
ASSET_SHA = 'c998359cef8c247c5c9c50ea0d07e778590be7cdaa1d21beaf84abccea7840ca'
NATIVE_SHA = '0fb149a6a1624cdf64cb03a8c0dcb0fc6a21d9d3f43a4fb0f3389e4e48485daa'
SCHEMA = 'helix-orca-v1-windows-stock-yolo-summary/v1'


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def sha(path, maximum=2*1024**3):
    path = Path(path)
    if str(path).startswith(('\\\\','//')) or path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise Refused('local_source_or_artifact_unavailable')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read_json(path):
    sha(path,c.MAX_MESSAGE)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    with path.open('xb') as stream:
        stream.write(c.canonical(value))


def run(args):
    context = c.validate_context(read_json(args.context))
    if c.digest(context) != CONTEXT_SHA or context['runtime'] != p.PINS[PIN]:
        raise Refused('immutable_original_context_or_runtime_mismatch')
    if sha(args.executable) != EXE_SHA or sha(args.asset) != ASSET_SHA or sha(args.native) != NATIVE_SHA:
        raise Refused('exact_executable_public_asset_or_native_pin_mismatch')
    manifest = read_json(args.native_manifest)
    now = int(time.time())
    request = c.validate_request(dict(schema='helix-orca-v1-request/v1', request_id=secrets.token_hex(16),
        origin_id=context['origin_id'], context_sha256=c.digest(context), calibration='flow_ratio_yolo',
        parameters={'pass':1}, created_at=now, expires_at=now+3600, not_applied=True),now=now)
    inputs = p.generation_inputs(request,context,PIN)
    if (manifest.get('schema') != 'helix-orca-v1-native-reference/v1' or manifest.get('method') != 'native_orca_ui'
            or manifest.get('imported_candidate') is not False or manifest.get('inputs_sha256') != c.digest(inputs)
            or manifest.get('artifact') != p.file_record(args.native) or manifest.get('source_commit') != PIN
            or manifest.get('runtime') != p.PINS[PIN] or len(manifest.get('evidence',[])) < 2):
        raise Refused('independent_native_reference_provenance_mismatch')
    for item in manifest['evidence']:
        if p.file_record(item['path']) != item['artifact']:
            raise Refused('independent_native_evidence_changed')
    if str(args.output_dir).startswith(('\\\\','//')) or args.output_dir.is_symlink():
        raise Refused('new_local_output_directory_required')
    args.output_dir.mkdir(exist_ok=False)
    code_files = {name:sha(SOURCE_ROOT/name) for name in (
        'integration/v1_contract.py','integration/v1_generation.py','integration/v1_parity.py',
        'scripts/v1-windows-stock-yolo.py','scripts/v1-windows-parity.py')}
    config = dict(source_commit=PIN,runtime=p.PINS[PIN],now=now,
        executable=str(args.executable.resolve()),executable_sha256=EXE_SHA,timeout_seconds=45,
        flow_asset=dict(path=str(args.asset.resolve()),sha256=ASSET_SHA,source_commit=PIN),
        native_reference=dict(manifest=dict(path=str(args.native_manifest.resolve()),sha256=sha(args.native_manifest)),
                              gcode=dict(path=str(args.native.resolve()),sha256=NATIVE_SHA)))
    write_json(args.output_dir/'request.json',request)
    write_json(args.output_dir/'generation-config.json',config)
    write_json(args.output_dir/'source-files.json',code_files)
    try:
        # Deliberately call production implementation, with no injected runner.
        prepared = g.generate(request,context,args.output_dir/'job',config)
    except Exception as error:
        write_json(args.output_dir/'generation-failure.json',dict(type=type(error).__name__,detail=str(error),
                   physical_actions=False,physical_readiness=False))
        raise
    report = read_json(args.output_dir/'job/parity.json')
    if prepared['parity']['report_sha256'] != c.digest(report):
        raise Refused('production_report_digest_mismatch')
    if report.get('qualified') is True and not p.verify_report(report,prepared):
        raise Refused('qualified_report_revalidation_failed')
    specification = importlib.util.spec_from_file_location('sanitized_windows_parity',SOURCE_ROOT/'scripts/v1-windows-parity.py')
    summary_module = importlib.util.module_from_spec(specification);specification.loader.exec_module(summary_module)
    summary = summary_module.sanitized(report,prepared,manifest,code_files)
    summary.update(schema=SCHEMA,production_generator='integration.v1_generation.generate',
                   request_sha256=c.digest(request),context_sha256=c.digest(context),
                   executable_sha256=EXE_SHA,public_asset_sha256=ASSET_SHA,
                   timeout_seconds=45,request_created_at=now,request_expires_at=now+3600)
    provenance = dict(schema='helix-orca-v1-local-production-generation/v1',source_files=code_files,
        request_sha256=c.digest(request),inputs_sha256=c.digest(inputs),context_sha256=c.digest(context),
        executable_sha256=EXE_SHA,public_asset_sha256=ASSET_SHA,native_sha256=NATIVE_SHA,
        native_manifest_sha256=c.digest(manifest),prepared_sha256=c.digest(prepared),report_sha256=c.digest(report),
        invocation_sha256=sha(args.output_dir/'job/invocation.json'),physical_actions=False,physical_readiness=False)
    write_json(args.output_dir/'generation-provenance.json',provenance)
    summary['generation_provenance_sha256'] = c.digest(provenance)
    if len(c.canonical(summary)) > 65536:
        raise Refused('summary_too_large')
    write_json(args.output_dir/'summary.json',summary)
    return summary


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise Refused('invalid_cli_arguments')


def main():
    try:
        parser=Parser(description=__doc__)
        for name in ('context','executable','asset','native','native-manifest','output-dir'):
            parser.add_argument('--'+name,type=Path,required=True)
        result=run(parser.parse_args())
        print(c.canonical(result).decode())
        return 0
    except Exception as error:
        code=error.code if isinstance(error,(Refused,g.GenerationBlocked)) else 'local_production_generation_failed'
        print(json.dumps(dict(schema=SCHEMA,success=False,qualified=False,failure=code,
                              physical_actions=False,physical_readiness=False),sort_keys=True))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
