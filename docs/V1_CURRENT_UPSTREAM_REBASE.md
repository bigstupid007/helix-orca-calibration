# V1 current-upstream completion amendment

## Authority and preserved baseline

The controlling authority is the Founder's 2026-10-25 amendment in Issue #14
(`issuecomment-6401570758`). It supersedes the earlier Build Program only where
that program required exact-request parity, a universal Voron macro ABI,
HelixScreen beta.9, the October 15 Orca build, or a NOT APPLIED result. Draft PR
#15 remains the implementation and review unit and must remain draft and
unmerged until Founder acceptance.

The accepted Issue #12 / PR #13 physical Temperature proof remains valid
historical evidence: Helix chose Temperature, the owner deliberately started
the exact prepared job, the print completed, 220 C was selected, and the result
returned to the originating Orca context. Its installed product, profile state,
physical evidence, and rollback material are preserved. The amendment extends
that workflow; it does not relabel or overwrite the accepted evidence.

Shared Development System authority was reconstructed at
`4a42a944b344427c8f925241191595eb57c6949c`. The clean PR integration worktree
started from `63462643ed647acb52414a571a61aac8c0ce824a`. The dirty canonical
checkout is deliberately untouched.

## Exact upstream pins

The completion candidate is pinned to:

- HelixScreen `v1.1.0-beta.12`, source commit
  `00a9fe6030c37d56748b2122b41fd36de1fdf831`.
- OrcaSlicer nightly source commit
  `b5e9cb3c5e7a925adf8379366ae580e4dabb1d03`.
- Orca's official mutable-preset transaction implementation, introduced by
  ancestor `557feba64931d83908323933b73656ca697f6870`.

The official Orca Windows x64 portable artifact is GitHub Actions artifact
`12608613863` from run `40220020944`. Its archive digest is
`e38b26af21e17e5aa8785a3d6041a7dae9cb934060571ce947b33b7ce10346c0`;
the contained `orca-slicer.exe` digest is
`aab75b0bf66bba057e695ffd8425d723f881b7d409a496c486caad0983fe6761`.
The x64 build job (`121250255545`), Windows build-script tests
(`121249364052`), and x64 unit tests (`121261641595`) succeeded. The upstream
workflow's overall conclusion is failure because its macOS arm64 cache check
failed; this record does not misstate the mixed-conclusion run as wholly green.

The beta.12 SDL review artifact is release asset `671432139`. Its archive
digest is `c87b12c8c6e884ac788fc28de326d9c4e1e19329531e758ac2ca65f12bbabee3`
and its `helix-screen` digest is
`3811d962d76d1d652602c5cc465fd7487db76bd1f00fceb343d10c52111a93db`.
The x86 framebuffer installation artifact is release asset `671432152`, with
archive digest `175ee88dcecd69dfee3c32fa987ba3b9f2258eda29c9c9cc90d9fff37ef7b172`
and binary digest
`cc6208976b66ed41dc35dce43379856136666f632ee77b14d14b32a131232fd4`.
Release artifacts are accelerators only. The durable bootstrap must still build
the exact source and all fourteen recursively pinned submodules.

## Controlling product interpretation

Orca owns printer-specific calibration preparation, final slicing, start/end
G-code, heater behavior, movement, and placement. Product qualification is
therefore bound to an exact generator build and route, exercised over a
representative matrix. An ordinary native-valid future request uses that
qualified route without requiring a duplicate native reference for its exact
values. Each generated job remains independently bound to its request, context,
artifact bytes, processing result, warnings, target, and execution history.
The qualification record also binds the exact adapter/resource inventory and
installed package manifest. Startup, generation, Confirm, and Start recompute
that closure; changing any executing byte invalidates qualification instead of
carrying a prior build result forward.

Known non-fatal Orca warnings remain visible and require a deliberate,
request-bound acknowledgement before physical Start. Unknown warnings and all
fatal processing errors fail closed. The historical 60 C bed / 55 C
vitrification case must be rerun as a warning-flow regression; it must not be
silently suppressed or treated as a slicing failure.

The owned-job adapter is printer-neutral. It retains random no-overwrite names,
upload-without-start, remote byte readback, fresh idle and empty-queue checks,
separate Confirm and Start, journal-before-side-effect one-shot dispatch,
exact-job monitoring/history, exact-owned cancellation, and conservative
recovery. A universal `PRINT_START` / `PRINT_END` macro signature is not a
product prerequisite. Target identity, live configuration, profile/nozzle
binding, and beta.12-equivalent fit findings are explicit qualification inputs.
The physical Voron target may be action-enabled only after its exact gate passes;
AD5X is a generation, slicing, and context-compatibility target and cannot
construct a physical action adapter in this program.

## Originating preset transaction

The result targets the immutable originating filament's explicit 1-based slot
and preset identity. Multi-slot contexts require an explicit origin choice;
the plugin must never infer a slot from the globally edited filament tab. Apply
runs only on Orca's Script worker through
`orca.host.preset.filament.begin_update(slot_number=..., preset_name=...)`,
stages serialized values, and commits once. It never writes preset files or
saves the preset.

The source-current mappings are:

| Calibration | Official filament setting transaction |
| --- | --- |
| Temperature | `nozzle_temperature`; initial-layer temperature is unchanged |
| Flow Ratio YOLO | `filament_flow_ratio` |
| Pressure Advance Pattern | `enable_pressure_advance = "1"` and `pressure_advance` in one batch |
| Retraction | `filament_retraction_length` |
| Maximum Volumetric Speed | `filament_max_volumetric_speed` |

Orca's own selection and unsaved-edit dialogs are authoritative. Cancellation,
stale slot mappings, invalid values, or commit failure leave the result pending
and retryable. A crash after commit but before a durable receipt is uncertain
and must not be blindly replayed. A verified success is presented as modified in
Orca and unsaved, including the transaction's target, dirty state, changed slot
assignment, and shared slots.

## Native and operational review boundary

Beta.12 plugin dialogs, overlays, confirmations, and editors are queued behind
application-owned dialogs. Result presentation therefore waits for Orca/Helix
application surfaces, supports dismissal and manual reopen, and never assumes a
queued surface is already visible. `helix.ui.edit_number` is used where its
two-decimal limit preserves the value; a bounded precise path remains for
Pressure Advance and any other native-valid higher-precision input.

The pinned Orca numeric domains are preserved exactly: PA start/end remain in
0–2 with step at least 0.001; Retraction accepts start at or above zero and any
strictly positive step; MVS accepts strictly positive start and step. Result
sets up to 128 values use the native dropdown. Larger native-valid sets remain
bounded as start/end/step and use the owned precise keypad, with arithmetic
membership validation rather than eager list allocation.

The coordinator is an ordinary owner-local, per-user runtime with explicit
install, status, start, stop, restart, rollback, and uninstall. It creates no
service, machine account, public listener, firewall rule, or new credential.
Installed code is immutable and manifest-bound; mutable state, job journals,
logs, accepted evidence, and rollback material remain outside the versioned
package.
Each installed candidate retains its own exact originating storage, config and
deployment-authorization binding. Rollback restores that complete candidate tuple rather
than combining old code with the newer candidate's target authorization.
Likewise, Orca application state is request-scoped: a completed calibration is
archived before the next exact inbox is applied, while unrelated unresolved or
uncertain state still fails closed.

No physical run is qualified by this document. After implementation, current
Windows acceptance, beta.12 eleven-target evidence, AD5X compatibility,
installation/rollback, exact-head CI, fresh independent engineering review,
Cold-Start UX, AI Product Preflight, and all other non-consequential gates pass,
the five authorized calibrations run one at a time on the Founder's Voron. Each
physical dispatch still requires the Founder to deliberately press the native
Helix Start control; generation, receipt, recovery, or an agent never substitutes
for that action.

## Frozen completion candidate

The completion candidate is frozen at
`2f1ffe1041b9f591d2c621e821975f53414efd65`. Build-level qualification remains
bound to product head `4c0379b05e9a58a7546b42da9fbcc09658fabba8` and harness
head `992577c15aac24ee7b23cf850c98f016c0ac73a4`. The intervening commits are
bounded companion-name/UI-thread, transport, machine-binding, warning-recovery,
owner-runtime, and owned-job recovery corrections; they do not change the
qualified generator, route, Orca executable, or resource closure. The final generator corrections
project current Orca's comma-delimited numeric/nullable vectors and its exact
semicolon/C-style string cells into each active CLI filament preset, while
retaining comma/bracket-bearing strings and the accepted V2
`filament_flow_ratio` wire representation. The 55-key string-vector type
inventory exactly matches the pinned Orca source. The accepted base
Temperature companion remains byte-identical at
`8f0269e6510ca11848144c14fc2c42a33ea288e8dd1bfa7bd1e5789636bf3d52`.
The correction changes no Helix product byte.

The initial exact Windows qualification at `60dbbad` then exposed one native
MVS parity defect rather than a navigation/timing failure: the adapter rejected
a UI-valid range when its calculated cut height exceeded the stock asset.
Pinned Orca keeps the full asset and attempts the final slice in that case.
`f838503` removes the extra rejection; the failed run remains preserved as a
separate diagnostic and was not retried at the old head.

The first `f838503` Windows qualification then exposed a second actual adapter
assertion at AD5X Temperature/default: the adapter promoted a pinned Orca
`Print::validate` floating-cantilever warning to a fatal error. Pinned Plater
instead continues when `error.string` is empty and presents those entries as
nonblocking `ValidateWarning` notifications. `cb46647` restores that split and
retains the exact warning array as hash-bound private case evidence. The failed
run remains preserved and was not retried at `f838503`.

The next exact Windows qualification exposed a third actual adapter assertion:
an Orca final-slice warning was still classified as fatal. `4c0379b` follows
pinned Orca's warning severity while retaining the exact warning evidence. Its
subsequent AD5X Flow failure came from a preserved owner process with Spiral
vase enabled, not a product defect; the product was frozen and representative
qualification moved to another already-preserved native AD5X process with
Spiral vase off.

That context-corrected run then reached the exact `0.01→0.011/0.001` MVS
stress corner. Pinned Orca correctly rejected the approximately 1001 mm tower
against AD5X build volume. Per Founder direction the failed run is retained as
separate extreme-range evidence. `992577c` changes only the representative
matrix cell to `0.01→1.01/1`; ordinary runtime remains open to every finite
native-valid request and reports exact native fit blockers.

The frozen source passes 637 dependency-free tests with seven host skips,
the protected Temperature preservation verifier, the beta.9 preservation proof,
and `git diff --check`. Exact-`992577c` CI run `40342726011`, Temperature
readiness run `40342726039`, and V1 native-UI run `40342726496` pass;
source-pinned Windows run `40342726026` passes. The retained actual Windows
matrix qualifies 50/50 cases and the final owner-local runtime completes its
stop/rollback/install/start/status sequence. Exact frozen-head CI also passes:
offline evidence `40454341347`, policy `40454341394`, native UI `40454341387`,
and pinned Windows native engine `40454341448`.

One exact-head official-Orca GUI capture ended before product interaction with
`Capture is occluded.` The diagnostic is preserved and separated from product
evidence. It is not an application assertion, was not retried, and caused no
product change. The focused beta.12 proof remains the core presentation
evidence; its frames are independent fixtures, not a sequential exact-job
trace. Twenty-six of its 28
captured source files are unchanged at freeze, while the two protocol/runtime
files changed later and are covered by tests and bounded playback rather than a
new screenshot matrix. The prior eleven-target run remains layout lineage and
the separate range proof remains an extreme harness diagnostic.

The bounded physical continuation then exposed a different limit. One exact
Temperature job reached prepared review, warning acknowledgement, Confirm, and
the Founder's deliberate Start, but printer readiness rejected before upload.
Independent readback proved that no file was uploaded or started. After the
recovery corrections and a complete owner-runtime upgrade, beta.12 still
presented that retired uncertain request as active while the healthy coordinator
held no request; Request generation returned to the chooser. Per Founder
direction this stale-session/navigation failure was preserved, the product was
frozen, and no further repair loop or physical retry began. The amendment's five
new end-to-end physical workflows therefore remain incomplete rather than being
inferred from the accepted Issue #12 Temperature print.
