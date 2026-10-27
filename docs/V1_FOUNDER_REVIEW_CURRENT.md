# Integrated V1 Founder Review — current amendment candidate

This is the current review guide for the Founder's 2026-10-25 completion
amendment in Issue #14. Draft PR #15 remains draft and unmerged. The candidate
is frozen at `2f1ffe1041b9f591d2c621e821975f53414efd65`. Its build-level
qualification remains bound to `4c0379b` product bytes and the `992577c`
representative harness; later commits are bounded companion, transport,
runtime, and owned-job recovery corrections.

**Current disposition:** automated tests and the Windows 50-case matrix pass.
The owner-local lifecycle receipt is partial: stop/rollback/install/start/status
and final freeze stop passed, while restart/uninstall are implementation/test
reviewed only. The amended physical sequence is incomplete and
blocked by a preserved beta.12 stale-session/navigation failure after the first
deliberate Start was proven to have stopped before upload. Per Founder direction,
the product is frozen and that path is not being repaired or retried. This guide
is the mature evidence/blocker review candidate; **do not start another physical
calibration from it**.

**Founder action now: none. Do not interact with the Orca Calibration tile.**
The owner-local coordinator on SPARE is stopped and frozen; its installed
candidate, journals, authorization, and rollback material remain preserved.

## What is pinned and preserved

- HelixScreen is `v1.1.0-beta.12` at
  `00a9fe6030c37d56748b2122b41fd36de1fdf831` with fourteen recursive
  submodules pinned.
- OrcaSlicer is the nightly at
  `b5e9cb3c5e7a925adf8379366ae580e4dabb1d03`.
- The accepted Issue #12 physical Temperature implementation, evidence,
  installed state, and rollback material remain preserved.
- Orca owns the originating filament-preset transaction. The result is visible
  as modified and unsaved; this workflow never presses Save.
- The coordinator is an ordinary owner-local per-user process. It creates no
  service, startup task, public listener, firewall rule, account, or credential.
- AD5X is compatibility-only. Its preserved owner-profile context is qualified
  without configuring AD5X in the isolated physical Orca datadir and without
  allowing an AD5X physical adapter.

## Intended product flow — retained for evidence review, not executable

The intended flow opens **Orca Calibration** from the Helix home tile. The chooser must show the
current printer, process, originating filament preset, and explicit 1-based
slot. If this candidate had completed acceptance, one calibration at a time
would have proceeded as follows. Do not execute these steps now:

1. Choose the named calibration and verify the prepared values below.
2. Request preparation. This generates and final-slices through pinned Orca;
   it does not start the printer.
3. If Orca reports the known request-bound warning, read it and press
   **Continue** only when the exact warning is acceptable. Continue still does
   not start the printer. Any unknown warning or fatal error remains blocked.
4. On **Review your print**, check the printer, originating filament slot and
   values, then press **Confirm prepared job**.
5. When the screen says **Ready to start**, deliberately press **Start**. This
   is the only print-dispatch action and is never synthesized by an agent,
   receipt, recovery path, or timeout.
6. Wait for the exact owned job to reach completion. Do not start another
   calibration while a job or result is unresolved.
7. At **Which result is best?**, select the observed printed sample and press
   **Use in Orca**.
8. Verify **APPLIED · UNSAVED**, the originating preset/slot, and the returned
   value. Review the modified preset in Orca, but do not Save it during this
   controlled sequence. Press **Done** before proceeding.

If the transaction reports failure, leave the result pending and use the
visible **Retry in Orca** action only after reading the message. If it reports
an uncertain state, stop; do not replay Start or the preset transaction.

## Controlled five-calibration sequence

The table below is the accepted target sequence, retained for review. It is not
a request to execute it on this frozen candidate: zero of the five amended jobs
completed, and no additional repair/retry loop is permitted for the recorded
stale-session/navigation failure.

Use the order and values below. These are the controlled physical-validation
jobs, not a general recommendation for every filament.

| Order | Helix choice | Prepared values | Founder observations |
| --- | --- | --- | --- |
| 1 | Temperature · Standard tower | 225 → 215 °C, fixed 5 °C step, scale on | Press Start; after completion choose the best printed temperature and verify `nozzle_temperature` is modified/unsaved in the originating slot. |
| 2 | Flow Ratio · YOLO | Recommended, Archimedean Chords | Press Start; choose the best labeled sample and verify `filament_flow_ratio` is modified/unsaved in the originating slot. |
| 3 | Pressure Advance · Pattern | 0 → 0.02, step 0.005 | Press Start; choose the best printed value and verify one atomic unsaved transaction sets `enable_pressure_advance = "1"` and `pressure_advance`. |
| 4 | Retraction · Tower | 0 → 1 mm, step 0.2 mm | Press Start; choose the best printed value and verify `filament_retraction_length` is modified/unsaved in the originating slot. |
| 5 | Max Volumetric Speed · Tower | 5 → 10 mm³/s, step 1 mm³/s | Press Start; choose the best printed value and verify `filament_max_volumetric_speed` is modified/unsaved in the originating slot. |

Each Start and each observed-result selection is an owner judgment. The product
handles source/build qualification, context capture, generation, upload,
readback, fit, idle/queue checks, monitoring, exact result routing, and preset
targeting. The Founder is not asked to choose a qualification fixture, edit a
profile for the harness, copy files, run commands, re-enter generated values,
or diagnose transport.

## Completion signals

A calibration is complete only when all of the following are visible or
recorded for the same request:

- the prepared artifact and final slice are bound to the exact current context;
- Confirm and Start are separate, with one owner Start and no replay;
- the exact uploaded file completes successfully on the Founder's Voron;
- the selected result returns to the immutable originating preset and slot;
- Orca reports the official transaction as applied and unsaved;
- the pre-transaction saved profile remains unchanged until the Founder later
  chooses whether to save outside this validation sequence.

## Recovery and rollback

- Before Start, Back or a native cancellation leaves the printer untouched.
- During a running owned job, **Cancel print** may cancel only that exact job.
- A connection or restart ambiguity fails closed; never press Start again to
  “see whether it worked.”
- Owner-runtime rollback restores the complete prior code/configuration/
  authorization tuple. Uninstall removes versioned runtime files while leaving
  retained journals and evidence available for review.
- The accepted Temperature baseline remains the recovery point. No firmware,
  Moonraker, Klipper, printer macro, saved Orca preset, or normal Orca
  installation is replaced by this review.

## Evidence boundary

The beta.12 screenshots are independent deterministic fixtures, not a single
chronological job, so values can differ between those frames. Exact-job
continuity is established only by Windows qualification and physical receipts.
The occluded Windows GUI capture is retained as capture-ownership evidence and
was not retried. The approximately 1001 mm MVS request is retained separately
as extreme-range native build-volume evidence and is not a representative core
matrix cell. Neither diagnostic is treated as a product-navigation failure or
as permission to alter the frozen product.

The physical continuation is separately retained at
`docs/evidence/issue-14/amendment/physical-stale-session-navigation-diagnostic.json`.
It proves the coordinator was healthy and held no new request while beta.12
continued to present the retired uncertain request as active. Independent
Moonraker readback found no active virtual-SD file, no new owned upload, and no
new print. This is the specific acceptance blocker; it is not relabeled as a
successful five-calibration playback.
