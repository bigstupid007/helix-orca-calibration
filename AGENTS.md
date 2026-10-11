# AGENTS.md

## Issue #1 product authority

`helix-plugin/orcacal/` is the accepted permissionless HelixScreen calibration
plugin for the stock Lua framework introduced in `v1.1.0-beta.4`. Its baseline
product flow is:

`native home tile -> calibration chooser -> Temperature detail -> Start toast`

Keep the plugin inside the verified beta.4 XML/API allowlist and native overlay
stack. Preserve Helix-owned navigation, headers, Back behavior, dark visual
language, responsive design tokens, the compact Current Context card, the
calibration list, and calibration-specific detail components.

Temperature is the only implemented module. Its detail remains a read-only
`230°C -> 190°C` range plus the local `Calibration request test` Start toast.
Do not add Moonraker coordination, networking, storage, G-code, slicing, print
execution/monitoring, results, or Orca writeback without new approval.

Future calibration modules must extend the accepted local registry and
chooser/detail shell rather than replace or reinterpret its navigation and
visual structure. Do not expose placeholder modules or controls for behavior
that does not exist.

`references/OrcaSlicer`, `references/helixscreen`, `references/moonraker`, and
`references/klipper` are read-only. Run
`python3 -m unittest discover -s tests -v`, `git diff --check`, and the complete
viewport matrix in `helix-plugin/CAPABILITY_PREFLIGHT.md` after Helix UI changes.

## OSS safety before GitHub changes

No GitHub mutation is implied by an implementation request. Before any future
push, issue, pull request, release, or other GitHub mutation, verify all of:

- the working path is the canonical checkout
  `~/Projects/personal/helix-orca-calibration` (personal/OSS repositories may
  canonically live beneath `~/Projects/personal/`);
- `git config user.name` is `bigstupid007`;
- `git config user.email` is `monkey.nfm@gmail.com`;
- the origin uses the `github-oss` SSH host;
- `gh-oss auth status` shows `bigstupid007` as the active account using the
  isolated `GH_CONFIG_DIR=$HOME/.config/gh-bigstupid007` profile.

Use `gh-oss` for this repository's Issues, pull requests, Actions, releases,
and other GitHub control-plane operations. Keep the normal `gh` profile and
the default `github.com` SSH behavior on `cdemichael`; do not switch, remove,
or rewrite that business identity while working on this repository.

Stop and report a mismatch instead of changing identity or remote settings
without explicit instruction.
