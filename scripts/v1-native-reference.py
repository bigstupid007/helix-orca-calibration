#!/usr/bin/env python3
"""Register Windows-local native evidence; emit fixed-key scalar diagnostics.

Run using existing Python -I -S. This utility has no candidate input and never
qualifies generation or physical readiness. Raw reports remain in a new local
directory; stdout contains no G-code, paths, profiles, hooks or error text.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from integration import v1_contract as c
from integration import v1_parity as p

PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
CONTEXT_SHA = '3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'
SCHEMA = 'helix-orca-v1-native-reference-summary/v1'
DEFAULTS = {'temperature': {'start': 230, 'end': 190, 'step': 5, 'scale': True},
            'flow_ratio_yolo': {'pass': 1},
            'pressure_advance_pattern': {'start': 0, 'end': .08, 'step': .005},
            'retraction': {'start': 0, 'end': 2, 'step': .1},
            'max_volumetric_speed': {'start': 5, 'end': 20, 'step': .5}}


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def local_file(path, maximum):
    path = Path(path)
    if str(path).startswith(('\\\\', '//')) or path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise Refused('local_file_missing_unsafe_or_oversized')
    return path


def read_json(path):
    return json.loads(local_file(path, c.MAX_MESSAGE).read_text(encoding='utf-8-sig'))


def sha(path):
    with local_file(path, p.MAX_GCODE_BYTES).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def artifact(record):
    return {'size': record['size'], 'sha256': record['sha256']}


def failure_code(error):
    # Controlled categories only. Never forward any input-derived string.
    message = str(error)
    for needle, code in (
        ('no actual model deposition', 'no_actual_model_deposition'),
        ('native PA Pattern requires four', 'pa_section_count'),
        ('PA Pattern section values', 'pa_values_or_reset'),
        ('PA Pattern actual deposition Z', 'pa_deposition_z'),
        ('PA sample lacks', 'pa_chevron_walls'),
        ('PA chevron side', 'pa_chevron_length'),
        ('retraction printed Z', 'retraction_layer_z'),
        ('retraction length differs', 'retraction_episode_length'),
        ('missing actual retraction', 'retraction_missing_section'),
        ('no actual software retraction', 'retraction_no_episodes'),
        ('retraction tower does not cover', 'retraction_height'),
        ('MVS tower does not cover', 'mvs_height'),
        ('MVS actual wall feed', 'mvs_wall_feed'),
        ('missing increasing native MVS', 'mvs_missing_speed_sections'),
        ('non-belt', 'unsupported_belt_context'),
        ('arcs or firmware', 'unsupported_arc_or_firmware_retraction'),
        ('PRINT_START hook', 'macro_effective_start_abi'),
        ('PRINT_END hook', 'macro_effective_end_abi'),
        ('PRINT_START/PRINT_END', 'macro_placement'),
        ('macro arguments', 'macro_targets'),
        ('visible waits', 'macro_visible_waits'),
        ('wait hooks', 'macro_effective_wait_hooks'),
        ('coordinate/extrusion mode', 'motion_or_extrusion_mode'),
        ('plate temperatures', 'bed_targets'),
        ('nozzle command differs', 'nozzle_targets'),
        ('effective ', 'effective_value_unavailable'),
    ):
        if needle in message:
            return code
    return 'native_invariant_rejected'


def sanitized_invariants(value):
    clean = {'passed': isinstance(value, dict), 'macro_semantics_present': False,
             'accepted_abi_signature': False, 'physical_readiness': False,
             'hardware_abi_qualified': False}
    if not isinstance(value, dict):
        return clean
    for key in ('model_moves', 'layers', 'executable_commands'):
        if type(value.get(key)) is int and value[key] >= 0:
            clean[key] = value[key]
    temperatures = value.get('deposition_temperatures')
    if isinstance(temperatures, list) and len(temperatures) <= 100 and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 600 for v in temperatures):
        clean['deposition_temperatures'] = temperatures
    macro = value.get('macro_semantics')
    if isinstance(macro, dict):
        clean['macro_semantics_present'] = True
        clean['accepted_abi_signature'] = macro.get('accepted_abi_signature') is True
    semantics = value.get('calibration_semantics')
    if isinstance(semantics, dict):
        clean['calibration'] = {}
        allowed = ('custom_layers', 'samples_per_layer', 'walls_per_sample', 'native_end_can_be_exceeded',
                   'layer_height_mm', 'retraction_episode_count', 'boundary_z_tolerance_mm', 'flow_mm3_per_mm',
                   'line_width_mm', 'checked_layers', 'initial_and_slowdown_layers_excluded',
                   'serialized_z_tolerance_mm', 'serialized_feed_tolerance_mm_s')
        for key in allowed:
            item = semantics.get(key)
            if type(item) is bool or type(item) in (int, float) and math.isfinite(item):
                clean['calibration'][key] = item
        for key in ('pressure_advance_values', 'measured_retraction_lengths_mm', 'distinct_wall_speeds_mm_s'):
            items = semantics.get(key)
            if isinstance(items, list) and all(type(v) in (int, float) and math.isfinite(v) for v in items):
                clean['calibration'][key + '_count'] = len(items)
                if len(items) <= 256:
                    clean['calibration'][key] = items
    return clean


def run(args):
    if args.calibration not in DEFAULTS:
        raise Refused('unknown_calibration')
    context = c.validate_context(read_json(args.context))
    if c.digest(context) != CONTEXT_SHA or context['runtime'] != p.PINS[PIN]:
        raise Refused('immutable_original_context_or_runtime_mismatch')
    parameters = c.validate_parameters(args.calibration, read_json(args.parameters) if args.parameters else DEFAULTS[args.calibration])
    native = local_file(args.native, p.MAX_GCODE_BYTES)
    if not 2 <= len(args.native_evidence) <= 16:
        raise Refused('independent_native_ui_evidence_required')
    for path in args.native_evidence:
        path = local_file(path, 16 * 1024 * 1024)
        with path.open('rb') as stream:
            if path.suffix.lower() != '.png' or stream.read(8) != b'\x89PNG\r\n\x1a\n':
                raise Refused('native_ui_png_evidence_required')
    if len({str(path.resolve()) for path in args.native_evidence}) != len(args.native_evidence):
        raise Refused('native_ui_evidence_must_be_distinct')
    manifest = p.create_native_reference(native, context, args.calibration, parameters, PIN,
                                         [args.context, *args.native_evidence])
    inputs = p.generation_inputs({'calibration': args.calibration, 'parameters': parameters,
                                 'context_sha256': c.digest(context)}, context, PIN)
    source_files = {key: sha(path) for key, path in (
        ('contract', SOURCE_ROOT/'integration/v1_contract.py'),
        ('parity', SOURCE_ROOT/'integration/v1_parity.py'), ('inspector', Path(__file__)))}
    report = {'schema': 'helix-orca-v1-native-inspection/v1', 'qualified': False,
              'reference_registered': True, 'calibration': args.calibration, 'parameters': parameters,
              'source_commit': PIN, 'runtime': context['runtime'], 'inputs': inputs,
              'native_path': str(native.resolve()), 'native_reference': manifest,
              'source_files': source_files, 'native_invariants': None, 'invariants_passed': False,
              'physical_actions': False, 'physical_readiness': False, 'hardware_abi_qualified': False}
    code = None
    try:
        report['native_invariants'] = p.invariants(native.read_text(encoding='utf-8-sig'), inputs)
        report['invariants_passed'] = True
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        code = failure_code(error)
        report['invariant_failure'] = {'code': code, 'detail': str(error)}
    summary = {'schema': SCHEMA, 'success': True, 'qualified': False, 'reference_registered': True,
               'invariants_passed': report['invariants_passed'], 'calibration': args.calibration,
               'parameters': parameters, 'source_commit': PIN, 'runtime': context['runtime'],
               'context_sha256': c.digest(context), 'inputs_sha256': c.digest(inputs),
               'native': artifact(manifest['artifact']), 'native_manifest_sha256': c.digest(manifest),
               'report_sha256': c.digest(report), 'source_files': source_files,
               'native_evidence': [artifact(item['artifact']) for item in manifest['evidence']],
               'invariants': sanitized_invariants(report['native_invariants']),
               'physical_actions': False, 'physical_readiness': False, 'hardware_abi_qualified': False}
    if code:
        summary['invariant_failure_code'] = code
    if len(c.canonical(summary)) > 65536:
        raise Refused('summary_too_large')
    args.output_dir.mkdir(exist_ok=False)
    for name, value in (('native-reference.json', manifest), ('native-inspection.json', report), ('summary.json', summary)):
        with (args.output_dir/name).open('xb') as stream:
            stream.write(c.canonical(value))
    return summary


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('invalid_cli_arguments')


def main():
    try:
        parser = Parser(description=__doc__)
        for name in ('native', 'context', 'output-dir'):
            parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--calibration', choices=tuple(DEFAULTS), required=True)
        parser.add_argument('--parameters', type=Path)
        parser.add_argument('--native-evidence', action='append', type=Path, required=True)
        args = parser.parse_args()
        result = run(args)
        print(c.canonical(result).decode())
        return 0
    except Exception as error:
        code = error.code if isinstance(error, Refused) else 'local_registration_input_failed'
        print(json.dumps({'schema': SCHEMA, 'success': False, 'qualified': False, 'reference_registered': False,
                          'physical_actions': False, 'physical_readiness': False, 'failure': code}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
