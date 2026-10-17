import copy
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "temperature_print_lifecycle",
    ROOT / "integration" / "temperature-print" / "lifecycle.py",
)
lifecycle = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lifecycle
SPEC.loader.exec_module(lifecycle)


FILE_DATA = b"; miniature temperature tower\nM104 S210\nM104 S205\nM104 S200\n"
FILE_SHA = hashlib.sha256(FILE_DATA).hexdigest()
REQUEST_ID = "1" * 32
ORIGIN_ID = "2" * 32
CONTEXT_SHA = "3" * 64
PRINTER = "Voron 2.4 300"
MOONRAKER_VERSION = "v0.10.0-31-gd5ee171"
PRINTER_CONFIG_SHA256 = "e" * 64
PHYSICAL_PRINTER_IDENTITY = "4" * 64
FILE = "mini-temperature-210-200.gcode"


class Clock:
    def __init__(self):
        self.wall = 1_000.0
        self.mono = 50.0

    def wall_time(self):
        return self.wall

    def monotonic(self):
        return self.mono


class FakeAdapter:
    def __init__(self):
        self.current = lifecycle.PrinterSnapshot(
            connected=True,
            ready=True,
            eventtime=101.0,
            state="standby",
        )
        self.file_data = FILE_DATA
        self.latest = lifecycle.HistoryRecord(
            job_id="prior-job",
            filename="prior.gcode",
            status="completed",
            start_time=1.0,
            end_time=2.0,
        )
        self.records = {self.latest.job_id: self.latest}
        self.start_calls = []
        self.cancel_calls = 0
        self.snapshot_calls = 0
        self.last_snapshot_eventtime = None
        self.snapshot_sequence = []
        self.read_calls = []
        self.history_calls = []
        self.start_error = None
        self.cancel_error = None
        self.snapshot_error = None

    def snapshot(self):
        self.snapshot_calls += 1
        if self.snapshot_error:
            raise self.snapshot_error
        sample = self.snapshot_sequence.pop(0) if self.snapshot_sequence else self.current
        if sample.moonraker_version is None:
            sample = replace(sample, moonraker_version=MOONRAKER_VERSION)
        if sample.configuration_sha256 is None:
            sample = replace(sample, configuration_sha256=PRINTER_CONFIG_SHA256)
        if sample.printer_identity is None:
            sample = replace(sample, printer_identity=PHYSICAL_PRINTER_IDENTITY)
        if (
            self.last_snapshot_eventtime is not None
            and sample.eventtime == self.last_snapshot_eventtime
        ):
            sample = replace(sample, eventtime=sample.eventtime + 0.1)
        self.last_snapshot_eventtime = sample.eventtime
        return sample

    def read_file_bytes(self, filename):
        self.read_calls.append(filename)
        return self.file_data

    def start_print(self, filename):
        self.start_calls.append(filename)
        if self.start_error:
            raise self.start_error

    def history(self, job_id=None):
        self.history_calls.append(job_id)
        return self.latest if job_id is None else self.records.get(job_id)

    def cancel_print(self):
        self.cancel_calls += 1
        if self.cancel_error:
            raise self.cancel_error

    def show_printing(self, *, eventtime=102.0, job_id="owned-job", filename=FILE):
        record = lifecycle.HistoryRecord(
            job_id=job_id,
            filename=filename,
            status="printing",
            start_time=10.0,
        )
        self.records[job_id] = record
        self.latest = record
        self.current = lifecycle.PrinterSnapshot(
            connected=True,
            ready=True,
            eventtime=eventtime,
            state="printing",
            filename=filename,
            job_id=job_id,
            start_time=10.0,
        )

    def show_complete(self, *, eventtime=103.0, history_status="completed"):
        job_id = self.current.job_id or "owned-job"
        filename = self.current.filename or FILE
        record = lifecycle.HistoryRecord(
            job_id=job_id,
            filename=filename,
            status=history_status,
            start_time=10.0,
            end_time=20.0 if history_status != "printing" else None,
        )
        self.records[job_id] = record
        self.latest = record
        self.current = lifecycle.PrinterSnapshot(
            connected=True,
            ready=True,
            eventtime=eventtime,
            state="complete",
            filename=filename,
            job_id=job_id,
            start_time=10.0,
        )

    def show_cancelled(self, *, eventtime=104.0):
        job_id = self.current.job_id
        filename = self.current.filename
        record = lifecycle.HistoryRecord(
            job_id=job_id,
            filename=filename,
            status="cancelled",
            start_time=10.0,
            end_time=15.0,
        )
        self.records[job_id] = record
        self.latest = record
        self.current = lifecycle.PrinterSnapshot(
            connected=True,
            ready=True,
            eventtime=eventtime,
            state="cancelled",
            filename=filename,
            job_id=job_id,
            start_time=10.0,
        )


def request(**updates):
    value = {
        "schema": lifecycle.REQUEST_SCHEMA,
        "physical_calibration": True,
        "not_applied": True,
        "request_id": REQUEST_ID,
        "origin_id": ORIGIN_ID,
        "context_sha256": CONTEXT_SHA,
        "file_sha256": FILE_SHA,
        "file": FILE,
        "file_bytes": len(FILE_DATA),
        "printer": PRINTER,
        "choices": [210, 205, 200],
        "expires_at": 4_600,
        "ttl_seconds": 3_600,
    }
    value.update(updates)
    return value


def qualification(**updates):
    value = {
        "schema": lifecycle.QUALIFICATION_SCHEMA,
        "request_id": REQUEST_ID,
        "origin_id": ORIGIN_ID,
        "context_sha256": CONTEXT_SHA,
        "file_sha256": FILE_SHA,
        "file": FILE,
        "file_bytes": len(FILE_DATA),
        "printer": PRINTER,
        "physical_printer_identity": PHYSICAL_PRINTER_IDENTITY,
        "printer_config_sha256": PRINTER_CONFIG_SHA256,
        "moonraker_version": MOONRAKER_VERSION,
        "choices": [210, 205, 200],
        "band_count": 3,
        "estimated_duration_s": 900,
        "suitable": True,
        "geometry_verified": True,
        "temperature_commands_verified": True,
        "temperature_order_verified": True,
        "file_identity_verified": True,
    }
    value.update(updates)
    return value


def start_intent(**updates):
    value = {
        "schema": lifecycle.START_SCHEMA,
        "request_id": REQUEST_ID,
        "origin_id": ORIGIN_ID,
        "context_sha256": CONTEXT_SHA,
        "file_sha256": FILE_SHA,
        "file": FILE,
        "file_bytes": len(FILE_DATA),
        "printer": PRINTER,
        "choices": [210, 205, 200],
        "nonce": REQUEST_ID + ":100000000",
        "eventtime": 100.0,
        "expires_eventtime": 1_000.0,
    }
    value.update(updates)
    return value


class TemperaturePrintLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "journal.json"
        self.clock = Clock()
        self.adapter = FakeAdapter()
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )

    def tearDown(self):
        self.coordinator.close()
        self.temporary.cleanup()

    def bind(self, request_value=None, qualification_value=None):
        return self.coordinator.bind_request(
            request_value or request(), qualification_value or qualification()
        )

    def permit_and_intent(self):
        parsed = self.coordinator.parse_start_intent(start_intent())
        permit = self.coordinator.issue_local_permit(
            parsed,
            authorization_id="a" * 32,
            deadline_monotonic=60.0,
        )
        return parsed, permit

    def dispatch(self):
        self.bind()
        parsed, permit = self.permit_and_intent()
        return self.coordinator.start(parsed, permit=permit)

    def confirm_printing(self):
        self.adapter.show_printing()
        self.clock.mono = 51.0
        return self.coordinator.poll()

    def test_request_receipt_is_persist_only_and_does_not_touch_adapter(self):
        original = request()
        retained = copy.deepcopy(original)
        status = self.bind(original)
        self.assertEqual(status.phase, "awaiting_start")
        self.assertEqual(original, retained)
        self.assertEqual(self.adapter.snapshot_calls, 0)
        self.assertEqual(self.adapter.start_calls, [])
        self.assertFalse(status.result_available)

    def test_qualification_rejects_duration_over_twenty_minutes(self):
        with self.assertRaises(lifecycle.ValidationError):
            self.bind(qualification_value=qualification(estimated_duration_s=1_200.01))
        self.assertEqual(self.adapter.start_calls, [])
        self.assertFalse(self.path.exists())

    def test_requires_exact_three_descending_choices_and_verified_suitability(self):
        with self.assertRaises(lifecycle.ValidationError):
            self.bind(request_value=request(choices=[200, 205, 210]))
        with self.assertRaises(lifecycle.ValidationError):
            self.bind(qualification_value=qualification(suitable=False))
        self.assertEqual(self.adapter.start_calls, [])

    def test_wire_authorization_cannot_create_a_physical_permit(self):
        with self.assertRaises(lifecycle.ValidationError):
            self.bind(request_value=request(physical_authorized=True))
        self.bind()
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(start_intent(), permit=True)
        self.assertEqual(self.coordinator.status().phase, "awaiting_start")
        self.assertEqual(self.adapter.start_calls, [])

    def test_start_requires_exact_fresh_native_intent_and_local_permit(self):
        self.bind()
        parsed, permit = self.permit_and_intent()
        mismatched = start_intent(file_sha256="f" * 64)
        with self.assertRaises(lifecycle.ValidationError):
            self.coordinator.start(mismatched, permit=permit)
        self.assertEqual(self.adapter.start_calls, [])
        self.adapter.current = lifecycle.PrinterSnapshot(
            connected=True, ready=True, eventtime=1_000.0, state="standby"
        )
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(parsed, permit=permit)
        self.assertEqual(self.coordinator.status().phase, "start_rejected")
        self.assertEqual(self.adapter.start_calls, [])

    def test_stale_absolute_request_cannot_start(self):
        self.bind()
        parsed, permit = self.permit_and_intent()
        self.clock.wall = 4_600
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(parsed, permit=permit)
        self.assertEqual(self.coordinator.status().phase, "start_rejected")
        self.assertEqual(self.adapter.start_calls, [])

    def test_idle_queue_file_and_hash_are_revalidated_before_dispatch(self):
        cases = (
            lifecycle.PrinterSnapshot(True, True, 101.0, "printing", FILE, "other", 9.0),
            lifecycle.PrinterSnapshot(True, True, 101.0, "standby", queue_job_ids=("queued",)),
            lifecycle.PrinterSnapshot(False, False, 101.0, "standby"),
        )
        for sample in cases:
            with self.subTest(sample=sample):
                self.coordinator.close()
                self.path.unlink(missing_ok=True)
                self.coordinator = lifecycle.TemperaturePrintLifecycle(
                    self.path,
                    self.adapter,
                    wall_time=self.clock.wall_time,
                    monotonic=self.clock.monotonic,
                )
                self.adapter.current = sample
                self.bind()
                parsed, permit = self.permit_and_intent()
                before = len(self.adapter.start_calls)
                with self.assertRaises(lifecycle.SafetyViolation):
                    self.coordinator.start(parsed, permit=permit)
                self.assertEqual(len(self.adapter.start_calls), before)
        self.coordinator.close()
        self.path.unlink(missing_ok=True)
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )
        self.adapter.current = lifecycle.PrinterSnapshot(True, True, 101.0, "standby")
        self.adapter.file_data = FILE_DATA + b"tampered"
        self.bind()
        parsed, permit = self.permit_and_intent()
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(parsed, permit=permit)
        self.assertEqual(self.adapter.start_calls, [])

    def test_final_pre_dispatch_sample_rechecks_identity_idle_and_freshness(self):
        self.bind()
        parsed, permit = self.permit_and_intent()
        self.adapter.snapshot_sequence = [
            lifecycle.PrinterSnapshot(
                True,
                True,
                101.0,
                "standby",
                printer_identity=PHYSICAL_PRINTER_IDENTITY,
            ),
            lifecycle.PrinterSnapshot(
                True,
                True,
                102.0,
                "printing",
                FILE,
                "unexpected-job",
                9.0,
                printer_identity=PHYSICAL_PRINTER_IDENTITY,
            ),
        ]
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(parsed, permit=permit)
        self.assertEqual(self.coordinator.status().phase, "start_rejected")
        self.assertEqual(self.adapter.start_calls, [])

    def test_physical_identity_is_local_qualification_not_saved_preset_label(self):
        self.bind()
        parsed, permit = self.permit_and_intent()
        self.adapter.current = lifecycle.PrinterSnapshot(
            True,
            True,
            101.0,
            "standby",
            printer_identity="5" * 64,
        )
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(parsed, permit=permit)
        self.assertEqual(self.adapter.start_calls, [])

    def test_dispatch_is_one_shot_and_actual_start_requires_observation(self):
        status = self.dispatch()
        self.assertEqual(status.phase, "start_dispatched")
        self.assertFalse(status.result_available)
        self.assertEqual(self.adapter.start_calls, [FILE])
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(start_intent(), permit=None)
        self.assertEqual(self.adapter.start_calls, [FILE])
        status = self.confirm_printing()
        self.assertEqual(status.phase, "printing")
        self.assertTrue(status.can_cancel)

    def test_ambiguous_start_failure_is_never_retried_even_after_restart(self):
        self.adapter.start_error = TimeoutError("lost response")
        self.bind()
        parsed, permit = self.permit_and_intent()
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.start(parsed, permit=permit)
        self.assertEqual(self.coordinator.status().phase, "start_uncertain")
        self.assertEqual(self.adapter.start_calls, [FILE])
        self.coordinator.close()
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )
        self.assertEqual(self.coordinator.poll().phase, "start_uncertain")
        self.assertEqual(self.adapter.start_calls, [FILE])

    def test_crash_window_start_intent_recovers_by_observation_without_redispatch(self):
        self.dispatch()
        state = self.coordinator._state
        state["phase"] = "start_dispatch_intent"
        state["reason"] = "simulated crash after durable intent"
        self.coordinator._persist()
        self.coordinator.close()
        self.adapter.show_printing()
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )
        self.clock.mono = 51.0
        status = self.coordinator.poll()
        self.assertEqual(status.phase, "printing")
        self.assertEqual(self.adapter.start_calls, [FILE])

    def test_start_confirmation_timeout_fails_closed(self):
        self.dispatch()
        self.clock.mono = 81.0
        self.adapter.current = lifecycle.PrinterSnapshot(True, True, 102.0, "standby")
        status = self.coordinator.poll()
        self.assertEqual(status.phase, "start_uncertain")
        self.assertFalse(status.result_available)

    def test_prior_or_wrong_job_and_false_completion_are_rejected(self):
        self.dispatch()
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 102.0, "complete", "prior.gcode", "prior-job", 1.0
        )
        status = self.coordinator.poll()
        self.assertEqual(status.phase, "failed")
        self.assertFalse(status.result_available)

    def test_running_job_replacement_pause_error_cancel_and_disconnect_fail_closed(self):
        variants = (
            lifecycle.PrinterSnapshot(True, True, 103.0, "printing", "other.gcode", "other", 11.0),
            lifecycle.PrinterSnapshot(True, True, 103.0, "paused", FILE, "owned-job", 10.0),
            lifecycle.PrinterSnapshot(True, True, 103.0, "error", FILE, "owned-job", 10.0),
            lifecycle.PrinterSnapshot(True, True, 103.0, "cancelled", FILE, "owned-job", 10.0),
            lifecycle.PrinterSnapshot(False, False, 103.0, "printing", FILE, "owned-job", 10.0),
        )
        for sample in variants:
            with self.subTest(state=sample.state, connected=sample.connected):
                self.coordinator.close()
                self.path.unlink(missing_ok=True)
                self.adapter = FakeAdapter()
                self.coordinator = lifecycle.TemperaturePrintLifecycle(
                    self.path,
                    self.adapter,
                    wall_time=self.clock.wall_time,
                    monotonic=self.clock.monotonic,
                )
                self.dispatch()
                self.confirm_printing()
                self.adapter.current = sample
                self.clock.mono = 52.0
                status = self.coordinator.poll()
                self.assertEqual(status.phase, "failed")
                self.assertFalse(status.result_available)

    def test_clock_rollback_or_repeated_sample_fails_closed(self):
        self.dispatch()
        self.adapter.current = lifecycle.PrinterSnapshot(True, True, 101.0, "standby")
        status = self.coordinator.poll()
        self.assertEqual(status.phase, "failed")
        self.assertIn("stale or rolled back", status.reason)

    def test_completion_requires_same_running_job_and_two_independent_sources(self):
        self.dispatch()
        self.confirm_printing()
        self.adapter.show_complete(history_status="printing")
        self.clock.mono = 52.0
        pending = self.coordinator.poll()
        self.assertEqual(pending.phase, "completion_pending")
        self.assertFalse(pending.result_available)
        self.adapter.show_complete(eventtime=104.0, history_status="completed")
        self.clock.mono = 53.0
        complete = self.coordinator.poll()
        self.assertEqual(complete.phase, "completed")
        self.assertTrue(complete.result_available)
        self.assertRegex(complete.completion_proof_sha256, r"^[0-9a-f]{64}$")

    def test_failed_history_can_never_unlock_result(self):
        self.dispatch()
        self.confirm_printing()
        self.adapter.show_complete(history_status="failed")
        self.clock.mono = 52.0
        pending = self.coordinator.poll()
        self.assertEqual(pending.phase, "completion_pending")
        self.clock.mono = 83.0
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 104.0, "complete", FILE, "owned-job", 10.0
        )
        failed = self.coordinator.poll()
        self.assertEqual(failed.phase, "failed")
        self.assertFalse(failed.result_available)

    def test_restart_does_not_unlock_persisted_success_without_fresh_proof(self):
        self.dispatch()
        self.confirm_printing()
        self.adapter.show_complete()
        self.clock.mono = 52.0
        self.assertTrue(self.coordinator.poll().result_available)
        self.coordinator.close()
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )
        self.assertFalse(self.coordinator.status().result_available)
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 104.0, "complete", FILE, "owned-job", 10.0
        )
        self.assertTrue(self.coordinator.poll().result_available)
        self.assertEqual(self.adapter.start_calls, [FILE])

    def test_cancel_is_guarded_journaled_and_requires_actual_confirmation(self):
        self.dispatch()
        self.confirm_printing()
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 103.0, "printing", FILE, "owned-job", 10.0
        )
        self.clock.mono = 52.0
        status = self.coordinator.cancel()
        self.assertEqual(status.phase, "cancel_dispatched")
        self.assertEqual(self.adapter.cancel_calls, 1)
        self.assertFalse(status.result_available)
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.cancel()
        self.assertEqual(self.adapter.cancel_calls, 1)
        self.adapter.show_cancelled()
        self.clock.mono = 53.0
        status = self.coordinator.poll()
        self.assertEqual(status.phase, "cancelled")
        self.assertFalse(status.result_available)

    def test_cancel_rejects_wrong_job_and_ambiguous_dispatch_never_retries(self):
        self.dispatch()
        self.confirm_printing()
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 103.0, "printing", "other.gcode", "other", 11.0
        )
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.cancel()
        self.assertEqual(self.adapter.cancel_calls, 0)
        self.assertEqual(self.coordinator.status().phase, "cancel_rejected")

        self.coordinator.close()
        self.path.unlink(missing_ok=True)
        self.adapter = FakeAdapter()
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )
        self.dispatch()
        self.confirm_printing()
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 103.0, "printing", FILE, "owned-job", 10.0
        )
        self.adapter.cancel_error = TimeoutError("lost response")
        with self.assertRaises(lifecycle.SafetyViolation):
            self.coordinator.cancel()
        self.assertEqual(self.adapter.cancel_calls, 1)
        self.assertEqual(self.coordinator.status().phase, "cancel_uncertain")
        self.assertFalse(self.coordinator.status().result_available)
        self.coordinator.close()
        self.coordinator = lifecycle.TemperaturePrintLifecycle(
            self.path,
            self.adapter,
            wall_time=self.clock.wall_time,
            monotonic=self.clock.monotonic,
        )
        self.assertEqual(self.coordinator.poll().phase, "cancel_uncertain")
        self.assertEqual(self.adapter.cancel_calls, 1)

    def test_completed_after_cancel_request_is_never_a_result(self):
        self.dispatch()
        self.confirm_printing()
        self.adapter.current = lifecycle.PrinterSnapshot(
            True, True, 103.0, "printing", FILE, "owned-job", 10.0
        )
        self.coordinator.cancel()
        self.adapter.show_complete(eventtime=104.0)
        self.clock.mono = 53.0
        status = self.coordinator.poll()
        self.assertEqual(status.phase, "cancel_uncertain")
        self.assertFalse(status.result_available)

    def test_atomic_journal_rejects_concurrent_owner(self):
        self.bind()
        with self.assertRaises(lifecycle.JournalError):
            lifecycle.TemperaturePrintLifecycle(
                self.path,
                self.adapter,
                wall_time=self.clock.wall_time,
                monotonic=self.clock.monotonic,
            )


if __name__ == "__main__":
    unittest.main()
