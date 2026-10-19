"""Exact native lookup guards. Synthetic fixture bytes are never parity proof."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from integration import v1_contract as c,v1_engine as e,v1_parity as p


class ExactNativeCatalog(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        effective=dict(plugins='',post_process='',slicing_pipeline_plugin='',belt_printer='0',
            curr_bed_type='High Temp Plate',nozzle_diameter='0.4',gcode_flavor='klipper')
        self.context=dict(schema='helix-orca-v1-context/v1',origin_id='1'*32,runtime=p.PINS[e.ORCA_SOURCE],
            effective=effective,nozzle_mm=.4)
        for role in ('printer','process','filament'):
            self.context[role]={state:dict(name=role+'-'+state,config={'fixture':state}) for state in ('saved','edited')}
        self.backend=dict(receipt={'capabilities':{'required_effective_keys':list(effective)},'adapter':{'sha256':'a'*64}},
            executable=self.root/'test-only-native',resources=self.root/'assets',receipt_sha256='b'*64,inputs_sha256='c'*64)
        setting=patch.object(e,'require_native_generation',return_value=self.backend);setting.start();self.addCleanup(setting.stop)
        self.runner_calls=[]

    def request(self,kind,parameters,context=None):
        context=context or self.context
        return dict(schema='helix-orca-v1-request/v1',request_id='2'*32,origin_id=context['origin_id'],
            context_sha256=c.digest(context),calibration=kind,parameters=parameters,
            created_at=100,expires_at=200,not_applied=True)

    def inputs(self,request,context=None):return p.generation_inputs(request,context or self.context,e.ORCA_SOURCE)

    def reference(self,name):
        native=self.root/(name+'.gcode');native.write_text('SYNTHETIC NATIVE '+name+'; NEVER QUALIFICATION')
        manifest=self.root/(name+'.json');manifest.write_bytes(c.canonical({'synthetic_reference':name}))
        return dict(manifest=dict(path=str(manifest),sha256=e._sha_file(manifest)),
            gcode=dict(path=str(native),sha256=e._sha_file(native)))

    def runner(self,argv,destination):
        request=json.loads((destination/'request.json').read_text());self.runner_calls.append(request)
        artifact=destination/'native-calibration.gcode';artifact.write_text('SYNTHETIC CANDIDATE; NEVER QUALIFICATION')
        native={key:request[key] for key in ('calibration','parameters','request_id','origin_id','context_sha256')}
        native.update(source_commit=e.ORCA_SOURCE,artifact=artifact.name,size=artifact.stat().st_size,
            qualified=False,not_applied=True,processing=dict(error_code=0,warnings=[]),max_parallelism=2)
        (destination/'native-generation.json').write_bytes(c.canonical(native));return 0

    def generate(self,request,catalog,context=None,name='job',**extra):
        config=dict(now=150,runner=self.runner,native_references=catalog,**extra)
        return e.generate(request,context or self.context,self.root/name,config)

    def test_all_four_routes_select_exact_parameters_and_complete_context(self):
        cases=[];catalog={}
        changed=dict(temperature={'start':235,'end':195,'step':5,'scale':True},
            pressure_advance_pattern={'start':.01,'end':.09,'step':.01},
            retraction={'start':.2,'end':2.2,'step':.2},max_volumetric_speed={'start':6,'end':21,'step':.75})
        for index,kind in enumerate(sorted(e._NATIVE_ROUTES)):
            for version,parameters in enumerate((c.DEFAULTS[kind],changed[kind])):
                context=copy.deepcopy(self.context)
                context['filament']['edited']['config']['fixture']=str(index)+'/'+str(version)
                request=self.request(kind,parameters,context);inputs=self.inputs(request,context)
                ref=self.reference(kind+str(version));catalog[c.digest(inputs)]=ref
                cases.append((request,context,ref))
        before=copy.deepcopy(catalog)
        for index,(request,context,ref) in enumerate(cases):
            def evaluate(candidate,native,manifest,inputs):
                self.assertEqual(str(native),ref['gcode']['path'])
                self.assertEqual(c.digest(inputs),c.digest(self.inputs(request,context)))
                return p.unqualified(candidate,inputs,'Synthetic selection check only')
            with patch.object(p,'evaluate',side_effect=evaluate) as evaluate_call:
                prepared=self.generate(request,catalog,context,name='job'+str(index))
            evaluate_call.assert_called_once();self.assertFalse(prepared['parity']['qualified'])
            self.assertEqual(prepared['parameters'],request['parameters'])
            self.assertEqual(prepared['context_sha256'],c.digest(context))
        self.assertEqual(len(self.runner_calls),8);self.assertEqual(catalog,before)

    def test_different_parameter_or_origin_never_falls_back_to_another_entry(self):
        request=self.request('retraction',c.DEFAULTS['retraction']);reference=self.reference('retained')
        catalog={c.digest(self.inputs(request)):reference}
        for label,changed,context in (
            ('parameters',dict(request,parameters={'start':.2,'end':2.2,'step':.2}),self.context),
            ('origin',None,dict(self.context,origin_id='3'*32)),
            ('saved',None,copy.deepcopy(self.context))):
            if label=='saved':context['filament']['saved']['name']='A different saved identity'
            if changed is None:changed=self.request('retraction',c.DEFAULTS['retraction'],context)
            with self.subTest(label=label),patch.object(p,'evaluate') as evaluate:
                prepared=self.generate(changed,catalog,context,name=label)
            evaluate.assert_not_called();self.assertFalse(prepared['parity']['qualified'])
            self.assertIn('No native catalog entry',prepared['parity']['reason'])
            self.assertEqual(prepared['origin_id'],context['origin_id'])
            self.assertEqual(prepared['parameters'],changed['parameters'])
            selection=json.loads((self.root/label/'native-reference-selection.json').read_text())
            self.assertFalse(selection['matched']);self.assertEqual(selection['inputs_sha256'],c.digest(self.inputs(changed,context)))

    def test_selected_file_tamper_blocks_parity_and_retains_false_artifact(self):
        request=self.request('temperature',c.DEFAULTS['temperature']);ref=self.reference('temperature')
        Path(ref['gcode']['path']).write_text('TAMPERED SYNTHETIC FILE')
        with patch.object(p,'evaluate') as evaluate:
            prepared=self.generate(request,{c.digest(self.inputs(request)):ref})
        evaluate.assert_not_called();self.assertFalse(prepared['parity']['qualified'])
        self.assertIn('digest',prepared['parity']['reason'])
        self.assertTrue((self.root/'job/native-calibration.gcode').is_file())

    def test_wrong_reference_under_right_key_still_uses_mandatory_evaluator(self):
        request=self.request('retraction',c.DEFAULTS['retraction']);ref=self.reference('wrong-input-reference')
        with patch.object(p,'evaluate',side_effect=lambda candidate,native,manifest,inputs:
                          p.unqualified(candidate,inputs,'Native reference provenance or exact inputs do not match')) as evaluate:
            prepared=self.generate(request,{c.digest(self.inputs(request)):ref})
        evaluate.assert_called_once();self.assertFalse(prepared['parity']['qualified'])
        self.assertIn('exact inputs',prepared['parity']['reason'])

    def test_catalog_shape_keys_bounds_and_ambiguous_single_reference_are_rejected(self):
        ref=self.reference('one');key='a'*64
        for bad in ([],None,{'A'*64:ref},{'a'*63:ref},{key:{'manifest':ref['manifest']}},
                    {key:dict(ref,extra=True)},{key:dict(ref,gcode={'path':'x','sha256':'bad'})},
                    {format(i,'064x'):ref for i in range(65)}):
            with self.subTest(catalog=type(bad).__name__),self.assertRaises(e.NativeEngineBlocked):
                e.select_native_reference({'native_references':bad},key)
        with self.assertRaisesRegex(e.NativeEngineBlocked,'not both'):
            e.select_native_reference({'native_reference':ref,'native_references':{key:ref}},key)
        self.assertIs(e.select_native_reference({'native_reference':ref},key),ref)
        selected=e.select_native_reference({'native_references':{key:ref}},key)
        selected['manifest']['sha256']='f'*64;self.assertNotEqual(ref['manifest']['sha256'],'f'*64)

    def test_real_processor_warning_takes_priority_over_missing_catalog_reference(self):
        request=self.request('pressure_advance_pattern',c.DEFAULTS['pressure_advance_pattern'])
        def warned(argv,destination):
            self.runner(argv,destination)
            (destination/'native-processing.json').write_bytes(c.canonical(dict(error_code=0,warnings=[
                dict(level=3,message='native bed threshold warning',error_code='1000C001')])))
            return 1
        with patch.object(e,'select_native_reference',wraps=e.select_native_reference) as select:
            with self.assertRaises(e.NativeEngineBlocked) as caught:
                e.generate(request,self.context,self.root/'warned',dict(now=150,runner=warned,native_references={}))
        self.assertEqual(caught.exception.code,'native_warning');self.assertIn('1000C001',str(caught.exception))
        select.assert_not_called();self.assertFalse((self.root/'warned/prepared.json').exists())
        report=json.loads((self.root/'warned/parity.json').read_text());self.assertFalse(report['qualified'])
        self.assertEqual(json.loads((self.root/'warned/request.json').read_text()),request)


if __name__=='__main__':unittest.main()
