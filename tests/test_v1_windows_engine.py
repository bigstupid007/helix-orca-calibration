"""Synthetic PE/receipt guard tests, never actual Windows build qualification."""
import copy
import importlib.util
from pathlib import Path
import struct
import time
import unittest
from unittest.mock import patch
from integration import v1_engine as engine
from integration import v1_pe as pe
import test_v1_native_transport as fixtures


def pe_fixture(imports, dll=False):
    data = bytearray(1536)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<HH', data, 132, 0x8664, 1)
    struct.pack_into('<HH', data, 148, 240, 0x2002 if dll else 2)
    optional = 152
    struct.pack_into('<H', data, optional, 0x20b)
    struct.pack_into('<I', data, optional+60, 512)
    struct.pack_into('<I', data, optional+108, 16)
    struct.pack_into('<II', data, optional+120, 4096, (len(imports)+1)*20)
    struct.pack_into('<IIII', data, optional+240+8, 1024, 4096, 1024, 512)
    for index, name in enumerate(imports):
        struct.pack_into('<I', data, 512+20*index+12, 4352+index*128)
        encoded = name.encode()+b'\0'
        data[768+index*128:768+index*128+len(encoded)] = encoded
    return data


class WindowsNativeGuards(unittest.TestCase):
    record = fixtures.NativeTransport.record
    refresh_receipts = fixtures.NativeTransport.refresh_receipts
    runner = fixtures.NativeTransport.runner
    generate = fixtures.NativeTransport.generate

    def setUp(self):
        fixtures.NativeTransport.setUp(self)
        self.exe.unlink()
        self.exe = self.root/'helix_orca_native.exe'
        self.exe.write_bytes(pe_fixture(['kernel32.dll', 'msvcp140.dll']))
        self.exe.chmod(0o700)
        dll = self.root/'msvcp140.dll'
        dll.write_bytes(pe_fixture(['kernel32.dll'], dll=True))
        self.inputs['owned_inputs'] = {name:engine._sha_file(engine._ROOT/name) for name in engine._WINDOWS_OWNED_INPUTS}
        self.inputs['builder'] = {'schema': 'helix-orca-v1-windows-builder/v1',
            'repository': 'bigstupid007/helix-orca-calibration', 'workflow': '.github/workflows/v1-windows-engine.yml',
            'runner_image': 'windows-2022', 'image_version': 'synthetic-checker-only',
            'run_id': '1', 'run_attempt': '1', 'application_commit': '0'*40,
            'run_url': 'https://github.com/bigstupid007/helix-orca-calibration/actions/runs/1',
            'toolchain': {name:{'sha256':'1'*64, 'size':1} for name in ('cl','link','cmake','ninja','perl','msbuild')}}
        self.receipt.update(application_commit='0'*40, target=dict(engine._WINDOWS_TARGET),
            runtime_dlls={'msvcp140.dll': {'sha256':engine._sha_file(dll), 'size':dll.stat().st_size}},
            import_closure={self.exe.name:['kernel32.dll','msvcp140.dll'], 'msvcp140.dll':['kernel32.dll']},
            system_imports=['kernel32.dll'])
        self.receipt['capabilities']['target'] = dict(engine._WINDOWS_TARGET)
        self.receipt['adapter'] = dict(size=self.exe.stat().st_size, sha256=engine._sha_file(self.exe))
        self.config['native_executable'] = self.record(self.exe)
        self.refresh_receipts()
        self.addCleanup(patch.stopall)
        patch.object(engine.platform, 'system', return_value='Windows').start()
        patch.object(engine.platform, 'machine', return_value='AMD64').start()

    def test_actual_pe_envelope_without_reference_is_still_unqualified(self):
        result = self.generate()
        self.assertFalse(result['parity']['qualified'])
        self.assertTrue(self.called)

    def test_real_warning_semantics_remain_fatal_on_windows_envelope(self):
        fixtures.NativeTransport.test_legitimate_bed_warning_reports_exact_blocker_without_mutating_inputs(self)

    def test_wrong_architecture_and_dll_substitution_never_dispatch(self):
        data = bytearray(self.exe.read_bytes())
        struct.pack_into('<H', data, 132, 0x14c)
        self.exe.write_bytes(data)
        self.receipt['adapter']['sha256'] = engine._sha_file(self.exe)
        self.config['native_executable'] = self.record(self.exe)
        self.refresh_receipts()
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.assertFalse(self.called)
        self.exe.write_bytes(pe_fixture(['kernel32.dll', 'msvcp140.dll']))
        self.receipt['adapter']['sha256'] = engine._sha_file(self.exe)
        self.config['native_executable'] = self.record(self.exe)
        self.refresh_receipts()
        (self.root/'msvcp140.dll').write_bytes(pe_fixture(['user32.dll'], dll=True))
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.assertFalse(self.called)

    def test_extra_or_missing_dll_and_unresolved_imports_never_dispatch(self):
        (self.root/'extra.dll').write_bytes(pe_fixture([], dll=True))
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        (self.root/'extra.dll').unlink()
        self.receipt['import_closure'][self.exe.name] = ['kernel32.dll']
        self.refresh_receipts()
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.assertFalse(self.called)

    def test_foreign_builder_or_mismatched_commit_never_enables_capability(self):
        original = copy.deepcopy(self.inputs['builder'])
        for key, value in [('repository','foreign/repository'), ('run_url','https://example.test/run'),
                           ('application_commit','2'*40), ('workflow','other.yml')]:
            self.inputs['builder'] = dict(original, **{key:value})
            self.refresh_receipts()
            with self.assertRaises(engine.NativeEngineBlocked):
                self.generate()
            self.assertFalse(any(row['available'] for row in engine.capabilities(self.config)))
        self.assertFalse(self.called)

    def test_truncated_and_unsafe_pe_import_names_are_rejected(self):
        self.exe.write_bytes(pe_fixture(['../evil.dll']))
        with self.assertRaises(ValueError):
            pe.inspect(self.exe)
        self.exe.write_bytes(pe_fixture(['kernel32.dll'])[:700])
        with self.assertRaises(ValueError):
            pe.inspect(self.exe)

    def test_source_inventory_rejects_missing_substituted_and_duplicate_archives(self):
        import hashlib
        spec = importlib.util.spec_from_file_location('windows_source_inventory', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        downloads = self.root/'downloads'
        downloads.mkdir()
        source = downloads/'source.tar.gz'
        payload = b'known source archive bytes'
        source.write_bytes(payload)
        lock = {'sources':[{'url':'https://source.example/source.tar.gz',
                            'sha256':hashlib.sha256(payload).hexdigest()}],
                'source_supplements':[], 'binary_only_downloads':['excluded.zip']}
        roots = {'dependency-archives':downloads}
        inventory = module.inventory_source_archives(lock, roots, lambda:None)
        self.assertEqual(inventory['archives'][0]['size'], len(payload))
        source.unlink()
        with self.assertRaises(module.SourceMaterialsUnavailable):
            module.inventory_source_archives(lock, roots, lambda:None)
        source.write_bytes(b'substituted source archive')
        with self.assertRaises(module.SourceMaterialsUnavailable):
            module.inventory_source_archives(lock, roots, lambda:None)
        source.write_bytes(payload)
        duplicate = downloads/'duplicate.tar.gz'
        duplicate.write_bytes(payload)
        with self.assertRaises(module.SourceMaterialsUnavailable):
            module.inventory_source_archives(lock, roots, lambda:None)

    def test_source_zip_uses_only_verified_archives_and_rechecks_mutation(self):
        import hashlib
        import io
        import zipfile
        spec = importlib.util.spec_from_file_location('windows_source_zip', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        downloads = self.root/'archive-inputs'
        downloads.mkdir()
        payload = b'original verified source bytes'
        source = downloads/'source.tar.gz'
        source.write_bytes(payload)
        (downloads/'excluded.zip').write_bytes(b'binary-only download')
        (downloads/'unlocked.zip').write_bytes(b'unrecognized archive must never be copied')
        lock = {'sources':[{'url':'https://source.example/source.tar.gz',
                            'sha256':hashlib.sha256(payload).hexdigest()}],
                'source_supplements':[], 'binary_only_downloads':['excluded.zip']}
        roots = {'dependency-archives':downloads}
        inventory = module.inventory_source_archives(lock, roots, lambda:None)
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            module.write_verified_archives(archive, inventory, roots, lambda:None)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist(), ['dependency-archives/source.tar.gz'])
            self.assertEqual(archive.read(archive.namelist()[0]), payload)
        source.write_bytes(b'X'+payload[1:])
        with zipfile.ZipFile(io.BytesIO(), 'w') as archive:
            with self.assertRaises(module.SourceMaterialsUnavailable):
                module.write_verified_archives(archive, inventory, roots, lambda:None)

    def test_source_supplements_are_hash_bound_bounded_and_never_executed(self):
        import hashlib
        import io
        spec = importlib.util.spec_from_file_location('windows_builder_supplements', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = b'checker-only archive bytes; never extracted or executed'
        row = {'component':'fixture','version':'0','url':'https://source.example/fixture.tar.bz2',
               'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        class Response(io.BytesIO):
            def geturl(self):
                return row['url']
        guards = []
        with patch.object(module, 'urlopen', return_value=Response(payload)):
            result = module.retain_source_supplements({'source_supplements':[row]}, self.root/'source-materials', lambda:guards.append(True))
        self.assertTrue(result[0]['verified'])
        self.assertFalse(result[0]['executed'])
        self.assertTrue(guards)
        self.assertEqual((self.root/'source-materials/fixture.tar.bz2').read_bytes(), payload)
        for name, modified in [('digest',dict(row,sha256='0'*64)), ('oversize',dict(row,size=1))]:
            with patch.object(module, 'urlopen', return_value=Response(payload)):
                with self.assertRaises(module.SourceMaterialsUnavailable):
                    module.retain_source_supplements({'source_supplements':[modified]}, self.root/name, lambda:None)
        def refused():
            raise RuntimeError('actual resource guard')
        with patch.object(module, 'urlopen', return_value=Response(payload)):
            with self.assertRaisesRegex(RuntimeError, 'actual resource guard'):
                module.retain_source_supplements({'source_supplements':[row]}, self.root/'guarded', refused)

    def test_cmake_cache_path_values_do_not_contain_windows_escape_sequences(self):
        from pathlib import PureWindowsPath
        spec = importlib.util.spec_from_file_location('windows_builder_paths', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path = PureWindowsPath('D:/a/_temp/native build/prefix')
        for key in ('DESTDIR', 'DEP_DOWNLOAD_DIR', 'DEP_PYTHON_HOST', 'CMAKE_PREFIX_PATH',
                    'CMAKE_PROJECT_OrcaSlicer_INCLUDE'):
            argument = module.cmake_path(key, path)
            self.assertEqual(argument, '-D'+key+'=D:/a/_temp/native build/prefix')
            self.assertNotIn('\\', argument)

    def test_source_byte_diagnostic_retains_crlf_mismatch_without_normalizing(self):
        import hashlib
        import json
        spec = importlib.util.spec_from_file_location('windows_builder_source', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected, actual = b'a\nb\n', b'a\r\nb\r\n'
        name = 'public-source.hpp'
        source = self.root/'source'
        source.mkdir()
        evidence = self.root/'evidence'
        evidence.mkdir()
        (source/name).write_bytes(actual)
        with patch.object(engine, 'SOURCE_HASHES', {name:hashlib.sha256(expected).hexdigest()}):
            with self.assertRaises(engine.NativeSourceError):
                module.audit_source(source, evidence)
            row = json.loads((evidence/'source-byte-inventory.json').read_text())['files'][name]
            self.assertEqual(row['actual_sha256'], hashlib.sha256(actual).hexdigest())
            self.assertEqual(row['expected_sha256'], hashlib.sha256(expected).hexdigest())
            self.assertEqual((row['size'], row['lf_count'], row['crlf_count']), (6, 2, 2))
            self.assertEqual((source/name).read_bytes(), actual)
            (source/name).write_bytes(expected)
            self.assertTrue(module.audit_source(source, evidence)['source_verified'])

    def test_msvc_environment_call_uses_owned_batch_without_nested_command_quotes(self):
        spec = importlib.util.spec_from_file_location('windows_builder_env', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        vs = self.root/'Program Files'/'Visual Studio'
        developer = vs/'Common7/Tools/VsDevCmd.bat'
        developer.parent.mkdir(parents=True)
        developer.write_text('test-only')
        msbuild = vs/'MSBuild/Current/Bin/amd64/MSBuild.exe'
        msbuild.parent.mkdir(parents=True)
        msbuild.write_bytes(b'test-only')
        run = module.Build.__new__(module.Build)
        run.work = self.root
        with patch.dict(module.os.environ, {'ProgramFiles(x86)':str(self.root), 'COMSPEC':'cmd.exe'}), \
                patch.object(module.subprocess, 'check_output', side_effect=[str(vs), 'VSCMD_ARG_TGT_ARCH=x64\nPATH=test-only\n']) as call:
            environment = run.msvc_environment()
        batch = self.root/'native-msvc-environment.cmd'
        self.assertIn('call "'+str(developer)+'" -arch=x64 -host_arch=x64', batch.read_text())
        self.assertIn('if errorlevel 1 exit /b %errorlevel%', batch.read_text())
        self.assertEqual(call.call_args_list[1].args[0], ['cmd.exe','/d','/c',str(batch)])
        self.assertEqual(environment['MSBUILD'], str(msbuild))

    def test_constructor_failure_retains_honest_lifecycle_artifact(self):
        import json
        spec = importlib.util.spec_from_file_location('windows_builder_failure', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        work = self.root/'failed-build'
        def failed_constructor(source, target):
            (target/'evidence').mkdir(parents=True)
            raise RuntimeError('Synthetic environment setup failure')
        with patch.object(module, 'Build', side_effect=failed_constructor), \
                patch.object(module.sys, 'argv', ['builder','--source',str(self.root),'--work',str(work)]):
            with self.assertRaises(RuntimeError):
                module.main()
        lifecycle = json.loads((work/'evidence/build-lifecycle.json').read_text())
        self.assertEqual(lifecycle['state'], 'failed')
        self.assertEqual(lifecycle['stage'], 'constructor')
        self.assertIsNone(lifecycle['stage_processes_exited'])
        self.assertNotIn('runtime_clear', lifecycle)

    def test_build_guard_stops_at_reserve_peak_and_watchdog(self):
        spec = importlib.util.spec_from_file_location('windows_builder', engine._ROOT/'scripts/v1-engine-windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        run = module.Build.__new__(module.Build)
        run.work, run.free, run.start = self.root, 14*module.GIB, time.monotonic()
        for free in (module.RESERVE, run.free-module.PEAK-1):
            with patch.object(module.shutil, 'disk_usage', return_value=type('Usage',(),{'free':free})()):
                with self.assertRaises(RuntimeError):
                    run.guard()
        run.start -= 7201
        with patch.object(module.shutil, 'disk_usage', return_value=type('Usage',(),{'free':run.free})()):
            with self.assertRaises(RuntimeError):
                run.guard()
