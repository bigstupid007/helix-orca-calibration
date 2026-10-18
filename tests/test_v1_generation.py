"""Job isolation, explicit effective inputs and fail-closed readiness checks."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from integration import v1_contract as contract
from integration import v1_generation as generation
from integration import v1_parity as parity


class StockGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = self.root / 'model.stl'
        self.model.write_text('test-only geometry; test runner never slices')
        self.exe = self.root / 'orca'
        self.exe.write_text('test-only adapter')
        self.pin = next(iter(parity.PINS))
        effective = {'nozzle_diameter': '0.4', 'belt_printer': '0', 'curr_bed_type': 'High Temp Plate',
                     'gcode_flavor': 'marlin', 'layer_change_gcode': ';existing\\n;[layer_z]',
                     'post_process': '', 'layer_height': '0.2', 'initial_layer_print_height': '0.2',
                     'line_width': '0.45', 'filament_flow_ratio': '1', 'filament_max_volumetric_speed': '12',
                     'top_surface_speed': '30', 'internal_solid_infill_speed': '40'}
        self.snapshot = {'schema': 'helix-orca-v1-context/v1', 'origin_id': '1' * 32,
                         'runtime': parity.PINS[self.pin], 'nozzle_mm': .4, 'effective': effective}
        for role in ('printer', 'process', 'filament'):
            self.snapshot[role] = {state: {'name': role + '-' + state, 'config': effective.copy()} for state in ('saved', 'edited')}
        self.request = {'schema': 'helix-orca-v1-request/v1', 'request_id': '2' * 32,
                        'origin_id': '1' * 32, 'context_sha256': contract.digest(self.snapshot),
                        'calibration': 'temperature', 'parameters': {'start': 230, 'end': 220, 'step': 5, 'scale': True},
                        'created_at': 100, 'expires_at': 200, 'not_applied': True}
        self.config = {'source_commit': self.pin, 'runtime': parity.PINS[self.pin], 'now': 150,
                       'executable': str(self.exe), 'executable_sha256': hashlib.sha256(self.exe.read_bytes()).hexdigest(),
                       'temperature_model': {'path': str(self.model), 'sha256': hashlib.sha256(self.model.read_bytes()).hexdigest(),
                                             'source_commit': self.pin, 'nozzle_mm': .4, 'parameters': self.request['parameters']},
                       'runner': self.runner}

    def runner(self, argv, out):
        (out / 'plate_1.gcode').write_text(';test-only synthetic output\nG90\n')
        (out / 'result.json').write_text(json.dumps({'return_code': 0, 'warnings': []}))
        return 0

    def run_generation(self):
        return generation.generate(self.request, self.snapshot, self.root / 'job', self.config)

    def test_slice_success_never_means_ready_without_native_reference(self):
        prepared = self.run_generation()
        self.assertFalse(prepared['parity']['qualified'])
        self.assertTrue(prepared['not_applied'])
        self.assertEqual(contract.validate_prepared(prepared, self.request), prepared)
        self.assertEqual(parity.file_record(self.root / 'job/plate_1.gcode'), prepared['artifact'])
        self.assertEqual(contract.digest(json.loads((self.root / 'job/parity.json').read_text())), prepared['parity']['report_sha256'])

    def test_job_materialization_preserves_original_profiles_and_native_hook(self):
        old = copy.deepcopy(self.snapshot)
        self.run_generation()
        self.assertEqual(old, self.snapshot)
        machine = json.loads((self.root / 'job/machine.json').read_text())
        self.assertTrue(machine['layer_change_gcode'].startswith(old['effective']['layer_change_gcode']))
        self.assertIn('M104 S', machine['layer_change_gcode'])
        invocation = json.loads((self.root / 'job/invocation.json').read_text())['argv']
        self.assertIn('High Temp Plate', invocation)
        self.assertIn('--strict', invocation)

    def test_effective_unavailable_never_falls_back_to_edited_or_saved(self):
        del self.snapshot['effective']['curr_bed_type']
        self.request['context_sha256'] = contract.digest(self.snapshot)
        with self.assertRaisesRegex(generation.GenerationBlocked, 'bed type'):
            self.run_generation()

    def test_context_and_asset_mismatches_block_before_execution(self):
        self.snapshot['nozzle_mm'] = .6
        with self.assertRaisesRegex(generation.GenerationBlocked, 'immutable original context'):
            self.run_generation()
        self.snapshot['nozzle_mm'] = .4
        self.model.write_text('altered')
        with self.assertRaisesRegex(generation.GenerationBlocked, 'digest'):
            self.run_generation()

    def test_native_state_calibrations_have_specific_shared_blockers(self):
        for kind in generation.BLOCKERS:
            request = dict(self.request, calibration=kind, parameters=contract.DEFAULTS[kind])
            with self.subTest(kind=kind), self.assertRaises(generation.GenerationBlocked) as ctx:
                generation.generate(request, self.snapshot, self.root / kind, self.config)
            self.assertEqual(ctx.exception.code, 'native_engine_required')

    def test_post_process_profile_does_not_run(self):
        self.snapshot['effective']['post_process'] = 'arbitrary-script'
        self.request['context_sha256'] = contract.digest(self.snapshot)
        with self.assertRaisesRegex(generation.GenerationBlocked, 'post-processing'):
            self.run_generation()

    def test_failed_slice_or_warning_never_produces_prepared(self):
        def warned(argv, out):
            self.runner(argv, out)
            (out / 'result.json').write_text(json.dumps({'return_code': 0, 'warnings': ['unexpected']}))
            return 0
        self.config['runner'] = warned
        with self.assertRaisesRegex(generation.GenerationBlocked, 'warnings'):
            self.run_generation()
        self.assertFalse((self.root / 'job/prepared.json').exists())

    def test_native_yolo_assets_keep_all_labels_and_distinct_object_ratios(self):
        asset = self.root / 'Orca-LinearFlow.3mf'
        ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        model = ET.Element('{' + ns + '}model')
        resources = ET.SubElement(model, '{' + ns + '}resources')
        names = ['flowrate_0'] + [f'flowrate_{sign}0.0{i}' for sign in ('', 'm') for i in range(1, 6)]
        for index, name in enumerate(names):
            ET.SubElement(resources, '{' + ns + '}object', {'id': str(index+1), 'name': name})
        with zipfile.ZipFile(asset, 'w') as archive:
            archive.writestr('3D/3dmodel.model', ET.tostring(model))
        self.request.update(calibration='flow_ratio_yolo', parameters={'pass': 1})
        self.config['flow_asset'] = {'path': str(asset), 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(), 'source_commit': self.pin}
        result = self.run_generation()
        self.assertFalse(result['parity']['qualified'])
        with zipfile.ZipFile(self.root / 'job/model.3mf') as archive:
            config = ET.fromstring(archive.read('Metadata/model_settings.config'))
        objects = [{m.attrib['key']: m.attrib['value'] for m in obj.findall('metadata')} for obj in config.findall('object')]
        self.assertEqual({x['name'] for x in objects}, set(names))
        self.assertEqual(len({x['print_flow_ratio'] for x in objects}), 11)
        self.assertTrue(all(x['calib_flowrate_topinfill_special_order'] == '1' for x in objects))


if __name__ == '__main__':
    unittest.main()
