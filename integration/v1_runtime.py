"""Durable local coordinator. Product runtime never uses the Spare test worker.

This candidate deliberately has no action-enabled printer adapter. All generated
files remain local; Start is rejected, including for parity-qualified files.
"""
import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import time

from integration.v1_contract import (CALIBRATIONS, DEFAULTS, SETTINGS, ContractError,
    canonical, digest, exact, hex_value, validate_context, validate_prepared, validate_request)


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1048576:
        raise ContractError("Bounded regular JSON file required")
    def pairs(items):
        obj = {}
        for key, val in items:
            if key in obj:
                raise ContractError("Duplicate JSON key")
            obj[key] = val
        return obj
    with path.open("rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576:
        raise ContractError("Oversized JSON")
    value = json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ContractError("Non-finite JSON")))
    canonical(value)
    return value


def atomic_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ContractError("Refusing symlink artifact")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = canonical(value)
    fd, name = tempfile.mkstemp(prefix=".v1-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class InstanceLock:
    """Kernel-owned lock; abnormal exit releases it, stale files do not block."""
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ContractError("Symlink lock refused")
        self.file = self.path.open("a+b")
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                if self.path.stat().st_size == 0:
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.file.close()
            raise
        return self

    def __exit__(self, *_):
        self.file.close()


class Coordinator:
    def __init__(self, root, generator, config, capabilities, now=time.time, job_adapter=None):
        self.root = Path(root)
        self.generator = generator
        self.config = config
        self.capabilities = copy.deepcopy(capabilities)
        self.now = now
        # Trusted in-process factory only. Never construct from a native request.
        # The shipped launcher intentionally supplies none: no physical test grant.
        self.job_adapter = job_adapter
        self.path = self.root / "coordinator.json"
        if self.path.exists():
            self.state = read_json(self.path)
            if self.state.get("schema") != "helix-orca-v1-journal/v1":
                raise ContractError("Unknown coordinator journal")
            if self.state.get("request"):
                req = self.state["request"]
                validate_request(req, now=req["created_at"])
                if digest(self.state["context"]) != req["context_sha256"]:
                    raise ContractError("Recovered original context differs")
                if self.state.get("prepared"):
                    validate_prepared(self.state["prepared"], req)
                # Interrupted preparation is ambiguous: never rerun from receipt.
                if self.state["phase"] == "preparing":
                    self._status("blocked", "Preparation interrupted. Original request retained; no print was dispatched.")
                elif self.state["phase"] in ("starting", "printing", "verifying", "cancelling"):
                    self._status("uncertain", "Recovered job requires fresh independent status/history; Start will never be repeated.")
        else:
            self.state = {"schema": "helix-orca-v1-journal/v1", "context": None, "offer": None,
                          "request": None, "prepared": None, "result": None, "phase": "requested",
                          "sequence": 0, "message": "Waiting for Orca profiles.", "consumed_intents": [],
                          "job": None, "completion": None, "receipt": None}
            self._persist()

    def _persist(self):
        atomic_json(self.path, self.state)

    def _status(self, phase, message):
        message = str(message).encode("utf-8")[:768].decode("utf-8", errors="ignore")
        self.state.update(phase=phase, message=message, sequence=self.state["sequence"] + 1)
        self._persist()

    def offer(self, context):
        context = validate_context(context)
        if self.state["request"] is not None and self.state["phase"] == "delivered" and not self.state.get("native_acknowledged", False):
            return copy.deepcopy(self.state["offer"])
        if self.state["request"] is not None and self.state["phase"] not in ("delivered", "failed", "cancelled", "blocked"):
            return self.state["offer"]
        if self.state["request"] is None and self.state["context"] == context and self.state["offer"] and self.now() < self.state["offer"]["expires_at"]:
            return self.state["offer"]
        # Archive completed/blocked immutable session before allowing a fresh nonce.
        if self.state["request"]:
            atomic_json(self.root / "history" / (self.state["request"]["request_id"] + ".json"), self.state)
        now = int(self.now())
        offer = dict(schema="helix-orca-v1-offer/v1", request_id=secrets.token_hex(16),
                     origin_id=context["origin_id"], context_sha256=digest(context),
                     created_at=now, expires_at=now + 3600, nozzle_mm=context["nozzle_mm"],
                     capabilities=self.capabilities, defaults=copy.deepcopy(DEFAULTS))
        for role in ("printer", "process", "filament"):
            offer[role] = context[role]["saved"]["name"]
        self.state.update(context=context, offer=offer, request=None, prepared=None, result=None,
                          phase="requested", message="Choose a calibration on Helix.", consumed_intents=[],
                          job=None, completion=None, receipt=None, native_acknowledged=False)
        self._persist()
        return copy.deepcopy(offer)

    def request(self, value):
        if self.state["request"] is not None and canonical(value) == canonical(self.state["request"]):
            return self.status()  # Owned monitoring/result return outlives the Start deadline.
        request = validate_request(value, now=self.now())
        if self.state["request"]:
            if request == self.state["request"]:
                return self.status()
            raise ContractError("An immutable request is already retained")
        offer = self.state["offer"]
        if not offer:
            raise ContractError("No original Orca context")
        for k in ("request_id", "origin_id", "context_sha256", "created_at", "expires_at"):
            if request[k] != offer[k]:
                raise ContractError("Request differs from original offer: " + k)
        self.state["request"] = request
        self._status("preparing", "Preparing with Orca; nothing has started.")
        try:
            self.evaluation()
        except (ValueError, KeyError) as exc:
            self._status("blocked", "Evaluation unavailable for these inputs: " + str(exc))
            return self.status()
        cap = next((c for c in self.capabilities if c["id"] == request["calibration"]), None)
        if not cap or not cap["available"]:
            self._status("blocked", cap["reason"] if cap else "Generator unavailable")
            return self.status()
        directory = self.root / "jobs" / request["request_id"]
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        try:
            prepared = validate_prepared(self.generator(request, copy.deepcopy(self.state["context"]), directory, self.config), request)
            self.state["prepared"] = prepared
            atomic_json(directory / "prepared.json", prepared)
            if prepared["artifact"]:
                self.verify_artifact(prepared, directory)
            # A bare qualified flag is never trusted. V1 parity owns full report validation.
            if prepared["parity"]["qualified"]:
                self.verify_parity(prepared, directory)
                self._status("review", "Prepared job verified. Review profiles and parameters, then Confirm.")
            else:
                self._status("blocked", prepared["parity"]["reason"])
        except Exception as exc:
            self._status("blocked", "Preparation unavailable: " + str(exc)[:700])
        return self.status()

    @staticmethod
    def verify_artifact(prepared, directory):
        artifact = prepared["artifact"]
        path = directory / artifact["name"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size != artifact["size"]:
            raise ContractError("Prepared artifact missing or changed")
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ContractError("Prepared artifact bytes differ")

    @staticmethod
    def verify_parity(prepared, directory):
        # This boundary stays closed until a reusable report verifier is available.
        from integration.v1_parity import verify_report
        report = read_json(directory / "parity.json")
        if digest(report) != prepared["parity"]["report_sha256"]:
            raise ContractError("Parity report digest differs")
        if verify_report(report, prepared) is not True:
            raise ContractError("Independent native parity report failed re-verification")

    def intent(self, value):
        exact(value, "schema request_id origin_id prepared_sha256 action intent_id", "intent")
        if value["schema"] != "helix-orca-v1-intent/v1" or value["action"] not in ("confirm", "start", "cancel"):
            raise ContractError("Unknown native intent")
        hex_value(value["intent_id"], 32)
        req, prepared = self.state["request"], self.state["prepared"]
        if req is None or prepared is None or any(value[k] != req[k] for k in ("request_id", "origin_id")) or value["prepared_sha256"] != digest(prepared):
            raise ContractError("Intent differs from prepared job")
        if value["intent_id"] in self.state["consumed_intents"]:
            return self.status()
        if value["action"] != "cancel" and self.now() >= req["expires_at"]:
            raise ContractError("Original Start window expired")
        self.state["consumed_intents"].append(value["intent_id"])
        self._persist()
        if value["action"] == "confirm":
            if self.state["phase"] != "review":
                raise ContractError("Confirmation requires a verified prepared job")
            directory = self.root / "jobs" / req["request_id"]
            self.verify_artifact(prepared, directory)
            self.verify_parity(prepared, directory)
            self._status("confirmed", "Confirmed. Start remains a separate deliberate action.")
        elif value["action"] == "start":
            if self.state["phase"] != "confirmed":
                raise ContractError("Start requires prior confirmation")
            if self.job_adapter is None:
                self._status("blocked", "Physical execution is disabled for this review candidate. No upload, queue, heat or motion was requested.")
            else:
                directory = self.root / "jobs" / req["request_id"]
                self.verify_artifact(prepared, directory)
                self.verify_parity(prepared, directory)
                # Durable intent before dispatch. A crash cannot authorize replay.
                self._status("starting", "Start requested. Confirming the same printer job.")
                try:
                    job = self.job_adapter.start(copy.deepcopy(req), copy.deepcopy(prepared), directory, copy.deepcopy(value))
                    exact(job, "job_id file_sha256 request_id origin_id", "started job")
                    if not isinstance(job["job_id"], str) or not job["job_id"] or any(job[k] != req[k] for k in ("request_id", "origin_id")) or job["file_sha256"] != prepared["artifact"]["sha256"]:
                        raise ContractError("Dispatched job identity differs")
                    self.state["job"] = job
                    self._status("starting", "Waiting for independently matched printer status.")
                except Exception:
                    self._status("uncertain", "Start outcome is uncertain; no automatic retry is permitted.")
                    raise
        else:
            if self.state["phase"] in ("starting", "printing", "verifying", "uncertain") and self.state.get("job"):
                if self.job_adapter is None:
                    raise ContractError("Physical cancellation adapter unavailable; use native printer controls")
                self._status("uncertain", "Cancellation requested; waiting for independent printer confirmation.")
                self.job_adapter.cancel(copy.deepcopy(self.state["job"]), copy.deepcopy(value))
                return self.status()
            if self.state["phase"] not in ("review", "confirmed", "blocked"):
                raise ContractError("No cancellable prepared job")
            self._status("cancelled", "Preparation cancelled. Nothing was sent to the printer.")
        return self.status()

    def poll_job(self):
        if self.state["result"] or self.state["phase"] not in ("starting", "printing", "verifying", "uncertain"):
            return self.status()
        job = self.state.get("job")
        if self.job_adapter is None or not job:
            return self.status()
        try:
            proof = self.job_adapter.observe(copy.deepcopy(job))
            exact(proof, "job_id file_sha256 print_state history_state history_job_id history_file_sha256", "independent observation")
            if proof["job_id"] != job["job_id"] or proof["file_sha256"] != job["file_sha256"]:
                raise ContractError("Unrelated job cannot advance calibration")
            state = proof["print_state"]
            if state in ("error", "failed", "cancelled"):
                self._status("cancelled" if state == "cancelled" else "failed", "Calibration did not complete successfully. No result is available.")
            elif state == "printing":
                self._status("printing", "Calibration is printing. Evaluation stays locked.")
            elif state == "complete":
                if proof["history_job_id"] == job["job_id"] and proof["history_file_sha256"] == job["file_sha256"] and proof["history_state"] == "completed":
                    self.state["completion"] = proof
                    self._status("complete", "Completed job independently verified. Evaluate the print and return your result.")
                else:
                    self._status("verifying", "Print ended. Waiting for independently matched completed-job history.")
            else:
                self._status("uncertain", "Printer status is uncertain. Original job retained; evaluation locked.")
        except Exception:
            self._status("uncertain", "Independent printer status unavailable. Original job retained; no automatic Start retry.")
            raise
        return self.status()

    def evaluation(self):
        req = self.state["request"]
        if not req:
            return None
        kind, p = req["calibration"], req["parameters"]
        if kind == "temperature":
            options = list(range(p["start"], p["end"] - 1, -5))
            unit = "°C"
        elif kind == "flow_ratio_yolo":
            current = Decimal(self.state["context"]["effective"]["filament_flow_ratio"])
            options = [float(current + Decimal(i) / 100) for i in range(-5, 6)]
            unit = "ratio"
        else:
            start, end, step = (Decimal(str(p[k])) for k in ("start", "end", "step"))
            options = [float(start + step * i) for i in range(int((end - start) // step) + 1)]
            unit = {"retraction": "mm", "pressure_advance_pattern": "s", "max_volumetric_speed": "mm³/s"}[kind]
        if len(options) > 128:
            raise ContractError("Evaluation exceeds native option limit")
        return dict(setting=SETTINGS[kind], options=options, unit=unit)

    def result(self, value):
        exact(value, "schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value not_applied", "result")
        req, prepared, proof = self.state["request"], self.state["prepared"], self.state.get("completion")
        if value["schema"] != "helix-orca-v1-result/v1" or value["not_applied"] is not True or not req or not prepared or not proof:
            raise ContractError("No independently completed original calibration")
        if any(value[k] != req[k] for k in ("request_id", "origin_id", "context_sha256")) or value["prepared_sha256"] != digest(prepared) or value["completion_sha256"] != digest(proof) or value["job_id"] != self.state["job"]["job_id"]:
            raise ContractError("Result is unrelated to original job")
        evaluation = self.evaluation()
        if value["setting"] != evaluation["setting"] or type(value["value"]) not in (int, float) or value["value"] not in evaluation["options"]:
            raise ContractError("Result outside completed calibration choices")
        if self.state["result"]:
            if canonical(value) != canonical(self.state["result"]):
                raise ContractError("Committed result is immutable")
            return copy.deepcopy(value)
        if self.state["phase"] != "complete":
            raise ContractError("Evaluation is locked")
        self.state["result"] = copy.deepcopy(value)
        self._status("returning", "Returning the selected result to the original Orca context. NOT APPLIED.")
        return copy.deepcopy(value)

    def acknowledge(self, receipt):
        result = self.state["result"]
        expected = dict(schema="helix-orca-v1-ack/v1", request_id=result["request_id"], origin_id=result["origin_id"],
                        result_sha256=digest(result), result=result, not_applied=True) if result else None
        if expected is None or canonical(receipt) != canonical(expected):
            raise ContractError("Only the exact originating companion receipt can acknowledge delivery")
        if self.state.get("receipt") != receipt:
            self.state["receipt"] = copy.deepcopy(receipt)
            self._status("delivered", "Result returned to original Orca. NOT APPLIED.")
        return copy.deepcopy(receipt)

    def status(self):
        req = self.state["request"]
        if req is None:
            return None
        prepared = self.state["prepared"]
        return dict(schema="helix-orca-v1-status/v1", request_id=req["request_id"], origin_id=req["origin_id"],
                    sequence=self.state["sequence"], phase=self.state["phase"], message=self.state["message"],
                    prepared=copy.deepcopy(prepared), prepared_sha256=digest(prepared) if prepared else None,
                    job_id=self.state["job"]["job_id"] if self.state.get("job") else None,
                    completion_sha256=digest(self.state["completion"]) if self.state.get("completion") else None,
                    evaluation=self.evaluation() if self.state.get("completion") else None)
