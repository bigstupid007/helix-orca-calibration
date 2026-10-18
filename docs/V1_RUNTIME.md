# V1 coordinator and companion — development candidate

This is Issue #14 implementation, not physical deployment or production
qualification. Accepted Temperature hardware behavior, installed files, original
profiles/settings, first/final physical evidence and rollback are unchanged.

## Responsibility and ordinary-use direction

The V1 Orca companion is a generated self-contained `.py` capability. Opening
**Helix V1 Calibration** in the normal native action launcher publishes a private
immutable profile snapshot below `orca.host.plugin.storage()/v1`. It separately
reads saved preset, edited copy and merged serialized settings. Missing data is
unavailable. Only this host storage is used for runtime data/artifact I/O.

`python3 scripts/v1-companion.py /new/path/helix_calibration.py` builds the
candidate without replacing an accepted plugin. Install only into a marked
isolated October 15 test environment for this program. The actual Windows test
uses `%LOCALAPPDATA%\HelixOrcaCalibration\v1-qualification\data`, separate browser
storage, and the hash-pinned October 15 executable. `scripts/v1-windows-review.py`
retains executable/datadir/marker/owner/WebView/pointer checks and excludes other
Orca instances. This testing worker is not a product runtime dependency.

The external coordinator runs on the Orca host. It reads local context, executes
only the explicit configured generator with bounded arguments, retains a durable
one-request journal and offers the native Helix workflow. It replaces the former
one-request agent-operated relay in the development architecture. No inbound
Windows listener, arbitrary command protocol, service installation, scheduled
task, new credential or firewall change is introduced.

## Development operation

```
python3 scripts/v1-runtime.py --storage /exact/plugin/storage/v1 --config /private/config.json
```

Default channel is an **offline directory** below the runtime journal. It cannot
contact a printer. `context.json` and `status.json` there are test channel outputs;
`native.json` is an explicit development input. `--once` performs one bounded
poll. Normal foreground execution polls every two seconds, handles Ctrl+C/TERM,
retains journals and uses storage-scoped and journal-scoped kernel locks.
Health is retained at `v1/runtime/health.json`. The explicit `--run-id` and
`--stop-file` interface accepts only the exact nonce-bound JSON graceful stop.

The [Windows lifecycle package](V1_WINDOWS_RUNTIME.md) adds per-user start,
status and stop with an owned detached supervisor, exact process identity,
private local state and bounded logs. It produces a review-only startup plan;
it does not register startup entries or install a service. Actual Windows
lifecycle qualification is tracked separately from the Linux state-machine tests.

Generator configuration is explicit: exact executable/source/runtime hashes,
assets and optional independent native reference as documented in
[V1 generation/parity](V1_GENERATION_PARITY.md). It never discovers normal profile
files. Generated job directories, logs, inputs, output bytes and reports are
retained below the runtime's owned state tree.

Optional `--moonraker-events` uses only existing exact trusted-LAN HTTP origin,
version pin, V1 event namespace and approved single-file native storage bridge.
The config's `moonraker` object requires `origin`, `expected_host`,
`expected_version`, `existing_trusted_lan_ack:true`; optional `api_key_env` names
an existing environment secret (default `HELIX_ORCA_MOONRAKER_API_KEY`). This
candidate introduces no key or access change and must not be activated against
the accepted physical installation. Existing LAN HTTP remains unencrypted and
has no per-message cryptographic authentication. This is inherited proof-boundary
code, **not production security qualification**. A production deployment decision
must resolve that limitation under the approved security boundary.

## Job and result invariants

Requests bind a retained origin, full context digest, native parameters and a
single-use runtime nonce. A completed/blocked session is archived before a fresh
nonce; active or unreturned completed work cannot be retargeted by profile changes.
Generation persists its intent before invoking Orca. An interrupted preparation
is blocked and never silently rerun. Qualification reopens actual output and
native evidence; a bare true flag cannot enable review. Confirm and Start are
separate immutable native intents. Every intent is consumed durably once.

**The shipped launcher supplies no physical action adapter.** Start cannot
upload, queue, heat, move or print. A trusted in-process normalized adapter
interface exists for isolated tests, with durable dispatch intent, no replay
on uncertain recovery, exact same-job status plus independent completed history,
healthy-job monitoring beyond the Start deadline, and result locking for failed,
cancelled, disconnected or unrelated jobs. This is synthetic behavior proof,
not an implemented or qualified production physical adapter. Production activation
also needs the accepted owned-job/cancellation/configuration safeguards.

A returned result binds original context, prepared bytes, exact job and completion
proof. Orca retains each immutable originating snapshot under `origins/`; only a
matching result can be durably committed. A receipt follows that commit and
contains the full result/digest. Later invalid inbox data cannot hide the last
committed result. Supported host profile lifecycle events flag a subsequent UI
poll to refresh saved/edited/effective context; unavailable selection disables
new preparation without replacing an active job’s original context. Native delivery cannot be claimed before the
originating receipt. The coordinator retains the session until native readback
confirms ACK persistence, so event loss cannot discard the receipt. Results are
**NOT APPLIED**. No preset setter or profile writeback exists.

## Current proof and limitations

Focused tests cover source distinction, generation replay/crash, qualification
flag rejection, separate intents, unrelated-job/history lag, long healthy jobs,
immutable selection, original-context receipt and recovery. Native matrix and
actual isolated Windows observations are separate evidence tiers. Generated
G-code remains local and unqualified until exact parity passes. No new physical
test or deployment is part of this program's validation.
