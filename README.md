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

## Issue #4 — Temperature round trip (qualification gate active)

Issue #4 replaces the deferred interactive-picker idea with one bounded
Temperature round trip. The first gate is qualification of the fixed October
11 Windows Orca nightly in a separate settings tree. The source-verified,
read-only probe is `plugin/helix_calibration.py` version `0.3.0`; it preserves
the accepted context window and diagnostic export and adds an Orca-owned panel
for exact build/context/lifecycle evidence.

The Windows launcher and interactive checklist are in
[`docs/ORCA_NIGHTLY_QUALIFICATION.md`](docs/ORCA_NIGHTLY_QUALIFICATION.md).
Spare is the intended interactive Windows target. The founder approved minimum
LAN-only command/GUI testing access on October 11. The prepared unelevated
reverse worker reuses existing SSH without a Windows listener, installation,
firewall change, or Tailscale. Actual Windows access is still unproven pending
its first local launch; see [`docs/SPARE_TEST_ACCESS.md`](docs/SPARE_TEST_ACCESS.md).

Windows runtime qualification is still pending, so no round-trip transport,
result handling, profile writeback, or printing behavior has been implemented.
The accepted Helix plugin remains unchanged.

The approved integration may later simulate a complete print lifecycle only in
the isolated mock harness. Qualification UI driving is evidence tooling, not a
shipping Orca automation path. Dock-panel/event integration retains
modeless-window and explicit manual-file fallbacks. The interactive Temperature
picker remains deferred and unimplemented.

## Verify

```sh
python3 -m unittest discover -s tests -v
git diff --check
```

The Issue #2 candidate contains 22 committed tests: seven Issue #1 plugin
policy tests plus fifteen harness tests. This canonical checkout currently also
contains 18 unrelated, uncommitted Orca diagnostic tests, so the full dirty
working-tree command reports 40. The earlier Issue #1 note saying “25 tests”
described that mixed working tree; the exact Issue #1 commit contained seven.
