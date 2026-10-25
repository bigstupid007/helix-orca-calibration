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


def _numeric_vector(mapping, key):
    if key not in mapping or not isinstance(mapping[key], str):
        _blocked('effective_unavailable', 'Effective ' + key + ' is unavailable.')
    raw = mapping[key].strip()
    try:
        decoded = json.loads(raw)
        values = decoded if isinstance(decoded, list) else [decoded]
    except (ValueError, TypeError):
        values = [item.strip() for item in re.split(r'[;,]', raw) if item.strip()]
    try:
        result = [float(item) for item in values]
    except (ValueError, TypeError):
        _blocked('effective_malformed', 'Effective ' + key + ' is not a finite vector.')
    if not result or any(not math.isfinite(item) for item in result):
        _blocked('effective_malformed', 'Effective ' + key + ' is not a finite vector.')
    return result


def _origin_numeric(snapshot, key):
    """Resolve a filament vector at the explicit V2 originating slot."""
    if snapshot.get('schema') != 'helix-orca-v1-context/v2':
        return _numeric(snapshot['effective'], key)
    values = _numeric_vector(snapshot['effective'], key)
    index = snapshot['origin_filament']['slot_number'] - 1
    if index < 0 or index >= len(values):
        _blocked('effective_unavailable', 'Effective ' + key + ' lacks the originating filament slot.')
    return values[index]


def _slot_serialized_value(value, index, count):
    """Project one exact active-filament vector cell into a CLI preset slot."""
    if not isinstance(value, str):
        return value
    raw = value.strip()
    try:
        decoded = json.loads(raw)
        if isinstance(decoded, list) and len(decoded) == count:
            selected = decoded[index]
            return selected if isinstance(selected, str) else json.dumps(selected, separators=(',', ':'))
    except (ValueError, TypeError):
        pass
    cells = raw.split(';')
    if len(cells) == count and all(cell.strip() for cell in cells):
        return cells[index].strip()
    return value


def _filament_slot_profiles(snapshot, origin_profile):
    """Stage one official CLI filament preset per complete active V2 slot."""
    slots = sorted(snapshot['filament_slots'], key=lambda item: item['slot_number'])
    result = []
    for slot in slots:
        profile = copy.deepcopy(origin_profile)
        index = slot['slot_number'] - 1
        for key in tuple(profile):
            if key not in ('name', 'from', 'type', 'instantiation') and key in snapshot['effective']:
                profile[key] = _slot_serialized_value(snapshot['effective'][key], index, len(slots))
        profile['name'] = slot['preset_name']
        result.append(profile)
    return result


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
        _blocked('temperature_envelope', 'Stock Temperature recipe currently supports scaled 0.4/0.6 mm Marlin/Klipper towers only; other inputs need native qualification.')
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
    if not nozzle > 0:
        _blocked('flow_geometry', 'YOLO requires a positive explicit nozzle diameter.')
    pass_number = request['parameters']['pass']
    asset_key = 'flow_asset' if pass_number == 1 else 'flow_fine_asset'
    asset = config.get(asset_key)
    if not asset:
        _blocked('flow_asset', 'Native YOLO ' + ('Recommended' if pass_number == 1 else 'Perfectionist') +
                 ' requires its separate pinned ' + asset_key + '.')
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
    flow = _origin_numeric(snapshot, 'filament_flow_ratio')
    max_volume = _origin_numeric(snapshot, 'filament_max_volumetric_speed')
    if flow <= 0 or max_volume <= 0:
        _blocked('flow_speed', 'YOLO flow ratio and volumetric limit must be positive.')
    # CalibUtils.cpp:209 uses the variant's largest positive additive offset.
    max_modifier = 0.05 if pass_number == 1 else 0.035
    max_speed = max_volume / (area * (flow + max_modifier) / flow)
    speeds = {key: str(math.floor(min(_numeric(effective, key), max_speed))) for key in ('internal_solid_infill_speed', 'top_surface_speed')}
    settings = {
        'wall_loops': '1', 'only_one_wall_top': '1', 'thick_internal_bridges': '0',
        'enable_extra_bridge_layer': 'disabled', 'internal_bridge_density': '100%',
        'sparse_infill_density': '35%', 'min_width_top_surface': '100%',
        'bottom_shell_layers': '2', 'top_shell_layers': '5', 'top_shell_thickness': '0',
        'bottom_shell_thickness': '0', 'detect_thin_wall': '1', 'filter_out_gap_fill': '0',
        'sparse_infill_pattern': 'rectilinear', 'top_surface_line_width': repr(native_surface_width),
        'internal_solid_infill_line_width': repr(native_surface_width),
        'top_surface_pattern': ('archimedeanchords' if request['parameters'].get('pattern', 'archimedean_chords') == 'archimedean_chords' else 'monotonic'),
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
        original_model = archive.read('3D/3dmodel.model')
        model = ET.fromstring(original_model)
        objects = model.findall('c:resources/c:object', namespace)
        patches = parity.yolo_patch_modifiers(pass_number)
        expected = set(patches.values())
        seen = set()
        for obj in objects:
            name = obj.get('name', '')
            if name not in patches:
                _blocked('flow_asset', 'Unexpected YOLO object label.')
            try:
                modifier = float(name[9:].replace('m', '-', 1))
            except ValueError:
                _blocked('flow_asset', 'Malformed YOLO modifier.')
            seen.add(modifier)
            node = ET.SubElement(model_settings, 'object', {'id': obj.attrib['id']})
            object_settings = {'name': name, **settings,
                               'print_flow_ratio': repr((flow + f32(modifier)) / flow)}
            if snapshot.get('schema') == 'helix-orca-v1-context/v2':
                # BBS_3MF_Importer deserializes this 1-based ModelObject key;
                # unlike --load-filament-ids, it remains authoritative for 3MF.
                object_settings['extruder'] = str(snapshot['origin_filament']['slot_number'])
            for key, value in object_settings.items():
                ET.SubElement(node, 'metadata', {'key': key, 'value': value})
        if seen != expected or len(objects) != len(patches):
            _blocked('flow_asset', 'YOLO requires all ' + str(len(patches)) + ' native variant patches, without duplicates.')
        xy_scale = nozzle / .6 if nozzle / .6 > 1.2 else 1.0
        z_scale = f32((native_initial + 9 * native_layer) / 2)
        centered_model, layout = _center_flow_build(
            original_model, snapshot, len(patches), (xy_scale, xy_scale, z_scale))
        (destination / 'flow-layout.json').write_bytes(contract.canonical(layout))
        output = destination / 'model.3mf'
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
            for info in archive.infolist():
                if info.filename == '3D/3dmodel.model':
                    target.writestr(info.filename, centered_model)
                elif info.filename != 'Metadata/model_settings.config':
                    target.writestr(info.filename, archive.read(info))
            target.writestr('Metadata/model_settings.config', ET.tostring(model_settings, encoding='utf-8', xml_declaration=True))
    profiles['machine']['resonance_avoidance'] = '0'
    profiles['process'].update({'layer_height': repr(native_layer), 'initial_layer_print_height': repr(native_initial),
                               'alternate_extra_wall': '0', 'reduce_crossing_wall': '1',
                               'enable_wrapping_detection': '0', 'max_volumetric_extrusion_rate_slope': '0'})
    return output


def _flow_bed_center(snapshot):
    """BuildVolume::bed_center is the printable-area bounding-box center."""
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
    return [(low[i] + high[i]) / 2 for i in range(2)]


def _center_flow_build(raw, snapshot, patch_count=11, scale=(1.0, 1.0, 1.0)):
    """Apply native group translation to build items, never mesh coordinates.

    The registered Oct15 CLI disables --center (PrintConfig.cpp12818), so its
    dead transform branch cannot be used. Actual BBS import keeps build-item
    instance transforms and explicitly does not bake them into float meshes.
    Preserve resources/vertex XML bytes and all item ordering/linear/Z values.
    """
    center = _flow_bed_center(snapshot)
    if (not isinstance(scale, tuple) or len(scale) != 3
            or any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in scale)):
        _blocked('flow_layout', 'YOLO native scale is malformed.')
    ns = {'c': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    try:
        text = raw.decode('utf-8')
        if '<!DOCTYPE' in text or '<!ENTITY' in text:
            raise ValueError('entities')
        model = ET.fromstring(raw)
        if model.get('unit', 'millimeter') != 'millimeter':
            raise ValueError('units')
        objects = {obj.get('id'): obj for obj in model.findall('c:resources/c:object', ns)}
        items = model.findall('c:build/c:item', ns)
        if (patch_count not in (11, 16) or len(objects) != patch_count or len(items) != patch_count
                or {item.get('objectid') for item in items} != set(objects)):
            raise ValueError('single build instance per patch required')
        translations, world_points = [], []
        for item in items:
            transform = [float(value) for value in item.get('transform', '1 0 0 0 1 0 0 0 1 0 0 0').split()]
            if (len(transform) != 12 or any(not math.isfinite(value) or abs(value) > 10000 for value in transform)
                    or transform[:9] != [1,0,0,0,1,0,0,0,1]):
                raise ValueError('only original identity/translation transforms supported')
            obj = objects[item.get('objectid')]
            vertices = obj.findall('c:mesh/c:vertices/c:vertex', ns)
            if not vertices or len(vertices) > 200000 or obj.find('c:components', ns) is not None:
                raise ValueError('direct bounded mesh vertices required')
            points = []
            for vertex in vertices:
                point = [struct.unpack('f', struct.pack('f', float(vertex.get(axis))))[0] for axis in 'xyz']
                if any(not math.isfinite(value) or abs(value) > 10000 for value in point):
                    raise ValueError('bounded finite float vertices required')
                points.append([(point[i] + transform[9+i]) * scale[i] for i in range(3)])
            if abs(min(point[2] for point in points)) > .000001:
                raise ValueError('original native patches must already rest on bed')
            translations.append(transform)
            world_points.extend(points)
        low = [min(point[i] for point in world_points) for i in range(3)]
        high = [max(point[i] for point in world_points) for i in range(3)]
        shift = [center[i] - (low[i]+high[i])/2 for i in range(2)]
        builds = list(re.finditer(r'<build\b[^>]*>(.*?)</build\s*>', text, re.S))
        resources = list(re.finditer(r'<resources\b[^>]*>.*?</resources\s*>', text, re.S))
        if len(builds) != 1 or len(resources) != 1:
            raise ValueError('original unprefixed core XML layout required')
        transforms = iter(translations)
        count = 0
        def translate(match):
            nonlocal count
            original = match[0]
            values = list(next(transforms))
            values[0], values[4], values[8] = scale
            values[9] = values[9] * scale[0] + shift[0]
            values[10] = values[10] * scale[1] + shift[1]
            values[11] = values[11] * scale[2]
            value = ' '.join(format(number,'.17g') for number in values)
            attribute = ' transform="' + value + '"'
            count += 1
            if re.search(r'\s+transform\s*=', original):
                return re.sub(r'\s+transform\s*=\s*([\"\']).*?\1', attribute, original, count=1, flags=re.S)
            return re.sub(r'\s*/>$', attribute + '/>', original)
        replacement = re.sub(r'<item\b[^>]*?/>', translate, builds[0][0], flags=re.S)
        if count != len(items):
            raise ValueError('original self-closing core build items required')
        centered = (text[:builds[0].start()] + replacement + text[builds[0].end():]).encode('utf-8')
        unchanged_resources = re.search(rb'<resources\b[^>]*>.*?</resources\s*>', centered, re.S)[0]
        if unchanged_resources != resources[0][0].encode('utf-8'):
            raise ValueError('resource mesh XML changed')
    except (ValueError, TypeError, KeyError, OverflowError, ET.ParseError, UnicodeError, StopIteration):
        _blocked('flow_layout', 'Unsupported or malformed YOLO asset build layout; no geometry or transform approximation is permitted.')
    return centered, {'policy':'native-group-build-translation-v1', 'source_model_xml_sha256':hashlib.sha256(raw).hexdigest(),
        'centered_model_xml_sha256':hashlib.sha256(centered).hexdigest(),
        'unchanged_resources_xml_sha256':hashlib.sha256(unchanged_resources).hexdigest(),
        'native_float_group_bounds_mm':[low,high], 'bed_center_mm':center, 'uniform_translation_xy_mm':shift,
        'build_instances':len(items), 'mesh_coordinates_changed':False,
        'native_relative_scale_xyz':list(scale), 'cli_arguments':['--arrange','0']}


def prepare_inputs(request, snapshot, output_dir, config):
    """Stage the shared stock recipe bundle without invoking a slicer."""
    current = request.get('schema') == 'helix-orca-v1-request/v2'
    request = (contract.validate_request_v2(request, now=config.get('now')) if current
               else contract.validate_request(request, now=config.get('now')))
    snapshot = contract.validate_context_v2(snapshot) if current else contract.validate_context(snapshot)
    if request['context_sha256'] != contract.digest(snapshot) or request['origin_id'] != snapshot['origin_id']:
        _blocked('context_mismatch', 'Generation request does not match its immutable original context.')
    kind = request['calibration']
    if kind in BLOCKERS:
        _blocked('native_engine_required', BLOCKERS[kind])
    source = config.get('source_commit')
    runtime_identity = {key: snapshot['runtime'][key] for key in ('version', 'build')}
    if parity.PINS.get(source) != runtime_identity or config.get('runtime') != runtime_identity:
        _blocked('runtime_pin', 'Snapshot and configured exact engine source/runtime differ.')
    effective = snapshot['effective']
    if effective.get('belt_printer') not in ('0', 'false'):
        _blocked('belt_unavailable', 'Explicit non-belt effective configuration is required.')
    if current:
        nozzles = _numeric_vector(effective, 'nozzle_diameter')
        if any(value != snapshot['nozzle_mm'] for value in nozzles):
            _blocked('nozzle', 'Effective nozzle vector differs from the explicit V2 context.')
    elif _numeric(effective, 'nozzle_diameter') != snapshot['nozzle_mm']:
        _blocked('nozzle', 'Effective single-tool nozzle differs from the context.')
    bed = effective.get('curr_bed_type')
    if not bed:
        _blocked('bed_unavailable', 'Effective bed type is unavailable; no CLI default is allowed.')
    destination = Path(output_dir).resolve()
    if destination.exists() and any(destination.iterdir()):
        _blocked('output_exists', 'Generation requires a new empty job directory.')
    destination.mkdir(parents=True, exist_ok=True)
    profiles = _configs(snapshot)
    layout_arguments = ['--arrange', '0' if kind == 'flow_ratio_yolo' else '1']
    if kind == 'flow_ratio_yolo':
        _flow_bed_center(snapshot)  # Explicit geometry required before asset preparation.
    model = (_temperature if kind == 'temperature' else _flow)(request, snapshot, destination, config, profiles)
    for role, value in profiles.items():
        (destination / (role + '.json')).write_bytes(contract.canonical(value))
    filament_paths = [destination / 'filament.json']
    if current:
        filament_profiles = _filament_slot_profiles(snapshot, profiles['filament'])
        filament_paths = []
        for index, profile in enumerate(filament_profiles, 1):
            path = destination / ('filament-' + str(index) + '.json')
            path.write_bytes(contract.canonical(profile))
            filament_paths.append(path)
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
            'layout_arguments': layout_arguments, 'filament_paths': filament_paths}


def _slice_argv(executable, data, destination, staged, bed, current):
    request, snapshot, model = staged['request'], staged['snapshot'], staged['model']
    argv = [str(executable), '--datadir', str(data), '--load-settings', str(destination / 'machine.json') + ';' + str(destination / 'process.json'),
            '--load-filaments', ';'.join(str(path) for path in staged['filament_paths']), '--curr-bed-type', bed,
            *staged['layout_arguments'], '--orient', '0', '--strict', '--outputdir', str(destination),
            '--export-settings', str(destination / 'effective.json'), '--slice', '0', str(model)]
    if current and request['calibration'] == 'temperature':
        # OrcaSlicer.cpp maps the one STL input to this 1-based loaded-filament
        # index.  3MF rejects this option and carries its assignment in object
        # metadata instead (the Flow path above).
        argv[argv.index('--strict'):argv.index('--strict')] = [
            '--load-filament-ids', str(snapshot['origin_filament']['slot_number'])]
    return argv


def generate(request, snapshot, output_dir, config):
    current = request.get('schema') == 'helix-orca-v1-request/v2'
    qualification = contract.validate_build_qualification_v2(config.get('build_qualification')) if current else None
    executable = _checked_file({'path': config.get('executable', ''), 'sha256': config.get('executable_sha256')}, maximum=2 * 1024**3)
    if current and config.get('executable_sha256') != contract.ORCA_EXECUTABLE_SHA256_V2:
        _blocked('runtime_pin', 'V2 stock slicing requires the exact official Orca executable.')
    staged = prepare_inputs(request, snapshot, output_dir, config)
    request, snapshot, destination = staged['request'], staged['snapshot'], staged['destination']
    model, source, bed = staged['model'], config['source_commit'], snapshot['effective']['curr_bed_type']
    data = destination / 'orca-data'
    data.mkdir()
    argv = _slice_argv(executable, data, destination, staged, bed, current)
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
    result = {'return_code': 0, 'warnings': []}
    if result_file.exists():
        result = json.loads(result_file.read_text())
        if result.get('return_code') != 0:
            _blocked('slice_failed', 'Stock Orca reported a slicing failure.')
        if not current and result.get('warnings'):
            _blocked('slice_warnings', 'Stock Orca reported warnings; historical V1 remains fail-closed.')
    outputs = list(destination.glob('*.gcode'))
    if len(outputs) != 1:
        _blocked('artifact', 'Stock Orca did not produce exactly one G-code artifact.')
    artifact = outputs[0]
    inputs = parity.generation_inputs(request, snapshot, source)
    (destination / 'inputs.json').write_bytes(contract.canonical(inputs))
    if current:
        warnings = []
        for item in result.get('warnings', []):
            if not isinstance(item, dict):
                _blocked('slice_warnings', 'Stock Orca returned an unstructured warning.')
            code, message = item.get('error_code'), item.get('message', item.get('msg'))
            known = contract.KNOWN_WARNINGS_V2.get(code) == message
            warnings.append(contract.validate_warning_v2(dict(level=item.get('level', 0), message=message,
                error_code=code, params=item.get('params', []), known=known, requires_ack=known)))
        processing = dict(error_code=0, warnings=warnings,
                          status='ready' if all(item['known'] for item in warnings) else 'blocked')
        prepared = {key: request[key] for key in ('request_id', 'origin_id', 'context_sha256', 'calibration', 'parameters')}
        prepared.update(schema='helix-orca-v1-prepared/v2', request_sha256=contract.digest(request),
            artifact=parity.file_record(artifact), generator=dict(source_commit=source,
                route='stock-cli-recipe-v2', executable_sha256=config['executable_sha256'],
                qualification_sha256=contract.digest(qualification),
                machine_sha256=contract.machine_sha256_v2(snapshot)), processing=processing)
        prepared = contract.validate_prepared_v2(prepared, request)
        (destination / 'prepared.json').write_bytes(contract.canonical(prepared))
        return prepared
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
