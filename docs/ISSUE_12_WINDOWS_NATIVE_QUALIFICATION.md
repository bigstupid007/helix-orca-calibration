# Issue #12 Windows native miniature qualification

Status: **PASS — corrected native export and actual Windows companion round trip.**

This is the preserved pre-physical readiness qualification. Current Founder
acceptance of the final actual print/automatic chooser/NOT APPLIED return and
the governed closeout are recorded in [Issue #12 acceptance](ISSUE_12_ACCEPTANCE.md). The subsequent
Founder-initiated physical calibration also succeeded and returned actual
220°C NOT APPLIED; [its separate evidence](evidence/issue-12/physical-first/README.md)
is not synthetic Windows/mock proof. The later compact-widget build changes no
Windows companion, normal profiles or physical installation. Restoration facts
below describe the earlier readiness session, before separately authorized
physical staging of the reviewed baseline.

Preferred October 15 nightly `6a7763f08d1a175a464a00ce13f0b5a815662fc4`
ran on Spare through its existing unelevated worker, with the marked isolated
datadir. No normal Orca environment or physical printer was used for execution.
Raw G-code, frames, target configuration and payloads remain private.

## Native preparation and exact output

Orca Calibration → Temperature prepared exactly **225/220/215°C bottom to top**
with the native 5°C step and bundled tower. Native uniform Scale 70% yielded
31.15 × 7 × 21 mm; native 0.28 mm layers, Slice Plate and Export produced
`temperature-miniature-225-215-step5-uniform70-oct15.gcode`:

- **484,552 bytes**, SHA-256 `83fd38e22aca7237c1b8c9fa8a8971657f72b47d344a06f42120c78d05503074`.
- **75 layers**, highest extrusion Z20.92 mm; exported motion Z0.20–21.32 mm.
- 225°C extrusion Z0.20–6.92; 220°C Z7.20–13.92; 215°C Z14.20–20.92.
- Native normal-mode estimate **12m00s**, including model 11m58s. Macro overhead is excluded; this estimate is information, with no duration or combined-time gate.

The only temporary machine-start edit was Orca's in-memory template:

```gcode
PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]
```

The exact export resolves it to `PRINT_START BED_TEMP=60 EXTRUDER_TEMP=225`.
No custom generator or exported-file edit was used. Native New Project → No
save → Discard restored the original 0.20 mm process and 220°C context.

## Offline suitability and preserved safeguards

GET-only refresh matches the reviewed identity/configuration/Moonraker version,
standby and empty queue. All 17 exported commands are registered; object
definition precedes PRINT_START. The 0.4 mm nozzle and X/Y 0–300, Z −5–290 mm
limits cover exported motion, reviewed adaptive purge and end parking.
Exported acceleration never exceeds the existing 8000 mm/s² limit.

Unchanged macro dependencies retain cold/warm motor, homing and QGL guards,
probe-temperature handling, saved 60°C mesh, target-temperature wait, adaptive
purge, guarded end parking and heater shutdown. Offline qualification binds
these sources/configuration and exact file bytes; it passes without any grant
or action-enabled adapter. The inspection JSON's `physical_ready: false` means
the standalone byte inspector cannot resolve printer macros or authorize
hardware; the separate suitability review resolves those dependencies.
Founder-confirmed material and approved bands supply the material basis; no
additional spool-label verification was introduced.

## Actual Windows and isolated native return

Reviewed generated companion **0.6.1**, SHA-256
`30a5a51539e432513181d04966d09196d93057d085ba5d918ea77a262164c86b`,
was installed only in the isolated nightly. Native plugin-manager version,
Keep original, exact-file chooser and Send were observed. Saved, edited and
effective original temperatures each remained **220°C**. The real Windows
outbox drove the isolated beta.9 native UI; its exact persisted 220°C selection
was relayed to the originating companion. Only that companion's committed
receipt allowed native acknowledgement and Returned. Windows displayed the
original profile/setting, original 220°C values, selected 220°C and **NOT APPLIED**.

Job `000001`, authorization, status/history, completion digest and clock inputs
were **synthetic** in Docker network-none isolation. This proves software return
and correlation, never physical calibration or measured temperature quality.
The single-target Windows integration is additional to the separate complete
11-target/88-frame native capture. Private export qualification is reproducible
from retained bytes and GET inputs; independent review reproduced its outputs
idempotently, rather than treating their mtimes as an original capture.

## Preservation and later physical execution

The candidate source hash was verified on Windows before restoration. Accepted
0.5.0 (`bc3d35eb260a1360e1095bd97d8e7d31e3ab96e8b3cafde1f145e3adf5b4d71f`)
is restored, with the isolated Orca process closed. Candidate artifacts are
archived privately. All **five accepted communication files**, **12 saved user
profile JSON files**, and **1,429 normal profile/configuration files** match
their preserved hashes. Normal aggregate SHA-256 remains
`41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`.
Temporary UI preferences are not claimed byte-identical. No profile writeback,
physical upload, queue, print, heat, motion, macro or firmware change occurred.

The consumed mock request and synthetic completion cannot authorize a physical
test. A later separately authorized test uses a fresh original request, current
identity/configuration qualification and explicit native Start through the
existing safeguards. No live permit, physical derivative install or activation
had occurred at that readiness capture. The later deployment, physical tests
and Founder-authorized merge supersede that historical restriction; the
qualification artifacts and their original proof boundary remain unchanged.

Earlier 210/205/200°C and 0.6.0 evidence remains
[superseded history](evidence/issue-12/history/README.md).
