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
            self.assertLessEqual(set(defaults),set(offered))
            for key,value in defaults.items():
                rule=offered[key]
                if rule['kind']=='number':
                    self.assertGreaterEqual(value,rule['min'])
                    if 'max' in rule:self.assertLessEqual(value,rule['max'])
                elif rule['kind']=='choice':self.assertIn(value,rule['values'])
                elif rule['kind']=='fixed':self.assertEqual(value,rule['value'])
                else:self.assertIs(type(value),bool)
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
    def test_derivative_is_exactly_pinned_to_beta12(self):
        self.assertEqual(qualifier.beta12.SOURCE_COMMIT,'00a9fe6030c37d56748b2122b41fd36de1fdf831')
        self.assertEqual(qualifier.beta12.ACTIONS_BINARY_SHA256,'1ae6d052ec14d0148a300caaa049cb4b5ca8a5048390b9426814f48227adb04a')
        self.assertEqual(qualifier.beta12.RELEASE_BINARY_SHA256,'3811d962d76d1d652602c5cc465fd7487db76bd1f00fceb343d10c52111a93db')
        self.assertEqual(len(qualifier.beta12.SUBMODULES),14)
        self.assertNotEqual(qualifier.beta12.ACTIONS_BINARY_SHA256,qualifier.beta12.RELEASE_BINARY_SHA256)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'orcacal';builder.generate(out)
            manifest=json.loads((out/'manifest.json').read_text())
            generated=json.loads((out/'.helix-orca-v1-generated.json').read_text())
            self.assertEqual(manifest['helix_version'],'>=1.1.0-beta.12')
            self.assertEqual(manifest['version'],'1.1.0-v1-beta12')
            self.assertEqual(generated['helix_source_commit'],qualifier.beta12.SOURCE_COMMIT)
            self.assertEqual(generated['native_adapter_schema'],'helix-orca-v1-native-adapter/v2')
    def test_native_capture_refuses_an_unknown_or_empty_viewport_selection(self):
        self.assertEqual([entry[0] for entry in qualifier.selected_viewports('medium_800x480')],
                         ['medium_800x480'])
        with self.assertRaisesRegex(ValueError,'Unknown native viewport'):
            qualifier.selected_viewports('medium')
    def test_warning_dialog_uses_beta12_responsive_widths(self):
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_warning.xml')
        constants={item.attrib['name']:item.attrib['value'] for item in doc.findall('./consts/px')}
        self.assertEqual(constants,{
            'orcacal__v1_warning_w_small':'200',
            'orcacal__v1_warning_w_medium':'260',
            'orcacal__v1_warning_w_large':'320',
        })
        self.assertEqual(doc.find(".//lv_obj[@name='orcacal__v1_warning_body']").attrib['width'],
                         '#orcacal__v1_warning_w')
    def test_v2_adapter_is_parallel_to_legacy_wire_objects(self):
        source=(ROOT/'integration/v1-native/main.lua').read_text()
        for schema in ('helix-orca-v1-request/v2','helix-orca-v1-prepared/v2','helix-orca-v1-result/v2',
                       'helix-orca-v1-native-warning-decision/v2','helix-orca-v1-application-retry/v2'):
            self.assertIn(schema,source)
        self.assertIn("v1_exact(p.generator,'source_commit route executable_sha256 qualification_sha256')",source)
        self.assertIn("v1_exact(p.processing,'error_code warnings status')",source)
        self.assertIn("d.dirty~=true or d.unsaved~=true",source)
        self.assertIn("application.state='failed'",source)
        self.assertIn("helix.moonraker.on_agent_event('helix_orca_v1.warning.v2'",source)
        self.assertIn('warning_sha256=warning.warning_sha256',source)
        self.assertNotIn('acknowledged_at=0',source)
        self.assertIn('v1_session.application_retry=nil',source)
        self.assertIn('if not v1_text(transaction_id,128) then transaction_id=d.application_sha256 end',source)
        cancel=source[source.index("if action=='cancel' then",source.index('local function v1_warning_decision')):
                      source.index("warning.decision=",source.index('local function v1_warning_decision'))]
        self.assertIn("v1_intent('cancel')",cancel)
        self.assertNotIn('warning.decision=',cancel)

    def test_current_native_storage_roundtrip_uses_the_real_runtime_tick(self):
        offer=qualifier.current_offer()
        request={key:offer[key] for key in ('request_id','origin_id','context_sha256','created_at','expires_at')}
        request.update(schema='helix-orca-v1-request/v2',calibration='temperature',
                       parameters=offer['defaults']['temperature'])
        saved=dict(request=request,offer=offer,phase='requested',sequence=0,
                   message='Generation requested · nothing started',
                   v2=dict(schema='helix-orca-v1-native-adapter/v2',application_sequence=0,
                           origin_filament=offer['origin_filament']))
        with tempfile.TemporaryDirectory() as name:
            proof=qualifier.current_storage_roundtrip(saved,Path(name))
        self.assertTrue(proof['synthetic_only'])
        self.assertEqual(proof['physical_actions'],0)
        self.assertEqual(proof['status_phase'],'review')
        self.assertEqual(proof['request_sha256'],proof['coordinator_request_sha256'])
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
            if path.name in ('orcacal__v1_result_picker.xml','orcacal__v1_warning.xml'):
                self.assertEqual(view.attrib['extends'],'ui_dialog')
                self.assertIsNotNone(view.find('modal_header'))
                self.assertIsNotNone(view.find('modal_button_row'))
            else:
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
            # Unit checks supply the upstream settings template explicitly;
            # only actual native capture requires the verified runtime cache.
            cache=Path(name)/'isolated-cache'
            template=cache/'runtime/helixscreen/config/settings.json.template'
            template.parent.mkdir(parents=True)
            template.write_text(json.dumps({'plugins':{},'printers':{},'dark_mode':False}))
            config=Path(name)/'config'
            with patch.object(qualifier.beta12,'cache_root',return_value=cache):
                qualifier.settings(config)
            widgets=json.loads((config/'settings-test.json').read_text())['printers']['default']['panel_widgets']['home']['pages'][0]['widgets']
            home=json.loads((config/'settings-test.json').read_text())['printers']['default']['panel_widgets']['home']
            self.assertNotIn('grid',home);self.assertNotIn('parked_grids',home)
            tile=next(w for w in widgets if w['id']=='orcacal__tile')
            self.assertNotIn('colspan',tile);self.assertNotIn('rowspan',tile)
            self.assertEqual((tile['col'],tile['row']),(-1,-1))
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
        self.assertIn('Recommended',labels);self.assertIn('Perfectionist',labels);self.assertIn('Archimedean Chords',labels)
        self.assertEqual(builder.CATALOG['flow_ratio_yolo']['parameters']['pass'],{'kind':'choice','values':[1,2]})
        self.assertEqual(builder.CATALOG['flow_ratio_yolo']['parameters']['pattern'],
                         {'kind':'choice','values':['archimedean_chords','monotonic']})
    def test_beta12_result_picker_is_a_distinct_queued_native_dialog(self):
        with tempfile.TemporaryDirectory() as name:
            output=Path(name)/'plugin';builder.generate(output)
            picker=ET.parse(output/'ui/orcacal__v1_result_picker.xml').getroot()
            view=picker.find('view');self.assertEqual(view.attrib['extends'],'ui_dialog')
            self.assertIsNotNone(view.find('modal_header'))
            row=view.find('modal_button_row')
            self.assertEqual(row.attrib['primary_user_data'],'orcacal__v1_return')
            self.assertEqual(row.attrib['secondary_user_data'],'orcacal__v1_result_later')
            source=(output/'main.lua').read_text()
            self.assertIn("helix.ui.dialog('orcacal__v1_result_picker'",source)
            self.assertIn("schema='helix-orca-v1-presentation-claim/v2'",source)
            self.assertNotIn('orcacal__v1_auto_result',source)

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

    def test_terminal_evaluation_uses_flat_native_scroll_parent_and_hidden_bindings(self):
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_job.xml')
        content=doc.find('view/lv_obj')
        for key in ('evaluation_heading','evaluation_note','return'):
            node=next(n for n in content if n.attrib.get('name')=='orcacal__v1_'+key)
            self.assertEqual(node.find('bind_flag_if_eq').attrib,dict(subject='orcacal__v1_evaluate_on',flag='hidden',ref_value='0'))
        modes={
            'evaluation':'orcacal__v1_evaluation_options_on',
            'evaluation_range':'orcacal__v1_evaluation_range_on',
        }
        for key,subject in modes.items():
            node=next(n for n in content if n.attrib.get('name')=='orcacal__v1_'+key)
            self.assertEqual(node.find('bind_flag_if_eq').attrib,dict(subject=subject,flag='hidden',ref_value='0'))
        self.assertNotIn('Printing is unavailable',ET.tostring(doc.getroot(),encoding='unicode'))
        source=(ROOT/'integration/v1-native/main.lua').read_text()
        self.assertIn("pcall(helix.ui.confirm,'Cancel this calibration print?'",source)
        self.assertIn("severity='warning',confirm_text='Cancel print'",source)
    def test_monitor_and_result_view_have_no_new_action_authority_or_ack_popup(self):
        source=(ROOT/'integration/v1-native/main.lua').read_text()
        self.assertNotIn('→',source)
        self.assertIn("..' to '..",source)
        self.assertIn("s.monitor=nil -- retained telemetry",source)
        self.assertIn('m.elapsed_s>2678400',source)
        self.assertIn("'Progress unavailable'",source)
        self.assertIn("'Elapsed unavailable'",source)
        ack=source[source.index('local function v1_receive_ack'):source.index("helix.moonraker.on_agent_event")]
        self.assertNotIn('v1_open_result',ack)
        self.assertNotIn('overlay(',ack)
        for line in source.splitlines():
            if any("v1_set('"+name+"'" in line for name in ('evaluate_on','confirm_on','start_on','cancel_on')):
                self.assertNotIn('monitor',line)
        doc=ET.parse(ROOT/'integration/v1-native/ui/orcacal__v1_result.xml')
        self.assertEqual(doc.find('view').attrib['extends'],'overlay_panel')
        self.assertTrue(any(n.attrib.get('bind_text')=='orcacal__v1_result_heading' for n in doc.iter()))
        self.assertTrue(any(n.attrib.get('user_data')=='orcacal__v1_result_close' for n in doc.iter('event_cb')))
        self.assertTrue(any(n.attrib.get('text')=='Done' for n in doc.iter()))

    def test_native_terminal_visibility_checks_named_section_even_when_control_descended(self):
        with patch.object(qualifier,'ctl',return_value=dict(flags=dict(hidden=True),target=dict(flags=dict(hidden=False)))):
            self.assertFalse(qualifier.native_hidden('owned','evaluation_section'))
        with patch.object(qualifier,'ctl',return_value=dict(flags=dict(hidden=False),target=dict(flags=dict(hidden=True)))):
            self.assertTrue(qualifier.native_hidden('owned','evaluation_section'))

    def test_next_offer_context_is_distinct_from_immutable_job_and_result(self):
        for name in ('orcacal__wizard','orcacal__v1_temperature','orcacal__v1_flow_ratio_yolo','orcacal__v1_pressure_advance_pattern','orcacal__v1_retraction','orcacal__v1_max_volumetric_speed'):
            xml=(ROOT/'integration/v1-native/ui'/ (name+'.xml')).read_text()
            self.assertIn('bind_text="orcacal__v1_offer_printer"',xml)
            self.assertNotIn('bind_text="orcacal__v1_printer"',xml)
        for name in ('orcacal__v1_job','orcacal__v1_result'):
            xml=(ROOT/'integration/v1-native/ui'/ (name+'.xml')).read_text()
            self.assertIn('bind_text="orcacal__v1_printer"',xml)
            self.assertNotIn('bind_text="orcacal__v1_offer_printer"',xml)
