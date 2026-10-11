# Issue #1 native runtime acceptance

Date: 2026-10-10

The reusable chooser/Temperature candidate passed isolated native mock-printer
testing against HelixScreen `v1.1.0-beta.4` at commit
`13a77bec42616d5c6f4fa397f1d5e12682fa4376`.

The capability and viewport preflight was completed before implementation and
is recorded in [`CAPABILITY_PREFLIGHT.md`](CAPABILITY_PREFLIGHT.md).

## Test authority and isolation

- Binary: official `helix-screen-ubuntu-22.04` artifact from successful
  upstream Build run `37385776288`.
- Binary SHA-256:
  `ab819714fd469ff32657dc974585ad3bb05270829247da08eb71161a2d5197d0`.
- Runtime: native x86-64 binary inside an Ubuntu 22.04 image with local digest
  `sha256:0d79be9b45c1da3b945e960dd386cabac8bf849d249dc4a5385d6c2051df2ab6`.
- Isolation: Docker `--network none`; plugin and beta.4 release data mounted
  read-only; unique config directory and control socket for every viewport.
- Invocation: `--test --skip-wizard --skip-splash --dark --no-sound -vv`, SDL
  dummy video/audio, software rendering, explicit size/layout/DPI, and
  `HELIX_PLUGIN_DIR=/plugin`.
- Enabled-plugin record: version `0.2.0`, empty permissions, with the accepted
  `orcacal__tile` placement on its own native Home page.

The original Issue #1 closeout used
`/tmp/orcacal-issue1-closeout.BbJLnb`. Issue #2 replaces that ephemeral,
machine-specific procedure with the reproducible repository command
`./scripts/helix-dev capture`. Full generated artifacts now persist beneath
`~/.local/state/helix-orca-calibration/helix-dev/captures/`; a bounded durable
matrix, report, and the initial landing plus final native frame per target are
versioned beneath
[`../docs/evidence/issue-2/`](../docs/evidence/issue-2/).
That replacement can build the exact pinned source after the short-lived
Actions artifact expires, and promoted evidence is rejected unless its
capture-time candidate, product, matrix, and frame hashes still match.

## Runtime matrix

| Viewport | Layout / DPI | Result |
| --- | --- | --- |
| 480x272 | standard / 160 | PASS |
| 272x480 | portrait / 160 | PASS |
| 480x320 | standard / 160 | PASS |
| 480x400 | standard / 160 | PASS |
| 800x480 | standard / 160 | PASS |
| 480x800 | portrait / 160 | PASS |
| 1024x600 | standard / 160 | PASS |
| 1280x720 | standard / 160 | PASS |
| 1080x2400 | portrait / 405 | PASS |
| 1920x480 | ultrawide / 160 | PASS |
| 320x1480 | portrait / 160 | PASS |

At every size the harness proved:

- `[PluginHost] orcacal: loaded` after discovery and persisted enablement;
- native state lands on physical Home page zero with the complete tile visible;
- a screen-coordinate native pointer tap opens `orcacal__wizard`;
- chooser XML exposes native Back and the Temperature row;
- selecting Temperature pushes `orcacal__temperature` as the second native
  overlay;
- every measured plugin descendant remains inside the horizontal viewport and
  reports no positive left/right scroll extent;
- **Start** can be scrolled into view where needed, accepts a native pointer
  tap, and emits the exact native toast `Calibration request test`;
- Back pops Temperature to the chooser and the chooser to Home; and
- Helix's normal Home action keeps the tile visible and a second native pointer
  tap reopens the chooser after the stack closes.

This stronger gate repairs the Issue #2 Founder Review defect. The rejected
harness put the tile on retained carousel page 1 even though beta.4's normal
Home action always selects physical page 0, then used object-name clicks that
could activate the off-screen widget. The repaired mock configuration uses one
deterministic page-zero layout and the capture path uses the same pointer input
as the review viewer. The Issue #1 plugin files remain byte-identical.

Visual inspection of the smallest landscape, smallest portrait, narrow-tall,
high-DPI phone, default, and ultrawide captures confirms native Helix headers,
navigation placement, dark tokens, compact cards, typography, and controls.
There is no custom sidebar/workspace, fake application navigation,
Generate/Run/Result stage, Apply-to-Orca control, or future-module placeholder.

The authorized final polish retained all four context values but combined them
into two responsive lines with smaller native padding. Runtime geometry measured
the context card shrinking from 150 to 90 px at 800x480, from 98 to 59 px at
480x272, 272x480, and 320x1480, and from 394 to 227 px at 1080x2400/405 DPI.
The Temperature screenshots before and after the polish are byte-identical at
800x480 and 272x480, confirming that its range-and-Start surface did not change.

## Automated policy result

Issue #1's exact commit contains seven tests in `tests/test_helix_plugin.py`.
The closeout command reported 25 because the dirty canonical checkout also
contained 18 unrelated, uncommitted Orca diagnostic tests. The seven Helix
tests validate the beta.4 manifest contract, closed XML allowlist,
plugin-owned names, native overlay/scroller structure, permissionless Lua
handler coverage, fixed context and Temperature content, and absence of
unsupported visible features. Issue #2 adds fifteen committed harness tests;
its candidate CI suite therefore contains 22 tests.

## Verdict

Issue #1 is the closed native beta.4 mock-printer baseline for future
calibration modules. Issue #2 makes that acceptance procedure reproducible but
does not change the product. Neither is real-printer execution acceptance:
Moonraker coordination, G-code, print control/monitoring, results, and Orca
writeback remain unimplemented and out of scope.
