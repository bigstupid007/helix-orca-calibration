#!/usr/bin/env python3
"""Exercise the display-only receipt on the exact beta.9 developer runtime."""

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
PLUGIN = ROOT / "integration/helix-orca-display"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


beta9 = load("beta9_qualification", ROOT / "scripts/helix-beta9-qualify.py")
accepted = beta9.accepted

VALID_PAYLOAD = {
    "schema": "helix-orca-display/v1",
    "display_only": True,
    "request_id": "0123456789abcdef0123456789abcdef",
    "file_sha256": "94c92b561d249ecba76fe6059af09ab89068d2fcc15a6524f5f12a832d32c387",
    "file": "temperature-230-190-step5-oct15.gcode",
    "file_bytes": 3028194,
    "printer": "Voron 2.4 300 0.4 nozzle",
    "filament": "Generic PLA - Voron Rapido - Initial",
    "process": "Voron 0.20 Standard - Fast Quality",
    "nozzle_mm": 0.4,
    "current_temperature_c": 220,
    "temperatures": [230, 225, 220, 215, 210, 205, 200, 195, 190],
}

TILE_XML = """<?xml version="1.0"?>
<component>
  <view name="{component}" extends="lv_obj" width="100%" height="100%"
        clickable="true" scrollable="false" style_pad_all="#space_xs"
        style_flex_main_place="center" style_flex_cross_place="center" flex_flow="column">
    <event_cb trigger="clicked" callback="plugin_event" user_data="helix-orca-display__{action}"/>
    <text_small text="{label}" style_text_align="center"/>
  </view>
</component>
"""


class DisplayQualificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plugin_hashes(root: Path = PLUGIN) -> dict[str, str]:
    return {str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*")) if path.is_file()}


def make_fixture(destination: Path) -> Path:
    plugin_root = destination / "plugins"
    target = plugin_root / "helix-orca-display"
    shutil.copytree(PLUGIN, target)
    valid = json.dumps(VALID_PAYLOAD, separators=(",", ":"))
    # Instrument the exact copied source from inside its lexical scope. The
    # shipping plugin remains event-only; these two UI callbacks exist only in
    # the network-disabled qualification fixture.
    hook = f"""
local qualification_valid = helix.json.decode([==[{valid}]==])
helix.ui.on("qualify_valid", function()
    local receipt = validate(qualification_valid)
    if receipt then show_receipt(receipt) end
end)
helix.ui.on("qualify_invalid", function()
    local invalid = helix.json.decode([==[{valid}]==])
    invalid.start = true
    local receipt = validate(invalid)
    if receipt then show_receipt(receipt) end
end)
"""
    with (target / "main.lua").open("a", encoding="utf-8") as handle:
        handle.write(hook)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    manifest["widgets"] = [
        {"id": "helix-orca-display__valid-tile", "name": "Valid receipt", "icon": "check",
         "description": "Test-only valid receipt trigger", "component": "helix-orca-display__valid-tile", "colspan": 3, "rowspan": 2},
        {"id": "helix-orca-display__invalid-tile", "name": "Invalid receipt", "icon": "close",
         "description": "Test-only invalid receipt trigger", "component": "helix-orca-display__invalid-tile", "colspan": 3, "rowspan": 2},
    ]
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for action, label in (("valid", "Valid receipt"), ("invalid", "Invalid receipt")):
        component = f"helix-orca-display__{action}-tile"
        (target / "ui" / f"{component}.xml").write_text(
            TILE_XML.format(component=component, action=f"qualify_{action}", label=label), encoding="utf-8"
        )
    return plugin_root


def seed_settings(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    settings = json.loads((beta9.cache_root() / "runtime/helixscreen/config/settings.json.template").read_text())
    settings.update({"dark_mode": True, "disable_sound": True, "sounds_enabled": False,
                     "wizard_completed": True, "tour": {"completed": True, "last_seen_version": 1},
                     "active_printer_id": "default"})
    settings.setdefault("plugins", {})["enabled"] = {
        "helix-orca-display": {"permissions": [], "version": "0.1.0"}
    }
    printer = settings.setdefault("printers", {}).setdefault("default", {})
    printer["name"] = "Helix display qualification"
    printer.setdefault("hardware", {})["expected"] = list(accepted.BETA4_MOCK_ACKNOWLEDGED_HARDWARE)
    printer["panel_widgets"] = {"home": {"grid": "12x8", "main_page_index": 0, "next_page_id": 1,
        "pages": [{"id": "main", "widgets": [
            {"col": 0, "colspan": 3, "enabled": True, "id": "helix-orca-display__invalid-tile", "row": 0, "rowspan": 2},
            {"col": 3, "colspan": 3, "enabled": True, "id": "helix-orca-display__valid-tile", "row": 0, "rowspan": 2},
        ]}]}}
    accepted.json_write(config_dir / "settings-test.json", settings)


def wait_ready(name: str) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if not accepted._docker_running(name):
            break
        if accepted.ctl(name, "ping", check=False) == "pong":
            logs = accepted.run(["docker", "logs", name], capture=True, check=False)
            if "[PluginHost] helix-orca-display: loaded" in logs.stdout + logs.stderr:
                return
        time.sleep(0.2)
    logs = accepted.run(["docker", "logs", name], capture=True, check=False)
    raise DisplayQualificationError("display plugin did not load:\n" + logs.stdout + logs.stderr)


def visible_home(name: str, width: int, height: int) -> None:
    current = accepted.ctl(name, "current")
    if current.get("panel") != "home" or current.get("overlays") != []:
        raise DisplayQualificationError(f"display qualification did not reach Home: {current}")
    for widget in ("helix-orca-display__invalid-tile", "helix-orca-display__valid-tile"):
        accepted._visible_widget_geometry(accepted.ctl(name, "geom", widget, "0"), widget, width, height)


def run_viewport(entry: tuple[str, int, int, str, int], root: Path, plugin_root: Path) -> dict[str, object]:
    label, width, height, layout, dpi = entry
    output = root / label
    output.mkdir()
    (output / "home").mkdir()
    seed_settings(output / "config")
    name = f"display-i6-{os.getpid()}-{label.replace('_', '-')}"
    accepted._remove_container(name)
    accepted.PLUGIN_ROOT = plugin_root
    accepted.run(accepted._container_args(name, output, width, height, layout, dpi), capture=True)
    assertions = []
    try:
        wait_ready(name)
        assertions.append("plugin-loaded")
        deadline = time.monotonic() + 10
        while True:
            try:
                visible_home(name, width, height)
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)
        assertions.append("test-triggers-visible")
        accepted._tap_visible_widget(name, "helix-orca-display__invalid-tile", width, height)
        accepted._assert_overlay(accepted.ctl(name, "current"), [])
        assertions.append("extra-key-rejected-without-overlay")
        accepted._tap_visible_widget(name, "helix-orca-display__valid-tile", width, height)
        accepted._assert_overlay(accepted.ctl(name, "current"), ["helix-orca-display__receipt"])
        assertions.append("valid-contract-opens-receipt")
        receipt = accepted.ctl(name, "ls", "helix-orca-display__receipt")
        for widget in ("helix-orca-display__receipt_line", "helix-orca-display__effective_line",
                       "helix-orca-display__file_line", "helix-orca-display__hash_line",
                       "helix-orca-display__dismiss"):
            accepted._assert_widget(receipt, widget)
        accepted._assert_horizontal_fit(
            accepted.ctl(name, "geom", "helix-orca-display__receipt_content", "8"), width
        )
        assertions.extend(("receipt-fields-present", "receipt-horizontal-fit"))
        accepted._screenshot(name, output, "receipt.png")
        accepted.ctl(name, "scroll", "helix-orca-display__dismiss")
        accepted.ctl(name, "wait_idle")
        accepted._tap_visible_widget(name, "helix-orca-display__dismiss", width, height)
        accepted._assert_overlay(accepted.ctl(name, "current"), [])
        assertions.append("dismiss-closes-receipt")
        accepted._screenshot(name, output, "dismissed.png")
        return {"assertions": assertions, "dpi": dpi, "label": label, "layout": layout,
                "result": "PASS", "viewport": f"{width}x{height}"}
    finally:
        logs = accepted.run(["docker", "logs", name], capture=True, check=False)
        (output / "runtime.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        accepted._remove_container(name)


def capture(output: Path) -> None:
    runtime = beta9.verify_cache()
    beta9.configure_accepted_harness()
    image = accepted.image_metadata()
    if output.exists():
        raise DisplayQualificationError(f"capture destination exists: {output}")
    output.mkdir(parents=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="helix-display-fixture-", dir=output))
    before = plugin_hashes()
    rows = []
    try:
        plugin_root = make_fixture(fixture_dir)
        fixture_hashes = plugin_hashes(plugin_root / "helix-orca-display")
        for entry in accepted.VIEWPORTS:
            row = run_viewport(entry, output, plugin_root)
            rows.append(row)
            print(f"PASS {row['label']}: {row['viewport']}", flush=True)
        screenshots = {str(path.relative_to(output)): sha256(path) for path in sorted(output.rglob("*.png"))}
        report = {
            "candidate_plugin_files": before,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "container_network": "none",
            "dependency_image": accepted.IMAGE,
            "dependency_image_id": image["id"],
            "fixture_files": fixture_hashes,
            "qualification_sources": {
                "scripts/helix-display-qualify.py": sha256(ROOT / "scripts/helix-display-qualify.py"),
                "scripts/helix-beta9-qualify.py": sha256(ROOT / "scripts/helix-beta9-qualify.py"),
                "scripts/helix_dev.py": sha256(ROOT / "scripts/helix_dev.py"),
            },
            "results": rows,
            "runtime": runtime,
            "screenshots": screenshots,
            "test_payload": VALID_PAYLOAD,
        }
        accepted.json_write(output / "report.json", report)
    finally:
        shutil.rmtree(fixture_dir, ignore_errors=True)
    if plugin_hashes() != before:
        raise DisplayQualificationError("display qualification changed candidate plugin files")
    print(f"Display-only beta.9 matrix retained at {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DisplayQualificationError, beta9.QualificationError, accepted.HarnessError,
            OSError, subprocess.SubprocessError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
