"""Focused build/wiring checks; actual operator propagation is a separate gate."""
import copy
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from integration.v1_contract import DEFAULTS, PA_DEFAULTS, validate_parameters
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('parameter_control_builder',ROOT/'scripts/v1-native-plugin.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class NativeParameterTests(unittest.TestCase):
    def test_every_numeric_field_has_operator_edit_button(self):
        numeric={ident:{key:rule for key,rule in entry['parameters'].items() if rule['kind']=='number'}
                 for ident,entry in builder.CATALOG.items()}
        for ident,limits in numeric.items():
            if not limits:continue
            doc=ET.parse(ROOT/f'integration/v1-native/ui/orcacal__v1_{ident}.xml')
            self.assertEqual(doc.findall('.//lv_dropdown'),[])
            for key,rule in limits.items():
                button=doc.find(f'.//lv_button[@name="orcacal__v1_{ident}_{key}"]')
                self.assertIsNotNone(button)
                self.assertEqual(button.find('event_cb').attrib['user_data'],f'orcacal__v1_edit:{ident}:{key}')
                self.assertEqual(button.find('lv_label').attrib['bind_text'],f'orcacal__v1_{ident}_{key}_value')
    def test_fixed_temperature_increment_is_not_editable(self):
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_temperature.xml')
        self.assertIsNone(doc.find('.//lv_button[@name="orcacal__v1_temperature_step"]'))
        self.assertIn('5°C (fixed)',' '.join(n.attrib.get('text','') for n in doc.iter()))
        self.assertEqual(builder.CATALOG['temperature']['parameters']['step'],dict(kind='fixed',value=5))
        for scale in (False,True):self.assertEqual(validate_parameters('temperature',dict(DEFAULTS['temperature'],scale=scale))['scale'],scale)
    def test_flow_modes_and_pa_defaults_are_deliberate_actions(self):
        flow=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_flow_ratio_yolo.xml')
        data={n.attrib.get('user_data') for n in flow.iter('event_cb')}
        self.assertTrue({'orcacal__v1_flow_mode:1','orcacal__v1_flow_mode:2'}<=data)
        for value in (1,2):self.assertEqual(validate_parameters('flow_ratio_yolo',{'pass':value}),{'pass':value})
        pa=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_pressure_advance_pattern.xml')
        data={n.attrib.get('user_data') for n in pa.iter('event_cb')}
        self.assertTrue({'orcacal__v1_pa_defaults:direct_drive','orcacal__v1_pa_defaults:bowden'}<=data)
        self.assertNotIn('extruder_type',builder.CATALOG['pressure_advance_pattern']['parameters'])
        for values in PA_DEFAULTS.values():self.assertEqual(validate_parameters('pressure_advance_pattern',values),values)
    def test_owned_precise_fallback_covers_digits_decimal_edit_and_commit(self):
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_keypad.xml')
        data={n.attrib.get('user_data') for n in doc.iter('event_cb')}
        self.assertTrue({f'orcacal__v1_key:{i}' for i in range(10)}<=data)
        self.assertTrue({'orcacal__v1_key:.','orcacal__v1_key:,','orcacal__v1_key:clear','orcacal__v1_key:back','orcacal__v1_key_set'}<=data)
        self.assertEqual(doc.find('view').attrib['extends'],'overlay_panel')
        self.assertEqual(doc.findall('.//text_input'),[])
        self.assertEqual(doc.findall('.//lv_keyboard'),[])
        self.assertEqual(doc.findall('.//lv_textarea'),[])
        source=(ROOT/'integration/v1-native/controls.lua').read_text()
        self.assertIn("local precise=rule.kind=='positive_int_list' or rule.max==nil",source)
        self.assertIn('v1_precise_editor(id,key,rule,p,entry)',source)

    def test_current_orca_numeric_domains_preserve_real_maxima_and_pa_lists_are_editable(self):
        for ident in ('retraction','max_volumetric_speed'):
            for key in ('start','end','step'):
                self.assertNotIn('max',builder.CATALOG[ident]['parameters'][key])
        pa=builder.CATALOG['pressure_advance_pattern']['parameters']
        for key in ('start','end'):
            self.assertEqual(pa[key]['max'],2.0)
        self.assertNotIn('max',pa['step'])
        for key in ('accelerations','speeds'):
            self.assertEqual(pa[key],{'kind':'positive_int_list','max_items':64})
            button=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_pressure_advance_pattern.xml').find(
                f'.//lv_button[@name="orcacal__v1_pressure_advance_pattern_{key}"]')
            self.assertIsNotNone(button)
        source=(ROOT/'integration/v1-native/controls.lua').read_text()
        self.assertIn("rule.kind=='positive_int_list'",source)
        self.assertIn("for item in v1_edit_buffer:gmatch('[^,]+')",source)
        self.assertEqual(builder.CATALOG['retraction']['parameters']['step'],
                         {'kind':'number','min':0,'exclusive_min':True})
        self.assertEqual(builder.CATALOG['max_volumetric_speed']['parameters']['start'],
                         {'kind':'number','min':0,'exclusive_min':True})
        self.assertEqual(builder.CATALOG['max_volumetric_speed']['parameters']['step'],
                         {'kind':'number','min':0,'exclusive_min':True})
        self.assertIn("helix.ui.on('v1_evaluation_edit'",source)
        self.assertIn("v1_evaluation_range_value(v1_session.evaluation,number)",source)
    def test_beta12_native_number_editor_handles_zero_to_two_decimal_fields(self):
        source=(ROOT/'integration/v1-native/controls.lua').read_text()
        self.assertIn('pcall(helix.ui.edit_number',source)
        self.assertIn('decimals=decimals',source)
        self.assertIn('min=rule.min,max=rule.max',source)
        self.assertIn('validate=function(value) return v1_valid_field(rule,value)',source)
        self.assertIn('on_accept=function(value)',source)
        self.assertIn('on_cancel=function() v1_editor_open=false end',source)
    def test_all_parameter_actions_resolve_to_owned_handlers(self):
        registered=set(re.findall(r"helix\.ui\.on\('([^']+)'",(ROOT/'integration/v1-native/main.lua').read_text()+(ROOT/'integration/v1-native/controls.lua').read_text()))
        for ident in (*builder.ORDER,'keypad'):
            path=ROOT/f'integration/v1-native/ui/orcacal__v1_{ident}.xml'
            for node in ET.parse(path).iter('event_cb'):
                handler=node.attrib['user_data'].split(':',1)[0].removeprefix('orcacal__')
                self.assertIn(handler,registered,(path,handler))
                self.assertEqual(node.attrib['callback'],'plugin_event')
    def test_build_refuses_catalog_resource_limits_drift(self):
        changed=copy.deepcopy(builder.CATALOG);changed['retraction']['parameters']['end']['max']=21
        with tempfile.TemporaryDirectory() as tmp,patch.object(builder,'CATALOG',changed):
            output=Path(tmp)/'plugin'
            with self.assertRaisesRegex(ValueError,'domain differs'):builder.generate(output)
            self.assertFalse(output.exists())
    def test_generated_derivative_includes_keypad_without_fixture_or_extra_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'plugin';builder.generate(output)
            ET.parse(output/'ui/orcacal__v1_keypad.xml')
            import json
            self.assertEqual(json.loads((output/'manifest.json').read_text())['permissions'],['storage'])
            source=(output/'main.lua').read_text()
            self.assertNotIn('V1_PARAMETER_CONTROLS',source)
            self.assertNotIn('fixture_signal',source)
            self.assertIn("helix.ui.on('v1_key_set'",source)
            self.assertIn('helix.ui.edit_number',source)
            self.assertIn('local V1_PA_DEFAULTS =',source)

    def test_native_qualifier_drives_large_range_exactness_without_extra_frames(self):
        source=(ROOT/'scripts/v1-native-qualify.py').read_text()
        self.assertIn("'native-compact-range-rejects-off-step-and-returns-exact-step'",source)
        self.assertIn("range={start=0,['end']=1,step=0.0000001}",source)
        self.assertIn("for char in '0.84750005'",source)
        self.assertIn("for char in '0.8475'",source)
        self.assertIn("count=10000001,rejected=0.84750005",source)

    def test_large_range_membership_tolerance_never_grows_with_index(self):
        source=(ROOT/'integration/v1-native/main.lua').read_text()
        self.assertIn('math.abs(index-nearest)<=1e-7',source)
        self.assertNotIn('math.abs(index-nearest)<=1e-7*',source)

if __name__=='__main__':unittest.main()
