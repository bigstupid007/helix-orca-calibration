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

## Verify

```sh
python3 -m unittest discover -s tests -v
git diff --check
```
