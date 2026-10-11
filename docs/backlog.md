# Backlog

## Completed: Issue #1 — Helix calibration hub/detail foundation

Founder accepted the final candidate on 2026-10-10. HelixScreen plugin
`orcacal` version `0.2.0` establishes the baseline product shell:

`native home tile -> calibration chooser -> Temperature detail -> Start toast`

- [x] Complete the beta.4 source/runtime capability and viewport preflight.
- [x] Preserve Helix-owned overlay/header/Back behavior and dark visual tokens.
- [x] Add a reusable local calibration registry.
- [x] Present the same four development-context values in a compact two-line
  card above the dominant calibration list.
- [x] Expose only the current Temperature module.
- [x] Keep Temperature to `230°C -> 190°C` and the existing local Start toast.
- [x] Request no permissions and expose no unsupported future workflow UI.
- [x] Validate discovery, enablement, tile, chooser, Temperature, Start toast,
  native Back, close/reopen, and horizontal fit at every supported target size.
- [x] Pass 25 dependency-free unit/policy tests and `git diff --check`.

The closeout matrix covers 480x272, 272x480, 480x320, 480x400, 800x480,
480x800, 1024x600, 1280x720, 1080x2400 at 405 DPI, 1920x480, and 320x1480.

This chooser/detail structure is the baseline for future calibration modules.
Future modules extend the registry and add their own native detail component;
they do not redesign the accepted Helix shell.

## Deferred — requires new approval

- Moonraker coordination or networking.
- G-code generation, modification, upload, or execution.
- Print start, monitoring, results, or calibration scoring.
- Orca preset mutation or writeback.
- Additional calibration modules beyond a separately approved increment.
