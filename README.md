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
record the resolved findings and Founder Review limits. PR #5 remains unmerged.

Qualification UI driving and complete mock lifecycle simulation remain test
infrastructure. Modeless-window and explicit manual-file fallbacks remain
supported. The interactive Temperature picker is deferred and unimplemented.

## Verify

```sh
python3 -m unittest discover -s tests -v
git diff --check
```

The Issue #4 candidate includes the earlier product/harness policy suite and
the Orca qualification, access, request/result, and evidence checks. Run the
suite from the candidate checkout; historical dirty-checkout counts are not
the candidate's validation result.
