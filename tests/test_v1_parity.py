"""Qualification must follow independently prepared retained native bytes."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from integration import v1_parity as parity


def temperature_gcode():
    lines = ['G90', 'M83', 'M140 S60', 'M190 S60', 'M109 S230']
    for i, temp in enumerate((230, 230, 225, 225, 220, 220)):
        lines += [';LAYER_CHANGE', f';Z:{(i+1)*.2:.1f}', f'G1 Z{(i+1)*.2:.1f}',
                  f'M104 S{temp}', '; printing object temperature_tower.drc id:0 copy 0',
                  'G1 X1 Y1 E1 F1200', 'G1 X2 Y2 E1', '; stop printing object temperature_tower.drc id:0 copy 0']
    return '\n'.join(lines + ['M104 S0', 'M140 S0']) + '\n'


class NativeParity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidate = self.root / 'candidate.gcode'
        self.native = self.root / 'native.gcode'
        for p in (self.candidate, self.native):
            p.write_text(temperature_gcode())
        evidence = self.root / 'native-actions.txt'
        evidence.write_text('Test-only simulated native capture; not acceptance evidence.')
        self.inputs = {'calibration': 'temperature', 'parameters': {'start': 230, 'end': 220, 'step': 5, 'scale': True},
                       'nozzle_mm': .4, 'context_sha256': 'a' * 64,
                       'source_commit': next(iter(parity.PINS)), 'runtime': next(iter(parity.PINS.values()))}
        self.manifest = {'schema': 'helix-orca-v1-native-reference/v1', 'method': 'native_orca_ui',
                         'imported_candidate': False, 'inputs_sha256': parity.digest(self.inputs),
                         'source_commit': self.inputs['source_commit'], 'runtime': self.inputs['runtime'],
                         'artifact': parity.file_record(self.native),
                         'evidence': [{'path': str(evidence), 'artifact': parity.file_record(evidence)}]}

    def evaluate(self):
        return parity.evaluate(self.candidate, self.native, self.manifest, self.inputs)

    def test_exact_synthetic_reference_qualifies_checker_only(self):
        report = self.evaluate()
        self.assertTrue(report['qualified'], report['reason'])
        self.assertEqual(report['candidate_invariants']['deposition_temperatures'], [220., 225., 230.])

    def test_annotations_not_a_recipe_oracle(self):
        self.candidate.write_text(self.candidate.read_text().replace(';Z:', '; ignored nominal height '))
        self.assertTrue(self.evaluate()['qualified'])

    def test_late_band_cannot_be_repaired_after_first_deposition(self):
        s = self.candidate.read_text().replace('M104 S225', 'M104 S230', 1)
        self.candidate.write_text(s)
        report = self.evaluate()
        self.assertFalse(report['qualified'])
        self.assertIn('deposition', report['reason'])

    def test_nominal_layer_comments_cannot_hide_wrong_z(self):
        self.candidate.write_text(self.candidate.read_text().replace('G1 Z0.6', 'G1 Z0.8'))
        self.assertIn('printed Z', self.evaluate()['reason'])

    def test_motion_or_extrusion_difference_blocks(self):
        self.candidate.write_text(self.candidate.read_text().replace('G1 X2 Y2 E1', 'G1 X3 Y2 E1', 1))
        report = self.evaluate()
        self.assertFalse(report['qualified'])
        self.assertTrue(report['differences'])
        self.assertIn('executable behavior', report['reason'])
        self.assertFalse(report['observations']['motion_extrusion_equal'])
        self.assertTrue(report['observations']['heater_stream_equal'])

    def test_bed_change_blocks_even_with_correct_nozzle(self):
        self.candidate.write_text(self.candidate.read_text().replace('M140 S60', 'M140 S35'))
        self.assertFalse(self.evaluate()['qualified'])

    def test_self_reference_and_recipe_import_rejected(self):
        self.assertFalse(parity.evaluate(self.native, self.native, self.manifest, self.inputs)['qualified'])
        self.manifest['imported_candidate'] = True
        self.assertFalse(self.evaluate()['qualified'])

    def test_wrong_build_or_profiles_rejected(self):
        self.manifest['inputs_sha256'] = '0' * 64
        self.assertFalse(self.evaluate()['qualified'])

    def test_evidence_changed_blocks(self):
        Path(self.manifest['evidence'][0]['path']).write_text('changed')
        self.assertFalse(self.evaluate()['qualified'])

    def test_shutdown_and_external_actions_rejected(self):
        self.candidate.write_text(self.candidate.read_text().replace('M104 S0', 'SAVE_CONFIG'))
        self.assertFalse(self.evaluate()['qualified'])

    def klipper_pair(self):
        self.inputs['effective'] = {'gcode_flavor': 'klipper', 'use_relative_e_distances': '1',
                                   'machine_start_gcode': 'PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]',
                                   'machine_end_gcode': 'PRINT_END', 'curr_bed_type': 'High Temp Plate',
                                   'hot_plate_temp_initial_layer': '60', 'hot_plate_temp': '60',
                                   'printable_area': '0x0,300x0,300x300,0x300', 'printable_height': '290'}
        text = temperature_gcode().replace('M190 S60\n', '').replace('M109 S230\n', 'PRINT_START BED_TEMP=60 EXTRUDER_TEMP=230\n')
        text = text.replace('M104 S0\nM140 S0\n', 'PRINT_END\n')
        self.candidate.write_text(text)
        self.native.write_text(text)
        self.manifest.update(inputs_sha256=parity.digest(self.inputs), artifact=parity.file_record(self.native))

    def test_exact_accepted_klipper_macro_invocations_compare_without_physical_claim(self):
        self.klipper_pair()
        report = self.evaluate()
        self.assertTrue(report['qualified'], report['reason'])
        semantics = report['candidate_invariants']['macro_semantics']
        self.assertFalse(semantics['physical_readiness'])
        self.assertIn('unobserved', semantics['macro_internals'])
        self.assertEqual(semantics['start'], 'PRINT_START BED_TEMP=60 EXTRUDER_TEMP=230')

    def test_changed_klipper_macro_arguments_or_effective_abi_block(self):
        self.klipper_pair()
        self.candidate.write_text(self.candidate.read_text().replace('EXTRUDER_TEMP=230', 'EXTRUDER_TEMP=235'))
        self.assertFalse(self.evaluate()['qualified'])
        self.klipper_pair()
        self.inputs['effective']['machine_start_gcode'] = 'PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]'
        self.manifest['inputs_sha256'] = parity.digest(self.inputs)
        self.assertIn('wait hooks', self.evaluate()['reason'])

    def test_original_klipper_abi_with_matching_visible_waits_has_no_hardware_claim(self):
        self.klipper_pair()
        self.inputs['effective']['machine_start_gcode'] = 'M190 S[bed_temperature_initial_layer_single]\\nM109 S[nozzle_temperature_initial_layer]\\nPRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]'
        for path in (self.candidate, self.native):
            path.write_text(path.read_text().replace('PRINT_START BED_TEMP=60 EXTRUDER_TEMP=230',
                                                    'M190 S60\nM109 S230\nPRINT_START EXTRUDER=230 BED=60'))
        self.manifest.update(inputs_sha256=parity.digest(self.inputs), artifact=parity.file_record(self.native))
        report = self.evaluate()
        self.assertTrue(report['qualified'], report['reason'])
        semantics = report['candidate_invariants']['macro_semantics']
        self.assertEqual(semantics['policy'], 'native-original-visible-waits-v1')
        self.assertFalse(semantics['hardware_abi_qualified'])
        self.assertFalse(semantics['physical_readiness'])
        self.candidate.write_text(self.candidate.read_text().replace('M109 S230\n', ''))
        self.assertIn('visible waits', self.evaluate()['reason'])

    def test_same_bad_bed_command_in_both_klipper_files_still_blocks_invariant(self):
        self.klipper_pair()
        for path in (self.candidate, self.native):
            path.write_text(path.read_text().replace('M104 S225', 'M140 S35\nM104 S225', 1))
        self.manifest['artifact'] = parity.file_record(self.native)
        self.assertIn('plate temperatures', self.evaluate()['reason'])

    def test_misplaced_end_or_wrong_extrusion_mode_blocks_klipper(self):
        self.klipper_pair()
        for path in (self.candidate, self.native):
            path.write_text('PRINT_END\n' + path.read_text().replace('PRINT_END\n', ''))
        self.manifest['artifact'] = parity.file_record(self.native)
        self.assertFalse(self.evaluate()['qualified'])
        self.klipper_pair()
        self.inputs['effective']['use_relative_e_distances'] = '0'
        self.manifest['inputs_sha256'] = parity.digest(self.inputs)
        self.assertIn('mode', self.evaluate()['reason'])

    def test_m73_difference_is_measured_but_still_not_waived(self):
        self.candidate.write_text('M73 P0 R36\n' + self.candidate.read_text())
        self.native.write_text('M73 P0 R37\n' + self.native.read_text())
        self.manifest['artifact'] = parity.file_record(self.native)
        report = self.evaluate()
        self.assertFalse(report['qualified'])
        self.assertFalse(report['observations']['progress_estimates_equal'])
        self.assertTrue(report['observations']['motion_extrusion_equal'])

    def test_klipper_dynamic_acceleration_is_measured_separately_from_static_limits(self):
        self.candidate.write_text('SET_VELOCITY_LIMIT ACCEL=3000\n' + self.candidate.read_text())
        self.native.write_text('SET_VELOCITY_LIMIT ACCEL=6000\n' + self.native.read_text())
        self.manifest['artifact'] = parity.file_record(self.native)
        report = self.evaluate()
        self.assertFalse(report['qualified'])
        self.assertFalse(report['observations']['static_machine_limit_commands_present'])
        self.assertFalse(report['observations']['dynamic_acceleration_stream_equal'])
        self.assertFalse(report['observations']['dynamic_acceleration_unique_values_equal'])

    def test_global_settings_difference_requires_native_object_evidence(self):
        a = temperature_gcode() + '; brim_type = outer_only\n; brim_object_gap = 0\n'
        b = temperature_gcode() + '; brim_type = no_brim\n; brim_object_gap = 0.1\n'
        data = parity.compare_emitted_settings(a, b)
        self.assertEqual(len(data['differences']), 2)
        self.assertTrue(all('object' in item['classification'] for item in data['differences']))

    def test_native_manifest_requires_independent_full_native_context(self):
        context = {'schema': 'helix-orca-v1-context/v1', 'origin_id': '1' * 32,
                   'runtime': self.inputs['runtime'], 'nozzle_mm': .4,
                   'effective': {'gcode_flavor': 'marlin'}}
        for role in ('printer', 'process', 'filament'):
            context[role] = {state: {'name': role, 'config': {'gcode_flavor': 'marlin'}} for state in ('saved', 'edited')}
        evidence = [self.manifest['evidence'][0]['path'], str(self.native)]
        created = parity.create_native_reference(self.native, context, 'temperature', self.inputs['parameters'],
                                                 self.inputs['source_commit'], evidence)
        self.assertFalse('qualified' in created)
        self.assertEqual(created['artifact'], parity.file_record(self.native))
        with self.assertRaises(ValueError):
            parity.create_native_reference(self.native, context, 'temperature', self.inputs['parameters'],
                                            self.inputs['source_commit'], [])

    def test_qualified_report_is_recomputed_from_retained_bytes(self):
        report = self.evaluate()
        prepared = {'artifact': report['candidate'], 'calibration': 'temperature', 'parameters': self.inputs['parameters'],
                    'context_sha256': self.inputs['context_sha256'], 'generator': {'build': self.inputs['source_commit']},
                    'parity': {'qualified': True, 'report_sha256': parity.digest(report)}}
        self.assertTrue(parity.verify_report(report, prepared))
        self.candidate.write_text(self.candidate.read_text() + 'M500\n')
        self.assertFalse(parity.verify_report(report, prepared))

    def test_forged_flag_and_rehashed_report_still_rejected(self):
        self.candidate.write_text(self.candidate.read_text().replace('M140 S60', 'M140 S35'))
        report = self.evaluate()
        report['qualified'] = True
        prepared = {'artifact': report['candidate'], 'calibration': 'temperature', 'parameters': self.inputs['parameters'],
                    'context_sha256': self.inputs['context_sha256'], 'generator': {'build': self.inputs['source_commit']},
                    'parity': {'qualified': True, 'report_sha256': parity.digest(report)}}
        self.assertFalse(parity.verify_report(report, prepared))


class NativeCalibrationSchedules(unittest.TestCase):
    """Synthetic executable forgeries exercise checkers, never qualification evidence."""
    def inputs(self, calibration, parameters):
        return {'calibration': calibration, 'parameters': parameters, 'nozzle_mm': .4,
                'source_commit': '6a7763f08d1a175a464a00ce13f0b5a815662fc4',
                'effective': {'belt_printer': '0', 'z_offset': '0', 'gcode_flavor': 'klipper',
                              'use_relative_e_distances': '1', 'nozzle_temperature_initial_layer': '220',
                              'nozzle_temperature': '215', 'hot_plate_temp_initial_layer': '60',
                              'hot_plate_temp': '60', 'curr_bed_type': 'High Temp Plate',
                              'filament_flow_ratio': '0.98', 'slow_down_layers': '2',
                              'initial_layer_print_height': '0.2', 'layer_height': '0.2',
                              'machine_start_gcode': 'PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]',
                              'machine_end_gcode': 'PRINT_END'}}

    def header(self):
        return ['G90', 'M83', 'M190 S60', 'M109 S220', 'PRINT_START BED_TEMP=60 EXTRUDER_TEMP=220']

    def retraction(self):
        inputs = self.inputs('retraction', {'start': .2, 'end': .6, 'step': .2})
        lines = self.header()
        for layer in range(17):
            z = (layer + 1) * .2
            length = .2 + math.floor(max(0., z - .4 + 1e-8)) * .2
            lines += [';LAYER_CHANGE', f'G1 Z{z:.1f}', 'M104 S' + ('220' if layer == 0 else '215'),
                      '; printing object retraction_tower.drc id:0 copy 0',
                      f'G1 X1 Y1 E1 F1800', f'G1 E{-length/2:.5f}',
                      f'G1 X1.1 E{-length/2:.5f}', f'G1 E{length:.5f}',
                      'G1 X2 Y2 E1', '; stop printing object retraction_tower.drc id:0 copy 0']
        return '\n'.join(lines + ['PRINT_END']), inputs

    def mvs(self):
        inputs = self.inputs('max_volumetric_speed', {'start': 5., 'end': 8., 'step': 1.})
        n = inputs['nozzle_mm']
        width, height = parity._f32(n * 1.75), parity._f32(n * .8)
        flow = parity._f32(height * (width - height * (1 - math.pi/4))) * .98
        lines = self.header()
        for layer in range(12):
            z = (layer + 1) * .32
            speed = 30 if layer < 2 else math.floor((5 + z) / flow + .5)
            lines += [';LAYER_CHANGE', f'G1 Z{z-.3:.3f}', 'M104 S' + ('220' if layer == 0 else '215'),
                      '; printing object SpeedTestStructure.drc id:0 copy 0', ';TYPE:Outer wall',
                      f'G1 X1 Y1 Z{z-.15:.3f} E1 F{speed*60}', f'G1 X2 Y2 Z{z:.3f} E1',
                      '; stop printing object SpeedTestStructure.drc id:0 copy 0']
        return '\n'.join(lines + ['PRINT_END']), inputs

    def pa_pattern(self):
        inputs = self.inputs('pressure_advance_pattern', {'start': 0., 'end': .012, 'step': .005})
        samples = [0., .005, .01, .015]
        lines = self.header()
        for layer in range(4):
            lines += [';LAYER_CHANGE', 'M104 S' + ('220' if layer == 0 else '215'),
                      '; start pressure advance pattern for layer', f'G1 Z{(layer+1)*.2:.1f}',
                      ';TYPE:Outer wall']
            if layer < 2:
                lines += ['SET_PRESSURE_ADVANCE ADVANCE=0']
            x = y = 0.
            for sample in samples:
                lines += [f'SET_PRESSURE_ADVANCE ADVANCE={sample:.4g}', f'G1 X{x:.6f} Y{y:.6f}']
                side = 20 if layer == 0 else 30 / math.sqrt(2)
                for wall in range(3):
                    x += side
                    y += side
                    lines += [f'G1 X{x:.6f} Y{y:.6f} E1 F1800']
                    x -= side
                    y += side
                    lines += [f'G1 X{x:.6f} Y{y:.6f} E1']
                    y = 0
                    x += 1
                    lines += [f'G1 X{x:.6f} Y0']
            if layer == 3:
                lines += ['SET_PRESSURE_ADVANCE ADVANCE=0']
            lines += ['; end pressure advance pattern for layer']
        return '\n'.join(lines + ['PRINT_END']), inputs

    def test_native_retraction_measures_split_wipe_episodes(self):
        text, inputs = self.retraction()
        result = parity.invariants(text, inputs)
        # Native height cut and layer quantization can reach the next band;
        # GCode.cpp does not clamp the ramp to the dialog end value.
        self.assertEqual(result['calibration_semantics']['measured_retraction_lengths_mm'], [.2, .4, .6, .8])
        self.assertTrue(result['macro_semantics']['accepted_abi_signature'])
        self.assertFalse(result['macro_semantics']['physical_readiness'])

    def test_retraction_forged_sections_and_firmware_are_rejected(self):
        text, inputs = self.retraction()
        for forgery in (text.replace('G1 E-0.20000', 'G1 E-0.21000', 1),
                        text.replace('G1 Z2.0', 'G1 Z2.1'), text.replace('G1 E-0.10000', 'G10', 1)):
            with self.subTest(forgery=forgery[-20:]), self.assertRaises(ValueError):
                parity.invariants(forgery, inputs)

    def test_retraction_transition_topup_uses_measured_nominal_layer_not_old_or_hopped_z(self):
        text, inputs = self.retraction()
        transition = ('G1 E-0.40000\n;LAYER_CHANGE\nG1 Z2.8\n'
                      'G1 E-0.20000\nG1 Z2.4\nG1 E0.60000')
        text = text.replace(';LAYER_CHANGE\nG1 Z2.4', transition)
        data = parity.analyze(text)
        crossing = [episode for episode in data['retract_episodes']
                    if episode['layer'] != episode['last_negative_layer']]
        self.assertEqual(len(crossing), 1)
        self.assertAlmostEqual(crossing[0]['z'], 2.2)
        self.assertEqual(crossing[0]['layer'], 10)
        self.assertEqual(crossing[0]['last_negative_layer'], 11)
        self.assertAlmostEqual(crossing[0]['length'], .6)
        result = parity.invariants(text, inputs)
        self.assertEqual(result['calibration_semantics']['episode_layer_policy'],
                         'last-negative-command-measured-nominal-layer-v1')
        # Both an incomplete and excessive top-up remain invalid; a forged
        # native-looking comment cannot confer the requested executable value.
        for wrong in ('0.10000', '0.30000'):
            forged = transition.replace('G1 E-0.20000',
                                         '; Calib_Retraction_tower: Z_HEIGHT: 2.4, length:0.6\nG1 E-' + wrong)
            with self.assertRaisesRegex(ValueError, 'actual software retraction length'):
                parity.invariants(text.replace(transition, forged), inputs)

    def test_native_mvs_uses_layer_top_not_each_spiral_segment(self):
        text, inputs = self.mvs()
        result = parity.invariants(text, inputs)
        self.assertEqual(result['calibration_semantics']['checked_layers'], 10)
        self.assertGreater(len(result['calibration_semantics']['distinct_wall_speeds_mm_s']), 3)

    def test_mvs_forged_flat_ramp_and_missing_height_rejected(self):
        text, inputs = self.mvs()
        import re
        for forgery in (re.sub(r'F\d+', 'F1800', text), text.replace('G1 X2 Y2 Z3.840', 'G1 X2 Y2 Z3.200')):
            with self.assertRaises(ValueError):
                parity.invariants(forgery, inputs)

    def test_native_pa_four_layers_ceil_range_and_actual_chevrons(self):
        text, inputs = self.pa_pattern()
        result = parity.invariants(text, inputs)
        self.assertEqual(result['calibration_semantics']['samples_per_layer'], 4)
        self.assertTrue(result['calibration_semantics']['native_end_can_be_exceeded'])
        self.assertTrue(result['macro_semantics']['accepted_abi_signature'])

    def test_pa_forged_values_sections_geometry_and_reset_rejected(self):
        text, inputs = self.pa_pattern()
        cases = [text.replace('ADVANCE=0.01\n', 'ADVANCE=0.011\n', 1),
                 text.replace('; start pressure advance pattern for layer\n', '', 1),
                 text.replace('G1 X20.000000 Y20.000000 E1', 'G1 X21.000000 Y20.000000 E1', 1),
                 text.replace('G1 Z0.6', 'G1 Z0.7')]
        # Remove only the final reset; matching comments cannot repair it.
        index = text.rfind('SET_PRESSURE_ADVANCE ADVANCE=0\n')
        cases.append(text[:index] + text[index:].replace('SET_PRESSURE_ADVANCE ADVANCE=0\n', '', 1))
        for forgery in cases:
            with self.subTest(forgery=forgery[-100:]), self.assertRaises(ValueError):
                parity.invariants(forgery, inputs)

    def test_all_native_routes_reject_wrong_or_changed_deposition_modes(self):
        for factory in (self.retraction, self.mvs, self.pa_pattern):
            text, inputs = factory()
            for forgery in (text.replace('M83', 'M82', 1), text.replace(';LAYER_CHANGE', ';LAYER_CHANGE\nG91', 2)):
                with self.subTest(calibration=inputs['calibration']), self.assertRaises(ValueError):
                    parity.invariants(forgery, inputs)

    def test_generic_macro_uses_effective_nozzle_and_retains_original_abi_boundary(self):
        text, inputs = self.mvs()
        self.assertEqual(parity.invariants(text, inputs)['macro_semantics']['initial_nozzle_c'], 220)
        with self.assertRaisesRegex(ValueError, 'arguments'):
            parity.invariants(text.replace('EXTRUDER_TEMP=220', 'EXTRUDER_TEMP=5'), inputs)
        original = 'M190 S[bed_temperature_initial_layer_single]\\nM109 S[nozzle_temperature_initial_layer]\\nPRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]'
        inputs['effective']['machine_start_gcode'] = original
        text = text.replace('PRINT_START BED_TEMP=60 EXTRUDER_TEMP=220', 'PRINT_START EXTRUDER=220 BED=60')
        semantics = parity.invariants(text, inputs)['macro_semantics']
        self.assertFalse(semantics['accepted_abi_signature'])
        self.assertFalse(semantics['hardware_abi_qualified'])
        with self.assertRaisesRegex(ValueError, 'visible waits'):
            parity.invariants(text.replace('M109 S220\n', ''), inputs)

    def test_yolo_exposes_generic_accepted_macro_semantics(self):
        inputs = self.inputs('flow_ratio_yolo', {'pass': 1})
        lines = self.header() + [';LAYER_CHANGE', 'G1 Z0.2', ';TYPE:Top surface']
        names = ['flowrate_0'] + [f'flowrate_{sign}0.0{i}' for sign in ('', 'm') for i in range(1, 6)]
        for name in names:
            lines += [f'; printing object {name} id:0 copy 0', 'G1 X1 Y1 E1 F1800', 'G1 X2 Y2 E1',
                      f'; stop printing object {name} id:0 copy 0']
        text = '\n'.join(lines + ['PRINT_END'])
        result = parity.invariants(text, inputs)
        self.assertTrue(result['macro_semantics']['accepted_abi_signature'])
        self.assertEqual(result['macro_semantics']['initial_nozzle_c'], 220)
        for forgery in (text.replace('M190 S60', 'M190 S35'),
                        text.replace('EXTRUDER_TEMP=220', 'EXTRUDER_TEMP=230'),
                        text.replace(';TYPE:Top surface', ';TYPE:Top surface\nM82')):
            with self.assertRaises(ValueError):
                parity.invariants(forgery, inputs)

    def test_native_source_belt_and_required_effective_data_are_not_assumed(self):
        for factory in (self.retraction, self.mvs, self.pa_pattern):
            text, inputs = factory()
            for mutate in (lambda i: i.update(source_commit=next(iter(parity.PINS))),
                           lambda i: i['effective'].pop('belt_printer'),
                           lambda i: i['effective'].pop('z_offset'),
                           lambda i: i['parameters'].update(step=0)):
                altered = copy.deepcopy(inputs)
                mutate(altered)
                with self.assertRaises(ValueError):
                    parity.invariants(text, altered)


if __name__ == '__main__':
    unittest.main()
