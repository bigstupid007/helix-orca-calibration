"""Source-only Windows helper checks; synthetic bytes are never parity proof."""
import argparse
import copy
import importlib.util
import json
import os
import hashlib
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/v1-windows-temperature-native-geometry.py'
spec = importlib.util.spec_from_file_location('windows_temperature_recipe',SCRIPT)
recipe = importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
# Unit fixtures explicitly inject already imported modules; production bootstrap
# is exercised separately in an isolated subprocess below.
from integration import v1_contract,v1_generation,v1_parity
from integration.v1_temperature_geometry import inspect_stl
recipe.c,recipe.g,recipe.p,recipe.inspect_stl = v1_contract,v1_generation,v1_parity,inspect_stl


def tetrahedron():
    vertices = [(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
    data = bytearray(80)+struct.pack('<I',4)
    for face in ((0,2,1),(0,1,3),(0,3,2),(1,2,3)):
        data.extend(struct.pack('<12fH',*([0.,0.,0.]+[v for i in face for v in vertices[i]]),0))
    return data


class WindowsTemperatureGeometry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source_root = self.root/'reviewed';self.source_root.mkdir()
        for name in recipe.SOURCE_NAMES:
            target = self.source_root/name;target.parent.mkdir(exist_ok=True)
            shutil.copyfile(SCRIPT.parents[1]/name,target)
        source_manifest = self.root/'reviewed-source.json'
        source_manifest.write_text(json.dumps(dict(schema=recipe.SOURCE_SCHEMA,
            files={name:recipe.sha(self.source_root/name) for name in recipe.SOURCE_NAMES})))
        self.source_manifest = source_manifest
        for name,value in (('ROOT',self.source_root),('__file__',str(self.source_root/'scripts'/SCRIPT.name)),
                           ('sys',SimpleNamespace(flags=SimpleNamespace(isolated=1,no_site=1)))):
            setting = patch.object(recipe,name,value);setting.start();self.addCleanup(setting.stop)
        setting = patch.object(recipe,'load_owned');setting.start();self.addCleanup(setting.stop)
        context = dict(schema='helix-orca-v1-context/v1',origin_id='1'*32,
            runtime=recipe.p.PINS[recipe.PIN],nozzle_mm=.4,effective={'SECRET_EFFECTIVE':'SECRET_PAYLOAD'})
        for role in ('printer','process','filament'):
            context[role] = {state:dict(name='SECRET_PROFILE',config={'test':'SECRET_VALUE'}) for state in ('saved','edited')}
        self.context = context
        self.context_path = self.root/'context.json';self.context_path.write_bytes(recipe.c.canonical(context))
        self.native = self.root/'native.gcode';self.native.write_text('synthetic native fixture; not qualification')
        self.exe = self.root/'orca.exe';self.exe.write_text('synthetic executable; never launched')
        self.model = self.root/'model.stl';self.model.write_bytes(tetrahedron())
        evidence = []
        for name in ('context.json','dialog.png','export.png'):
            path = self.root/name
            if not path.exists(): path.write_text('synthetic UI evidence; not qualification')
            evidence.append(dict(path=str(path),artifact=recipe.p.file_record(path)))
        inputs = recipe.p.generation_inputs(dict(calibration='temperature',parameters=recipe.PARAMETERS,
            context_sha256=recipe.c.digest(context)),context,recipe.PIN)
        self.manifest = dict(schema='helix-orca-v1-native-reference/v1',method='native_orca_ui',
            imported_candidate=False,inputs_sha256=recipe.c.digest(inputs),source_commit=recipe.PIN,
            runtime=context['runtime'],artifact=recipe.p.file_record(self.native),evidence=evidence)
        self.manifest_path = self.root/'native-reference.json'
        self.manifest_path.write_bytes(recipe.c.canonical(self.manifest))
        self.receipt = dict(schema='helix-orca-v1-native-temperature-geometry/v1',source_commit=recipe.PIN,
            calibration='temperature',request_id='2'*32,origin_id=context['origin_id'],
            context_sha256=recipe.c.digest(context),parameters=recipe.PARAMETERS,nozzle_mm=.4,
            qualified=False,gcode_generated=False,not_applied=True,request_sha256='3'*64,
            native_metadata_sha256='4'*64,build_receipt_sha256='5'*64,
            build_inputs_sha256='6'*64,executable_sha256='7'*64,
            metrics=recipe.inspect_stl(self.model),
            model=dict(path='SECRET_DEVBOX_PATH',sha256=recipe.sha(self.model),source_commit=recipe.PIN,
                       nozzle_mm=.4,parameters=recipe.PARAMETERS))
        self.receipt_path = self.root/'geometry-receipt.json';self.receipt_path.write_bytes(recipe.c.canonical(self.receipt))
        self.args = argparse.Namespace(context=self.context_path,executable=self.exe,model=self.model,
            geometry_receipt=self.receipt_path,geometry_receipt_sha256=recipe.sha(self.receipt_path),
            model_sha256=recipe.sha(self.model),native=self.native,native_sha256=recipe.sha(self.native),
            native_manifest=self.manifest_path,native_manifest_sha256=recipe.sha(self.manifest_path),
            output_dir=self.root/'new-job',source_manifest=source_manifest,
            source_manifest_sha256=recipe.sha(source_manifest))
        for key,value in (('CONTEXT_SHA',recipe.c.digest(context)),('EXE_SHA',recipe.sha(self.exe)),
                          ('NATIVE_SHA',recipe.sha(self.native))):
            setting = patch.object(recipe,key,value);setting.start();self.addCleanup(setting.stop)

    def producer(self,request,context,out,config):
        self.assertEqual(request['calibration'],'temperature')
        self.assertEqual(request['parameters'],{'start':230,'end':190,'step':5,'scale':True})
        self.assertEqual(context,self.context)
        self.assertNotIn('runner',config);self.assertEqual(config['timeout_seconds'],45)
        self.assertEqual(config['temperature_model']['sha256'],recipe.sha(self.model))
        self.assertNotEqual(config['temperature_model']['path'],'SECRET_DEVBOX_PATH')
        out.mkdir();(out/'model.stl').write_bytes(self.model.read_bytes())
        candidate = out/'plate_1.gcode';candidate.write_text('synthetic candidate; not native proof')
        inputs = recipe.p.generation_inputs(request,context,recipe.PIN)
        report = dict(qualified=False,reason='SECRET_DIFFERENCE',differences=[{'raw':'SECRET_COMMAND'}],
            inputs=inputs,inputs_sha256=recipe.c.digest(inputs),candidate=recipe.p.file_record(candidate),
            reference=recipe.p.file_record(self.native),candidate_invariants={'model_moves':1},
            native_invariants={'model_moves':1},observations={})
        prepared = {key:request[key] for key in ('request_id','origin_id','context_sha256','calibration','parameters')}
        prepared.update(schema='helix-orca-v1-prepared/v1',request_sha256=recipe.c.digest(request),
            artifact=recipe.p.file_record(candidate),generator={'build':recipe.PIN,'route':'stock-cli-recipe-v1'},
            parity={'qualified':False,'report_sha256':recipe.c.digest(report),'reason':report['reason']},not_applied=True)
        for name,value in (('parity.json',report),('prepared.json',prepared),('invocation.json',{'argv':['SECRET_PATH']})):
            (out/name).write_bytes(recipe.c.canonical(value))
        return prepared

    def test_real_entrypoint_configuration_retains_false_parity_and_sanitizes_summary(self):
        with patch.object(recipe,'os',SimpleNamespace(name='nt',walk=os.walk)),patch.object(recipe.time,'time',return_value=100),\
                patch.object(recipe.g,'generate',side_effect=self.producer) as generate:
            summary = recipe.run(self.args)
        self.assertEqual(generate.call_count,1)
        self.assertFalse(summary['qualified']);self.assertFalse(summary['physical_actions'])
        self.assertEqual(summary['production_generator'],'integration.v1_generation.generate')
        self.assertEqual(summary['disposition'],'executable_difference')
        self.assertNotIn('SECRET',json.dumps(summary))
        self.assertIn('SECRET_PAYLOAD',(self.args.output_dir/'job/parity.json').read_text())
        self.assertEqual(recipe.sha(self.args.output_dir/'generation-provenance.json'),summary['generation_provenance_sha256'])
        self.assertEqual(json.loads((self.args.output_dir/'summary.json').read_text()),summary)

    def test_geometry_context_parameters_source_and_qualification_cannot_change(self):
        for key,value in (('context_sha256','f'*64),('parameters',dict(recipe.PARAMETERS,start=235)),
                          ('source_commit','e'*40),('qualified',True),('gcode_generated',True)):
            with self.subTest(key=key):
                receipt = copy.deepcopy(self.receipt);receipt[key] = value
                with self.assertRaisesRegex(recipe.Refused,'geometry_request_context_or_source'):
                    recipe.validate_geometry(self.context,self.model,self.args.model_sha256,receipt)
        receipt = copy.deepcopy(self.receipt);receipt['model']['parameters'] = dict(recipe.PARAMETERS,end=195)
        with self.assertRaisesRegex(recipe.Refused,'descriptor_mismatch'):
            recipe.validate_geometry(self.context,self.model,self.args.model_sha256,receipt)

    def test_wrong_geometry_metrics_and_corrupt_stl_are_rejected(self):
        bad = copy.deepcopy(self.receipt);bad['metrics']['triangles'] = 99
        with self.assertRaisesRegex(recipe.Refused,'exported_metrics'):
            recipe.validate_geometry(self.context,self.model,self.args.model_sha256,bad)
        self.model.write_bytes(self.model.read_bytes()[:-1])
        with self.assertRaisesRegex(recipe.Refused,'descriptor_mismatch'):
            recipe.validate_geometry(self.context,self.model,self.args.model_sha256,self.receipt)

    def test_retained_reference_cannot_change_parameters_or_repeat_evidence(self):
        bad = copy.deepcopy(self.manifest);bad['inputs_sha256'] = 'f'*64
        with self.assertRaisesRegex(recipe.Refused,'temperature_reference'):
            recipe.validate_reference(self.context,self.native,bad,100)
        bad = copy.deepcopy(self.manifest);bad['evidence'][2] = bad['evidence'][1]
        with self.assertRaisesRegex(recipe.Refused,'distinct_native'):
            recipe.validate_reference(self.context,self.native,bad,100)

    def test_slice_warning_failure_remains_private_and_never_becomes_summary(self):
        with patch.object(recipe,'os',SimpleNamespace(name='nt',walk=os.walk)),\
                patch.object(recipe.g,'generate',side_effect=recipe.g.GenerationBlocked('slice_warnings','SECRET_WARNING')):
            with self.assertRaises(recipe.g.GenerationBlocked): recipe.run(self.args)
        self.assertIn('SECRET_WARNING',(self.args.output_dir/'generation-failure.json').read_text())
        self.assertFalse((self.args.output_dir/'summary.json').exists())

    def test_platform_and_invalid_cli_cannot_execute_or_echo_private_input(self):
        with patch.object(recipe,'os',SimpleNamespace(name='posix')),patch.object(recipe.g,'generate') as generate:
            with self.assertRaisesRegex(recipe.Refused,'windows_execution_required'): recipe.run(None)
            generate.assert_not_called()
        result = subprocess.run([sys.executable,'-I','-S',str(SCRIPT),'--runner','SECRET_PATH'],
                                capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['failure'],'invalid_cli_arguments')
        self.assertNotIn('SECRET',result.stdout+result.stderr)

    def test_external_source_manifest_pin_and_exact_closure_are_mandatory(self):
        with self.assertRaisesRegex(recipe.Refused,'manifest_digest'):
            recipe.ReviewedSource(self.source_manifest,'f'*64)
        manifest = json.loads(self.source_manifest.read_text())
        manifest['files']['../escaped.py'] = 'e'*64
        self.source_manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(recipe.Refused,'inventory_mismatch'):
            recipe.ReviewedSource(self.source_manifest,recipe.sha(self.source_manifest))

    def test_stale_bytecode_extra_code_and_symlink_are_rejected_before_owned_load(self):
        for name in ('integration/unused.py','integration/v1_contract.pyc','scripts/unreviewed.pyd'):
            with self.subTest(name=name):
                path = self.source_root/name;path.write_bytes(b'never execute')
                with self.assertRaisesRegex(recipe.Refused,'unexpected_owned_source'):
                    recipe.ReviewedSource(self.source_manifest,self.args.source_manifest_sha256)
                path.unlink()
        cache = self.source_root/'integration/__pycache__';cache.mkdir()
        with self.assertRaisesRegex(recipe.Refused,'unexpected_owned_source'):
            recipe.ReviewedSource(self.source_manifest,self.args.source_manifest_sha256)
        cache.rmdir()
        linked = self.source_root/'integration/v1_contract.py'
        backup = self.root/'contract.py';linked.rename(backup);linked.symlink_to(backup)
        with self.assertRaisesRegex(recipe.Refused,'link_or_reparse'):
            recipe.ReviewedSource(self.source_manifest,self.args.source_manifest_sha256)
        recipe.load_owned.assert_not_called()

    def test_changed_source_after_generation_blocks_all_summary_and_provenance_writes(self):
        def mutate(request,context,out,config):
            prepared = self.producer(request,context,out,config)
            path = self.source_root/'integration/v1_contract.py'
            path.write_bytes(path.read_bytes()+b'\n# source changed during generation\n')
            return prepared
        with patch.object(recipe,'os',SimpleNamespace(name='nt',walk=os.walk)),\
                patch.object(recipe.g,'generate',side_effect=mutate):
            with self.assertRaisesRegex(recipe.Refused,'source_file_changed'): recipe.run(self.args)
        self.assertFalse((self.args.output_dir/'summary.json').exists())
        self.assertFalse((self.args.output_dir/'generation-provenance.json').exists())

    def test_source_change_during_sanitization_cannot_publish_qualified_summary(self):
        execute = recipe.ReviewedSource.execute
        def mutating_sanitizer(reviewed,name,relative):
            module = execute(reviewed,name,relative)
            original = module.sanitized
            def sanitized(*args):
                result = original(*args);result['qualified'] = True
                path = self.source_root/relative
                path.write_bytes(path.read_bytes()+b'\n# sanitizer changed\n')
                return result
            module.sanitized = sanitized
            return module
        with patch.object(recipe,'os',SimpleNamespace(name='nt',walk=os.walk)),\
                patch.object(recipe.g,'generate',side_effect=self.producer),\
                patch.object(recipe.ReviewedSource,'execute',mutating_sanitizer):
            with self.assertRaisesRegex(recipe.Refused,'source_file_changed'): recipe.run(self.args)
        self.assertFalse((self.args.output_dir/'summary.json').exists())
        self.assertFalse((self.args.output_dir/'generation-provenance.json').exists())

    def test_source_loader_compiles_captured_verified_bytes_and_rejects_disk_mutation(self):
        reviewed = recipe.ReviewedSource(self.source_manifest,self.args.source_manifest_sha256)
        path = self.source_root/'scripts/v1-windows-parity.py'
        marker = self.root/'should-never-exist'
        path.write_bytes(path.read_bytes()+('\nopen('+repr(str(marker))+',"w").write("bad")\n').encode())
        module = reviewed.execute('captured_sanitizer','scripts/v1-windows-parity.py')
        self.assertTrue(callable(module.sanitized));self.assertFalse(marker.exists())
        with self.assertRaisesRegex(recipe.Refused,'source_file_changed'): reviewed.recheck()

    def test_isolated_bootstrap_imports_only_manifest_source_and_never_bytecode(self):
        code = '''import importlib.util,json,pathlib,sys
spec=importlib.util.spec_from_file_location('fresh_recipe',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert not any(n=='integration' or n.startswith('integration.') for n in sys.modules)
guard=module.ReviewedSource(sys.argv[2],sys.argv[3])
module.load_owned(guard)
assert set(n for n in sys.modules if n.startswith('integration.'))=={
'integration.v1_contract','integration.v1_generation','integration.v1_parity',
'integration.v1_engine','integration.v1_temperature_geometry'}
assert not list(pathlib.Path(module.ROOT).rglob('*.pyc'))
assert not list(pathlib.Path(module.ROOT).rglob('__pycache__'))
guard.recheck()
print(json.dumps({'verified':True,'owned_modules':5,'bytecode':False}))
'''
        result = subprocess.run([sys.executable,'-I','-S','-B','-c',code,
            str(self.source_root/'scripts'/SCRIPT.name),str(self.source_manifest),
            self.args.source_manifest_sha256],capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'verified':True,'owned_modules':5,'bytecode':False})


if __name__ == '__main__': unittest.main()
