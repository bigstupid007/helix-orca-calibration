import importlib.util
import datetime
import json
import pathlib
import sys
import tempfile
import tomllib
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin" / "helix_calibration.py"


class FakeWindow:
    def __init__(self):
        self.open = True
        self.posts = []

    def is_open(self):
        return self.open

    def post(self, payload):
        self.posts.append(payload)

    def close(self):
        self.open = False

    def show(self):
        self.open = True


class FakeUI:
    def __init__(self):
        self.windows = []
        self.last_create = None

    def create_window(self, **kwargs):
        self.last_create = kwargs
        window = FakeWindow()
        self.windows.append(window)
        return window

    def create_dock_panel(self, **kwargs):
        return self.create_window(**kwargs)


class FakeExecutionResult:
    @staticmethod
    def success(message="", data=""):
        return {"success": True, "message": message, "data": data}

    @staticmethod
    def failure(status, message="", data=""):
        return {"success": False, "status": status, "message": message, "data": data}


def load_plugin():
    fake_orca = types.ModuleType("orca")
    fake_orca.script = types.SimpleNamespace(ScriptPluginCapabilityBase=object)
    fake_orca.base = object
    fake_orca.plugin = lambda cls: cls
    fake_orca.registered_capabilities = []
    fake_orca.register_capability = fake_orca.registered_capabilities.append
    fake_orca.ExecutionResult = FakeExecutionResult
    fake_orca.PluginResult = types.SimpleNamespace(RecoverableError="recoverable")
    fake_orca.host = types.SimpleNamespace(ui=FakeUI())
    sys.modules["orca"] = fake_orca

    spec = importlib.util.spec_from_file_location("helix_calibration_plugin", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, fake_orca


class FakePreset:
    def __init__(
        self,
        name,
        *,
        dirty=False,
        system=False,
        user=False,
        project=False,
        external=False,
        default=False,
        bundle=False,
        values=None,
        failing_keys=None,
    ):
        self.name = name
        self.alias = ""
        self.bundle_id = ""
        self.is_dirty = dirty
        self.is_system = system
        self.is_visible = True
        self.is_compatible = True
        self._is_user = user
        self.is_project_embedded = project
        self.is_external = external
        self.is_default = default
        self._is_bundle = bundle
        self.values = dict(values or {})
        self.failing_keys = set(failing_keys or ())

    def is_user(self):
        return self._is_user

    def is_from_bundle(self):
        return self._is_bundle

    def config_keys(self):
        return list(self.values)

    def config_value(self, key):
        if key in self.failing_keys:
            raise RuntimeError(f"failed {key}")
        return self.values.get(key)


class FakeCollection:
    def __init__(self, selected, edited):
        self._selected = selected
        self._edited = edited

    def selected_preset(self):
        return self._selected

    def edited_preset(self):
        return self._edited


class FakeBundle:
    def __init__(self, values=None, names=None, filament_presets=None):
        self.values = dict(values or {})
        self.printers = FakeCollection(
            FakePreset("Voron 2.4 0.4", system=True),
            FakePreset("Voron 2.4 0.4", dirty=True, system=True),
        )
        self.prints = FakeCollection(
            FakePreset("0.20mm Standard", user=True),
            FakePreset("0.20mm Standard", user=True),
        )
        self.names = list(names or ["PolyLite PLA Black"])
        self.filament_presets = list(
            filament_presets
            or [FakePreset("PolyLite PLA Black", dirty=True, user=True)]
        )

    def full_config_value(self, key):
        return self.values.get(key)

    def full_config_keys(self):
        return list(self.values)

    def current_filament_preset_names(self):
        return list(self.names)

    def current_filament_presets(self):
        return list(self.filament_presets)


class FakeHost:
    def __init__(self, bundle, *, storage_root=None, version="2.5.0-dev", build="210bc927"):
        self.bundle = bundle
        self._model = FakeModel()
        self._plater = FakePlater()
        self._app_info = {
            "version": version,
            "build": build,
            "mode": "editor",
            "language": "en_US",
        }
        self.plugin = types.SimpleNamespace(storage=lambda: storage_root)

    def preset_bundle(self):
        return self.bundle

    def model(self):
        return self._model

    def plater(self):
        return self._plater

    def app_language(self):
        return "en_US"

    def app_info(self):
        return dict(self._app_info)


class FakePlater:
    def is_project_dirty(self):
        return False

    def is_presets_dirty(self):
        return True

    def inside_snapshot_capture(self):
        return False


class FakeModel:
    def id(self):
        return 10

    def object_count(self):
        return 0

    def material_count(self):
        return 0

    def current_plate_index(self):
        return 2

    def is_fdm_support_painted(self):
        return False

    def is_seam_painted(self):
        return False

    def is_mm_painted(self):
        return False

    def is_fuzzy_skin_painted(self):
        return False

    def designer(self):
        return ""

    def design_id(self):
        return ""

    def objects(self):
        return []


class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin, cls.orca = load_plugin()

    def snapshot(self, **kwargs):
        values = {
            "printer_technology": "FFF",
            "nozzle_diameter": "0.4",
            "nozzle_temperature": "215",
        }
        values.update(kwargs.pop("values", {}))
        return self.plugin.build_context(FakeHost(FakeBundle(values=values, **kwargs)))

    def inventory(self, bundle):
        captured_at = datetime.datetime(2026, 9, 22, 12, 34, 56, tzinfo=datetime.timezone.utc)
        return self.plugin.build_context_inventory(FakeHost(bundle), captured_at=captured_at)

    @staticmethod
    def inventory_source(snapshot, namespace):
        return next(
            source
            for source in snapshot["configuration_sources"]
            if source["namespace"] == namespace
        )

    def test_pep_723_metadata_is_complete_and_dependency_free(self):
        source = PLUGIN_PATH.read_text(encoding="utf-8")
        self.assertTrue(source.startswith("# /// script\n"))
        metadata_lines = []
        for line in source.splitlines()[1:]:
            if line == "# ///":
                break
            self.assertTrue(line.startswith("#"))
            metadata_lines.append(line[2:] if line.startswith("# ") else "")
        metadata = tomllib.loads("\n".join(metadata_lines))
        self.assertEqual(">=3.12", metadata["requires-python"])
        plugin = metadata["tool"]["orcaslicer"]["plugin"]
        self.assertEqual("Helix Calibration Context", plugin["name"])
        self.assertEqual("script", plugin["type"])
        self.assertEqual("0.3.0", plugin["version"])
        self.assertNotIn("dependencies", metadata)

    def test_initial_html_escapes_host_text(self):
        markup = self.plugin._render_context_html(
            {"status": "error", "message": "</div><script>alert('x')</script> &", "warnings": []}
        )
        self.assertNotIn("<script>alert", markup)
        self.assertIn("&lt;/div&gt;&lt;script&gt;", markup)
        self.assertIn("&amp;", markup)

    def test_single_filament_reports_saved_and_current_effective_context(self):
        snapshot = self.snapshot()
        self.assertEqual("ok", snapshot["status"])
        self.assertEqual("Voron 2.4 0.4", snapshot["profiles"]["printer"]["selected"]["name"])
        self.assertTrue(snapshot["profiles"]["printer"]["edited"]["dirty"])
        self.assertEqual("0.4 mm", snapshot["extruders"][0]["nozzle_diameter"]["display"])
        self.assertEqual(
            "215 °C",
            snapshot["filaments"][0]["normal_nozzle_temperature"]["display"],
        )
        self.assertIn("current effective", snapshot["provenance"]["settings"])
        self.assertIn("not claimed to be saved", snapshot["provenance"]["settings"])

    def test_multiple_filaments_preserve_slot_order(self):
        snapshot = self.snapshot(
            values={"nozzle_diameter": "0.4;0.6", "nozzle_temperature": "215;245"},
            names=["PLA Black", "PETG Blue"],
            filament_presets=[
                FakePreset("PLA Black", user=True),
                FakePreset("PETG Blue", system=True),
            ],
        )
        self.assertEqual(["PLA Black", "PETG Blue"], [f["selected_name"] for f in snapshot["filaments"]])
        self.assertEqual([215, 245], [f["normal_nozzle_temperature"]["value"] for f in snapshot["filaments"]])
        self.assertEqual([0.4, 0.6], [e["nozzle_diameter"]["value"] for e in snapshot["extruders"]])

    def test_malformed_temperature_is_unavailable_not_partially_substituted(self):
        snapshot = self.snapshot(values={"nozzle_temperature": "215;hot"})
        setting = snapshot["filaments"][0]["normal_nozzle_temperature"]
        self.assertFalse(setting["available"])
        self.assertIn("unsupported value", setting["reason"])

    def test_missing_setting_is_reported(self):
        snapshot = self.snapshot(values={"nozzle_diameter": None})
        setting = snapshot["extruders"][0]["nozzle_diameter"]
        self.assertFalse(setting["available"])
        self.assertIn("absent", setting["reason"])

    def test_filament_count_mismatch_does_not_repeat_values(self):
        snapshot = self.snapshot(
            values={"nozzle_temperature": "215"},
            names=["PLA", "PETG"],
            filament_presets=[FakePreset("PLA", user=True)],
        )
        self.assertTrue(snapshot["filaments"][0]["normal_nozzle_temperature"]["available"])
        self.assertFalse(snapshot["filaments"][1]["normal_nozzle_temperature"]["available"])
        self.assertEqual("Unavailable", snapshot["filaments"][1]["current"]["name"])
        self.assertNotEqual(snapshot["filaments"][1]["selected_name"], snapshot["filaments"][1]["current"]["name"])
        self.assertTrue(any("different counts" in warning for warning in snapshot["warnings"]))

    def test_non_fff_context_is_explicitly_unsupported(self):
        snapshot = self.snapshot(values={"printer_technology": "SLA"})
        self.assertEqual("unsupported", snapshot["status"])
        self.assertIn("SLA", snapshot["message"])

    def test_initial_context_is_embedded_and_refresh_replaces_snapshot(self):
        bundle = FakeBundle(
            values={
                "printer_technology": "FFF",
                "nozzle_diameter": "0.4",
                "nozzle_temperature": "220",
            }
        )
        self.orca.host = FakeHost(bundle)
        self.orca.host.ui = FakeUI()

        capability = self.plugin.HelixCalibrationContext()
        result = capability.execute()
        first_window = capability.window
        self.assertTrue(result["success"])
        self.assertEqual([], first_window.posts)
        initial_html = self.orca.host.ui.last_create["html"]
        self.assertNotIn(self.plugin.INITIAL_CONTENT_MARKER, initial_html)
        self.assertNotIn("Reading current Orca context", initial_html)
        self.assertIn("Voron 2.4 0.4", initial_html)
        self.assertIn("220 °C", initial_html)
        self.assertIn("Unsaved edits present", initial_html)
        self.assertIn("window.orca.onMessage", self.plugin.PAGE)

        bundle.values["nozzle_temperature"] = "215"
        capability.on_message({"command": "refresh"})
        self.assertEqual(215, first_window.posts[-1]["filaments"][0]["normal_nozzle_temperature"]["value"])

        capability.execute()
        self.assertFalse(first_window.is_open())
        self.assertIsNot(first_window, capability.window)

    def test_inventory_enumerates_each_source_and_preserves_raw_values(self):
        start_gcode = "PRINT_START BED={first_layer_bed_temperature[0]}\n; café λ\nG28\n"
        bundle = FakeBundle(values={"machine_start_gcode": start_gcode, "merged_zero": 0})
        bundle.printers = FakeCollection(
            FakePreset(
                "Saved Printer",
                system=True,
                values={"speed": "42", "empty": "", "null_value": None, "false_value": False},
            ),
            FakePreset("Saved Printer", dirty=True, system=True, values={"speed": "43"}),
        )
        bundle.prints = FakeCollection(
            FakePreset("Saved Process", user=True, values={"layer_height": "0.2"}),
            FakePreset("Saved Process", dirty=True, user=True, values={"layer_height": "0.19"}),
        )

        snapshot = self.inventory(bundle)
        saved = self.inventory_source(snapshot, "printer.selected_saved")
        values = {entry["key"]: entry["raw_value"] for entry in saved["entries"]}
        self.assertEqual(4, saved["enumerable_key_count"])
        self.assertEqual("", values["empty"])
        self.assertIsNone(values["null_value"])
        self.assertIs(values["false_value"], False)
        self.assertEqual(3, saved["read_outcome_counts"][self.plugin.READ_SUCCEEDED])
        self.assertEqual(1, saved["read_outcome_counts"][self.plugin.DATA_ABSENT])

        merged = self.inventory_source(snapshot, "preset_bundle.merged_full_config")
        merged_values = {entry["key"]: entry["raw_value"] for entry in merged["entries"]}
        self.assertEqual(start_gcode, merged_values["machine_start_gcode"])
        self.assertEqual(0, merged_values["merged_zero"])
        report = snapshot["gcode_and_template_fields"]
        self.assertIn(self.plugin.READ_SUCCEEDED, report["explicit_fields"]["machine_start_gcode"]["exposure"])
        interpretation = next(item for item in report["template_interpretation_separate_from_raw_values"] if item["key"] == "machine_start_gcode")
        self.assertTrue(interpretation["placeholder_or_expression_markers_present"])
        self.assertIn("PRINT_START", interpretation["line_leading_firmware_macro_candidates"])

    def test_inventory_keeps_saved_edited_and_filament_slot_associations_separate(self):
        bundle = FakeBundle(
            values={"nozzle_temperature": "217;245"},
            names=["PLA", "PETG"],
            filament_presets=[
                FakePreset("PLA", dirty=True, user=True, values={"nozzle_temperature": "217"}),
                FakePreset("PETG", system=True, values={"nozzle_temperature": "245"}),
            ],
        )
        bundle.printers = FakeCollection(
            FakePreset("Printer", values={"nozzle_diameter": "0.4"}),
            FakePreset("Printer", dirty=True, values={"nozzle_diameter": "0.6"}),
        )
        bundle.filaments = FakeCollection(
            FakePreset("PLA", user=True, values={"nozzle_temperature": "215"}),
            FakePreset("PLA", dirty=True, user=True, values={"nozzle_temperature": "217"}),
        )

        snapshot = self.inventory(bundle)
        saved = self.inventory_source(snapshot, "printer.selected_saved")
        edited = self.inventory_source(snapshot, "printer.current_edited")
        self.assertEqual("0.4", saved["entries"][0]["raw_value"])
        self.assertEqual("0.6", edited["entries"][0]["raw_value"])

        slots = snapshot["preset_bundle"]["filaments"]["slots"]
        self.assertEqual(["PLA", "PETG"], [slot["selected_name"]["raw_value"] for slot in slots])
        self.assertEqual("unique_name_match", slots[0]["association"]["collection_edited_mapping"])
        self.assertEqual("not_established_for_this_slot", slots[1]["association"]["collection_edited_mapping"])
        self.assertNotEqual(slots[0]["config_source"], "filament_editor.current_edited")

    def test_inventory_records_absent_values_and_individual_read_failures(self):
        bundle = FakeBundle(values={"present": "yes", "absent": None, "broken": "unread"})
        bundle.failing_keys = {"broken"}

        def failing_value(key):
            if key == "broken":
                raise RuntimeError("synthetic read failure")
            return bundle.values.get(key)

        bundle.full_config_value = failing_value
        snapshot = self.inventory(bundle)
        merged = self.inventory_source(snapshot, "preset_bundle.merged_full_config")
        entries = {entry["key"]: entry for entry in merged["entries"]}
        self.assertEqual(self.plugin.READ_SUCCEEDED, entries["present"]["read_status"])
        self.assertEqual(self.plugin.DATA_ABSENT, entries["absent"]["read_status"])
        self.assertEqual(self.plugin.READ_FAILED, entries["broken"]["read_status"])
        self.assertIn("synthetic read failure", entries["broken"]["reason"])
        self.assertEqual(1, merged["read_outcome_counts"][self.plugin.READ_FAILED])

    def test_inventory_redacts_credentials_and_known_personal_paths_without_hiding_keys(self):
        bundle = FakeBundle(
            values={
                "printhost_apikey": "secret-token",
                "printer_password": "secret-password",
                "post_process": r"C:\\Users\\Chris\\private-script.cmd",
                "print_host": "http://printer.local",
            }
        )
        snapshot = self.inventory(bundle)
        merged = self.inventory_source(snapshot, "preset_bundle.merged_full_config")
        entries = {entry["key"]: entry for entry in merged["entries"]}
        for key in ("printhost_apikey", "printer_password", "post_process"):
            self.assertEqual(self.plugin.REDACTED, entries[key]["read_status"])
            self.assertIsNone(entries[key]["raw_value"])
        self.assertEqual("http://printer.local", entries["print_host"]["raw_value"])
        self.assertEqual(3, merged["read_outcome_counts"][self.plugin.REDACTED])

    def test_inventory_captures_object_and_volume_overrides_without_mesh_or_input_paths(self):
        class Volume:
            name = "Part"

            def id(self): return 301
            def extruder_id(self): return 2
            def is_model_part(self): return True
            def is_modifier(self): return False
            def is_negative_volume(self): return False
            def is_support_enforcer(self): return False
            def is_support_blocker(self): return False
            def config_keys(self): return ["wall_loops"]
            def config_value(self, key): return "4" if key == "wall_loops" else None

        class Instance:
            printable = True

            def id(self): return 201

        class ModelObject:
            name = "Tower"
            module_name = ""
            printable = True

            def id(self): return 101
            def instance_count(self): return 1
            def volume_count(self): return 1
            def has_custom_layering(self): return False
            def is_fdm_support_painted(self): return False
            def is_seam_painted(self): return False
            def is_mm_painted(self): return False
            def is_fuzzy_skin_painted(self): return False
            def config_keys(self): return ["layer_height"]
            def config_value(self, key): return "0.16" if key == "layer_height" else None
            def instances(self): return [Instance()]
            def volumes(self): return [Volume()]

        class Model(FakeModel):
            def object_count(self): return 1
            def objects(self): return [ModelObject()]

        host = FakeHost(FakeBundle(values={"key": "value"}))
        host._model = Model()
        captured_at = datetime.datetime(2026, 9, 22, tzinfo=datetime.timezone.utc)
        snapshot = self.plugin.build_context_inventory(host, captured_at=captured_at)

        object_source = self.inventory_source(snapshot, "model.objects[0].config")
        volume_source = self.inventory_source(snapshot, "model.objects[0].volumes[0].config")
        self.assertEqual("0.16", object_source["entries"][0]["raw_value"])
        self.assertEqual("4", volume_source["entries"][0]["raw_value"])
        self.assertEqual(2, volume_source["association"]["extruder_id_one_based"])
        object_record = snapshot["project_model_context"]["objects"][0]
        self.assertEqual("input_file", object_record["omitted_fields"][0]["field"])
        self.assertEqual(self.plugin.REDACTED, object_record["volumes"]["items"][0]["mesh_data"]["read_status"])
        self.assertEqual(self.plugin.DIFFERENT_PHASE, object_record["instances"]["items"][0]["effective_is_printable"]["read_status"])

    def test_json_export_is_utf8_valid_and_export_failures_are_reported(self):
        snapshot = self.inventory(FakeBundle(values={"unicode": "café λ", "multiline": "one\ntwo\n"}))
        timestamp = datetime.datetime(2026, 9, 22, 1, 2, 3, 456789, tzinfo=datetime.timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            export_path = pathlib.Path(
                self.plugin.write_context_export(snapshot, directory, captured_at=timestamp)
            )
            self.assertEqual("orca-context-20260922T010203.456789Z.json", export_path.name)
            loaded = json.loads(export_path.read_text(encoding="utf-8"))
            merged = self.inventory_source(loaded, "preset_bundle.merged_full_config")
            values = {entry["key"]: entry["raw_value"] for entry in merged["entries"]}
            self.assertEqual("café λ", values["unicode"])
            self.assertEqual("one\ntwo\n", values["multiline"])

            blocked_root = pathlib.Path(directory) / "not-a-directory"
            blocked_root.write_text("occupied", encoding="utf-8")
            with self.assertRaises(OSError):
                self.plugin.write_context_export(snapshot, blocked_root, captured_at=timestamp)

            host = FakeHost(FakeBundle(values={"key": "value"}))
            host.plugin = types.SimpleNamespace(storage=lambda: str(blocked_root))
            self.orca.host = host
            result = self.plugin.ExportOrcaContextJson().execute()
            self.assertFalse(result["success"])
            self.assertIn("export failed", result["message"])

    def test_export_action_writes_to_host_storage_and_all_actions_register(self):
        with tempfile.TemporaryDirectory() as directory:
            host = FakeHost(FakeBundle(values={"key": "value"}))
            host.plugin = types.SimpleNamespace(storage=lambda: directory)
            self.orca.host = host
            result = self.plugin.ExportOrcaContextJson().execute()
            self.assertTrue(result["success"])
            export_path = pathlib.Path(result["data"])
            self.assertTrue(export_path.is_file())
            self.assertEqual(pathlib.Path(directory) / "exports", export_path.parent)

        self.orca.registered_capabilities.clear()
        self.plugin.HelixCalibrationPlugin().register_capabilities()
        self.assertEqual(
            [
                self.plugin.HelixCalibrationContext,
                self.plugin.ExportOrcaContextJson,
                self.plugin.NightlyQualificationPanel,
            ],
            self.orca.registered_capabilities,
        )

    def test_inventory_records_exact_runtime_build_metadata(self):
        snapshot = self.inventory(FakeBundle(values={"key": "value"}))
        self.assertEqual(self.plugin.READ_SUCCEEDED, snapshot["capture"]["host_build_metadata_read_status"])
        self.assertEqual("2.5.0-dev", snapshot["capture"]["host_build"]["version"])
        self.assertEqual("210bc927", snapshot["capture"]["host_build"]["build"])

    def test_lifecycle_payload_preserves_event_association_fields(self):
        event = types.SimpleNamespace(name="GCodeExportFinished")
        context = types.SimpleNamespace(
            name="temperature-tower.gcode",
            code=types.SimpleNamespace(name="Ok"),
            msg=r"C:\\qualification\\temperature-tower.gcode",
            id="model-17",
            previous_name="",
            device_id="",
            job_id="",
            source="gcode-export",
            index=0,
            dirty=False,
        )
        captured_at = datetime.datetime(2026, 10, 11, 12, 0, tzinfo=datetime.timezone.utc)
        payload = self.plugin.lifecycle_event_payload(event, context, captured_at=captured_at)
        self.assertEqual("GCodeExportFinished", payload["event"])
        self.assertEqual(r"C:\\qualification\\temperature-tower.gcode", payload["msg"])
        self.assertEqual("model-17", payload["id"])
        self.assertEqual("2026-10-11T12:00:00Z", payload["captured_at_utc"])

    def test_qualification_panel_is_host_owned_read_only_and_saves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            host = FakeHost(
                FakeBundle(
                    values={
                        "printer_technology": "FFF",
                        "nozzle_diameter": "0.4",
                        "nozzle_temperature": "217",
                    }
                ),
                storage_root=directory,
            )
            host.ui = FakeUI()
            self.orca.host = host
            capability = self.plugin.NightlyQualificationPanel()

            result = capability.execute()
            self.assertTrue(result["success"])
            self.assertEqual("right", host.ui.last_create["dock"])
            self.assertIn("never starts a print", host.ui.last_create["html"])
            self.assertNotIn("window.open", host.ui.last_create["html"])

            capability.on_message({"command": "ready"})
            state = capability.panel.posts[-1]
            self.assertEqual("state", state["command"])
            self.assertTrue(state["runtime"]["matches_target"])
            self.assertEqual(
                217,
                state["context"]["filaments"][0]["normal_nozzle_temperature"]["value"],
            )

            event = types.SimpleNamespace(name="PresetSelected")
            context = types.SimpleNamespace(
                name="Generic PLA - Qualification",
                code=types.SimpleNamespace(name="Ok"),
                msg="",
                id="",
                previous_name="Generic PLA",
                device_id="",
                job_id="",
                source="preset",
                index=0,
                dirty=True,
            )
            capability.on_lifecycle_event(event, context)
            self.assertEqual("event", capability.panel.posts[-1]["command"])
            self.assertEqual("PresetSelected", capability.panel.posts[-1]["event"]["event"])

            capability.on_message({"command": "save"})
            saved = pathlib.Path(capability.panel.posts[-1]["saved_path"])
            self.assertEqual(pathlib.Path(directory) / "qualification", saved.parent)
            evidence = json.loads(saved.read_text(encoding="utf-8"))
            self.assertEqual("helix-orca-nightly-qualification/v1", evidence["schema"])
            self.assertTrue(evidence["runtime"]["matches_target"])
            self.assertEqual("PresetSelected", evidence["lifecycle"]["events"][0]["event"])
            self.assertIn("does not start", evidence["non_claims"][0])

            capability.on_message({"command": "clear"})
            self.assertEqual([], capability.events)
            self.assertEqual([], capability.panel.posts[-1]["lifecycle"]["events"])

    def test_manual_file_selection_is_bounded_and_clears_invalid_replacements(self):
        capability = self.plugin.NightlyQualificationPanel()
        valid = {"name": "temperature.gcode", "size": 3619562,
                 "sha256": "0" * 64, "bands": list(range(230, 189, -5))}
        capability.on_message({"command": "manual_file", "file": valid})
        self.assertEqual(valid, capability.manual_file)
        for change in ({"name": "../tower.gcode"}, {"size": True}, {"size": 20000001},
                       {"sha256": "bad"}, {"bands": [230, 220]}, {"name": "tower.txt"}):
            with self.subTest(change=change):
                capability.on_message({"command": "manual_file", "file": valid})
                capability.on_message({"command": "manual_file", "file": dict(valid, **change)})
                self.assertIsNone(capability.manual_file)
        capability.on_message({"command": "manual_file", "file": None})
        self.assertIsNone(capability.manual_file)

    def test_qualification_rejects_a_different_runtime_build(self):
        host = FakeHost(
            FakeBundle(values={"printer_technology": "FFF"}),
            version="2.5.0-dev",
            build="different",
        )
        runtime = self.plugin._runtime_build(host)
        self.assertFalse(runtime["matches_target"])
        self.assertIn("does not match", runtime["reason"])

    def test_host_api_failure_returns_visible_error_payload(self):
        class BrokenHost:
            def preset_bundle(self):
                raise RuntimeError("preset API missing")

        snapshot = self.plugin.build_context(BrokenHost())
        self.assertEqual("error", snapshot["status"])
        self.assertIn("preset API missing", snapshot["message"])

    def test_plugin_has_no_out_of_scope_runtime_imports(self):
        source = PLUGIN_PATH.read_text(encoding="utf-8")
        for forbidden in ("import socket", "import urllib", "import requests", "import subprocess", "import threading"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
