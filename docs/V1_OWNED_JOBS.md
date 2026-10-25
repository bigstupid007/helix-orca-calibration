# V1 owned-job adapter candidate

> **Current adapter authority:** printer-neutral exact-job execution replaces
> the universal `PRINT_START` / `PRINT_END` ABI. The amended adapter retains
> no-overwrite naming, upload-without-start, remote byte readback, fresh
> target/idle/queue checks, separate Confirm and Start, one-shot recovery,
> exact history, and exact-owned Cancel, with beta.12-equivalent fit findings.
> Voron may be physically enabled only by its exact target qualification; AD5X
> remains generation-only. [Amendment record](V1_CURRENT_UPSTREAM_REBASE.md).

`integration/v1_jobs.py` supplies a bounded owned-job adapter for the integrated
coordinator. It supports every calibration through the same prepared-artifact
contract. It neither generates G-code nor makes an unqualified generator work.
The adapter requires an explicit reviewed `orca_machine_sha256` and a typed
physical target qualification in addition to the transport's physical/configuration
pins. Both action switches default to `actions=False`. The ordinary review
launcher has no enabled physical action adapter. No physical deployment or print
is claimed by this source implementation or its loopback HTTP fixtures.

The design preserves the accepted Temperature transport/lifecycle safeguards
without editing those accepted modules: pinned private host and Moonraker
version; exact MCU/network physical identity and reviewed configuration digest;
ready idle printer and empty queue; readback; two distinct native actions;
durable one-shot dispatch; correlated live metadata and independent history;
and cancellation only of the exact independently owned running job. As in the
accepted lifecycle, Start requires `standby` with no current filename/job. It
never clears or resets another print's state to obtain that precondition.

## Integration and default-off construction

The coordinator calls these exact interfaces:

```python
adapter.confirm(request, prepared, directory, native_confirm_intent)
job = adapter.start(request, prepared, directory, native_start_intent)
job_or_none = adapter.recover(request, prepared, exact_retained_native_start_intent)
proof = adapter.observe(job)
adapter.cancel(job, native_cancel_intent)
```

Confirm verifies the current request, exact artifact and independent parity
report, then requires its digest-bound
`candidate_invariants.macro_semantics.accepted_abi_signature` to be exactly
`true` before retaining the request/prepared objects and native Confirm ID.
Native-only `PRINT_START EXTRUDER/BED` parity cannot pass this gate for the
accepted target's `EXTRUDER_TEMP/BED_TEMP` signature. Missing/null semantics also
blocks upload (including a Flow report that has not implemented this invariant).
The report's `hardware_abi_qualified` and `physical_readiness` remain false:
recognizing the accepted command signature alone is not a physical qualification.
An additional independently reviewed local target qualification is mandatory;
the source implementation and synthetic tests create no operational qualification.
Start requires a different native ID bound to the same prepared SHA-256. It
re-verifies the artifact/parity and original expiry before any upload and again
checks expiry before Start dispatch. Cancellation remains available after the
original request's Start window expires, but only for the retained owned job.
No wire flag, incoming request, result or plugin context can authorize actions.

The typed factory is:

```python
from_config(config: dict, root: Path, *, deployment_authorized: bool = False,
            api_key: str | None = None) -> OwnedJobAdapter | None
```

`config` is the existing private coordinator configuration. Its optional
`owned_jobs` section has exactly these fields (values below are placeholders,
not a deployable configuration):

```json
{
  "owned_jobs": {
    "schema": "helix-orca-v1-job-deployment/v1",
    "origin": "http://<exact-private-IPv4>:<existing-port>",
    "expected_host": "<same exact private IPv4>",
    "expected_version": "<reviewed installed Moonraker version>",
    "physical_identity": "<reviewed lowercase 64-hex digest>",
    "configuration_sha256": "<reviewed lowercase 64-hex digest>",
    "orca_machine_sha256": "<reviewed full Orca printer-profile and nozzle digest>",
    "physical_qualification": "<typed reviewed object described below; never a flag>",
    "existing_trusted_lan_ack": true,
    "actions_enabled": false
  }
}
```

Missing configuration or either disabled gate returns `None`, creates no
adapter journal and makes no network/process request. An enabled configuration
alone cannot authorize deployment. `deployment_authorized=True` must come from a
separate explicitly approved local deployment gate in the launcher, never native
storage/events or Orca data. The integrated coordinator's optional
`--deployment-authorization` requires a separately approved, existing
owner-private ordinary local file. It validates every ancestor against
links/reparse points and independently inspects POSIX owner/mode or Windows
current-token SID and file DACL without a subprocess. The exact local schema
`helix-orca-v1-local-deployment/v1` requires `approved: true`,
`native_start_only: true`, a nonempty approval reference, the canonical private
configuration digest, and a runtime closure fingerprint covering the CLI,
`integration/v1_*.py` and `scripts/helix-display-request.py`. The review creates no
such approval record. An enabled target also requires `--moonraker-events` and
identical pinned native-event/job origins, hosts and versions. Only both gates permit construction of the active
adapter. Existing credentials may be supplied separately by the local caller;
this module neither creates/discovers credentials nor changes access policy.
The private journal root must remain beneath the launcher's owner-private
runtime directory. One coordinator/adapter root and its kernel instance lock
must govern the printer; independent uncoordinated installations are unsupported.

The machine digest is exactly
`digest({'printer': report['inputs']['profiles']['printer'], 'nozzle_mm': report['inputs']['nozzle_mm']})`
from the independently verified report. It pins the complete saved/edited Orca
machine profile object and numeric nozzle, not a display name. A missing or
mismatched machine/nozzle blocks before HTTP. Ordinary process and filament
selection remain request scope and are not pinned by this field. Any machine-pin
change changes the private configuration digest and requires a new separately
approved deployment record.

## Required physical target qualification

The local `physical_qualification` object has exactly these fields:

- `schema`: `helix-orca-v1-physical-target-qualification/v1`.
- `physical_identity`, `configuration_sha256`, `orca_machine_sha256` and
  `moonraker_version`: exactly the transport/machine pins above.
- `macro_safety_reviewed` and `printer_safety_reviewed`: both boolean `true`;
  `review_reference`: a nonempty bounded reference of at most 512 characters.
- `start_required_arguments`: exactly `["BED_TEMP", "EXTRUDER_TEMP"]`.
- `macro_sources_sha256`: uppercase custom macro names mapped to SHA-256 of each
  actual parsed Klipper `gcode_macro <name>` settings section using the shared
  canonical JSON digest. The exact inventory includes directly invoked custom
  macros and every statically resolved transitive custom call.
- `motion_bounds`: exact `X`, `Y`, `Z` keys, each a finite increasing two-number
  list. `filament_range_c`, `nozzle_range_c`, and `bed_range_c`: reviewed finite
  increasing temperature ranges (bounded to 0–600°C for filament/nozzle and
  0–150°C for bed).

Constructor validation binds this record to the exact physical/configuration,
machine/nozzle and Moonraker version. Confirm retains its digest; Start must see
that identical qualification digest. Actual candidate bytes are independently
parsed before any HTTP: every visible travel/deposition coordinate must fit the
reviewed XYZ envelope, every nonzero visible nozzle target must fit both
filament and nozzle ranges, and every nonzero bed target must fit the bed range.
Zero heater-off commands are permitted. Exactly one positive-target
`PRINT_START BED_TEMP=… EXTRUDER_TEMP=…` and one argument-free `PRINT_END` must
surround actual visible deposition. Arc geometry, XYZ rebasing, unknown units,
malformed motion/heater values, unreviewed custom commands and extra custom
macro arguments require separate qualification and remain blocked. Named
heater/offset/stepper mutation commands in candidate G-code are outside the
bounded visible-command inspector and are rejected rather than skipped.

Every live snapshot already re-verifies full printer configuration and physical
identity. It additionally hashes actual macro sections, inspects the real
PRINT_START `params.*` argument names and builds a static transitive call graph.
The candidate's exact custom invocation closure must match the reviewed source
inventory and digests. Standard Klipper/G-code commands remain built-ins;
configured macro overrides of their names require their actual reviewed sources.
Missing helper macros, dynamic command names, unsupported inline template
constructs, unresolved calls, recursive calls or unrelated inventory entries
block upload. No template or macro is executed during this inspection.

This conservative static inventory supports literal command names, separate-line
bounded Jinja control/set statements and response/error template actions. It
does not claim a general Jinja interpreter or prove runtime macro expansion.
The explicit source safety review remains mandatory; macro internals remain
unobserved in parity reports, and their `hardware_abi_qualified` and
`physical_readiness` flags remain false. No safety record, deployment approval,
real macro qualification or new physical print is produced by this build.

## Ownership and failure behavior

Each staging filename contains the exact request ID and a fresh random 128-bit
suffix. Before staging, the adapter refuses existing metadata **and** existing
file bytes. The multipart upload fixes `root=gcodes` and `print=false`; its
acknowledgment must explicitly say `print_started=false`, `print_queued=false`,
and name that exact owned file. The adapter reads the uploaded bytes back, then
requires another fresh idle/queue snapshot before the separate Start request.
No upload ever requests print or queue insertion. No file is automatically
removed, overwritten, renamed or cleaned up after failure.

The private per-request journal records upload intent before upload, Start
intent before Start, and Cancel intent before Cancel. Recovery cannot resend
these operations, including after an ambiguous response. An active-operation
journal blocks new request dispatch while an earlier operation remains
unresolved. After Start, up to 30 seconds of bounded observation must establish
an actual new job ID/start time: same unique filename, live print metadata and
matching `in_progress` history beyond the retained history baseline. A command
acknowledgment alone never becomes a running job. If correlation times out,
state stays uncertain and dispatch retry is forbidden; native printer controls
and retained journals are the recovery route for an unproven job.

`recover(request, prepared, intent)` is a read-only, idempotent adoption path
under the adapter lock. It performs zero transport calls, writes no job state,
and never uploads, dispatches, retries Start or sends any HTTP mutation. It
returns a four-field public handle only when the exact retained request,
prepared descriptor, full distinct Start intent and qualification digest match
an already independently history-confirmed durable job. Supported durable phases
are printing, terminal states and owned cancel phases; pre-job or ambiguous
phases return `None`. Mismatched identities or intents fail closed. Merely
having metadata or a non-null job ID in an uncertain journal is insufficient.

Before dispatch the coordinator atomically retains the complete
`pending_start_intent`. If the adapter saved independently confirmed printing
but the coordinator died before saving its job handle, `poll_job` adopts only
the exact recovered handle, persists it and then obtains fresh independent
observation. Recovery does not reuse old status as completion proof. Monitoring,
exact cancellation and returned results remain available after the original
Start expiry; no new Start window or action is created.

Observation requires fresh eventtime and the exact owned filename/job ID/start
time. Successful completion additionally requires independent history with that
same identity, `completed`, and a valid end time after the original start. A
current owned-file readback must still match the prepared hash. The normalized
`history_file_sha256` therefore means correlated history plus verified owned-file
readback; Moonraker does not supply an independently signed history G-code hash.
Replacement jobs, stale metadata, missing history or changed files keep
evaluation locked. Cancellation requires two fresh snapshots, an empty queue, and matching
running history immediately before dispatch. A Cancel acknowledgment is not
completion: matching cancelled history must prove cancellation. An ambiguous
Cancel is never retried, and racing completion never silently reverses the
user's cancellation into an evaluable result.

The transport has fixed routes only: bounded identity/status/configuration,
queue status, owned file metadata/readback, one-job history, owned G-code upload,
Start and Cancel. It provides no arbitrary RPC/G-code command, queue mutation,
profile/configuration/firmware mutation, listener or startup registration. HTTP
responses are bounded (JSON 1 MiB, G-code 20 MB); requests use five-second timeouts,
no ambient proxy, no redirects, and an exact private IPv4 origin. Production
TLS/credential provisioning and public exposure are outside this candidate.

## Verification and remaining limits

The dependency-free tests use a real HTTP server bound only to loopback. A
test-only opener rewrites the pinned synthetic private origin to that fixture;
no printer or private network host is contacted. Synthetic G-code tests inject
only the parity verifier, whose genuine behavior has its own mandatory harness
tests. They claim no native generation parity or physical qualification.

The fixtures cover multipart no-print/no-queue staging, artifact tampering,
configuration changes, busy queue/existing filenames, disabled action gates,
separate Confirm/Start, request expiry, upload readback mismatch, ambiguous Start
and recovery, unresolved earlier jobs, bounded history timeout, unrelated jobs,
independent successful history, exact owned Cancel, cancellation ambiguity and
racing completion. No fixture result can qualify production physical behavior.
The added true Coordinator↔OwnedJobAdapter HTTP fixtures kill execution after
the adapter's durable independently confirmed `printing` journal and before
the coordinator saves its handle. A fresh coordinator/adapter then adopts and
observes that same job, proves successful completion and returns a result, or
cancels the exact owned job. Both paths assert one upload and one Start only.
Additional negative tests cover review/binding/range errors, actual macro source
and argument mismatch, transitive/dynamic macro resolution, unchanged
qualification digest and read-only ambiguous/mismatched recovery.

Known limits remain explicit:

- Moonraker's upload API has no atomic create-only condition. Random owned names,
  existence checks and exact readback reduce collision risk but do not prove an
  atomic reservation against another privileged client. Concurrent external
  writers can also race any preflight; deployment requires the existing private
  trust envelope and one coordinating owner.
- The supported upload envelope is at most 20 MB even though the generic prepared
  contract permits larger files. Larger files fail before upload.
- An uncertain Start may have dispatched before metadata/history could prove a
  job ID. The coordinator cannot claim ownership or offer programmatic Cancel
  for that unproven job; use the printer's native controls. No retry is offered.
- The 30-second ownership window is a loop deadline; a final bounded HTTP snapshot
  may finish after it. Individual HTTP operations retain their five-second
  timeouts. This is not a hard real-time supervisor.
- Journal integrity assumes the launcher's private user ACL and a single retained
  adapter root. A separately approved deployment must verify that envelope,
  existing credentials/transport security, and actual target behavior. No such
  physical activation or new print is authorized or performed here.
