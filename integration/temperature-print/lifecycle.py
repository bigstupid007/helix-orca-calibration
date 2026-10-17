"""Fail-closed, transport-independent Temperature print lifecycle.

This module contains no Moonraker transport and performs no hardware action by
itself.  A caller must provide both a normalized adapter and a locally-created
``PhysicalPermit``.  The durable journal is deliberately one-shot: recovery
may observe an already-dispatched operation, but can never dispatch it again.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


REQUEST_SCHEMA = "helix-orca-temperature-print-session/v1"
QUALIFICATION_SCHEMA = "helix-orca-temperature-gcode-qualification/v1"
START_SCHEMA = "helix-orca-temperature-start/v1"
JOURNAL_SCHEMA = "helix-orca-temperature-print-journal/v1"
COMPLETION_PROOF_SCHEMA = "helix-orca-temperature-completion-proof/v1"
CHOICES = (210, 205, 200)
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ESTIMATED_DURATION_S = 20 * 60
MAX_REQUEST_TTL_S = 60 * 60
MAX_START_LIFETIME_S = 15 * 60
START_CONFIRMATION_TIMEOUT_S = 30.0
COMPLETION_CONFIRMATION_TIMEOUT_S = 30.0
CANCEL_CONFIRMATION_TIMEOUT_S = 30.0
RUN_OVERRUN_GRACE_S = 5 * 60

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_NONCE = re.compile(r"^([0-9a-f]{32}):([0-9]{1,20})$")
_PERMIT_TOKEN = object()


class LifecycleError(RuntimeError):
    """Base error for validation, safety, and lifecycle failures."""


class ValidationError(LifecycleError):
    """An input or normalized adapter response is malformed."""


class SafetyViolation(LifecycleError):
    """A fail-closed safety gate rejected an operation."""


class JournalError(LifecycleError):
    """The durable one-shot journal is unavailable or malformed."""


def _finite_number(value: Any, name: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValidationError(f"{name} must be a finite number >= {minimum}")
    return result


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValidationError(f"{name} is outside {minimum}..{maximum}")
    return value


def _string(value: Any, name: str, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        raise ValidationError(f"{name} must be a non-empty bounded string")
    return value


def _hex(value: Any, pattern: re.Pattern[str], name: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValidationError(f"{name} has an invalid lowercase hexadecimal value")
    return value


def _file_name(value: Any) -> str:
    name = _string(value, "file", 255)
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise ValidationError("file must be a base name without path separators")
    return name


def _choices(value: Any) -> tuple[int, int, int]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValidationError("choices must be the exact three-band sequence")
    converted = tuple(value)
    if converted != CHOICES:
        raise ValidationError("choices must be exactly [210, 205, 200]")
    return CHOICES


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class BoundRequest:
    request_id: str
    origin_id: str
    context_sha256: str
    file_sha256: str
    file: str
    file_bytes: int
    printer: str
    choices: tuple[int, int, int]
    expires_at: int
    ttl_seconds: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], now_wall: float) -> "BoundRequest":
        if not isinstance(value, Mapping):
            raise ValidationError("request must be an object")
        for forbidden in ("authorized", "physical_authorized", "permit", "start"):
            if forbidden in value:
                raise ValidationError(f"wire request may not contain {forbidden}")
        if value.get("schema") != REQUEST_SCHEMA:
            raise ValidationError(f"request schema must be {REQUEST_SCHEMA}")
        if value.get("physical_calibration") is not True:
            raise ValidationError("request must explicitly identify physical calibration")
        if value.get("not_applied") is not True:
            raise ValidationError("request must preserve NOT APPLIED behavior")
        request = cls(
            request_id=_hex(value.get("request_id"), _HEX32, "request_id"),
            origin_id=_hex(value.get("origin_id"), _HEX32, "origin_id"),
            context_sha256=_hex(value.get("context_sha256"), _HEX64, "context_sha256"),
            file_sha256=_hex(value.get("file_sha256"), _HEX64, "file_sha256"),
            file=_file_name(value.get("file")),
            file_bytes=_integer(value.get("file_bytes"), "file_bytes", 1, MAX_FILE_BYTES),
            printer=_string(value.get("printer"), "printer", 512),
            choices=_choices(value.get("choices")),
            expires_at=_integer(value.get("expires_at"), "expires_at", 1, 4_102_444_800),
            ttl_seconds=_integer(value.get("ttl_seconds"), "ttl_seconds", 1, MAX_REQUEST_TTL_S),
        )
        if request.ttl_seconds != MAX_REQUEST_TTL_S:
            raise ValidationError("print request ttl_seconds must be exactly 3600")
        if request.expires_at <= now_wall:
            raise ValidationError("print request is stale")
        if request.expires_at > now_wall + request.ttl_seconds:
            raise ValidationError("print request expiry exceeds its original lifetime")
        return request

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "origin_id": self.origin_id,
            "context_sha256": self.context_sha256,
            "file_sha256": self.file_sha256,
            "file": self.file,
            "file_bytes": self.file_bytes,
            "printer": self.printer,
            "choices": list(self.choices),
            "expires_at": self.expires_at,
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass(frozen=True)
class GcodeQualification:
    request_id: str
    origin_id: str
    context_sha256: str
    file_sha256: str
    file: str
    file_bytes: int
    printer: str
    physical_printer_identity: str
    choices: tuple[int, int, int]
    estimated_duration_s: float

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GcodeQualification":
        if not isinstance(value, Mapping) or value.get("schema") != QUALIFICATION_SCHEMA:
            raise ValidationError(f"qualification schema must be {QUALIFICATION_SCHEMA}")
        required_true = (
            "suitable",
            "geometry_verified",
            "temperature_commands_verified",
            "temperature_order_verified",
            "file_identity_verified",
        )
        for name in required_true:
            if value.get(name) is not True:
                raise ValidationError(f"qualification did not prove {name}")
        if value.get("band_count") != 3:
            raise ValidationError("qualification must prove exactly three bands")
        duration = _finite_number(
            value.get("estimated_duration_s"), "estimated_duration_s", 0.001
        )
        if duration > MAX_ESTIMATED_DURATION_S:
            raise ValidationError("qualified duration exceeds the 20-minute maximum")
        return cls(
            request_id=_hex(value.get("request_id"), _HEX32, "qualification request_id"),
            origin_id=_hex(value.get("origin_id"), _HEX32, "qualification origin_id"),
            context_sha256=_hex(
                value.get("context_sha256"), _HEX64, "qualification context_sha256"
            ),
            file_sha256=_hex(value.get("file_sha256"), _HEX64, "qualification file_sha256"),
            file=_file_name(value.get("file")),
            file_bytes=_integer(
                value.get("file_bytes"), "qualification file_bytes", 1, MAX_FILE_BYTES
            ),
            printer=_string(value.get("printer"), "qualification printer", 512),
            physical_printer_identity=_hex(
                value.get("physical_printer_identity"),
                _HEX64,
                "qualification physical_printer_identity",
            ),
            choices=_choices(value.get("choices")),
            estimated_duration_s=duration,
        )

    def assert_matches(self, request: BoundRequest) -> None:
        for name in (
            "request_id",
            "origin_id",
            "context_sha256",
            "file_sha256",
            "file",
            "file_bytes",
            "printer",
            "choices",
        ):
            if getattr(self, name) != getattr(request, name):
                raise ValidationError(f"qualification {name} does not match request")

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "origin_id": self.origin_id,
            "context_sha256": self.context_sha256,
            "file_sha256": self.file_sha256,
            "file": self.file,
            "file_bytes": self.file_bytes,
            "printer": self.printer,
            "physical_printer_identity": self.physical_printer_identity,
            "choices": list(self.choices),
            "estimated_duration_s": self.estimated_duration_s,
        }


@dataclass(frozen=True)
class StartIntent:
    request_id: str
    origin_id: str
    context_sha256: str
    file_sha256: str
    file: str
    file_bytes: int
    printer: str
    choices: tuple[int, int, int]
    nonce: str
    eventtime: float
    expires_eventtime: float

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StartIntent":
        if not isinstance(value, Mapping) or value.get("schema") != START_SCHEMA:
            raise ValidationError(f"start intent schema must be {START_SCHEMA}")
        expected_keys = {
            "schema",
            "request_id",
            "origin_id",
            "context_sha256",
            "file_sha256",
            "file",
            "file_bytes",
            "printer",
            "choices",
            "nonce",
            "eventtime",
            "expires_eventtime",
        }
        if set(value) != expected_keys:
            raise ValidationError("start intent must have the exact bounded key set")
        for forbidden in ("authorized", "physical_authorized", "permit"):
            if forbidden in value:
                raise ValidationError(f"start intent may not contain {forbidden}")
        eventtime = _finite_number(value.get("eventtime"), "eventtime")
        expires = _finite_number(value.get("expires_eventtime"), "expires_eventtime")
        if expires <= eventtime or expires - eventtime > MAX_START_LIFETIME_S:
            raise ValidationError("start intent lifetime must be within 900 seconds")
        request_id = _hex(value.get("request_id"), _HEX32, "start request_id")
        nonce = _string(value.get("nonce"), "nonce", 80)
        match = _NONCE.fullmatch(nonce)
        if match is None or match.group(1) != request_id:
            raise ValidationError("nonce must bind the exact request_id")
        try:
            micros = int(
                (Decimal(str(eventtime)) * Decimal(1_000_000)).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            )
        except (InvalidOperation, ValueError):
            raise ValidationError("nonce eventtime is invalid") from None
        if int(match.group(2)) != micros:
            raise ValidationError("nonce must bind the sampled eventtime in microseconds")
        return cls(
            request_id=request_id,
            origin_id=_hex(value.get("origin_id"), _HEX32, "start origin_id"),
            context_sha256=_hex(value.get("context_sha256"), _HEX64, "start context_sha256"),
            file_sha256=_hex(value.get("file_sha256"), _HEX64, "start file_sha256"),
            file=_file_name(value.get("file")),
            file_bytes=_integer(value.get("file_bytes"), "start file_bytes", 1, MAX_FILE_BYTES),
            printer=_string(value.get("printer"), "start printer", 512),
            choices=_choices(value.get("choices")),
            nonce=nonce,
            eventtime=eventtime,
            expires_eventtime=expires,
        )

    def assert_matches(self, request: BoundRequest) -> None:
        for name in (
            "request_id",
            "origin_id",
            "context_sha256",
            "file_sha256",
            "file",
            "file_bytes",
            "printer",
            "choices",
        ):
            if getattr(self, name) != getattr(request, name):
                raise ValidationError(f"start intent {name} does not match request")

    def as_dict(self) -> dict[str, Any]:
        result = {
            "request_id": self.request_id,
            "origin_id": self.origin_id,
            "context_sha256": self.context_sha256,
            "file_sha256": self.file_sha256,
            "file": self.file,
            "file_bytes": self.file_bytes,
            "printer": self.printer,
            "choices": list(self.choices),
            "nonce": self.nonce,
            "eventtime": self.eventtime,
            "expires_eventtime": self.expires_eventtime,
        }
        return result


@dataclass(frozen=True, init=False)
class PhysicalPermit:
    """An in-process local authorization that cannot be decoded from wire JSON."""

    authorization_id: str
    request_id: str
    origin_id: str
    context_sha256: str
    file_sha256: str
    file: str
    file_bytes: int
    printer: str
    physical_printer_identity: str
    nonce: str
    deadline_monotonic: float

    def __init__(
        self,
        authorization_id: str,
        request: BoundRequest,
        qualification: GcodeQualification,
        intent: StartIntent,
        deadline_monotonic: float,
        _token: object,
    ) -> None:
        if _token is not _PERMIT_TOKEN:
            raise TypeError("PhysicalPermit must be issued locally with PhysicalPermit.issue")
        object.__setattr__(self, "authorization_id", authorization_id)
        object.__setattr__(self, "request_id", request.request_id)
        object.__setattr__(self, "origin_id", request.origin_id)
        object.__setattr__(self, "context_sha256", request.context_sha256)
        object.__setattr__(self, "file_sha256", request.file_sha256)
        object.__setattr__(self, "file", request.file)
        object.__setattr__(self, "file_bytes", request.file_bytes)
        object.__setattr__(self, "printer", request.printer)
        object.__setattr__(
            self, "physical_printer_identity", qualification.physical_printer_identity
        )
        object.__setattr__(self, "nonce", intent.nonce)
        object.__setattr__(self, "deadline_monotonic", deadline_monotonic)

    @classmethod
    def issue(
        cls,
        request: BoundRequest,
        qualification: GcodeQualification,
        intent: StartIntent,
        *,
        authorization_id: str,
        deadline_monotonic: float,
    ) -> "PhysicalPermit":
        auth = _hex(authorization_id, _HEX32, "authorization_id")
        deadline = _finite_number(deadline_monotonic, "permit deadline_monotonic")
        qualification.assert_matches(request)
        intent.assert_matches(request)
        return cls(auth, request, qualification, intent, deadline, _PERMIT_TOKEN)

    def assert_matches(
        self,
        request: BoundRequest,
        qualification: GcodeQualification,
        intent: StartIntent,
        now_monotonic: float,
    ) -> None:
        expected = {
            "request_id": request.request_id,
            "origin_id": request.origin_id,
            "context_sha256": request.context_sha256,
            "file_sha256": request.file_sha256,
            "file": request.file,
            "file_bytes": request.file_bytes,
            "printer": request.printer,
            "physical_printer_identity": qualification.physical_printer_identity,
            "nonce": intent.nonce,
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise SafetyViolation(f"physical permit {name} does not match")
        if now_monotonic > self.deadline_monotonic:
            raise SafetyViolation("physical permit expired")


@dataclass(frozen=True)
class PrinterSnapshot:
    connected: bool
    ready: bool
    eventtime: float
    state: str
    filename: Optional[str] = None
    job_id: Optional[str] = None
    start_time: Optional[float] = None
    queue_job_ids: tuple[str, ...] = ()
    printer_identity: Optional[str] = None


@dataclass(frozen=True)
class HistoryRecord:
    job_id: str
    filename: str
    status: str
    start_time: float
    end_time: Optional[float] = None


class MoonrakerAdapter(Protocol):
    """Normalized adapter contract; concrete transports live outside this module."""

    def snapshot(self) -> PrinterSnapshot: ...

    def read_file_bytes(self, filename: str) -> bytes: ...

    def start_print(self, filename: str) -> None: ...

    def history(self, job_id: Optional[str] = None) -> Optional[HistoryRecord]: ...

    def cancel_print(self) -> None: ...


@dataclass(frozen=True)
class LifecycleStatus:
    phase: str
    reason: str
    request_id: Optional[str]
    job_id: Optional[str]
    result_available: bool
    can_cancel: bool
    completion_proof_sha256: Optional[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "reason": self.reason,
            "request_id": self.request_id,
            "job_id": self.job_id,
            "result_available": self.result_available,
            "can_cancel": self.can_cancel,
            "completion_proof_sha256": self.completion_proof_sha256,
        }


class AtomicJsonJournal:
    """A small atomic, fsync-backed journal with one active process owner."""

    def __init__(self, path: Path | str, maximum_bytes: int = 256 * 1024) -> None:
        self.path = Path(path)
        self.maximum_bytes = maximum_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise JournalError("journal path may not be a symlink")
        self._lock_file = open(str(self.path) + ".lock", "a+b")
        try:
            import fcntl

            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError, OSError) as exc:
            self._lock_file.close()
            raise JournalError("journal is already owned or cannot be locked") from exc

    def close(self) -> None:
        if not self._lock_file.closed:
            self._lock_file.close()

    def load(self) -> Optional[dict[str, Any]]:
        if not self.path.exists():
            return None
        if self.path.is_symlink() or not self.path.is_file():
            raise JournalError("journal must be a regular file")
        if self.path.stat().st_size > self.maximum_bytes:
            raise JournalError("journal exceeds its bounded size")
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise JournalError("journal is unreadable") from exc
        if not isinstance(value, dict) or value.get("schema") != JOURNAL_SCHEMA:
            raise JournalError("journal schema is invalid")
        return value

    def store(self, value: Mapping[str, Any]) -> None:
        if value.get("schema") != JOURNAL_SCHEMA:
            raise JournalError("refusing to write an invalid journal schema")
        encoded = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
        if len(encoded) > self.maximum_bytes:
            raise JournalError("journal exceeds its bounded size")
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


class TemperaturePrintLifecycle:
    """One-request coordinator with durable one-shot command semantics."""

    def __init__(
        self,
        journal_path: Path | str,
        adapter: MoonrakerAdapter,
        *,
        wall_time: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.adapter = adapter
        self.wall_time = wall_time
        self.monotonic = monotonic
        self.journal = AtomicJsonJournal(journal_path)
        loaded = self.journal.load()
        self._state = loaded or {
            "schema": JOURNAL_SCHEMA,
            "phase": "empty",
            "reason": "no request bound",
        }
        self._success_verified_this_process = False
        self._recovery_error: Optional[str] = None
        self._validate_loaded_state()

    def close(self) -> None:
        self.journal.close()

    def __enter__(self) -> "TemperaturePrintLifecycle":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _validate_loaded_state(self) -> None:
        if self._state.get("schema") != JOURNAL_SCHEMA:
            raise JournalError("journal schema is invalid")
        phase = self._state.get("phase")
        if not isinstance(phase, str):
            raise JournalError("journal phase is invalid")
        if phase != "empty":
            request = self._state.get("request")
            qualification = self._state.get("qualification")
            if not isinstance(request, dict) or not isinstance(qualification, dict):
                raise JournalError("journal binding is incomplete")
            self._request_from_state()
            self._qualification_from_state()

    def _request_from_state(self) -> BoundRequest:
        value = self._state["request"]
        return BoundRequest(
            request_id=value["request_id"],
            origin_id=value["origin_id"],
            context_sha256=value["context_sha256"],
            file_sha256=value["file_sha256"],
            file=value["file"],
            file_bytes=value["file_bytes"],
            printer=value["printer"],
            choices=tuple(value["choices"]),
            expires_at=value["expires_at"],
            ttl_seconds=value["ttl_seconds"],
        )

    def _qualification_from_state(self) -> GcodeQualification:
        value = self._state["qualification"]
        return GcodeQualification(
            request_id=value["request_id"],
            origin_id=value["origin_id"],
            context_sha256=value["context_sha256"],
            file_sha256=value["file_sha256"],
            file=value["file"],
            file_bytes=value["file_bytes"],
            printer=value["printer"],
            physical_printer_identity=value["physical_printer_identity"],
            choices=tuple(value["choices"]),
            estimated_duration_s=value["estimated_duration_s"],
        )

    def _persist(self) -> None:
        self.journal.store(self._state)

    def _set_phase(self, phase: str, reason: str, **updates: Any) -> None:
        self._state.update(updates)
        self._state["phase"] = phase
        self._state["reason"] = reason
        self._persist()

    def _fail(self, phase: str, reason: str) -> None:
        self._success_verified_this_process = False
        self._set_phase(phase, reason)

    def bind_request(
        self, request_value: Mapping[str, Any], qualification_value: Mapping[str, Any]
    ) -> LifecycleStatus:
        if self._state["phase"] != "empty":
            raise SafetyViolation("journal already owns a request")
        request = BoundRequest.from_mapping(request_value, self.wall_time())
        qualification = GcodeQualification.from_mapping(qualification_value)
        qualification.assert_matches(request)
        self._state = {
            "schema": JOURNAL_SCHEMA,
            "phase": "awaiting_start",
            "reason": "qualified request bound; physical start permit absent",
            "request": request.as_dict(),
            "qualification": qualification.as_dict(),
        }
        self._persist()
        return self.status()

    def bound_request(self) -> BoundRequest:
        if self._state["phase"] == "empty":
            raise SafetyViolation("no request is bound")
        return self._request_from_state()

    def parse_start_intent(self, value: Mapping[str, Any]) -> StartIntent:
        intent = StartIntent.from_mapping(value)
        intent.assert_matches(self.bound_request())
        return intent

    def issue_local_permit(
        self,
        intent: StartIntent,
        *,
        authorization_id: str,
        deadline_monotonic: float,
    ) -> PhysicalPermit:
        """Create a local capability; callers must enforce Founder authorization."""
        return PhysicalPermit.issue(
            self.bound_request(),
            self._qualification_from_state(),
            intent,
            authorization_id=authorization_id,
            deadline_monotonic=deadline_monotonic,
        )

    def _normalized_snapshot(self) -> PrinterSnapshot:
        try:
            sample = self.adapter.snapshot()
        except Exception as exc:
            raise SafetyViolation("Moonraker snapshot unavailable") from exc
        if not isinstance(sample, PrinterSnapshot):
            raise ValidationError("adapter snapshot must be PrinterSnapshot")
        _finite_number(sample.eventtime, "snapshot eventtime")
        if not isinstance(sample.connected, bool) or not isinstance(sample.ready, bool):
            raise ValidationError("snapshot connection flags are invalid")
        identity = _hex(
            sample.printer_identity, _HEX64, "snapshot printer_identity"
        )
        if (
            self._state["phase"] != "empty"
            and identity
            != self._qualification_from_state().physical_printer_identity
        ):
            raise SafetyViolation("physical printer identity does not match request")
        if not isinstance(sample.queue_job_ids, tuple) or any(
            not isinstance(item, str) or not item for item in sample.queue_job_ids
        ):
            raise ValidationError("snapshot queue_job_ids are invalid")
        if sample.state not in {
            "standby",
            "printing",
            "paused",
            "complete",
            "error",
            "cancelled",
        }:
            raise ValidationError("snapshot state is unexpected")
        return sample

    @staticmethod
    def _validate_history(record: Optional[HistoryRecord]) -> Optional[HistoryRecord]:
        if record is None:
            return None
        if not isinstance(record, HistoryRecord):
            raise ValidationError("adapter history must be HistoryRecord or None")
        _string(record.job_id, "history job_id", 256)
        _file_name(record.filename)
        _finite_number(record.start_time, "history start_time")
        if record.end_time is not None:
            _finite_number(record.end_time, "history end_time")
        if record.status not in {"printing", "completed", "failed", "cancelled"}:
            raise ValidationError("history status is unexpected")
        return record

    def _history(self, job_id: Optional[str]) -> Optional[HistoryRecord]:
        try:
            return self._validate_history(self.adapter.history(job_id))
        except LifecycleError:
            raise
        except Exception as exc:
            raise SafetyViolation("Moonraker history unavailable") from exc

    def _fresh_after_last(self, sample: PrinterSnapshot) -> None:
        previous = self._state.get("last_eventtime")
        if previous is not None and sample.eventtime <= previous:
            raise SafetyViolation("Moonraker eventtime is stale or rolled back")

    def _terminal_start_rejection(self, reason: str) -> None:
        self._fail("start_rejected", reason)
        raise SafetyViolation(reason)

    @staticmethod
    def _assert_start_ready(sample: PrinterSnapshot, intent: StartIntent) -> None:
        if not sample.connected or not sample.ready:
            raise SafetyViolation("printer is disconnected or not ready")
        if sample.eventtime < intent.eventtime:
            raise SafetyViolation("Moonraker eventtime rolled back before start")
        if sample.eventtime >= intent.expires_eventtime:
            raise SafetyViolation("native Start intent is stale")
        if sample.state != "standby":
            raise SafetyViolation("printer is not in the ready idle state")
        if (
            sample.filename is not None
            or sample.job_id is not None
            or sample.start_time is not None
        ):
            raise SafetyViolation("printer reports an unexpected current job")
        if sample.queue_job_ids:
            raise SafetyViolation("printer queue is not empty")

    def start(
        self,
        intent_value: Mapping[str, Any] | StartIntent,
        *,
        permit: Optional[PhysicalPermit] = None,
    ) -> LifecycleStatus:
        if self._state["phase"] != "awaiting_start":
            raise SafetyViolation("start is one-shot and this request is no longer startable")
        request = self.bound_request()
        qualification = self._qualification_from_state()
        intent = (
            intent_value
            if isinstance(intent_value, StartIntent)
            else self.parse_start_intent(intent_value)
        )
        intent.assert_matches(request)
        now_mono = _finite_number(self.monotonic(), "local monotonic time")
        if not isinstance(permit, PhysicalPermit):
            raise SafetyViolation("a separate local physical permit is required")
        permit.assert_matches(request, qualification, intent, now_mono)
        created_at = request.expires_at - request.ttl_seconds
        if self.wall_time() >= min(request.expires_at, created_at + MAX_START_LIFETIME_S):
            self._terminal_start_rejection("request expired before start")

        try:
            sample = self._normalized_snapshot()
            self._assert_start_ready(sample, intent)
            baseline = self._history(None)
            file_data = self.adapter.read_file_bytes(request.file)
            if not isinstance(file_data, bytes):
                raise ValidationError("adapter file readback must return bytes")
            if len(file_data) != request.file_bytes:
                raise SafetyViolation("printer file byte count does not match")
            if hashlib.sha256(file_data).hexdigest() != request.file_sha256:
                raise SafetyViolation("printer file hash does not match")
            final_sample = self._normalized_snapshot()
            if final_sample.eventtime <= sample.eventtime:
                raise SafetyViolation("final pre-dispatch status sample is not fresh")
            self._assert_start_ready(final_sample, intent)
            dispatch_monotonic = _finite_number(
                self.monotonic(), "final local monotonic time"
            )
            permit.assert_matches(
                request, qualification, intent, dispatch_monotonic
            )
            if self.wall_time() >= request.expires_at:
                raise SafetyViolation("request expired during start preflight")
        except Exception as exc:
            reason = str(exc) if isinstance(exc, LifecycleError) else "Moonraker preflight unavailable"
            self._terminal_start_rejection(reason)

        self._state.update(
            {
                "intent": intent.as_dict(),
                "authorization_id": permit.authorization_id,
                "physical_permit_deadline_monotonic": permit.deadline_monotonic,
                "physical_printer_identity": permit.physical_printer_identity,
                "last_eventtime": final_sample.eventtime,
                "baseline_history_job_id": baseline.job_id if baseline else None,
                "baseline_history_start_time": baseline.start_time if baseline else None,
                "start_dispatch_monotonic": dispatch_monotonic,
                "start_confirmation_deadline": (
                    dispatch_monotonic + START_CONFIRMATION_TIMEOUT_S
                ),
            }
        )
        self._set_phase(
            "start_dispatch_intent",
            "durable one-shot start intent recorded before dispatch",
        )
        try:
            self.adapter.start_print(request.file)
        except Exception as exc:
            self._fail("start_uncertain", "start dispatch outcome is ambiguous; retry prohibited")
            raise SafetyViolation("start dispatch outcome is ambiguous; retry prohibited") from exc
        self._set_phase(
            "start_dispatched",
            "start command returned; actual printer start is not yet confirmed",
        )
        return self.status()

    def _same_owned_job(self, sample: PrinterSnapshot) -> bool:
        return (
            sample.filename == self._state.get("owned_filename")
            and sample.job_id == self._state.get("owned_job_id")
            and sample.start_time == self._state.get("owned_start_time")
        )

    def _observe_start(self, sample: PrinterSnapshot, now_mono: float) -> None:
        request = self.bound_request()
        if sample.state in {"paused", "error", "cancelled", "complete"}:
            self._fail("failed", f"unexpected {sample.state} before owned running job confirmation")
            return
        if sample.state == "standby":
            if now_mono > self._state["start_confirmation_deadline"]:
                self._fail("start_uncertain", "actual start was not confirmed before timeout")
            else:
                self._state["last_eventtime"] = sample.eventtime
                self._persist()
            return
        if sample.state != "printing":
            self._fail("failed", "unexpected printer state while confirming start")
            return
        if (
            sample.filename != request.file
            or not sample.job_id
            or sample.start_time is None
        ):
            self._fail("failed", "printing job does not match the requested file and identity")
            return
        try:
            history = self._history(sample.job_id)
        except LifecycleError as exc:
            self._fail("failed", str(exc))
            return
        if (
            history is None
            or history.status != "printing"
            or history.filename != request.file
            or history.job_id != sample.job_id
            or history.start_time != sample.start_time
        ):
            self._fail("failed", "running job lacks matching independent history proof")
            return
        baseline_id = self._state.get("baseline_history_job_id")
        baseline_start = self._state.get("baseline_history_start_time")
        if history.job_id == baseline_id or (
            baseline_start is not None and history.start_time <= baseline_start
        ):
            self._fail("failed", "observed print is not a new job after dispatch")
            return
        self._set_phase(
            "printing",
            "owned running job independently confirmed",
            last_eventtime=sample.eventtime,
            owned_filename=history.filename,
            owned_job_id=history.job_id,
            owned_start_time=history.start_time,
            run_deadline_monotonic=(
                now_mono
                + self._qualification_from_state().estimated_duration_s
                + RUN_OVERRUN_GRACE_S
            ),
        )

    def _completion_proof(
        self, sample: PrinterSnapshot, history: HistoryRecord
    ) -> tuple[dict[str, Any], str]:
        request = self.bound_request()
        proof = {
            "schema": COMPLETION_PROOF_SCHEMA,
            "request_id": request.request_id,
            "origin_id": request.origin_id,
            "context_sha256": request.context_sha256,
            "file_sha256": request.file_sha256,
            "file": request.file,
            "file_bytes": request.file_bytes,
            "printer": request.printer,
            "choices": list(request.choices),
            "job_id": history.job_id,
            "start_time": history.start_time,
            "end_time": history.end_time,
            "print_stats_state": sample.state,
            "print_stats_eventtime": sample.eventtime,
            "history_status": history.status,
        }
        return proof, _canonical_digest(proof)

    def _matching_completion_history(
        self, sample: PrinterSnapshot
    ) -> Optional[HistoryRecord]:
        if sample.state != "complete" or not self._same_owned_job(sample):
            return None
        try:
            history = self._history(self._state["owned_job_id"])
        except LifecycleError:
            return None
        if (
            history is not None
            and history.status == "completed"
            and history.job_id == self._state["owned_job_id"]
            and history.filename == self._state["owned_filename"]
            and history.start_time == self._state["owned_start_time"]
            and history.end_time is not None
            and history.end_time > history.start_time
        ):
            return history
        return None

    def _observe_running(self, sample: PrinterSnapshot, now_mono: float) -> None:
        if now_mono > self._state["run_deadline_monotonic"]:
            self._fail("failed", "print exceeded the bounded monitoring timeout")
            return
        if sample.state == "printing":
            if not self._same_owned_job(sample):
                self._fail("failed", "a replacement or mismatched job was observed")
                return
            try:
                history = self._history(self._state["owned_job_id"])
            except LifecycleError as exc:
                self._fail("failed", str(exc))
                return
            if (
                history is None
                or history.status != "printing"
                or history.filename != self._state["owned_filename"]
                or history.start_time != self._state["owned_start_time"]
            ):
                self._fail("failed", "running job history correlation failed")
                return
            self._state["last_eventtime"] = sample.eventtime
            self._persist()
            return
        if sample.state == "complete":
            if not self._same_owned_job(sample):
                self._fail("failed", "completion belongs to a different job")
                return
            history = self._matching_completion_history(sample)
            if history is None:
                self._set_phase(
                    "completion_pending",
                    "print_stats completed; awaiting independent matching history",
                    last_eventtime=sample.eventtime,
                    completion_confirmation_deadline=(
                        now_mono + COMPLETION_CONFIRMATION_TIMEOUT_S
                    ),
                )
                return
            proof, digest = self._completion_proof(sample, history)
            self._set_phase(
                "completed",
                "same-job print_stats and independent history prove successful completion",
                last_eventtime=sample.eventtime,
                completion_proof=proof,
                completion_proof_sha256=digest,
            )
            self._success_verified_this_process = True
            return
        self._fail("failed", f"unexpected {sample.state} while owned print was running")

    def _observe_completion_pending(self, sample: PrinterSnapshot, now_mono: float) -> None:
        if sample.state != "complete" or not self._same_owned_job(sample):
            self._fail("failed", "completion proof changed before independent confirmation")
            return
        history = self._matching_completion_history(sample)
        if history is not None:
            proof, digest = self._completion_proof(sample, history)
            self._set_phase(
                "completed",
                "same-job print_stats and independent history prove successful completion",
                last_eventtime=sample.eventtime,
                completion_proof=proof,
                completion_proof_sha256=digest,
            )
            self._success_verified_this_process = True
        elif now_mono > self._state["completion_confirmation_deadline"]:
            self._fail("failed", "independent completion proof timed out")
        else:
            self._state["last_eventtime"] = sample.eventtime
            self._persist()

    def _observe_cancel(self, sample: PrinterSnapshot, now_mono: float) -> None:
        if not self._same_owned_job(sample):
            self._fail("cancel_uncertain", "printer switched away from the owned cancellation target")
            return
        if sample.state == "cancelled":
            try:
                history = self._history(self._state["owned_job_id"])
            except LifecycleError as exc:
                self._fail("cancel_uncertain", str(exc))
                return
            if (
                history is not None
                and history.status == "cancelled"
                and history.filename == self._state["owned_filename"]
                and history.start_time == self._state["owned_start_time"]
                and history.end_time is not None
                and history.end_time > history.start_time
            ):
                self._set_phase(
                    "cancelled",
                    "same owned job cancellation independently confirmed",
                    last_eventtime=sample.eventtime,
                )
                return
        elif sample.state in {"complete", "error", "standby", "paused"}:
            self._fail("cancel_uncertain", f"unexpected {sample.state} after cancel request")
            return
        if now_mono > self._state["cancel_confirmation_deadline"]:
            self._fail("cancel_uncertain", "actual cancellation was not confirmed before timeout")
        else:
            self._state["last_eventtime"] = sample.eventtime
            self._persist()

    def _recover_completed(self, sample: PrinterSnapshot) -> None:
        history = self._matching_completion_history(sample)
        if history is None:
            self._recovery_error = "fresh independent completion proof is unavailable"
            self._fail("completion_revoked", self._recovery_error)
            return
        persisted = self._state.get("completion_proof")
        if (
            not isinstance(persisted, dict)
            or _canonical_digest(persisted)
            != self._state.get("completion_proof_sha256")
            or persisted.get("job_id") != history.job_id
            or persisted.get("file") != history.filename
            or persisted.get("start_time") != history.start_time
            or persisted.get("end_time") != history.end_time
            or persisted.get("history_status") != "completed"
            or persisted.get("print_stats_state") != "complete"
        ):
            self._recovery_error = "fresh completion identity differs from persisted proof"
            self._fail("completion_revoked", self._recovery_error)
            return
        self._state["last_eventtime"] = sample.eventtime
        self._persist()
        self._success_verified_this_process = True

    def poll(self) -> LifecycleStatus:
        phase = self._state["phase"]
        if phase not in {
            "start_dispatch_intent",
            "start_dispatched",
            "printing",
            "completion_pending",
            "cancel_dispatch_intent",
            "cancel_dispatched",
            "completed",
        }:
            return self.status()
        now_mono = _finite_number(self.monotonic(), "local monotonic time")
        try:
            sample = self._normalized_snapshot()
            if not sample.connected or not sample.ready:
                raise SafetyViolation("printer disconnected or became unready")
            self._fresh_after_last(sample)
        except LifecycleError as exc:
            failure = "completion_revoked" if phase == "completed" else "failed"
            self._fail(failure, str(exc))
            return self.status()

        if phase in {"start_dispatch_intent", "start_dispatched"}:
            self._observe_start(sample, now_mono)
        elif phase == "printing":
            self._observe_running(sample, now_mono)
        elif phase == "completion_pending":
            self._observe_completion_pending(sample, now_mono)
        elif phase in {"cancel_dispatch_intent", "cancel_dispatched"}:
            self._observe_cancel(sample, now_mono)
        elif phase == "completed":
            self._recover_completed(sample)
        return self.status()

    def cancel(self) -> LifecycleStatus:
        if self._state["phase"] != "printing":
            raise SafetyViolation("cancel is allowed only for the confirmed owned running job")
        now_mono = _finite_number(self.monotonic(), "local monotonic time")
        try:
            sample = self._normalized_snapshot()
            if not sample.connected or not sample.ready:
                raise SafetyViolation("printer disconnected or became unready")
            self._fresh_after_last(sample)
            if sample.state != "printing" or not self._same_owned_job(sample):
                raise SafetyViolation("cancel target is not the same owned running job")
            history = self._history(self._state["owned_job_id"])
            if (
                history is None
                or history.status != "printing"
                or history.filename != self._state["owned_filename"]
                or history.start_time != self._state["owned_start_time"]
            ):
                raise SafetyViolation("cancel target lacks matching independent history")
            final_sample = self._normalized_snapshot()
            if final_sample.eventtime <= sample.eventtime:
                raise SafetyViolation("final pre-cancel status sample is not fresh")
            if final_sample.state != "printing" or not self._same_owned_job(final_sample):
                raise SafetyViolation("cancel target changed before command dispatch")
        except LifecycleError as exc:
            self._fail("cancel_rejected", str(exc))
            raise
        self._set_phase(
            "cancel_dispatch_intent",
            "durable one-shot cancel intent recorded before dispatch",
            last_eventtime=final_sample.eventtime,
            cancel_dispatch_monotonic=now_mono,
            cancel_confirmation_deadline=now_mono + CANCEL_CONFIRMATION_TIMEOUT_S,
        )
        try:
            self.adapter.cancel_print()
        except Exception as exc:
            self._fail("cancel_uncertain", "cancel dispatch outcome is ambiguous; retry prohibited")
            raise SafetyViolation("cancel dispatch outcome is ambiguous; retry prohibited") from exc
        self._set_phase(
            "cancel_dispatched",
            "cancel command returned; actual cancellation is not yet confirmed",
        )
        return self.status()

    def status(self) -> LifecycleStatus:
        phase = self._state["phase"]
        return LifecycleStatus(
            phase=phase,
            reason=self._recovery_error or self._state.get("reason", ""),
            request_id=(self._state.get("request") or {}).get("request_id"),
            job_id=self._state.get("owned_job_id"),
            result_available=(phase == "completed" and self._success_verified_this_process),
            can_cancel=(phase == "printing"),
            completion_proof_sha256=self._state.get("completion_proof_sha256"),
        )
