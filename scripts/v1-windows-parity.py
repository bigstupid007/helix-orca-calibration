#!/usr/bin/env python3
"""Evaluate local Windows artifacts; retain raw reports, emit fixed-key metrics.

Run with an existing Python -I -S and only curated source beside this script.
No networking, subprocesses, profiles, G-code or raw exception text is emitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from integration import v1_contract as c
from integration import v1_parity as p

PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
EXE_SHA = 'e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
SCHEMA = 'helix-orca-v1-windows-parity-summary/v1'


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def read_json(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > c.MAX_MESSAGE:
        raise Refused('json_unavailable_or_oversized')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def artifact(value):
    return {'size': value['size'], 'sha256': value['sha256']}


def sanitized(report, prepared, native_manifest, code_files):
    """Only fixed fields; raw report strings/keys/commands are never forwarded."""
    if report.get('qualified') is True:
        disposition = 'exact_executable_and_invariants_match'
    elif report.get('differences'):
        disposition = 'executable_difference'
    elif not report.get('candidate_invariants') or not report.get('native_invariants'):
        disposition = 'calibration_invariant_or_provenance_failed'
    else:
        disposition = 'comparison_failed'
    summary = {'schema': SCHEMA, 'success': True, 'qualified': report.get('qualified') is True,
               'disposition': disposition, 'policy': 'exact-executable-v1',
               'physical_actions': False, 'physical_readiness': False,
               'macro_internals_observed': False, 'hardware_abi_qualified': False,
               'inputs_sha256': report['inputs_sha256'], 'source_commit': PIN,
               'candidate': artifact(report['candidate']), 'native': artifact(report['reference']),
               'report_sha256': c.digest(report), 'prepared_sha256': c.digest(prepared),
               'native_manifest_sha256': c.digest(native_manifest), 'source_files': code_files,
               'native_evidence': [artifact(item['artifact']) for item in native_manifest['evidence']],
               'invariants': {}, 'observations': {}, 'emitted_setting_difference_count': 0,
               'unclassified_setting_difference_count': 0}
    for label in ('candidate', 'native'):
        inv = report.get(label + '_invariants', {})
        clean = {'passed': bool(inv)}
        for key in ('model_moves', 'layers', 'executable_commands'):
            if type(inv.get(key)) is int:
                clean[key] = inv[key]
        values = inv.get('deposition_temperatures')
        if isinstance(values, list) and len(values) <= 100 and all(type(v) in (int,float) and math.isfinite(v) and 0 <= v <= 600 for v in values):
            clean['deposition_temperatures'] = values
        summary['invariants'][label] = clean
    obs = report.get('observations', {})
    allowed = ('heater_stream_equal', 'machine_limits_equal', 'static_machine_limit_commands_present',
               'dynamic_acceleration_stream_equal', 'dynamic_acceleration_unique_values_equal',
               'candidate_dynamic_acceleration_commands', 'native_dynamic_acceleration_commands',
               'progress_estimates_equal', 'motion_extrusion_equal', 'candidate_model_extrusion_mm',
               'native_model_extrusion_mm', 'candidate_model_moves', 'native_model_moves')
    for key in allowed:
        value = obs.get(key)
        if type(value) is bool or type(value) in (int,float) and math.isfinite(value):
            summary['observations'][key] = value
    if 'candidate_printed_xy_bounds_mm' in obs and 'native_printed_xy_bounds_mm' in obs:
        summary['observations']['printed_xy_bounds_equal'] = obs['candidate_printed_xy_bounds_mm'] == obs['native_printed_xy_bounds_mm']
    diffs = report.get('emitted_settings', {}).get('differences', [])
    summary['emitted_setting_difference_count'] = len(diffs)
    summary['unclassified_setting_difference_count'] = sum(item.get('classification') == 'unclassified effective setting difference' for item in diffs)
    return summary


def run(args):
    context = c.validate_context(read_json(args.context))
    request = read_json(args.request)
    # This is historical evidence inspection, never a live dispatch/Start gate.
    request = c.validate_request(request, now=request['created_at'])
    if request['context_sha256'] != c.digest(context) or request['origin_id'] != context['origin_id']:
        raise Refused('immutable_context_mismatch')
    if context['runtime'] != p.PINS[PIN]:
        raise Refused('runtime_mismatch')
    bundle = read_json(args.bundle_manifest)
    record = read_json(args.result_record)
    inputs = p.generation_inputs(request, context, PIN)
    if (bundle.get('schema') != 'helix-orca-v1-generation-bundle/v1'
            or bundle.get('source_commit') != PIN or bundle.get('executable_sha256') != EXE_SHA
            or bundle.get('context_sha256') != c.digest(context)
            or bundle.get('request_sha256') != c.digest(request)
            or bundle.get('inputs_sha256') != c.digest(inputs)):
        raise Refused('generation_bundle_provenance_mismatch')
    if (record.get('schema') != 'helix-orca-v1-windows-cli/v1' or record.get('exit_code') != 0
            or record.get('physical_actions') is not False or record.get('executable_sha256') != EXE_SHA
            or record.get('bundle_sha256') != sha(args.generation_archive)
            or record.get('script_sha256') != sha(args.generation_helper)):
        raise Refused('windows_execution_provenance_mismatch')
    for item in bundle.get('files', []):
        if re.fullmatch(r'[a-z-]+\.(json|stl|3mf)', item.get('name', '')) is None:
            raise Refused('unsafe_bundle_member')
        if p.file_record(args.bundle_manifest.parent/item['name']) != item:
            raise Refused('staged_bundle_member_changed')
    candidate = p.file_record(args.candidate)
    if not any(item == candidate for item in record.get('files', [])):
        raise Refused('candidate_not_bound_to_cli_execution')
    if len(args.native_evidence) < 2 or len(args.native_evidence) > 16:
        raise Refused('independent_native_ui_evidence_required')
    native_manifest = p.create_native_reference(args.native, context, request['calibration'], request['parameters'], PIN,
                                                [args.context, *args.native_evidence])
    report = p.evaluate(args.candidate, args.native, native_manifest, inputs)
    prepared = {key: request[key] for key in ('request_id','origin_id','context_sha256','calibration','parameters')}
    prepared.update(schema='helix-orca-v1-prepared/v1', request_sha256=c.digest(request), artifact=candidate,
                    generator={'build': PIN, 'route': 'stock-cli-recipe-v1'},
                    parity={'qualified': report['qualified'], 'report_sha256': c.digest(report), 'reason': report['reason'][:1000]},
                    not_applied=True)
    prepared = c.validate_prepared(prepared, request)
    if report['qualified'] and not p.verify_report(report, prepared):
        raise Refused('qualified_report_revalidation_failed')
    code_files = {}
    for label, path in (('contract', SOURCE_ROOT/'integration/v1_contract.py'),
                        ('parity', SOURCE_ROOT/'integration/v1_parity.py'), ('runner', Path(__file__))):
        code_files[label] = sha(path)
    result = sanitized(report, prepared, native_manifest, code_files)
    args.output_dir.mkdir(exist_ok=False)
    for name,value in (('native-reference.json',native_manifest), ('inputs.json',inputs),
                       ('parity.json',report), ('prepared.json',prepared), ('summary.json',result)):
        with (args.output_dir/name).open('xb') as stream:
            stream.write(c.canonical(value))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','native','context','request','bundle-manifest','result-record','generation-archive','generation-helper','output-dir'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--native-evidence', action='append', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args)
        output = c.canonical(result)
        if len(output) > 65536:
            raise Refused('summary_too_large')
        print(output.decode())
        return 0
    except Exception as error:
        code = error.code if isinstance(error, Refused) else 'local_input_or_comparison_failed'
        print(json.dumps({'schema':SCHEMA,'success':False,'qualified':False,'physical_actions':False,
                          'physical_readiness':False,'failure':code},sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
