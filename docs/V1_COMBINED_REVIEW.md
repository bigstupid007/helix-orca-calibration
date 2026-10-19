# V1 combined independent review

The program uses one combined substantial review, with bounded correction
rechecks. A fresh-context independent Codex reviewer reviewed the
integrated change from accepted main `523bc5d` through `d7634bf`. The reviewer
read the initiating scope, governing program, shared contracts and implementation;
it did not implement the reviewed changes. Founder acceptance remains pending.

The review identified five material issues. All five were corrected in the
integration branch and independently rechecked:

| Finding | Correction and verification |
| --- | --- |
| P1: restarted native UI could remain locked behind an equal status sequence | Explicit read-only coordinator reconciliation validates the entire retained binding, durably advances the current sequence once, and retains strict stale/replay rejection. Actual Coordinator-derived Review, Confirmed and Complete fixtures exercise restart recovery. |
| P2: Orca current selection could be confused with the original job/result context | Separate current selection, immutable active-job original context and retained result original context. Profile switching cannot retarget a job or result. |
| P1: intent consumption and its durable outcome could be separated by a crash | Confirm outcome/consumption are atomic. Start persists its complete pending intent and consumption with `starting` before dispatch. Cancellation consumption/uncertain transition is likewise atomic. |
| P1: future physical qualification could overlook transitive start-macro behavior | Typed qualification binds exact machine/configuration and reviewed static transitive macro sources, arguments and independent safe bounds. Dynamic, unresolved or recursive macro closure fails closed. No operational qualification or deployment grant was made. |
| P1: crash after owned adapter dispatch could orphan the same job | Read-only recovery adopts only an exact durably owned post-dispatch job and never repeats upload or Start. Missing/ambiguous/pre-dispatch ownership remains locked. |

The reviewer independently ran the then-current 26 owned-job tests, 11 native
checks, four recovery cases, two real Coordinator/HTTP-fixture crash cases and
three companion checks. They passed. HTTP/job evidence is synthetic; it does not
qualify a physical printer. Source corrections do not replace exact target-native
UI captures or actual generator parity.

Later integrated deltas include nullable same-job monitoring, native product
review corrections, the stock YOLO recipe correction and actual native-engine
build/generation. Their bounded correction rechecks are recorded below. Runtime outcomes and
target-native evidence remain separate from a source-review verdict.

## Bounded final source rechecks

The same independent reviewer rechecked the integrated monitoring, compact
native result/Start states, companion readiness and corrected YOLO transform
through `f28187a`. No new material code defect was found. The actual R8 strict
parity pass independently supports the transform convention; hardware and
physical readiness remain false. Unsupported reviewer-model attribution was
removed and historical pre-R8 pending language was corrected.

A second bounded correction recheck through `f6198a7` covered actual NanoSVG
linkage, definition-created enum-aware retained config, private managed smoke
diagnostics, native auto-placement and direct-scroll evaluation controls. No
new material source defect was found. The reviewer ran 15 native UI checks and
nine engine/dependency checks successfully. Runtime configuration uses defaults
only to inventory required keys, never to supply a missing retained value.
Diagnostics expose phase/key names, not configuration values. Evaluation controls
retain the same completion-dependent visibility binding.

These are corrections within the one combined review. Actual engine runtime
outcomes, complete final native captures and any new interactive-review wrapper
remain separately identified qualification gates. The lead's combined suite
then passed 418 tests, with two Windows-only skips on Linux. Accepted Issue #2,
#8 and #12 source-bound offline evidence checks also passed unchanged.

## Qualification infrastructure and rejected-artifact corrections

A later P2 in the test-only Windows companion qualifier used optimization-
removable `assert` gates. It was replaced with explicit persistent validation,
exact marker/root identity and local path/source checks. Two optimized negative
tests and actual optimized Windows receipt readback/wrong-root rejection passed;
the same reviewer resolved the finding. Existing R8 proof and the original
driver remain retained rather than relabeled as hardened-source execution.

The native adapter now retains a mandatory false-parity disposition whenever
a rejected/failed process leaves actual G-code, and before successful-process
result validation. Rejected or invalid artifacts cannot become Prepared. The
reviewer independently passed 11 native-transport tests and the two optimized
qualifier tests. No new material finding remained in those corrections.

The new interactive viewer received bounded review before any listener launch.
Corrections cover lazy portable/pinned lifecycle loading, source closure for its
privacy validator, authoritative helper-root lookup, private first-launch state,
frame denial and conservative pointer release after lost replies. The final
independent correction recheck through `48b7e0c` found no remaining material
source defect and passed all 13 focused viewer tests plus `git diff --check`.
The integrated lead suite passed 434 tests with two Windows-only skips on Linux.
Actual viewer lifecycle/browser qualification remains a separate gate. These
changes affect review infrastructure, not the frozen native product/capture
source.
