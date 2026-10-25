#!/usr/bin/env python3
"""Preserve the accepted parameter-control proof across generator-only changes.

This verifier does not qualify the current generator implementation.  It freezes
the accepted 66bfaf6 proof bytes and checks the explicitly reviewed amendment
boundary independently.  Generator dispositions retained in the old record
remain historical and cannot be relabelled as current-nightly qualification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("docs/evidence/issue-14/parameters")
ACCEPTED_COMMIT = "66bfaf6bb8df9a453c1ee85fbb43ba827daeda5b"
ACCEPTED_RUN = "b04728721c2741bd8d05b3001a343cdf"
ACCEPTED_BLOBS = {
    "scripts/v1-parameter-evidence.py": "f3176e139a6400bb8c50d2ff8319e2eddb4a6be35864ae2b5c4f6fa32e00febc",
    str(EVIDENCE / "report.json"): "a0386c8cb0edb96976e8e3ec411980ed9dd506052103a66de46730ee5775ece2",
    str(EVIDENCE / "operator.json"): "f39b272a459bc309fb3cb34cab9e5cd1aa6bf2fa2b7efce1e80e59182ba85449",
    str(EVIDENCE / "windows-parity.json"): "678593d6efd9ec43015f37bd6c2ad0aff4b58ca455c232f4fa522072618d815e",
}
ACCEPTED_SOURCE_MANIFEST_SHA256 = "256792025ec6abea748d4c80fcee8800cd1e2734fe15caedc3a210c3ef29180d"
HISTORICAL_REPORT_SHA256 = "178dc0551495db1322f2d64ab37429eff02e91ad8240ec5a1902d27156b813c5"
OPERATOR_DRIVER_SHA256 = "8284483945350ea699e4e7f56b7d1f0bec0d4b7a2df08a14ad379fb37c55f389"

# These files are the current-equivalence claim.  They are deliberately
# narrower than the accepted report's source inventory: generator, parity,
# deployment, job, and companion implementations require current evidence.
CONTROL_BOUNDARY = (
    "integration/temperature-print/ui/orcacal__tile.xml",
    "integration/v1_contract.py",
    "integration/v1_private_file.py",
    "integration/v1_routing.py",
    "integration/v1_runtime.py",
    "integration/v1_transport.py",
    "scripts/helix-beta9-qualify.py",
    "scripts/helix_dev.py",
    "scripts/temperature-communication-plugin.py",
    "scripts/temperature-communication-qualify.py",
    "scripts/temperature-viewer.html",
    "scripts/v1-native-plugin.py",
    "scripts/v1-native-qualify.py",
    "scripts/v1-native-review.py",
    "scripts/v1-runtime.py",
)
# The October 25 amendment intentionally changes only these entries in the
# otherwise-retained control boundary.  Keeping the accepted manifest immutable
# while pinning the replacement bytes makes the authority transition explicit;
# it does not turn either record into build-qualification evidence.
AMENDMENT_CONTROL_BOUNDARY_SHA256 = {
    "integration/v1_contract.py": "5180172eef09015de72b780fd335390085dcb4c372caeb4149d326ea52541d2e",
    "integration/v1_routing.py": "b3174a1816a6313e8730ac10a597bb1b5e0114a0f4bda6c3ab46f57ededf907a",
    "integration/v1_runtime.py": "ad2e09e3bd59dac8e4bfede3d15b26f00eb77704d77b35e514bafec748ed4c66",
    "integration/v1_transport.py": "b5f1afc43d099cb58868d02247c4f6431e154e172891511af2abd6fec778067b",
    "scripts/v1-native-plugin.py": "80c3f2f908211b657396dd4d627b3b0c1e5e08a04b4c8074da50c60761cdbf48",
    "scripts/v1-native-qualify.py": "5627f766b00ac1bf1c7070d86a211a69489c3385be2158f646b6cc8dde87ec41",
    "scripts/v1-native-review.py": "ea4131f1ef0c694539641da174ef5abd2e3b29e34d2648e244f6ca1616c6dc43",
    "scripts/v1-runtime.py": "9622d752eccdd4bdeb7548cc35541c84a81e2f737422e9f8326a7cf642b6826c",
}
NATIVE_SOURCE_PREFIX = "integration/v1-native/"
AMENDMENT_NATIVE_REMOVED = frozenset()
AMENDMENT_NATIVE_SHA256 = {
    "integration/v1-native/README.md": "0690ab6b87bb933f9b0b412e7a665e0164652bb25e961367c224a86f0e5b621a",
    "integration/v1-native/catalog.json": "ac8c17d40b33cf33b9d0660c4e3e046abe7c3c44de401909e4f0bf4a41d92415",
    "integration/v1-native/controls.lua": "a836d2c2d24675c7e33d8937dd20f690d892aee3b59f35567dc8bf0b293462b3",
    "integration/v1-native/main.lua": "8ce5e32e98d683845d9ca9c80669f9e5981af01fc52b0f01fa123307ca11a2b0",
    "integration/v1-native/presentation.lua": "df952a096fdcc559bff2da0e1f376fbad57b22e5e335279ecfd6430610e2943e",
    "integration/v1-native/ui/orcacal__v1_flow_ratio_yolo.xml": "19e735f60faba3d20173edbbf568e97ca5359df6ac9fdc8efba4c0f37a0e1249",
    "integration/v1-native/ui/orcacal__v1_job.xml": "914488e9f5c524a2942af6d56dca5a7ce3b3299feaf289dcfe909602a75640aa",
    "integration/v1-native/ui/orcacal__v1_keypad.xml": "06df03ddf2bc4cbe39e91733adc7190be8c41022ba1e1573b777d61c0831f326",
    "integration/v1-native/ui/orcacal__v1_pressure_advance_pattern.xml": "3070dc7e7962d2601441cb48879f0cc87662cda6f7634d0d80867f20342766bf",
    "integration/v1-native/ui/orcacal__v1_result.xml": "4f37d0c5276550cb99d5fc0c1a442be046da9efc824b96eb7b33f01dce51d444",
    "integration/v1-native/ui/orcacal__v1_result_picker.xml": "3f65f14d58e6846b8a328d947ea2e1b7960f2aa7aab002bc4ebe3ff99e6e7b79",
    "integration/v1-native/ui/orcacal__v1_warning.xml": "0e9150774a289a9083c1354ec9b9a3346d228bcaace177efb5a8b55f5dc1ce89",
}
EXCLUDED_GENERATOR_SOURCES = frozenset({
    "integration/v1_deployment.py",
    "integration/v1_engine.py",
    "integration/v1_generation.py",
    "integration/v1_jobs.py",
    "integration/v1_orca_extension.py",
    "integration/v1_parity.py",
})


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load(root, relative):
    path = Path(root) / relative
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe retained file: {relative}")
    require(path.resolve().is_relative_to(Path(root).resolve()), f"Retained path escaped root: {relative}")
    return json.loads(path.read_text())


def verify_source_manifest(report):
    sources = report.get("sources", {})
    require(len(sources) == 38, "Accepted source inventory changed")
    require(digest(sources) == ACCEPTED_SOURCE_MANIFEST_SHA256,
            "Accepted source manifest changed")


def verify_immutable_blobs(root=ROOT):
    root = Path(root)
    for relative, expected in ACCEPTED_BLOBS.items():
        path = root / relative
        require(path.is_file() and not path.is_symlink(), f"Missing/unsafe accepted blob: {relative}")
        require(sha(path) == expected, f"Accepted proof blob changed: {relative}")
    report = load(root, EVIDENCE / "report.json")
    operator = load(root, EVIDENCE / "operator.json")
    parity = load(root, EVIDENCE / "windows-parity.json")
    verify_source_manifest(report)
    require(report["verifier_sha256"] == ACCEPTED_BLOBS["scripts/v1-parameter-evidence.py"],
            "Accepted verifier binding changed")
    require(report["operator_sha256"] == ACCEPTED_BLOBS[str(EVIDENCE / "operator.json")],
            "Accepted operator binding changed")
    require(report["windows_parity_sha256"] == ACCEPTED_BLOBS[str(EVIDENCE / "windows-parity.json")],
            "Accepted parity binding changed")
    return report, operator, parity


def verify_historical_matrix(root, report):
    historical = report["historical"]
    require(historical == {
        "frames": 396,
        "report_sha256": HISTORICAL_REPORT_SHA256,
        "scope": "Historical synthetic matrix; does not qualify current parameter controls",
    }, "Historical evidence scope changed")
    directory = Path(root) / "docs/evidence/issue-14/native"
    source = directory / "report.json"
    require(sha(source) == HISTORICAL_REPORT_SHA256, "Historical native report changed")
    native = json.loads(source.read_text())
    require(len(native.get("screenshots", {})) == 396, "Historical frame inventory changed")
    for name, expected in native["screenshots"].items():
        item = Path(name)
        path = directory / item
        require(not item.is_absolute() and ".." not in item.parts and path.is_file()
                and not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()),
                "Missing/unsafe historical frame")
        require(sha(path) == expected, f"Historical native frame changed: {name}")


def verify_accepted_semantics(report, operator, parity):
    lifecycle = report["lifecycle"]
    require(lifecycle["run_id"] == ACCEPTED_RUN and lifecycle["state"] == "complete"
            and lifecycle["exit_code"] == 0 and lifecycle["runtime_clear"] is True
            and lifecycle["errors"] == [], "Accepted managed lifecycle changed")
    require(operator["schema"] == "helix-orca-v1-windows-parameter-operator/v1"
            and operator["passed"] is True and operator["viewport"] == "800x480",
            "Accepted operator result changed")
    require(operator["health"] == {"status": "ok", "synthetic_only": True, "run_id": ACCEPTED_RUN},
            "Accepted operator/run binding changed")
    require(operator["browser_version"] == "140.0.7339.186"
            and operator["page_errors"] == [] and operator["read_retries"] == [],
            "Accepted browser result changed")
    for key in ("physical_actions", "profile_writeback", "prepared_fixtures"):
        require(operator[key] is False, "Accepted proof crossed action boundary")
    require(operator["driver_sha256"] == OPERATOR_DRIVER_SHA256,
            "Accepted operator driver binding changed")
    require(operator["values"] == {
        "temperature": {"start": 235, "end": 195, "step": 5, "scale": False},
        "pressure_advance_pattern": {"start": .01, "end": .09, "step": .01},
        "retraction": {"start": .2, "end": 2.2, "step": .2},
        "max_volumetric_speed": {"start": 6, "end": 21, "step": .75},
        "flow_ratio_yolo": {"pass": 2},
    }, "Accepted selected values changed")
    require(len(operator["screenshots"]) == 14
            and len({item["name"] for item in operator["screenshots"]}) == 14
            and all(re.fullmatch(r"[a-f0-9]{64}", item["sha256"])
                    for item in operator["screenshots"]), "Accepted private-frame attestations changed")
    proofs = {item["kind"]: item for item in operator["proofs"]}
    traces = report["traces"]
    require(set(proofs) == set(traces) == set(operator["values"]) and len(proofs) == 5,
            "Accepted calibration inventory changed")
    for kind, proof in proofs.items():
        trace = traces[kind]
        request = proof["native_request"]
        require(request == proof["transport_request"] == proof["coordinator_request"]
                == trace["native_request"] == trace["transport_request"]
                == trace["coordinator_request"], "Accepted request propagation changed")
        require(request["calibration"] == kind and request["parameters"] == operator["values"][kind],
                "Accepted request selection changed")
        expected_digest = digest(request)
        require({proof["request_sha256"], proof["native_sha256"], proof["transport_sha256"],
                 proof["coordinator_sha256"], trace["native_sha256"], trace["transport_sha256"],
                 trace["coordinator_sha256"]} == {expected_digest},
                "Accepted request digest changed")
        flow = kind == "flow_ratio_yolo"
        require(proof["phase"] == trace["phase"] == ("review" if flow else "blocked"),
                "Accepted recorded phase changed")
        require(proof["generator_dispatched"] is flow and proof["artifact_generated"] is flow
                and proof["actual_windows_qualified"] is flow and proof["qualified"] is flow,
                "Accepted recorded generator disposition changed")
        require(proof["physical_adapter_enabled"] is False, "Accepted proof enabled an adapter")
    require(not any(action.get("widget") in {
        "orcacal__v1_confirm", "orcacal__v1_start", "orcacal__v1_cancel"
    } for action in operator["actions"]), "Accepted operator entered an action gate")
    require(parity["schema"] == "helix-orca-v1-windows-native-request-parity/v1"
            and parity["qualified"] is True and parity["success"] is True
            and parity["policy"] == "exact-executable-v1"
            and parity["parameters"] == {"pass": 2}
            and parity["hardware_abi_qualified"] is False
            and parity["physical_readiness"] is False
            and parity["physical_actions"] is False,
            "Accepted Windows parity record changed")


def current_equivalence_paths(report):
    sources = report["sources"]
    accepted_native = {name for name in sources if name.startswith(NATIVE_SOURCE_PREFIX)}
    require(AMENDMENT_NATIVE_REMOVED < accepted_native,
            "Amendment removal is not part of the accepted native inventory")
    require(not (set(AMENDMENT_NATIVE_SHA256) & AMENDMENT_NATIVE_REMOVED),
            "Amendment native add/change and removal overlap")
    native = sorted((accepted_native - AMENDMENT_NATIVE_REMOVED) | set(AMENDMENT_NATIVE_SHA256))
    expected = sorted((*CONTROL_BOUNDARY, *native))
    require(not (set(expected) & EXCLUDED_GENERATOR_SOURCES), "Equivalence/exclusion overlap")
    accepted_or_amended = set(sources) | set(AMENDMENT_NATIVE_SHA256)
    require(
        set(expected).issubset(accepted_or_amended),
        "Accepted control-boundary source missing",
    )
    return expected, native


def verify_current_equivalence(root, report):
    root = Path(root)
    expected, native = current_equivalence_paths(report)
    actual_native = sorted(str(path.relative_to(root)) for path in (root / "integration/v1-native").rglob("*")
                           if path.is_file())
    require(actual_native == native, "Current native UI/catalog inventory changed")
    for relative in expected:
        path = root / relative
        require(path.is_file() and not path.is_symlink(), f"Missing/unsafe current boundary source: {relative}")
        expected_sha256 = AMENDMENT_NATIVE_SHA256.get(relative,
            AMENDMENT_CONTROL_BOUNDARY_SHA256.get(relative, report["sources"].get(relative)))
        require(expected_sha256 is not None, f"Missing amendment digest: {relative}")
        require(sha(path) == expected_sha256,
                f"Current control/request boundary changed: {relative}")
    driver = root / "scripts/v1-windows-parameter-operator.cjs"
    require(driver.is_file() and not driver.is_symlink() and sha(driver) == OPERATOR_DRIVER_SHA256,
            "Current operator observation driver changed")


def verify(root=ROOT):
    root = Path(root)
    report, operator, parity = verify_immutable_blobs(root)
    verify_accepted_semantics(report, operator, parity)
    verify_historical_matrix(root, report)
    verify_current_equivalence(root, report)
    print("PASS: retained 66bfaf6 proof and exact beta.12 amendment boundary; current build qualification remains separate")


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("usage: python3 scripts/v1-parameter-preservation.py")
    verify()
