"""Durable local coordinator. Product runtime never uses the Spare test worker.

The default review invocation has no action-enabled printer adapter. A separate
local deployment record and configuration are required before an owned adapter
can be supplied; this build program creates neither approval nor activation.
"""
import copy
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import tempfile
import time

from integration.v1_contract import (CALIBRATIONS, DEFAULTS, SETTINGS, ContractError,
    canonical, digest, exact, hex_value, validate_context, validate_prepared, validate_request,
    default_parameters, context_extruder_type, flow_ratio_choices, default_parameters_v2,
    validate_context_v2, validate_request_v2, validate_prepared_v2,
    validate_build_qualification_v2, validate_warning_acknowledgement_v2, validate_result_v2,
    machine_sha256_v2)


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
        # The review launcher supplies none without a separate exact local deployment gate.
        self.job_adapter = job_adapter
        self.path = self.root / "coordinator.json"
        if self.path.exists():
            self.state = read_json(self.path)
            if self.state.get("schema") != "helix-orca-v1-journal/v1":
                raise ContractError("Unknown coordinator journal")
            if self.state.get("request"):
                req = self.state["request"]
                current = req.get("schema") == "helix-orca-v1-request/v2"
                (validate_request_v2 if current else validate_request)(req, now=req["created_at"])
                if digest(self.state["context"]) != req["context_sha256"]:
                    raise ContractError("Recovered original context differs")
                if self.state.get("prepared"):
                    prepared = (validate_prepared_v2 if current else validate_prepared)(self.state["prepared"], req)
                    if current:
                        if prepared["generator"]["machine_sha256"] != machine_sha256_v2(self.state["context"]):
                            raise ContractError("Recovered prepared job differs from its immutable machine context")
                        qualification = validate_build_qualification_v2(self.state.get("qualification"))
                        if digest(qualification) != prepared["generator"]["qualification_sha256"]:
                            raise ContractError("Recovered build qualification differs from the prepared job")
                        acknowledgement = self.state.get("warning_ack")
                        if acknowledgement is not None:
                            validate_warning_acknowledgement_v2(acknowledgement, prepared)
                # Interrupted preparation is ambiguous: never rerun from receipt.
                if self.state["phase"] == "preparing":
                    self._status("blocked", "Preparation interrupted. Original request retained; no print was dispatched.")
                elif self.state["phase"] in ("starting", "printing", "verifying", "cancelling"):
                    self._status("uncertain", "Recovered job requires fresh independent status/history; Start will never be repeated.")
        else:
            self.state = {"schema": "helix-orca-v1-journal/v1", "context": None, "offer": None,
                          "request": None, "prepared": None, "result": None, "phase": "requested",
                          "sequence": 0, "message": "Waiting for Orca profiles.", "consumed_intents": [],
                          "job": None, "completion": None, "receipt": None, "pending_start_intent": None, "monitor": None,
                          "warning_ack": None, "qualification": None}
            self.state.update(application_digest=None, application_event=None)
            self._persist()

    def _current(self):
        request = self.state.get("request")
        if request is not None:
            return request.get("schema") == "helix-orca-v1-request/v2"
        context = self.state.get("context")
        return context is not None and context.get("schema") == "helix-orca-v1-context/v2"

    def _persist(self):
        atomic_json(self.path, self.state)

    def _status(self, phase, message):
        message = str(message).encode("utf-8")[:768].decode("utf-8", errors="ignore")
        self.state.update(phase=phase, message=message, sequence=self.state["sequence"] + 1)
        self._persist()

    def offer(self, context):
        current = context.get("schema") == "helix-orca-v1-context/v2"
        context = validate_context_v2(context) if current else validate_context(context)
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
        offer = dict(schema="helix-orca-v1-offer/v2" if current else "helix-orca-v1-offer/v1", request_id=secrets.token_hex(16),
                     origin_id=context["origin_id"], context_sha256=digest(context),
                     created_at=now, expires_at=now + 3600, nozzle_mm=context["nozzle_mm"],
                     capabilities=self.capabilities, defaults=default_parameters_v2(context) if current else default_parameters(context),
                     extruder_type=context_extruder_type(context))
        if current:
            offer["origin_filament"] = copy.deepcopy(context["origin_filament"])
            offer["filament_slots"] = copy.deepcopy(context["filament_slots"])
        for role in ("printer", "process", "filament"):
            offer[role] = context[role]["saved"]["name"]
        self.state.update(context=context, offer=offer, request=None, prepared=None, result=None,
                          phase="requested", message="Choose a calibration on Helix.", consumed_intents=[],
                          job=None, completion=None, receipt=None, native_acknowledged=False, pending_start_intent=None, monitor=None,
                          warning_ack=None, qualification=None)
        self.state.update(application_digest=None, application_event=None)
        self._persist()
        return copy.deepcopy(offer)

    def request(self, value):
        if self.state["request"] is not None and canonical(value) == canonical(self.state["request"]):
            return self.status()  # Owned monitoring/result return outlives the Start deadline.
        current = value.get("schema") == "helix-orca-v1-request/v2"
        request = (validate_request_v2 if current else validate_request)(value, now=self.now())
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
            prepared = (validate_prepared_v2 if current else validate_prepared)(
                self.generator(copy.deepcopy(request), copy.deepcopy(self.state["context"]), directory, self.config), request)
            if current and prepared["generator"]["machine_sha256"] != machine_sha256_v2(self.state["context"]):
                raise ContractError("Prepared job differs from its immutable machine context")
            self.state["prepared"] = prepared
            atomic_json(directory / "prepared.json", prepared)
            if prepared["artifact"]:
                self.verify_artifact(prepared, directory)
            if current:
                qualification = validate_build_qualification_v2(self.config.get("build_qualification"))
                if (digest(qualification) != prepared["generator"]["qualification_sha256"]
                        or qualification["routes"][request["calibration"]]["qualified"] is not True
                        or qualification["routes"][request["calibration"]]["route_id"] != prepared["generator"]["route"]):
                    raise ContractError("Prepared route differs from build-level qualification")
                self.state["qualification"] = qualification
                if prepared["processing"]["status"] != "ready":
                    self._status("blocked", "Unknown warning or processor error blocks this exact job.")
                elif any(item["requires_ack"] for item in prepared["processing"]["warnings"]):
                    self._status("warning", "Review and acknowledge Orca's structured warning before Confirm.")
                else:
                    self._status("review", "Exact job verified against the qualified build/route. Review, then Confirm.")
            # A bare qualified flag is never trusted. Historical V1 parity owns full report validation.
            elif prepared["parity"]["qualified"]:
                self.verify_parity(prepared, directory)
                self._status("review", "Prepared job verified. Review profiles and parameters, then Confirm.")
            else:
                self._status("blocked", prepared["parity"]["reason"])
        except Exception as exc:
            self._status("blocked", "Preparation unavailable: " + str(exc)[:700])
        return self.status()

    def acknowledge_warnings(self, value):
        if not self._current() or self.state.get("prepared") is None:
            raise ContractError("No current structured warning is awaiting acknowledgement")
        acknowledged = validate_warning_acknowledgement_v2(value, self.state["prepared"])
        retained = self.state.get("warning_ack")
        if retained is not None:
            if canonical(retained) != canonical(acknowledged):
                raise ContractError("Structured warning acknowledgement is immutable")
            return copy.deepcopy(retained)
        if self.state["phase"] != "warning":
            raise ContractError("No current structured warning is awaiting acknowledgement")
        self.state["warning_ack"] = acknowledged
        self._status("review", "Structured Orca warning acknowledged. Review the exact job, then Confirm.")
        return copy.deepcopy(acknowledged)

    def warning_event(self):
        """Return the bounded native warning prompt for the exact prepared job."""
        if not self._current() or self.state.get("prepared") is None:
            return None
        prepared = self.state["prepared"]
        warnings = [item for item in prepared["processing"]["warnings"] if item["requires_ack"]]
        if not warnings:
            return None
        codes = sorted(item["error_code"] for item in warnings)
        return dict(schema="helix-orca-v1-native-warning/v2",
                    request_id=prepared["request_id"], origin_id=prepared["origin_id"],
                    prepared_sha256=digest(prepared), warning_sha256=digest(warnings),
                    warning_codes=codes, title="Orca slicing warning",
                    message=("Orca reports a known filament/bed temperature warning ("
                             + ", ".join(codes) + "). Continue or cancel before confirmation."))

    def application_event(self, application):
        """Validate an Orca-side transaction journal and publish native state.

        Failed journals receive a durable coordinator authorization envelope,
        but it cannot reach Orca's retry file until native returns it unchanged.
        Uncertain commit-boundary outcomes are terminal and never retryable.
        """
        result = self.state.get("result")
        if not self._current() or result is None:
            raise ContractError("No current returned result can own a preset application")
        exact(application,
              "schema status phase request_id origin_id result_sha256 attempt target_name slot_number shared_slots updates created_at updated_at message outcome",
              "V2 preset application")
        if (application["schema"] != "helix-orca-v1-application/v2"
                or application["status"] not in ("pending", "applied", "failed", "uncertain")
                or application["request_id"] != result["request_id"]
                or application["origin_id"] != result["origin_id"]
                or application["result_sha256"] != digest(result)
                or type(application["attempt"]) is not int or application["attempt"] < 1
                or type(application["message"]) is not str):
            raise ContractError("Preset application differs from the returned result")
        application_sha256 = digest(application)
        if (self.state.get("application_digest") == application_sha256
                and self.state.get("application_event") is not None):
            return copy.deepcopy(self.state["application_event"])
        retained = self.state.get("application_event")
        sequence = (retained["sequence"] if retained else 0) + 1
        status = application["status"]
        native_state = "applying" if status == "pending" else "failed" if status == "uncertain" else status
        outcome = application.get("outcome")
        dirty = status == "applied" and isinstance(outcome, dict) and outcome.get("dirty") is True
        if status == "applied" and not dirty:
            raise ContractError("Applied preset transaction lacks Orca's dirty outcome")
        retry = None
        if status == "failed":
            retry = dict(schema="helix-orca-v1-application-retry/v2",
                         request_id=result["request_id"], origin_id=result["origin_id"],
                         result_sha256=digest(result),
                         failed_application_sha256=application_sha256,
                         attempt=application["attempt"] + 1, token=secrets.token_hex(16),
                         authorized_at=int(self.now()))
        message = application["message"].encode("utf-8")[:512].decode("utf-8", errors="ignore")
        if status == "uncertain":
            message = "Orca could not prove the preset transaction outcome. Inspect it in Orca; retry is disabled."
        event = dict(schema="helix-orca-v1-application/v2", request_id=result["request_id"],
                     origin_id=result["origin_id"], sequence=sequence, state=native_state,
                     message=message, result_sha256=digest(result), result=copy.deepcopy(result),
                     transaction_id=application_sha256 if status == "applied" else "",
                     dirty=dirty, unsaved=dirty, retry_authorization=retry)
        self.state["application_digest"] = application_sha256
        self.state["application_event"] = copy.deepcopy(event)
        self._persist()
        return event

    def authorize_application_retry(self, value):
        event = self.state.get("application_event")
        expected = event.get("retry_authorization") if isinstance(event, dict) else None
        if expected is None or canonical(value) != canonical(expected):
            raise ContractError("Application retry is not the exact current owner authorization")
        return copy.deepcopy(expected)

    def _verify_prepared_authority(self, prepared, directory):
        self.verify_artifact(prepared, directory)
        if self._current():
            qualification = validate_build_qualification_v2(self.state.get("qualification"))
            if prepared["generator"]["machine_sha256"] != machine_sha256_v2(self.state["context"]):
                raise ContractError("Prepared job differs from its immutable machine context")
            if digest(qualification) != prepared["generator"]["qualification_sha256"]:
                raise ContractError("Build qualification changed")
            if qualification["routes"][prepared["calibration"]]["route_id"] != prepared["generator"]["route"]:
                raise ContractError("Prepared generator route differs from build qualification")
            if any(item["requires_ack"] for item in prepared["processing"]["warnings"]):
                validate_warning_acknowledgement_v2(self.state.get("warning_ack"), prepared)
        else:
            self.verify_parity(prepared, directory)

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
        expected_schema = "helix-orca-v1-intent/v2" if self._current() else "helix-orca-v1-intent/v1"
        if value["schema"] != expected_schema or value["action"] not in ("confirm", "start", "cancel"):
            raise ContractError("Unknown native intent")
        hex_value(value["intent_id"], 32)
        req, prepared = self.state["request"], self.state["prepared"]
        if req is None or prepared is None or any(value[k] != req[k] for k in ("request_id", "origin_id")) or value["prepared_sha256"] != digest(prepared):
            raise ContractError("Intent differs from prepared job")
        if value["intent_id"] in self.state["consumed_intents"]:
            return self.status()
        if value["action"] != "cancel" and self.now() >= req["expires_at"]:
            raise ContractError("Original Start window expired")
        if value["action"] == "confirm":
            if self.state["phase"] != "review":
                raise ContractError("Confirmation requires a verified prepared job")
            directory = self.root / "jobs" / req["request_id"]
            try:
                self._verify_prepared_authority(prepared, directory)
                confirm = getattr(self.job_adapter, "confirm", None)
                if confirm is not None:
                    confirm(copy.deepcopy(req), copy.deepcopy(prepared), directory, copy.deepcopy(value))
            except Exception as exc:
                self.state["consumed_intents"].append(value["intent_id"])
                self._status("blocked", "Prepared job cannot start: " + str(exc))
                return self.status()
            # Confirmation is local/idempotent. A crash before this atomic journal
            # write can safely reconcile the same confirmation again.
            self.state["consumed_intents"].append(value["intent_id"])
            self._status("confirmed", "Confirmed. Start remains a separate deliberate action.")
        elif value["action"] == "start":
            if self.state["phase"] != "confirmed":
                raise ContractError("Start requires prior confirmation")
            if self.job_adapter is None:
                self.state["consumed_intents"].append(value["intent_id"])
                self._status("blocked", "Physical execution is disabled for this review candidate. No upload, queue, heat or motion was requested.")
            else:
                directory = self.root / "jobs" / req["request_id"]
                try:
                    self._verify_prepared_authority(prepared, directory)
                except Exception as exc:
                    self.state["consumed_intents"].append(value["intent_id"])
                    self._status("blocked", "Prepared job cannot start: " + str(exc))
                    return self.status()
                # Retain exact intent so a read-only recovery can adopt a job
                # the adapter durably confirmed before a coordinator crash.
                self.state["pending_start_intent"] = copy.deepcopy(value)
                # Consume and mark the dispatch phase in the same atomic journal.
                self.state["consumed_intents"].append(value["intent_id"])
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
        elif self.state["phase"] == "warning":
            self.state["consumed_intents"].append(value["intent_id"])
            self._status("cancelled", "Known warning cancelled. Nothing was sent to the printer.")
        else:
            if self.state["phase"] in ("starting", "printing", "verifying", "uncertain") and self.state.get("job"):
                if self.job_adapter is None:
                    raise ContractError("Physical cancellation adapter unavailable; use native printer controls")
                self.state["consumed_intents"].append(value["intent_id"])
                self._status("uncertain", "Cancellation requested; waiting for independent printer confirmation.")
                self.job_adapter.cancel(copy.deepcopy(self.state["job"]), copy.deepcopy(value))
                return self.status()
            if self.state["phase"] not in ("review", "confirmed", "blocked"):
                raise ContractError("No cancellable prepared job")
            self.state["consumed_intents"].append(value["intent_id"])
            self._status("cancelled", "Preparation cancelled. Nothing was sent to the printer.")
        return self.status()

    def poll_job(self):
        if self.state["result"] or self.state["phase"] not in ("starting", "printing", "verifying", "uncertain"):
            return self.status()
        job = self.state.get("job")
        if self.job_adapter is None:
            return self.status()
        try:
            if not job:
                recover = getattr(self.job_adapter, "recover", None)
                pending = self.state.get("pending_start_intent")
                if recover is None or pending is None:
                    return self.status()
                job = recover(copy.deepcopy(self.state["request"]), copy.deepcopy(self.state["prepared"]), copy.deepcopy(pending))
                if job is None:
                    return self.status()
                exact(job, "job_id file_sha256 request_id origin_id", "recovered owned job")
                req, prepared = self.state["request"], self.state["prepared"]
                if (not isinstance(job["job_id"], str) or not job["job_id"]
                        or any(job[key] != req[key] for key in ("request_id", "origin_id"))
                        or job["file_sha256"] != prepared["artifact"]["sha256"]):
                    raise ContractError("Recovered adapter job identity differs")
                self.state["job"] = copy.deepcopy(job)
                self._status("uncertain", "Recovered exact owned job. Verifying independent printer status/history.")
            proof = self.job_adapter.observe(copy.deepcopy(job))
            self.state["monitor"] = None
            exact(proof, "job_id file_sha256 print_state history_state history_job_id history_file_sha256", "independent observation")
            if proof["job_id"] != job["job_id"] or proof["file_sha256"] != job["file_sha256"]:
                raise ContractError("Unrelated job cannot advance calibration")
            monitor_read = getattr(self.job_adapter, "monitor", None)
            if monitor_read is not None:
                monitor = monitor_read(copy.deepcopy(job))
                if isinstance(monitor, dict) and set(monitor) == {"elapsed_s", "progress"}:
                    normalized = {}
                    for key, maximum in (("elapsed_s", 31*86400), ("progress", 1)):
                        value = monitor[key]
                        normalized[key] = value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum else None
                    self.state["monitor"] = normalized
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
            self.state["monitor"] = None
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
            options = flow_ratio_choices(self.state["context"]["effective"]["filament_flow_ratio"], p["pass"])
            unit = "ratio"
        else:
            start, end, step = (Decimal(str(p[k])) for k in ("start", "end", "step"))
            options = [float(start + step * i) for i in range(int((end - start) // step) + 1)]
            unit = {"retraction": "mm", "pressure_advance_pattern": "s", "max_volumetric_speed": "mm³/s"}[kind]
        if not self._current() and len(options) > 128:
            raise ContractError("V1 supports at most 128 result choices. Increase Step or reduce the range.")
        return dict(setting=SETTINGS[kind], options=options, unit=unit)

    def result(self, value):
        req, prepared, proof = self.state["request"], self.state["prepared"], self.state.get("completion")
        current = self._current()
        if current:
            if not req or not prepared:
                raise ContractError("No independently completed original calibration")
            value = validate_result_v2(value, req, prepared)
        else:
            exact(value, "schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value not_applied", "result")
        if ((not current and (value["schema"] != "helix-orca-v1-result/v1" or value["not_applied"] is not True))
                or not req or not prepared or not proof):
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
        self._status("returning", ("Returning the selected result for explicit originating-preset application."
                                   if current else "Returning the selected result to the original Orca context. NOT APPLIED."))
        return copy.deepcopy(value)

    def acknowledge(self, receipt):
        result = self.state["result"]
        if self._current():
            exact(receipt, "schema request_id origin_id result_sha256 application_sha256 status", "V2 application receipt")
            application = self.state.get("application_event")
            application_sha256 = self.state.get("application_digest")
            if (result is None or receipt["schema"] != "helix-orca-v1-ack/v2" or receipt["status"] != "applied"
                    or receipt["request_id"] != result["request_id"] or receipt["origin_id"] != result["origin_id"]
                    or receipt["result_sha256"] != digest(result)
                    or not isinstance(application, dict) or application.get("state") != "applied"
                    or application.get("dirty") is not True or application.get("unsaved") is not True
                    or application.get("transaction_id") != application_sha256
                    or receipt["application_sha256"] != application_sha256):
                raise ContractError("Only the exact originating preset application can acknowledge delivery")
            hex_value(receipt["application_sha256"])
            if self.state.get("receipt") != receipt:
                self.state["receipt"] = copy.deepcopy(receipt)
                self._status("delivered", "Result applied to Orca's edited originating filament preset; save remains the owner's choice.")
            return copy.deepcopy(receipt)
        expected = dict(schema="helix-orca-v1-ack/v1", request_id=result["request_id"], origin_id=result["origin_id"],
                        result_sha256=digest(result), result=result, not_applied=True) if result else None
        if expected is None or canonical(receipt) != canonical(expected):
            raise ContractError("Only the exact originating companion receipt can acknowledge delivery")
        if self.state.get("receipt") != receipt:
            self.state["receipt"] = copy.deepcopy(receipt)
            self._status("delivered", "Result returned to original Orca. NOT APPLIED.")
        return copy.deepcopy(receipt)

    def reconcile_native(self, native):
        """Republish retained authority after a native restart, without an action.

        A repeated marker cannot keep advancing the journal: only an exact equal
        sequence needs a durable version bump; an older reader gets current state.
        """
        req = self.state["request"]
        if (not isinstance(native, dict) or native.get("recovery_required") is not True
                or native.get("phase") != "uncertain" or req is None
                or native.get("request") != req or type(native.get("sequence")) is not int
                or not 0 <= native["sequence"] <= self.state["sequence"]):
            return False
        prepared = self.state["prepared"]
        bindings = {"prepared_sha256": digest(prepared) if prepared else None,
                    "job_id": self.state["job"]["job_id"] if self.state.get("job") else None,
                    "completion_sha256": digest(self.state["completion"]) if self.state.get("completion") else None}
        if any(native.get(key) != expected for key, expected in bindings.items()):
            return False
        if native.get("prepared") != prepared:
            return False
        if native["sequence"] == self.state["sequence"]:
            self._status(self.state["phase"], self.state["message"])
        return True

    def status(self):
        req = self.state["request"]
        if req is None:
            return None
        prepared = self.state["prepared"]
        result = dict(schema="helix-orca-v1-status/v2" if self._current() else "helix-orca-v1-status/v1",
                    request_id=req["request_id"], origin_id=req["origin_id"],
                    sequence=self.state["sequence"], phase=self.state["phase"], message=self.state["message"],
                    prepared=copy.deepcopy(prepared), prepared_sha256=digest(prepared) if prepared else None,
                    job_id=self.state["job"]["job_id"] if self.state.get("job") else None,
                    completion_sha256=digest(self.state["completion"]) if self.state.get("completion") else None,
                    evaluation=self.evaluation() if self.state.get("completion") else None,
                    monitor=copy.deepcopy(self.state.get("monitor")) if self.state["phase"] in ("printing", "verifying", "complete") else None)
        if self._current():
            result.update(warning_ack=copy.deepcopy(self.state.get("warning_ack")),
                          qualification_sha256=(digest(self.state["qualification"])
                                                if self.state.get("qualification") else None))
        return result
