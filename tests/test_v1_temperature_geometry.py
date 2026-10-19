"""Preparation provenance failures; fixtures are never generation evidence."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from integration import v1_contract as contract
from integration import v1_engine as engine
from integration import v1_temperature_geometry as geometry


def tetrahedron():
    vertices = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    data = bytearray(80) + struct.pack('<I', len(faces))
    for face in faces:
        values = [0., 0., 0.] + [value for i in face for value in vertices[i]]
        data.extend(struct.pack('<12fH', *values, 0))
    return data


class NativeTemperatureGeometry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.snapshot = {'schema': 'helix-orca-v1-context/v1', 'origin_id': '1'*32,
                         'runtime': {'version': '2.5.0-dev', 'build': '6a7763f0'},
                         'nozzle_mm': .4, 'effective': {'nozzle_diameter': '0.4', 'belt_printer': '0'}}
        for role in ('printer', 'process', 'filament'):
            self.snapshot[role] = {state: {'name': role + '-' + state, 'config': {'identity': state}}
                                   for state in ('saved', 'edited')}
        self.request = {'schema': 'helix-orca-v1-request/v1', 'request_id': '2'*32,
                        'origin_id': self.snapshot['origin_id'], 'context_sha256': contract.digest(self.snapshot),
                        'calibration': 'temperature',
                        'parameters': {'start': 235, 'end': 195, 'step': 5, 'scale': True},
                        'created_at': 100, 'expires_at': 200, 'not_applied': True}
        self.backend = {'executable': self.root/'native', 'resources': self.root/'resources',
                        'receipt': {'adapter': {'sha256': '3'*64}},
                        'receipt_sha256': '4'*64, 'inputs_sha256': '5'*64}
        patcher = patch.object(engine, 'require_native_generation', return_value=self.backend)
        self.native = patcher.start()
        self.addCleanup(patcher.stop)
        self.config = {'now': 150, 'runner': self.runner}

    def runner(self, argv, output):
        self.assertEqual(argv[1], '--prepare-temperature')
        self.assertEqual(len(argv), 6)
        self.assertNotIn('--slice', argv)
        request = json.loads((output/'request.json').read_text())
        self.assertEqual(request, self.request)
        model = output/'model.stl'
        model.write_bytes(tetrahedron())
        metadata = dict(schema='helix-orca-v1-native-temperature-geometry/v1',
                        source_commit=engine.ORCA_SOURCE, calibration='temperature',
                        request_id=request['request_id'], origin_id=request['origin_id'],
                        context_sha256=request['context_sha256'], parameters=request['parameters'],
                        nozzle_mm=.4, model='model.stl', gcode_generated=False, qualified=False,
                        not_applied=True, signed_volume_mm3=1/6, **geometry.inspect_stl(model))
        (output/'temperature-geometry.json').write_text(json.dumps(metadata))
        return 0

    def prepare(self):
        return geometry.prepare(self.request, self.snapshot, self.root/'job', self.config)

    def test_exact_changed_parameters_and_full_context_preserved_without_qualification(self):
        before = copy.deepcopy(self.snapshot)
        receipt = self.prepare()
        self.assertEqual(self.snapshot, before)
        self.assertEqual(receipt['parameters'], self.request['parameters'])
        self.assertEqual(receipt['request_sha256'], contract.digest(self.request))
        self.assertEqual(receipt['context_sha256'], contract.digest(self.snapshot))
        self.assertEqual(receipt['model']['sha256'], engine._sha_file(self.root/'job/model.stl'))
        self.assertEqual(json.loads((self.root/'job/context.json').read_text()), before)
        self.assertFalse(receipt['qualified'])
        self.assertFalse(receipt['gcode_generated'])
        self.assertFalse((self.root/'job/prepared.json').exists())
        self.assertEqual(json.loads((self.root/'job/temperature-model.json').read_text()),
                         {'temperature_model': receipt['model']})

    def test_mismatched_context_blocks_before_native_process(self):
        self.snapshot['effective']['nozzle_diameter'] = '0.6'
        with self.assertRaisesRegex(geometry.TemperatureGeometryBlocked, 'immutable context'):
            self.prepare()
        self.native.assert_not_called()
        self.assertFalse((self.root/'job').exists())

    def test_authoritative_nozzle_and_non_belt_state_required(self):
        for key, value in [('nozzle_diameter', '0.6'), ('nozzle_diameter', '0.4,0.6'), ('belt_printer', '1')]:
            with self.subTest(key=key, value=value):
                snapshot = copy.deepcopy(self.snapshot); snapshot['effective'][key] = value
                request = dict(self.request, context_sha256=contract.digest(snapshot))
                with self.assertRaises(geometry.TemperatureGeometryBlocked):
                    geometry.prepare(request, snapshot, self.root/'job', self.config)
                self.assertFalse((self.root/'job').exists())
        self.native.assert_not_called()

    def test_other_calibration_cannot_use_temperature_prepare(self):
        self.request.update(calibration='flow_ratio_yolo', parameters={'pass': 2})
        with self.assertRaisesRegex(geometry.TemperatureGeometryBlocked, 'Temperature only'):
            self.prepare()
        self.native.assert_not_called()

    def test_native_failure_and_unexpected_gcode_never_produce_model_descriptor(self):
        for mode in ('failure', 'gcode', 'prepared'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                def runner(argv, output):
                    self.runner(argv, output)
                    if mode != 'failure':
                        (output/('unexpected.gcode' if mode == 'gcode' else 'prepared.json')).write_text('test-only')
                    return 1 if mode == 'failure' else 0
                with self.assertRaises(geometry.TemperatureGeometryBlocked):
                    geometry.prepare(self.request, self.snapshot, Path(directory)/'job',
                                     dict(self.config, runner=runner))
                self.assertFalse((Path(directory)/'job/temperature-model.json').exists())

    def test_native_metadata_cannot_replace_requested_parameters_or_claim_qualification(self):
        for field, value in [('parameters', {'start': 230, 'end': 190, 'step': 5, 'scale': True}),
                             ('qualified', True), ('context_sha256', '6'*64), ('triangles', 9)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                def runner(argv, output):
                    self.runner(argv, output)
                    path = output/'temperature-geometry.json'
                    metadata = json.loads(path.read_text()); metadata[field] = value
                    path.write_text(json.dumps(metadata))
                    return 0
                with self.assertRaisesRegex(geometry.TemperatureGeometryBlocked, 'metadata differs'):
                    geometry.prepare(self.request, self.snapshot, Path(directory)/'job',
                                     dict(self.config, runner=runner))

    def test_stl_rejects_truncation_nonfinite_and_degenerate_faces(self):
        for mode in ('truncated', 'nonfinite', 'degenerate'):
            with self.subTest(mode=mode):
                data = tetrahedron()
                if mode == 'truncated': data.pop()
                elif mode == 'nonfinite': struct.pack_into('<f', data, 96, float('nan'))
                else: data[96:132] = struct.pack('<9f', *([0.]*9))
                path = self.root/(mode+'.stl'); path.write_bytes(data)
                with self.assertRaises(geometry.TemperatureGeometryBlocked): geometry.inspect_stl(path)

    def test_existing_directory_or_symlink_cannot_be_overwritten(self):
        (self.root/'job').mkdir()
        sentinel = self.root/'job/sentinel'; sentinel.write_text('preserve')
        with self.assertRaisesRegex(geometry.TemperatureGeometryBlocked, 'new private job'):
            self.prepare()
        self.assertEqual(sentinel.read_text(), 'preserve')
        (self.root/'link').symlink_to(self.root/'job', target_is_directory=True)
        with self.assertRaises(geometry.TemperatureGeometryBlocked):
            geometry.prepare(self.request, self.snapshot, self.root/'link', self.config)


if __name__ == '__main__': unittest.main()
