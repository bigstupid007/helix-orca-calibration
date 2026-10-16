# Helix-Orca Calibration

## Issue #1 — native Helix calibration foundation

`helix-plugin/orcacal/` is the accepted product baseline. Version `0.2.0`
targets the stock Lua plugin framework in HelixScreen `v1.1.0-beta.4` and uses
the native flow:

`home tile -> calibration chooser overlay -> Temperature overlay`

The chooser presents the fixed development context in a compact two-line card
so the calibration list remains dominant. Temperature is the only current
module. Its detail shows `230°C -> 190°C`; **Start** only displays the native
toast `Calibration request test`.

The plugin uses Helix-owned navigation, headers, overlays, theme tokens, cards,
icons, and responsive sizing. It requests no permissions and has no Moonraker,
networking, storage, G-code, slicing, print execution/monitoring, results, or
Orca writeback.

Future calibration modules extend the local registry and add plugin-owned
native detail components to this chooser/detail shell. They do not introduce a
second application shell or speculative workflow controls.

The beta.4 capability and viewport contract is recorded in
[`helix-plugin/CAPABILITY_PREFLIGHT.md`](helix-plugin/CAPABILITY_PREFLIGHT.md).
Native mock-printer closeout evidence for all eleven supported target
geometries is in [`helix-plugin/PREFLIGHT.md`](helix-plugin/PREFLIGHT.md).
Installation and local test instructions are in
[`helix-plugin/README.md`](helix-plugin/README.md).

## Issue #2 — native developer harness candidate

[`scripts/helix-dev`](scripts/helix-dev) owns the reproducible native beta.4
mock-printer loop without changing the accepted plugin shell:

```sh
./scripts/helix-dev bootstrap
./scripts/helix-dev up
./scripts/helix-dev status
./scripts/helix-dev reload
./scripts/helix-dev capture
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
./scripts/helix-dev down
```

The default interactive target is the real 800x480 dark Helix runtime at
`http://192.168.1.114:8540/`. The browser page displays Helix-rendered frames
and sends input through Helix's native control API; it is not a replacement UI.
The Helix container is read-only, uses the mock printer with `--network none`,
and mounts the current plugin directly for beta.4 hot reload.

The capture path exercises the accepted tile -> chooser -> Temperature ->
Start-toast -> Back flow at all eleven verified target sizes. Default artifacts
are retained outside Git in XDG state; the bounded promoted evidence is in
[`docs/evidence/issue-2/`](docs/evidence/issue-2/). Setup, safety, exact pins,
operations, and evidence reproduction are documented in
[`docs/HELIX_DEV_HARNESS.md`](docs/HELIX_DEV_HARNESS.md).

Bootstrap pins the annotated source commit and release data. A short-lived
upstream Actions binary is used only as a SHA-verified accelerator; the durable
fallback builds the exact public source and recursive submodule revisions with
the pinned repository-owned builder recipe.

## Issue #4 — qualified mock Temperature round trip

Issue #4 replaces the deferred interactive-picker idea with one bounded
Temperature round trip. The first gate is qualification of the fixed October
11 Windows Orca nightly in a separate settings tree. The source-verified,
companion is `plugin/helix_calibration.py` version `0.4.0`; it preserves
the qualified context/export/panel capabilities and adds a host-owned mock
round-trip dock. The completed qualification used version `0.3.0`.

The Windows launcher and interactive checklist are in
[`docs/ORCA_NIGHTLY_QUALIFICATION.md`](docs/ORCA_NIGHTLY_QUALIFICATION.md).
Spare is the verified interactive Windows target. The founder-approved LAN-only
worker uses existing pinned SSH, without an inbound Windows service, firewall
change, Tailscale, or identity changes. Its restarted command capture passed the
actual Windows inherited-pipe regression. See
[`docs/SPARE_TEST_ACCESS.md`](docs/SPARE_TEST_ACCESS.md).

The fixed Windows nightly now proves plugin installation, real saved `220 °C`
versus unsaved/merged `217 °C`, a working Orca-owned dock, useful preset/dirty
events, and normal Temperature preparation/export. The exported file contains
all nine `230–190 °C` choices. Lifecycle events identify only the temporary
slicing file; native manual selection verified the actual export's bytes/hash.
A child-only WebView2 data override now separates test browser state as well as
Orca settings.

The Windows gate passed on Spare at 2026-10-12 01:14 UTC. The supported offline
bundle importer resolves the original printer's System-name collision while
preserving all six supplied JSON files byte-for-byte. Runtime context identifies
the original leaf under `_local/helix-issue-4-original-context/`, with
`is_system=false`. The full run used separate Orca and browser storage; all
1,429 normal settings/profile files remain unchanged.

The bounded report and native frames are in
[`docs/evidence/issue-4/windows/`](docs/evidence/issue-4/windows/).
The new export is 3,619,569 bytes, SHA-256
`24594869ed17ec6d26c920ff684329c087487d20cbffddaf849c1afd4cdf271b`.
The mock round trip now passes at all eleven native Helix sizes and returns
205°C to the retained original filament with **NOT APPLIED** instructions,
even after Orca's current filament changes. Duplicate/stale/conflicting results
and real artifact delivery failures/retries are proven. The accepted Helix
plugin remains unchanged. Native beta.4's loopback HTTP guard is preserved;
the isolated proof uses pinned LAN SSH and native plugin-storage artifacts.
See [the proof and working review path](docs/TEMPERATURE_ROUND_TRIP.md).
The [candidate review and AI Product Preflight](docs/ISSUE_4_PRODUCT_PREFLIGHT.md)
record the consolidated Founder Review repair and its review limits. The mock
proof provides a prominent immediate Finish control and native Home return
tile/print card. The Orca companion leads with the selected result, original
profile, live effective value and exact manual update steps. **NOT APPLIED** is
prominent; preparation and technical details are expandable. Founder accepted
Issue #4 and PR #5 on 2026-10-12 (America/Chicago) as a completed mock-only
technical proof of concept and explicitly authorized merge and closeout.
Further UX polish is [deferred backlog work](docs/backlog.md), not a completion
gate. Acceptance authorizes no hardware, production, or profile-write use.

Qualification UI driving and complete mock lifecycle simulation remain test
infrastructure. Modeless-window and explicit manual-file fallbacks remain
supported. The interactive Temperature picker is deferred and unimplemented.

## Issue #6 — accepted display-only real-HelixScreen milestone

Issue #6 qualifies HelixScreen `v1.1.0-beta.9` and the pinned October 15 Orca
nightly for a bounded physical display increment. Normal Orca's explicit
**Upload** action transfers the prepared file without starting or queuing a
print. A readback of those exact bytes is bound to the retained original Orca
context before the permissionless `helix-orca-display` plugin receives its
separate display-only event.

The plugin requests no permissions and presents one native receipt with
**Dismiss** as its only action. The owner observed the expected
`Received · not printed · not applied` receipt, retained original effective
temperature, prepared range, and successful Dismiss after exactly one event.
Target-specific operational evidence remains private. The release pins,
qualification boundaries, independent review, and reproducible public evidence
are recorded in
[`docs/ISSUE_6_QUALIFICATION.md`](docs/ISSUE_6_QUALIFICATION.md).

Founder accepted Issue #6 and PR #7 on 2026-10-15 (America/Chicago) and
authorized governed merge and closeout. Acceptance is limited to the physical
display receipt. The real Orca result-return path remains mock-only; print,
queue, heating, motion, profile writeback, service/security changes, public
access, release, and deployment remain outside the accepted milestone. Visual
polish is deferred until the complete Orca-to-Helix-to-Orca workflow functions.

## Verify

```sh
python3 -m unittest discover -s tests -v
git diff --check
```

The suite includes the accepted product/harness policy, Orca qualification,
request/result, display-only transport, release-lock, and evidence checks. Run
it from the candidate checkout; historical dirty-checkout counts are not the
candidate's validation result.

## Issue #8 — bidirectional communication candidate

[Build Program #8](https://github.com/bigstupid007/helix-orca-calibration/issues/8)
authorizes one real Temperature request/selection return without printing. The
candidate generates a beta.9 derivative of the accepted `orcacal` chooser and
Temperature detail, a self-contained October 15 Orca companion derivative, and
a bounded relay using existing access. Accepted Issue #1, #4 and #6 sources and
the beta.4 harness remain unchanged.

The candidate passes 172 tests, corrected eleven-viewport native evidence,
isolated Windows validation and reviewed receipt-driven retry/recovery. The
owner enabled the exact storage-only plugin and observed the original context
and simulated 205°C/Return on the actual screen. **The physical return is
blocked:** beta.9 writes its sidecar under the install tree, outside the
Moonraker config route assumed by the relay. No result or receipt reached Spare.
The relay is stopped; no configuration remedy is authorized or applied.

The founder approved the disclosed trusted-LAN boundary, which remains
unencrypted and without per-message cryptographic authentication. A narrowly
reviewed proposal would create one real shared directory and one file link,
exposing only `orcacal.json` through the existing config API; this needs a new
explicit owner decision and existing owner access. See the
[storage gate](docs/TEMPERATURE_COMMUNICATION_STORAGE_GATE.md),
[program](docs/BUILD_PROGRAM_TEMPERATURE_COMMUNICATION.md), and
[operations](docs/TEMPERATURE_COMMUNICATION.md). PR #9 remains draft; full AI
Product Preflight, Founder Review, merge and deployment are not complete.
