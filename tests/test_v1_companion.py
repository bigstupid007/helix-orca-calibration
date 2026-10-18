import importlib.util
from pathlib import Path
import tempfile
import types
import json
import unittest

import test_plugin

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("v1_companion_builder", ROOT/"scripts/v1-companion.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CompanionTests(unittest.TestCase):
    def load(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"helix_calibration.py"
            path.write_text(builder.generate())
            previous = test_plugin.PLUGIN_PATH
            test_plugin.PLUGIN_PATH = path
            try:
                return test_plugin.load_plugin()
            finally:
                test_plugin.PLUGIN_PATH = previous

    def test_actual_callback_captures_saved_edited_effective_to_host_storage(self):
        plugin, orca = self.load()
        bundle = test_plugin.FakeBundle(values={"nozzle_diameter":"0.4", "nozzle_temperature":"215", "gcode_flavor":"klipper"}, names=["Original PLA"])
        bundle.filaments = test_plugin.FakeCollection(
            test_plugin.FakePreset("Original PLA", values={"nozzle_temperature":"220"}),
            test_plugin.FakePreset("Original PLA", dirty=True, values={"nozzle_temperature":"217"}))
        bundle.printers = test_plugin.FakeCollection(test_plugin.FakePreset("Printer",values={"nozzle_diameter":"0.4"}), test_plugin.FakePreset("Printer",values={"nozzle_diameter":"0.4"}))
        bundle.prints = test_plugin.FakeCollection(test_plugin.FakePreset("Process",values={"layer_height":"0.2"}), test_plugin.FakePreset("Process",values={"layer_height":"0.2"}))
        host = test_plugin.FakeHost(bundle, build="6a7763f0")
        host.ui = orca.host.ui
        with tempfile.TemporaryDirectory() as root:
            host.plugin = types.SimpleNamespace(storage=lambda: root)
            orca.host = host
            panel = plugin.V1CalibrationPanel()
            panel.execute()
            panel.on_message({"command":"ready"})
            self.assertIsNone(panel.error)
            self.assertEqual(panel.context["filament"]["saved"]["config"]["nozzle_temperature"], "220")
            self.assertEqual(panel.context["filament"]["edited"]["config"]["nozzle_temperature"], "217")
            self.assertEqual(panel.context["effective"]["nozzle_temperature"], "215")
            first = panel.context["origin_id"]
            panel.on_message({"command":"refresh"})
            self.assertEqual(panel.context["origin_id"], first)
            self.assertTrue((Path(root)/"v1/context.json").is_file())
            self.assertFalse((Path(root)/"v1/result.json").exists())

    def test_generator_is_self_contained_and_accepted_capabilities_survive(self):
        plugin, orca = self.load()
        source = builder.generate()
        self.assertNotIn("from integration", source)
        self.assertIn("V1CalibrationPanel", source)
        self.assertTrue(hasattr(plugin, "TemperatureRoundTripPanel"))
        self.assertNotIn("subprocess", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("import threading", source)

    def test_result_commits_before_receipt_and_wrong_origin_or_conflict_rejects(self):
        from test_v1_runtime import context, request, prepared
        plugin, _ = self.load()
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root);(directory/"origins").mkdir()
            original=context()
            plugin.v1_write(directory/"origins"/(original["origin_id"]+".json"),original)
            req=request(dict(request_id="2"*32,origin_id=original["origin_id"],context_sha256=plugin.digest(original),created_at=100,expires_at=3700))
            prep=prepared(req);prep["artifact"]=dict(name="fixture.gcode",size=1,sha256="a"*64);prep["parity"].update(qualified=True,report_sha256="b"*64)
            proof=dict(job_id="owned",file_sha256="a"*64,print_state="complete",history_state="completed",history_job_id="owned",history_file_sha256="a"*64)
            result=dict(schema="helix-orca-v1-result/v1",request_id=req["request_id"],origin_id=req["origin_id"],context_sha256=req["context_sha256"],prepared_sha256=plugin.digest(prep),job_id="owned",completion_sha256=plugin.digest(proof),setting="nozzle_temperature",value=220,not_applied=True)
            inbox=dict(request=req,prepared=prep,completion=proof,result=result)
            plugin.v1_write(directory/"inbox.json",inbox)
            committed=plugin.v1_commit_inbox(directory)
            self.assertEqual(committed["original"],original)
            receipt=json.loads((directory/"receipt.json").read_text())
            self.assertEqual(receipt["result_sha256"],plugin.digest(result))
            self.assertEqual(plugin.v1_commit_inbox(directory),committed)
            inbox["result"]=dict(result,value=225)
            plugin.v1_write(directory/"inbox.json",inbox)
            with self.assertRaises(ValueError):
                plugin.v1_commit_inbox(directory)
            self.assertEqual(json.loads((directory/"receipt.json").read_text()),receipt)


if __name__ == "__main__":
    unittest.main()
