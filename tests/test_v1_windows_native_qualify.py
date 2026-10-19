"""Public-source driver guards; every executable/G-code fixture is synthetic."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from integration import v1_contract as c,v1_engine as e,v1_parity as p,v1_pe as pe

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/v1-windows-native-qualify.py'
spec=importlib.util.spec_from_file_location('native_qualify_driver',SCRIPT)
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
driver.c,driver.e,driver.p,driver.pe=c,e,p,pe


class NativeWindowsQualification(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.source.mkdir()
        for name in driver.SOURCE_NAMES:
            target=self.source/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(SCRIPT.parents[1]/name,target)
        self.manifest=self.root/'reviewed.json';self.manifest.write_text(json.dumps(dict(schema=driver.SOURCE_SCHEMA,
            files={name:driver.sha(self.source/name) for name in driver.SOURCE_NAMES})))
        for name,value in (('ROOT',self.source),('__file__',str(self.source/'scripts'/SCRIPT.name)),
                           ('sys',SimpleNamespace(flags=SimpleNamespace(isolated=1,no_site=1))),
                           ('os',SimpleNamespace(name='nt',walk=os.walk))):
            setting=patch.object(driver,name,value);setting.start();self.addCleanup(setting.stop)
        setting=patch.object(driver,'load_owned');setting.start();self.addCleanup(setting.stop)
        self.context=dict(schema='helix-orca-v1-context/v1',origin_id='1'*32,runtime=p.PINS[driver.PIN],
            nozzle_mm=.4,effective={'SECRET_EFFECTIVE':'SECRET_VALUE'})
        for role in ('printer','process','filament'):
            self.context[role]={state:dict(name='SECRET_PROFILE',config={'fixture':'SECRET'}) for state in ('saved','edited')}
        self.context_path=self.root/'context.json';self.context_path.write_bytes(c.canonical(self.context))
        self.parameters={'start':0,'end':.08,'step':.005}
        self.parameters_path=self.root/'parameters.json';self.parameters_path.write_bytes(c.canonical(self.parameters))
        self.native=self.root/'native.gcode';self.native.write_text('SYNTHETIC NATIVE FIXTURE; NOT QUALIFICATION')
        self.pngs=[]
        for name in ('native-dialog.png','native-export.png'):
            path=self.root/name;path.write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC UI FIXTURE');self.pngs.append(path)
        self.reference=p.create_native_reference(self.native,self.context,'pressure_advance_pattern',self.parameters,
            driver.PIN,[self.context_path,*self.pngs])
        self.reference_path=self.root/'reference.json';self.reference_path.write_bytes(c.canonical(self.reference))
        self.exe=self.root/'native.exe';self.exe.write_bytes(b'SYNTHETIC EXE; NEVER EXECUTE')
        self.resources=self.root/'resources';self.resources.mkdir()
        assets={}
        for name in sorted(e._NATIVE_ASSETS):
            path=self.resources/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic asset')
            assets[name]=driver.sha(path)
        receipt=dict(target=e._WINDOWS_TARGET,application_commit='a'*40,runtime_dlls={},resources=assets)
        self.receipt=self.root/'build-receipt.json';self.receipt.write_bytes(c.canonical(receipt))
        self.inputs=self.root/'build-inputs.json';self.inputs.write_text('{"fixture":"public-build-inputs"}')
        self.backend=dict(receipt=receipt,executable=self.exe,resources=self.resources)
        setting=patch.object(e,'_backend',return_value=self.backend);self.backend_call=setting.start();self.addCleanup(setting.stop)
        self.args=argparse.Namespace(calibration='pressure_advance_pattern',register_native_only=False,
            source_manifest=self.manifest,source_manifest_sha256=driver.sha(self.manifest),
            context=self.context_path,context_sha256=driver.sha(self.context_path),
            parameters=self.parameters_path,parameters_sha256=driver.sha(self.parameters_path),
            native=self.native,native_sha256=driver.sha(self.native),native_manifest=self.reference_path,
            native_manifest_sha256=driver.sha(self.reference_path),native_executable=self.exe,
            native_executable_sha256=driver.sha(self.exe),build_receipt=self.receipt,
            build_receipt_sha256=driver.sha(self.receipt),build_inputs=self.inputs,
            build_inputs_sha256=driver.sha(self.inputs),resources=self.resources,timeout_seconds=120,
            application_commit='a'*40,output_dir=self.root/'new-case',
            native_evidence=self.pngs,native_evidence_sha256=[driver.sha(path) for path in self.pngs])

    def produce(self,request,context,out,config,qualified=False):
        self.assertNotIn('runner',config);self.assertEqual(config['timeout_seconds'],120)
        self.assertEqual(request['parameters'],self.parameters);self.assertEqual(context,self.context)
        out.mkdir();artifact=out/'native-calibration.gcode';artifact.write_text('SYNTHETIC CANDIDATE; NOT QUALIFICATION')
        inputs=p.generation_inputs(request,context,driver.PIN)
        report=dict(qualified=qualified,reason='SECRET_RAW_REASON',differences=[] if qualified else [{'raw':'SECRET_COMMAND'}],
            inputs=inputs,inputs_sha256=c.digest(inputs),candidate=p.file_record(artifact),reference=p.file_record(self.native),
            candidate_invariants={'model_moves':1},native_invariants={'model_moves':1},observations={})
        prepared={key:request[key] for key in ('request_id','origin_id','context_sha256','calibration','parameters')}
        prepared.update(schema='helix-orca-v1-prepared/v1',request_sha256=c.digest(request),artifact=p.file_record(artifact),
            generator=dict(build=driver.PIN,route='native-engine-v1'),
            parity=dict(qualified=qualified,report_sha256=c.digest(report),reason=report['reason']),not_applied=True)
        for name,value in (('parity.json',report),('prepared.json',prepared)):
            (out/name).write_bytes(c.canonical(value))
        return prepared

    def test_exact_live_engine_entrypoint_and_sanitized_false_parity(self):
        with patch.object(e,'generate',side_effect=self.produce) as generate:
            summary=driver.run(self.args)
        self.assertEqual(generate.call_count,1);self.assertGreaterEqual(self.backend_call.call_count,2)
        self.assertFalse(summary['qualified']);self.assertFalse(summary['physical_actions'])
        self.assertEqual(summary['production_generator'],'integration.v1_engine.generate')
        self.assertEqual(summary['parameters'],self.parameters)
        self.assertNotIn('SECRET',json.dumps(summary))
        self.assertEqual(driver.sha(self.args.output_dir/'generation-provenance.json'),summary['generation_provenance_sha256'])
        self.assertIn('SECRET_EFFECTIVE',(self.args.output_dir/'job/parity.json').read_text())

    def test_qualified_flag_requires_actual_strict_report_verification(self):
        with patch.object(e,'generate',side_effect=lambda *args:self.produce(*args,qualified=True)),\
                patch.object(p,'verify_report',return_value=False) as verify:
            with self.assertRaisesRegex(driver.Refused,'strict_native_parity'):driver.run(self.args)
        verify.assert_called_once();self.assertFalse((self.args.output_dir/'summary.json').exists())

    def test_original_warning_remains_blocked_with_exact_request_and_safe_warning_code(self):
        def warn(request,context,out,config):
            out.mkdir();(out/'native-calibration.gcode').write_text('SYNTHETIC INCOMPLETE ARTIFACT')
            (out/'native-processing.json').write_bytes(c.canonical(dict(error_code=0,warnings=[
                dict(level=3,message='SECRET_WARNING_TEXT',error_code='1000C001')])))
            raise e.NativeEngineBlocked('SECRET_RAW_WARNING','native_warning')
        with patch.object(e,'generate',side_effect=warn):summary=driver.run(self.args)
        self.assertEqual(summary['blocker'],'native_warning');self.assertEqual(summary['warning_codes'],['1000C001'])
        self.assertFalse(summary['qualified']);self.assertFalse(summary['prepared'])
        self.assertNotIn('SECRET',json.dumps(summary));self.assertFalse((self.args.output_dir/'job/prepared.json').exists())
        request=json.loads((self.args.output_dir/'request.json').read_text())
        self.assertEqual(request['parameters'],self.parameters)
        self.assertEqual(c.digest(request),summary['request_sha256'])
        self.assertIn('SECRET_RAW_WARNING',(self.args.output_dir/'generation-failure.json').read_text())

    def test_context_native_executable_resource_and_source_mutation_block_publication(self):
        for kind in ('context','native','executable','resource','source'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                self.args.output_dir=Path(directory)/'case'
                path={'context':self.context_path,'native':self.native,'executable':self.exe,
                      'resource':self.resources/next(iter(e._NATIVE_ASSETS)),
                      'source':self.source/'integration/v1_contract.py'}[kind]
                original=path.read_bytes()
                def mutate(*args):
                    prepared=self.produce(*args);path.write_bytes(original+b' changed');return prepared
                try:
                    with patch.object(e,'generate',side_effect=mutate) as generate:
                        with self.assertRaises(driver.Refused):driver.run(self.args)
                    generate.assert_called_once()
                    self.assertFalse((self.args.output_dir/'summary.json').exists())
                finally:path.write_bytes(original)

    def test_external_package_context_pins_and_windows_target_cannot_be_replaced(self):
        self.args.context_sha256='f'*64
        with patch.object(e,'generate') as generate:
            with self.assertRaisesRegex(driver.Refused,'input_digest'):driver.run(self.args)
            generate.assert_not_called()
        self.args.context_sha256=driver.sha(self.context_path)
        self.backend['receipt']['target']=e._TARGET
        with self.assertRaisesRegex(driver.Refused,'actual_windows_amd64'):driver.run(self.args)
        self.backend['receipt']['target']=e._WINDOWS_TARGET
        self.args.application_commit='b'*40
        with self.assertRaisesRegex(driver.Refused,'application_commit'):driver.run(self.args)

    def test_registration_needs_no_package_and_calls_original_native_invariants(self):
        self.args.register_native_only=True
        self.args.native_executable=self.args.build_receipt=self.args.build_inputs=self.args.resources=None
        with patch.object(p,'invariants',return_value={'model_moves':3,'layers':4,'executable_commands':9}) as invariants,\
                patch.object(e,'generate') as generate:
            summary=driver.run(self.args)
        self.backend_call.assert_not_called();generate.assert_not_called();invariants.assert_called_once()
        self.assertEqual(summary['mode'],'register-native-only');self.assertFalse(summary['qualified'])
        self.assertFalse(summary['prepared']);self.assertTrue(summary['native_invariants_passed'])
        native=json.loads((self.args.output_dir/'native-reference.json').read_text())
        self.assertEqual(native,self.reference)

    def test_registration_refuses_repeated_ui_evidence_and_invariant_failure(self):
        self.args.register_native_only=True;self.args.native_evidence=[self.pngs[0],self.pngs[0]]
        self.args.native_evidence_sha256=[driver.sha(self.pngs[0])]*2
        with self.assertRaisesRegex(driver.Refused,'distinct_native'):driver.run(self.args)
        self.args.native_evidence=self.pngs;self.args.native_evidence_sha256=[driver.sha(path) for path in self.pngs]
        with patch.object(p,'invariants',side_effect=ValueError('SECRET_INVARIANT_DIAGNOSTIC')):
            with self.assertRaisesRegex(driver.Refused,'native_invariant_rejected'):driver.run(self.args)
        self.assertFalse((self.args.output_dir/'native-reference.json').exists())
        self.assertIn('SECRET_INVARIANT',(self.args.output_dir/'native-invariant-failure.json').read_text())

    def test_bytecode_unexpected_module_and_source_pin_are_rejected(self):
        (self.source/'integration/extra.pyc').write_bytes(b'NEVER EXECUTE')
        with self.assertRaisesRegex(driver.Refused,'unexpected_owned_source'):
            driver.ReviewedSource(self.manifest,self.args.source_manifest_sha256)
        (self.source/'integration/extra.pyc').unlink()
        with self.assertRaisesRegex(driver.Refused,'manifest_digest'):
            driver.ReviewedSource(self.manifest,'f'*64)
        driver.load_owned.assert_not_called()

    def test_all_four_routes_are_supported_without_parameter_substitution(self):
        parameters=dict(pressure_advance_pattern={'start':.01,'end':.09,'step':.01},
            retraction={'start':.2,'end':2.2,'step':.2},max_volumetric_speed={'start':6,'end':21,'step':.75},
            temperature={'start':235,'end':195,'step':5,'scale':False})
        for calibration,value in parameters.items():
            with self.subTest(calibration=calibration):
                request=driver.request_for(self.context,calibration,value)
                self.assertEqual(request['parameters'],value);self.assertEqual(request['calibration'],calibration)
        self.assertEqual(set(driver.CALIBRATIONS),set(e._NATIVE_ROUTES))

    def test_invalid_cli_never_echoes_private_input_or_accepts_runner(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(SCRIPT),'--runner','SECRET_PATH'],
            capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['failure'],'invalid_cli_arguments')
        self.assertNotIn('SECRET',result.stdout+result.stderr)

    def test_isolated_source_bootstrap_loads_only_reviewed_runtime_modules(self):
        code='''import importlib.util,json,pathlib,sys
spec=importlib.util.spec_from_file_location('fresh_native',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert not any(n=='integration' or n.startswith('integration.') for n in sys.modules)
r=m.ReviewedSource(sys.argv[2],sys.argv[3]);m.load_owned(r)
assert {n for n in sys.modules if n.startswith('integration.')}==set(m.MODULE_NAMES)
assert not list(pathlib.Path(m.ROOT).rglob('*.pyc'));r.recheck()
print(json.dumps({'loaded':4,'bytecode':False,'verified':True}))
'''
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(self.source/'scripts'/SCRIPT.name),
            str(self.manifest),self.args.source_manifest_sha256],capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),dict(loaded=4,bytecode=False,verified=True))

    def catalog(self,values=None):
        if values is None:
            values={self.reference['inputs_sha256']:dict(
                manifest=dict(path=str(self.reference_path),sha256=driver.sha(self.reference_path)),
                gcode=dict(path=str(self.native),sha256=driver.sha(self.native)))}
        path=self.root/'native-catalog.json';path.write_bytes(c.canonical(values))
        self.args.native_catalog=path;self.args.native_catalog_sha256=driver.sha(path)
        return values

    def test_one_catalog_reaches_real_engine_configuration_without_single_fallback(self):
        catalog=self.catalog()
        def generate(request,context,out,config):
            self.assertNotIn('native_reference',config)
            self.assertEqual(config['native_references'],catalog)
            return self.produce(request,context,out,config)
        with patch.object(e,'generate',side_effect=generate) as generate_call:
            summary=driver.run(self.args)
        generate_call.assert_called_once()
        self.assertEqual(summary['native_catalog_sha256'],self.args.native_catalog_sha256)
        provenance=json.loads((self.args.output_dir/'generation-provenance.json').read_text())
        self.assertEqual(provenance['native_catalog_sha256'],self.args.native_catalog_sha256)

    def test_empty_catalog_generates_then_reports_actual_missing_reference_without_sanitizer_error(self):
        self.catalog({})
        def missing(request,context,out,config):
            self.assertNotIn('native_reference',config);self.assertEqual(config['native_references'],{})
            prepared=self.produce(request,context,out,config)
            report=p.unqualified(out/'native-calibration.gcode',p.generation_inputs(request,context,driver.PIN),
                'No native catalog entry matches exact inputs')
            prepared['parity'].update(report_sha256=c.digest(report),reason=report['reason'])
            (out/'parity.json').write_bytes(c.canonical(report))
            (out/'prepared.json').write_bytes(c.canonical(prepared))
            return prepared
        with patch.object(e,'generate',side_effect=missing) as generate:
            summary=driver.run(self.args)
        generate.assert_called_once();self.assertFalse(summary['qualified'])
        self.assertEqual(summary['blocker'],'native_reference_missing')
        self.assertEqual(summary['parameters'],self.parameters)
        self.assertTrue((self.args.output_dir/'blocked-summary.json').is_file())
        self.assertFalse((self.args.output_dir/'summary.json').exists())

    def test_catalog_cannot_mask_actual_native_warning(self):
        self.catalog({})
        def warned(request,context,out,config):
            self.assertEqual(config['native_references'],{})
            out.mkdir()
            (out/'native-processing.json').write_bytes(c.canonical(dict(error_code=0,warnings=[
                dict(level=3,message='PRIVATE_ACTUAL_WARNING',error_code='1000C001')])))
            raise e.NativeEngineBlocked('PRIVATE_WARNING','native_warning')
        with patch.object(e,'generate',side_effect=warned) as generate:
            summary=driver.run(self.args)
        generate.assert_called_once();self.assertEqual(summary['blocker'],'native_warning')
        self.assertEqual(summary['warning_codes'],['1000C001']);self.assertFalse(summary['qualified'])
        self.assertNotIn('PRIVATE',json.dumps(summary))

    def test_catalog_and_unselected_reference_are_rechecked_after_generation(self):
        for kind in ('catalog','unselected_native'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                self.args.output_dir=Path(directory)/'case'
                other=self.root/'unselected.gcode';other.write_text('SYNTHETIC UNSELECTED NATIVE')
                catalog=self.catalog()
                catalog['f'*64]=dict(manifest=catalog[self.reference['inputs_sha256']]['manifest'],
                    gcode=dict(path=str(other),sha256=driver.sha(other)))
                self.catalog(catalog)
                def mutate(*args):
                    prepared=self.produce(*args)
                    target=self.args.native_catalog if kind=='catalog' else other
                    target.write_bytes(target.read_bytes()+b' changed')
                    return prepared
                with patch.object(e,'generate',side_effect=mutate):
                    with self.assertRaisesRegex(driver.Refused,'qualification_input_changed'):driver.run(self.args)
                self.assertFalse((self.args.output_dir/'summary.json').exists())

    def test_catalog_entry_must_match_independently_checked_current_cli_reference(self):
        reference=dict(manifest=dict(path=str(self.reference_path),sha256=driver.sha(self.reference_path)),
            gcode=dict(path=str(self.native),sha256=driver.sha(self.native)))
        copied=self.root/'wrong-native.gcode';copied.write_text('SYNTHETIC OTHER REFERENCE')
        reference['gcode']=dict(path=str(copied),sha256=driver.sha(copied))
        self.catalog({self.reference['inputs_sha256']:reference})
        with patch.object(e,'generate') as generate:
            with self.assertRaisesRegex(driver.Refused,'catalog_selection_differs'):driver.run(self.args)
            generate.assert_not_called()


if __name__=='__main__':unittest.main()
