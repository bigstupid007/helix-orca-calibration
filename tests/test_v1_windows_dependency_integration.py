"""Build checkpoint wiring with synthetic files; never native qualification."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from integration import v1_engine as engine


class DependencyBuildWiring(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        spec=importlib.util.spec_from_file_location('checkpoint_builder',engine._ROOT/'scripts/v1-engine-windows.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.build=self.module.Build.__new__(self.module.Build)
        self.build.work=self.root/'work';self.build.work.mkdir()
        self.build.source=self.root/'source';self.build.source.mkdir()
        self.build.evidence=self.build.work/'evidence';self.build.evidence.mkdir()
        self.build.environment={'CMAKE_BUILD_PARALLEL_LEVEL':'2','_CL_':'','CL_MPCOUNT':'1'}
        self.build.compiler=Path('C:/VS18/VC/Tools/Llvm/x64/bin/clang-cl.exe')
        self.build.compiler_identity=dict(family='Clang',version='22.1.3',frontend_variant='MSVC',visual_studio_major='18',
            generator='Ninja Multi-Config',configuration='Release',runtime_library='MD',msvc_toolset_version='14.51.36231',
            windows_sdk_version='10.0.26100.0',linker_family='LLD',linker_version='22.1.3',probe_sha256='a'*64,release_flags_sha256='b'*64)
        self.build.verify_compiler_configuration=lambda path:None
        self.build.tools={name:dict(size=1,sha256='1'*64)for name in self.module.dependencies.CLANG_TOOLS}
        self.build.children=[]
        self.build.guard=lambda:None
        self.calls=[];self.environments=[]
        def run(label,argv,environment=None):
            self.calls.append((label,argv));self.environments.append(environment)
            if label=='deps-configure':
                for directory in ('deps','prefix','downloads'):
                    (self.build.work/directory).mkdir()
                (self.build.work/'deps/intermediate').write_bytes(b'synthetic compiler intermediate')
                (self.build.work/'prefix/library.lib').write_bytes(b'synthetic dependency payload, not a real library')
                (self.build.work/'downloads/source.tar').write_bytes(b'synthetic source archive')
        self.build.run=run
        self.lock={'sources':[dict(target='dep_fixture')],'in_tree_targets':[]}
        self.submodules=[]  # Exact pinned source has no submodules.
        self.publisher=dict(schema='helix-orca-v1-windows-builder/v2',compiler=self.build.compiler_identity,
            repository='bigstupid007/helix-orca-calibration',workflow='.github/workflows/v1-windows-engine.yml',
            application_commit='3'*40,run_id='1',run_attempt='1',runner_image='windows-2025-vs2026',
            image_version='fixture-only',toolchain=self.build.tools,
            run_url='https://github.com/bigstupid007/helix-orca-calibration/actions/runs/1')

    def test_cold_checkpoint_retains_complete_inputs_and_intermediates(self):
        result=self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
        self.assertFalse(result['qualified']);self.assertFalse(result['restored'])
        self.assertEqual([row[0]for row in self.calls],['deps-configure','dep_fixture'])
        self.assertTrue((self.build.work/'deps/intermediate').is_file())
        self.assertTrue((self.build.work/'prefix/library.lib').is_file())
        self.assertTrue((self.build.work/'downloads/source.tar').is_file())
        self.assertEqual(result['sha256'],self.module.sha(self.build.work/'native-windows-dependencies.zip'))
        self.assertFalse((self.build.evidence/'dependency-intermediates-retired.json').exists())

    def test_explicit_pinned_restore_skips_all_dependency_commands_and_keeps_original_producer(self):
        receipt=self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
        self.calls.clear()
        for directory in ('deps','prefix','downloads'):shutil.rmtree(self.build.work/directory)
        self.build.dependency_input=dict(path=self.build.work/'native-windows-dependencies.zip',
            sha256=receipt['sha256'],run_id='1',run_attempt='1',application_commit='3'*40)
        current=dict(self.publisher,run_id='2',application_commit='4'*40,
            run_url='https://github.com/bigstupid007/helix-orca-calibration/actions/runs/2')
        result=self.build.prepare_dependencies(self.lock,self.submodules,current)
        self.assertTrue(result['restored']);self.assertFalse(result['qualified'])
        self.assertEqual(result['publisher'],self.publisher)
        self.assertEqual(self.calls,[])
        self.assertFalse((self.build.work/'deps').exists())

    def test_changed_compiler_flags_or_include_path_reject_restore_before_commands(self):
        receipt=self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
        self.calls.clear()
        for directory in ('deps','prefix','downloads'):shutil.rmtree(self.build.work/directory)
        self.build.dependency_input=dict(path=self.build.work/'native-windows-dependencies.zip',
            sha256=receipt['sha256'],run_id='1',run_attempt='1',application_commit='3'*40)
        for name,value in (('CL','/fp:fast'),('Include','different-include-path')):
            with self.subTest(name=name):
                self.build.environment[name]=value
                with self.assertRaises(self.module.dependencies.BundleError):
                    self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
                self.assertEqual(self.calls,[])
                self.assertFalse((self.build.work/'prefix').exists())
                del self.build.environment[name]

    def test_occt_override_stays_within_declared_four_compiler_bound(self):
        self.lock['sources']=[dict(target='dep_OCCT'),dict(target='dep_fixture')]
        self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
        self.assertEqual(self.environments,[None,dict(self.build.environment,CMAKE_BUILD_PARALLEL_LEVEL='4'),None])
        self.assertEqual(self.build.environment['CMAKE_BUILD_PARALLEL_LEVEL'],'2')
        self.assertEqual(self.environments[1]['_CL_'],'')
        self.assertEqual(self.environments[1]['CL_MPCOUNT'],'1')
        self.assertEqual(self.calls[1][1][-2:],['--parallel','1'])
        contract=json.loads((self.build.evidence/'dependency-contract.json').read_text())
        self.assertEqual(json.loads(contract['environment']['DEPENDENCY_TARGET_ENVIRONMENTS']),
            {'dep_OCCT':{'CMAKE_BUILD_PARALLEL_LEVEL':'4'},'dep_python3':{'_CL_':'/MP1'},'dep_OpenSSL':{'_CL_':'/MP1'}})

    def test_only_real_msvc_dependencies_receive_appended_single_compiler_hint(self):
        self.lock['sources']=[dict(target=name)for name in ('dep_python3','dep_OpenSSL','dep_fixture')]
        self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
        self.assertEqual(self.environments,[None,dict(self.build.environment,_CL_='/MP1'),
            dict(self.build.environment,_CL_='/MP1'),None])
        self.assertEqual(self.build.environment['_CL_'],'')
        contract=json.loads((self.build.evidence/'dependency-contract.json').read_text())
        overrides=json.loads(contract['environment']['DEPENDENCY_TARGET_ENVIRONMENTS'])
        self.assertEqual(overrides['dep_python3'],{'_CL_':'/MP1'})
        self.assertEqual(overrides['dep_OpenSSL'],{'_CL_':'/MP1'})

    def test_bad_provenance_rejected_before_any_dependency_command(self):
        with self.assertRaisesRegex(self.module.dependencies.BundleError,'exact_initialized_submodules_required'):
            self.build.prepare_dependencies(self.lock,['-'+'2'*40+' deps_src/uninitialized'],self.publisher)
        self.assertEqual(self.calls,[])
        self.assertFalse((self.build.work/'deps').exists())
        self.assertFalse((self.build.work/'native-windows-dependencies.zip').exists())

    def test_environment_capture_is_case_insensitive_and_rejects_collisions(self):
        selected=self.module.dependency_environment({'VCToolsVersion':'14.44','Include':'sdk','CL':'/O2'})
        self.assertEqual(selected['VCTOOLSVERSION'],'14.44')
        self.assertEqual(selected['INCLUDE'],'sdk')
        self.assertEqual(selected['CL'],'/O2')
        with self.assertRaisesRegex(ValueError,'Ambiguous case-insensitive'):
            self.module.dependency_environment({'Include':'sdk','INCLUDE':'other'})

    def test_provenance_failure_is_fatal_but_optional_checkpoint_capacity_is_explicit(self):
        with patch.object(self.module.dependencies,'create_bundle',
                side_effect=self.module.dependencies.BundleError('closed_source_inventory_changed')):
            with self.assertRaisesRegex(self.module.dependencies.BundleError,'closed_source_inventory_changed'):
                self.build.prepare_dependencies(self.lock,self.submodules,self.publisher)
        self.assertTrue((self.build.work/'deps/intermediate').is_file())
        self.assertFalse((self.build.evidence/'dependency-checkpoint-failure.json').exists())
        for directory in ('deps','prefix','downloads'):shutil.rmtree(self.build.work/directory)
        with patch.object(self.module.dependencies,'create_bundle',
                side_effect=self.module.dependencies.BundleError('archive_size_bound_exceeded')):
            self.assertIsNone(self.build.prepare_dependencies(self.lock,self.submodules,self.publisher))
        self.assertTrue((self.build.work/'deps/intermediate').is_file())
        failed=json.loads((self.build.evidence/'dependency-checkpoint-failure.json').read_text())
        self.assertFalse(failed['available']);self.assertFalse(failed['qualified'])

    def test_partial_or_malformed_external_checkpoint_pins_cannot_start_build(self):
        args=argparse.Namespace(dependency_bundle=None,dependency_bundle_sha256=None,dependency_run_id=None,
            dependency_application_commit=None,dependency_run_attempt=None)
        self.assertIsNone(self.module.dependency_input(args))
        args.dependency_bundle=Path('checkpoint.zip')
        with self.assertRaises(ValueError):self.module.dependency_input(args)
        args.dependency_bundle_sha256='0'*64;args.dependency_run_id='1';args.dependency_application_commit='3'*40
        self.assertEqual(self.module.dependency_input(args)['run_attempt'],'1')
        args.dependency_run_id='1;bad'
        with self.assertRaises(ValueError):self.module.dependency_input(args)
