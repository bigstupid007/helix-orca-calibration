import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "helix-plugin" / "orcacal"
PLUGIN_ID = "orcacal"
OWNED_PREFIX = f"{PLUGIN_ID}__"


class HelixPluginTests(unittest.TestCase):
    def test_manifest_matches_beta4_contract(self):
        manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["id"], PLUGIN_ID)
        self.assertEqual(manifest["name"], "Orca Calibration")
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["helix_version"], ">=1.1.0-beta.4")
        self.assertEqual(manifest["permissions"], [])
        self.assertRegex(manifest["id"], r"^[a-z][a-z0-9-]{1,31}$")

        self.assertEqual(len(manifest["widgets"]), 1)
        widget = manifest["widgets"][0]
        self.assertEqual(widget["id"], "orcacal__tile")
        self.assertEqual(widget["component"], "orcacal__tile")
        self.assertEqual((widget["colspan"], widget["rowspan"]), (3, 2))
        self.assertEqual(widget["icon"], "tune")
        self.assertTrue((PLUGIN / "ui" / f'{widget["component"]}.xml').is_file())

    def test_xml_uses_only_plugin_allowed_elements_and_names(self):
        allowed = {
            "component",
            "view",
            "api",
            "prop",
            "style",
            "event_cb",
            "play_timeline_event",
            "overlay_panel",
            "ui_card",
            "icon",
            "text_heading",
            "text_body",
            "text_muted",
            "text_small",
            "text_xs",
            "text_tiny",
            "plugin_canvas",
        }
        base_fonts = {
            "#font_xs",
            "#font_small",
            "#font_body",
            "#font_body_bold",
            "#font_heading",
            "#font_xl",
            "#font_display",
            "#font_mono",
        }

        for path in sorted((PLUGIN / "ui").glob("*.xml")):
            self.assertTrue(path.stem.startswith(OWNED_PREFIX))
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, "component")
            for element in root.iter():
                tag = element.tag
                self.assertTrue(
                    tag in allowed
                    or tag.startswith("lv_")
                    or tag.startswith("bind_")
                    or tag.startswith("remove_style"),
                    f"{path}: <{tag}> is not available to beta.4 plugins",
                )
                if tag == "view" and "extends" in element.attrib:
                    extended = element.attrib["extends"]
                    self.assertTrue(extended in allowed or extended.startswith("lv_"))

                for name, value in element.attrib.items():
                    is_callback = (
                        name in {"callback", "event_cb"}
                        or name.endswith("_callback")
                        or name.endswith("_cb")
                    )
                    if is_callback:
                        self.assertEqual(value, "plugin_event")
                    if name == "user_data":
                        self.assertTrue(value.split(":", 1)[0].startswith(OWNED_PREFIX))
                    if name == "name" and tag not in {"prop", "style"}:
                        self.assertTrue(value.startswith(OWNED_PREFIX))
                    if name == "style_text_font" and value.startswith("#font_"):
                        self.assertIn(value, base_fonts)

    def test_events_are_backed_by_permissionless_lua_handlers(self):
        source = (PLUGIN / "main.lua").read_text(encoding="utf-8")
        handlers = set(re.findall(r'helix\.ui\.on\("([a-z0-9_-]+)"', source))
        targets = set()
        for path in (PLUGIN / "ui").glob("*.xml"):
            for element in ET.parse(path).getroot().iter("event_cb"):
                target = element.attrib["user_data"].split(":", 1)[0]
                targets.add(target.removeprefix(OWNED_PREFIX))

        self.assertEqual(targets, {"open", "select", "start"})
        self.assertTrue(targets.issubset(handlers))
        self.assertIn('helix.ui.overlay("orcacal__wizard")', source)
        self.assertIn('component = "orcacal__temperature"', source)
        self.assertIn("CALIBRATIONS[id]", source)
        self.assertIn("helix.ui.overlay(calibration.component)", source)
        self.assertIn('helix.ui.toast("Calibration request test")', source)
        for forbidden in ("helix.gcode", "helix.moonraker", "helix.http", "helix.storage"):
            self.assertNotIn(forbidden, source)

    def test_wizard_is_a_context_and_calibration_chooser(self):
        root = ET.parse(PLUGIN / "ui" / "orcacal__wizard.xml").getroot()
        text = {element.attrib["text"] for element in root.iter() if "text" in element.attrib}
        self.assertTrue(
            {
                "Voron 2.4 300 · 0.4 mm",
                "Generic PLA - Rapido · Fast Quality",
                "Temperature",
                "230°C",
                "190°C",
            }.issubset(text)
        )

        context_card = next(root.iter("ui_card"))
        self.assertEqual(context_card.attrib.get("style_pad_all"), "#space_sm")
        context_values = [
            element.attrib["text"]
            for element in context_card
            if element.tag in {"text_body", "text_small"}
        ]
        self.assertEqual(
            context_values,
            [
                "CURRENT CONTEXT",
                "Voron 2.4 300 · 0.4 mm",
                "Generic PLA - Rapido · Fast Quality",
            ],
        )
        self.assertNotIn("Start", text)
        self.assertTrue(
            any(
                element.tag == "event_cb"
                and element.attrib.get("user_data") == "orcacal__select:temperature"
                for element in root.iter()
            )
        )

    def test_temperature_detail_preserves_h1_range_and_start_proof(self):
        root = ET.parse(PLUGIN / "ui" / "orcacal__temperature.xml").getroot()
        text = {element.attrib["text"] for element in root.iter() if "text" in element.attrib}
        self.assertTrue(
            {
                "Voron 2.4 300",
                "Generic PLA - Rapido · 0.4 mm",
                "Fast Quality",
                "Temperature range",
                "230°C",
                "190°C",
                "Start",
            }.issubset(text)
        )
        self.assertTrue(
            any(
                element.tag == "icon" and element.attrib.get("src") == "arrow_right"
                for element in root.iter()
            )
        )
        self.assertTrue(
            any(
                element.tag == "event_cb"
                and element.attrib.get("user_data") == "orcacal__start"
                for element in root.iter()
            )
        )

    def test_overlays_use_native_shell_and_own_only_vertical_overflow(self):
        for filename in ("orcacal__wizard.xml", "orcacal__temperature.xml"):
            root = ET.parse(PLUGIN / "ui" / filename).getroot()
            view = next(root.iter("view"))
            self.assertEqual(view.attrib.get("extends"), "overlay_panel")
            self.assertNotIn("back_button_callback", view.attrib)
            content = next(child for child in view if child.tag == "lv_obj")
            self.assertEqual(content.attrib.get("width"), "100%")
            self.assertEqual(content.attrib.get("flex_grow"), "1")
            self.assertEqual(content.attrib.get("scrollable"), "true")

    def test_visible_ui_does_not_claim_unimplemented_capabilities(self):
        visible_text = "\n".join(
            element.attrib["text"]
            for path in sorted((PLUGIN / "ui").glob("*.xml"))
            for element in ET.parse(path).getroot().iter()
            if "text" in element.attrib
        )
        for forbidden in (
            "Generate",
            "Run",
            "Result",
            "Apply to Orca",
            "Moonraker",
            "G-code",
            "Workspace",
        ):
            self.assertNotIn(forbidden, visible_text)


if __name__ == "__main__":
    unittest.main()
