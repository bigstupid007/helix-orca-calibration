import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest

from integration import v1_contract as contract
from integration import v1_engine
from integration import v1_generation
from integration.v1_runtime import Coordinator, atomic_json, read_json
from integration.v1_transport import DirectoryEvents
import test_plugin

ROOT = Path(__file__).resolve().parents[1]


def context():
    value = dict(schema="helix-orca-v1-context/v2", origin_id="1" * 32,
        runtime=dict(contract.ORCA_RUNTIME_V2, source_commit=contract.ORCA_SOURCE_V2,
                     executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2),
        nozzle_mm=.4, effective={"filament_flow_ratio": "0.8;1.2", "nozzle_diameter": "0.4;0.4"},
        filament_slots=[dict(slot_number=1, preset_name="AD5X PLA"),
                        dict(slot_number=2, preset_name="AD5X PLA")],
        origin_filament=dict(slot_number=2, preset_name="AD5X PLA", shared_slots=[1, 2]))
    for role in ("printer", "process", "filament"):
        name = "AD5X PLA" if role == "filament" else role.title()
        value[role] = {kind: dict(name=name, config={"fixture": kind}) for kind in ("saved", "edited")}
    return contract.validate_context_v2(value)


def request(original, calibration="pressure_advance_pattern"):
    return contract.validate_request_v2(dict(schema="helix-orca-v1-request/v2",
        request_id="2" * 32, origin_id=original["origin_id"], context_sha256=contract.digest(original),
        calibration=calibration, parameters=contract.V2_DEFAULTS[calibration], created_at=100, expires_at=200), now=150)


def qualification():
    coverage = [dict(context=context_name, parameter_case=parameter_case,
                     case_sha256=hashlib.sha256((context_name + ":" + parameter_case).encode()).hexdigest())
                for context_name in contract.V2_QUALIFICATION_CONTEXTS
                for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES]
    def route(kind):
        return dict(qualified=True,
            route_id=("stock-cli-recipe-v2" if kind in ("temperature", "flow_ratio_yolo") else "native-engine-v2"),
            case_count=len(coverage), cases_sha256=contract.digest(coverage), coverage=coverage,
            final_slice_path=["Print.process", "Print.export_gcode"])
    return contract.validate_build_qualification_v2(dict(schema="helix-orca-v1-build-qualification/v2",
        source_commit=contract.ORCA_SOURCE_V2, runtime=contract.ORCA_RUNTIME_V2,
        platform="Windows x86_64 exact job 121250255545; mixed-conclusion upstream run 40220020944",
        distribution=dict(archive_sha256=contract.ORCA_ARCHIVE_SHA256_V2,
                          executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2),
        upstream=dict(run_id=contract.ORCA_UPSTREAM_RUN_V2, overall_conclusion="failure",
            sole_failed_job="build_macos_arch (arm64) / Check Cache",
            exact_jobs={name: dict(job_id=job_id, conclusion="success")
                        for name, job_id in contract.ORCA_UPSTREAM_JOBS_V2.items()}),
        adapter=dict(sha256="4" * 64), resources_sha256="5" * 64,
        routes={kind: route(kind) for kind in contract.CALIBRATIONS}, evidence_sha256="6" * 64,
        qualified=True))


def prepared(req, build, warnings=None):
    warnings = [] if warnings is None else warnings
    value = {key: req[key] for key in ("request_id", "origin_id", "context_sha256", "calibration", "parameters")}
    value.update(schema="helix-orca-v1-prepared/v2", request_sha256=contract.digest(req),
        artifact=dict(name="exact-job.gcode", size=123, sha256="7" * 64),
        generator=dict(source_commit=contract.ORCA_SOURCE_V2, route="native-engine-v2",
                       executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2,
                       qualification_sha256=contract.digest(build),
                       machine_sha256=contract.machine_sha256_v2(context())),
        processing=dict(error_code=0, warnings=warnings,
                        status="ready" if all(item["known"] for item in warnings) else "blocked"))
    return contract.validate_prepared_v2(value, req)


class FakeTransaction:
    def __init__(self, editor, slot, name):
        self.editor, self.slot, self.name, self.staged = editor, slot, name, []

    def set(self, key, value):
        self.staged.append((key, value))

    def commit(self):
        self.editor.commits += 1
        if self.editor.fail_commit:
            raise RuntimeError("unobserved test commit")
        keys = [key for key, _ in self.staged]
        return type("Outcome", (), dict(category="filament", target_name=self.name,
            selection_changed=False, slot_number=self.slot, slot_assignment_changed=False,
            shared_slots=[1, 2], keys=keys, dirty=True))()


class FakeEditor:
    def __init__(self, fail_commit=False):
        self.fail_commit, self.commits, self.bindings = fail_commit, 0, []

    def begin_update(self, *, slot_number, preset_name):
        self.bindings.append((slot_number, preset_name))
        return FakeTransaction(self, slot_number, preset_name)


class V2ContractApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("v2_companion_builder", ROOT / "scripts/v1-companion.py")
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def load_plugin(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "helix_calibration.py"
        path.write_text(self.builder.generate(), encoding="utf-8", newline="\n")
        previous = test_plugin.PLUGIN_PATH
        test_plugin.PLUGIN_PATH = path
        try:
            return test_plugin.load_plugin()[0]
        finally:
            test_plugin.PLUGIN_PATH = previous

    def inbox(self, root, warning=False, parameters=None, result_value=.04):
        original, build = context(), qualification()
        req = request(original)
        if parameters is not None:
            req["parameters"] = parameters
            req = contract.validate_request_v2(req, now=150)
        warning_value = []
        if warning:
            warning_value = [contract.validate_warning_v2(dict(level=3,
                message="bed_temperature_too_high_than_filament", error_code="1000C001",
                params=["100", "60"], known=True, requires_ack=True))]
        prep = prepared(req, build, warning_value)
        proof = dict(job_id="owned", file_sha256=prep["artifact"]["sha256"], print_state="complete",
                     history_state="completed", history_job_id="owned",
                     history_file_sha256=prep["artifact"]["sha256"])
        result = dict(schema="helix-orca-v1-result/v2", request_id=req["request_id"],
            origin_id=req["origin_id"], context_sha256=req["context_sha256"],
            prepared_sha256=contract.digest(prep), job_id="owned",
            completion_sha256=contract.digest(proof), setting="pressure_advance", value=result_value)
        ack = None
        if warning:
            ack = dict(schema="helix-orca-v1-warning-ack/v2", request_id=req["request_id"],
                       prepared_sha256=contract.digest(prep), warning_codes=["1000C001"], acknowledged_at=160)
        (root / "origins").mkdir()
        return original, dict(result=result, request=req, prepared=prep, completion=proof,
                              warning_ack=ack, qualification=build)

    def test_v2_contract_carries_explicit_shared_origin_and_native_parameters(self):
        original = context()
        self.assertEqual(original["origin_filament"],
                         dict(slot_number=2, preset_name="AD5X PLA", shared_slots=[1, 2]))
        flow = contract.validate_parameters_v2("flow_ratio_yolo", {"pass": 2, "pattern": "monotonic"})
        self.assertEqual(flow["pattern"], "monotonic")
        pa = contract.validate_parameters_v2("pressure_advance_pattern",
            {"start": 0, "end": .1, "step": .01, "accelerations": [1000, 2000], "speeds": [100, 200]})
        self.assertEqual(pa["accelerations"], [1000, 2000])
        with self.assertRaisesRegex(contract.ContractError, "exceed"):
            contract.validate_parameters_v2("pressure_advance_pattern",
                {"start": 0, "end": .1, "step": .01, "accelerations": [100], "speeds": [200]})
        with self.assertRaisesRegex(contract.ContractError, "2.0"):
            contract.validate_parameters_v2("pressure_advance_pattern",
                {"start": 1.9, "end": 2.1, "step": .1, "accelerations": [], "speeds": []})
        self.assertEqual(contract.validate_parameters_v2("retraction",
            {"start": 0, "end": .002, "step": .0005}),
            {"start": 0, "end": .002, "step": .0005})
        self.assertEqual(contract.validate_parameters_v2("max_volumetric_speed",
            {"start": .005, "end": .015, "step": .005}),
            {"start": .005, "end": .015, "step": .005})
        with self.assertRaisesRegex(contract.ContractError, "greater than zero"):
            contract.validate_parameters_v2("max_volumetric_speed",
                {"start": 0, "end": .01, "step": .005})

        many = request(original, "retraction")
        many["parameters"] = {"start": 0, "end": 1, "step": .0005}
        many = contract.validate_request_v2(many, now=150)
        evaluation = contract.evaluation_v2(many, original)
        self.assertEqual(set(evaluation), {"setting", "range", "unit"})
        self.assertEqual(evaluation["range"], {"start": 0.0, "end": 1.0, "step": .0005})
        self.assertEqual(contract.evaluation_value_v2(evaluation, .8475), .8475)
        with self.assertRaisesRegex(contract.ContractError, "outside"):
            contract.evaluation_value_v2(evaluation, .8476)

        pa_ceiling = request(original, "pressure_advance_pattern")
        pa_ceiling["parameters"] = {"start": 0, "end": .095, "step": .02,
                                    "accelerations": [], "speeds": []}
        pa_ceiling = contract.validate_request_v2(pa_ceiling, now=150)
        pa_evaluation = contract.evaluation_v2(pa_ceiling, original)
        self.assertEqual(pa_evaluation["options"], [0.0, .02, .04, .06, .08, .1])
        self.assertEqual(contract.evaluation_value_v2(pa_evaluation, .1), .1)
        with self.assertRaisesRegex(contract.ContractError, "outside"):
            contract.evaluation_value_v2(pa_evaluation, .095)

        build = qualification()
        build["routes"]["temperature"]["coverage"].pop()
        build["routes"]["temperature"]["case_count"] -= 1
        build["routes"]["temperature"]["cases_sha256"] = contract.digest(
            build["routes"]["temperature"]["coverage"])
        with self.assertRaisesRegex(contract.ContractError, "Voron and AD5X"):
            contract.validate_build_qualification_v2(build)
        invalid_prepared = prepared(request(original), qualification())
        invalid_prepared["generator"]["route"] = "arbitrary-route"
        with self.assertRaisesRegex(contract.ContractError, "route"):
            contract.validate_prepared_v2(invalid_prepared, request(original))
        self.assertEqual(v1_generation._origin_numeric(original, "filament_flow_ratio"), 1.2)
        flow_request = request(original, "flow_ratio_yolo")
        selected = contract.flow_ratio_choices("1.2", 1)[0]
        updates = self.load_plugin().v2_application_updates(
            flow_request, {"setting": "filament_flow_ratio", "value": selected}, original)
        self.assertEqual(updates, [("filament_flow_ratio", str(selected))])

    def test_native_wrapper_requires_uniform_v2_nozzle_vector(self):
        original = context()
        self.assertEqual(v1_engine._validated_effective_nozzle(original, True), .4)
        original["effective"]["nozzle_diameter"] = "0.4;0.6"
        with self.assertRaisesRegex(v1_engine.NativeEngineBlocked, "vector differs"):
            v1_engine._validated_effective_nozzle(original, True)
        legacy = {"nozzle_mm": .4, "effective": {"nozzle_diameter": "0.4"}}
        self.assertEqual(v1_engine._validated_effective_nozzle(legacy, False), .4)
        legacy["effective"]["nozzle_diameter"] = "0.4;0.4"
        with self.assertRaisesRegex(v1_engine.NativeEngineBlocked, "single nozzle"):
            v1_engine._validated_effective_nozzle(legacy, False)

    def test_coordinator_uses_build_qualification_and_persists_warning_ack(self):
        original, build = context(), qualification()
        warning = contract.validate_warning_v2(dict(level=3,
            message="bed_temperature_too_high_than_filament", error_code="1000C001",
            params=["100", "60"], known=True, requires_ack=True))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def generate(req, snapshot, directory, config):
                artifact = directory / "exact-job.gcode"
                artifact.write_bytes(b"G90\n")
                value = {key: req[key] for key in ("request_id", "origin_id", "context_sha256", "calibration", "parameters")}
                value.update(schema="helix-orca-v1-prepared/v2", request_sha256=contract.digest(req),
                    artifact=dict(name=artifact.name, size=4, sha256=hashlib.sha256(b"G90\n").hexdigest()),
                    generator=dict(source_commit=contract.ORCA_SOURCE_V2, route="native-engine-v2",
                        executable_sha256=contract.ORCA_EXECUTABLE_SHA256_V2,
                        qualification_sha256=contract.digest(build),
                        machine_sha256=contract.machine_sha256_v2(snapshot)),
                    processing=dict(error_code=0, warnings=[warning], status="ready"))
                return value
            runtime = Coordinator(root, generate, dict(build_qualification=build),
                                  [dict(id=kind, available=True, reason="qualified") for kind in contract.CALIBRATIONS],
                                  now=lambda: 100)
            offer = runtime.offer(original)
            req = dict(schema="helix-orca-v1-request/v2", request_id=offer["request_id"],
                origin_id=offer["origin_id"], context_sha256=offer["context_sha256"],
                calibration="pressure_advance_pattern", parameters=contract.V2_DEFAULTS["pressure_advance_pattern"],
                created_at=offer["created_at"], expires_at=offer["expires_at"])
            self.assertEqual(runtime.request(req)["phase"], "warning")
            prep = runtime.state["prepared"]
            ack = dict(schema="helix-orca-v1-warning-ack/v2", request_id=req["request_id"],
                       prepared_sha256=contract.digest(prep), warning_codes=["1000C001"], acknowledged_at=101)
            runtime.acknowledge_warnings(ack)
            self.assertEqual(runtime.status()["warning_ack"], ack)
            self.assertEqual(runtime.acknowledge_warnings(ack), ack)
            recovered = Coordinator(root, generate, dict(build_qualification=build),
                                    [dict(id=kind, available=True, reason="qualified")
                                     for kind in contract.CALIBRATIONS], now=lambda: 100)
            self.assertEqual(recovered.status()["warning_ack"], ack)
            intent = dict(schema="helix-orca-v1-intent/v2", request_id=req["request_id"],
                          origin_id=req["origin_id"], prepared_sha256=contract.digest(prep),
                          action="confirm", intent_id="8" * 32)
            self.assertEqual(runtime.intent(intent)["phase"], "confirmed")
            self.assertFalse((root / "jobs" / req["request_id"] / "parity.json").exists())

    def test_prepared_wrong_machine_is_refused_before_action_transport(self):
        original, build = context(), qualification()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def generate(req, snapshot, directory, config):
                artifact = directory / "exact-job.gcode"
                artifact.write_bytes(b"G90\n")
                value = prepared(req, build)
                value["artifact"] = dict(name=artifact.name, size=4,
                    sha256=hashlib.sha256(b"G90\n").hexdigest())
                value["generator"]["machine_sha256"] = "f" * 64
                return value
            runtime = Coordinator(root, generate, dict(build_qualification=build),
                [dict(id=kind, available=True, reason="qualified") for kind in contract.CALIBRATIONS],
                now=lambda: 100)
            offer = runtime.offer(original)
            req = dict(schema="helix-orca-v1-request/v2", request_id=offer["request_id"],
                origin_id=offer["origin_id"], context_sha256=offer["context_sha256"],
                calibration="pressure_advance_pattern",
                parameters=contract.V2_DEFAULTS["pressure_advance_pattern"],
                created_at=offer["created_at"], expires_at=offer["expires_at"])
            status = runtime.request(req)
            self.assertEqual(status["phase"], "blocked")
            self.assertIn("immutable machine context", status["message"])
            self.assertIsNone(runtime.state["prepared"])

    def test_warning_cancel_is_a_v2_prestart_terminal_action(self):
        original, build = context(), qualification()
        warning = contract.validate_warning_v2(dict(level=3,
            message="bed_temperature_too_high_than_filament", error_code="1000C001",
            params=["100", "60"], known=True, requires_ack=True))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def generate(req, snapshot, directory, config):
                artifact = directory / "exact-job.gcode"; artifact.write_bytes(b"G90\n")
                value = prepared(req, build, [warning])
                value["artifact"] = dict(name=artifact.name, size=4,
                                         sha256=hashlib.sha256(b"G90\n").hexdigest())
                return value
            runtime = Coordinator(root, generate, dict(build_qualification=build),
                [dict(id=kind, available=True, reason="qualified") for kind in contract.CALIBRATIONS],
                now=lambda: 100)
            offer = runtime.offer(original)
            req = dict(schema="helix-orca-v1-request/v2", request_id=offer["request_id"],
                origin_id=offer["origin_id"], context_sha256=offer["context_sha256"],
                calibration="pressure_advance_pattern", parameters=contract.V2_DEFAULTS["pressure_advance_pattern"],
                created_at=offer["created_at"], expires_at=offer["expires_at"])
            runtime.request(req)
            prompt = runtime.warning_event()
            decision = dict(schema="helix-orca-v1-native-warning-decision/v2",
                **{key: prompt[key] for key in
                   ("request_id", "origin_id", "prepared_sha256", "warning_sha256", "warning_codes")},
                action="cancel", intent_id="d" * 32)
            intent = dict(schema="helix-orca-v1-intent/v2", request_id=req["request_id"],
                origin_id=req["origin_id"], prepared_sha256=contract.digest(runtime.state["prepared"]),
                action="cancel", intent_id="c" * 32)
            spec = importlib.util.spec_from_file_location("v1_runtime_cancel_cli", ROOT / "scripts/v1-runtime.py")
            cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
            channel = DirectoryEvents(root / "channel")
            calls, invoke = [], runtime.intent
            def counted(value):
                calls.append(value)
                return invoke(value)
            runtime.intent = counted
            atomic_json(channel.directory / "native.json",
                        {"v2": {"warning": {"decision": decision}}, "intent": intent})
            cli.tick(runtime, root / "storage", channel)
            self.assertEqual(runtime.state["phase"], "cancelled")
            self.assertEqual([value["intent_id"] for value in calls], ["c" * 32])
            self.assertIsNone(runtime.state["job"])

    def test_pa_applies_two_keys_atomically_to_origin_slot_without_save(self):
        plugin = self.load_plugin()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, inbox = self.inbox(root, warning=True,
                parameters={"start": 0, "end": .095, "step": .02,
                            "accelerations": [], "speeds": []}, result_value=.1)
            plugin.v1_write(root / "origins" / (original["origin_id"] + ".json"), original)
            plugin.v1_write(root / "inbox.json", inbox)
            editor = FakeEditor()
            state = plugin.v2_apply_inbox(root, editor, now=170)
            self.assertEqual(state["status"], "applied")
            self.assertEqual(editor.bindings, [(2, "AD5X PLA")])
            self.assertEqual(state["updates"], [dict(key="enable_pressure_advance", value="1"),
                                                dict(key="pressure_advance", value="0.1")])
            self.assertEqual(state["outcome"]["shared_slots"], [1, 2])
            self.assertTrue(state["outcome"]["dirty"])
            self.assertEqual(editor.commits, 1)
            self.assertEqual(plugin.v2_apply_inbox(root, editor, now=180), state)
            self.assertEqual(editor.commits, 1)

    def test_two_sequential_calibrations_rotate_applied_state_and_apply_exact_second_result(self):
        plugin = self.load_plugin()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, first = self.inbox(root)
            plugin.v1_write(root / "origins" / (original["origin_id"] + ".json"), original)
            plugin.v1_write(root / "inbox.json", first)
            editor = FakeEditor()
            applied_first = plugin.v2_apply_inbox(root, editor, now=170)
            self.assertEqual(applied_first["request_id"], "2" * 32)

            build = first["qualification"]
            second_request = contract.validate_request_v2(dict(
                schema="helix-orca-v1-request/v2", request_id="3" * 32,
                origin_id=original["origin_id"], context_sha256=contract.digest(original),
                calibration="retraction", parameters=contract.V2_DEFAULTS["retraction"],
                created_at=101, expires_at=201), now=150)
            second_prepared = prepared(second_request, build)
            second_proof = dict(job_id="owned-second",
                file_sha256=second_prepared["artifact"]["sha256"], print_state="complete",
                history_state="completed", history_job_id="owned-second",
                history_file_sha256=second_prepared["artifact"]["sha256"])
            second_result = dict(schema="helix-orca-v1-result/v2",
                request_id=second_request["request_id"], origin_id=second_request["origin_id"],
                context_sha256=second_request["context_sha256"],
                prepared_sha256=contract.digest(second_prepared), job_id="owned-second",
                completion_sha256=contract.digest(second_proof),
                setting="filament_retraction_length", value=.5)
            plugin.v1_write(root / "inbox.json", dict(
                result=second_result, request=second_request, prepared=second_prepared,
                completion=second_proof, warning_ack=None, qualification=build))
            applied_second = plugin.v2_apply_inbox(root, editor, now=180)

            self.assertEqual(applied_second["request_id"], "3" * 32)
            self.assertEqual(applied_second["updates"], [
                dict(key="filament_retraction_length", value="0.5")])
            self.assertEqual(editor.commits, 2)
            history = list((root / "application-history").glob("*.json"))
            self.assertEqual(len(history), 1)
            self.assertEqual(plugin.v1_read(history[0]), applied_first)
            self.assertEqual(plugin.v1_read(root / "receipt.json")["request_id"], "3" * 32)

    def test_commit_exception_is_failed_and_only_explicit_result_bound_retry_runs(self):
        plugin = self.load_plugin()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, inbox = self.inbox(root)
            plugin.v1_write(root / "origins" / (original["origin_id"] + ".json"), original)
            plugin.v1_write(root / "inbox.json", inbox)
            editor = FakeEditor(fail_commit=True)
            with self.assertRaisesRegex(RuntimeError, "unobserved"):
                plugin.v2_apply_inbox(root, editor, now=170)
            state = json.loads((root / "application.json").read_text())
            self.assertEqual((state["status"], state["phase"]), ("failed", "commit_rolled_back"))
            with self.assertRaisesRegex(ValueError, "explicit result-bound retry"):
                plugin.v2_apply_inbox(root, editor, now=180)
            self.assertEqual(editor.commits, 1)
            retry = dict(schema="helix-orca-v1-application-retry/v2", request_id=state["request_id"],
                         origin_id=state["origin_id"],
                         result_sha256=state["result_sha256"], failed_application_sha256=plugin.digest(state),
                         attempt=2, token="9" * 32, authorized_at=181)
            plugin.v1_write(root / "application-retry.json", retry)
            editor.fail_commit = False
            applied = plugin.v2_apply_inbox(root, editor, now=182)
            self.assertEqual((applied["status"], applied["attempt"]), ("applied", 2))
            self.assertEqual(editor.commits, 2)
            self.assertTrue((root / "application-retry-consumed.json").is_file())

    def test_worker_auto_applies_initial_result_without_owner_relay(self):
        plugin = self.load_plugin()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, inbox = self.inbox(root)
            plugin.v1_write(root / "origins" / (original["origin_id"] + ".json"), original)
            plugin.v1_write(root / "inbox.json", inbox)
            editor = FakeEditor()
            plugin.orca.host.plugin = types.SimpleNamespace(storage=lambda: root.parent)
            # v1_storage appends its ordinary owner-local v1 directory.
            directory = root.parent / "v1"
            if directory != root:
                plugin.orca.host.plugin = types.SimpleNamespace(storage=lambda: Path(temporary))
                directory = Path(temporary) / "v1"
                directory.mkdir()
                for name in ("origins",):
                    (directory / name).mkdir(exist_ok=True)
                plugin.v1_write(directory / "origins" / (original["origin_id"] + ".json"), original)
                plugin.v1_write(directory / "inbox.json", inbox)
            plugin.orca.host.preset = types.SimpleNamespace(filament=editor)
            panel = plugin.V2CalibrationPanel()
            worker = threading.Thread(target=panel.execute)
            worker.start()
            deadline = time.time() + 3
            while time.time() < deadline:
                state = plugin.v1_read(directory / "application.json")
                if state and state.get("status") == "applied":
                    break
                time.sleep(.02)
            panel.on_close()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(plugin.v1_read(directory / "application.json")["status"], "applied")
            self.assertEqual(editor.commits, 1)

    def test_only_returned_coordinator_retry_runs_and_uncertain_cannot_retry(self):
        plugin = self.load_plugin()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, inbox = self.inbox(root)
            plugin.v1_write(root / "origins" / (original["origin_id"] + ".json"), original)
            plugin.v1_write(root / "inbox.json", inbox)
            editor = FakeEditor(fail_commit=True)
            with self.assertRaises(RuntimeError):
                plugin.v2_apply_inbox(root, editor, now=170)
            failed = plugin.v1_read(root / "application.json")
            retry = dict(schema="helix-orca-v1-application-retry/v2",
                         request_id=failed["request_id"], origin_id=failed["origin_id"],
                         result_sha256=failed["result_sha256"],
                         failed_application_sha256=plugin.digest(failed), attempt=2,
                         token="a" * 32, authorized_at=171)
            plugin.v1_write(root / "application-retry.json", retry)
            editor.fail_commit = False
            self.assertEqual(plugin.v2_apply_inbox(root, editor, now=172)["status"], "applied")

            uncertain = plugin.v1_read(root / "application.json")
            uncertain.update(status="uncertain", phase="unexpected_outcome")
            plugin.v1_write(root / "application.json", uncertain)
            with self.assertRaisesRegex(ValueError, "uncertain; no retry"):
                plugin.v2_apply_inbox(root, editor, now=173)

    def test_v2_receipt_requires_exact_current_applied_transaction(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Coordinator(Path(temporary), lambda *_: None, {}, [], now=lambda: 100)
            result = dict(request_id="2" * 32, origin_id="1" * 32, value=.04)
            runtime.state["request"] = {"schema": "helix-orca-v1-request/v2"}
            runtime.state["result"] = result
            receipt = dict(schema="helix-orca-v1-ack/v2", request_id=result["request_id"],
                origin_id=result["origin_id"], result_sha256=contract.digest(result),
                application_sha256="a" * 64, status="applied")
            for state in ("failed", "uncertain"):
                runtime.state["application_digest"] = "a" * 64
                runtime.state["application_event"] = dict(
                    state=state, transaction_id="", dirty=False, unsaved=False)
                with self.subTest(state=state), self.assertRaisesRegex(
                        contract.ContractError, "exact originating preset application"):
                    runtime.acknowledge(receipt)
            runtime.state["application_event"] = dict(
                state="applied", transaction_id="a" * 64, dirty=True, unsaved=True)
            with self.assertRaisesRegex(contract.ContractError, "exact originating preset application"):
                runtime.acknowledge(dict(receipt, application_sha256="b" * 64))
            self.assertEqual(runtime.acknowledge(receipt), receipt)
            self.assertEqual(runtime.state["phase"], "delivered")

    def test_tick_bridge_warning_result_failed_retry_applied_and_ack(self):
        plugin = self.load_plugin()
        spec = importlib.util.spec_from_file_location("v2_runtime_tick", ROOT / "scripts/v1-runtime.py")
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        original, build = context(), qualification()
        warning = contract.validate_warning_v2(dict(level=3,
            message="bed_temperature_too_high_than_filament", error_code="1000C001",
            params=["100", "60"], known=True, requires_ack=True))
        class Adapter:
            def confirm(self, *_): pass
            def start(self, req, prep, directory, intent):
                return dict(job_id="owned", file_sha256=prep["artifact"]["sha256"],
                            request_id=req["request_id"], origin_id=req["origin_id"])
            def observe(self, job):
                return dict(job_id="owned", file_sha256=job["file_sha256"], print_state="complete",
                            history_state="completed", history_job_id="owned",
                            history_file_sha256=job["file_sha256"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); storage = root / "storage"; storage.mkdir()
            channel = DirectoryEvents(root / "channel")
            def generate(req, snapshot, directory, config):
                artifact = directory / "exact-job.gcode"; artifact.write_bytes(b"G90\n")
                value = prepared(req, build, [warning])
                value["artifact"] = dict(name=artifact.name, size=4,
                                         sha256=hashlib.sha256(b"G90\n").hexdigest())
                return value
            runtime = Coordinator(root / "runtime", generate, dict(build_qualification=build),
                [dict(id=kind, available=True, reason="qualified") for kind in contract.CALIBRATIONS],
                now=lambda: 100, job_adapter=Adapter())
            atomic_json(storage / "context.json", original); cli.tick(runtime, storage, channel)
            offer = read_json(channel.directory / "context.json")
            req = dict(schema="helix-orca-v1-request/v2", request_id=offer["request_id"],
                origin_id=offer["origin_id"], context_sha256=offer["context_sha256"],
                calibration="pressure_advance_pattern", parameters=contract.V2_DEFAULTS["pressure_advance_pattern"],
                created_at=offer["created_at"], expires_at=offer["expires_at"])
            atomic_json(channel.directory / "native.json", {"request": req}); cli.tick(runtime, storage, channel)
            prompt = read_json(channel.directory / "warning.json")
            decision = dict(schema="helix-orca-v1-native-warning-decision/v2",
                **{key: prompt[key] for key in ("request_id", "origin_id", "prepared_sha256", "warning_sha256", "warning_codes")},
                action="continue", intent_id="d" * 32)
            synthetic_ack = dict(schema="helix-orca-v1-warning-ack/v2",
                request_id=req["request_id"], prepared_sha256=prompt["prepared_sha256"],
                warning_codes=prompt["warning_codes"], acknowledged_at=0)
            atomic_json(channel.directory / "native.json",
                        {"v2": {"warning": {"decision": decision}}, "warning_ack": synthetic_ack})
            cli.tick(runtime, storage, channel); self.assertEqual(runtime.state["phase"], "review")
            self.assertEqual(runtime.state["warning_ack"]["acknowledged_at"], 100)
            base = dict(schema="helix-orca-v1-intent/v2", request_id=req["request_id"], origin_id=req["origin_id"],
                        prepared_sha256=contract.digest(runtime.state["prepared"]))
            atomic_json(channel.directory / "native.json", {"intent": dict(base, action="confirm", intent_id="e" * 32)})
            cli.tick(runtime, storage, channel); self.assertEqual(runtime.state["phase"], "confirmed")
            atomic_json(channel.directory / "native.json", {"intent": dict(base, action="start", intent_id="f" * 32)})
            cli.tick(runtime, storage, channel); self.assertEqual(runtime.state["phase"], "complete")
            result = dict(schema="helix-orca-v1-result/v2", request_id=req["request_id"],
                origin_id=req["origin_id"], context_sha256=req["context_sha256"],
                prepared_sha256=contract.digest(runtime.state["prepared"]), job_id="owned",
                completion_sha256=contract.digest(runtime.state["completion"]),
                setting="pressure_advance", value=.04)
            atomic_json(channel.directory / "native.json", {"result": result}); cli.tick(runtime, storage, channel)
            (storage / "origins").mkdir()
            plugin.v1_write(storage / "origins" / (original["origin_id"] + ".json"), original)
            editor = FakeEditor(fail_commit=True)
            with self.assertRaises(RuntimeError): plugin.v2_apply_inbox(storage, editor, now=101)
            atomic_json(channel.directory / "native.json", {}); cli.tick(runtime, storage, channel)
            failed = read_json(channel.directory / "application.json")
            self.assertEqual(failed["state"], "failed"); self.assertIsNotNone(failed["retry_authorization"])
            atomic_json(channel.directory / "native.json",
                        {"v2": {"application_retry": failed["retry_authorization"]}})
            cli.tick(runtime, storage, channel)
            editor.fail_commit = False; plugin.v2_apply_inbox(storage, editor, now=102)
            atomic_json(channel.directory / "native.json", {}); cli.tick(runtime, storage, channel)
            self.assertEqual(read_json(channel.directory / "application.json")["state"], "applied")
            self.assertEqual(read_json(channel.directory / "ack.json")["status"], "applied")
            self.assertEqual(runtime.state["phase"], "delivered")

    def test_native_adapter_sources_use_origin_slot_and_pa_matrix(self):
        source = (ROOT / "integration/v1-native-engine/main.cpp").read_text()
        self.assertIn('get_at(params.extruder_id)', source)
        self.assertIn('new ConfigOptionInt(params.extruder_id+1)', source)
        self.assertIn('params.speeds.size()*params.accelerations.size()', source)
        self.assertIn('!junction_deviation&&config.get_abs_value_at("default_jerk",params.extruder_id)>0', source)
        self.assertIn('config.set_key_value("default_junction_deviation",new ConfigOptionFloatsNullable(1,0))', source)
        self.assertIn('object->config.set_key_value("outer_wall_speed"', source)
        self.assertIn('object->config.set_key_value("outer_wall_acceleration"', source)


if __name__ == "__main__":
    unittest.main()
