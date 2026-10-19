"""Dependency-free V1 derivative ownership and shared contract checks."""
import importlib.util
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=load('v1_native_builder_test',ROOT/'scripts/v1-native-plugin.py')
contract=load('v1_native_contract_test',ROOT/'integration/v1_contract.py')
qualifier=load('v1_native_source_checks',ROOT/'scripts/v1-native-qualify.py')
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

    def test_tile_exactly_preserves_accepted_compact_style_and_status_binding(self):
        expected=builder.ACCEPTED_TILE.read_text().replace('orcacal__tp_tile_status','orcacal__v1_tile')
        self.assertEqual((ROOT/'integration/v1-native/ui/orcacal__tile.xml').read_text(),expected)
        with tempfile.TemporaryDirectory() as name:
            output=Path(name)/'plugin';builder.generate(output)
            self.assertEqual((output/'ui/orcacal__tile.xml').read_text(),expected)
            config=Path(name)/'config';qualifier.settings(config)
            widgets=json.loads((config/'settings-test.json').read_text())['printers']['default']['panel_widgets']['home']['pages'][0]['widgets']
            tile=next(w for w in widgets if w['id']=='orcacal__tile')
            self.assertNotIn('colspan',tile);self.assertNotIn('rowspan',tile)
    def test_compact_geometry_rejects_clipping_and_overlap(self):
        geometry={'widgets':[
            dict(name='orcacal__tile',x=0,y=0,w=100,h=100),
            dict(name='orcacal__tile_icon',x=40,y=0,w=20,h=20),
            dict(name='orcacal__tile_identity',x=10,y=30,w=80,h=40),
            dict(name='orcacal__tile_status',x=20,y=80,w=60,h=20)]}
        qualifier.assert_compact_bounds(geometry,120,120)
        for index,key,value in ((1,'x',90),(2,'y',10),(3,'y',65)):
            invalid=copy.deepcopy(geometry);invalid['widgets'][index][key]=value
            with self.assertRaises(ValueError):qualifier.assert_compact_bounds(invalid,120,120)
    def test_yolo_explains_native_method_without_fixed_implementation_control(self):
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_flow_ratio_yolo.xml')
        self.assertEqual(doc.findall('.//lv_dropdown'),[])
        labels=' '.join(node.attrib.get('text','') for node in doc.iter())
        self.assertIn('YOLO (recommended)',labels);self.assertIn('Archimedean Chords',labels)
        self.assertEqual(builder.CATALOG['flow_ratio_yolo']['parameters'],{'pass':[1]})
    def test_automatic_view_preserves_original_bindings_and_return_callbacks(self):
        with tempfile.TemporaryDirectory() as name:
            output=Path(name)/'plugin';builder.generate(output)
            manual=ET.parse(output/'ui/orcacal__v1_job.xml').getroot()
            automatic=ET.parse(output/'ui/orcacal__v1_auto_result.xml').getroot()
            self.assertNotEqual(manual.find('view').attrib['name'],automatic.find('view').attrib['name'])
            for left,right in zip(manual.iter(),automatic.iter()):
                self.assertEqual(left.tag,right.tag)
                self.assertEqual({k:v for k,v in left.attrib.items() if k!='name'},
                                 {k:v for k,v in right.attrib.items() if k!='name'})
            self.assertEqual(len(list(manual.iter())),len(list(automatic.iter())))
            auto_names={n.attrib['name'] for n in automatic.iter() if 'name' in n.attrib}
            self.assertIn('orcacal__v1_auto_evaluation',auto_names)
            self.assertIn('orcacal__v1_auto_return',auto_names)

    def test_recovery_fixtures_use_real_coordinator_transitions_and_durable_republish(self):
        cases=qualifier.recovery_fixtures()
        self.assertEqual(cases,qualifier.recovery_fixtures())
        for phase,case in cases.items():
            with self.subTest(phase=phase):
                retained,old,fresh,again=(case[k] for k in ('retained','same_sequence','fresh','again'))
                self.assertEqual(retained['phase'],phase)
                self.assertEqual(old['phase'],phase)
                self.assertEqual(fresh,dict(old,sequence=old['sequence']+1))
                self.assertEqual(again,dict(old,sequence=old['sequence']+2))
                self.assertEqual(fresh['prepared_sha256'],contract.digest(retained['prepared']))
                self.assertEqual(retained['prepared']['request_sha256'],contract.digest(retained['request']))
                self.assertEqual(phase!='review','intent' in retained)
                if phase=='complete':
                    self.assertEqual(retained['intent']['action'],'start')
                    self.assertTrue(fresh['completion_sha256'])
                    self.assertTrue(fresh['evaluation']['options'])
                elif phase=='confirmed':self.assertEqual(retained['intent']['action'],'confirm')
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);qualifier.fixture(root)
            lua=(root/'orcacal/main.lua').read_text()
            self.assertIn('local fixture_recovery=',lua)
            self.assertIn("v1_receive_status('fixture',second and case.fresh or case.same_sequence)",lua)
            self.assertIn("v1_receive_status('fixture',fresh)",lua)
        self.assertIn('integration/v1_runtime.py',qualifier.hashes())
    def test_native_recovery_keeps_monotonic_proof_and_terminal_outcomes(self):
        # Actual Lua behavior is additionally exercised by the managed native
        # matrix; these source guards prevent silently weakening replay policy.
        source=(ROOT/'integration/v1-native/main.lua').read_text()
        self.assertIn('d.sequence<=v1_session.sequence',source)
        self.assertIn("s.phase='uncertain';s.evaluation=nil;s.recovery_required=true",source)
        self.assertIn("local recovering=s.recovery_required==true and s.phase=='uncertain'",source)
        self.assertIn("(s.phase~='review' and not recovering) or action~='confirm'",source)
        self.assertIn('s.recovery_required=nil',source)
        for token in ('v1_same(s.prepared,d.prepared)','s.job_id~=d.job_id','s.completion_sha256~=d.completion_sha256'):
            self.assertIn(token,source)
        self.assertIn("elseif s.phase=='blocked' or s.phase=='failed' or s.phase=='cancelled' then",source)

    def test_manual_reopen_deliberately_navigates_home_after_preserved_native_panel(self):
        calls=[]
        with patch.object(qualifier.q,'back_to_home',side_effect=lambda name:calls.append(('pop',name))),\
             patch.object(qualifier,'ctl',side_effect=lambda *args:calls.append(args)),\
             patch.object(qualifier,'navigation',return_value=dict(panel='home',overlays=[])),\
             patch.object(qualifier,'tap',side_effect=lambda name,widget,*args:calls.append(('tap',widget))),\
             patch.object(qualifier.a,'_assert_overlay'):
            qualifier.reopen_job('owned',800,480,Path('/synthetic'))
        self.assertLess(calls.index(('pop','owned')),calls.index(('owned','navigate','home')))
        self.assertLess(calls.index(('owned','navigate','home')),calls.index(('tap','orcacal__tile')))
