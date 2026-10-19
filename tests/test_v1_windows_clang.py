"""Configured compiler identity guards; fixtures never qualify Windows output."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
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


if __name__=='__main__':unittest.main()
