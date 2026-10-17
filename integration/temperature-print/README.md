# Bounded Temperature print lifecycle

`lifecycle.py` is a transport-independent, one-request coordinator. It does not
contain a Moonraker client, physical-printer address, CLI entry point, or
enabled physical adapter. `transport.py` provides the separate bounded HTTP
adapter with actions disabled by default. The one-request
`scripts/temperature-print-relay.py` runner defaults to offline preflight;
execution requires a separate exact private Founder grant and native intent.
Physical wiring remains unactivated; tests use only an injected fake adapter.

The caller constructs `TemperaturePrintLifecycle(journal_path, adapter)`, then
uses this sequence:

1. `bind_request(request, qualification)` validates and durably binds the
   immutable request and offline G-code qualification. This method performs no
   adapter call and cannot start a print.
2. `parse_start_intent(value)` validates the native physical-screen Start
   artifact. `issue_local_permit(...)` creates a separate in-process
   `PhysicalPermit`; the application layer must call it only after the Founder
   has separately authorized that exact physical test. A wire boolean or JSON
   object cannot act as this capability.
3. `start(intent, permit=permit)` rechecks request and intent expiry, fresh
   Moonraker eventtime, ready/idle state, empty queue, no current job, exact
   file bytes and SHA-256. After readback it requires another fresh status
   sample and rechecks identity, ready/idle, current job and queue immediately
   before journaling and dispatch. RPC return is not treated as proof that
   printing began.
4. `poll()` confirms a new running filename/job ID/start time against
   independent history, monitors only that job, and unlocks
   `LifecycleStatus.result_available` only after matching fresh `print_stats`
   completion and independent completed history. A recovered completed journal
   remains locked until another fresh two-source proof passes.
5. `cancel()` is available only for the confirmed owned running job. It
   rechecks current state and history, journals before the one adapter command,
   and requires independently confirmed cancellation. A cancel intent makes a
   later result impossible.

The request schema is
`helix-orca-temperature-print-session/v1`. It preserves the Issue #8 identity
fields, requires `physical_calibration: true`, `not_applied: true`, exactly
`choices: [210, 205, 200]`, and a 3600-second original lifetime. The required
offline report schema is
`helix-orca-temperature-gcode-qualification/v1`; its exact request/file/printer
binding, three bands, geometry, temperature commands and ordering, file
identity, suitability and combined native-plus-startup duration must all pass.
The target is 600–1200 seconds. Durations above 1200 seconds
are rejected. This local reviewed qualification also binds
`physical_printer_identity` as a lowercase SHA-256 digest of the locally
reviewed target identity, which is separate from the Orca saved-preset
`printer` label. Qualification and grant also bind `printer_config_sha256` and
the reviewed `moonraker_version`, rechecked by every real snapshot. The physical
permit binds those values too. The wire
request and Start intent do not add or infer a machine identity.

The native Start artifact uses schema
`helix-orca-temperature-start/v1`. It repeats the exact request, origin,
context, file hash/name/byte count, printer and choices. It also contains:

- `eventtime`: the Moonraker monotonic value sampled for the physical tap;
- `expires_eventtime`: a deadline within the original 900-second Start window; and
- `nonce`: `<request_id>:<eventtime_us>`, where `eventtime_us` is
  `floor(eventtime * 1000000)` with no padding.

The injected adapter normalizes five operations:

```text
snapshot() -> PrinterSnapshot
read_file_bytes(filename) -> bytes
start_print(filename) -> None
history(job_id=None) -> HistoryRecord | None
cancel_print() -> None
```

`PrinterSnapshot` must include the independently established
`printer_identity`, connection/readiness, monotonic eventtime,
`print_stats` state, filename, correlated job ID/start time, and queued job
IDs. `history(None)` supplies the pre-dispatch latest-job baseline;
`history(job_id)` supplies independent running/completion/cancellation proof.
The adapter may normalize Moonraker history's `in_progress` status to the
coordinator's `printing`, but its job ID and print start time must come from
independent current-job/file metadata rather than `print_stats` alone.
Transport exceptions, disconnects, stale/rollback clocks, replacement jobs,
unexpected printer states and ambiguous commands all fail closed. A durable
start or cancel intent is never redispatched after failure or restart.

The runner accepts structurally valid expired grant/request artifacts only for
explicit `--resume` against the exact existing journal. This allows observation
of an already-dispatched job after expiry. Any new start still requires a live
grant, original Start window and native intent; recovery never retries dispatch.
A canonical grant digest is durably bound before offer and cannot be replaced.
An awaiting request requires that same live grant; expiry retires it. A native
tap must follow the authorized offer. The runner creates no grant. No execution command was invoked in Issue #12.

`gcode.py` reads normal native exports only. It verifies three ordered explicit
and extruding bands, geometry, native time and exact bytes; unresolved macros,
actual filament/machine safety and a substantiated allowance for all opaque macros (startup and normal end) must be
reviewed before it can produce a request-bound qualification. The actual
12-minute export remains unqualified for physical use because its combined
cold-start total is unknown. See `docs/TEMPERATURE_PRINT_READINESS.md`.
