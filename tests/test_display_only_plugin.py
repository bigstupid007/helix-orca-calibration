import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integration" / "helix-orca-display"
SOURCE = PLUGIN / "main.lua"
VIEW = PLUGIN / "ui" / "helix-orca-display__receipt.xml"


class DisplayOnlyPluginTests(unittest.TestCase):
    def test_manifest_is_permissionless_overlay_only_beta9_plugin(self):
        manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "helix-orca-display")
        self.assertEqual(manifest["helix_version"], ">=1.1.0-beta.9")
        self.assertEqual(manifest["permissions"], [])
        self.assertEqual(manifest["widgets"], [])
        self.assertEqual(manifest["settings"], [])

    def test_uses_one_unique_agent_event_and_no_official_bridge_events(self):
        source = SOURCE.read_text(encoding="utf-8")
        handlers = re.findall(r"helix\.moonraker\.on_agent_event\(([^,]+),", source)
        self.assertEqual(handlers, ["EVENT_NAME"])
        self.assertEqual(source.count('"helix_orca_display.available.v1"'), 1)
        self.assertNotIn("helixcal.available", source)
        self.assertNotIn("helixcal.cancel", source)

    def test_forbidden_capabilities_are_absent(self):
        source = SOURCE.read_text(encoding="utf-8")
        manifest = (PLUGIN / "manifest.json").read_text(encoding="utf-8")
        for forbidden in (
            "helix.http",
            "helix.storage",
            "helix.printer",
            "helix.gcode",
            "helix.moonraker.call",
            "helix.moonraker.query",
            "helix.moonraker.subscribe",
            "printer.print",
            "job_queue",
            "gcode.script",
            "firmware_restart",
        ):
            self.assertNotIn(forbidden, source)
        for permission in ("http", "storage", "moonraker_write", "gcode"):
            self.assertNotIn(f'"{permission}"', manifest)

    def test_validation_covers_the_exact_display_contract_before_mutation(self):
        source = SOURCE.read_text(encoding="utf-8")
        validate_body = source[source.index("local function validate"):source.index("local function on_overlay_closed")]
        show_body = source[source.index("local function show_receipt"):source.index("helix.moonraker.on_agent_event")]

        for marker in (
            'data.schema ~= SCHEMA',
            'data.display_only ~= true',
            'exact_lower_hex(data.request_id, 32)',
            'exact_lower_hex(data.file_sha256, 64)',
            'valid_filename(data.file)',
            'data.file_bytes ~= math.floor(data.file_bytes)',
            'data.file_bytes < 1',
            'data.file_bytes > MAX_FILE_BYTES',
            'bounded_text(data.printer)',
            'bounded_text(data.filament)',
            'bounded_text(data.process)',
            'data.nozzle_mm < 0.05',
            'data.nozzle_mm > 2',
            'finite_number(data.current_temperature_c)',
            'data.current_temperature_c < 0',
            'data.current_temperature_c > 500',
            'exact_temperatures(data.temperatures)',
            'key_count ~= 12',
            'not PAYLOAD_KEYS[key]',
        ):
            self.assertIn(marker, validate_body)
        self.assertIn('value:match("^[0-9a-f]+$")', source)
        self.assertIn('value:match("%.gcode$")', source)
        self.assertIn("valid_filename(data.file)", validate_body)
        self.assertNotIn("uploaded_filename", source)
        self.assertIn('value:find("/", 1, true) == nil', source)
        self.assertIn('value:find("\\\\", 1, true) == nil', source)
        self.assertIn('value:find("..", 1, true) == nil', source)
        self.assertIn('value:find("%c") == nil', source)
        self.assertIn("local MAX_FILE_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("local MAX_CONTEXT_TEXT = 128", source)
        self.assertIn("local TEMPERATURES = {230, 225, 220, 215, 210, 205, 200, 195, 190}", source)
        self.assertNotIn(":set(", validate_body)
        self.assertNotIn("helix.ui.overlay", validate_body)
        self.assertIn("receipt_line:set", show_body)
        self.assertIn("helix.ui.overlay", show_body)

    def test_overlay_shows_receipt_context_file_and_only_dismiss_action(self):
        root = ET.parse(VIEW).getroot()
        view = next(root.iter("view"))
        self.assertEqual(view.attrib.get("extends"), "overlay_panel")
        content = next(child for child in view if child.tag == "lv_obj")
        self.assertEqual(content.attrib.get("width"), "100%")
        self.assertEqual(content.attrib.get("flex_grow"), "1")
        self.assertEqual(content.attrib.get("scrollable"), "true")

        text = {node.attrib["text"] for node in root.iter() if "text" in node.attrib}
        self.assertTrue({
            "Display-only request",
            "No print started by this request",
            "Received · not printed · not applied",
            "Calibration context",
            "Transferred file",
            "Dismiss",
        }.issubset(text))
        subjects = {node.attrib["bind_text"] for node in root.iter() if "bind_text" in node.attrib}
        self.assertTrue({
            "helix-orca-display__receipt_line",
            "helix-orca-display__printer_line",
            "helix-orca-display__filament_line",
            "helix-orca-display__process_line",
            "helix-orca-display__effective_line",
            "helix-orca-display__file_line",
            "helix-orca-display__hash_line",
            "helix-orca-display__temperatures_line",
        }.issubset(subjects))
        actions = [node.attrib["user_data"] for node in root.iter("event_cb")]
        self.assertEqual(actions, ["helix-orca-display__dismiss"])
        source = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'helix\.ui\.on\("([^"]+)"', source), ["dismiss"])
        self.assertIn("overlay_handle.close()", source)
        self.assertIn('effective_line:set("Original effective: "', source)


if __name__ == "__main__":
    unittest.main()
