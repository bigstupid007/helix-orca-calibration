# Orca nightly qualification gate

## Status

The fixed Windows x64 runtime passed qualification on Spare at
2026-10-12 01:14:49 UTC, using the approved manual exported-file fallback.
The original target profiles, saved/edited/effective distinction, unsaved value,
profile switches, host-owned dock, useful events, normal Temperature export,
manual byte/hash association, and normal-settings preservation are proven.
The subsequent mock-only round trip is complete and Founder-accepted as a
technical proof of concept; see [the completion record](ISSUE_4_PRODUCT_PREFLIGHT.md).
Qualification was not restarted for acceptance or closeout. Hardware, production
and profile-write restrictions remain in force.

See [`evidence/issue-4/windows/qualification.json`](evidence/issue-4/windows/qualification.json)
and its eight target-only native frames. Full diagnostic inventories, actual
G-code and file-picker captures remain private in XDG state.

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
| Spare name resolution | Owner-confirmed private LAN address | Current address resolved by devbox |
| Established SSH socket | Spare address to devbox's LAN SSH endpoint | Spare-to-devbox connection exists |
| SSH to Spare | Eight-second batch-mode attempt timed out before authentication | Windows execution via reverse SSH is unproven |
| TCP to Spare ports 22, 3389, 5985 | Each five-second check timed out | These standard access endpoints were unreachable from devbox |
| Session tools | No Windows-local command or desktop-control tool | Launching this chat on Spare does not provide Windows execution here |

At that initial checkpoint, the installed Orca version, Windows account,
interactive session state, and fixed nightly launch had not been observed. Do not infer that Spare is asleep,
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
hash-verified. The restarted worker passed an actual bounded-pipe capture regression,
and the retry nightly was observed running.

The first launch used an unsupported `--no-single-instance` flag and crashed;
that flag was removed. Reconnection confirmed the original-argument retry was
running. The corrected worker then passed its actual Windows bounded-pipe
regression. No further owner access action is pending.

### Completed run and supported original-context resolution

The ordinary single-JSON importer rejects the supplied user printer's name
because a bundled System preset already uses it. The exact source also supports
offline `.orca_bundle` import with `bundle_structure.json` and a separate local
namespace (`PresetBundle.cpp:1738–1828,1885–1889,8208`). That supported route
imported all six supplied configs without changing their JSON bytes, names,
IDs, inheritance or values. The actual printer is
`_local/helix-issue-4-original-context/Voron 2.4 300 0.4 nozzle`, with the
original bare alias, `is_from_bundle=true` and `is_system=false`. No parent or
System profile substitutes for the original leaf.

`scripts/orca-qualification-bundle.py` reproduces the offline wrapper with fixed
ZIP timestamps and verifies every extracted profile byte. Its archive digest
differs from the first imported archive only because that archive used current
ZIP timestamps; both archive digests and original fixture hashes are recorded.
Import the ordinary JSON parents first, then the bundle; Orca owns dependency
resolution and import storage.

Editing the selected bundle filament caused Orca to select the same-named
ordinary imported User filament. The diagnostic preserves these native names
and origins. It reports selected-saved config `220`, current-edited `217`, and
merged effective `217`. The host also reports dirty metadata on the saved
selection during the edit; that flag does not mean the saved config became 217.
The original bundle printer/process identities remain distinct. Resetting the
unsaved test changes restores 220 without saving a preset.

The completed run used test Orca PID 32504 and separate WebView2 storage.
Normal Orca PID 40056 remained running. The dock reports `2.5.0-dev`, `210bc927`,
match Yes; all three profile categories were switched away/back, dirty true/false
arrived, and explicit refresh followed real context. Lifecycle events alone do
not automatically refresh the context display.

Normal built-in PLA Temperature preparation/export used a separate temporary
System context. The export is 3,619,569 bytes, SHA-256
`24594869ed17ec6d26c920ff684329c087487d20cbffddaf849c1afd4cdf271b`, with exactly
50 `M104` commands at each of 230,225,220,215,210,205,200,195,190 degrees.
Export events identify only the temporary slicing path (ID 7), with no exact
manual export destination. The approved native manual picker read the actual
new export and its local SHA-256 and choices matched the returned file.

`--datadir` alone previously shared normal WebView2 browser data; the guard
refused its shared picker. The launcher now sets Microsoft's documented
child-only `WEBVIEW2_USER_DATA_FOLDER` override, and separate process/storage
was proved before the complete run. See
[Microsoft's override reference](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/win32/webview2-idl).
Earlier captures are retained as historical observations, never as the passing
isolation run. The original fixture also emits a host-identity `DeviceSelected`
event; Device/Print/Upload/Send controls were never invoked. The exact source
keeps the printer webview lazy until that page is visited.

A mistaken unsaved test bed-temperature edit during revert was caught by Orca's
safety dialog and reset. At close, the test project and all temporary calibration
preset edits were discarded. All 1,429 normal settings/profile files matched
the pre-test aggregate; only the normal Orca process remained running. This
qualification confers no physical-printer authority and is not a completed mock
round trip.

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

It stages the current `plugin/helix_calibration.py` as a local-install input
and the bounded test
profiles into that directory, records the exact `--datadir` launch arguments,
and creates `qualification-output` for manual export. Existing Orca program
files, settings, presets, and login state are not selected.

The portable executable and separate marked data path were observed alongside
the untouched ordinary Orca process. The launcher also sets a child-only
WebView2 data override; verify a separate browser process/storage path before
any plugin UI input. It prints the test process ID and records launch metadata.
Install the staged `.py` through Plugins > Install local plugin; copying into
`orca_plugins` alone did not initially register it.

## Interactive checklist

Retain screenshots of the named UI states and the two generated JSON evidence
files. Record any mismatch exactly and stop.

1. Complete the first-run wizard inside the isolated data directory without
   signing in or adding a physical printer. The test stays local.
2. Import the ordinary JSON parents from `qualification-inputs\orca-profiles`
   first. Run `python3 scripts/orca-qualification-bundle.py` on devbox, transfer
   its verified offline bundle as a test input, and import it through normal
   File > Import > Import Configs. All six unchanged profiles must import.
   Select the original leaf from the **Helix Issue 4 original fixtures** bundle:
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

Normal Orca preservation was checked after GUI testing: all 1429 settings/profile
files matched the pre-test aggregate SHA-256
`ed4cd00fff296723223ede35beabcacb41a64d2046c8c30a60513aa1de3bd0f0`.
`scripts/spare-normal-preservation.ps1` records the exact hash-only recipe and
excludes cache, logs, and plugin data. This establishes normal profile/settings
preservation, while the earlier shared browser-cache gap remains disclosed.

## Subsequent companion build

The qualification above is historical `0.3.0` evidence. Actual Spare testing
of `0.4.0` also installed/activated all four capabilities, retained original
220/217/217 context, verified the same file, and received native 205°C
instructions as **not applied** after a filament switch. Duplicate/stale/
conflicting result selection and normal settings preservation were checked.
On each fresh session this build may omit the colliding bundle leaf; re-import
the identical offline bundle normally before selecting the original target.
See [the completed proof](TEMPERATURE_ROUND_TRIP.md).


The later result-first companion repair changes only its HTML presentation.
Supported plugin Reload in the same isolated process loaded the new source;
focused actual Windows file selection/request creation/result import passed
with the same original context and qualified file. This is subsequent runtime
validation, not a qualification restart. The current companion source hash and
Windows frame are in
[`evidence/issue-4/roundtrip/companion/report.json`](evidence/issue-4/roundtrip/companion/report.json).
