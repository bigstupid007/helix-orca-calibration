# Orca nightly qualification gate

## Status

Source qualification is complete; Windows x64 runtime qualification is still
pending. Do not begin the Temperature round-trip implementation until every
required observation below has been captured from the fixed Windows build.
Linux execution, Wine, source inspection, or a headless Windows CI process is
not a substitute for this interactive target-runtime check.

This gate qualifies the existing read-only Orca context plugin and the host
surfaces needed by Issue #4. Passing it does not authorize the round-trip
implementation by itself; it satisfies the explicit first gate in the approved
Issue #4 work item.

## Fixed target

| Item | Pin |
| --- | --- |
| Upstream workflow | `Build all` scheduled run `38106132250` on 2026-10-11 |
| Source commit | `210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3` |
| Artifact | `11690627983` / `OrcaSlicer_Windows_V2.5.0-dev_x64_portable` |
| GitHub artifact digest | `sha256:080b00bc001256fd521a663e2939004d09a14f9bdef08c351167580e0d505d13` |
| `orca-slicer.exe` | `8d9db0bec8b8a8e0ad0a70485daaf7ee9fa1c88d5f1395f92eabf0430ce0339b` |
| `OrcaSlicer.dll` | `5b71e5dbf2f6b3319d6d69f597e3aa3dbf9403f9ea63f93c3c72dc294efba0a4` |

The artifact expires on 2026-12-10. Download it while authenticated from the
[upstream workflow run](https://github.com/SoftFever/OrcaSlicer/actions/runs/38106132250)
and extract it to a separate test directory. Do not replace or update the
normal Orca installation.

## What source inspection established

The exact source commit exposes all of the candidate surfaces:

- `orca.host.app_info()` returns the Orca version and build commit;
- `orca.host.ui.create_dock_panel()` creates an Orca-owned panel in the Prepare
  and Preview workspace;
- `PresetSelected` and `ProjectDirtyChanged` carry the active profile/change
  observations needed to test context freshness;
- `GCodeExportStarted` and `GCodeExportFinished` carry the model ID/name,
  destination path, and outcome needed to associate a manually exported file;
- `--datadir` selects a separate settings tree; and
- `orca.host.plugin.storage()` gives the plugin a bounded evidence directory.

The probe deliberately does not use networking, start a print, write a preset,
or drive Orca's calibration UI.

## Launch with isolated settings

Open PowerShell in this repository and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\orca-nightly-qualify.ps1 -OrcaDir 'C:\path\to\extracted-nightly'
```

The launcher refuses the normal Orca settings paths and any non-empty data
directory it did not create. It verifies the exact executable and DLL hashes,
uses this separate data directory by default:

```text
%LOCALAPPDATA%\HelixOrcaCalibration\issue-4-nightly-210bc927
```

It stages only the current `plugin/helix_calibration.py` and the bounded test
profiles into that directory, records the exact `--datadir` launch arguments,
and creates `qualification-output` for manual export. Existing Orca program
files, settings, presets, and login state are not selected.

Close every ordinary Orca process before running the qualification so Windows
single-instance handoff cannot redirect the request into a different process.
The launcher prints the new process ID, data path, plugin hash, output path, and
launch-record path.

## Interactive checklist

Retain screenshots of the named UI states and the two generated JSON evidence
files. Record any mismatch exactly and stop.

1. Complete the first-run wizard inside the isolated data directory without
   signing in or adding a physical printer. The test stays local.
2. In Orca, import all JSON files from
   `qualification-inputs\orca-profiles`. Select:
   - printer `Voron 2.4 300 0.4 nozzle`;
   - filament `Generic PLA - Voron Rapido - Initial`; and
   - process `Voron 0.20 Standard - Fast Quality`.
3. Enable the three locally staged `Helix Calibration Context` version `0.3.0`
   script capabilities in Orca's plugin UI.
4. Run **Helix Calibration**. Verify that the saved printer/process/filament
   identities and effective `0.4 mm` nozzle / inherited `220 °C` filament
   temperature are visible. This is the original target-profile context.
5. In the filament editor, change normal nozzle temperature to `217 °C` but do
   not save the profile. Refresh **Helix Calibration**. Verify `217 °C` and
   **Unsaved edits present**. Run **Export Orca Context JSON** and retain the
   output. Its saved-profile, current-edited, and merged-effective sources must
   remain separate; an inherited saved value must not be fabricated as a leaf
   value.
6. Run **Helix Calibration Nightly Qualification**. Verify an Orca-owned panel
   appears in the Prepare/Preview workspace and reports version `2.5.0-dev`,
   build `210bc927`, target match **Yes**, the same active profiles, and the
   effective `217 °C` value.
7. Switch away from and back to each test profile. Make and revert one unsaved
   setting edit. Confirm the panel receives `PresetSelected` and
   `ProjectDirtyChanged` with the expected names/dirty state; confirm refreshed
   context follows the real selection.
8. Use Orca's normal **Calibration > Temperature** command. Choose PLA and the
   nightly's built-in `230 °C` start, `190 °C` end, and `5 °C` step. Accept the
   dialog to prepare the standard temperature tower. This is test-only
   preparation in the isolated settings tree; it must not replace the original
   target-profile context recorded in steps 4–5.
9. Slice with Orca normally, then use **Export G-code file** and choose the
   launcher's `qualification-output` directory. Verify the exported file exists
   and that the panel receives `GCodeExportStarted` followed by a successful
   `GCodeExportFinished` naming that exact path and the same model association.
   Do not click Print, Upload, Send, or any device action.
10. Inspect the prepared G-code and record the commanded Temperature choices.
    They must cover Helix's accepted `230, 225, 220, 215, 210, 205, 200, 195,
    190 °C` result choices. A mismatch is a qualification failure, not a reason
    to alter Helix or invent a custom generator.
11. Click **Save qualification evidence** in the dock panel. Retain:
    - `qualification-launch.json`;
    - the `orca-context-*.json` inventory;
    - the `nightly-qualification-*.json` event/context capture;
    - the actual exported `.gcode` plus its SHA-256; and
    - screenshots of the context window, unsaved value, dock panel runtime,
      event list, built-in Temperature dialog, sliced Preview, and export path.
12. Close the isolated nightly. Reopen the normal Orca installation normally
    and confirm its existing profiles/settings remain unchanged.

## Pass/fail boundary

Qualification passes only if all of these are observed in the actual fixed
Windows GUI runtime:

- exact runtime build match;
- real saved, edited/unsaved, and merged-effective context reads;
- working host-owned dock panel;
- `PresetSelected`, `ProjectDirtyChanged`, `GCodeExportStarted`, and successful
  `GCodeExportFinished` payloads with useful identity/path fields;
- an actual normally prepared and manually exported Temperature file whose
  choices match Helix; and
- isolation from the existing Orca installation.

Any plugin load failure, missing context distinction, missing or ambiguous file
association, event loss, incorrect Temperature schedule, or inability to keep
settings isolated is a genuine capability blocker. Stop there and attach the
evidence to Issue #4. Do not compensate with profile writes, UI automation, a
custom G-code generator, or physical-printer access.
