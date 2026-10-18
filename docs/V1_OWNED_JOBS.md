# V1 owned-job adapter candidate

`integration/v1_jobs.py` supplies a bounded owned-job adapter for the integrated
coordinator. It supports every calibration through the same prepared-artifact
contract. It neither generates G-code nor makes an unqualified generator work.
Both its transport and adapter default to `actions=False`. The ordinary review
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
recognizing the accepted command signature under pinned configuration is not a
new physical qualification.
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
    "existing_trusted_lan_ack": true,
    "actions_enabled": false
  }
}
```

Missing configuration or either disabled gate returns `None`, creates no
adapter journal and makes no network/process request. An enabled configuration
alone cannot authorize deployment. `deployment_authorized=True` must come from a
separate explicitly approved local deployment gate in the launcher, never native
storage/events or Orca data. Only both gates permit construction of the active
adapter. Existing credentials may be supplied separately by the local caller;
this module neither creates/discovers credentials nor changes access policy.
The private journal root must remain beneath the launcher's owner-private
runtime directory. One coordinator/adapter root and its kernel instance lock
must govern the printer; independent uncoordinated installations are unsupported.

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
and retained journals are the recovery route.

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
