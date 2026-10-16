#!/usr/bin/env python3
"""Qualify the generated OrcaCal Temperature return UI on exact beta.9."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "scripts/temperature-communication-plugin.py",
    "scripts/temperature-communication-qualify.py",
    "scripts/helix-beta9-qualify.py",
    "scripts/helix_dev.py",
)


def qualification_source_hashes() -> dict[str, str]:
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in SOURCE_PATHS}


# Capture before importing any executable qualification dependency.
LOADED_SOURCE_SNAPSHOT = qualification_source_hashes()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


beta9 = load("temperature_beta9", ROOT / "scripts/helix-beta9-qualify.py")
accepted = beta9.accepted
generator = load("temperature_plugin_generator", ROOT / "scripts/temperature-communication-plugin.py")

VALID_REQUEST = {
    "schema": "helix-orca-temperature-session/v1",
    "simulation_only": True,
    "not_applied": True,
    "request_id": "0123456789abcdef0123456789abcdef",
    "origin_id": "fedcba9876543210fedcba9876543210",
    "context_sha256": "2e93bbf07184d71f85cd3e417c87e09f80c70d9dfbbc9d7f18c5ee0495bf4df4",
    "file_sha256": "94c92b561d249ecba76fe6059af09ab89068d2fcc15a6524f5f12a832d32c387",
    "file": "temperature-230-190-step5-oct15.gcode",
    "file_bytes": 3028194,
    "printer": "Voron 2.4 300 0.4 nozzle",
    "filament": "Generic PLA - Voron Rapido - Initial",
    "process": "Voron 0.20 Standard - Fast Quality",
    "nozzle_mm": 0.4,
    "saved_current": 215,
    "edited_current": 217,
    "current": 220,
    "setting": "nozzle_temperature",
    "choices": [230, 225, 220, 215, 210, 205, 200, 195, 190],
    "expires_at": 2000000000,
    "ttl_seconds": 900,
}
VALID_ACK = {
    key: value for key, value in VALID_REQUEST.items()
    if key in {"simulation_only", "not_applied", "request_id", "origin_id",
               "context_sha256", "file_sha256", "file", "file_bytes", "setting"}
}
VALID_ACK.update({"schema": "helix-orca-temperature-ack/v1", "value": 205})
VALID_LEASE = {"issued_eventtime": 1000.0, "expires_eventtime": 1900.0}
VALID_ENVELOPE = {"session": VALID_REQUEST, "lease": VALID_LEASE}
FIXTURE_EVENTTIME = 1000.25
SYNTHETIC_CLOCK = {
    "kind": "synthetic-query-eventtime",
    "eventtime": FIXTURE_EVENTTIME,
    "scope": "test fixture wraps only printer.objects.query print_stats state",
}

TILE_XML = """<?xml version="1.0"?>
<component>
  <view name="{component}" extends="lv_obj" width="100%" height="100%"
        clickable="true" scrollable="false" style_pad_all="#space_xs"
        style_flex_main_place="center" style_flex_cross_place="center" flex_flow="column">
    <event_cb trigger="clicked" callback="plugin_event" user_data="orcacal__{action}"/>
    <text_small text="{label}" style_text_align="center"/>
  </view>
</component>
"""

EXPECTED_ASSERTIONS = (
    "plugin-loaded", "baseline-tile-visible", "baseline-chooser-compatible",
    "baseline-temperature-compatible", "baseline-start-toast", "request-trigger-visible",
    "request-auto-opens-accepted-stack", "request-updates-chooser-context",
    "request-updates-existing-temperature-detail", "request-native-back-to-home",
    "fixed-nine-value-selector", "native-selector-chooses-205", "selection-enters-waiting",
    "exact-result-persisted", "ack-enters-returned", "native-back-preserved", "horizontal-fit",
)


class QualificationError(RuntimeError):
    pass


def verify_source_snapshot(expected: dict[str, str] | None = None) -> dict[str, str]:
    expected = expected or LOADED_SOURCE_SNAPSHOT
    current = qualification_source_hashes()
    if current != expected:
        raise QualificationError("qualification source changed after module load")
    return current


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*")) if path.is_file()}


def state_root() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "helix-orca-calibration/temperature-communication"


def make_fixture(root: Path, envelope: dict | None = None,
                 eventtime: float = FIXTURE_EVENTTIME) -> Path:
    plugin_root = root / "plugins"
    target = plugin_root / "orcacal"
    generator.generate(target)
    request = json.dumps(envelope or VALID_ENVELOPE, separators=(",", ":"))
    ack = json.dumps(VALID_ACK, separators=(",", ":"))
    hook = f"""
local qualification_eventtime = {eventtime!r}
local qualification_clock_missing = false
local qualification_real_call = helix.moonraker.call
helix.moonraker.call = function(method, params)
    local response, err = qualification_real_call(method, params)
    local objects = type(params) == "table" and params.objects or nil
    local fields = type(objects) == "table" and objects.print_stats or nil
    local exact_query = method == "printer.objects.query"
        and type(fields) == "table" and #fields == 1 and fields[1] == "state"
    if exact_query and type(response) == "table" and type(response.result) == "table" then
        if qualification_clock_missing then
            response.result.eventtime = nil
        else
            response.result.eventtime = qualification_eventtime
        end
    end
    return response, err
end
local qualification_request = helix.json.decode([==[{request}]==])
local qualification_ack = helix.json.decode([==[{ack}]==])
helix.ui.on("qualify_request", function()
    on_temperature_request("qualification", qualification_request)
end)
helix.ui.on("qualify_ack", function()
    on_temperature_ack("qualification", qualification_ack)
end)
helix.ui.on("qualify_expire", function()
    qualification_eventtime = qualification_request.lease.expires_eventtime
end)
helix.ui.on("qualify_clock_missing", function()
    qualification_clock_missing = true
end)
helix.ui.on("qualify_clock_restore", function()
    qualification_clock_missing = false
end)
"""
    with (target / "main.lua").open("a", encoding="utf-8") as handle:
        handle.write(hook)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    manifest["widgets"].extend([
        {"id": "orcacal__qualify-request", "name": "Inject request", "icon": "download",
         "description": "Test-only request trigger", "component": "orcacal__qualify-request", "colspan": 3, "rowspan": 2},
        {"id": "orcacal__qualify-ack", "name": "Inject acknowledgement", "icon": "check",
         "description": "Test-only acknowledgement trigger", "component": "orcacal__qualify-ack", "colspan": 3, "rowspan": 2},
        {"id": "orcacal__qualify-expire", "name": "Advance lease clock", "icon": "clock",
         "description": "Test-only expiry trigger", "component": "orcacal__qualify-expire", "colspan": 3, "rowspan": 2},
        {"id": "orcacal__qualify-clock-missing", "name": "Hide lease clock", "icon": "cancel",
         "description": "Test-only missing clock trigger", "component": "orcacal__qualify-clock-missing", "colspan": 3, "rowspan": 2},
        {"id": "orcacal__qualify-clock-restore", "name": "Restore lease clock", "icon": "refresh",
         "description": "Test-only clock restore trigger", "component": "orcacal__qualify-clock-restore", "colspan": 3, "rowspan": 2},
    ])
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for suffix, action, label in (
        ("request", "qualify_request", "Inject request"),
        ("ack", "qualify_ack", "Inject acknowledgement"),
        ("expire", "qualify_expire", "Advance lease clock"),
        ("clock-missing", "qualify_clock_missing", "Hide lease clock"),
        ("clock-restore", "qualify_clock_restore", "Restore lease clock"),
    ):
        component = f"orcacal__qualify-{suffix}"
        (target / "ui" / f"{component}.xml").write_text(
            TILE_XML.format(component=component, action=action, label=label), encoding="utf-8"
        )
    return plugin_root


def seed_settings(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    settings = json.loads((beta9.cache_root() / "runtime/helixscreen/config/settings.json.template").read_text())
    settings.update({"dark_mode": True, "disable_sound": True, "sounds_enabled": False,
                     "wizard_completed": True, "tour": {"completed": True, "last_seen_version": 1},
                     "active_printer_id": "default"})
    settings.setdefault("plugins", {})["enabled"] = {
        "orcacal": {"permissions": ["storage"], "version": "0.3.0-issue8-native"}
    }
    printer = settings.setdefault("printers", {}).setdefault("default", {})
    printer["name"] = "Temperature communication qualification"
    printer.setdefault("hardware", {})["expected"] = list(accepted.BETA4_MOCK_ACKNOWLEDGED_HARDWARE)
    widgets = [
        {"col": 0, "colspan": 4, "enabled": True, "id": "orcacal__tile", "row": 0, "rowspan": 2},
        {"col": 4, "colspan": 4, "enabled": True, "id": "orcacal__qualify-request", "row": 0, "rowspan": 2},
        {"col": 8, "colspan": 4, "enabled": True, "id": "orcacal__qualify-ack", "row": 0, "rowspan": 2},
        {"col": 0, "colspan": 4, "enabled": True, "id": "orcacal__qualify-expire", "row": 2, "rowspan": 2},
        {"col": 4, "colspan": 4, "enabled": True, "id": "orcacal__qualify-clock-missing", "row": 2, "rowspan": 2},
        {"col": 8, "colspan": 4, "enabled": True, "id": "orcacal__qualify-clock-restore", "row": 2, "rowspan": 2},
    ]
    widgets.extend({"col": -1, "colspan": 1, "enabled": False, "id": widget_id,
                    "row": -1, "rowspan": 1} for widget_id in accepted.BETA4_DEFAULT_HOME_WIDGETS)
    printer["panel_widgets"] = {"home": {"grid": "12x8", "main_page_index": 0,
        "next_page_id": 1, "pages": [{"id": "main", "widgets": widgets}]}}
    accepted.json_write(config_dir / "settings-test.json", settings)


def wait_ready(name: str) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if not accepted._docker_running(name): break
        if accepted.ctl(name, "ping", check=False) == "pong":
            logs = accepted.run(["docker", "logs", name], capture=True, check=False)
            if "[PluginHost] orcacal: loaded" in logs.stdout + logs.stderr: return
        time.sleep(0.2)
    logs = accepted.run(["docker", "logs", name], capture=True, check=False)
    raise QualificationError("generated OrcaCal plugin did not load:\n" + logs.stdout + logs.stderr)


def tap(name: str, widget: str, width: int, height: int) -> None:
    accepted.ctl(name, "scroll", widget)
    accepted.ctl(name, "wait_idle")
    accepted._tap_visible_widget(name, widget, width, height)


def back_to_home(name: str) -> None:
    while accepted.ctl(name, "current").get("overlays"):
        accepted.ctl(name, "go_back")
        accepted.ctl(name, "wait_idle")


def open_temperature(name: str, width: int, height: int):
    tap(name, "orcacal__tile", width, height)
    accepted._assert_overlay(accepted.ctl(name, "current"), ["orcacal__wizard"])
    chooser = accepted.ctl(name, "ls", "orcacal__wizard")
    accepted._assert_widget(chooser, "back_button")
    tap(name, "orcacal__temperature_choice", width, height)
    accepted._assert_overlay(accepted.ctl(name, "current"), ["orcacal__wizard", "orcacal__temperature"])
    detail = accepted.ctl(name, "ls", "orcacal__temperature")
    accepted._assert_widget(detail, "back_button")
    return chooser, detail


def run_viewport(entry, output: Path, plugin_root: Path) -> dict[str, object]:
    label, width, height, layout, dpi = entry
    work = output / label
    work.mkdir()
    (work / "home").mkdir()
    seed_settings(work / "config")
    name = f"temperature-i8-{os.getpid()}-{label.replace('_', '-')}"
    accepted._remove_container(name)
    accepted.PLUGIN_ROOT = plugin_root
    accepted.run(accepted._container_args(name, work, width, height, layout, dpi), capture=True)
    assertions = []
    try:
        wait_ready(name); assertions.append("plugin-loaded")
        for widget in ("orcacal__tile", "orcacal__qualify-request", "orcacal__qualify-ack"):
            accepted._visible_widget_geometry(accepted.ctl(name, "geom", widget, "0"), widget, width, height)
        assertions.append("baseline-tile-visible")
        accepted._screenshot(name, work, "baseline-home.png")

        chooser, detail = open_temperature(name, width, height)
        accepted._assert_widget(chooser, "orcacal__temperature_choice")
        assertions.append("baseline-chooser-compatible")
        accepted._assert_widget(detail, "orcacal__start_button")
        assertions.append("baseline-temperature-compatible")
        tap(name, "orcacal__start_button", width, height)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            logs = accepted.run(["docker", "logs", name], capture=True, check=False)
            if "Toast shown: [info] Calibration request test" in logs.stdout + logs.stderr: break
            time.sleep(0.1)
        else: raise QualificationError("accepted Start toast was not preserved")
        assertions.append("baseline-start-toast")
        time.sleep(4.1)
        back_to_home(name)

        tap(name, "orcacal__qualify-request", width, height)
        assertions.append("request-trigger-visible")
        accepted._assert_overlay(accepted.ctl(name, "current"),
                                 ["orcacal__wizard", "orcacal__temperature"])
        assertions.append("request-auto-opens-accepted-stack")
        detail = accepted.ctl(name, "ls", "orcacal__temperature")
        for widget in ("orcacal__request_printer", "orcacal__request_values", "orcacal__request_file", "orcacal__request_hash"):
            accepted._assert_widget(detail, widget)
        accepted.ctl(name, "go_back"); accepted.ctl(name, "wait_idle")
        accepted._assert_overlay(accepted.ctl(name, "current"), ["orcacal__wizard"])
        chooser = accepted.ctl(name, "ls", "orcacal__wizard")
        for widget in ("orcacal__context_primary", "orcacal__context_secondary", "orcacal__active_status"):
            accepted._assert_widget(chooser, widget)
        assertions.append("request-updates-chooser-context")
        assertions.append("request-updates-existing-temperature-detail")
        accepted.ctl(name, "go_back"); accepted.ctl(name, "wait_idle")
        accepted._assert_overlay(accepted.ctl(name, "current"), [])
        assertions.append("request-native-back-to-home")
        chooser, detail = open_temperature(name, width, height)
        accepted._assert_widget(detail, "orcacal__temperature_selector")
        accepted._assert_widget(detail, "orcacal__return_selection")
        assertions.append("fixed-nine-value-selector")
        accepted._assert_horizontal_fit(accepted.ctl(name, "geom", "orcacal__temperature_content", "8"), width)
        accepted.ctl(name, "scroll", "orcacal__temperature_selector")
        accepted.ctl(name, "set_value", "orcacal__temperature_selector", "5")
        if accepted.ctl(name, "get", "orcacal__tc_choice_idx").get("value") != 5:
            raise QualificationError("native selector did not choose 205 C")
        assertions.append("native-selector-chooses-205")
        tap(name, "orcacal__return_selection", width, height)
        time.sleep(1.5)
        waiting = accepted.ctl(name, "ls", "orcacal__temperature")
        accepted._assert_widget(waiting, "orcacal__waiting_area")
        assertions.append("selection-enters-waiting")
        accepted._screenshot(name, work, "waiting.png")
        storage_path = work / "config/plugin-data/orcacal.json"
        stored = json.loads(storage_path.read_text(encoding="utf-8"))["session"]
        expected_result = dict(VALID_ACK)
        expected_result["schema"] = "helix-orca-temperature-selection/v1"
        if set(stored) != {"request", "lease", "result", "acknowledged", "recovery_required", "state", "tombstones"}:
            raise QualificationError(f"unexpected native session storage shape: {stored}")
        if stored["request"] != VALID_REQUEST or stored["lease"] != VALID_LEASE \
                or stored["result"] != expected_result:
            raise QualificationError("persisted native request/result does not match exact protocol")
        if stored["acknowledged"] is not False or stored["state"] not in {"queued", "waiting"}:
            raise QualificationError("selection claimed delivery before exact acknowledgement")
        assertions.append("exact-result-persisted")
        back_to_home(name)

        tap(name, "orcacal__qualify-ack", width, height)
        time.sleep(0.8)
        _, returned = open_temperature(name, width, height)
        accepted._assert_widget(returned, "orcacal__returned_area")
        accepted._assert_widget(returned, "orcacal__returned_value")
        assertions.append("ack-enters-returned")
        accepted._screenshot(name, work, "returned.png")
        time.sleep(0.7)
        stored = json.loads(storage_path.read_text(encoding="utf-8"))["session"]
        if stored["result"] != expected_result or stored["acknowledged"] is not True \
                or stored["state"] != "returned":
            raise QualificationError("exact acknowledgement did not commit returned native state")
        accepted.ctl(name, "go_back"); accepted.ctl(name, "wait_idle")
        accepted._assert_overlay(accepted.ctl(name, "current"), ["orcacal__wizard"])
        assertions.append("native-back-preserved")
        accepted._assert_horizontal_fit(accepted.ctl(name, "geom", "orcacal__chooser_content", "8"), width)
        assertions.append("horizontal-fit")
        return {"assertions": assertions, "dpi": dpi, "label": label, "layout": layout,
                "result": "PASS", "viewport": f"{width}x{height}"}
    finally:
        logs = accepted.run(["docker", "logs", name], capture=True, check=False)
        (work / "runtime.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        accepted._remove_container(name)


def capture(output: Path) -> None:
    runtime = beta9.verify_cache()
    beta9.configure_accepted_harness()
    image = accepted.image_metadata()
    if output.exists(): raise QualificationError(f"capture destination exists: {output}")
    output.mkdir(parents=True)
    fixture_parent = generator.default_output().parent / "qualification-fixtures"
    fixture_parent.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix="native-matrix-", dir=fixture_parent))
    baseline_before = generator.verify_baseline()
    rows = []
    try:
        plugin_root = make_fixture(fixture)
        fixture_files = file_hashes(plugin_root / "orcacal")
        verify_source_snapshot()
        if file_hashes(plugin_root / "orcacal") != fixture_files:
            raise QualificationError("qualification fixture changed before native execution")
        for entry in accepted.VIEWPORTS:
            row = run_viewport(entry, output, plugin_root)
            if row["assertions"] != list(EXPECTED_ASSERTIONS):
                raise QualificationError(f"assertion sequence mismatch: {row}")
            rows.append(row)
            print(f"PASS {row['label']}: {row['viewport']}", flush=True)
        verify_source_snapshot()
        if file_hashes(plugin_root / "orcacal") != fixture_files:
            raise QualificationError("qualification fixture changed during native execution")
        if generator.verify_baseline() != baseline_before:
            raise QualificationError("qualification changed the accepted OrcaCal baseline")
        report = {
            "accepted_baseline": baseline_before,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "container_network": "none", "dependency_image": accepted.IMAGE,
            "dependency_image_id": image["id"], "fixture_files": fixture_files,
            "qualification_sources": LOADED_SOURCE_SNAPSHOT,
            "results": rows, "runtime": runtime,
            "screenshots": {str(path.relative_to(output)): sha256(path) for path in sorted(output.rglob("*.png"))},
            "storage": {str(path.relative_to(output)): sha256(path)
                        for path in sorted(output.glob("*/config/plugin-data/orcacal.json"))},
            "test_envelope": VALID_ENVELOPE, "test_ack": VALID_ACK,
            "clock_fixture": dict(SYNTHETIC_CLOCK,
                                  wrapper_sha256=fixture_files["main.lua"]),
        }
        accepted.json_write(output / "report.json", report)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or state_root() / "captures" / time.strftime("%Y%m%d-%H%M%S")
    capture(output)
    print(f"Temperature communication beta.9 matrix retained at {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (QualificationError, generator.GenerationError, beta9.QualificationError,
            accepted.HarnessError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
