"""Explicit job-local stock-Orca recipes; no printer or user-profile writes.

Run this outside Orca's audited Python plugin. A successful slice is still
unqualified until v1_parity independently accepts retained native UI evidence.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import xml.etree.ElementTree as ET
import zipfile

from integration import v1_contract as contract
from integration import v1_parity as parity

BLOCKERS = {
    'pressure_advance_pattern': 'Stock CLI cannot inject Calib_Params or the native PA Pattern custom path/digit generator; a pinned native-engine adapter and independent native reference are required.',
    'retraction': 'Stock CLI cannot inject the native per-height writer retraction_length state; firmware command templates are not equivalent to software retraction.',
    'max_volumetric_speed': 'Stock CLI cannot inject the native height-dependent internal outer_wall_speed state; M220/feed overrides are not equivalent to native extrusion planning.',
}


class GenerationBlocked(RuntimeError):
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        super().__init__(reason)


def capabilities(config=None):
    config = config or {}
    result = []
    for kind in contract.CALIBRATIONS:
        reason = BLOCKERS.get(kind)
        if not reason and not config.get('executable'):
            reason = 'A hash-pinned stock Orca executable has not been configured.'
        if not reason and kind == 'temperature' and not (config.get('temperature_model') or config.get('temperature_base_model')):
            reason = 'A hash-bound native-derived model matching this range/nozzle is required.'
        if not reason and kind == 'flow_ratio_yolo' and not config.get('flow_asset'):
            reason = 'The exact pinned native Orca-LinearFlow.3mf asset is required.'
        result.append({'id': kind, 'available': reason is None, 'reason': reason or 'Stock recipe available; exact native parity is mandatory before Ready.'})
    return result


def _blocked(code, message):
    raise GenerationBlocked(code, message)


def _checked_file(record, maximum=parity.MAX_GCODE_BYTES):
    p = Path(record['path']).resolve()
    if not p.is_file() or p.stat().st_size > maximum:
        _blocked('asset', 'Required generator asset is unavailable or oversized.')
    if hashlib.sha256(p.read_bytes()).hexdigest() != record['sha256']:
        _blocked('asset_digest', 'Pinned generator asset digest differs.')
    return p


def _numeric(mapping, key):
    if key not in mapping:
        _blocked('effective_unavailable', 'Effective ' + key + ' is unavailable.')
    try:
        value = float(mapping[key])
    except (ValueError, TypeError):
        _blocked('effective_malformed', 'Effective ' + key + ' is not a single finite value.')
    if not math.isfinite(value):
        _blocked('effective_malformed', 'Effective ' + key + ' is nonfinite.')
    return value


def _configs(snapshot):
    effective = snapshot['effective']
    result = {}
    for role, kind in (('printer', 'machine'), ('process', 'process'), ('filament', 'filament')):
        edited = snapshot[role]['edited']
        # Each native serialized option stays native serialized. Stock ConfigBase
        # accepts JSON strings and calls set_deserialize, including vectors.
        config = copy.deepcopy(edited['config'])
        for metadata in ('inherits', 'name', 'from', 'type', 'instantiation', 'compatible_printers', 'compatible_printers_condition', 'compatible_prints', 'compatible_prints_condition', 'different_settings_to_system'):
            config.pop(metadata, None)
        for key in config:
            if key not in effective:
                _blocked('effective_unavailable', 'Effective ' + key + ' is unavailable; no edited/saved fallback is permitted.')
            config[key] = effective[key]
        for metadata in ('inherits', 'name', 'from', 'type', 'instantiation', 'compatible_printers', 'compatible_printers_condition', 'compatible_prints', 'compatible_prints_condition', 'different_settings_to_system'):
            config.pop(metadata, None)
        config.update({'name': edited['name'], 'from': 'User', 'type': kind, 'instantiation': 'true'})
        result[kind] = config
    # Project/effective-only options may be absent from preset-local key maps.
    # The stock CLI applies supplied DynamicPrintConfig keys; preserve those
    # authoritative options explicitly instead of silently taking CLI defaults.
    owned = set().union(*(profile.keys() for profile in result.values()))
    result['machine'].update({key: value for key, value in effective.items()
                              if key not in owned and key not in ('name', 'from', 'type', 'inherits', 'instantiation')})
    # Credentials never enter a job bundle. They do not affect slicing.
    for config in result.values():
        for key in list(config):
            if key.startswith('print_host') or key in ('printhost_apikey', 'printhost_user', 'printhost_password'):
                config.pop(key)
    if 'post_process' not in effective:
        _blocked('effective_unavailable', 'Effective post_process is unavailable.')
    if effective['post_process'] not in ('', '""'):
        _blocked('post_process', 'External post-processing is outside the qualified generation route.')
    result['process']['post_process'] = []
    return result


def _temperature(request, snapshot, destination, config, profiles):
    p = request['parameters']
    if p['start'] % 5 or p['end'] % 5:
        _blocked('temperature_bands', 'Native standard tower requires start and end individually divisible by five.')
    if not p['scale'] or snapshot['nozzle_mm'] not in (0.4, 0.6) or snapshot['effective'].get('gcode_flavor') not in ('marlin', 'klipper'):
        _blocked('temperature_envelope', 'Stock Temperature recipe currently supports scaled 0.4/0.6 mm single-tool Marlin/Klipper towers only; other inputs need native qualification.')
    model = config.get('temperature_model')
    output = destination / 'model.stl'
    if model:
        if (model.get('parameters') != p or model.get('nozzle_mm') != snapshot['nozzle_mm']
                or model.get('source_commit') != config['source_commit']):
            _blocked('temperature_geometry', 'No hash-bound native-derived tower matches the exact range, scale, nozzle and source pin.')
        shutil.copyfile(_checked_file(model), output)
    else:
        base = config.get('temperature_base_model', {})
        if (base.get('source_commit') != config['source_commit']
                or base.get('decoded_from_sha256') != '47edfab84d48f3b762cf536fba532a0e4564653d80e20d4f936ddd5c4541796b'):
            _blocked('temperature_geometry', 'A pinned full native tower decoded from the exact source DRC is required.')
        source = _checked_file(base)
        try:
            import trimesh
        except ImportError:
            _blocked('geometry_dependency', 'Native tower cutting requires the separately packaged trimesh/mapbox-earcut geometry dependencies or an exact pre-cut model.')
        try:
            mesh = trimesh.load_mesh(source, process=True)
            upper = ((500 - p['end']) // 5 + 1) * 10 - 1e-4
            lower = ((500 - p['start']) // 5) * 10 + 1e-4
            mesh = mesh.slice_plane([0, 0, upper], [0, 0, -1], cap=True, engine='earcut')
            mesh = mesh.slice_plane([0, 0, lower], [0, 0, 1], cap=True, engine='earcut')
            mesh.apply_scale(snapshot['nozzle_mm'] / 0.4)
            mesh.apply_translation([-mesh.bounds.mean(axis=0)[0], -mesh.bounds.mean(axis=0)[1], -mesh.bounds[0, 2]])
            if not mesh.is_watertight or not all(math.isfinite(x) and x > 0 for x in mesh.extents):
                _blocked('temperature_geometry', 'Native-derived cut mesh is not a finite watertight solid.')
            mesh.export(output)
            (destination / 'geometry.json').write_bytes(contract.canonical({
                'method': 'native-asset-cut-cap-scale', 'source': base,
                'cut_planes': {'upper': upper, 'lower': lower}, 'extents_mm': mesh.extents.tolist(),
                'faces': len(mesh.faces), 'watertight': True,
                'limitation': 'External cut/cap triangulation differs from native; mandatory native parity remains required.'}))
        except GenerationBlocked:
            raise
        except Exception as error:
            _blocked('temperature_geometry', 'Native-derived cut failed: ' + str(error)[:300])
    start, end = p['start'], p['end']
    bands = (start - end) // 5 + 1
    ramp = (f'{{if layer_num <= 1}}\nM104 S{start}\n{{else}}\n'
            f'M104 S{{{start} - 5 * min({bands - 1}, int(layer_num * {bands} / (total_layer_count - 1)))}}\n{{endif}}')
    machine, process, filament = profiles['machine'], profiles['process'], profiles['filament']
    if 'layer_change_gcode' not in snapshot['effective']:
        _blocked('hook_unavailable', 'Effective layer-change hook is unavailable.')
    machine['layer_change_gcode'] = snapshot['effective']['layer_change_gcode'] + '\\n' + ramp.replace('\n', '\\n')
    machine['resonance_avoidance'] = '0'
    process.update({'layer_height': str(snapshot['nozzle_mm'] / 2),
                    'initial_layer_print_height': str(snapshot['nozzle_mm'] / 2),
                    'brim_type': 'outer_only', 'brim_width': '5', 'brim_object_gap': '0',
                    'alternate_extra_wall': '0', 'seam_slope_type': 'none', 'overhang_reverse': '0',
                    'precise_z_height': '0', 'enable_wrapping_detection': '0'})
    filament.update({'nozzle_temperature': str(start), 'nozzle_temperature_initial_layer': str(start)})
    return output


def _flow(request, snapshot, destination, config, profiles):
    effective = snapshot['effective']
    nozzle = snapshot['nozzle_mm']
    # Bound geometry to native 0.4 mm/ten-layer asset; wider envelope awaits
    # retained native references, avoiding guessed selection.scale semantics.
    if nozzle != 0.4 or _numeric(effective, 'initial_layer_print_height') != 0.2:
        _blocked('flow_geometry', 'YOLO recipe currently supports 0.4 mm nozzle and 0.2 mm first layer; native-scaled geometry for other cases is pending.')
    asset = config.get('flow_asset', {})
    if asset.get('source_commit') != config['source_commit']:
        _blocked('flow_asset', 'Native YOLO asset source pin does not match the engine.')
    source = _checked_file(asset)
    f32 = lambda value: struct.unpack('f', struct.pack('f', value))[0]
    layer_height = f32(_numeric(effective, 'layer_height'))
    width = f32(_numeric(effective, 'line_width'))
    native_nozzle = f32(nozzle)
    native_layer = native_nozzle / 2.0
    native_initial = max(_numeric(effective, 'initial_layer_print_height'), native_layer)
    native_surface_width = f32(native_nozzle * f32(1.2))
    if not layer_height > 0 or not width >= layer_height:
        _blocked('flow_speed', 'YOLO needs explicit absolute line width at least the original layer height.')
    area = layer_height * (width - layer_height * (1 - math.pi / 4))
    flow = _numeric(effective, 'filament_flow_ratio')
    max_volume = _numeric(effective, 'filament_max_volumetric_speed')
    if flow <= 0 or max_volume <= 0:
        _blocked('flow_speed', 'YOLO flow ratio and volumetric limit must be positive.')
    max_speed = max_volume / (area * (flow + 0.05) / flow)
    speeds = {key: str(math.floor(min(_numeric(effective, key), max_speed))) for key in ('internal_solid_infill_speed', 'top_surface_speed')}
    settings = {
        'wall_loops': '1', 'only_one_wall_top': '1', 'thick_internal_bridges': '0',
        'enable_extra_bridge_layer': 'disabled', 'internal_bridge_density': '100%',
        'sparse_infill_density': '35%', 'min_width_top_surface': '100%',
        'bottom_shell_layers': '2', 'top_shell_layers': '5', 'top_shell_thickness': '0',
        'bottom_shell_thickness': '0', 'detect_thin_wall': '1', 'filter_out_gap_fill': '0',
        'sparse_infill_pattern': 'rectilinear', 'top_surface_line_width': repr(native_surface_width),
        'internal_solid_infill_line_width': repr(native_surface_width), 'top_surface_pattern': 'archimedeanchords',
        'top_solid_infill_flow_ratio': '1', 'infill_direction': '45', 'solid_infill_direction': '135',
        'center_of_surface_pattern': 'each_surface', 'separated_infills': '0',
        'align_infill_direction_to_model': '1', 'ironing_type': 'no ironing',
        'seam_slope_type': 'none', 'gap_fill_target': 'nowhere',
        'calib_flowrate_topinfill_special_order': '1', 'top_surface_fill_order': 'default',
        **speeds,
    }
    namespace = {'c': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    model_settings = ET.Element('config')
    with zipfile.ZipFile(source) as archive:
        if sum(i.file_size for i in archive.infolist()) > parity.MAX_GCODE_BYTES:
            _blocked('flow_asset', 'Oversized native asset archive.')
        model = ET.fromstring(archive.read('3D/3dmodel.model'))
        objects = model.findall('c:resources/c:object', namespace)
        expected = {0.0} | {sign * i / 100 for i in range(1, 6) for sign in (-1, 1)}
        seen = set()
        for obj in objects:
            name = obj.get('name', '')
            if not name.startswith('flowrate_'):
                _blocked('flow_asset', 'Unexpected YOLO object label.')
            try:
                modifier = float(name[9:].replace('m', '-', 1))
            except ValueError:
                _blocked('flow_asset', 'Malformed YOLO modifier.')
            seen.add(modifier)
            node = ET.SubElement(model_settings, 'object', {'id': obj.attrib['id']})
            for key, value in {'name': name, **settings, 'print_flow_ratio': repr((flow + f32(modifier)) / flow)}.items():
                ET.SubElement(node, 'metadata', {'key': key, 'value': value})
        if seen != expected or len(objects) != 11:
            _blocked('flow_asset', 'YOLO requires all eleven native patches, without duplicates.')
        output = destination / 'model.3mf'
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
            for info in archive.infolist():
                if info.filename != 'Metadata/model_settings.config':
                    target.writestr(info.filename, archive.read(info))
            target.writestr('Metadata/model_settings.config', ET.tostring(model_settings, encoding='utf-8', xml_declaration=True))
    profiles['machine']['resonance_avoidance'] = '0'
    profiles['process'].update({'layer_height': repr(native_layer), 'initial_layer_print_height': repr(native_initial),
                               'alternate_extra_wall': '0', 'reduce_crossing_wall': '1',
                               'enable_wrapping_detection': '0', 'max_volumetric_extrusion_rate_slope': '0'})
    return output


def _flow_layout_arguments(snapshot):
    """Match native GUI 3MF import: preserve layout, center the whole group.

    Plater.cpp10004–10006 and OrcaSlicer.cpp4919–4937 call the same Model
    helper. BuildVolume::bed_center is the printable-area bounding-box center.
    Forced auto-arrangement changes labeled patch placement and print ordering.
    """
    raw = snapshot['effective'].get('printable_area')
    if not isinstance(raw, str):
        _blocked('flow_layout', 'YOLO needs explicit effective printable_area for native group centering.')
    points = []
    for token in raw.split(','):
        match = re.fullmatch(r'(-?(?:\d+(?:\.\d*)?|\.\d+))x(-?(?:\d+(?:\.\d*)?|\.\d+))', token.strip())
        if match is None:
            _blocked('flow_layout', 'YOLO effective printable_area is malformed; no placement default is permitted.')
        point = tuple(float(value) for value in match.groups())
        if any(not math.isfinite(value) or abs(value) > 10000 for value in point):
            _blocked('flow_layout', 'YOLO effective printable_area exceeds the bounded native layout.')
        points.append(point)
    if not 3 <= len(points) <= 128:
        _blocked('flow_layout', 'YOLO needs a bounded explicit effective printable-area polygon.')
    low = [min(p[i] for p in points) for i in range(2)]
    high = [max(p[i] for p in points) for i in range(2)]
    if any(low[i] >= high[i] for i in range(2)):
        _blocked('flow_layout', 'YOLO printable-area extent is degenerate.')
    center = ','.join(format((low[i] + high[i]) / 2, '.17g') for i in range(2))
    return ['--center', center, '--arrange', '0']


def prepare_inputs(request, snapshot, output_dir, config):
    """Stage the shared stock recipe bundle without invoking a slicer."""
    request = contract.validate_request(request, now=config.get('now'))
    snapshot = contract.validate_context(snapshot)
    if request['context_sha256'] != contract.digest(snapshot) or request['origin_id'] != snapshot['origin_id']:
        _blocked('context_mismatch', 'Generation request does not match its immutable original context.')
    kind = request['calibration']
    if kind in BLOCKERS:
        _blocked('native_engine_required', BLOCKERS[kind])
    source = config.get('source_commit')
    if parity.PINS.get(source) != snapshot['runtime'] or config.get('runtime') != snapshot['runtime']:
        _blocked('runtime_pin', 'Snapshot and configured exact engine source/runtime differ.')
    effective = snapshot['effective']
    if effective.get('belt_printer') not in ('0', 'false'):
        _blocked('belt_unavailable', 'Explicit non-belt effective configuration is required.')
    if _numeric(effective, 'nozzle_diameter') != snapshot['nozzle_mm']:
        _blocked('nozzle', 'Effective single-tool nozzle differs from the context.')
    bed = effective.get('curr_bed_type')
    if not bed:
        _blocked('bed_unavailable', 'Effective bed type is unavailable; no CLI default is allowed.')
    destination = Path(output_dir).resolve()
    if destination.exists() and any(destination.iterdir()):
        _blocked('output_exists', 'Generation requires a new empty job directory.')
    destination.mkdir(parents=True, exist_ok=True)
    profiles = _configs(snapshot)
    layout_arguments = _flow_layout_arguments(snapshot) if kind == 'flow_ratio_yolo' else ['--arrange', '1']
    model = (_temperature if kind == 'temperature' else _flow)(request, snapshot, destination, config, profiles)
    for role, value in profiles.items():
        (destination / (role + '.json')).write_bytes(contract.canonical(value))
    merged = copy.deepcopy(snapshot['effective'])
    for profile in profiles.values():
        merged.update({key: value for key, value in profile.items()
                       if key not in ('name', 'from', 'type', 'instantiation', 'post_process')})
    merged['post_process'] = ''
    for key in list(merged):
        if key.startswith('print_host') or key in ('printhost_apikey', 'printhost_user', 'printhost_password'):
            merged.pop(key)
    (destination / 'native-effective.json').write_bytes(contract.canonical(merged))
    inputs = parity.generation_inputs(request, snapshot, source)
    (destination / 'inputs.json').write_bytes(contract.canonical(inputs))
    return {'request': request, 'snapshot': snapshot, 'destination': destination,
            'model': model, 'profiles': profiles, 'native_effective': merged, 'inputs': inputs,
            'layout_arguments': layout_arguments}


def generate(request, snapshot, output_dir, config):
    executable = _checked_file({'path': config.get('executable', ''), 'sha256': config.get('executable_sha256')}, maximum=2 * 1024**3)
    staged = prepare_inputs(request, snapshot, output_dir, config)
    request, snapshot, destination = staged['request'], staged['snapshot'], staged['destination']
    model, source, bed = staged['model'], config['source_commit'], snapshot['effective']['curr_bed_type']
    data = destination / 'orca-data'
    data.mkdir()
    argv = [str(executable), '--datadir', str(data), '--load-settings', str(destination / 'machine.json') + ';' + str(destination / 'process.json'),
            '--load-filaments', str(destination / 'filament.json'), '--curr-bed-type', bed,
            *staged['layout_arguments'], '--orient', '0', '--strict', '--outputdir', str(destination),
            '--export-settings', str(destination / 'effective.json'), '--slice', '0', str(model)]
    (destination / 'invocation.json').write_bytes(contract.canonical({'argv': argv, 'source_commit': source, 'executable_sha256': config['executable_sha256']}))
    runner = config.get('runner')
    if runner:
        # Trusted in-process adapter only; never accepted from request JSON.
        returncode = runner(argv, destination)
    else:
        environment = os.environ.copy()
        environment.update({key: str(destination / key.lower()) for key in
                            ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'WEBVIEW2_USER_DATA_FOLDER')})
        environment['OMP_NUM_THREADS'] = '2'
        with (destination / 'slice.log').open('wb') as log:
            try:
                result = subprocess.run(argv, cwd=destination, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=min(config.get('timeout_seconds', 180), 300), env=environment, check=False)
                returncode = result.returncode
            except subprocess.TimeoutExpired:
                _blocked('slice_timeout', 'Pinned stock Orca exceeded its job deadline.')
    if returncode != 0:
        _blocked('slice_failed', 'Stock Orca slicing failed; retained slice.log contains diagnostics.')
    result_file = destination / 'result.json'
    if result_file.exists():
        result = json.loads(result_file.read_text())
        if result.get('return_code') != 0 or result.get('warnings'):
            _blocked('slice_warnings', 'Stock Orca reported failure or warnings; no qualification is allowed.')
    outputs = list(destination.glob('*.gcode'))
    if len(outputs) != 1:
        _blocked('artifact', 'Stock Orca did not produce exactly one G-code artifact.')
    artifact = outputs[0]
    inputs = parity.generation_inputs(request, snapshot, source)
    (destination / 'inputs.json').write_bytes(contract.canonical(inputs))
    reference = config.get('native_reference')
    if reference:
        manifest_path = _checked_file(reference['manifest'])
        manifest = json.loads(manifest_path.read_text())
        report = parity.evaluate(artifact, _checked_file(reference['gcode']), manifest, inputs)
    else:
        report = parity.unqualified(artifact, inputs, 'No independent native UI reference with matching exact inputs has been retained.')
    (destination / 'parity.json').write_bytes(contract.canonical(report))
    prepared = {key: request[key] for key in ('request_id', 'origin_id', 'context_sha256', 'calibration', 'parameters')}
    prepared.update({'schema': 'helix-orca-v1-prepared/v1', 'request_sha256': contract.digest(request),
                     'artifact': parity.file_record(artifact), 'generator': {'build': source, 'route': 'stock-cli-recipe-v1'},
                     'parity': {'qualified': report['qualified'], 'report_sha256': contract.digest(report), 'reason': report['reason']}, 'not_applied': True})
    prepared = contract.validate_prepared(prepared, request)
    (destination / 'prepared.json').write_bytes(contract.canonical(prepared))
    return prepared
