"""Dependency checkpoint trust, closed inventories and failure atomicity."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from integration import v1_windows_dependencies as d


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class DependencyBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.prefix=self.root/'prefix';self.downloads=self.root/'downloads';self.bundle=self.root/'deps.zip'
        (self.prefix/'usr/local/lib').mkdir(parents=True)
        (self.prefix/'usr/local/empty').mkdir()
        (self.prefix/'usr/local/lib/library.lib').write_bytes(b'actual build output\0'*40)
        self.downloads.mkdir()
        (self.downloads/'upstream.tar.gz').write_bytes(b'archive bytes\x00\xff'*30)
        (self.downloads/'otherwise-unused-source.zip').write_bytes(b'preserve ALL downloads')
        tools={name:dict(size=10,sha256=hashlib.sha256(name.encode()).hexdigest()) for name in d.TOOLS}
        self.contract=dict(schema=d.CONTRACT_SCHEMA,source_commit=d.ORCA_SOURCE,
            submodules=[' '+'1'*40+' deps/example'],dependencies_lock_sha256='2'*64,
            builder_sha256='3'*64,workflow_sha256='4'*64,module_sha256=sha(d.__file__),
            toolchain=tools,environment=dict(CMAKE_BUILD_PARALLEL_LEVEL='2',_CL_='/MP1',
                DEP_PYTHON_HOST='C:/host/python.exe',actual_deps_configure_argv='["cmake","-G","Ninja"]'),
            prefix=str(self.prefix),downloads=str(self.downloads))
        self.publisher=dict(schema='helix-orca-v1-windows-builder/v1',repository='bigstupid007/helix-orca-calibration',
            workflow='.github/workflows/v1-windows-engine.yml',application_commit='5'*40,run_id='123',run_attempt='1',
            runner_image='windows-2022',image_version='20261018.1',toolchain=copy.deepcopy(tools),
            run_url='https://github.com/bigstupid007/helix-orca-calibration/actions/runs/123')
        self.calls=0
    def guard(self):self.calls+=1
    def create(self):return d.create_bundle(self.bundle,self.prefix,self.downloads,self.contract,self.publisher,self.guard)
    def remove_roots(self):shutil.rmtree(self.prefix);shutil.rmtree(self.downloads)
    def restore(self,path=None,expected=None,contract=None,publisher=None,guard=None):
        path=path or self.bundle
        return d.restore_bundle(path,expected or sha(path),self.prefix,self.downloads,
            contract or self.contract,publisher or self.publisher,guard or self.guard)
    def no_staging(self):self.assertEqual(list(self.root.glob('.dependency-*')),[])
    def rewrite(self,transform):
        with zipfile.ZipFile(self.bundle) as source:
            entries=[(item,source.read(item)) for item in source.infolist()]
        path=self.root/'changed.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(path,'w') as output:
                for info,raw in transform(entries):output.writestr(info,raw)
        return path

    def test_roundtrip_exact_closed_inventory_and_original_producer(self):
        before=d._inventory(dict(prefix=self.prefix,downloads=self.downloads),self.guard)
        receipt=self.create();self.assertFalse(receipt['qualified']);self.assertFalse(receipt['restored'])
        self.assertEqual(receipt['sha256'],sha(self.bundle));self.assertGreater(self.calls,20)
        with zipfile.ZipFile(self.bundle) as archive:
            self.assertIn('downloads/otherwise-unused-source.zip',archive.namelist())
            manifest=json.loads(archive.read(d.MANIFEST));self.assertIn('prefix/usr/local/empty',manifest['directories'])
        self.remove_roots();restored=self.restore()
        self.assertFalse(restored['qualified']);self.assertTrue(restored['restored'])
        self.assertEqual(restored['publisher'],self.publisher)
        self.assertEqual(before,d._inventory(dict(prefix=self.prefix,downloads=self.downloads),self.guard));self.no_staging()

    def test_external_pin_required_and_wrong_pin_never_promotes(self):
        self.create();self.remove_roots()
        for pin in ('','ABC','0'*64):
            with self.subTest(pin=pin),self.assertRaises(d.BundleError):
                d.restore_bundle(self.bundle,pin,self.prefix,self.downloads,self.contract,self.publisher,self.guard)
            self.assertFalse(self.prefix.exists());self.assertFalse(self.downloads.exists());self.no_staging()

    def test_exact_producer_and_recipe_no_fallback(self):
        self.create();self.remove_roots()
        for key,value in [('application_commit','6'*40),('run_attempt','2'),('image_version','different')]:
            publisher=copy.deepcopy(self.publisher);publisher[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(d.BundleError,'publisher_mismatch'):
                self.restore(publisher=publisher)
        for key,value in [('dependencies_lock_sha256','7'*64),('builder_sha256','8'*64),
                ('workflow_sha256','9'*64),('environment',{'_CL_':'/MP2'}),('submodules',[' '+'9'*40+' deps/example'])]:
            contract=copy.deepcopy(self.contract);contract[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(d.BundleError,'contract_mismatch'):
                self.restore(contract=contract)
        self.assertFalse(self.prefix.exists());self.no_staging()

    def test_module_source_and_fixed_paths_are_mandatory(self):
        for key,value in [('module_sha256','0'*64),('prefix',str(self.root/'other')),
                ('source_commit','1'*40),('submodules',[{}])]:
            contract=copy.deepcopy(self.contract);contract[key]=value
            with self.subTest(key=key),self.assertRaises(d.BundleError):
                d.create_bundle(self.bundle,self.prefix,self.downloads,contract,self.publisher,self.guard)
        self.assertFalse(self.bundle.exists());self.no_staging()

    def test_symlink_and_case_collision_sources_refused(self):
        link=self.prefix/'linked';link.symlink_to(self.downloads,target_is_directory=True)
        with self.assertRaises(d.BundleError):self.create()
        link.unlink();(self.downloads/'CASE').write_bytes(b'a');(self.downloads/'case').write_bytes(b'b')
        with self.assertRaises(d.BundleError):self.create()
        self.assertFalse(self.bundle.exists());self.no_staging()

    def test_archive_escape_unknown_case_duplicate_and_symlink_refused(self):
        self.create();self.remove_roots()
        def add(name,mode=None):
            def transform(entries):
                info=zipfile.ZipInfo(name)
                if mode is not None:info.create_system=3;info.external_attr=mode<<16
                return entries+[(info,b'bad')]
            return transform
        transforms=[add('prefix/../escape'),add('other/file'),add('prefix/evil:ads'),
            add('downloads/UPSTREAM.TAR.GZ'),add('prefix/link',stat.S_IFLNK|0o777)]
        for transform in transforms:
            with self.subTest(transform=transform),self.assertRaises(d.BundleError):self.restore(path=self.rewrite(transform))
            self.assertFalse(self.prefix.exists());self.no_staging()

    def test_payload_tampering_and_unlisted_files_refused_even_with_matching_zip_pin(self):
        self.create();self.remove_roots()
        def corrupt(entries):
            return [(info,b'X'*len(raw) if info.filename.startswith('downloads/') else raw) for info,raw in entries]
        with self.assertRaisesRegex(d.BundleError,'digest_mismatch'):self.restore(path=self.rewrite(corrupt))
        with self.assertRaisesRegex(d.BundleError,'closed_archive_inventory'):
            self.restore(path=self.rewrite(lambda entries:entries+[(zipfile.ZipInfo('downloads/unlisted.zip'),b'not listed')]))
        self.assertFalse(self.prefix.exists());self.no_staging()

    def test_manifest_duplicate_keys_and_false_qualification_refused(self):
        self.create();self.remove_roots()
        for replacement in ('duplicate','qualified'):
            def change(entries):
                output=[]
                for info,raw in entries:
                    if info.filename==d.MANIFEST:
                        if replacement=='duplicate':raw=raw[:-1]+b',"qualified":false}'
                        else:
                            data=json.loads(raw);data['qualified']=True;raw=json.dumps(data).encode()
                    output.append((info,raw))
                return output
            with self.subTest(replacement=replacement),self.assertRaises(d.BundleError):self.restore(path=self.rewrite(change))
        self.no_staging()

    def test_no_overwrite_archive_or_destination(self):
        self.bundle.write_bytes(b'existing archive')
        with self.assertRaises(d.BundleError):self.create()
        self.assertEqual(self.bundle.read_bytes(),b'existing archive');self.bundle.unlink();self.create()
        with self.assertRaises(d.BundleError):self.restore()
        self.assertEqual((self.prefix/'usr/local/lib/library.lib').read_bytes(),b'actual build output\0'*40)

    def test_closed_source_change_during_archive_refused(self):
        changed=False
        def guard():
            nonlocal changed
            if not changed and list(self.root.glob('.dependency-bundle-*')):
                changed=True;(self.downloads/'appeared.zip').write_bytes(b'late')
        with self.assertRaisesRegex(d.BundleError,'source_inventory_changed'):
            d.create_bundle(self.bundle,self.prefix,self.downloads,self.contract,self.publisher,guard)
        self.assertTrue(changed);self.assertFalse(self.bundle.exists());self.no_staging()

    def test_guard_failure_after_first_promotion_rolls_back_own_roots(self):
        self.create();self.remove_roots()
        def guard():
            if self.prefix.exists():raise RuntimeError('budget cancelled')
        with self.assertRaisesRegex(RuntimeError,'budget cancelled'):self.restore(guard=guard)
        self.assertFalse(self.prefix.exists());self.assertFalse(self.downloads.exists());self.no_staging()

    def test_foreign_destination_race_preserved_and_first_promotion_rolled_back(self):
        self.create();self.remove_roots()
        def guard():
            if self.prefix.exists() and not self.downloads.exists():
                self.downloads.mkdir();(self.downloads/'foreign').write_bytes(b'keep')
        with self.assertRaises(d.BundleError):self.restore(guard=guard)
        self.assertFalse(self.prefix.exists());self.assertEqual((self.downloads/'foreign').read_bytes(),b'keep');self.no_staging()

    def test_bounds_checked_on_create_and_restore(self):
        for key,value in [('MAX_FILES',1),('MAX_RAW_BYTES',10),('MAX_ZIP_BYTES',32)]:
            with self.subTest(key=key),patch.object(d,key,value),self.assertRaises(d.BundleError):self.create()
            self.assertFalse(self.bundle.exists());self.no_staging()
        self.create();self.remove_roots()
        for key,value in [('MAX_FILES',1),('MAX_RAW_BYTES',10),('MAX_ZIP_BYTES',32)]:
            with self.subTest(key=key),patch.object(d,key,value),self.assertRaises(d.BundleError):self.restore()
            self.assertFalse(self.prefix.exists());self.assertFalse(self.downloads.exists());self.no_staging()

    def test_walk_error_is_not_silently_omitted(self):
        def walk(*args,**kwargs):
            kwargs['onerror'](PermissionError('unreadable dependency'))
            return iter(())
        with patch.object(d.os,'walk',walk),self.assertRaises(PermissionError):self.create()
        self.assertFalse(self.bundle.exists())


if __name__=='__main__':unittest.main()
