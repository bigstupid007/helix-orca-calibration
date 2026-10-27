# V1 completion-amendment acceptance ledger

This ledger is controlled by the Founder amendment in Issue #14 comment
`6401570758`. It prevents implementation, qualification, deployment, and
Founder acceptance from being conflated. A row may be marked **PASS** only by
the named current evidence; preserved October 15 and Issue #12 records remain
historical unless the row explicitly names them.

The candidate started from draft PR #15 head
`63462643ed647acb52414a571a61aac8c0ce824a`. Product behavior is now frozen at
`2f1ffe1041b9f591d2c621e821975f53414efd65`. The build-level generator
qualification remains bound to product head `4c0379b05e9a58a7546b42da9fbcc09658fabba8`
and harness head `992577c15aac24ee7b23cf850c98f016c0ac73a4`; the later commits are bounded
companion, transport, runtime, and owned-job recovery corrections and do not
change the qualified generator or resource closure. PR #15 stays draft and unmerged, and
preserves the accepted Issue #12 physical Temperature installation, evidence,
profile fingerprint, and rollback material.

## Exact candidate identity

| Boundary | Required identity | Status |
| --- | --- | --- |
| Helix source | `v1.1.0-beta.12` / `00a9fe6030c37d56748b2122b41fd36de1fdf831`, all 14 recursive submodules pinned | **PASS** — exact source fallback built and ran with `--network none`; focused managed report `0da1cf01…956d` completed and cleaned up |
| Orca source | `b5e9cb3c5e7a925adf8379366ae580e4dabb1d03` | **PASS (source)** — checkout, mutable API ancestry, current serialization types, and final-slice integration are source-verified; exact Windows engine gate remains below |
| Official Windows Orca | artifact `12608613863`, archive `e38b26af…46c0`, executable `aab75b0b…761e` | **PASS** — bytes verified and actual SPARE 50-case qualification completed with exit 0 |
| Mutable preset API | ancestor `557feba64931d83908323933b73656ca697f6870` | Source verified; actual transaction acceptance pending |
| Integration identity | frozen product plus exact qualification and runtime receipts | **FROZEN PRODUCT** — `2f1ffe1041b9f591d2c621e821975f53414efd65`; **QUALIFICATION** — `4c0379b` product / `992577c` harness; **INSTALLED RUNTIME** — candidate `41dc24a7…109` |

## Product and engineering gates

| Gate | Required proof | Status |
| --- | --- | --- |
| All-five Helix configuration | Every current-Orca-valid Temperature, YOLO, PA Pattern, Retraction, and MVS parameter shape is representable; native invalid inputs remain blocked | **PASS (source/native)** — 26 focused beta.12 assertions and 39 frames cover all five surfaces; extreme-range harness proof is separately retained and is not core evidence |
| Current Orca final slice | Selected printer, process, originating filament slot, nozzle, bed, and effective machine G-code reach Orca's ordinary `Print.process` / `Print.export_gcode` path | **PASS** — actual Windows matrix completed 50/50 through the pinned final-slice path; qualification `66c8616c…9ee` |
| Build-level qualification | Representative all-five matrix covers defaults, non-default accepted ranges/steps, meaningful boundaries, Voron, and AD5X; runtime has no exact-request catalog gate | **PASS** — five calibrations × five parameter cases × two contexts; separate extreme-range diagnostic excluded from the representative core |
| Warning fidelity | Fatal/unknown findings block; `1000C001` follows the pinned Orca warning/continue path through an exact prepared-job acknowledgement | **PASS (Windows/build)** — request-bound warning receipts are retained in the 50-case qualification; physical beta.12 Continue was also observed without Start |
| Printer-neutral execution | Exact target/file binding, fit check, no-overwrite upload, idle/queue checks, Confirm, deliberate Start, history/completion, owned Cancel, and fail-closed recovery; no universal Voron macro ABI | **PARTIAL / PHYSICAL BLOCKED** — implementation and target/file checks pass; the only Start attempt rejected before upload and a later stale beta.12 session prevented a fresh request. No upload or print occurred; final independent review found no material stock-path dispatch defect |
| Official result transaction | Exact originating 1-based slot/preset; source-current setting mapping; atomic PA two-key commit; Orca dirty/unsaved; normal dialogs authoritative; failure retry and uncertain no-replay | **PARTIAL — implementation/synthetic host only** — all mappings and transaction invariants pass; no amended physical completion reached an actual pinned-Orca result transaction |
| Owner-local runtime | Manifest-bound per-user install, status/start/stop/restart, upgrade/rollback/uninstall; no service, account, public listener, firewall rule, or new credential | **PARTIAL / FROZEN STOPPED** — actual SPARE stop/rollback/install/start/status and final stop completed; restart/uninstall are implementation/test-reviewed, not exact-receipt validated. The package, journals and rollback remain preserved; zero physical actions |
| AD5X compatibility | Matching available Orca context generates/final-slices all five without Voron macro/model assumptions; no AD5X physical deployment | **PASS** — all 25 representative AD5X cases final-sliced in the actual Windows matrix; no physical adapter exists |
| Helix beta.12 evidence | Current runtime/API behavior, target layouts, queued dialogs, numeric/list editors, all-five workflows, recovery, and exact cleanup | **PARTIAL** — focused `480x272` presentation proof and earlier eleven-target capture are layout lineage; current protocol-source deltas pass tests and bounded beta.12 playback, but no all-files frozen-head screenshot matrix exists and actual navigation ended blocked |
| Windows acceptance | Official pinned portable runtime, current companion, multi-slot context, warnings, all mappings, dirty/Save behavior, profile preservation, install/rollback | **PARTIAL** — pinned runtime, context capture, build matrix, warning flow and the bounded lifecycle sequence pass. Restart/uninstall lack an exact SPARE receipt, and actual result application remains coupled to the incomplete physical chain; no Save was performed |
| Voron target acceptance | Exact live identity/configuration/fit qualification and deployment/rollback without firmware or configuration mutation | **PASS through pre-dispatch** — identity/configuration, beta.12 service, HelixPrint analysis, exact-file fit, deployment and rollback pass; independent readback proves no new upload/start after the rejected attempt |
| Five physical workflows | One controlled native-valid print per calibration: configure → final slice → prepared → Founder Start → exact completion → select → exact preset transaction → visible unsaved value | **BLOCKED WITH SPECIFIC EVIDENCE** — zero of five amended prints completed. Request `92fac…` prepared and was deliberately started, but readiness rejected it before upload; the bounded continuation then exposed a stale beta.12 session/navigation state and created no new request. Per Founder direction the product is frozen and no new repair loop is permitted |
| Specification fidelity | Independent source-to-Founder-playback trace with no extra manual relay, file recreation, value re-entry, or automatic Save | **BLOCKED / PARTIAL** — intended implementation contains no relay/re-entry/Save, but actual playback terminates at the documented product session/navigation blocker |
| Independent engineering review | Fresh combined review after implementation and evidence freeze; all material findings corrected and rechecked | **BLOCK overall; committed delta PASS** — [final review](V1_FINAL_INDEPENDENT_REVIEW.md) found no material code defect, corrected lifecycle/CI scope, and retains the frozen stale-session failure as the acceptance blocker |
| Product Preflight | Fresh evidence-first beta.12, Windows, install/recovery, and full-playback audit | **REVIEW COMPLETE / PRODUCT BLOCKED** — native and Windows/build/lifecycle evidence are coherent within declared scopes; actual playback failed in stale session/navigation. Compact touch/scroll, low-contrast text, dense PA copy, and unmeasured accessibility remain explicit limitations |
| Regression and CI | Full dependency-free suite, `git diff --check`, preserved historical evidence verifiers, and all exact-head PR checks | **LOCAL PASS / NEW CI PENDING** — 637 tests pass (7 host skips) and `git diff --check` passes. All four prior `992577c` checks, including Windows `40342726026`, passed; exact frozen-head checks are required after publication |
| Guided Founder Review | One concise current guide, exact entry points, expected observations, limits, rollback, and only unavoidable owner actions | [Current guide prepared](V1_FOUNDER_REVIEW_CURRENT.md); it is a mature evidence/blocker review, not an instruction to repeat the failed physical flow |

## Physical authority and stop boundary

The amendment authorizes the minimum controlled five-calibration execution and
bounded correction reruns only after all non-consequential gates pass. The
automation may prepare, deploy, monitor, verify, apply, and roll back. It may
never synthesize the Founder’s deliberate Helix **Start** tap, automatically
save an Orca preset, change firmware/printer configuration, enqueue unrelated
work, or expose a public listener.

If access to SPARE or the Founder’s Voron requires an owner-only action, the
review package must first be complete enough that the action is a single short
instruction rather than a technical procedure. An unavailable host is not a
reason to relabel an implementation or evidence gap as accepted.
