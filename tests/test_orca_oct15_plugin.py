import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import test_plugin


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts/orca-oct15-plugin.py"
spec = importlib.util.spec_from_file_location("oct15_plugin", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class October15PluginTests(unittest.TestCase):
    def test_accepted_plugin_bytes_are_unchanged_and_fail_closed(self):
        value = (ROOT / "plugin/helix_calibration.py").read_bytes()
        self.assertEqual(hashlib.sha256(value).hexdigest(), adapter.BASE_SHA256)
        source = adapter.generate()
        self.assertIn('# version = "0.4.1"', source)
        self.assertIn('("2.5.0-dev", "6a7763f0")', source)
        self.assertNotEqual(hashlib.sha256(source.encode()).hexdigest(), adapter.BASE_SHA256)

    def test_generated_plugin_accepts_only_both_qualified_builds(self):
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary) / "helix_calibration.py"
            generated.write_text(adapter.generate(), encoding="utf-8")
            previous = test_plugin.PLUGIN_PATH
            test_plugin.PLUGIN_PATH = generated
            try:
                plugin, _ = test_plugin.load_plugin()
            finally:
                test_plugin.PLUGIN_PATH = previous
        bundle = test_plugin.FakeBundle(
            values={"nozzle_diameter": "0.4", "nozzle_temperature": "217"},
            names=["Original PLA"],
        )
        bundle.filaments = test_plugin.FakeCollection(
            test_plugin.FakePreset("Original PLA", values={"nozzle_temperature": "220"}),
            test_plugin.FakePreset("Original PLA", dirty=True, values={"nozzle_temperature": "217"}),
        )
        for build in ("210bc927", "6a7763f0"):
            with self.subTest(build=build):
                target = plugin.capture_temperature_target(test_plugin.FakeHost(bundle, build=build))
                self.assertEqual(target["runtime"]["build"], build)
                self.assertEqual(target["effective_temperature"], 217)
        with self.assertRaises(ValueError):
            plugin.capture_temperature_target(test_plugin.FakeHost(bundle, build="other"))


if __name__ == "__main__":
    unittest.main()
