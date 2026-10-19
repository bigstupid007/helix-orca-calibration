"""Public-code/local-input production driver provenance and output privacy."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from integration import v1_contract as c, v1_parity as p

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/v1-windows-stock-yolo.py'
SPEC=importlib.util.spec_from_file_location('stock_yolo_driver',SCRIPT)
driver=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(driver)


class WindowsStockYolo(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        context=dict(schema='helix-orca-v1-context/v1',origin_id='1'*32,runtime=p.PINS[driver.PIN],nozzle_mm=.4,
                     effective={'SECRET_EFFECTIVE':'SECRET_PROFILE_PAYLOAD'})
        for role in ('printer','process','filament'):
            context[role]={state:dict(name='SECRET_PROFILE',config={'key':'SECRET_VALUE'}) for state in ('saved','edited')}
        self.context=context
        context_path=self.root/'SECRET-context.json';context_path.write_bytes(c.canonical(context))
        native=self.root/'SECRET-native.gcode';native.write_bytes(b'SYNTHETIC NATIVE FIXTURE; NOT QUALIFICATION')
        executable=self.root/'orca.exe';executable.write_bytes(b'SYNTHETIC TEST ONLY; NEVER EXECUTED')
        asset=self.root/'public-asset.3mf';asset.write_bytes(b'SYNTHETIC PUBLIC ASSET FIXTURE')
        evidence=[]
        for name in ('native-dialog.png','native-export.png'):
            item=self.root/name;item.write_bytes(b'Synthetic evidence fixture');evidence.append(item)
        manifest=p.create_native_reference(native,context,'flow_ratio_yolo',{'pass':1},driver.PIN,evidence)
        native_manifest=self.root/'native-reference.json';native_manifest.write_bytes(c.canonical(manifest))
        self.args=argparse.Namespace(context=context_path,native=native,native_manifest=native_manifest,
            executable=executable,asset=asset,output_dir=self.root/'fresh-case')
        for key,value in (('CONTEXT_SHA',c.digest(context)),('NATIVE_SHA',driver.sha(native)),
                          ('EXE_SHA',driver.sha(executable)),('ASSET_SHA',driver.sha(asset))):
            setting=patch.object(driver,key,value);setting.start();self.addCleanup(setting.stop)

    def synthetic_producer(self,request,context,out,config):
        self.assertNotIn('runner',config)
        self.assertEqual(config['timeout_seconds'],45)
        self.assertEqual(request['created_at'],100)
        self.assertEqual(request['expires_at'],3700)
        self.assertEqual(request['parameters'],{'pass':1})
        self.assertEqual(context,self.context)
        out.mkdir()
        candidate=out/'plate_1.gcode';candidate.write_bytes(b'SYNTHETIC CANDIDATE ONLY')
        inputs=p.generation_inputs(request,context,driver.PIN)
        native_manifest=json.loads(self.args.native_manifest.read_text())
        self.assertEqual(c.digest(inputs),native_manifest['inputs_sha256'])
        report=dict(qualified=False,reason='SECRET raw failure',differences=[dict(candidate='SECRET_COMMAND')],
            inputs=inputs,inputs_sha256=c.digest(inputs),candidate=p.file_record(candidate),reference=p.file_record(self.args.native),
            candidate_invariants=dict(model_moves=1,objects=['SECRET_OBJECT']),native_invariants=dict(model_moves=1),observations={})
        prepared={key:request[key] for key in ('request_id','origin_id','context_sha256','calibration','parameters')}
        prepared.update(schema='helix-orca-v1-prepared/v1',request_sha256=c.digest(request),artifact=p.file_record(candidate),
            generator=dict(build=driver.PIN,route='stock-cli-recipe-v1'),parity=dict(qualified=False,report_sha256=c.digest(report),reason=report['reason']),not_applied=True)
        (out/'parity.json').write_bytes(c.canonical(report))
        (out/'prepared.json').write_bytes(c.canonical(prepared))
        (out/'invocation.json').write_bytes(c.canonical({'argv':['SECRET_LOCAL_PATH']}))
        return prepared

    def test_fresh_nonce_real_entrypoint_config_and_private_local_provenance(self):
        with patch.object(driver.time,'time',return_value=100), patch.object(driver.g,'generate',side_effect=self.synthetic_producer) as generate:
            summary=driver.run(self.args)
        self.assertEqual(generate.call_count,1)
        self.assertFalse(summary['qualified']);self.assertFalse(summary['physical_actions'])
        self.assertEqual(summary['production_generator'],'integration.v1_generation.generate')
        self.assertNotIn('SECRET',json.dumps(summary))
        self.assertNotIn('argv',summary)
        self.assertLess(len(c.canonical(summary)),65536)
        raw=(self.args.output_dir/'job/parity.json').read_text()
        self.assertIn('SECRET_PROFILE_PAYLOAD',raw)
        self.assertEqual(driver.sha(self.args.output_dir/'generation-provenance.json'),summary['generation_provenance_sha256'])
        request=json.loads((self.args.output_dir/'request.json').read_text())
        self.assertEqual(len(request['request_id']),32)

    def test_changed_pin_or_native_evidence_never_calls_generator(self):
        self.args.asset.write_bytes(b'changed public asset')
        with patch.object(driver.g,'generate') as generate, self.assertRaises(driver.Refused):driver.run(self.args)
        generate.assert_not_called();self.assertFalse(self.args.output_dir.exists())

    def test_generation_failure_diagnostic_stays_local(self):
        with patch.object(driver.g,'generate',side_effect=driver.g.GenerationBlocked('slice_failed','SECRET_LOCAL_REASON')):
            with self.assertRaises(driver.g.GenerationBlocked):driver.run(self.args)
        self.assertIn('SECRET_LOCAL_REASON',(self.args.output_dir/'generation-failure.json').read_text())
        self.assertFalse((self.args.output_dir/'summary.json').exists())

    def test_invalid_cli_does_not_echo_paths_or_accept_runner_injection(self):
        result=subprocess.run([sys.executable,'-I','-S',str(SCRIPT),'--runner','SECRET_PATH'],capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['failure'],'invalid_cli_arguments')
        self.assertNotIn('SECRET',result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
