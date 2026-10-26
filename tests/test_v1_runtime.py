import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from integration.v1_contract import ContractError, DEFAULTS, canonical, digest, validate_context, validate_parameters, validate_prepared, validate_request
from integration.v1_runtime import Coordinator, InstanceLock, atomic_json, read_json
from integration.v1_transport import DirectoryEvents, MoonrakerEvents


def context():
    value = dict(schema="helix-orca-v1-context/v1", origin_id="1" * 32,
                 runtime=dict(version="2.5.0-dev", build="6a7763f0"),
                 effective={"nozzle_temperature": "217", "curr_bed_type": "High Temp Plate"}, nozzle_mm=0.4)
    for role in ("printer", "process", "filament"):
        value[role] = dict(saved=dict(name=role, config={"setting": "220"}), edited=dict(name=role, config={"setting": "217"}))
    return value


def request(offer, calibration="temperature"):
    value = {k: offer[k] for k in ("request_id", "origin_id", "context_sha256", "created_at", "expires_at")}
    value.update(schema="helix-orca-v1-request/v1", calibration=calibration, parameters=DEFAULTS[calibration], not_applied=True)
    return value


def prepared(req, qualified=False):
    value = {k: req[k] for k in ("request_id", "origin_id", "context_sha256", "calibration", "parameters")}
    value.update(schema="helix-orca-v1-prepared/v1", request_sha256=digest(req), artifact=None,
                 generator=dict(build="6a7763f0", route="fixture"),
                 parity=dict(qualified=qualified, report_sha256=None, reason="Independent native reference absent"), not_applied=True)
    return value


class ContractTests(unittest.TestCase):
    def test_preserves_distinct_context_and_rejects_missing_effective(self):
        source = context()
        self.assertEqual(validate_context(source), source)
        self.assertNotEqual(source["filament"]["saved"]["config"], source["filament"]["edited"]["config"])
        source["effective"] = None
        with self.assertRaises(ContractError):
            validate_context(source)

    def test_all_native_defaults_and_dialog_normalization(self):
        for key, val in DEFAULTS.items():
            self.assertEqual(validate_parameters(key, val), val)
        bad = dict(DEFAULTS["temperature"], start=231, end=191)
        with self.assertRaises(ContractError):
            validate_parameters("temperature", bad)

    def test_request_expiry_unknown_fields_and_nan(self):
        offer = dict(request_id="2"*32, origin_id="1"*32, context_sha256=digest(context()), created_at=100, expires_at=3700)
        good = request(offer)
        self.assertEqual(validate_request(good, 100), good)
        for bad, now in ((dict(good, extra=True), 100), (good, 3700), (good, 99), (dict(good, not_applied=False), 100)):
            with self.assertRaises(ContractError):
                validate_request(bad, now)
        with self.assertRaises(ContractError):
            canonical({"x": float("nan")})

    def test_prepared_cannot_claim_qualification_without_provenance(self):
        req = request(dict(request_id="2"*32, origin_id="1"*32, context_sha256=digest(context()), created_at=100, expires_at=3700))
        with self.assertRaises(ContractError):
            validate_prepared(prepared(req, True), req)
        with self.assertRaises(ContractError):
            validate_prepared(dict(prepared(req), parameters=DEFAULTS["retraction"]), req)


class RuntimeTests(unittest.TestCase):
    def make(self, root, generator=None, available=True):
        return Coordinator(root, generator or (lambda req, *_: prepared(req)), {},
            [dict(id=k, available=available, reason="No executable configured") for k in DEFAULTS], now=lambda: 100)

    def test_generation_once_duplicate_and_restart_retain_original(self):
        with tempfile.TemporaryDirectory() as root:
            calls = []
            def generate(req, *_):
                calls.append(req)
                return prepared(req)
            runtime = self.make(root, generate)
            offer = runtime.offer(context())
            req = request(offer)
            runtime.request(req)
            runtime.request(req)
            self.assertEqual(len(calls), 1)
            recovered = self.make(root, generate)
            recovered.request(req)
            self.assertEqual(len(calls), 1)
            self.assertEqual(recovered.state["context"], context())
            self.assertEqual(recovered.status()["phase"], "blocked")

    def test_request_cannot_retarget_original_context(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = self.make(root)
            req = request(runtime.offer(context()))
            req["context_sha256"] = "a" * 64
            with self.assertRaises(ContractError):
                runtime.request(req)
            self.assertIsNone(runtime.state["request"])

    def test_terminal_request_gets_fresh_nonce_without_retargeting_history(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = self.make(root, available=False)
            first = runtime.offer(context())
            req = request(first)
            runtime.request(req)
            second = runtime.offer(context())
            self.assertNotEqual(first["request_id"], second["request_id"])
            self.assertEqual(first["context_sha256"], second["context_sha256"])
            self.assertEqual(read_json(Path(root)/"history"/(first["request_id"]+".json"))["request"], req)
            self.assertEqual(second, runtime.offer(context()))

    def test_tick_ignores_archived_native_artifacts_and_unavailable_context(self):
        spec = importlib.util.spec_from_file_location("v1_cli_tick", Path(__file__).resolve().parents[1]/"scripts/v1-runtime.py")
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); storage=root/"storage"; storage.mkdir()
            runtime=self.make(root/"runtime", available=False)
            original=context(); atomic_json(storage/"context.json",original)
            old=request(runtime.offer(original)); runtime.request(old)
            channel=DirectoryEvents(root/"channel")
            atomic_json(channel.directory/"native.json",dict(request=old,result=dict(request_id=old["request_id"]),intent=dict(request_id=old["request_id"])))
            cli.tick(runtime,storage,channel)
            fresh=runtime.state["offer"]
            self.assertNotEqual(fresh["request_id"],old["request_id"])
            self.assertIsNone(runtime.state["request"])
            atomic_json(storage/"context-status.json",dict(available=False))
            cli.tick(runtime,storage,channel)
            disabled=read_json(channel.directory/"context.json")
            self.assertTrue(all(not item["available"] for item in disabled["capabilities"]))
            self.assertEqual(runtime.state["offer"],fresh)
            runtime.request(request(fresh))
            cli.tick(runtime,storage,channel)
            self.assertIsNone(runtime.state["request"])
            self.assertTrue(all(not item["available"] for item in read_json(channel.directory/"context.json")["capabilities"]))

    def test_available_is_not_qualification_and_unavailable_never_runs(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = self.make(root, lambda *_: self.fail("Unavailable generator called"), available=False)
            req = request(runtime.offer(context()))
            runtime.request(req)
            self.assertEqual(runtime.status()["phase"], "blocked")
            self.assertIsNone(runtime.status()["prepared"])

    def test_qualified_flag_is_reverified_against_actual_report(self):
        with tempfile.TemporaryDirectory() as root:
            def liar(req, *_):
                value = prepared(req)
                value["artifact"] = dict(name="test.gcode", size=1, sha256="a"*64)
                value["parity"].update(qualified=True, report_sha256="b"*64)
                return value
            runtime = self.make(root, liar)
            runtime.request(request(runtime.offer(context())))
            self.assertEqual(runtime.status()["phase"], "blocked")
            self.assertIn("artifact", runtime.status()["message"])

    def test_crash_during_generation_never_redispatches(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = self.make(root)
            req = request(runtime.offer(context()))
            runtime.state.update(request=req, phase="preparing")
            runtime._persist()
            recovered = self.make(root, lambda *_: self.fail("Recovered generation rerun"))
            self.assertEqual(recovered.status()["phase"], "blocked")
            recovered.request(req)

    def test_start_requires_confirm_and_remains_physically_disabled(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = self.make(root)
            req = request(runtime.offer(context()))
            runtime.state.update(request=req, prepared=prepared(req), phase="confirmed")
            runtime._persist()
            intent = dict(schema="helix-orca-v1-intent/v1", request_id=req["request_id"], origin_id=req["origin_id"],
                          prepared_sha256=digest(runtime.state["prepared"]), action="start", intent_id="3"*32)
            result = runtime.intent(intent)
            self.assertEqual(result["phase"], "blocked")
            self.assertIn("disabled", result["message"])
            self.assertEqual(runtime.intent(intent), result)

    def test_normalized_adapter_exact_job_history_result_receipt_and_restart(self):
        """Synthetic adapter exercises transitions; it is not physical proof."""
        with tempfile.TemporaryDirectory() as root:
            class Adapter:
                starts = 0
                proof = None
                confirms = []
                def confirm(self, req, prepared, directory, intent):
                    self.confirms.append(copy.deepcopy(intent))
                def start(self, req, prepared, directory, intent):
                    if not self.confirms or self.confirms[-1]["prepared_sha256"] != intent["prepared_sha256"] or self.confirms[-1]["intent_id"] == intent["intent_id"]:
                        raise ContractError("Separate bound confirmation required")
                    self.starts += 1
                    self.job = dict(job_id="owned-job", file_sha256=prepared["artifact"]["sha256"], request_id=req["request_id"], origin_id=req["origin_id"])
                    return self.job
                def observe(self, job):
                    return self.proof
            adapter = Adapter()
            def generate(req, snapshot, directory, config):
                data = b"; synthetic fixture, never sent to a printer\n"
                (directory/"fixture.gcode").write_bytes(data)
                val = prepared(req)
                val["artifact"] = dict(name="fixture.gcode",size=len(data),sha256=hashlib.sha256(data).hexdigest())
                val["parity"].update(qualified=True,report_sha256="c"*64)
                return val
            runtime = self.make(root, generate)
            runtime.job_adapter = adapter
            with patch.object(Coordinator, "verify_parity", return_value=None):
                req = request(runtime.offer(context()))
                runtime.request(req)
                self.assertEqual(runtime.status()["phase"], "review")
                base = dict(schema="helix-orca-v1-intent/v1",request_id=req["request_id"], origin_id=req["origin_id"],prepared_sha256=digest(runtime.state["prepared"]))
                confirm = dict(base,action="confirm",intent_id="3"*32)
                runtime.intent(confirm)
                runtime.intent(confirm)
                self.assertEqual(adapter.confirms,[confirm])
                start = dict(base,action="start",intent_id="4"*32)
                runtime.intent(start)
                runtime.intent(start)
                self.assertEqual(adapter.starts, 1)
                original = copy.deepcopy(runtime.state["context"])
                newer = context();newer["origin_id"]="a"*32;newer["filament"]["saved"]["name"]="Different filament"
                runtime.offer(newer)
                self.assertEqual(runtime.state["context"], original)
                adapter.proof = dict(job_id="unrelated", file_sha256=adapter.job["file_sha256"],print_state="complete",history_state="completed",history_job_id="unrelated",history_file_sha256=adapter.job["file_sha256"])
                with self.assertRaises(ContractError):
                    runtime.poll_job()
                self.assertEqual(runtime.status()["phase"], "uncertain")
                adapter.proof.update(job_id="owned-job", print_state="printing", history_state=None,history_job_id=None,history_file_sha256=None)
                runtime.now=lambda: 9000  # A healthy owned print has no request-TTL duration limit.
                runtime.poll_job()
                self.assertEqual(runtime.status()["phase"], "printing")
                adapter.proof["print_state"]="complete"
                runtime.poll_job()
                self.assertEqual(runtime.status()["phase"], "verifying")
                adapter.proof.update(history_state="completed",history_job_id="owned-job",history_file_sha256=adapter.job["file_sha256"])
                runtime.poll_job()
                self.assertEqual(runtime.status()["phase"], "complete")
                result = dict(schema="helix-orca-v1-result/v1", request_id=req["request_id"], origin_id=req["origin_id"],context_sha256=req["context_sha256"],prepared_sha256=digest(runtime.state["prepared"]),job_id="owned-job",completion_sha256=digest(adapter.proof),setting="nozzle_temperature",value=220,not_applied=True)
                runtime.result(result)
                with self.assertRaises(ContractError):
                    runtime.result(dict(result,value=225))
                with self.assertRaises(ContractError):
                    runtime.acknowledge(dict(schema="helix-orca-v1-ack/v1",request_id=req["request_id"],origin_id="f"*32,result_sha256=digest(result),result=result,not_applied=True))
                receipt=dict(schema="helix-orca-v1-ack/v1",request_id=req["request_id"],origin_id=req["origin_id"],result_sha256=digest(result),result=result,not_applied=True)
                runtime.acknowledge(receipt)
                self.assertEqual(runtime.status()["phase"], "delivered")
                recovered=self.make(root,generate)
                self.assertEqual(recovered.state["result"],result)
                self.assertEqual(recovered.state["receipt"],receipt)
                self.assertEqual(adapter.starts,1)

    def test_confirm_failure_is_a_visible_terminal_blocker(self):
        with tempfile.TemporaryDirectory() as root:
            runtime=self.make(root)
            req=request(runtime.offer(context()))
            runtime.state.update(request=req,prepared=prepared(req),phase="review")
            class Incompatible:
                def confirm(self,*_): raise ContractError("Prepared macro signature is unavailable for this target")
            runtime.job_adapter=Incompatible()
            intent=dict(schema="helix-orca-v1-intent/v1",request_id=req["request_id"],origin_id=req["origin_id"],
                prepared_sha256=digest(runtime.state["prepared"]),action="confirm",intent_id="3"*32)
            with patch.object(Coordinator,"verify_artifact"),patch.object(Coordinator,"verify_parity"):
                status=runtime.intent(intent)
            self.assertEqual(status["phase"],"blocked")
            self.assertIn("macro signature",status["message"])
            self.assertEqual(runtime.intent(intent),status)
            self.assertIsNone(runtime.state["job"])

    def test_json_duplicate_symlink_and_competing_instance_refuse(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"data.json"
            path.write_text('{"x":1,"x":2}')
            with self.assertRaises(ContractError):
                read_json(path)
            path.unlink()
            path.symlink_to(Path(root)/"elsewhere")
            with self.assertRaises(ContractError):
                atomic_json(path, {})
            with InstanceLock(Path(root)/"lock"):
                with self.assertRaises(OSError):
                    with InstanceLock(Path(root)/"lock"):
                        pass

    def test_event_transport_has_no_action_or_external_origin(self):
        for origin, host in (("http://example.com", "8.8.8.8"), ("http://192.168.1.1/other", "192.168.1.1")):
            with self.assertRaises(ContractError):
                MoonrakerEvents(origin, host, "pin", trusted_lan=True)
        with tempfile.TemporaryDirectory() as root:
            adapter = DirectoryEvents(root)
            with self.assertRaises(ContractError):
                adapter.send("printer.print.start", {})
            adapter.send("helix_orca_v1.context.v1", {"safe": True})
            self.assertEqual(read_json(Path(root)/"context.json"), {"safe": True})

    def test_missing_initial_native_storage_is_empty_but_other_http_errors_fail(self):
        class Opener:
            def __init__(self, status):
                self.status = status

            def open(self, request, timeout):
                raise HTTPError(request.full_url, self.status, "test", {}, None)

        adapter = MoonrakerEvents(
            "http://192.168.1.10", "192.168.1.10", "pin", trusted_lan=True)
        adapter.assert_identity = lambda: None
        adapter.opener = Opener(404)
        self.assertEqual(adapter.read(), {})
        with self.assertRaises(HTTPError):
            adapter._get("/server/info")
        for status in (401, 403, 503):
            adapter.opener = Opener(status)
            with self.subTest(status=status), self.assertRaises(HTTPError):
                adapter.read()


if __name__ == "__main__":
    unittest.main()
