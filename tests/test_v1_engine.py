"""Fail-closed source/runtime boundaries for the proposed native backend."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("v1_engine", Path(__file__).resolve().parents[1] / "integration/v1_engine.py")
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


class NativeBoundaryTests(unittest.TestCase):
    def test_source_inventory_cannot_qualify_missing_or_substituted_bytes(self):
        with self.assertRaises(engine.NativeSourceError):
            engine.verify_source_bytes({})
        sources = {name: b"unreviewed replacement" for name in engine.SOURCE_HASHES}
        with self.assertRaisesRegex(engine.NativeSourceError, "source mismatch"):
            engine.verify_source_bytes(sources)

    def test_source_verification_failure_is_not_silently_ignored(self):
        with patch.object(engine.subprocess, "run", side_effect=subprocess.CalledProcessError(128, "git")):
            with self.assertRaises(engine.NativeSourceError):
                engine.audit_git_source("/nonexistent")

    def test_audit_reads_fixed_commit_without_replace_objects(self):
        with patch.object(engine.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"wrong source", b"")) as run:
            with self.assertRaises(engine.NativeSourceError):
                engine.audit_git_source("/tmp")
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertIn("--no-replace-objects", argv)
            self.assertTrue(argv[-1].startswith(engine.ORCA_SOURCE + ":"))
            self.assertTrue(call.kwargs["check"])
            self.assertLessEqual(call.kwargs["timeout"], 20)

    def test_mutating_capability_response_cannot_enable_native_execution(self):
        capabilities = engine.capabilities()
        for capability in capabilities:
            capability["available"] = True
            with self.assertRaises(engine.NativeEngineBlocked):
                engine.require_native_generation(capability["id"])
        self.assertFalse(any(item["available"] for item in engine.capabilities()))

    def test_unknown_mode_cannot_escape_into_native_dispatch(self):
        for value in ("Calib_PA_Line", "../temperature", "temperature; print", None, [], {}):
            with self.assertRaises(engine.NativeEngineBlocked):
                engine.require_native_generation(value)


if __name__ == "__main__":
    unittest.main()
