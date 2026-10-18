"""Raw Windows evidence stays local; returned diagnostics disclose fixed fields."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from integration import v1_contract as c, v1_parity as p
from test_v1_parity import temperature_gcode

SPEC=importlib.util.spec_from_file_location('v1_windows_parity',Path(__file__).resolve().parents[1]/'scripts/v1-windows-parity.py')
runner=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class WindowsParitySummary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        context={'schema':'helix-orca-v1-context/v1','origin_id':'1'*32,'runtime':p.PINS[runner.PIN],
                 'nozzle_mm':.4,'effective':{'gcode_flavor':'marlin'}}
        for role in ('printer','process','filament'):
            context[role]={state:{'name':'SECRET_PROFILE','config':{'setting':'SECRET_PRIVATE_VALUE'}} for state in ('saved','edited')}
        request={'schema':'helix-orca-v1-request/v1','request_id':'2'*32,'origin_id':context['origin_id'],
                 'context_sha256':c.digest(context),'calibration':'temperature',
                 'parameters':{'start':230,'end':220,'step':5,'scale':True},'created_at':100,'expires_at':200,'not_applied':True}
        for name,value in [('snapshot.json',context),('request.json',request)]:
            (self.root/name).write_bytes(c.canonical(value))
        candidate=self.root/'plate_1.gcode';native=self.root/'SECRET-native.gcode'
        candidate.write_text(temperature_gcode());native.write_text(temperature_gcode())
        helper=self.root/'helper.ps1';helper.write_text('# synthetic test provenance; never executed')
        archive=self.root/'inputs.zip';archive.write_bytes(b'synthetic test archive; never executed')
        bundle={'schema':'helix-orca-v1-generation-bundle/v1','source_commit':runner.PIN,'executable_sha256':runner.EXE_SHA,
                'context_sha256':c.digest(context),'request_sha256':c.digest(request),
                'inputs_sha256':c.digest(p.generation_inputs(request,context,runner.PIN)),
                'files':[p.file_record(self.root/name) for name in ('snapshot.json','request.json')]}
        manifest=self.root/'generation-bundle.json';manifest.write_bytes(c.canonical(bundle))
        record={'schema':'helix-orca-v1-windows-cli/v1','exit_code':0,'physical_actions':False,
                'executable_sha256':runner.EXE_SHA,'bundle_sha256':runner.sha(archive),'script_sha256':runner.sha(helper),
                'files':[p.file_record(candidate)]}
        result=self.root/'result-record.json';result.write_bytes(c.canonical(record))
        evidence=[]
        for name in ('inputs.png','exported.png'):
            path=self.root/name;path.write_bytes(b'synthetic UI fixture, not actual Windows evidence');evidence.append(path)
        self.args=argparse.Namespace(candidate=candidate,native=native,context=self.root/'snapshot.json',request=self.root/'request.json',
                                    bundle_manifest=manifest,result_record=result,generation_archive=archive,generation_helper=helper,
                                    native_evidence=evidence,output_dir=self.root/'reports')

    def test_historical_checker_revalidates_and_returns_no_raw_private_data(self):
        summary=runner.run(self.args)
        self.assertTrue(summary['qualified'])
        self.assertFalse(summary['physical_readiness'])
        self.assertFalse(summary['hardware_abi_qualified'])
        self.assertNotIn('SECRET',json.dumps(summary))
        self.assertNotIn('G1 X',json.dumps(summary))
        raw=(self.args.output_dir/'parity.json').read_text()
        self.assertIn('SECRET_PROFILE',raw)
        self.assertEqual(runner.sha(self.args.output_dir/'parity.json'),summary['report_sha256'])

    def test_changed_execution_or_staging_provenance_refuses(self):
        self.args.generation_helper.write_text('changed after execution')
        with self.assertRaises(runner.Refused) as ctx:runner.run(self.args)
        self.assertEqual(ctx.exception.code,'windows_execution_provenance_mismatch')
        self.assertFalse(self.args.output_dir.exists())

    def test_modified_candidate_is_not_attributed_to_original_cli_execution(self):
        self.args.candidate.write_text(self.args.candidate.read_text()+'M500\n')
        with self.assertRaises(runner.Refused) as ctx:runner.run(self.args)
        self.assertEqual(ctx.exception.code,'candidate_not_bound_to_cli_execution')

    def test_sanitization_never_forwards_failure_text_commands_or_configuration(self):
        report={'qualified':False,'reason':'SECRET_PATH','differences':[{'candidate':'SECRET_COMMAND'}],
                'inputs_sha256':'a'*64,'candidate':{'name':'SECRET_NAME','size':1,'sha256':'b'*64},
                'reference':{'name':'SECRET_REFERENCE','size':2,'sha256':'c'*64},
                'candidate_invariants':{'objects':['SECRET_OBJECT'],'model_moves':1},
                'emitted_settings':{'differences':[{'key':'private_setting','candidate':'SECRET_VALUE','classification':'unclassified effective setting difference'}]}}
        clean=runner.sanitized(report,{'secret':'SECRET_PREPARED'},{'evidence':[]},{})
        self.assertNotIn('SECRET',json.dumps(clean))
        self.assertEqual(clean['disposition'],'executable_difference')
        self.assertEqual(clean['unclassified_setting_difference_count'],1)


if __name__=='__main__':unittest.main()
