"""Configured compiler identity guards; fixtures never qualify Windows output."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from integration import v1_engine as e, v1_windows_dependencies as d


class ClangRecipe(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        spec=importlib.util.spec_from_file_location('clang_builder',e._ROOT/'scripts/v1-engine-windows.py')
        self.b=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.b)
        self.compiler=dict(family='Clang',version='22.1.3',frontend_variant='MSVC',visual_studio_major='18',
            generator='Ninja Multi-Config',configuration='Release',runtime_library='MD',
            msvc_toolset_version='14.51.36231',windows_sdk_version='10.0.26100.0',
            linker_family='LLD',linker_version='22.1.3',probe_sha256='a'*64,release_flags_sha256='b'*64)
        self.tools={name:dict(size=1,sha256=hashlib.sha256(name.encode()).hexdigest())for name in d.CLANG_TOOLS}
        self.publisher=dict(schema='helix-orca-v1-windows-builder/v2',repository='bigstupid007/helix-orca-calibration',
            workflow='.github/workflows/v1-windows-engine.yml',application_commit='c'*40,run_id='1',run_attempt='1',
            runner_image='windows-2025-vs2026',image_version='fixture-only',toolchain=self.tools,compiler=self.compiler,
            run_url='https://github.com/bigstupid007/helix-orca-calibration/actions/runs/1')

    def configuration(self):
        compiler='C:/VS18/VC/Tools/Llvm/x64/bin/clang-cl.exe';linker='C:/VS18/VC/Tools/Llvm/x64/bin/lld-link.exe'
        (self.root/'CMakeFiles/4.3.5').mkdir(parents=True)
        for lang in ('C','CXX'):
            values=dict(COMPILER=compiler,COMPILER_ID='Clang',COMPILER_VERSION='22.1.3',
                COMPILER_FRONTEND_VARIANT='MSVC',COMPILER_LINKER=linker)
            (self.root/('CMakeFiles/4.3.5/CMake'+lang+'Compiler.cmake')).write_text(''.join(
                'set(CMAKE_'+lang+'_'+key+' "'+value+'")\n'for key,value in values.items()))
        (self.root/'CMakeCache.txt').write_text('CMAKE_GENERATOR:INTERNAL=Ninja Multi-Config\nCMAKE_BUILD_TYPE:STRING=Release\n'
            'CMAKE_C_FLAGS_RELEASE:STRING=/MD /O2 /Ob2 /DNDEBUG\nCMAKE_CXX_FLAGS_RELEASE:STRING=/MD /O2 /Ob2 /DNDEBUG\n')

    def test_both_languages_actual_compiler_and_linker_metadata_are_required(self):
        self.configuration();actual=self.b.compiler_configuration(self.root)
        self.assertEqual(actual['c_compiler'],actual['cxx_compiler'])
        self.assertEqual(actual['c_linker'],actual['cxx_linker'])
        self.assertEqual(actual['runtime_library'],'MD')
        path=self.root/'CMakeFiles/4.3.5/CMakeCCompiler.cmake'
        path.write_text(path.read_text().replace('Clang','MSVC'))
        with self.assertRaisesRegex(ValueError,'Exact upstream Clang'):self.b.compiler_configuration(self.root)

    def test_wrong_version_fast_math_static_crt_and_generator_are_refused(self):
        self.configuration()
        compiler=self.root/'CMakeFiles/4.3.5/CMakeCXXCompiler.cmake';before=compiler.read_text()
        compiler.write_text(before.replace('22.1.3','22.1.4'))
        with self.assertRaises(ValueError):self.b.compiler_configuration(self.root)
        compiler.write_text(before)
        cache=self.root/'CMakeCache.txt';before=cache.read_text()
        for changed in (before.replace('/MD','/MT'),before+'CMAKE_CXX_FLAGS:STRING=/fp:fast\n',
                        before.replace('Ninja Multi-Config','Ninja'),before.replace('/MD','/MDd'),
                        before.replace('/MD ',''),before.replace('/O2 ',''),before.replace('/DNDEBUG','')):
            cache.write_text(changed)
            with self.assertRaises(ValueError):self.b.compiler_configuration(self.root)

    def test_explicit_clang_identity_cannot_be_relabelled_as_legacy_msvc(self):
        receipt=dict(application_commit='c'*40)
        self.assertTrue(e._windows_builder_valid(self.publisher,receipt))
        for field,value in (('version','22.1.4'),('runtime_library','MT'),('visual_studio_major','17'),
                            ('linker_family','unverified'),('windows_sdk_version','different')):
            bad=copy.deepcopy(self.publisher);bad['compiler'][field]=value
            with self.subTest(field=field):self.assertFalse(e._windows_builder_valid(bad,receipt))
        for changed in (dict(self.publisher,schema='helix-orca-v1-windows-builder/v1'),
                        dict(self.publisher,runner_image='windows-2022')):
            self.assertFalse(e._windows_builder_valid(changed,receipt))
        bad=copy.deepcopy(self.publisher);del bad['toolchain']['clang-cl']
        self.assertFalse(e._windows_builder_valid(bad,receipt))

    def test_dependency_provenance_binds_compiler_recipe_without_legacy_fallback(self):
        prefix=self.root/'prefix';downloads=self.root/'downloads'
        contract=dict(schema=d.CONTRACT_SCHEMA,source_commit=d.ORCA_SOURCE,submodules=[],
            dependencies_lock_sha256='d'*64,builder_sha256='e'*64,workflow_sha256='f'*64,
            module_sha256=hashlib.sha256(Path(d.__file__).read_bytes()).hexdigest(),toolchain=self.tools,
            environment={'COMPILER_IDENTITY':d._canonical(self.compiler).decode()},prefix=str(prefix),downloads=str(downloads))
        d.validate_provenance(contract,self.publisher,prefix,downloads,lambda:None)
        contract['environment']['COMPILER_IDENTITY']='{}'
        with self.assertRaisesRegex(d.BundleError,'compiler_recipe_identity_mismatch'):
            d.validate_provenance(contract,self.publisher,prefix,downloads,lambda:None)
        self.assertFalse(prefix.exists());self.assertFalse(downloads.exists())


class ArchivePreflight(unittest.TestCase):
    setUp=ClangRecipe.setUp
    def archive_fixture(self, off_valid=True, on_valid=False):
        run=self.b.Build.__new__(self.b.Build)
        run.work=self.root/'work';run.work.mkdir();run.evidence=run.work/'evidence';run.evidence.mkdir()
        run.environment={'PATH':'fixture-only','PATHEXT':'.EXE;.BAT'};run.guard=lambda:None
        tools=self.root/'tools';tools.mkdir()
        run.compiler=tools/'clang-cl.exe';run.selected_linker=tools/'lld-link.exe'
        for path in (run.compiler,run.selected_linker,tools/'llvm-lib.exe',tools/'ccache.exe'):path.write_bytes(b'fixture-only')
        run.tools={name:self.b.record(path)for name,path in [('clang-cl',run.compiler),('selected-linker',run.selected_linker)]}
        run.compiler_probe={'configuration':{'same_actual_flags':'fixture-only'}}
        calls=[]
        def execute(label,argv,**kwargs):
            calls.append((label,argv,kwargs))
            build=run.work/label.removesuffix('-configure').removesuffix('-build')
            enabled='-on-'in label
            if label.endswith('-configure'):
                build.mkdir();(build/'detected-ccache.txt').write_text(str(tools/'ccache.exe')if enabled else'')
                (build/'CMakeCache.txt').write_text('CMAKE_AR:FILEPATH='+str(tools/'llvm-lib.exe'))
                (build/'detected-launcher.txt').write_text('ccache'if enabled else'')
                return 0
            valid=on_valid if enabled else off_valid
            if valid:
                (build/'probe.cpp.obj').write_bytes(b'\x64\x86'+b'0'*30)
                (build/'Release').mkdir();(build/'Release/helix_archive_probe.lib').write_bytes(b'!<arch>\nfixture')
            return 0 if valid else 1
        run.run=execute
        process=lambda argv,**kwargs:SimpleNamespace(returncode=0,stdout=str(tools/'ccache.exe')+'\n'if argv[0]=='where.exe'else'ccache fixture',stderr='')
        return run,calls,process

    def test_optional_cache_failure_does_not_replace_required_uncached_outputs(self):
        run,calls,process=self.archive_fixture()
        with patch.object(self.b.subprocess,'run',side_effect=process),patch.object(self.b,'compiler_configuration',return_value=run.compiler_probe['configuration']):
            run.probe_archive()
        result=json.loads((run.evidence/'archive-probe.json').read_text())
        self.assertFalse(result['qualified']);self.assertFalse(result['physical_actions'])
        self.assertFalse(result['results']['on']['objects_valid']);self.assertEqual(result['results']['on']['exit_code'],1)
        self.assertTrue(result['results']['off']['objects_valid']);self.assertTrue(result['results']['off']['archive_valid'])
        self.assertTrue(calls[1][2]['allow_failure']);self.assertFalse(calls[3][2]['allow_failure'])
        self.assertIn('-DUSE_CCACHE:BOOL=OFF',calls[2][1])
        self.assertEqual(calls[1][1][3:],calls[3][1][3:])
        self.assertEqual(result['results']['off']['rule_launch_link'],'')
        self.assertEqual(result['results']['on']['archiver'],result['results']['off']['archiver'])

    def test_missing_off_outputs_are_fatal_even_if_cache_on_produced_them(self):
        run,calls,process=self.archive_fixture(off_valid=False,on_valid=True)
        with patch.object(self.b.subprocess,'run',side_effect=process),patch.object(self.b,'compiler_configuration',return_value=run.compiler_probe['configuration']):
            with self.assertRaisesRegex(ValueError,'Uncached native object'):run.probe_archive()
        result=json.loads((run.evidence/'archive-probe.json').read_text())
        self.assertTrue(result['results']['on']['archive_valid']);self.assertFalse(result['results']['off']['archive_valid'])

    def test_preflight_only_main_never_calls_dependency_or_package_build(self):
        import time
        from unittest.mock import Mock
        evidence=self.root/'evidence';evidence.mkdir();(evidence/'archive-probe.json').write_text('{}')
        run=SimpleNamespace(evidence=evidence,compiler_identity={'fixture_only':True},children=[],
            start=time.monotonic(),free=0,min_free=0,package=Mock(side_effect=AssertionError('package must not run')))
        args=['builder','--source',str(self.root/'source'),'--work',str(self.root/'work'),'--toolchain-preflight-only']
        with patch.object(self.b.sys,'argv',args),patch.object(self.b,'Build',return_value=run):self.b.main()
        run.package.assert_not_called()
        summary=json.loads((evidence/'toolchain-preflight-summary.json').read_text())
        self.assertTrue(summary['completed']);self.assertFalse(summary['built']);self.assertFalse(summary['qualified'])
        self.assertEqual(json.loads((evidence/'build-lifecycle.json').read_text())['state'],'complete')

    def test_archive_diagnostic_cannot_change_compiler_recipe(self):
        run,calls,process=self.archive_fixture()
        with patch.object(self.b.subprocess,'run',side_effect=process),patch.object(self.b,'compiler_configuration',return_value={'changed_flags':True}):
            with self.assertRaisesRegex(ValueError,'compiler or flags differ'):run.probe_archive()
        self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
