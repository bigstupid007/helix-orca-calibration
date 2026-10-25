"""Owned V1 jobs, never activated by the shipped launcher.

The transport has only bounded private-origin reads, owned G-code upload with
print=false, deliberate Start and owned Cancel. Both action switches default to
False. No RPC/G-code-command, queue editing, profile/config mutation or listener.
The accepted Temperature implementation remains unchanged.
"""
from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import re
import secrets
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, ProxyHandler, build_opener

from integration.v1_contract import ContractError, canonical, digest, exact, hex_value, text, validate_prepared, validate_request
from integration.v1_fit import (FILE_ANALYSIS_SCHEMA, FIT_CHECK_VERSION, HELIXPRINT_VERSION,
    HELIXSCREEN_COMMIT, analysis_record, authorize_findings, check_fit, fit_file,
    machine_limits, require_machine_limits, validate_helix_status, warning_binding)
from integration.v1_runtime import Coordinator, InstanceLock, atomic_json, read_json
from integration.v1_transport import NoRedirect

MAX_BYTES = 20_000_000
JOB_ID = re.compile(r"[0-9A-Fa-f]{6,64}")
OWNED_FILE = re.compile(r"helix-orca-v1-[a-f0-9]{32}-[a-f0-9]{32}\.gcode")
IDENTITY_V1 = "mcu-network/v1"
IDENTITY_V2 = "multi-mcu-network/v2"


def physical_identity(config, system, algorithm):
    """Versioned physical identity; v1 preserves accepted Temperature evidence."""
    network = system.get("network") if isinstance(system, dict) else None
    macs = sorted({item.get("mac_address") for item in (network or {}).values()
                   if isinstance(item, dict) and isinstance(item.get("mac_address"), str)
                   and item.get("mac_address").strip()})
    if not macs:
        raise ContractError("Physical printer network identity unavailable")
    if algorithm == IDENTITY_V1:
        mcu = config.get("mcu", {})
        kind = "serial" if mcu.get("serial") else "canbus_uuid"
        identity = mcu.get(kind)
        if not isinstance(identity, str) or not identity.strip():
            raise ContractError("Historical physical printer MCU identity unavailable")
        value = dict(mcu_kind=kind, mcu_identity=identity, macs=macs)
    elif algorithm == IDENTITY_V2:
        mcus = []
        for section, options in config.items():
            if section != "mcu" and not section.startswith("mcu "):
                continue
            if not isinstance(options, dict):
                raise ContractError("Physical printer MCU configuration unavailable")
            kind = "serial" if options.get("serial") else "canbus_uuid"
            identity = options.get(kind)
            if not isinstance(identity, str) or not identity.strip():
                raise ContractError("Physical printer MCU identity unavailable")
            mcus.append(dict(section=section, kind=kind, identity=identity))
        if not mcus:
            raise ContractError("Physical printer MCU inventory unavailable")
        value = dict(schema="helix-orca-physical-identity/v2",
                     mcus=sorted(mcus, key=lambda item: item["section"]), macs=macs)
    else:
        raise ContractError("Unknown physical identity algorithm")
    return _hash(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _qualification(value, transport, machine):
    exact(value, "schema target_id deployment_mode identity_algorithm physical_identity configuration_sha256 orca_machine_sha256 moonraker_version helixscreen_commit helixprint_version file_analysis_schema fit_checker_version printer_safety_reviewed review_reference", "reviewed printer target qualification")
    if (value["schema"] != "helix-orca-v1-printer-target-qualification/v2"
            or value["deployment_mode"] != "physical" or value["printer_safety_reviewed"] is not True):
        raise ContractError("Explicit physical printer safety review required")
    text(value["target_id"], "printer target ID", 128)
    for key, expected in (("physical_identity", transport.identity),
                          ("configuration_sha256", transport.configuration),
                          ("orca_machine_sha256", machine)):
        if hex_value(value[key]) != expected:
            raise ContractError("Printer target qualification binding differs")
    if (value["identity_algorithm"] != transport.identity_algorithm
            or value["moonraker_version"] != transport.version
            or value["helixscreen_commit"] != HELIXSCREEN_COMMIT
            or value["helixprint_version"] != HELIXPRINT_VERSION
            or value["file_analysis_schema"] != FILE_ANALYSIS_SCHEMA
            or value["fit_checker_version"] != FIT_CHECK_VERSION):
        raise ContractError("Printer target source/API qualification differs")
    text(value["review_reference"], "printer safety review reference", 512)
    return copy.deepcopy(value)


def legacy_request_validator(request, now):
    """Temporary v1 bridge; the shared-contract lane can inject its v2 validator."""
    return validate_request(request, now)


def legacy_candidate_verifier(request, prepared, directory, machine):
    """Verify the pre-amendment prepared/parity envelope.

    Printer target and fit authorization deliberately do not depend on this
    shape. The build-qualification lane replaces only this callback when its v2
    request/prepared fields freeze.
    """
    validate_prepared(prepared, request)
    if prepared["parity"]["qualified"] is not True or prepared["artifact"] is None:
        raise ContractError("Independent native parity qualification required")
    Coordinator.verify_artifact(prepared, directory)
    Coordinator.verify_parity(prepared, directory)
    report = read_json(directory / "parity.json")
    if digest(report) != prepared["parity"]["report_sha256"]:
        raise ContractError("Independent generator qualification report differs")
    inputs = report.get("inputs", {})
    printer = inputs.get("profiles", {}).get("printer")
    nozzle = inputs.get("nozzle_mm")
    if (not isinstance(printer, dict) or not printer or type(nozzle) not in (int, float)
            or not math.isfinite(nozzle) or not 0.05 <= nozzle <= 2):
        raise ContractError("Immutable Orca machine/nozzle identity is unavailable")
    if digest(dict(printer=printer, nozzle_mm=nozzle)) != machine:
        raise ContractError("Orca machine/nozzle differs from the reviewed physical target; upload blocked")
    return (directory / prepared["artifact"]["name"]).read_bytes()


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError("Unavailable " + label)
    return value


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _filename(value):
    if not isinstance(value, str) or OWNED_FILE.fullmatch(value) is None:
        raise ContractError("Only the exact generated owned filename is permitted")
    return value


class PinnedMoonraker:
    """Fixed endpoint transport. Construction makes no connection.

    Existing private-LAN HTTP is an explicit trust envelope, not production TLS
    qualification. Ambient proxies and redirects are disabled, including reads.
    """
    def __init__(self, origin, expected_host, expected_version, physical_identity,
                 configuration_sha256, *, identity_algorithm=IDENTITY_V2,
                 trusted_lan=False, api_key=None, actions=False):
        text(origin, "private origin", 512)
        parsed = urlparse(origin)
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ContractError("Invalid private origin port")
        address = ipaddress.ip_address(expected_host)
        private = isinstance(address, ipaddress.IPv4Address) and any(address in ipaddress.ip_network(n)
            for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
        if not trusted_lan or not private or parsed.scheme != "http" or parsed.hostname != expected_host or parsed.path not in ("", "/") or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ContractError("Explicit exact existing private-LAN HTTP trust required")
        if type(actions) is not bool:
            raise ContractError("Actions must be a separate local boolean")
        self.origin = origin.rstrip("/")
        self.version = text(expected_version, "pinned Moonraker version", 128)
        self.identity = hex_value(physical_identity)
        self.configuration = hex_value(configuration_sha256)
        if identity_algorithm not in (IDENTITY_V1, IDENTITY_V2):
            raise ContractError("Unknown physical identity algorithm")
        self.identity_algorithm = identity_algorithm
        if api_key is not None:
            text(api_key, "existing API credential", 4096)
        self.api_key, self.actions = api_key, actions
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _wire(self, path, *, data=None, content_type=None, missing=False, raw=False):
        # All callers below construct fixed routes from validated owned names/IDs.
        headers = {"Accept": "application/octet-stream" if raw else "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        if content_type:
            headers["Content-Type"] = content_type
        limit = MAX_BYTES if raw else 1_048_576
        try:
            with self.opener.open(Request(self.origin + path, data=data, headers=headers,
                    method="POST" if data is not None else "GET"), timeout=5) as response:
                result = response.read(limit + 1)
        except HTTPError as exc:
            if missing and exc.code == 404:
                return None
            raise ContractError("Bounded Moonraker request failed") from exc
        if len(result) > limit:
            raise ContractError("Moonraker response exceeds bound")
        if raw:
            return result
        value = json.loads(result)
        canonical(value)
        if not isinstance(value, dict) or "result" not in value:
            raise ContractError("Moonraker result unavailable")
        return value["result"]

    def snapshot(self):
        began = time.monotonic()
        server = self._wire("/server/info")
        if server.get("moonraker_version") != self.version or server.get("klippy_state") != "ready" or server.get("failed_components"):
            raise ContractError("Pinned Moonraker version/readiness differs")
        system = self._wire("/machine/system_info")["system_info"]
        config = self._wire("/printer/objects/query?configfile")["status"]["configfile"]["settings"]
        config_hash = _hash(json.dumps(config, sort_keys=True, separators=(",", ":")).encode())
        physical = physical_identity(config, system, self.identity_algorithm)
        if config_hash != self.configuration or physical != self.identity:
            raise ContractError("Physical printer/configuration identity differs")
        fit_machine = require_machine_limits(machine_limits(config))
        queue = self._wire("/server/job_queue/status")
        if not isinstance(queue.get("queued_jobs"), list) or queue.get("queue_state") not in ("paused", "ready"):
            raise ContractError("Queue transition or unavailable queue")
        first = self._wire("/printer/objects/query?print_stats")
        stats = first["status"]["print_stats"]
        filename = stats.get("filename") or None
        metadata = self.metadata(filename) if filename and OWNED_FILE.fullmatch(filename) else None
        final = self._wire("/printer/objects/query?print_stats&virtual_sdcard")
        if any(final["status"]["print_stats"].get(k) != stats.get(k) for k in ("filename", "state")) or time.monotonic() - began > 5:
            raise ContractError("Printer changed during bounded snapshot")
        if stats.get("state") not in ("standby", "printing", "paused", "complete", "cancelled", "error"):
            raise ContractError("Unknown printer state")
        latest = final["status"]["print_stats"]
        elapsed = latest.get("total_duration")
        elapsed = float(elapsed) if type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= 31*86400 else None
        sd = final["status"].get("virtual_sdcard", {})
        progress = sd.get("progress") if isinstance(sd, dict) else None
        sd_path = sd.get("file_path") if isinstance(sd, dict) else None
        if (not isinstance(sd_path, str) or sd_path.rsplit("/", 1)[-1] != filename
                or type(progress) not in (int, float) or not math.isfinite(progress) or not 0 <= progress <= 1):
            progress = None
        return dict(eventtime=_number(final["eventtime"], "printer eventtime"), state=stats["state"], filename=filename,
            monitor=dict(elapsed_s=elapsed, progress=progress),
            job_id=metadata.get("job_id") if metadata else None, start_time=metadata.get("print_start_time") if metadata else None,
            queue_job_ids=tuple(j["job_id"] for j in queue["queued_jobs"]), physical_identity=physical,
            identity_algorithm=self.identity_algorithm, configuration_sha256=config_hash,
            fit_machine=fit_machine)

    def helix_status(self):
        return self._wire("/server/helix/status")

    def analysis(self, filename):
        return self._wire("/server/helix/analysis?filename=" + quote(_filename(filename), safe=""))

    def metadata(self, filename):
        value = self._wire("/server/files/metadata?filename=" + quote(_filename(filename), safe=""), missing=True)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ContractError("Owned file metadata unavailable")
        if value.get("job_id") is not None and (not isinstance(value["job_id"], str) or JOB_ID.fullmatch(value["job_id"]) is None):
            raise ContractError("Malformed metadata job ID")
        if value.get("print_start_time") is not None:
            _number(value["print_start_time"], "metadata start time")
        if value.get("size") is not None and (type(value["size"]) is not int or value["size"] <= 0):
            raise ContractError("Malformed metadata file size")
        if value.get("modified") is not None:
            _number(value["modified"], "metadata modified time")
        return value

    def file(self, filename, *, missing=False):
        return self._wire("/server/files/gcodes/" + quote(_filename(filename), safe=""), missing=missing, raw=True)

    @staticmethod
    def _history_record(value):
        if not isinstance(value, dict) or not isinstance(value.get("job_id"), str) or JOB_ID.fullmatch(value["job_id"]) is None:
            raise ContractError("History job identity unavailable")
        text(value.get("filename"), "history filename", 512)
        _number(value.get("start_time"), "history start time")
        if value.get("end_time") is not None:
            _number(value["end_time"], "history end time")
        if value.get("status") not in ("in_progress", "completed", "cancelled", "error", "interrupted", "klippy_shutdown", "klippy_disconnect"):
            raise ContractError("History status unavailable")
        return value

    def history(self, job_id=None):
        if job_id is None:
            jobs = self._wire("/server/history/list?limit=1&order=desc")["jobs"]
            if not isinstance(jobs, list) or len(jobs) > 1:
                raise ContractError("History baseline unavailable")
            return self._history_record(jobs[0]) if jobs else None
        if not isinstance(job_id, str) or JOB_ID.fullmatch(job_id) is None:
            raise ContractError("Invalid exact history job ID")
        value = self._wire("/server/history/job?uid=" + quote(job_id, safe=""), missing=True)
        return self._history_record(value["job"]) if value else None

    def _enabled(self):
        if self.actions is not True:
            raise ContractError("Physical actions disabled; no mutation requested")

    def upload(self, filename, data):
        self._enabled()
        _filename(filename)
        if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
            raise ContractError("Upload outside bounded artifact envelope")
        boundary = "helix_orca_v1_" + secrets.token_hex(16)
        while boundary.encode() in data:
            boundary = "helix_orca_v1_" + secrets.token_hex(16)
        parts = []
        for name, value in (("root", "gcodes"), ("print", "false")):
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode())
        parts += [(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode(), data, f"\r\n--{boundary}--\r\n".encode()]
        result = self._wire("/server/files/upload", data=b"".join(parts), content_type="multipart/form-data; boundary=" + boundary)
        if not isinstance(result, dict) or result.get("print_started") is not False or result.get("print_queued") is not False or result.get("item", {}).get("path") != filename or result.get("item", {}).get("root") != "gcodes":
            raise ContractError("Upload acknowledgement is not exact owned no-print/no-queue staging")

    def start(self, filename):
        self._enabled()
        if self._wire("/printer/print/start?filename=" + quote(_filename(filename), safe=""), data=b"") != "ok":
            raise ContractError("Start acknowledgement unavailable; retry forbidden")

    def cancel(self):
        self._enabled()
        if self._wire("/printer/print/cancel", data=b"") != "ok":
            raise ContractError("Cancel acknowledgement unavailable; retry forbidden")


class OwnedJobAdapter:
    """Private durable one-shot ownership. No automatic crash recovery dispatch.

    The deployment integrator must retain a single adapter journal root and both
    local action gates, and notify confirm before calling start. Shipped CLI does
    not instantiate this class. No wire field may enable actions.
    """
    def __init__(self, transport, root, *, orca_machine_sha256, physical_qualification=None,
                 candidate_verifier=None, request_validator=None, actions=False,
                 warning_acknowledger=None,
                 now=time.time, monotonic=time.monotonic, sleep=time.sleep):
        if type(actions) is not bool:
            raise ContractError("Actions must be a separate local boolean")
        self.machine = hex_value(orca_machine_sha256)
        self.qualification = _qualification(physical_qualification, transport, self.machine)
        self.qualification_sha256 = digest(self.qualification)
        self.transport, self.root, self.actions = transport, Path(root), actions
        self.candidate_verifier = candidate_verifier or legacy_candidate_verifier
        self.request_validator = request_validator or legacy_request_validator
        self.warning_acknowledger = warning_acknowledger
        if (not callable(self.candidate_verifier) or not callable(self.request_validator)
                or warning_acknowledger is not None and not callable(warning_acknowledger)):
            raise ContractError("Typed candidate/request validators required")
        self.now, self.monotonic, self.sleep = now, monotonic, sleep
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ContractError("Symlink adapter journal refused")

    def _path(self, request_id):
        return self.root / (hex_value(request_id, 32) + ".json")

    def _read(self, request_id):
        path = self._path(request_id)
        if path.is_symlink():
            raise ContractError("Symlink job journal refused")
        record = read_json(path)
        if record.get("schema") != "helix-orca-v1-owned-job/v1" or record.get("request", {}).get("request_id") != request_id:
            raise ContractError("Owned job journal unavailable")
        _filename(record["filename"])
        return record

    def _save(self, record):
        atomic_json(self._path(record["request"]["request_id"]), record)
        if record["phase"] != "confirmed":
            atomic_json(self.root / "active.json", dict(request_id=record["request"]["request_id"], phase=record["phase"]))

    def _snapshot(self, record):
        sample = self.transport.snapshot()
        q = self.qualification
        if (sample.get("physical_identity") != q["physical_identity"]
                or sample.get("identity_algorithm") != q["identity_algorithm"]
                or sample.get("configuration_sha256") != q["configuration_sha256"]):
            raise ContractError("Live printer target identity/configuration differs")
        require_machine_limits(sample.get("fit_machine"))
        return sample

    @staticmethod
    def _intent(request, prepared, intent, action):
        exact(intent, "schema request_id origin_id prepared_sha256 action intent_id", "native job intent")
        if intent["schema"] != "helix-orca-v1-intent/v1" or intent["action"] != action or any(intent[k] != request[k] for k in ("request_id", "origin_id")) or intent["prepared_sha256"] != digest(prepared):
            raise ContractError("Native intent differs from exact prepared job")
        hex_value(intent["intent_id"], 32)

    def _candidate(self, request, prepared, directory):
        self.request_validator(request, self.now())
        directory = Path(directory)
        if directory.is_symlink() or directory.name != request["request_id"]:
            raise ContractError("Exact request-owned artifact directory required")
        data = self.candidate_verifier(request, prepared, directory, self.machine)
        if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
            raise ContractError("Owned upload supports at most 20 MB")
        return data, _hash(data)

    def _fit_ready(self, filename, data, machine, request, prepared, intent):
        """Require beta.12 analysis of the exact uploaded bytes, fail closed."""
        validate_helix_status(self.transport.helix_status(), self.qualification)
        deadline = self.monotonic() + 30
        while True:
            reply = self.transport.analysis(filename)
            if isinstance(reply, dict) and reply.get("status") == "pending" and self.monotonic() < deadline:
                self.sleep(0.25)
                continue
            metadata = self.transport.metadata(filename)
            record = analysis_record(reply, filename, metadata)
            if record["file_size"] != len(data):
                raise ContractError("Analyzed file size differs from prepared artifact")
            findings = check_fit(machine, fit_file(record))
            binding = warning_binding(findings, target_id=self.qualification["target_id"],
                request_id=request["request_id"], prepared_sha256=digest(prepared),
                file_sha256=_hash(data))
            acknowledgement = None
            if (not any(item.get("severity") == "block" for item in findings)
                    and any(item.get("severity") == "warn" for item in findings)
                    and self.warning_acknowledger is not None):
                acknowledgement = self.warning_acknowledger(copy.deepcopy(request),
                    copy.deepcopy(prepared), copy.deepcopy(intent), copy.deepcopy(binding))
            findings = authorize_findings(findings, acknowledgement, binding=binding)
            return dict(schema="helix-orca-v1-fit-evidence/v1", filename=filename,
                        analysis_sha256=digest(record), findings=findings,
                        warning_acknowledgement_sha256=(digest(acknowledgement)
                            if acknowledgement is not None else None))

    def confirm(self, request, prepared, directory, intent):
        self._intent(request, prepared, intent, "confirm")
        _, candidate_sha256 = self._candidate(request, prepared, directory)
        with InstanceLock(self.root / "adapter.lock"):
            if self._path(request["request_id"]).exists():
                record = self._read(request["request_id"])
                if record["request"] == request and record["prepared"] == prepared and record["confirm"] == intent and record["phase"] == "confirmed" and record.get("qualification_sha256") == self.qualification_sha256 and record.get("candidate_sha256") == candidate_sha256:
                    return
                raise ContractError("Existing one-shot job cannot be replaced")
            record = dict(schema="helix-orca-v1-owned-job/v1", request=copy.deepcopy(request), prepared=copy.deepcopy(prepared),
                confirm=copy.deepcopy(intent), filename="helix-orca-v1-" + request["request_id"] + "-" + secrets.token_hex(16) + ".gcode",
                phase="confirmed", start=None, cancel=None, job=None, last_eventtime=None,
                baseline=None, ownership_confirmed=False, fit_evidence=None,
                target_id=self.qualification["target_id"])
            record.update(qualification_sha256=self.qualification_sha256,
                          candidate_sha256=candidate_sha256)
            self._save(record)

    def _enabled(self):
        if self.actions is not True or getattr(self.transport, "actions", False) is not True:
            raise ContractError("Physical actions disabled; separate deployment approval required")

    @staticmethod
    def _idle(sample):
        if sample["state"] != "standby" or sample["filename"] is not None or sample["job_id"] is not None or sample["start_time"] is not None or sample["queue_job_ids"]:
            raise ContractError("Start requires idle printer with empty queue and no current job")

    @staticmethod
    def _matching(sample, record):
        owned = record["job"]
        return owned is not None and sample["filename"] == record["filename"] and sample["job_id"] == owned["job_id"] and sample["start_time"] == owned["start_time"]

    @staticmethod
    def _history_matches(history, record, status):
        owned = record["job"]
        return bool(history and owned and history.get("job_id") == owned["job_id"] and history.get("filename") == record["filename"] and history.get("start_time") == owned["start_time"] and history.get("status") == status)

    @staticmethod
    def _fresh(sample, record):
        stamp = _number(sample["eventtime"], "printer eventtime")
        if record["last_eventtime"] is not None and stamp <= record["last_eventtime"]:
            raise ContractError("Repeated or backward printer snapshot")
        record["last_eventtime"] = stamp

    def _public_job(self, record):
        return dict(job_id=record["job"]["job_id"], file_sha256=record["candidate_sha256"],
            request_id=record["request"]["request_id"], origin_id=record["request"]["origin_id"])

    def start(self, request, prepared, directory, intent):
        self._enabled()
        self._intent(request, prepared, intent, "start")
        data, candidate_sha256 = self._candidate(request, prepared, directory)
        with InstanceLock(self.root / "adapter.lock"):
            record = self._read(request["request_id"])
            self._intent(request, prepared, record["confirm"], "confirm")
            if (record["request"] != request or record["prepared"] != prepared
                    or record["phase"] != "confirmed"
                    or intent["intent_id"] == record["confirm"]["intent_id"]
                    or record.get("qualification_sha256") != self.qualification_sha256
                    or record.get("candidate_sha256") != candidate_sha256
                    or record.get("target_id") != self.qualification["target_id"]):
                raise ContractError("Start requires distinct retained native Confirm; retry prohibited")
            active_path = self.root / "active.json"
            if active_path.exists():
                if active_path.is_symlink():
                    raise ContractError("Symlink active journal refused")
                active = read_json(active_path)
                exact(active, "request_id phase", "active owned job")
                hex_value(active["request_id"], 32)
                if active["request_id"] != request["request_id"] and active["phase"] not in ("complete", "cancelled", "error"):
                    raise ContractError("Earlier owned job remains unresolved; new dispatch blocked")
            sample = self._snapshot(record); self._idle(sample); self._fresh(sample, record)
            record["baseline"] = self.transport.history()
            filename = record["filename"]
            if self.transport.metadata(filename) is not None or self.transport.file(filename, missing=True) is not None:
                raise ContractError("Owned staging filename already exists; overwrite refused")
            record.update(phase="upload-intent", start=copy.deepcopy(intent)); self._save(record)
            try:
                self.transport.upload(filename, data)
                if self.transport.file(filename) != data:
                    raise ContractError("Uploaded bytes differ from prepared artifact")
                sample = self._snapshot(record); self._idle(sample); self._fresh(sample, record)
                record["fit_evidence"] = self._fit_ready(filename, data, sample["fit_machine"],
                    request, prepared, intent)
                if self.transport.file(filename) != data:
                    raise ContractError("Uploaded bytes changed during file-fit analysis")
                sample = self._snapshot(record); self._idle(sample); self._fresh(sample, record)
                self.request_validator(request, self.now())
                record["phase"] = "start-intent"; self._save(record)
                self.transport.start(filename)
                deadline = self.monotonic() + 30
                while self.monotonic() < deadline:
                    sample = self._snapshot(record); self._fresh(sample, record)
                    if sample["queue_job_ids"]:
                        raise ContractError("Queue changed during owned start")
                    if sample["state"] == "printing" and sample["filename"] == filename and sample["job_id"] and sample["start_time"] is not None:
                        job_id = sample["job_id"]
                        if not isinstance(job_id, str) or JOB_ID.fullmatch(job_id) is None:
                            raise ContractError("Owned job ID unavailable")
                        _number(sample["start_time"], "owned job start")
                        baseline = record["baseline"]
                        if baseline and (job_id == baseline.get("job_id") or sample["start_time"] <= _number(baseline.get("start_time"), "baseline history start")):
                            raise ContractError("Stale prior job metadata cannot establish ownership")
                        record["job"] = dict(job_id=job_id, start_time=sample["start_time"])
                        if self._history_matches(self.transport.history(job_id), record, "in_progress"):
                            record.update(phase="printing", ownership_confirmed=True); self._save(record)
                            return self._public_job(record)
                    elif sample["state"] != "standby":
                        raise ContractError("Unexpected job during owned start")
                    self._save(record)
                    self.sleep(0.25)
                raise ContractError("Actual owned start not independently confirmed within 30 seconds")
            except Exception:
                record["phase"] = "uncertain"; self._save(record)
                raise

    def _owned(self, job):
        exact(job, "job_id file_sha256 request_id origin_id", "owned job handle")
        record = self._read(job["request_id"])
        self._intent(record["request"], record["prepared"], record["confirm"], "confirm")
        self._intent(record["request"], record["prepared"], record["start"], "start")
        if not record["job"] or self._public_job(record) != job or record.get('ownership_confirmed') is not True or record.get('qualification_sha256') != self.qualification_sha256:
            raise ContractError("Unrelated job handle refused")
        return record

    def recover(self, request, prepared, intent):
        """Adopt only an already independently confirmed durable owned job.

        Read-only and idempotent: no dispatch, retries, journal writes or HTTP.
        Fresh observation remains mandatory after the coordinator adopts it.
        """
        self._intent(request, prepared, intent, 'start')
        with InstanceLock(self.root / 'adapter.lock'):
            if self._path(request['request_id']).is_symlink():
                raise ContractError('Symlink job journal refused')
            if not self._path(request['request_id']).exists():
                return None
            record = self._read(request['request_id'])
            if record['request'] != request or record['prepared'] != prepared or record.get('qualification_sha256') != self.qualification_sha256:
                raise ContractError('Recovery request/prepared/physical qualification differs')
            self._intent(request, prepared, record['confirm'], 'confirm')
            if record['start'] is None:
                return None
            self._intent(request, prepared, record['start'], 'start')
            if record['start'] != intent or record['start']['intent_id'] == record['confirm']['intent_id']:
                raise ContractError('Recovery requires the exact retained distinct native Start intent')
            if record['phase'] not in ('printing', 'complete', 'cancelled', 'error', 'cancel-intent', 'cancel-pending', 'cancel-uncertain') or record['job'] is None or record.get('ownership_confirmed') is not True:
                return None
            exact(record['job'], 'job_id start_time', 'durable independently confirmed job')
            if not isinstance(record['job']['job_id'], str) or JOB_ID.fullmatch(record['job']['job_id']) is None:
                raise ContractError('Durable owned job ID unavailable')
            _number(record['job']['start_time'], 'durable owned job start')
            return self._public_job(record)

    def monitor(self, job):
        """Display-only data from this exact job's most recent successful observe."""
        retained = getattr(self, "_last_monitor", None)
        return copy.deepcopy(retained["value"]) if retained and retained["job"] == job else None

    def observe(self, job):
        self._last_monitor = None
        with InstanceLock(self.root / "adapter.lock"):
            record = self._owned(job)
            sample = self._snapshot(record); self._fresh(sample, record)
            if not self._matching(sample, record):
                raise ContractError("Printer changed away from exact owned job")
            history = self.transport.history(job["job_id"])
            state = sample["state"]
            proof = dict(job_id=job["job_id"], file_sha256=job["file_sha256"], print_state="unknown",
                history_state=None, history_job_id=None, history_file_sha256=None)
            expected = {"printing": "in_progress", "complete": "completed", "cancelled": "cancelled", "error": "error"}.get(state)
            if record["cancel"] is not None and state != "cancelled":
                # An acknowledged Cancel is not cancellation proof. In particular,
                # a racing completed print never silently reverses cancellation.
                record["phase"] = "cancel-uncertain"
            elif expected is not None and self._history_matches(history, record, expected):
                ended = history.get("end_time")
                if state != "printing" and (ended is None or _number(ended, "history end") <= record["job"]["start_time"]):
                    raise ContractError("Independent terminal history lacks valid end time")
                if _hash(self.transport.file(record["filename"])) != job["file_sha256"]:
                    raise ContractError("Owned remote file changed")
                proof.update(print_state=state, history_state=expected, history_job_id=job["job_id"], history_file_sha256=job["file_sha256"])
                record["phase"] = state
            elif state == "complete":
                proof["print_state"] = "complete"  # Runtime keeps evaluation locked pending history.
            self._save(record)
            if proof["print_state"] in ("printing", "complete") and proof["history_job_id"] == job["job_id"]:
                self._last_monitor = dict(job=copy.deepcopy(job), value=copy.deepcopy(sample.get("monitor")))
            return proof

    def cancel(self, job, intent):
        self._enabled()
        with InstanceLock(self.root / "adapter.lock"):
            record = self._owned(job)
            self._intent(record["request"], record["prepared"], intent, "cancel")
            if record["phase"] != "printing" or record["cancel"] is not None or intent["intent_id"] in (record["confirm"]["intent_id"], record["start"]["intent_id"]):
                raise ContractError("Owned cancellation is one-shot and requires separate native intent")
            for _ in range(2):
                sample = self._snapshot(record); self._fresh(sample, record)
                if sample["state"] != "printing" or sample["queue_job_ids"] or not self._matching(sample, record) or not self._history_matches(self.transport.history(job["job_id"]), record, "in_progress"):
                    raise ContractError("Cancellation target is not the same independently owned running job")
            record.update(phase="cancel-intent", cancel=copy.deepcopy(intent)); self._save(record)
            try:
                self.transport.cancel()
            except Exception:
                record["phase"] = "cancel-uncertain"; self._save(record)
                raise
            record["phase"] = "cancel-pending"; self._save(record)


def from_config(config: dict, root: Path, *, deployment_authorized: bool = False,
                api_key: str | None = None, candidate_verifier=None,
                request_validator=None, warning_acknowledger=None) -> OwnedJobAdapter | None:
    """Construct only an explicitly physical, locally authorized target.

    The caller must derive deployment_authorized from a separate explicit local
    deployment approval, never native requests, Orca exports, or inbound events.
    A generation-only target is validated and always returns ``None`` before a
    transport exists, so no later wire value can promote it to physical actions.
    """
    if not isinstance(config, dict) or type(deployment_authorized) is not bool:
        raise ContractError("Typed private configuration/local authorization required")
    value = config.get("owned_jobs")
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("schema") != "helix-orca-v1-job-deployment/v2":
        raise ContractError("Malformed owned-job deployment schema")
    mode = value.get("deployment_mode")
    if mode == "generation-only":
        exact(value, "schema target_id deployment_mode orca_machine_sha256 actions_enabled", "generation-only printer target")
        text(value["target_id"], "printer target ID", 128)
        hex_value(value["orca_machine_sha256"])
        if value["actions_enabled"] is not False:
            raise ContractError("Generation-only target can never enable physical actions")
        return None
    exact(value, "schema target_id deployment_mode origin expected_host expected_version physical_identity identity_algorithm configuration_sha256 orca_machine_sha256 physical_qualification existing_trusted_lan_ack actions_enabled", "private owned-job deployment")
    if (mode != "physical" or type(value["existing_trusted_lan_ack"]) is not bool
            or type(value["actions_enabled"]) is not bool):
        raise ContractError("Malformed owned-job deployment safety flags")
    text(value["target_id"], "printer target ID", 128)
    machine = hex_value(value["orca_machine_sha256"])
    # Construction validates pins/origin but makes no request or filesystem write.
    transport = PinnedMoonraker(value["origin"], value["expected_host"], value["expected_version"],
        value["physical_identity"], value["configuration_sha256"], identity_algorithm=value["identity_algorithm"],
        trusted_lan=value["existing_trusted_lan_ack"], api_key=api_key, actions=False)
    qualification = _qualification(value['physical_qualification'], transport, machine)
    if qualification["target_id"] != value["target_id"] or qualification["deployment_mode"] != mode:
        raise ContractError("Deployment and target qualification differ")
    if not deployment_authorized or not value["actions_enabled"]:
        return None
    transport.actions = True
    return OwnedJobAdapter(transport, root, orca_machine_sha256=machine,
        physical_qualification=qualification, candidate_verifier=candidate_verifier,
        request_validator=request_validator, warning_acknowledger=warning_acknowledger,
        actions=True)
