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

## Windows host and access checkpoint

Spare is the intended interactive Windows qualification target, as confirmed
by the owner on 2026-10-11. LAPTOP-EC83OFDE is not the target. Devbox remains
the implementation, Git, and evidence-assembly authority at
`/home/dev/Projects/personal/helix-orca-calibration`; the existing Issue #4
branch/worktree preserves unrelated canonical changes. Windows receives only
bounded setup, runtime qualification, and capture work through existing
authorized access. Do not author implementation or create branches there.

At 18:51 UTC on October 11 (1:51 p.m. America/Chicago), this session observed:

| Check | Observation | What it proves |
| --- | --- | --- |
| Shell identity | devbox, Linux `6.8.0-146-generic` | Implementation execution is on devbox |
| Spare name resolution | `192.168.1.155` | Current address resolved by devbox |
| Established SSH socket | Spare address to `192.168.1.114:22` | Spare-to-devbox connection exists |
| SSH to Spare | Eight-second batch-mode attempt timed out before authentication | Windows execution via reverse SSH is unproven |
| TCP to Spare ports 22, 3389, 5985 | Each five-second check timed out | These standard access endpoints were unreachable from devbox |
| Session tools | No Windows-local command or desktop-control tool | Launching this chat on Spare does not provide Windows execution here |

The installed Orca version, Windows account, interactive session state, and
fixed nightly launch have not been observed. Do not infer that Spare is asleep,
that SSH is disabled, or that credentials are wrong from a timeout. Existing
Tailscale discovery does not list Spare; its separate laptop entry is not a
qualification substitute. No Windows access mechanism or configuration was
changed.

These observations precede the founder's explicit October 11 approval for
minimum LAN-only command/interactive GUI access. The prepared route in
[`SPARE_TEST_ACCESS.md`](SPARE_TEST_ACCESS.md) uses an unelevated worker over the
existing outbound SSH path; no Windows listener, installation, firewall change,
new key/account, or Tailscale is needed. Command execution and a native button
click are now proven. The exact nightly and test inputs were transferred and
hash-verified. An output-pipe capture timeout interrupted the launch retry;
the corrected worker needs one owner-only restart and focused Windows proof.

The first launch used an unsupported `--no-single-instance` flag and crashed;
that flag has been removed. Its internal parser helper is not CLI registration.
A retry with only `--datadir` has an unresolved outcome. Inspect test process
state/logs after reconnecting before relaunching. Normal Orca remains outside
the tooling's process/path/input guards. These observations do not pass the
Windows qualification gate. The agent then verifies Windows
hostname/account/session, normal Orca processes, and isolated paths and owns
setup and evidence collection. Stop only for unavoidable owner-only access or
a material risk change outside the approval. The Windows qualification gate
itself remains unchanged.

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

Qualification tooling may reproduce the checklist through isolated UI input
and capture screenshots. This is evidence automation only: it must use the same
normal Orca controls described below and must not become a product dependency
or call unsupported slicing/export APIs. If the dock panel is unavailable or
unreliable, the same read-only state/evidence UI may use Orca's host-owned
modeless window. If export lifecycle payloads cannot associate one file
unambiguously, later round-trip work must retain explicit manual file selection.

## Launch with isolated settings

Through the existing authorized Windows execution route, stage the exact
devbox candidate as validation inputs on Spare, then run its launcher in
PowerShell:

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
   appears in the Prepare/Preview workspace (or qualify the approved host-owned
   modeless-window fallback if the dock cannot work) and reports version `2.5.0-dev`,
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
   If lifecycle association is missing or ambiguous, retain the actual payload
   and qualify explicit manual selection of the exact exported file as the
   approved fallback. Do not click Print, Upload, Send, or any device action.
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

The later integration harness may simulate start, progress, completion, result,
delivery failure, and retry for a mock print. This qualification does not add
that behavior to Orca and never targets a physical printer.

## Pass/fail boundary

Qualification passes only if all of these are observed in the actual fixed
Windows GUI runtime:

- exact runtime build match;
- real saved, edited/unsaved, and merged-effective context reads;
- working host-owned dock panel or a qualified modeless-window fallback;
- useful `PresetSelected` and `ProjectDirtyChanged` payloads and truthful
  refreshed context;
- useful `GCodeExportStarted` and successful `GCodeExportFinished` association,
  or captured evidence of the limitation plus qualified explicit manual
  selection of the actual file;
- an actual normally prepared and manually exported Temperature file whose
  choices match Helix; and
- isolation from the existing Orca installation.

Any plugin load failure, missing context distinction, required event loss,
incorrect Temperature schedule, or inability to keep settings isolated is a
genuine capability blocker. Dock-panel or file-association limitations require
the approved fallback to be proved before proceeding; fallback permission is
not evidence that the fallback works. Stop if neither approved path can be
proved, and attach the observations to Issue #4. Do not compensate with profile
writes, unsupported product UI automation, a custom G-code generator, or
physical-printer access. Isolated qualification UI driving remains approved
test infrastructure.

The interactive Temperature picker remains a deferred product requirement and
is not part of this qualification or Issue #4 implementation.
