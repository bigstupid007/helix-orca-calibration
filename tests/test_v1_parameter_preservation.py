"""Focused negative checks for retained parameter-proof preservation."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "v1_parameter_preservation_test", ROOT / "scripts/v1-parameter-preservation.py")
preserve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preserve)


class ParameterPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.operator, cls.parity = preserve.verify_immutable_blobs(ROOT)

    def copy(self, destination, paths):
        for relative in paths:
            source = ROOT / relative
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    def boundary_copy(self, destination):
        paths, _ = preserve.current_equivalence_paths(self.report)
        self.copy(destination, [*paths, "scripts/v1-windows-parameter-operator.cjs"])

    def test_accepted_parameter_proof_remains_historical_after_beta12_amendment(self):
        self.assertNotEqual(
            preserve.sha(ROOT / "integration/v1_engine.py"),
            self.report["sources"]["integration/v1_engine.py"],
        )
        # The Founder amendment deliberately changes the native controls and
        # wire boundary. Its replacement inventory is hash-bound separately;
        # the accepted beta.9 blobs remain immutable and are never relabelled
        # as beta.12 or current-Orca build qualification.
        self.assertNotIn(
            "integration/v1-native/ui/orcacal__v1_cancel_confirm.xml",
            preserve.AMENDMENT_NATIVE_REMOVED,
        )
        self.assertEqual(
            preserve.sha(ROOT / "integration/v1-native/ui/orcacal__v1_cancel_confirm.xml"),
            self.report["sources"]["integration/v1-native/ui/orcacal__v1_cancel_confirm.xml"],
        )
        self.assertIn(
            "integration/v1-native/ui/orcacal__v1_warning.xml",
            preserve.AMENDMENT_NATIVE_SHA256,
        )
        preserve.verify_current_equivalence(ROOT, self.report)
        preserve.verify(ROOT)

    def test_any_accepted_blob_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.copy(root, preserve.ACCEPTED_BLOBS)
            path = root / preserve.EVIDENCE / "operator.json"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Accepted proof blob changed"):
                preserve.verify_immutable_blobs(root)

    def test_accepted_source_manifest_change_is_rejected(self):
        changed = copy.deepcopy(self.report)
        changed["sources"]["integration/v1_contract.py"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Accepted source manifest changed"):
            preserve.verify_source_manifest(changed)

    def test_changed_contract_transport_runtime_routing_or_operator_is_rejected(self):
        targets = (
            "integration/v1_contract.py", "integration/v1_transport.py",
            "integration/v1_runtime.py", "integration/v1_routing.py",
            "scripts/v1-windows-parameter-operator.cjs",
        )
        for relative in targets:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self.boundary_copy(root)
                path = root / relative
                path.write_bytes(path.read_bytes() + b"#changed\n")
                with self.assertRaisesRegex(ValueError, "changed"):
                    preserve.verify_current_equivalence(root, self.report)

    def test_native_ui_add_remove_or_change_is_rejected(self):
        for mode in ("add", "remove", "change"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self.boundary_copy(root)
                target = root / "integration/v1-native/controls.lua"
                if mode == "add":
                    (target.parent / "unexpected.lua").write_text("return {}\n")
                elif mode == "remove":
                    target.unlink()
                else:
                    target.write_bytes(target.read_bytes() + b"-- changed\n")
                with self.assertRaisesRegex(ValueError, "native UI/catalog inventory changed|boundary changed"):
                    preserve.verify_current_equivalence(root, self.report)

    def test_old_generator_dispositions_are_scoped_to_accepted_blobs(self):
        self.assertIn("integration/v1_engine.py", preserve.EXCLUDED_GENERATOR_SOURCES)
        paths, _ = preserve.current_equivalence_paths(self.report)
        self.assertTrue(set(paths).isdisjoint(preserve.EXCLUDED_GENERATOR_SOURCES))
        proofs = {item["kind"]: item for item in self.operator["proofs"]}
        self.assertEqual(proofs["temperature"]["phase"], "blocked")
        self.assertEqual(proofs["flow_ratio_yolo"]["phase"], "review")
        preserve.verify_accepted_semantics(self.report, self.operator, self.parity)


if __name__ == "__main__":
    unittest.main()
