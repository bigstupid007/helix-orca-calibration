# Issue #4 Temperature round-trip proof

The mock-only round trip passes on Spare's fixed Orca `2.5.0-dev` build
`210bc927` and native HelixScreen beta.4. Orca plugin `0.4.0` adds **Helix
Temperature Round Trip (mock only)** beside the three qualified read-only
capabilities. The accepted permissionless Helix plugin and ordinary native
harness are unchanged. The interactive Temperature picker remains deferred.

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
The report binds the actual binary and build provenance, every viewport's
recorded binary, and the imported `scripts/helix_dev.py` along with the driver,
Orca plugin and bridge sources.

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
LVGL value/click events handle the result while mock freeze pauses the pointer
sampler. These are test controls, not product APIs. No hardware or real print
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
   edit, and click **Retain original target context** before any temporary
   preparation. Prepare/slice/export normally, or use the existing qualified
   export. Explicitly select its actual bytes and click **Export mock request**.
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

The native proof viewer uses the already reserved trusted-LAN address
`http://192.168.1.114:8540/`. It shows native frames and forwards bounded
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

For Founder Review:

1. Start on **Mock Temperature**, where the original filament and
   **Effective: 217°C** appear with **Mock request received; not started**.
2. Click native **Start**. The real mock opens **Print Status**. Click the
   viewer's **Finish simulated print** to reach the native Temperature choices
   without waiting through the synthetic time estimate. Acknowledge the native
   completion dialog if it appears.
3. Choose **205°C** in the native dropdown and click **Next**. Expect
   **205°C — sent to the companion; not applied**.
4. On Spare, open the Orca companion through the Plugins menu. Its retained
   result names **Generic PLA - Voron Rapido - Initial**, **Other layers**, saved
   **220°C**, edited/effective **217/217°C**, selected **205°C**, and **NOT APPLIED**.

After **Home**, return through **Settings > Plugins > calibration-bridge > Open**;
drag upward within the native settings list to reach Plugins. The accepted
Orca Calibration tile remains its separate Issue #1 chooser/detail/toast flow.
Native **Back/Home** also returns to that unchanged accepted shell.
Judge whether the original context, mock Start, file association,
Temperature choice, retry messages, and unambiguous **not applied** instructions
are understandable. The committed runtime/preservation checks do not need to
be repeated by the owner. This is a proof candidate for one unmerged PR; no
release, merge or hardware activation is authorized.
