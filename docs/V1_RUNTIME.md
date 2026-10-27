# V1 coordinator and companion — development candidate

> **Current completion scope:** the October 25 amendment authorizes an ordinary
> owner-local installed coordinator and an action-enabled physical Voron target
> after exact gates pass. The current companion targets pinned Orca `b5e9cb3c`
> and applies a completed result to the explicit originating filament through
> Orca's official transaction, leaving it dirty and unsaved. Historical
> October 15 / NOT APPLIED descriptions below are preserved candidate history.
> [Amendment record](V1_CURRENT_UPSTREAM_REBASE.md).

This is the Issue #14 amendment candidate. The amendment explicitly authorizes
the exact-package, exact-config, exact-target owner-local installation and five
controlled Founder-started Voron calibrations after the non-consequential gates.
It is not a general production deployment or security qualification. Accepted
Temperature behavior/evidence and its rollback remain preserved.

## Responsibility and ordinary-use direction

The V1 Orca companion is a generated self-contained `.py` capability. Opening
**Helix V1 Calibration** in the normal native action launcher publishes a private
immutable profile snapshot below `orca.host.plugin.storage()/v1`. It separately
reads saved preset, edited copy and merged serialized settings. Missing data is
unavailable. Only this host storage is used for runtime data/artifact I/O.

`python3 scripts/v1-companion.py /new/path/helix_calibration.py` builds the
candidate without replacing the accepted base plugin. Current validation uses
the marked isolated official `b5e9cb3c` Windows portable runtime, a dedicated
data directory, separate WebView storage and exact executable/library/plugin
hashes. The SPARE testing bridge and UI driver remain evidence infrastructure;
neither is an ordinary product dependency.

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

Both runtime and offline generation CLI use `integration.v1_routing`: stock CLI
for Temperature/YOLO by default, receipt-guarded native engine for PA Pattern,
Retraction and MVS. The private `routes` map can explicitly select `stock-cli` or
`native-engine` per known calibration; unknown values fail and no fallback occurs.
Native configuration is isolated under `native_engine` and must bind actual build
receipt, inputs, executable and resources. Source presence never makes a route
available. Native build qualification and exact native-UI evidence remain separate
gates. A caller cannot select a route through its request payload. In V2, the
exact build qualification authorizes the pinned stock routes for Temperature/YOLO
and the pinned native-engine routes for PA Pattern, Retraction and MVS over the
full Voron/AD5X matrix. Runtime startup and every generation revalidate the
executing package, adapter, resources and route closure. A native-valid request
within a qualified route does not need a new per-request native reference, but
its own request, context, processing result, warnings and artifact bytes remain
exact.

Optional `--moonraker-events` uses only existing exact trusted-LAN HTTP origin,
version pin, V1 event namespace and approved single-file native storage bridge.
The config's `moonraker` object requires `origin`, `expected_host`,
`expected_version`, `existing_trusted_lan_ack:true`; optional `api_key_env` names
an existing environment secret (default `HELIX_ORCA_MOONRAKER_API_KEY`). This
candidate introduces no key or access change; only the exact separately bound
amendment deployment may activate it against the reviewed Voron. Existing LAN HTTP remains unencrypted and
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
separate immutable native intents. Every intent is consumed durably once. Confirmation outcome and intent consumption are one atomic journal update.
Start consumption and the complete pending intent are persisted with `starting`
before dispatch. Restart can adopt only an exact already-owned post-dispatch job
through read-only adapter recovery; it never replays Start. Native restart
reconciliation binds the complete retained request, preparation, job and completion
proof and advances the sequence without weakening stale-status rejection.

**The default launcher supplies no physical action adapter.** Only the separately
authorized amendment configuration can construct one for the exact reviewed
Voron target; the AD5X target is generation-only. The integrated
[owned-job adapter](V1_OWNED_JOBS.md) implements bounded staging/readback,
separate Confirm/Start, durable one-shot dispatch, exact-job status plus independent
history, owned cancellation and conservative recovery. Its real HTTP fixture
proof is synthetic; no new physical qualification or activation is claimed.

The optional `--deployment-authorization` path is a separate local gate, never a
native event, profile field or incoming request. For the controlled amendment
run, the owner-private record references Issue #14 comment `6401570758` and must
bind the exact private configuration and complete V1 Python runtime fingerprint,
and require native-Start-only operation. Direct CLI use independently validates
file ownership/privacy and every path ancestor. Both this gate and the explicit
owned-job configuration must agree before construction; active jobs also require
the exact same native-event printer origin/version. The [deployment boundary](V1_DEPLOYMENT.md)
records the acceptance and physical activation requirements.

A returned result binds original context, prepared bytes, exact job and completion
proof. Orca retains each immutable originating snapshot under `origins/`; only a
matching result can be durably committed. A receipt follows that commit and
contains the full result/digest. Later invalid inbox data cannot hide the last
committed result. Supported host profile lifecycle events flag a subsequent UI
poll to refresh saved/edited/effective context; unavailable selection disables
new preparation without replacing an active job’s original context. Native delivery cannot be claimed before the
originating receipt. The coordinator retains the session until native readback
confirms ACK persistence, so event loss cannot discard the receipt. In the
current V2 path the Script worker applies a verified result through Orca's
official `preset.filament.begin_update` transaction against the immutable
originating slot and preset. It commits one atomic batch, never calls Save,
never writes preset files, and requires Orca to report the expected target,
unchanged slot assignment and dirty state. Temperature changes only
`nozzle_temperature`; Pressure Advance commits both enable and value together.
Failure is retry-bound; an uncertain post-commit outcome is never replayed.
The historical V1 path remains NOT APPLIED and is not the amended workflow.

## Current proof and limitations

Focused tests cover source distinction, generation replay/crash, qualification
flag rejection, separate intents, unrelated-job/history lag, long healthy jobs,
immutable selection, original-context receipt and recovery. Native matrix,
actual isolated Windows observations and controlled physical receipts remain
separate evidence tiers. Current G-code remains local and unavailable until its
route's exact build qualification passes; physical Start additionally requires
the target and exact-file gates above.

## Monitoring and companion review corrections

The owned-job adapter reads elapsed time from Klipper `print_stats.total_duration`
and progress from `virtual_sdcard.progress` only when the file path matches the
exact owned artifact. It publishes these only after the same-job identity/history
checks. Each metric may be unavailable independently. A malformed or missing
metric clears the previous value; neither a timer nor 100% progress permits
evaluation. Actual completed same-job history remains mandatory.

The companion keeps the current Orca selection separate from the immutable
original calibration context and the originating context of the retained result.
The heading and preparation badge follow the same actual phase; waiting and
blocked states use attention styling. **Refresh selection** recaptures the host
selection without changing presets. Connection details describe retained health
as “last reported running” or “stopped,” rather than claiming a live heartbeat.
The candidate always states that physical execution is disabled. These source
corrections address the independent native Windows review; final target captures
and review status are recorded separately.
