# Issue #4 Temperature round-trip proof

The mock-only round trip passes on Spare's fixed Orca `2.5.0-dev` build
`210bc927` and native HelixScreen beta.4. Orca plugin `0.4.0` adds **Helix
Temperature Round Trip (mock only)** beside the three qualified read-only
capabilities. The accepted permissionless Helix plugin and ordinary native
harness are unchanged. The interactive Temperature picker remains deferred.

Founder accepted Issue #4 and PR #5 on 2026-10-12 (America/Chicago) as a completed
mock-only technical proof of concept and authorized merge and closeout. Further
UX polish is [future backlog work](backlog.md). The proven result remains NOT
APPLIED; hardware, production transport, real-print control and profile writes
remain prohibited. This closeout changes documentation only and preserves the
existing evidence and runtime sources.

## Proven result

The original target is the unchanged offline-bundle printer and process, with
`Generic PLA - Voron Rapido - Initial` as the original filament. Supported
runtime APIs report saved resolved nozzle temperature **220**, edited **217**,
and merged effective **217**, with a **0.4 mm** nozzle. These are three separate
reads; they do not claim equality with a raw inherited leaf JSON.

The explicitly selected, normally exported file is 3,619,569 bytes, SHA-256
`24594869ed17ec6d26c920ff684329c087487d20cbffddaf849c1afd4cdf271b`, with choices
230, 225, 220, 215, 210, 205, 200, 195 and 190. The request ID is
`f4a33a9c526e24c63c2d653fc51cfb0c`; its immutable artifact binds the original
context and actual file digest. Native Helix returns **205** for the same ID,
context, file, printer, filament and setting.

The native context label says **Effective: 217°C**, keeping that value distinct
from the saved 220°C. The executed source-built Helix binary is SHA-256
`29dbb6f32b26561b781522991279bf6f31d6acc4230f4bb6ac0cc9d6947ffcb4`;
the optional Actions accelerator is a different binary and was not executed.
The original report binds the executed source at its capture time, including
the binary, every viewport and imported harness. The later result-first
companion proof is
[`companion/report.json`](evidence/issue-4/roundtrip/companion/report.json).
It binds current source, the fresh request/result and actual Windows frame. An
AST contract check proves every plugin reader, callback and guard remains
identical while allowing the companion HTML to change. Original captures are
retained with their original hashes; they are not relabeled as new executions.

On Spare, selecting that native result shows:

- Profile: **Generic PLA - Voron Rapido - Initial**.
- Setting: **Filament > Print temperature > Nozzle > Other layers**
  (`nozzle_temperature`).
- Original saved: **220°C**; original edited/effective: **217/217°C**.
- Selected: **205°C**; status: **NOT APPLIED**.

The current filament was deliberately switched to the template and the unsaved
edit discarded before result reception. The instructions still name the
retained original target. Native Windows selection also proved identical
results are ignored, stale IDs are rejected, and a conflicting duplicate is
rejected, with the original 205°C instructions unchanged. No preset was saved
or value applied. All 1,429 normal settings/profile files still match the
pre-test aggregate fingerprint at `2026-10-12T02:45:44Z`.

[Fresh-browser repair proof](evidence/issue-4/roundtrip/browser/report.json)
records both Finish surfaces, normal Home/Back return, responsive controls,
actual 205°C selection, and Spare LAN readback.

[Committed proof](evidence/issue-4/roundtrip/report.json) retains the real Orca
request, native result, candidate/file/frame hashes and complete eleven-target
matrix. Public Windows instruction frames are direct bounded native screen
captures, keeping personal artifact paths in private evidence. The full export,
raw diagnostic inventory, access logs and complete captures remain in XDG state.

## Transport and isolation

The pinned upstream native bridge is
`ed8d0c4977873969613fcb49024109ff7df7d84e`. Its repository-only adaptation is
in [`../integration/`](../integration/README.md). It is mounted solely by the
separate proof driver; the ordinary harness does not discover or enable it.

Actual beta.4 refuses plugin HTTP to loopback/local addresses to protect the
printer host. That guard is preserved. The proof uses the existing pinned LAN
SSH route plus supported native plugin-storage artifacts. Orca never opens a
network connection. Native bridge request receipt only shows **Start**;
the mock print begins only after that visible native action.

The driver validates the request/context identity, file size/hash and actual
Temperature bands before copying the G-code byte-for-byte into a read-only
mock mount. The pinned native binary runs `--test`, Docker `--network none`,
read-only root/runtime/product/bridge/G-code mounts and a private control socket.
Only marked per-run state is writable. No production Moonraker or physical
printer can be reached from that container.

The complete eleven-size run proves missing request delivery/recovery, explicit
native Start, the mock's real printing notification, controlled 50% progress
and completion, native dropdown selection, failed native result write and Next
retry. It temporarily changes only the private run's plugin-data directory
permissions and restores them. Native pointer input starts the mock; native
LVGL value/click events handle matrix result selection; fresh-browser review
uses normal native pointer/dropdown input. The test clock is parked before
remote pointer creation so navigation stays live. These are test controls, not product APIs. No hardware or real print
execution is claimed.

Beta.4 also lacks the example's newer translation binding. The adapter uses
English and the supported native close callback to reopen a component after
queued navigation. No upstream changes or host security changes are needed.

## Reproduce on the qualified targets

1. Use the marked isolated nightly and child-only WebView2 data folder in
   [Windows qualification](ORCA_NIGHTLY_QUALIFICATION.md). On each new session,
   import the unchanged offline fixture bundle normally: this build's restart
   loader can omit the original System-name-colliding bundle leaf. Do not use
   normal Orca data or save a preset.
2. Install/activate `plugin/helix_calibration.py` through Orca's normal local
   plugin installer. Open **App menu > Plugins > Helix Calibration Context >
   Helix Temperature Round Trip (mock only)**.
3. Select the original imported profiles, make the deliberate unsaved 217°C
   edit, and click **Keep original profile** before any temporary
   preparation. Prepare/slice/export normally, or use the existing qualified
   export. Explicitly select its actual bytes and click **Prepare mock calibration**.
4. Transfer the bounded request and unchanged export through the approved
   private Spare worker. On devbox, run:

```sh
python3 scripts/temperature-evidence.py capture --request "$REQUEST_JSON" --gcode "$EXPORTED_GCODE"
python3 scripts/temperature-evidence.py promote --request "$REQUEST_JSON"
python3 scripts/temperature-evidence.py verify
python3 -m unittest discover -s tests -v
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
git diff --check
```

`REQUEST_JSON` and `EXPORTED_GCODE` identify actual retained artifacts. No file
generator or slicing automation exists. Default private output is beneath
`$XDG_STATE_HOME/helix-orca-calibration/temperature-roundtrip` (or
`~/.local/state/…`); runtime mount scaffolding stays in the user cache.

5. Return one run's `result.json` through the same SSH testing route, then
   explicitly select it in Orca. Review the named original profile and setting;
   the proof never applies the value.

## Working review path

Spare remains the interactive Windows target. The isolated nightly's dock
shows the returned original-profile instructions. The normal Orca installation
and data remain separate. Open the companion from the normal Plugins menu path
above if needed; original target/request state survives closing/reopening that
panel within this process.

The native proof viewer uses the reserved trusted-LAN address supplied in the
private task handoff. It shows native frames and forwards bounded
native tap/drag/Home/Back/capture input. **Finish simulated print** is the sole
additional proof control: after a received request is explicitly started, it
uses the same isolated mock completion sequence as the capture driver. It
rejects an unstarted request and cannot start printing. It binds devbox's LAN interface and
adds no Windows listener, firewall rule, service, public route or Tailscale.
Start/restart a review with the retained real artifacts:

```sh
python3 scripts/temperature-evidence.py review --request "$REQUEST_JSON" --gcode "$EXPORTED_GCODE"
python3 scripts/temperature-evidence.py down
```

For Founder Review, open a fresh browser session using the private handoff link.
The prominent **Finish simulated print** control sits above the native frame,
with an explicit mock-only label; it becomes enabled immediately after Start.
The native mock calibration also has that control while printing.

1. On **Mock Temperature**, review the original filament, **Effective: 217°C**,
   and **Mock request received; not started**, then click native **Start**.
2. While printing, exercise normal navigation: **Home** exposes the native
   **Mock Temperature** tile and stock active-print card. Tap the card to return
   to **Print Status**, then **Back** to Home. Tap **Mock Temperature** to resume
   the same active calibration. There is no Settings recovery step.
3. **Print Status** may show a long synthetic estimate. Click the prominent
   **Finish simulated print** above the frame, or the native calibration's
   Finish button, to reach choices immediately; no timer wait is needed.
   Acknowledge the native completion dialog if it appears.
4. Choose **205°C** in the native dropdown and click **Next**. Expect
   **205°C — sent to the companion; not applied**. Home and the tile can also
   reopen the waiting choices or returned result without losing state.
5. On Spare, read the top result card: **Generic PLA - Voron Rapido - Initial**,
   effective at calibration start **217°C**, selected **205°C**, and prominent
   **NOT APPLIED**. The live current effective value has its own filament label;
   it can differ after a profile switch. The card tells you to select the
   original profile, open **Filament > Print temperature > Nozzle > Other
   layers**, enter **205°C**, and save only if you choose to keep the result.
   No setting is applied by the companion. Expand **Technical details &
   diagnostics** for saved **220°C**, edited **217°C**, artifacts and identity
   evidence; expand **Load another result or start a new calibration** for file
   controls. Do not click **Keep original profile** unless starting a new task,
   because it clears the previous result.

The accepted **Orca Calibration** tile remains its separate Issue #1
chooser/detail/toast flow. The new mock tile and stock print card are seeded
only by the isolated proof driver; normal product/harness files are unchanged.
The proof parks its synthetic clock before remote input is created, keeping
completion stable instead of allowing a later mock snapshot to restart the
print. The existing test freeze also pauses periodic timers and disables
animations; native input, navigation, update and rendering remain live.
The viewer forwards ordinary native Home/Back and pointer input. It does not
intercept Home to reopen or trap the user in a calibration.

The native Finish action writes only a bounded request-ID/sequence artifact.
The owned mock driver checks that identity and the active-print state before
simulating completion. Duplicate finish actions do not replay, and a later
Cancel or an already completed result takes precedence. No real-printer
command is introduced. Updated viewer pages detect a subsequent candidate
change and reload rather than retaining obsolete controls.

Judge discoverability, state continuity and the clarity of simulated completion
and **not applied** instructions. Hashes, rejection cases, normal-data
preservation and the complete native matrix are toolchain checks already done.
The interactive Temperature picker, physical printing, profile application,
release and merge remain excluded.
