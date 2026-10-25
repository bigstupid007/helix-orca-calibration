import hashlib
from pathlib import Path
import tempfile
import unittest

from integration.v1_contract import ContractError, digest
from integration.v1_deployment import (authorized, require_native_channel,
    runtime_fingerprint, runtime_manifest, runtime_manifest_fingerprint)
from integration.v1_runtime import atomic_json


class DeploymentTests(unittest.TestCase):
    def test_installed_manifest_binds_complete_immutable_package(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); root=base/'package'; (root/'scripts').mkdir(parents=True); (root/'integration').mkdir()
            entry=root/'scripts/v1-runtime.py'; entry.write_bytes(b'# installed entry\n')
            dependency=root/'integration/v1_jobs.py'; dependency.write_bytes(b'# installed dependency\n')
            files=[]
            for path in (entry,dependency):
                files.append(dict(path=path.relative_to(root).as_posix(),size=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            manifest=dict(schema='helix-orca-v1-runtime-manifest/v1',candidate_sha256='a'*64,files=files)
            atomic_json(root/'runtime-manifest.json',manifest)
            self.assertEqual(runtime_manifest(entry),manifest)
            self.assertEqual(runtime_manifest_fingerprint(entry),digest(manifest))
            fingerprint=runtime_fingerprint(entry)
            config={'owned_jobs':{'actions_enabled':True}}
            approval=dict(schema='helix-orca-v1-local-deployment/v2',approved=True,native_start_only=True,
                approval_reference='Synthetic installed package gate',config_sha256=digest(config),
                runtime_sha256=fingerprint,package_manifest_sha256=digest(manifest))
            path=base/'approval.json'; atomic_json(path,approval)
            self.assertTrue(authorized(path,config,entry))
            dependency.write_bytes(b'# changed installed dependency\n')
            with self.assertRaises(ContractError): runtime_fingerprint(entry)
            dependency.write_bytes(b'# installed dependency\n')
            (root/'unlisted.py').write_bytes(b'# ambient code\n')
            with self.assertRaises(ContractError): runtime_fingerprint(entry)

    def test_manifest_rejects_unsafe_duplicate_or_unlisted_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'scripts').mkdir(); entry=root/'scripts/v1-runtime.py'; entry.write_bytes(b'x')
            item=dict(path='scripts/v1-runtime.py',size=1,sha256=hashlib.sha256(b'x').hexdigest())
            for files in ([dict(item,path='../escape')], [item,item], [dict(item,path='other.py')]):
                atomic_json(root/'runtime-manifest.json',dict(schema='helix-orca-v1-runtime-manifest/v1',candidate_sha256='a'*64,files=files))
                with self.assertRaises(ContractError): runtime_manifest(entry)

    def test_explicit_local_gate_binds_runtime_configuration_and_separate_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'scripts').mkdir(); entry=root/'scripts/runtime.py'; entry.write_text('# owned test runtime\n')
            config={'owned_jobs':{'actions_enabled':True}}
            self.assertFalse(authorized(None,config,entry))
            record=dict(schema='helix-orca-v1-local-deployment/v1',approved=True,native_start_only=True,
                approval_reference='Synthetic gate test only, no physical authority',config_sha256=digest(config),
                runtime_sha256=runtime_fingerprint(entry))
            path=root/'approval.json'; atomic_json(path,record)
            self.assertTrue(authorized(path,config,entry))
            (root/'integration').mkdir(); dependency=root/'integration/v1_runtime.py'
            dependency.write_text('# changed runtime dependency\n')
            with self.assertRaises(ContractError): authorized(path,config,entry)
            dependency.unlink()
            for changed in (dict(record,approved=False),dict(record,native_start_only=False),dict(record,approval_reference=''),dict(record,config_sha256='0'*64),dict(record,runtime_sha256='0'*64),dict(record,unknown=True)):
                atomic_json(path,changed)
                with self.assertRaises(ContractError): authorized(path,config,entry)
            atomic_json(path,record)
            with self.assertRaises(ContractError): authorized(path,{},entry)
            entry.write_text('# different runtime\n')
            with self.assertRaises(ContractError): authorized(path,config,entry)

    def test_native_channel_must_be_explicit_and_same_pinned_target(self):
        target=dict(origin='http://192.168.1.2:7125',expected_host='192.168.1.2',expected_version='test-pin')
        config=dict(moonraker=target,owned_jobs=dict(target))
        require_native_channel(config,True)
        with self.assertRaises(ContractError): require_native_channel(config,False)
        for key in target:
            changed=dict(config,owned_jobs=dict(target,**{key:'different'}))
            with self.assertRaises(ContractError): require_native_channel(changed,True)
