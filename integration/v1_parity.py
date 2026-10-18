"""Offline, fail-closed native-reference parity. Never generates a reference.

Exact executable equality is intentionally conservative. Differences remain
blocked until a separately reviewed behavioral comparison policy exists.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from integration.v1_contract import canonical, digest

CALIBRATIONS = ('temperature', 'flow_ratio_yolo', 'pressure_advance_pattern',
                'retraction', 'max_volumetric_speed')
PINS = {'210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3': {'version': '2.5.0-dev', 'build': '210bc927'},
        '6a7763f08d1a175a464a00ce13f0b5a815662fc4': {'version': '2.5.0-dev', 'build': '6a7763f0'}}
MAX_GCODE_BYTES = 128 * 1024 * 1024


def file_record(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size > MAX_GCODE_BYTES:
        raise ValueError('missing or oversized parity artifact')
    return {'name': p.name, 'size': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def generation_inputs(request, snapshot, source_commit):
    """No request ID/timestamp: a retained native run can match identical inputs."""
    return {'calibration': request['calibration'], 'parameters': request['parameters'],
            'source_commit': source_commit, 'runtime': snapshot['runtime'],
            'context_sha256': request['context_sha256'],
            'profiles': {k: snapshot[k] for k in ('printer', 'process', 'filament')},
            'effective': snapshot['effective'], 'nozzle_mm': snapshot['nozzle_mm']}


def executable(text):
    # Strip only comments/blank lines. Do not drop M73, wipe, motion, heat or E.
    return [code for raw in text.splitlines() if (code := raw.split(';', 1)[0].strip())]


def analyze(text):
    """Track real deposition, E mode, heater state and feed without recipe tags."""
    xyz = dict.fromkeys('XYZ', 0.0)
    e = 0.0
    relative_e = False
    absolute_xyz = True
    nozzle = None
    bed = None
    feed = None
    layer = -1
    object_name = None
    moves = []
    retracts = []
    heaters = []
    object_names = set()
    for line, raw in enumerate(text.splitlines(), 1):
        if raw == ';LAYER_CHANGE':
            layer += 1
        if raw.startswith('; printing object '):
            object_name = raw[len('; printing object '):].split(' id:', 1)[0]
        if raw.startswith('; stop printing object '):
            object_name = None
        code = raw.split(';', 1)[0].strip()
        if not code:
            continue
        op = code.split()[0]
        values = {k: float(v) for k, v in re.findall(r'([A-Z])(-?(?:\d+(?:\.\d*)?|\.\d+))', code)}
        if any(not math.isfinite(x) for x in values.values()):
            raise ValueError('nonfinite G-code')
        if op in ('G90', 'G91'):
            absolute_xyz = op == 'G90'
        if op in ('M82', 'M83'):
            relative_e = op == 'M83'
        if op == 'G92':
            xyz.update({k: values[k] for k in xyz if k in values})
            e = values.get('E', e)
        if op in ('M104', 'M109', 'M140', 'M190'):
            target = values.get('S', values.get('R'))
            if target is None:
                raise ValueError('unrecognized heater command')
            if op in ('M104', 'M109'):
                nozzle = target
            else:
                bed = target
            heaters.append({'line': line, 'op': op, 'target': target, 'layer': layer})
        if op not in ('G0', 'G1'):
            continue
        old = xyz.copy()
        for k in xyz:
            if k in values:
                xyz[k] = values[k] if absolute_xyz else xyz[k] + values[k]
        delta = values.get('E', 0.0) if relative_e else values.get('E', e) - e
        if 'E' in values:
            e += delta
        feed = values.get('F', feed)
        distance = math.hypot(xyz['X'] - old['X'], xyz['Y'] - old['Y'])
        if delta < 0:
            retracts.append({'z': xyz['Z'], 'length': -delta, 'layer': layer})
        if delta > 0 and distance > 0 and layer >= 0 and object_name:
            object_names.add(object_name)
            moves.append({'line': line, 'layer': layer, 'z': xyz['Z'],
                          'nozzle': nozzle, 'bed': bed, 'e': delta,
                          'distance': distance, 'feed': feed, 'object': object_name,
                          'xy_start': [old['X'], old['Y']], 'xy_end': [xyz['X'], xyz['Y']]})
    return {'moves': moves, 'retracts': retracts, 'heaters': heaters,
            'objects': sorted(object_names), 'layers': layer + 1}


def _f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


_BED_FIELDS = {'Cool Plate': 'cool_plate_temp', 'Engineering Plate': 'eng_plate_temp',
               'High Temp Plate': 'hot_plate_temp', 'Textured PEI Plate': 'textured_plate_temp',
               'Textured Cool Plate': 'textured_cool_plate_temp', 'Supertack Plate': 'supertack_plate_temp'}


def _native_unescape(value):
    """Native ConfigOptionString uses only backslash, quote, CR and LF escapes."""
    if not isinstance(value, str):
        raise ValueError('immutable effective hook is unavailable')
    escaped = {'\\': '\\', '"': '"', 'r': '\r', 'n': '\n'}
    def unescape(match):
        if match[1] not in escaped:
            raise ValueError('unsupported native hook escape')
        return escaped[match[1]]
    return re.sub(r'\\(.)', unescape, value)


def _klipper_temperature_semantics(text, inputs, data):
    """Exact invocation parity does not claim execution of macro internals.

    PRINT_START BED_TEMP/EXTRUDER_TEMP and PRINT_END are the accepted target
    ABI documented by Issue12. The complete native stream is still compared
    separately. No arbitrary macro name or invocation is substituted here.
    """
    effective = inputs.get('effective', {})
    start_hook = executable(_native_unescape(effective.get('machine_start_gcode')))
    end_hook = executable(_native_unescape(effective.get('machine_end_gcode')))
    accepted_template = 'PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]'
    original_template = 'PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]'
    templates = [line for line in start_hook if line.split()[0] == 'PRINT_START']
    if templates == [accepted_template]:
        original_abi = False
    elif templates == [original_template]:
        original_abi = True
        prefix = start_hook[:start_hook.index(original_template)]
        if ('M190 S[bed_temperature_initial_layer_single]' not in prefix
                or 'M109 S[nozzle_temperature_initial_layer]' not in prefix):
            raise ValueError('original macro ABI requires immutable explicit bed/nozzle wait hooks')
    else:
        raise ValueError('effective PRINT_START hook differs from either bounded native macro ABI')
    if [line for line in end_hook if line.split()[0] == 'PRINT_END'] != ['PRINT_END']:
        raise ValueError('effective PRINT_END hook differs from the retained accepted macro ABI')
    bed_field = _BED_FIELDS.get(effective.get('curr_bed_type'))
    if bed_field is None:
        raise ValueError('effective Klipper bed type is unavailable')
    try:
        initial_bed = float(effective[bed_field + '_initial_layer'])
        normal_bed = float(effective[bed_field])
    except (KeyError, ValueError, TypeError):
        raise ValueError('effective single-filament bed temperatures are unavailable')
    if not all(math.isfinite(v) and 0 < v <= 150 for v in (initial_bed, normal_bed)):
        raise ValueError('effective bed temperature is outside the bounded macro comparison')
    commands = [(index, raw.split(';', 1)[0].strip()) for index, raw in enumerate(text.splitlines(), 1)
                if raw.split(';', 1)[0].strip()]
    starts = [(line, code) for line, code in commands if code.split()[0] == 'PRINT_START']
    ends = [(line, code) for line, code in commands if code.split()[0] == 'PRINT_END']
    if len(starts) != 1 or len(ends) != 1 or starts[0][0] >= data['moves'][0]['line'] or ends[0][0] <= data['moves'][-1]['line']:
        raise ValueError('PRINT_START/PRINT_END missing, duplicated or misplaced around deposition')
    arguments = starts[0][1].split()[1:]
    if len(arguments) != 2 or not all('=' in part for part in arguments):
        raise ValueError('malformed PRINT_START arguments')
    values = dict(part.split('=', 1) for part in arguments)
    keys = ('BED', 'EXTRUDER') if original_abi else ('BED_TEMP', 'EXTRUDER_TEMP')
    try:
        valid = (set(values) == set(keys)
                 and float(values[keys[0]]) == initial_bed
                 and float(values[keys[1]]) == inputs['parameters']['start'])
    except (ValueError, KeyError):
        valid = False
    if original_abi:
        for op, target in (('M190', initial_bed), ('M109', inputs['parameters']['start'])):
            if not any(h['op'] == op and h['target'] == target and h['line'] < starts[0][0] for h in data['heaters']):
                raise ValueError('original macro ABI requires independently matching visible waits before PRINT_START')
    if not valid or ends[0][1] != 'PRINT_END':
        raise ValueError('native macro arguments differ from the exact effective calibration targets')
    prefix = [code.split()[0] for line, code in commands if line < data['moves'][0]['line']]
    xyz_modes = [op for op in prefix if op in ('G90', 'G91')]
    e_modes = [op for op in prefix if op in ('M82', 'M83')]
    relative = effective.get('use_relative_e_distances')
    if (relative not in ('0', '1') or not xyz_modes or xyz_modes[-1] != 'G90'
            or not e_modes or e_modes[-1] != ('M83' if relative == '1' else 'M82')):
        raise ValueError('native coordinate/extrusion mode differs from immutable effective input')
    for heater in data['heaters']:
        if heater['target'] and heater['op'] in ('M140', 'M190'):
            if heater['target'] != (initial_bed if heater['layer'] < 1 else normal_bed):
                raise ValueError('bed command differs from immutable effective plate temperatures')
    limits = {key: value for key, value in effective.items()
              if key.startswith('machine_max_') or key in ('printable_area', 'printable_height', 'printable_volume', 'gcode_flavor')}
    return {'policy': 'native-original-visible-waits-v1' if original_abi else 'accepted-klipper-macro-invocation-v1',
            'hardware_abi_qualified': False, 'accepted_abi_signature': not original_abi,
            'start': starts[0][1], 'end': ends[0][1],
            'initial_bed_c': initial_bed, 'normal_bed_c': normal_bed,
            'effective_hooks_sha256': digest({'start': effective['machine_start_gcode'], 'end': effective['machine_end_gcode']}),
            'effective_limits_sha256': digest(limits), 'coordinate_mode': 'absolute',
            'extrusion_mode': 'relative' if relative == '1' else 'absolute',
            'macro_internals': 'unobserved; identical native invocations are compared, not expanded or physically executed',
            'physical_readiness': False}


def invariants(text, inputs):
    """Conservative independent checks augment exact native executable parity."""
    d = analyze(text)
    if not d['moves']:
        raise ValueError('no actual model deposition')
    forbidden = re.compile(r'RUN_SHELL_COMMAND|SAVE_CONFIG|\bM500\b|\bM997\b|https?://', re.I)
    if any(forbidden.search(x) for x in executable(text)):
        raise ValueError('persistent or external executable command')
    kind = inputs['calibration']
    p = inputs['parameters']
    macro_semantics = None
    if kind == 'temperature':
        start, end = p['start'], p['end']
        count = int((start - end) / 5) + 1
        if d['layers'] < count or p['step'] != 5 or not p['scale']:
            raise ValueError('unsupported temperature invariant envelope')
        height = inputs['nozzle_mm'] / 2
        seen = set()
        for m in d['moves']:
            # Native interpolate_value_across_layers uses float arithmetic.
            band = min(count - 1, int(_f32(_f32(m['layer'] * count) / _f32(d['layers'] - 1))))
            expected = start - 5 * band
            if m['layer'] <= 1:
                expected = start
            if m['nozzle'] != expected:
                raise ValueError('temperature differs during actual deposition')
            if not math.isclose(m['z'], (m['layer'] + 1) * height, abs_tol=0.0001):
                raise ValueError('printed Z differs from fixed native layer schedule')
            seen.add(m['nozzle'])
        if seen != {start - 5 * i for i in range(count)}:
            raise ValueError('missing printed temperature section')
        for h in d['heaters']:
            if h['target'] == 0 and h['line'] <= d['moves'][-1]['line']:
                raise ValueError('premature heater shutdown')
            if h['target'] and h['op'] in ('M104', 'M109') and h['layer'] >= 0 and h['line'] <= d['moves'][-1]['line']:
                band = min(count - 1, int(_f32(_f32(h['layer'] * count) / _f32(d['layers'] - 1))))
                target = start if h['layer'] <= 1 else start - 5 * band
                if h['target'] != target:
                    raise ValueError('layer heater command differs from the calibration section')
        if inputs.get('effective', {}).get('gcode_flavor') == 'klipper':
            macro_semantics = _klipper_temperature_semantics(text, inputs, d)
        else:
            if not any(h['op'] == 'M109' and h['target'] == start and h['line'] < d['moves'][0]['line'] for h in d['heaters']):
                raise ValueError('missing initial nozzle wait')
            if not all(any(h['op'] == op and h['target'] == 0 and h['line'] > d['moves'][-1]['line'] for h in d['heaters']) for op in ('M104', 'M140')):
                raise ValueError('missing final heater shutdown')
    elif kind == 'flow_ratio_yolo':
        expected = {'flowrate_0'} | {f'flowrate_{sign}0.0{i}' for sign in ('', 'm') for i in range(1, 6)}
        names = {re.sub(r'\s+id.*$', '', n) for n in d['objects']}
        if names != expected or p != {'pass': 1} or ';TYPE:Top surface' not in text:
            raise ValueError('missing native YOLO labeled patches or top surfaces')
    else:
        raise ValueError('native-engine invariant adapter not yet implemented for ' + kind)
    return {'model_moves': len(d['moves']), 'layers': d['layers'],
            'deposition_temperatures': sorted({m['nozzle'] for m in d['moves'] if m['nozzle'] is not None}),
            'objects': d['objects'], 'executable_commands': len(executable(text)),
            'macro_semantics': macro_semantics, 'physical_readiness': False}


def observations(candidate_text, native_text):
    """Measurements explain differences without relaxing the qualification gate."""
    a, b = analyze(candidate_text), analyze(native_text)
    ac, bc = executable(candidate_text), executable(native_text)
    def op_stream(commands, allowed):
        return [line for line in commands if line.split()[0] in allowed]
    def bounds(data):
        return {axis: [min(m[pos][i] for m in data['moves'] for pos in ('xy_start', 'xy_end')),
                       max(m[pos][i] for m in data['moves'] for pos in ('xy_start', 'xy_end'))]
                for i, axis in enumerate('XY')} if data['moves'] else None
    heaters = lambda d: [(h['op'], h['target'], h['layer']) for h in d['heaters']]
    return {
        'heater_stream_equal': heaters(a) == heaters(b),
        'machine_limits_equal': op_stream(ac, {'M201', 'M203', 'M205', 'M566'}) == op_stream(bc, {'M201', 'M203', 'M205', 'M566'}),
        'progress_estimates_equal': op_stream(ac, {'M73'}) == op_stream(bc, {'M73'}),
        'motion_extrusion_equal': op_stream(ac, {'G0', 'G1', 'G2', 'G3', 'G92'}) == op_stream(bc, {'G0', 'G1', 'G2', 'G3', 'G92'}),
        'candidate_model_extrusion_mm': sum(m['e'] for m in a['moves']),
        'native_model_extrusion_mm': sum(m['e'] for m in b['moves']),
        'candidate_printed_xy_bounds_mm': bounds(a), 'native_printed_xy_bounds_mm': bounds(b),
        'candidate_model_moves': len(a['moves']), 'native_model_moves': len(b['moves']),
        'qualification': 'Measurements only. Every executable difference still blocks exact-executable-v1.'}


def create_native_reference(native, context, calibration, parameters, source_commit, evidence):
    """Register independently captured native inputs; no candidate is accepted.

    Caller must supply the native run's complete pre-calibration context and
    retained UI action evidence. A legacy lab run without that full snapshot
    cannot be upgraded into exact V1 input provenance by this utility.
    """
    from integration.v1_contract import validate_context, validate_parameters
    context = validate_context(context)
    parameters = validate_parameters(calibration, parameters)
    if PINS.get(source_commit) != context['runtime']:
        raise ValueError('native source/runtime pin mismatch')
    if len(evidence) < 2:
        raise ValueError('retain independent native input/dialog and export/action evidence')
    inputs = generation_inputs({'calibration': calibration, 'parameters': parameters,
                                'context_sha256': digest(context)}, context, source_commit)
    return {'schema': 'helix-orca-v1-native-reference/v1', 'method': 'native_orca_ui',
            'imported_candidate': False, 'inputs_sha256': digest(inputs),
            'source_commit': source_commit, 'runtime': context['runtime'],
            'artifact': file_record(native),
            'evidence': [{'path': str(Path(path).resolve()), 'artifact': file_record(path)} for path in evidence]}


def evaluate(candidate, native, manifest, inputs):
    """Retain every difference. A caller-supplied qualified flag has no authority."""
    report = {'schema': 'helix-orca-v1-parity/v1', 'qualified': False,
              'inputs_sha256': digest(inputs), 'candidate': file_record(candidate),
              'reference': None, 'source_commit': inputs['source_commit'],
              'reason': '', 'differences': [], 'policy': 'exact-executable-v1',
              'inputs': inputs, 'candidate_path': str(Path(candidate).resolve()),
              'native_path': str(Path(native).resolve()), 'manifest': manifest}
    try:
        if Path(candidate).resolve() == Path(native).resolve():
            raise ValueError('candidate cannot be its own native reference')
        report['reference'] = file_record(native)
        if (manifest.get('schema') != 'helix-orca-v1-native-reference/v1'
                or manifest.get('method') != 'native_orca_ui'
                or manifest.get('imported_candidate') is not False
                or manifest.get('inputs_sha256') != digest(inputs)
                or manifest.get('source_commit') != inputs['source_commit']
                or manifest.get('runtime') != inputs['runtime']
                or manifest.get('artifact') != report['reference']):
            raise ValueError('native reference provenance or exact inputs do not match')
        if PINS.get(inputs['source_commit']) != inputs['runtime']:
            raise ValueError('unqualified source/runtime pin')
        evidence = manifest.get('evidence', [])
        if not evidence:
            raise ValueError('native UI evidence is missing')
        # Evidence paths must be local, retained and exact bytes, not a URL claim.
        for item in evidence:
            if file_record(item['path']) != item['artifact']:
                raise ValueError('native UI evidence bytes changed')
        a = Path(candidate).read_text(encoding='utf-8')
        b = Path(native).read_text(encoding='utf-8')
        report['candidate_invariants'] = invariants(a, inputs)
        report['native_invariants'] = invariants(b, inputs)
        report['observations'] = observations(a, b)
        ac, bc = executable(a), executable(b)
        mismatches = []
        for index in range(max(len(ac), len(bc))):
            x = ac[index] if index < len(ac) else None
            y = bc[index] if index < len(bc) else None
            if x != y:
                if len(mismatches) < 20:
                    mismatches.append({'index': index, 'candidate': x, 'native': y})
        report['differences'] = mismatches
        report['candidate_executable_sha256'] = hashlib.sha256('\n'.join(ac).encode()).hexdigest()
        report['native_executable_sha256'] = hashlib.sha256('\n'.join(bc).encode()).hexdigest()
        if ac != bc:
            raise ValueError('executable behavior differs; no reviewed difference policy applies')
        report['qualified'] = True
        report['reason'] = 'Exact executable stream and calibration invariants match independently prepared native UI reference.'
    except (ValueError, KeyError, OSError, UnicodeError, TypeError) as error:
        report['reason'] = str(error)
    return report


def unqualified(candidate, inputs, reason):
    return {'schema': 'helix-orca-v1-parity/v1', 'qualified': False,
            'inputs_sha256': digest(inputs), 'candidate': file_record(candidate),
            'reference': None, 'source_commit': inputs['source_commit'],
            'reason': reason, 'differences': [], 'policy': 'exact-executable-v1'}


def verify_report(report, prepared):
    """Recompute qualified evidence from retained bytes; do not trust a flag."""
    try:
        if (report.get('schema') != 'helix-orca-v1-parity/v1'
                or report.get('qualified') is not True
                or prepared['parity']['qualified'] is not True
                or prepared['parity']['report_sha256'] != digest(report)
                or report['candidate'] != prepared['artifact']
                or report['inputs']['calibration'] != prepared['calibration']
                or report['inputs']['parameters'] != prepared['parameters']
                or report['inputs']['context_sha256'] != prepared['context_sha256']
                or report['source_commit'] != prepared['generator']['build']):
            return False
        rerun = evaluate(report['candidate_path'], report['native_path'], report['manifest'], report['inputs'])
        return rerun['qualified'] is True and canonical(rerun) == canonical(report)
    except (KeyError, TypeError, ValueError, OSError):
        return False
