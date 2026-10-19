"""Focused build/wiring checks; actual operator propagation is a separate gate."""
import copy
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from integration.v1_contract import DEFAULTS, PARAMETER_LIMITS, PA_DEFAULTS, validate_parameters
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('parameter_control_builder',ROOT/'scripts/v1-native-plugin.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class NativeParameterTests(unittest.TestCase):
    def test_every_numeric_field_has_operator_edit_button(self):
        for ident,limits in PARAMETER_LIMITS.items():
            doc=ET.parse(ROOT/f'integration/v1-native/ui/orcacal__v1_{ident}.xml')
            self.assertEqual(doc.findall('.//lv_dropdown'),[])
            for key,(minimum,maximum) in limits.items():
                rule=builder.CATALOG[ident]['parameters'][key]
                self.assertEqual((rule['min'],rule['max']),(minimum,maximum))
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
    def test_owned_keypad_covers_digits_decimal_edit_and_commit(self):
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_keypad.xml')
        data={n.attrib.get('user_data') for n in doc.iter('event_cb')}
        self.assertTrue({f'orcacal__v1_key:{i}' for i in range(10)}<=data)
        self.assertTrue({'orcacal__v1_key:.','orcacal__v1_key:clear','orcacal__v1_key:back','orcacal__v1_key_set'}<=data)
        self.assertEqual(doc.find('view').attrib['extends'],'overlay_panel')
        self.assertEqual(doc.findall('.//text_input'),[])
        self.assertEqual(doc.findall('.//lv_keyboard'),[])
        self.assertEqual(doc.findall('.//lv_textarea'),[])
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
            with self.assertRaisesRegex(ValueError,'limits differ'):builder.generate(output)
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
            self.assertIn('local V1_PA_DEFAULTS =',source)

if __name__=='__main__':unittest.main()
