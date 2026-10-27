"""Dependency-free verifier tests; injected generation is never qualification."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from integration import v1_contract as contract
from integration import v1_jobs
from integration import v1_routing as routing
from integration.v1_qualification import (
    PACKAGE_BINDING_KEY, SCHEMA as RUNTIME_CLOSURE_SCHEMA, runtime_build_qualification,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v1_build_qualify", ROOT / "scripts/v1-build-qualify.py")
qualify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualify)


def context(origin, printer_name, nozzle=.4):
    effective = {
        "nozzle_diameter": str(nozzle), "filament_flow_ratio": "1", "belt_printer": "0",
        "curr_bed_type": "High Temp Plate", "extruder_type": "Direct Drive",
    }
    value = {
        "schema": "helix-orca-v1-context/v2", "origin_id": origin * 32,
        "runtime": dict(contract.ORCA_RUNTIME_V2, source_commit=contract.ORCA_SOURCE_V2,
                        executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2),
        "nozzle_mm": nozzle, "effective": effective,
        "filament_slots": [{"slot_number": 1, "preset_name": printer_name + " PLA"}],
        "origin_filament": {"slot_number": 1, "preset_name": printer_name + " PLA", "shared_slots": [1]},
    }
    for role in ("printer", "process", "filament"):
        name = printer_name + " PLA" if role == "filament" else printer_name + " " + role
        value[role] = {state: {"name": name, "config": {"identity": printer_name + "-" + role + "-" + state}}
                       for state in ("saved", "edited")}
    return contract.validate_context_v2(value)


class FakeFinalSlice:
    """Exercises receipt verification only and is permanently marked test-only."""
    def __init__(self, warning=False):
        self.warning = warning

    def __call__(self, request, snapshot, output_dir, config):
        output = Path(output_dir)
        output.mkdir(mode=0o700, parents=True)
        selected = routing.routes(config)[request["calibration"]]
        route = qualify.ROUTE_IDS[selected]
        qualification_sha, authorization = contract.authorize_qualification_generation_v2(
            config, request, snapshot, route, output)
        (output / "qualification-authorization.json").write_bytes(contract.canonical(authorization))
        artifact_name = "native-calibration.gcode" if route == "native-engine-v2" else "plate_1.gcode"
        artifact = output / artifact_name
        artifact.write_text("; TEST-ONLY, NEVER QUALIFICATION\n; " + contract.digest(request) + "\n", encoding="utf-8")
        warning = []
        if self.warning:
            warning = [{"level": 1, "message": "bed_temperature_too_high_than_filament",
                        "error_code": "1000C001", "params": [], "known": True, "requires_ack": True}]
        processing = {"error_code": 0, "warnings": warning, "status": "ready"}
        prepared = {key: request[key] for key in
                    ("request_id", "origin_id", "context_sha256", "calibration", "parameters")}
        data = artifact.read_bytes()
        prepared.update(
            schema="helix-orca-v1-prepared/v2", request_sha256=contract.digest(request),
            artifact={"name": artifact.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()},
            generator={"source_commit": contract.ORCA_SOURCE_V2, "route": route,
                       "executable_sha256": contract.ORCA_EXECUTABLE_SHA256_V2,
                       "qualification_sha256": qualification_sha,
                       "machine_sha256": contract.machine_sha256_v2(snapshot)},
            processing=processing)
        prepared = contract.validate_prepared_v2(prepared, request)
        for name, value in (("prepared.json", prepared),
                            ("invocation.json", {"test_only": True, "route": route}),
                            ("inputs.json", {"request_sha256": contract.digest(request)})):
            (output / name).write_bytes(contract.canonical(value))
        if route == "native-engine-v2":
            (output / "native-processing.json").write_bytes(contract.canonical(processing))
            (output / "native-generation.json").write_bytes(contract.canonical({
                "test_only": True, "artifact_sha256": prepared["artifact"]["sha256"]}))
            (output / "native-validation-warnings.json").write_bytes(contract.canonical([]))
            (output / "native-slicing-warnings.json").write_bytes(contract.canonical([]))
        return prepared


class QualificationVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.voron = self.root / "voron.json"
        self.ad5x = self.root / "ad5x.json"
        self.voron.write_bytes(contract.canonical(context("1", "Voron")))
        self.ad5x.write_bytes(contract.canonical(context("2", "AD5X", .6)))
        self.archive = self.root / "official.zip"
        self.executable = self.root / "OrcaSlicer.exe"
        self.resource = self.root / "resource.3mf"
        self.archive.write_bytes(b"TEST-ONLY archive")
        self.executable.write_bytes(b"TEST-ONLY executable")
        self.resource.write_bytes(b"TEST-ONLY resource")
        resource_sha = hashlib.sha256(self.resource.read_bytes()).hexdigest()
        self.config = self.root / "config.json"
        value = {
            "schema": qualify.CONFIG_SCHEMA,
            "generator": {"executable": str(self.executable),
                          "executable_sha256": contract.ORCA_EXECUTABLE_SHA256_V2},
            "case_overrides": {},
            "official_archive": {"path": str(self.archive), "sha256": "a" * 64},
            "adapter_files": [],
            "resource_files": [{"label": "test-resource", "path": str(self.resource),
                                "sha256": resource_sha}],
        }
        self.config.write_bytes(contract.canonical(value))

    def run_test_matrix(self, name="evidence", warning=False, acknowledged=frozenset()):
        output = self.root / name
        manifest, record = qualify.qualify(
            self.voron, self.ad5x, self.config, output, epoch=100,
            acknowledged_codes=acknowledged, case_runner=FakeFinalSlice(warning), test_only=True)
        self.assertIsNone(record)
        return output, manifest

    def rewrite_manifest(self, output, manifest):
        (output / "test-evidence.json").write_bytes(contract.canonical(manifest))

    def test_complete_matrix_exercises_finite_domains_but_cannot_emit_final_record(self):
        output, manifest = self.run_test_matrix()
        self.assertEqual(len(manifest["cases"]), 50)
        self.assertFalse(manifest["qualified"])
        self.assertFalse((output / "build-qualification.json").exists())
        public = json.dumps(manifest, sort_keys=True)
        self.assertNotIn("Voron PLA", public)
        self.assertNotIn("AD5X PLA", public)
        self.assertNotIn("TEST-ONLY, NEVER QUALIFICATION", public)
        self.assertNotIn(str(self.root), public)
        combinations = set()
        for context_name in contract.V2_QUALIFICATION_CONTEXTS:
            for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES:
                request = json.loads((output / "private/jobs" / context_name / "flow_ratio_yolo" /
                                      parameter_case / "qualification-request.json").read_text())
                combinations.add((request["parameters"]["pass"], request["parameters"]["pattern"]))
        self.assertEqual(combinations, {(1, "archimedean_chords"), (1, "monotonic"),
                                        (2, "archimedean_chords"), (2, "monotonic")})
        for context_name in contract.V2_QUALIFICATION_CONTEXTS:
            temp = json.loads((output / "private/jobs" / context_name / "temperature" /
                               "non_default_step/qualification-request.json").read_text())
            self.assertEqual(temp["parameters"]["step"], 5)
            self.assertFalse(temp["parameters"]["scale"])
            pa = json.loads((output / "private/jobs" / context_name / "pressure_advance_pattern" /
                             "upper_boundary/qualification-request.json").read_text())
            self.assertEqual(pa["parameters"], {"start": 1.9, "end": 2, "step": .1,
                                                "accelerations": [], "speeds": []})
            mvs = json.loads((output / "private/jobs" / context_name / "max_volumetric_speed" /
                              "lower_boundary/qualification-request.json").read_text())
            self.assertEqual(mvs["parameters"], {"start": .01, "end": 1.01, "step": 1})
        qualify.verify_evidence(output, allow_test=True)

        # A final record is accepted at ordinary runtime only while every
        # executing adapter/resource byte still matches the qualified closure.
        provenance = json.loads((output / "private/provenance.json").read_text())
        record_manifest = copy.deepcopy(manifest)
        record_manifest["platform"] = qualify.PLATFORM_LABEL
        build = qualify._build_record(record_manifest)
        closure = dict(schema=RUNTIME_CLOSURE_SCHEMA,
            adapter_files=provenance["adapter_files"],
            resource_files=provenance["resource_files"],
            package_manifest_sha256=None)
        runtime_config = dict(build_qualification=build, qualification_closure=closure)
        self.assertEqual(runtime_build_qualification(runtime_config), build)
        self.resource.write_bytes(b"changed after qualification")
        with self.assertRaisesRegex(contract.ContractError, "runtime closure file differs"):
            runtime_build_qualification(runtime_config)

    def test_installed_runtime_binds_every_adapter_to_the_verified_package(self):
        output, evidence = self.run_test_matrix("installed-binding")
        provenance = json.loads((output / "private/provenance.json").read_text())
        qualified = copy.deepcopy(evidence)
        qualified["platform"] = qualify.PLATFORM_LABEL
        build = qualify._build_record(qualified)

        def installed_package(name, changed=False):
            root = self.root / name
            files = []
            for index, item in enumerate(provenance["adapter_files"]):
                target = root / item["label"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(item["path"], target)
                if changed and index == 0:
                    target.write_bytes(target.read_bytes() + b"\n# package B differs\n")
                data = target.read_bytes()
                files.append({"path": item["label"], "size": len(data),
                              "sha256": hashlib.sha256(data).hexdigest()})
            manifest = {"schema": "helix-orca-v1-runtime-manifest/v1",
                        "candidate_sha256": ("b" if changed else "a") * 64,
                        "files": files}
            return root, manifest

        package_a, manifest_a = installed_package("package-a")
        closure = dict(schema=RUNTIME_CLOSURE_SCHEMA,
            adapter_files=provenance["adapter_files"],
            resource_files=provenance["resource_files"],
            package_manifest_sha256=contract.digest(manifest_a))
        config = dict(build_qualification=build, qualification_closure=closure)
        self.assertEqual(runtime_build_qualification(
            config, package_root=package_a, package_manifest=manifest_a), build)
        config[PACKAGE_BINDING_KEY] = {"root": str(package_a), "manifest": manifest_a}
        request = {"schema": "helix-orca-v1-request/v2", "calibration": "retraction"}
        with patch.object(routing.native, "generate",
                side_effect=lambda _request, _snapshot, _output, native_config:
                runtime_build_qualification(native_config)):
            self.assertEqual(routing.generate(request, {}, self.root / "routed", config), build)

        # The closure still names A's qualified bytes. Claiming B's manifest
        # cannot make runtime execute B while rehashing A at its old paths.
        package_b, manifest_b = installed_package("package-b", changed=True)
        config["qualification_closure"]["package_manifest_sha256"] = contract.digest(manifest_b)
        with self.assertRaisesRegex(contract.ContractError, "Installed package differs"):
            runtime_build_qualification(
                config, package_root=package_b, package_manifest=manifest_b)

    def test_verifier_rejects_changed_artifact_input_route_machine_and_partial_or_duplicate_cells(self):
        mutations = ("artifact", "input", "route", "machine", "partial", "duplicate")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                output, manifest = self.run_test_matrix(mutation)
                case = manifest["cases"][0]
                case_dir = output / "private/jobs" / case["context"] / case["calibration"] / case["parameter_case"]
                if mutation == "artifact":
                    prepared = json.loads((case_dir / "prepared.json").read_text())
                    (case_dir / prepared["artifact"]["name"]).write_text("changed")
                elif mutation == "input":
                    (case_dir / "inputs.json").write_text("{}")
                elif mutation == "route":
                    prepared = json.loads((case_dir / "prepared.json").read_text())
                    prepared["generator"]["route"] = ("native-engine-v2" if prepared["generator"]["route"] ==
                                                        "stock-cli-recipe-v2" else "stock-cli-recipe-v2")
                    (case_dir / "prepared.json").write_bytes(contract.canonical(prepared))
                elif mutation == "machine":
                    prepared = json.loads((case_dir / "prepared.json").read_text())
                    prepared["generator"]["machine_sha256"] = "f" * 64
                    (case_dir / "prepared.json").write_bytes(contract.canonical(prepared))
                elif mutation == "partial":
                    manifest["cases"].pop()
                    self.rewrite_manifest(output, manifest)
                else:
                    manifest["cases"][-1] = copy.deepcopy(manifest["cases"][0])
                    self.rewrite_manifest(output, manifest)
                with self.assertRaises((qualify.QualificationError, contract.ContractError)):
                    qualify.verify_evidence(output, allow_test=True)

    def test_known_warning_needs_explicit_acknowledgement(self):
        with self.assertRaisesRegex(qualify.QualificationError, "explicitly acknowledged"):
            self.run_test_matrix("warning-rejected", warning=True)
        output, manifest = self.run_test_matrix(
            "warning-accepted", warning=True, acknowledged=frozenset({"1000C001"}))
        self.assertTrue(all(case["warning_codes"] == ["1000C001"] for case in manifest["cases"]))
        qualify.verify_evidence(output, allow_test=True)

    def test_intent_is_distinct_exact_one_shot_and_no_runtime_or_action_authority(self):
        original = context("1", "Voron")
        parameters = contract.default_parameters_v2(original)["temperature"]
        request = contract.validate_request_v2({
            "schema": "helix-orca-v1-request/v2", "request_id": "3" * 32,
            "origin_id": original["origin_id"], "context_sha256": contract.digest(original),
            "calibration": "temperature", "parameters": parameters,
            "created_at": 100, "expires_at": 200,
        }, now=150)
        output = self.root / "one-shot"
        intent = {
            "schema": contract.V2_QUALIFICATION_INTENT_SCHEMA, "case_id": "4" * 64,
            "source_commit": contract.ORCA_SOURCE_V2, "runtime": contract.ORCA_RUNTIME_V2,
            "executable_sha256": contract.ORCA_EXECUTABLE_SHA256_V2,
            "adapter_sha256": "1" * 64, "resources_sha256": "2" * 64,
            "context_sha256": contract.digest(original),
            "machine_sha256": contract.machine_sha256_v2(original),
            "request_sha256": contract.digest(request), "calibration": "temperature",
            "parameters_sha256": contract.digest(parameters), "route_id": "stock-cli-recipe-v2",
            "output_sha256": contract._output_sha256_v2(output),
            "final_slice_path": contract.V2_FINAL_SLICE_PATH,
            "generation_only": True, "one_shot": True,
        }
        with self.assertRaises(contract.ContractError):
            contract.validate_build_qualification_v2(intent)
        with self.assertRaises(contract.ContractError):
            v1_jobs.current_candidate_verifier(intent, lambda: intent)
        for value in ({"qualification_intent": intent},
                      {"qualification_intent": intent, "qualification_authorizer": "not callable"}):
            with self.assertRaises(contract.ContractError):
                contract.authorize_qualification_generation_v2(
                    value, request, original, "stock-cli-recipe-v2", output)
        gate = qualify.OneShotAuthorizer(intent)
        digest_value, receipt = contract.authorize_qualification_generation_v2(
            {"qualification_intent": intent, "qualification_authorizer": gate}, request, original,
            "stock-cli-recipe-v2", output)
        self.assertEqual(digest_value, contract.digest(intent))
        self.assertTrue(receipt["generation_only"])
        with self.assertRaises(qualify.QualificationError):
            contract.authorize_qualification_generation_v2(
                {"qualification_intent": intent, "qualification_authorizer": gate}, request, original,
                "stock-cli-recipe-v2", output)
        wrong = qualify.OneShotAuthorizer(dict(intent, case_id="5" * 64))
        with self.assertRaises(qualify.QualificationError):
            contract.authorize_qualification_generation_v2(
                {"qualification_intent": intent, "qualification_authorizer": wrong}, request, original,
                "stock-cli-recipe-v2", output)

    def test_fixture_hash_non_pe_and_changed_provenance_are_rejected(self):
        with self.assertRaisesRegex(qualify.QualificationError, "Synthetic fixture"):
            qualify._not_fixture_digest("a" * 64, "adapter")
        with self.assertRaisesRegex(qualify.QualificationError, "not PE"):
            qualify._validate_pe_x64(self.executable)
        output, _ = self.run_test_matrix("changed-provenance")
        self.resource.write_bytes(b"changed")
        with self.assertRaisesRegex(qualify.QualificationError, "digest differs"):
            qualify.verify_evidence(output, allow_test=True)

    def test_configured_input_and_output_symlinks_are_rejected_before_generation(self):
        linked_resource = self.root / "linked-resource.3mf"
        linked_resource.symlink_to(self.resource)
        value = json.loads(self.config.read_text())
        value["resource_files"][0]["path"] = str(linked_resource)
        linked_config = self.root / "linked-config.json"
        linked_config.write_bytes(contract.canonical(value))
        with self.assertRaisesRegex(qualify.QualificationError, "symlink path"):
            qualify.qualify(self.voron, self.ad5x, linked_config, self.root / "linked-input-output",
                            epoch=100, case_runner=FakeFinalSlice(), test_only=True)

        linked_executable = self.root / "linked-OrcaSlicer.exe"
        linked_executable.symlink_to(self.executable)
        value = json.loads(self.config.read_text())
        value["generator"]["executable"] = str(linked_executable)
        linked_executable_config = self.root / "linked-executable-config.json"
        linked_executable_config.write_bytes(contract.canonical(value))
        with self.assertRaisesRegex(qualify.QualificationError, "symlink path"):
            qualify.qualify(self.voron, self.ad5x, linked_executable_config,
                            self.root / "linked-executable-output", epoch=100,
                            case_runner=FakeFinalSlice(), test_only=True)

        target = self.root / "real-output"
        target.mkdir()
        linked_output = self.root / "linked-output"
        linked_output.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(qualify.QualificationError, "symlink path"):
            qualify.qualify(self.voron, self.ad5x, self.config, linked_output,
                            epoch=100, case_runner=FakeFinalSlice(), test_only=True)

        verified_output, _ = self.run_test_matrix("verified-output")
        linked_verified_output = self.root / "linked-verified-output"
        linked_verified_output.symlink_to(verified_output, target_is_directory=True)
        with self.assertRaisesRegex(qualify.QualificationError, "symlink path"):
            qualify.verify_evidence(linked_verified_output, allow_test=True)


if __name__ == "__main__":
    unittest.main()
