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
                     'top_surface_speed': '30', 'internal_solid_infill_speed': '40',
                     'printable_area': '0x0,300x0,300x300,0x300'}
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
        self.assertEqual(invocation[invocation.index('--arrange')+1], '1')
        self.assertNotIn('--center', invocation)

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

    def test_source_removed_compatibility_metadata_is_not_effective_fallback(self):
        for role in ('printer', 'process', 'filament'):
            self.snapshot[role]['edited']['config']['compatible_printers_condition'] = 'original compatibility metadata'
            self.snapshot[role]['edited']['config']['inherits'] = 'saved parent identity'
        self.request['context_sha256'] = contract.digest(self.snapshot)
        result = self.run_generation()
        self.assertFalse(result['parity']['qualified'])
        for role in ('machine', 'process', 'filament'):
            config = json.loads((self.root / ('job/' + role + '.json')).read_text())
            self.assertNotIn('compatible_printers_condition', config)
            self.assertNotIn('inherits', config)

    def test_effective_only_dynamic_axis_options_are_never_silently_defaulted(self):
        self.snapshot['effective']['machine_max_acceleration_x'] = '2000,2000'
        self.snapshot['effective']['machine_max_speed_x'] = '200,200'
        self.request['context_sha256'] = contract.digest(self.snapshot)
        self.run_generation()
        machine = json.loads((self.root / 'job/machine.json').read_text())
        self.assertEqual(machine['machine_max_acceleration_x'], '2000,2000')
        self.assertEqual(machine['machine_max_speed_x'], '200,200')

    def test_staging_is_shared_with_native_adapter_without_slicing(self):
        del self.config['executable']
        staged = generation.prepare_inputs(self.request, self.snapshot, self.root / 'job', self.config)
        self.assertEqual(staged['native_effective']['nozzle_temperature'], '230')
        self.assertTrue((self.root / 'job/native-effective.json').is_file())
        self.assertFalse((self.root / 'job/invocation.json').exists())

    def test_effective_post_processing_must_be_known(self):
        del self.snapshot['effective']['post_process']
        for role in ('printer', 'process', 'filament'):
            for state in ('saved', 'edited'):
                self.snapshot[role][state]['config'].pop('post_process')
        self.request['context_sha256'] = contract.digest(self.snapshot)
        with self.assertRaisesRegex(generation.GenerationBlocked, 'post_process is unavailable'):
            self.run_generation()

    def test_klipper_temperature_can_attempt_but_still_needs_native_parity(self):
        self.snapshot['effective']['gcode_flavor'] = 'klipper'
        self.request['context_sha256'] = contract.digest(self.snapshot)
        result = self.run_generation()
        self.assertFalse(result['parity']['qualified'])
        machine = json.loads((self.root / 'job/machine.json').read_text())
        self.assertEqual(machine['gcode_flavor'], 'klipper')

    def test_native_yolo_assets_keep_all_labels_and_distinct_object_ratios(self):
        asset = self.root / 'Orca-LinearFlow.3mf'
        ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        model = ET.Element('{' + ns + '}model')
        resources = ET.SubElement(model, '{' + ns + '}resources')
        names = ['flowrate_0'] + [f'flowrate_{sign}0.0{i}' for sign in ('', 'm') for i in range(1, 6)]
        for index, name in enumerate(names):
            obj = ET.SubElement(resources, '{' + ns + '}object', {'id': str(index+1), 'name': name})
            mesh = ET.SubElement(obj, '{' + ns + '}mesh')
            vertices = ET.SubElement(mesh, '{' + ns + '}vertices')
            for x,y,z in ((0,0,0),(30,0,0),(0,30,2)):
                ET.SubElement(vertices, '{' + ns + '}vertex', {'x':str(x),'y':str(y),'z':str(z)})
        build = ET.SubElement(model, '{' + ns + '}build')
        for index in range(len(names)):
            ET.SubElement(build, '{' + ns + '}item', {'objectid':str(index+1),
                         'transform':f'1 0 0 0 1 0 0 0 1 {index*31} {index%3*32} 0'})
        # Preserve ordinary public-asset default-core namespace serialization.
        original_model = ET.tostring(model).replace(b'ns0:',b'').replace(b'xmlns:ns0=',b'xmlns=')
        with zipfile.ZipFile(asset, 'w') as archive:
            archive.writestr('3D/3dmodel.model', original_model)
        self.request.update(calibration='flow_ratio_yolo', parameters={'pass': 1})
        self.config['flow_asset'] = {'path': str(asset), 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(), 'source_commit': self.pin}
        result = self.run_generation()
        self.assertFalse(result['parity']['qualified'])
        with zipfile.ZipFile(self.root / 'job/model.3mf') as archive:
            config = ET.fromstring(archive.read('Metadata/model_settings.config'))
            centered_model = archive.read('3D/3dmodel.model')
        original_tree, centered_tree = ET.fromstring(original_model), ET.fromstring(centered_model)
        self.assertEqual(ET.tostring(original_tree.find('{'+ns+'}resources')),
                         ET.tostring(centered_tree.find('{'+ns+'}resources')))
        old_items, new_items = (tree.findall('{'+ns+'}build/{'+ns+'}item') for tree in (original_tree,centered_tree))
        self.assertEqual([item.get('objectid') for item in old_items],[item.get('objectid') for item in new_items])
        layout = json.loads((self.root/'job/flow-layout.json').read_text())
        for old,new in zip(old_items,new_items):
            before,after = ([float(value) for value in item.get('transform').split()] for item in (old,new))
            self.assertEqual(before[:9],after[:9]);self.assertEqual(before[11],after[11])
            for axis in range(2):self.assertAlmostEqual(after[9+axis]-before[9+axis],layout['uniform_translation_xy_mm'][axis])
        self.assertEqual(layout['bed_center_mm'],[150,150])
        self.assertFalse(layout['mesh_coordinates_changed'])
        objects = [{m.attrib['key']: m.attrib['value'] for m in obj.findall('metadata')} for obj in config.findall('object')]
        self.assertEqual({x['name'] for x in objects}, set(names))
        self.assertEqual(len({x['print_flow_ratio'] for x in objects}), 11)
        self.assertTrue(all(x['calib_flowrate_topinfill_special_order'] == '1' for x in objects))
        by_name = {item['name']: item for item in objects}
        self.assertEqual(float(by_name['flowrate_0.01']['print_flow_ratio']), 1.0099999997764826)
        self.assertEqual(float(by_name['flowrate_0']['top_surface_line_width']), 0.48000001907348633)
        process = json.loads((self.root / 'job/process.json').read_text())
        self.assertEqual(float(process['layer_height']), 0.20000000298023224)
        invocation = json.loads((self.root/'job/invocation.json').read_text())['argv']
        self.assertEqual(invocation[invocation.index('--arrange')+1], '0')
        self.assertNotIn('--center',invocation)

    def test_yolo_group_center_uses_explicit_native_bounding_box_center(self):
        self.snapshot['effective']['printable_area'] = '-20x10,280x10,280x210,-20x210'
        self.assertEqual(generation._flow_bed_center(self.snapshot), [130,110])
        # Native get_extents uses bounds, not the polygon vertex average.
        self.snapshot['effective']['printable_area'] = '0x0,300x0,0x200'
        self.assertEqual(generation._flow_bed_center(self.snapshot), [150,100])

    def _perfectionist_asset(self, names=None):
        # Synthetic labeled meshes test staging, not real slicing or qualification.
        names = names or ['flowrate_0', 'flowrate_0.005', 'flowrate_0.01', 'flowrate_0.015',
                          'flowrate_0.02', 'flowrate_0.025', 'flowrate_0.03', 'flowrate_0.035',
                          'flowrate_m0.005', 'flowrate_m0.01', 'flowrate_m0.015', 'flowrate_m0.02',
                          'flowrate_m0.025', 'flowrate_m0.03', 'flowrate_m0.035', 'flowrate_m0.04']
        ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        model = ET.Element('model', xmlns=ns)
        resources, build = ET.SubElement(model, 'resources'), ET.SubElement(model, 'build')
        for index, name in enumerate(names):
            obj = ET.SubElement(resources, 'object', id=str(index+1), name=name)
            vertices = ET.SubElement(ET.SubElement(obj, 'mesh'), 'vertices')
            for x,y,z in ((0,0,0),(30,0,0),(0,30,2)):
                ET.SubElement(vertices, 'vertex', x=str(x), y=str(y), z=str(z))
            ET.SubElement(build, 'item', objectid=str(index+1),
                          transform=f'1 0 0 0 1 0 0 0 1 {index%4*31} {index//4*32} 0')
        asset = self.root/'Orca-LinearFlow_fine.3mf'
        with zipfile.ZipFile(asset,'w') as archive:
            archive.writestr('3D/3dmodel.model',ET.tostring(model))
        self.request.update(calibration='flow_ratio_yolo',parameters={'pass':2})
        self.config['flow_fine_asset'] = dict(path=str(asset),sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
                                              source_commit=self.pin)

    def test_perfectionist_stages_sixteen_native_offsets_with_its_own_speed_cap(self):
        self._perfectionist_asset()
        self.snapshot['effective'].update(top_surface_speed='1000',internal_solid_infill_speed='1000')
        self.request['context_sha256'] = contract.digest(self.snapshot)
        original = copy.deepcopy(self.snapshot)
        result = self.run_generation()
        with zipfile.ZipFile(self.root/'job/model.3mf') as archive:
            cfg = ET.fromstring(archive.read('Metadata/model_settings.config'))
        objects = [{m.get('key'):m.get('value') for m in obj.findall('metadata')} for obj in cfg.findall('object')]
        by_name = {item['name']:item for item in objects}
        self.assertEqual(len(objects),16)
        self.assertIn('flowrate_m0.04',by_name)
        self.assertNotIn('flowrate_0.04',by_name)
        self.assertAlmostEqual(float(by_name['flowrate_0.005']['print_flow_ratio']),1.0049999998882413)
        self.assertAlmostEqual(float(by_name['flowrate_m0.04']['print_flow_ratio']),0.9600000008940697)
        # Native CalibUtils .035 ceiling yields142; Recommended .05 would yield140.
        self.assertEqual({item['top_surface_speed'] for item in objects},{'142'})
        self.assertTrue(all(item['top_surface_pattern']=='archimedeanchords' for item in objects))
        self.assertEqual(original,self.snapshot)
        self.assertEqual(result['parameters'],{'pass':2})
        self.assertFalse(result['parity']['qualified'])
        self.assertEqual(json.loads((self.root/'job/inputs.json').read_text())['parameters'],{'pass':2})

    def test_perfectionist_never_falls_back_to_recommended_asset(self):
        self._perfectionist_asset()
        self.config['flow_asset'] = self.config.pop('flow_fine_asset')
        with self.assertRaisesRegex(generation.GenerationBlocked,'flow_fine_asset'):
            self.run_generation()
        self.assertFalse((self.root/'job/invocation.json').exists())

    def test_perfectionist_rejects_missing_duplicate_or_wrong_native_patch(self):
        for names in (['flowrate_0']*16,['flowrate_0','flowrate_0.04'],['flowrate_0']):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as output:
                self._perfectionist_asset(names)
                with self.assertRaises(generation.GenerationBlocked):
                    generation.prepare_inputs(self.request,self.snapshot,Path(output)/'job',self.config)

    def test_yolo_build_translation_changes_only_build_xml_and_blocks_unsupported_transforms(self):
        objects=''.join(f'<object id="{i}"><mesh><vertices><vertex x="{i}" y="0" z="0"/><vertex x="{i+1}" y="1" z="2"/></vertices></mesh></object>' for i in range(1,12))
        items=''.join(f'<item objectid="{i}"/>' for i in range(1,12))
        source=('<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter"><resources>'+objects+'</resources><build>'+items+'</build></model>').encode()
        centered,layout=generation._center_flow_build(source,self.snapshot)
        self.assertEqual(source.split(b'<build>')[0],centered.split(b'<build>')[0])
        self.assertEqual(layout['uniform_translation_xy_mm'],[143.5,149.5])
        self.assertEqual(layout['native_float_group_bounds_mm'],[[1.,0.,0.],[12.,1.,2.]])
        self.assertEqual(layout['build_instances'],11)
        self.assertEqual(layout['cli_arguments'],['--arrange','0'])
        invalid=(source.replace(b'<item objectid="1"/>',b'<item objectid="1" transform="0 -1 0 1 0 0 0 0 1 0 0 0"/>'),
                 source.replace(b'<item objectid="1"/>',b'<item objectid="1" transform="1 0 0 0 1 0 0 0 1 nan 0 0"/>'),
                 source.replace(b'<item objectid="1"/>',b''),source.replace(b'unit="millimeter"',b'unit="inch"'))
        for raw in invalid:
            with self.assertRaises(generation.GenerationBlocked):generation._center_flow_build(raw,self.snapshot)

    def test_yolo_missing_or_malformed_layout_never_uses_profile_or_cli_default(self):
        self.request.update(calibration='flow_ratio_yolo', parameters={'pass':1})
        for raw in (None, '', '0x0,300x0', '0x0,0x100,0x300', '0x0,300xnan,300x300', '0x0,10001x0,0x300'):
            if raw is None: self.snapshot['effective'].pop('printable_area',None)
            else: self.snapshot['effective']['printable_area'] = raw
            self.request['context_sha256'] = contract.digest(self.snapshot)
            with self.subTest(raw=raw), self.assertRaises(generation.GenerationBlocked) as error:
                self.run_generation()
            self.assertIn(error.exception.code, ('flow_layout', 'effective_unavailable'))
            self.assertFalse((self.root/'job/invocation.json').exists())


if __name__ == '__main__':
    unittest.main()
