#!/usr/bin/env python3
"""Read local 3MFs; emit only bounded calibration metrics and whitelisted settings.

No extraction, networking, subprocesses, model coordinates, profile names, hooks
or complete project text is emitted. Original archives are never modified.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import posixpath
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

CORE = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
PROD = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
MAX_BYTES = 32 * 1024 * 1024
MAX_VERTICES = 200000
MAX_TRIANGLES = 400000
IDENTITY = ((1., 0., 0., 0.), (0., 1., 0., 0.), (0., 0., 1., 0.), (0., 0., 0., 1.))
NUMERIC = {'brim_width', 'brim_object_gap', 'layer_height', 'initial_layer_print_height', 'extruder'}
BOOLEAN = {'alternate_extra_wall', 'overhang_reverse', 'precise_z_height', 'resonance_avoidance', 'enable_wrapping_detection'}
ENUMS = {'brim_type': {'no_brim', 'outer_only', 'inner_only', 'outer_and_inner', 'auto_brim', 'brim_ear'},
         'seam_slope_type': {'none', 'external', 'all'}}
OBJECT_KEYS = NUMERIC | BOOLEAN | set(ENUMS)
PROJECT_KEYS = {'initial_layer_print_height', 'resonance_avoidance', 'enable_wrapping_detection',
                'nozzle_temperature', 'nozzle_temperature_initial_layer', 'brim_type', 'brim_width', 'brim_object_gap'}


class MetricsError(ValueError):
    pass


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise MetricsError('Invalid numeric geometry or setting') from None
    if not math.isfinite(result) or abs(result) > 1e9:
        raise MetricsError('Nonfinite or excessive geometry or setting')
    return result


def _setting(key, value):
    if key in NUMERIC:
        number = _number(value)
        if not 0 <= number <= 10000:
            raise MetricsError('Setting outside scalar whitelist')
        return number
    if key in BOOLEAN:
        if str(value).lower() not in ('0', '1', 'true', 'false'):
            raise MetricsError('Setting outside boolean whitelist')
        return str(value).lower() in ('1', 'true')
    if key in ENUMS:
        if value not in ENUMS[key]:
            raise MetricsError('Setting outside enumeration whitelist')
        return value
    if key in ('nozzle_temperature', 'nozzle_temperature_initial_layer'):
        values = value if isinstance(value, list) else str(value).split(',')
        if not 1 <= len(values) <= 16:
            raise MetricsError('Temperature vector outside whitelist')
        result = [_number(item) for item in values]
        if not all(0 <= item <= 600 for item in result):
            raise MetricsError('Temperature vector outside whitelist')
        return result
    raise MetricsError('Unapproved setting')


def _matrix(text):
    if text is None:
        return IDENTITY
    values = [_number(value) for value in text.split()]
    if len(values) != 12:
        raise MetricsError('Invalid 3MF transform')
    return tuple(tuple(row) for row in ((values[0], values[3], values[6], values[9]),
                                       (values[1], values[4], values[7], values[10]),
                                       (values[2], values[5], values[8], values[11]), (0., 0., 0., 1.)))


def _multiply(parent, child):
    result = tuple(tuple(math.fsum(parent[i][k] * child[k][j] for k in range(4)) for j in range(4)) for i in range(4))
    if any(not math.isfinite(item) for row in result for item in row):
        raise MetricsError('Nonfinite composed transform')
    return result


def _point(matrix, point):
    result = tuple(math.fsum(matrix[i][j] * point[j] for j in range(3)) + matrix[i][3] for i in range(3))
    if any(not math.isfinite(value) or abs(value) > 1e12 for value in result):
        raise MetricsError('Nonfinite transformed geometry')
    return result


def _sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Project:
    def __init__(self, path):
        if str(path).startswith(('\\\\', '//')):
            raise MetricsError('Only local archive paths are supported')
        self.path = Path(path)
        if not self.path.is_file() or self.path.stat().st_size > MAX_BYTES:
            raise MetricsError('Missing or oversized archive')
        self.started = time.monotonic()
        self.archive = zipfile.ZipFile(self.path)
        entries = self.archive.infolist()
        if len(entries) > 512 or sum(item.file_size for item in entries) > MAX_BYTES:
            self.archive.close()
            raise MetricsError('Archive expansion bound exceeded')
        self.entries = {}
        for item in entries:
            name = self.name(item.filename)
            if name in self.entries:
                self.archive.close()
                raise MetricsError('Duplicate archive entry')
            self.entries[name] = item
        self.models = {}
        self.vertex_count = 0
        self.triangle_count = 0

    @staticmethod
    def name(value):
        value = value.replace('\\', '/').lstrip('/')
        if ':' in value or '..' in value.split('/'):
            raise MetricsError('External or traversing model reference')
        return posixpath.normpath(value)

    def deadline(self):
        if time.monotonic() - self.started > 25:
            raise MetricsError('Metrics deadline exceeded')

    def read(self, name):
        self.deadline()
        if name not in self.entries:
            raise MetricsError('Referenced archive entry is missing')
        return self.archive.read(self.entries[name])

    def xml(self, name):
        value = self.read(name)
        if b'<!doctype' in value.lower() or b'<!entity' in value.lower():
            raise MetricsError('DTD or entity declaration refused')
        return ET.fromstring(value)

    def model(self, name):
        if name not in self.models:
            root = self.xml(name)
            if root.tag != CORE + 'model' or root.attrib.get('unit', 'millimeter') != 'millimeter':
                raise MetricsError('Unsupported model namespace or units')
            objects = {}
            for obj in root.findall(CORE + 'resources/' + CORE + 'object'):
                ident = int(obj.attrib['id'])
                if ident in objects:
                    raise MetricsError('Duplicate model object')
                objects[ident] = obj
            self.models[name] = (root, objects)
        return self.models[name]

    def settings(self):
        objects = []
        name = 'Metadata/model_settings.config'
        if name in self.entries:
            root = self.xml(name)
            for obj in root.findall('object'):
                if len(objects) >= 128:
                    raise MetricsError('Object setting bound exceeded')
                result = {'id': int(obj.attrib['id']), 'name_is_expected_temperature_asset': False, 'settings': {}}
                for metadata in obj.findall('metadata'):
                    key, value = metadata.get('key'), metadata.get('value')
                    if key == 'name':
                        result['name_is_expected_temperature_asset'] = value == 'temperature_tower.drc'
                    elif key in OBJECT_KEYS:
                        result['settings'][key] = _setting(key, value)
                objects.append(result)
        project = {}
        name = 'Metadata/project_settings.config'
        if name in self.entries:
            data = json.loads(self.read(name))
            for key in PROJECT_KEYS:
                if key in data:
                    project[key] = _setting(key, data[key])
        return {'objects': objects, 'project': project}

    def metrics(self):
        bounds = [[math.inf, -math.inf] for _ in range(3)]
        count = {'mesh_instances': 0, 'vertices': 0, 'triangles': 0, 'components': 0,
                 'boundary_edges_by_index': 0, 'nonmanifold_edges_by_index': 0, 'degenerate_triangles': 0}
        volumes = []
        root_name = '3D/3dmodel.model'
        root, _ = self.model(root_name)

        def walk(name, ident, transform, stack):
            self.deadline()
            key = (name, ident)
            if key in stack or len(stack) >= 32:
                raise MetricsError('Cyclic or deep component graph')
            _, objects = self.model(name)
            if ident not in objects:
                raise MetricsError('Missing component object')
            obj = objects[ident]
            mesh = obj.find(CORE + 'mesh')
            components = obj.find(CORE + 'components')
            if (mesh is None) == (components is None):
                raise MetricsError('Unsupported model object shape')
            if components is not None:
                for component in components.findall(CORE + 'component'):
                    target = component.get(PROD + 'path')
                    if target:
                        target = self.name(target if target.startswith('/') else posixpath.join(posixpath.dirname(name), target))
                    else:
                        target = name
                    count['components'] += 1
                    walk(target, int(component.attrib['objectid']), _multiply(transform, _matrix(component.get('transform'))), stack | {key})
                return
            vertices = []
            for node in mesh.findall(CORE + 'vertices/' + CORE + 'vertex'):
                vertices.append(_point(transform, tuple(_number(node.attrib[axis]) for axis in 'xyz')))
            count['vertices'] += len(vertices)
            if count['vertices'] > MAX_VERTICES or not vertices:
                raise MetricsError('Vertex bound exceeded or empty mesh')
            for vertex in vertices:
                for axis in range(3):
                    bounds[axis][0] = min(bounds[axis][0], vertex[axis])
                    bounds[axis][1] = max(bounds[axis][1], vertex[axis])
            edges = Counter()
            origin = vertices[0]
            volume = []
            for index, node in enumerate(mesh.findall(CORE + 'triangles/' + CORE + 'triangle')):
                if index % 1000 == 0:
                    self.deadline()
                indices = tuple(int(node.attrib[key]) for key in ('v1', 'v2', 'v3'))
                if any(value < 0 or value >= len(vertices) for value in indices):
                    raise MetricsError('Invalid triangle vertex index')
                a, b, c = (tuple(vertices[value][axis] - origin[axis] for axis in range(3)) for value in indices)
                cross = (b[1]*c[2] - b[2]*c[1], b[2]*c[0] - b[0]*c[2], b[0]*c[1] - b[1]*c[0])
                volume.append(math.fsum(a[axis]*cross[axis] for axis in range(3))/6)
                u = tuple(b[axis]-a[axis] for axis in range(3))
                v = tuple(c[axis]-a[axis] for axis in range(3))
                area_cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                if len(set(indices)) < 3 or all(value == 0 for value in area_cross):
                    count['degenerate_triangles'] += 1
                for edge in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
                    edges[tuple(sorted(edge))] += 1
                count['triangles'] += 1
                if count['triangles'] > MAX_TRIANGLES:
                    raise MetricsError('Triangle bound exceeded')
            count['mesh_instances'] += 1
            count['boundary_edges_by_index'] += sum(value == 1 for value in edges.values())
            count['nonmanifold_edges_by_index'] += sum(value > 2 for value in edges.values())
            volumes.append(math.fsum(volume))

        items = root.findall(CORE + 'build/' + CORE + 'item')
        if not items:
            raise MetricsError('No build instances')
        for item in items:
            if item.get('printable', '1') not in ('0', 'false'):
                walk(root_name, int(item.attrib['objectid']), _matrix(item.get('transform')), set())
        if not count['mesh_instances']:
            raise MetricsError('No active mesh instances')
        settings = self.settings()
        geometry_hashes = sorted(hashlib.sha256(self.read(name)).hexdigest() for name in self.models)
        return {'sha256': _sha(self.path), 'size': self.path.stat().st_size, 'settings': settings,
                'geometry': {**count, 'finite_vertices': True, 'triangle_indices_valid': True,
                             'world_bounds_mm': bounds, 'world_extents_mm': [pair[1]-pair[0] for pair in bounds],
                             'signed_mesh_volume_mm3': math.fsum(volumes), 'geometry_entry_sha256': geometry_hashes,
                             'limitation': 'Indexed-edge and scalar mesh measurements only; no surface equivalence or physical quality claim.'}}


def inspect(path):
    project = Project(path)
    try:
        return project.metrics()
    finally:
        project.archive.close()


def compare(native, candidate):
    a, b = inspect(native), inspect(candidate)
    aa, bb = a['geometry'], b['geometry']
    return {'schema': 'helix-orca-v1-project-metrics/v1', 'native': a, 'candidate': b,
            'comparison': {'world_extents_delta_candidate_minus_native_mm': [y-x for x, y in zip(aa['world_extents_mm'], bb['world_extents_mm'])],
                           'signed_volume_delta_candidate_minus_native_mm3': bb['signed_mesh_volume_mm3']-aa['signed_mesh_volume_mm3'],
                           'qualified': False, 'reason': 'Whitelisted settings and scalar geometry diagnostics only; mandatory G-code parity remains separate.'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    args = parser.parse_args()
    try:
        report = compare(args.native, args.candidate)
        output = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(output.encode()) > 65536:
            raise MetricsError('Sanitized report bound exceeded')
        print(output)
        return 0
    except Exception:
        # Exception text can contain private names, XML data or file paths.
        print(json.dumps({'schema': 'helix-orca-v1-project-metrics/v1', 'error': 'Local project refused: invalid, unsupported, nonfinite, oversized or unavailable input.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
