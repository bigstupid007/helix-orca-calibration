"""Dependency-free V1 derivative ownership and shared contract checks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=load('v1_native_builder_test',ROOT/'scripts/v1-native-plugin.py')
contract=load('v1_native_contract_test',ROOT/'integration/v1_contract.py')
class V1NativeTests(unittest.TestCase):
    def test_shared_defaults_are_available_without_silent_substitution(self):
        self.assertEqual(set(builder.CATALOG),set(contract.CALIBRATIONS))
        for id,defaults in contract.DEFAULTS.items():
            offered=builder.CATALOG[id]['parameters']
            self.assertEqual(set(defaults),set(offered))
            for key,value in defaults.items():self.assertIn(value,offered[key])
            self.assertEqual(contract.validate_parameters(id,defaults),defaults)
    def test_derivative_preserves_hash_locked_base_and_storage_only_identity(self):
        base=builder.load_base();before=base.verify_baseline()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'orcacal';builder.generate(out)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual((manifest['id'],manifest['permissions']),('orcacal',['storage']))
            self.assertEqual((manifest['widgets'][0]['colspan'],manifest['widgets'][0]['rowspan']),(1,1))
            self.assertTrue((out/'main.lua').read_bytes().startswith((base.BASE/'main.lua').read_bytes()))
            self.assertEqual(base.verify_baseline(),before)
            source=(out/'main.lua').read_text()
            for forbidden in ('printer.print.start','helix.http','os.execute','helix.moonraker.call','io.open'):
                self.assertNotIn(forbidden,source)
            self.assertNotIn('fixture_signal',source)
            for xml in (out/'ui').glob('*.xml'):ET.parse(xml)
    def test_refuses_overwrite_symlink_and_repository_destinations(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'orcacal';out.mkdir();(out/'keep').write_text('preserved')
            with self.assertRaises(ValueError):builder.generate(out)
            self.assertEqual((out/'keep').read_text(),'preserved')
            link=root/'link';link.symlink_to(out,target_is_directory=True)
            with self.assertRaises(ValueError):builder.generate(link)
        with self.assertRaises(ValueError):builder.generate(ROOT/'v1-generated-forbidden')
    def test_native_xml_uses_helix_navigation_and_stacked_wrapping_content(self):
        for path in (ROOT/'integration/v1-native/ui').glob('*.xml'):
            doc=ET.parse(path);view=doc.find('view')
            if path.name.endswith('__tile.xml'):continue
            self.assertEqual(view.attrib['extends'],'overlay_panel')
            content=view.find('lv_obj');self.assertEqual(content.attrib['scrollable'],'true')
            self.assertEqual(content.attrib['width'],'100%')
            for node in doc.iter():
                if node.tag=='event_cb':self.assertEqual(node.attrib['callback'],'plugin_event')
                self.assertNotIn('on_header_back_clicked',node.attrib.values())
