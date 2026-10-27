# Issue #14 completion-amendment evidence

This directory contains the bounded public evidence for the Founder's
2026-10-25 completion amendment. The frozen candidate is
`2f1ffe1041b9f591d2c621e821975f53414efd65`. Its actual Windows build-level
qualification is bound to product source `4c0379b05e9a58a7546b42da9fbcc09658fabba8`
and harness head `992577c15aac24ee7b23cf850c98f016c0ac73a4`; later commits are bounded
companion, transport, runtime, and owned-job recovery corrections. PR #15
remains draft and unmerged.

## Core candidate evidence

- `native-beta12-focused/` is the HelixScreen beta.12 focused presentation proof
  and Product Preflight selection. Its 28-file inventory matches capture head
  `cb46647`; 26 files remain unchanged at the frozen head, while two later
  protocol/runtime files differ. It is presentation lineage, not byte-current
  full-source proof. The frames are independent deterministic fixtures, not one
  chronological job.
- `voron-preflight.json` is a sanitized read-only target snapshot. It records
  no action, print, configuration change, or physical qualification.
- `windows-build.json` binds the successful source-pinned Windows build at
  `60dbbad` and downloaded package/source archive digests. The later
  qualification reuses that verified build/resource closure; this record is
  not an exact-frozen-head build claim.
- `windows-build-qualification.json` binds the completed actual-Windows 50-case
  matrix for all five calibrations, five parameter cases, and both Voron and
  AD5X contexts through pinned Orca's ordinary final-slice path.
- `windows-runtime-lifecycle.json` binds the final owner-local package's
  stop/rollback/install/start/status sequence and final freeze stop, healthy
  action-enabled process, retained rollback, and preserved retired-request
  history. Restart/uninstall are outside this exact receipt. It records zero
  physical actions.

## Deliberately separated diagnostics

- `windows-gui-diagnostic.json` records that the bounded current-Orca capture
  stopped before product interaction with `Capture is occluded.` It is capture
  ownership/timing evidence, not a product assertion, and it was not retried.
- `windows-companion-ui-thread-process-exit-diagnostic.json` records the
  bounded companion UI-thread/process-exit failure that preceded the corrected
  recovery path. It is diagnostic evidence, not candidate acceptance.
- `windows-qualification-diagnostic.json` records the actual MVS lower-boundary
  assertion at the prior `60dbbad` head. The failed run was preserved and not
  retried at that head; its pinned-source parity correction is `f838503`.
- `windows-qualification-ad5x-validation-diagnostic.json` records the actual
  AD5X Temperature validation assertion at the prior `f838503` head. The failed
  run was preserved and not retried at that head; its pinned-source warning
  parity correction is `cb46647`.
- `windows-qualification-ad5x-flow-context-diagnostic.json` records pinned
  Orca's genuine multi-object/Spiral-vase block for one preserved AD5X owner
  process. The product did not override that saved process. Representative
  qualification instead uses another already-preserved AD5X process whose
  effective Spiral-vase setting is off.
- `windows-qualification-ad5x-mvs-extreme-diagnostic.json` records pinned
  Orca's genuine build-volume block for the approximately 1001 mm extreme MVS
  request. Per the Founder direction, that exact request is preserved as
  separate harness proof and is not a core candidate cell; `992577c` changes
  only the representative qualification boundary.
- `physical-stale-session-navigation-diagnostic.json` records the bounded
  Founder/Voron attempt in which beta.12 returned to the chooser and continued
  to present a retired uncertain session while the healthy idle coordinator
  held no request. Independent Moonraker readback proves that no new owned file
  was uploaded or started. This is a real product session/navigation failure,
  while not being evidence of generation, slicing, upload, dispatch, or print
  failure. Per Founder direction it is preserved and not retried in another
  repair loop.
- The complete earlier eleven-target beta.12 capture remains private layout
  lineage because four subsequently corrected product-source hashes differ.
- The extreme-range native report remains private harness diagnostic evidence
  at SHA-256
  `4ec9882a89df40d9ccd2b43b9d254acb723a3fdff9d29340c54aac9421ee0231`.
  It is not part of the core candidate.

Controlled physical receipts are added only when their exact gates complete.
No pending gate is implied by this directory's presence.
