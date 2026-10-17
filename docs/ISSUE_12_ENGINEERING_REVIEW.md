# Issue #12 corrected candidate — engineering review

Authority: direct Founder correction of 2026-10-17, current
[Build Program](BUILD_PROGRAM_TEMPERATURE_PRINT.md), application AGENTS.md and
published shared Development System main
`4a42a944b344427c8f925241191595eb57c6949c` (verified on resume).
Application main remains `89165d15993ccfcd065b299e1980bb19749fdcaf`.
Continue Issue #12 / PR #13, unmerged.

## Independent source review: PASS

A fresh-context GPT-5.6 Sol / High reviewer inspected the candidate and the
consolidated corrections, independently reran **54/54 affected tests**, and
reported no remaining material source finding. The full repository suite
passes **243 tests**. Accepted beta.4 and Issue #8 evidence verification and
`git diff --check` pass. This source disposition does not claim Windows or
hardware proof.

The source enforces exactly 225/220/215°C and original effective nozzle 220°C.
Saved and edited temperatures remain separate original values. Native print
estimates are finite, positive information, with no print-duration ceiling,
combined-time requirement or additional filament checkpoint.

Review found and the lead corrected post-dispatch request/lease/runner cutoffs,
premature failure on initial metadata/history lag, missing effective-220
binding, and the directly implicated active-slot and rejected-Start recovery
cases. A healthy owned job may exceed its estimate and original request expiry.
Request/grant expiry and the 900-second Start window still prevent new dispatch.
Fresh machine/configuration/version, status and exact owned-job history remain
mandatory throughout observation, cancellation, completion and recovery.

Initial missing/previous metadata and explicit metadata/history 404 responses
remain pending only inside the persisted 30-second confirmation deadline.
Contradictory evidence, other transport errors, unexpected jobs and deadline
expiry stay locked; pending state grants no ownership, result or redispatch.

A durable request-scoped local lifecycle marker is written before dispatch and
prevents abandoning a started/uncertain companion slot at TTL expiry/restart.
Deterministic authorization/preflight rejection consumes the native tap and
publishes failure with zero dispatch. An ambiguous command outcome publishes
uncertainty, keeps the slot blocked and cannot retry. Only the retained exact
request/context/file/job/completion proof may return a post-expiry selection;
a newer request rejects the old result. Return remains NOT APPLIED.

## Evidence dispositions

The renewed native eleven-target capture passes: **88 frames and eleven storage
snapshots**, promoted and verified against current source. It exercises effective-220 gating,
post-expiry active-session replacement refusal, monitoring/restart, result/ACK
and cancellation, in addition to the retained one-shot and failure invariants.
Its final report is in [current evidence](evidence/issue-12/README.md).
All native authorization/job/status/clock/completion inputs are synthetic.

Actual corrected Windows export and current 0.6.1 companion proof pass. The
installed source hash was verified before restoration:
`30a5a51539e432513181d04966d09196d93057d085ba5d918ea77a262164c86b`.
The exact Windows outbox, native persisted selection, inbox and originating
receipt are correlated; only that receipt permits native ACK. Completion is
explicitly synthetic. Exact-file offline suitability and read-only command,
macro, purge/park and acceleration review pass. Accepted companion restoration,
12 saved user profiles, 1,429 normal files and five communication artifacts are
verified. See [Windows qualification](ISSUE_12_WINDOWS_NATIVE_QUALIFICATION.md).
Affected Windows Product Preflight passes; PR #13 owns final exact-head CI.
Earlier reviews/captures at `68d1029`, `baf08d5` and `ac84114` do not replace
current export evidence.

## Final actual-file and integration review: PASS

The independent reviewer inspected the exact raw export, private GET-only
configuration/status evidence, current Windows and isolated native frames,
source binding, all request/result/receipt identities and final restoration.
No material file, UI, lifecycle-evidence or preservation blocker remains.
The export has 25 extruding layers in each approved band. Offline macro,
registered-command, geometry and acceleration checks pass. The genuine
originating Windows receipt precedes native ACK; the 220°C return remains
NOT APPLIED. Native completion is synthetic, not measured physical quality.
The reviewer idempotently reproduced the private deterministic qualifier once;
only its three derived private JSON outputs were rewritten from unchanged
inputs. Those outputs are reproducible analyses, not untouched capture mtimes.
No repository, Windows, network or hardware state was changed by that rerun.

Final read-only documentation and sanitized-evidence review is PASS: current
claims match retained proof, source hashes match, private operational data is
excluded, and physical execution remains separately authorized.

Final local validation passes 243 tests, accepted beta.4 and Issue #8 evidence,
current source-bound Issue #12 eleven-target evidence, static harness contract
and whitespace checks. Canonical HEAD and all sixteen pre-existing file hashes
match the private resume baseline. The Windows test process is closed, accepted
0.5.0 restored, and no candidate remains installed on a physical printer.

Accepted implementations/evidence, normal profiles, the dirty canonical checkout
and existing security boundaries remain preserved. No live grant/permit,
physical derivative installation, upload/queue/start, print, heating, motion,
macro, firmware/configuration change, profile writeback, merge, deployment or
Alpha physical adoption was performed.
