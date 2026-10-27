# V1 AI Product Preflight

> **Product Preflight review complete; product blocked:** the candidate is
> frozen at focused stale-session repair
> `f85936f002517640b20854ee36b30a7c6ca952f8`. The current beta.12 native
> evidence-first review is complete; build qualification, owner-runtime and
> controlled physical observations are recorded here when their bounded runs
> complete.  Earlier beta.9/October 15 sections remain history, not current
> evidence. [Amendment record](V1_CURRENT_UPSTREAM_REBASE.md).

The current native Product Preflight uses the focused
`480x272` proof and sixteen deliberately selected state frames. All 28 captured
source digests match capture candidate `cb46647`, and 26 of 28 remain unchanged
at the frozen head; 26 workflow assertions and 39 frames
pass, with HelixScreen beta.12 source-built at the exact pin, Docker network
`none`, zero physical actions, and complete managed cleanup. The inspected
states cover entry, chooser, all five configuration surfaces, prepared review,
Confirm, deliberate Start, monitoring, evaluation, applied/unsaved, application
failure, known warning, cancellation confirmation, and terminal cancellation.

The frames are independent fixtures rather than a chronological job. Their
values may differ across states; exact-job continuity must come from Windows
and physical receipts. Within the focused screenshots, the UI is coherent and
contains no screenshot-level blocker. Primary and safety actions are clear, warning Continue explicitly does
not start a print, and APPLIED / UNSAVED is prominent. Remaining risks are small
low-contrast secondary text, vertical-scroll discoverability, dense Pressure
Advance labels, compact touch targets, and unmeasured keyboard, focus,
assistive-technology, zoom, motor, and contrast behavior.

The `f838503`, `cb46647`, and `4c0379b` corrections leave the captured 28-file
inventory unchanged, and `992577c` changes only the qualification harness.
Later capability-refresh, machine-binding, and warning-recovery work changes
protocol validation/recovery lines in `integration/v1-native/main.lua` and
`integration/v1_runtime.py`, so the focused frames are presentation/layout
lineage rather than byte-current proof. Current source
tests and actual bounded beta.12 playback cover those protocol deltas and show
the same visible chooser/configuration/warning/review/Confirm/Start surfaces.

The older eleven-size beta.12 run is retained only as layout lineage because
four subsequently corrected source digests differ. The extreme-range proof is
separate harness diagnostic evidence. The current Windows GUI capture stopped
before product interaction because capture ownership reported `Capture is
occluded.` Per Founder instruction it was preserved, not retried or treated as
a product failure. See the [focused beta.12 evidence and exact limits](evidence/issue-14/amendment/native-beta12-focused/README.md)
and [sanitized capture diagnostic](evidence/issue-14/amendment/windows-gui-diagnostic.json).

The first bounded Founder/Voron continuation returned from Request generation
to the chooser while beta.12 still presented the retired uncertain request as
active. Readback found a healthy idle coordinator with no current request and
no new prepared job; Moonraker was ready with no active virtual-SD file and no
new owned upload. This is retained as a
[stale-session/navigation diagnostic](evidence/issue-14/amendment/physical-stale-session-navigation-diagnostic.json).
The October 27 continuation repaired and narrowly proved that exact retired
session reconciliation without replay. A fresh Temperature request then
prepared the exact 225→215 °C artifact and known warning, after which the real
beta.12 Request-generation tap crashed HelixScreen with signal 4 before Confirm
or Start. This separate actual product/runtime failure is the current Product
Preflight blocker. Independent readback proves no upload, dispatch, print, or
motion occurred. The coordinator is stopped and the product is frozen. See the
[focused correction and SIGILL record](evidence/issue-14/amendment/physical-stale-session-reconciliation-sigill.json).

The following visual audit, 396-frame matrix and earlier synthetic browser
workflow are historical, tied to their exact source snapshots. They do not
qualify the amended controls or current result transaction.

## Historical visual review and corrections

A fresh-context independent Codex reviewer inspected this program's
newly captured native beta.9 screens using the Product Design audit workflow.
The reviewer did not read implementation, design rationale or older captures.
The initial Helix audit covered all 31 fresh `480x272` workflow frames in the
private `v1-native/review-recovery-matrix/micro_480x272` capture. The initial Windows
audit inspected the actual isolated October 15 R6 companion screenshot, SHA-256
`41446ade94b7a76531c5fd0d2790090c51145072c30f4315ac7102c479f06cc9`.
Windows screenshots contain original profile names and remain private.

| Observed issue | Integrated correction | Verification |
| --- | --- | --- |
| Unsupported arrow glyph in compact Helix labels | Font-safe “to” labels | Fresh smallest/portrait captures passed and reviewed |
| Cancelled state still offered evaluation | Terminal outcome hides evaluation | Fresh cancellation frame passed and reviewed |
| Returned result remained an unfinished scrolled job view | Deliberate Return/manual reopen presents compact Returned / NOT APPLIED / Done overlay; ACK only updates state | Fresh returned frames reviewed; native navigation assertions passed |
| Destructive cancellation matched ordinary blue buttons | Danger cancellation and secondary Keep printing styling | Fresh smallest view passed and reviewed |
| Monitoring showed weak feedback and unconditional printing-unavailable copy | Independently nullable elapsed/progress; missing values explicit; redundant unavailable copy removed | All eleven targets passed populated/missing/invalid checks and 100%-progress evaluation lock |
| No explicit Start screen in the captured set | Five Confirmed frames added, one per calibration | Complete 36-frame × eleven-size matrix passed |
| Orca heading said “Ready at the printer” while status said “Waiting for Helix” | Heading and badge now follow the same phase; waiting/blocked use attention styling | Fresh actual Windows R7 recheck passed |
| “Refresh profiles” could imply preset mutation | “Refresh selection” names its read-only effect | Fresh actual Windows R7 recheck passed |
| Retained health could sound like a live response | “Last reported running” / “stopped” wording | Actual Windows lifecycle passed; current-source native waiting view reviewed |

The portrait test also exposed a test-seed grid-stamp mismatch before this final
capture: an inherited landscape grid caused Helix to reproject the logical 1×1
tile on portrait. The V1-only seed now omits that stamp and retains strict actual
child-bounds, overlap and logical-size assertions. The failed managed capture is
retained privately; no incomplete evidence was promoted.

The initial review called for attention. Small tertiary text, scrolling and
contrast at Windows scaling remain review considerations. Screenshot inspection
does not establish screen-reader, keyboard, motor-accessibility or full contrast
compliance. The waiting-only Windows frame proves neither active-job/result
behavior nor lifecycle startup. Those need separately identified evidence. All
native mock job states are explicit synthetic fixtures with physical execution
disabled; they are not real print or parity evidence.

## Bounded fresh Windows correction recheck

The same cold reviewer inspected the fresh R7 waiting frame at original
resolution. All three earlier waiting concerns were resolved: consistent Waiting
for Helix heading/status, amber treatment with explicit state text, and Refresh
selection wording. The waiting state was judged healthy within the still-image
evidence boundary.

The reviewer then inspected three fresh R8 native frames: actual production
preparation, a real isolated current-process switch with the original job context
retained, and explicitly synthetic NOT APPLIED result return. The visible state
model was judged healthy and coherent. The next action is clear, current and
original profiles are separately named, and result origin/NOT APPLIED remain
prominent. No physical completion or Confirm/Start claim was inferred.

Remaining medium opportunities: flag changed current rows explicitly rather
than requiring manual comparison of similar names; keep the synthetic fixture
qualification visible when presenting result evidence (use full frames). Narrow
dock content needs vertical scrolling. Exact contrast, keyboard/screen-reader
behavior, Windows scaling/high contrast and focus/scroll order remain unverified.
Screenshots and profile identifiers remain private; their hashes and bounded
workflow observations are recorded in the Windows inventory. The historical
corrected Helix matrix passed 396 frames across all eleven targets, including that candidate's smallest-layout scrolling correction.

## Fresh compact Helix correction recheck

The fresh `480x272` smoke passed all 36 frames and native lifecycle assertions
at source digest `e5dc3aff82501ed6f507d00e3bb34b692187c971b37a4173a13a0afdad81820a`.
The cold reviewer inspected all 36 frames: font-safe ranges, separate Confirmed
Start, progress/elapsed feedback, completion-only evaluation, compact result /
NOT APPLIED / Done, destructive cancellation and cancelled-state evaluation
removal all resolved the initial findings. Vertical scrolling remains necessary
for some configuration/evaluation content; native reachability was exercised.

The separate fresh `272x480` portrait smoke also passed all 36 frames. A bounded
cold check of Home, Chooser, Temperature Confirmed/Monitor/Returned, Flow
Returned, cancellation confirmation and Cancelled found a healthy visible flow.
Strict logical 1×1/child bounds passed in both orientations. Two apparent header
clipping reports were preview-rendering artifacts: SHA-bound original saved PNG
inspection by the lead and isolated rechecks showed complete headers/back
controls, and the reviewer fully retracted both. No speculative product change
was made. Full-frame original evidence is authoritative.

The historical complete corrected matrix is retained beneath
`docs/evidence/issue-14/native` and verifies against all eleven original private
ManagedRun records. The lead also inspected the saved phone PA Confirmed and
tall Flow Returned frames at original resolution. These bounded visual checks
do not claim independent visual inspection of every matrix frame.

Small low-emphasis metadata and scroll discoverability remain limitations;
keyboard, screen reader, contrast and motor accessibility are not qualified by
these stills. That candidate's complete eleven-size capture and synthetic browser interaction
qualification passed; these checks remain distinct from the cold visual
review scope above. No physical lifecycle or generation qualification is
inferred from the synthetic native flows.


## Historical browser review and exact cleanup

A fresh isolated Chromium 140 browser (Playwright 1.64.1) exercised actual native
pointer controls through Generate, Confirm, distinct Start, simulated completion,
Return result, NOT APPLIED receipt, Done, Home and Back. Native Returned was
asserted and each saved image awaited a fresh frame; all nine full browser frames
retain explicit synthetic/no-printer labeling. There were no page errors or owned browser
processes left. Live Host/Origin/token/command/coordinate refusals passed, followed
by nonce-bound graceful stop, listener closure and exact ManagedRun cleanup.
This lead-operated interaction check is separate from the independent cold
screenshot review and does not qualify accessibility or physical behavior.


## Current functional correction gate

Implemented numeric controls, both fixed YOLO modes and explicit PA defaults pass
focused source/build checks and independent actual800×480 native operator input.
All five selected requests match actual Windows transport/journal readback; Flow
reaches genuine qualified Review with mode-specific parity. All14 healthy frames,
current source closure and exact owned resource cleanup pass. Independent visual
inspection of these functional captures found no material issue; this is a focused
operability check, not a new Product Design audit. No new accessibility, physical
printing or broader visual design qualification is inferred.
