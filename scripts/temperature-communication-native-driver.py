#!/usr/bin/env python3
"""Run one Windows-origin request through the isolated native beta.9 picker."""

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


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


qualification = load("temperature_communication_qualification",
                     ROOT / "scripts/temperature-communication-qualify.py")
accepted = qualification.accepted
beta9 = qualification.beta9


class DriverError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selection_for(request: dict, value: int) -> dict:
    if value not in request.get("choices", []):
        raise DriverError("selected value is not one of the request choices")
    return {
        "schema": "helix-orca-temperature-selection/v1",
        "simulation_only": True,
        "not_applied": True,
        "request_id": request["request_id"],
        "origin_id": request["origin_id"],
        "context_sha256": request["context_sha256"],
        "file_sha256": request["file_sha256"],
        "file": request["file"],
        "file_bytes": request["file_bytes"],
        "setting": request["setting"],
        "value": value,
    }


def run(payload: Path, output: Path, result_output: Path, viewport_label: str, value: int,
        expiry_proof: bool = False) -> None:
    request = json.loads(payload.read_text(encoding="utf-8"))
    # The native extension remains the protocol authority. This exact key check
    # catches flattened-wrapper or accidental transport metadata before launch.
    if set(request) != set(qualification.VALID_REQUEST):
        raise DriverError("payload does not have the exact 20-key native request shape")
    expected_result = selection_for(request, value)
    try:
        choice_index = request["choices"].index(value)
    except (KeyError, ValueError) as exc:
        raise DriverError("payload does not contain the requested native selection") from exc
    entry = next((item for item in accepted.VIEWPORTS if item[0] == viewport_label), None)
    if entry is None:
        raise DriverError(f"unknown viewport label: {viewport_label}")
    if output.exists():
        raise DriverError(f"output exists: {output}")

    beta9.verify_cache()
    beta9.configure_accepted_harness()
    output.mkdir(parents=True)
    (output / "home").mkdir()
    qualification.seed_settings(output / "config")
    fixture = Path(tempfile.mkdtemp(prefix="helix-temperature-origin-"))
    qualification.VALID_REQUEST = request
    qualification.VALID_ACK = dict(expected_result, schema="helix-orca-temperature-ack/v1")
    plugin_root = qualification.make_fixture(fixture)
    label, width, height, layout, dpi = entry
    name = f"temperature-origin-{os.getpid()}"
    accepted._remove_container(name)
    accepted.PLUGIN_ROOT = plugin_root
    accepted.run(accepted._container_args(name, output, width, height, layout, dpi), capture=True)
    try:
        qualification.wait_ready(name)
        qualification.tap(name, "orcacal__qualify-request", width, height)
        accepted._assert_overlay(accepted.ctl(name, "current"),
                                 ["orcacal__wizard", "orcacal__temperature"])
        detail = accepted.ctl(name, "ls", "orcacal__temperature")
        for widget in ("orcacal__request_printer", "orcacal__request_values",
                       "orcacal__request_file", "orcacal__request_hash",
                       "orcacal__temperature_selector", "orcacal__return_selection"):
            accepted._assert_widget(detail, widget)
        accepted.ctl(name, "scroll", "orcacal__temperature_selector")
        accepted.ctl(name, "set_value", "orcacal__temperature_selector", str(choice_index))
        if accepted.ctl(name, "get", "orcacal__tc_choice_idx").get("value") != choice_index:
            raise DriverError("native selector did not retain requested value")
        qualification.tap(name, "orcacal__return_selection", width, height)
        time.sleep(0.8)
        storage = output / "config/plugin-data/orcacal.json"
        session = json.loads(storage.read_text(encoding="utf-8"))["session"]
        if session.get("request") != request or session.get("result") != expected_result:
            raise DriverError("native persisted request/result does not match Windows-origin payload")
        if session.get("acknowledged") is not False:
            raise DriverError("native result was acknowledged before originating companion receipt")
        assertions = ["fresh-request-auto-opened", "native-selector-used",
                      "exact-result-persisted", "awaiting-originating-companion-ack"]
        if expiry_proof:
            if request["ttl_seconds"] > 5:
                raise DriverError("expiry proof requires ttl_seconds <= 5")
            deadline = time.monotonic() + request["ttl_seconds"] + 1.5
            while time.monotonic() < deadline:
                session = json.loads(storage.read_text(encoding="utf-8"))["session"]
                if session.get("state") == "expired":
                    break
                time.sleep(0.1)
            else:
                raise DriverError("native session did not persist expiry")
            qualification.back_to_home(name)
            qualification.tap(name, "orcacal__qualify-ack", width, height)
            time.sleep(0.7)
            session = json.loads(storage.read_text(encoding="utf-8"))["session"]
            if session.get("state") != "expired" or session.get("acknowledged") is not False:
                raise DriverError("late exact ACK changed an expired session")
            assertions.append("late-ack-rejected-after-expiry")

            accepted._remove_container(name)
            accepted.run(accepted._container_args(name, output, width, height, layout, dpi), capture=True)
            qualification.wait_ready(name)
            if accepted.ctl(name, "current").get("overlays") != []:
                raise DriverError("expired restart unexpectedly opened native overlays")
            qualification.tap(name, "orcacal__tile", width, height)
            qualification.tap(name, "orcacal__temperature_choice", width, height)
            if accepted.ctl(name, "get", "orcacal__tc_choice_on").get("value") != 0:
                raise DriverError("expired restart re-enabled native selection")
            qualification.back_to_home(name)
            qualification.tap(name, "orcacal__qualify-request", width, height)
            if accepted.ctl(name, "current").get("overlays") != []:
                raise DriverError("duplicate expired request reopened native overlays")
            session = json.loads(storage.read_text(encoding="utf-8"))["session"]
            if session.get("state") != "expired" or session.get("acknowledged") is not False:
                raise DriverError("duplicate recovery changed persisted expired state")
            assertions.extend(("expired-state-survived-restart",
                               "duplicate-expired-recovery-rejected"))
        result_output.parent.mkdir(parents=True, exist_ok=True)
        result_output.write_text(json.dumps(expected_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        accepted._screenshot(name, output, "windows-origin-waiting.png")
        report = {
            "container_network": "none", "viewport": f"{width}x{height}",
            "layout": layout, "dpi": dpi, "request_sha256": sha256(payload),
            "result_sha256": sha256(result_output), "storage_sha256": sha256(storage),
            "state": session.get("state"), "acknowledged": False,
            "assertions": assertions,
        }
        (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        logs = accepted.run(["docker", "logs", name], capture=True, check=False)
        (output / "runtime.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        accepted._remove_container(name)
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result-output", type=Path, required=True)
    parser.add_argument("--viewport", default="medium_800x480")
    parser.add_argument("--value", type=int, default=205)
    parser.add_argument("--expiry-proof", action="store_true")
    args = parser.parse_args()
    run(args.payload, args.output, args.result_output, args.viewport, args.value, args.expiry_proof)
    print(f"Native selection retained at {args.result_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriverError, qualification.QualificationError, beta9.QualificationError,
            accepted.HarnessError, OSError, subprocess.SubprocessError,
            ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
