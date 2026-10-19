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
The actual browser/native workflow, live refusal checks and exact graceful
teardown now pass; their synchronized nine-frame proof is separate from source
review. These changes affect review infrastructure, not the frozen native
product/capture source.


## Final native-engine correction rechecks

The independent reviewer found no material issue in `0262ab4`: the explicit
two-thread task arena aligns Orca's thread-name/locale barrier count with the
retained global cap, preserving exception/result lifetime and export validation.
The actual targeted run clears the wait and exports PA; native warning `1000C001`
then correctly blocks Prepared, with mandatory false parity retained.

The lead's receipt audit found two missing fidelity hunks between worker and
integration C++ bytes. Source-only `e500374` restores pinned native retraction
float semantics and PA bed-relative primitive/initial placement. The independent
reviewer checked both against pinned GUI/Plater source and found no material
issue. All five owned native build inputs now exactly match the successful
actual build receipt; no prior differing integration bytes are relabeled built.
The complete native UI 396 matrix remains unchanged by these engine-only deltas.


Exact-head CI caught one unit check reading the devbox's cached runtime settings
template. The check now supplies its own isolated upstream template while
exercising the real seed transformation. All geometry/style assertions remain;
no runtime/product/capture source changed, and the complete native evidence
still verifies. The failed CI run is retained rather than relabeled successful.

## Functional parameter correction: final independent acceptance

The independent reviewer passes the integrated correction through
`54387c4de4a8f5930f54cb4aa5d441721067142c`, plus the final focused verifier,
evidence and reconciled documentation. No material source, contract, safety,
fidelity, privacy, evidence or current-documentation finding remains. This is a
bounded correction recheck within the one combined review, not a new design audit.

The reviewer independently operated the actual800×480 native UI through the LAN
browser: pointer, drag, native keypad, Set, both PA defaults, invalid Retraction
rejection and changed values for every required field/mode. Native requests,
actual Windows DirectoryEvents input and independently reread Coordinator journals
match exactly for all five calibrations. Four actual blockers dispatch no generator
or artifact. Perfectionist genuinely generates and passes unchanged strict native
parity, reaches Review, and retains exact parameters. All14 fresh frames/101 actions
pass, with zero navigation/read retries or page errors and no owned browser left.

Managed run `b04728721c2741bd8d05b3001a343cdf` completes with exit0, runtime clear
and no verification errors. Operator report SHA is
`f39b272a459bc309fb3cb34cab9e5cd1aa6bf2fa2b7efce1e80e59182ba85449`;
promoted report SHA is
`a0386c8cb0edb96976e8e3ec411980ed9dd506052103a66de46730ee5775ece2`.
The reviewer independently passes the portable verifier and inspects all14 private
frames. Public records contain controlled scalar metadata/hashes, without frames,
profile labels, local paths, full saved state or geometry. The review-only2GiB
aggregate shared-filesystem-loss limit retains5GiB reserve,512MiB margin and all
container/network/ownership controls; the pinned helper's exact excess boundary
was checked. Earlier failed/incomplete runs remain private and unpromoted.

The [focused proof](evidence/issue-14/parameters/README.md) controls this verdict.
Historical396-frame evidence stays historical. Temperature still lacks matching
qualified geometry/native parity. PA retains warning1000C001 and compatible audited
Windows engine/exact-parity gaps. Retraction/MVS retain the same Windows packaging
and native-parity gaps; they were not rerun past the shared engine blocker. This
proof presses no Confirm/Start/Cancel and makes no completion/evaluation, hardware
ABI, physical-readiness, deployment, profile-writeback or public-network claim.
Required exact-head GitHub CI is reported separately on draft PR #15. Founder
acceptance and merge remain pending.

## Generator-only correction review

The same independent reviewer performed a substantial generator/build review
through `02b9676ea8f19e49b36b7cd69f02cba0166b2fa4`. The review covered the
retained parameter-proof boundary, native C++ calibration fidelity, managed
Temperature geometry provenance, the Windows build/package path, warning
handling, independent native-reference registration and the four-route native
qualification driver. The native UI/control, request, Coordinator and transport
sources protected by the parameter-preservation gate remain byte-identical to
the accepted proof snapshot. Historical blocker statuses are not promoted into
current generator evidence.

The review found three material provenance defects. The Windows Temperature
helper originally imported owned modules before authenticating its reviewed
source closure. It now admits only an exact external manifest/inventory, compiles
captured verified bytes through a closed loader, rejects bytecode and linked or
reparse paths, and rechecks source after generation and sanitization and before
publication. The Windows source-material archive originally copied dependency
downloads without rehashing the bytes placed in the ZIP. It now requires every
nonexcluded locked direct, transitive and supplemental source digest exactly
once, inventories sizes and hashes, rehashes the same stream written to an
unpromoted ZIP and promotes atomically. A follow-up found that an unrecognized
download could still be omitted without making the source-material status
incomplete; `02b9676` now rejects every such file. Explicitly named binary-only
downloads remain excluded and disclosed. The reviewer rechecked all three
corrections and found no remaining material source defect at this head.

The native import, placement and Cut path matches the pinned GUI ordering. A
fresh closure-bound managed run independently reproduced the earlier Temperature
STL byte-for-byte, while retaining separate raw receipt/request hashes and
explicit nonce/path normalization. This is geometry reproducibility only; it is
not native executable parity and does not retroactively add provenance to the
earlier run. The protected Temperature transfer bundle remains unchanged and
requires its own explicit transfer authorization.

The Windows package keeps PE/import/resource/source checks fail closed. Actual
build attempts exposed and retained three portability failures before any
qualification: command-shell quoting, CRLF source checkout and backslashes in
generated CMake cache values. Their bounded corrections use an owned command
file, exact LF source-byte audit and forward-slash cache paths. Source materials
retain locked upstream GMP/MPFR versions but explicitly do not claim reproduction
of the historical vendor compiler, flags or patches. Windows OpenCV IPP-ICV and
excluded binary-only inputs remain disclosed production source-acceptance limits;
`complete_corresponding_source_claim` and physical readiness remain false.

The generic Windows qualification helper invokes the actual receipt-validated
Windows backend and generator for PA Pattern, Retraction, Max Volumetric Speed
and native Temperature. Native-reference registration cannot invoke or qualify
the package and records `qualified:false` and `prepared:false`. Qualification
requires exact context/parameters, a separately pinned native UI manifest,
candidate/reference path separation, matching input/source/runtime provenance,
receipt-bound DLL and resource closure, and a successful recomputation by the
unchanged strict parity verifier. Every native warning or processor error remains
fatal; fixed public codes and reasons are separated from retained private
diagnostics. Screenshots and registration ordering remain operator evidence and
must be inspected with the target run; PNG structure alone does not prove GUI
causality.

The deliberate unsaved 50°C bed case is a separate effective context. It may
qualify only with fresh visible edited-versus-saved evidence, exact native and
candidate binding, proof that the preset was not written back and restoration of
the original selection. It does not rewrite or qualify the retained 60°C bed /
55°C vitrification rejection. No Confirm, Start, physical adapter, deployment,
profile writeback or public-network operation is included in this source verdict.
The reviewer did not run a Windows build, target executable or heavy native job.
An actual successful Windows package receipt and calibration-specific target
results remain mandatory before this generator correction can be accepted.
