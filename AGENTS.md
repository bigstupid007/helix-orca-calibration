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

## Issue #2 development harness authority

`scripts/helix-dev` is the authority for the pinned HelixScreen
`v1.1.0-beta.4` native mock-printer loop, trusted-LAN review, hot-reload proof,
and eleven-target capture matrix. Preserve these boundaries:

- the Helix container runs `--test`, Docker `--network none`, a private control
  socket, and read-only runtime/plugin mounts, never `--real-moonraker`;
- the browser viewer at reserved devbox port `8540` displays native Helix
  screenshots and forwards only bounded native input/navigation actions; it is
  development infrastructure, not product UI;
- runtime assets live in the user cache and generated evidence in XDG state by
  default, never in an Issue-specific `/tmp` dependency;
- durable bootstrap must build the exact pinned public source and recursive
  submodule revisions after short-lived upstream artifacts expire; an Actions
  artifact may be only an optional SHA-verified accelerator;
- only a complete passing capture may be explicitly promoted beneath
  `docs/evidence/`, and `./scripts/helix-dev verify-evidence
  docs/evidence/issue-2/native` must bind it to the exact harness/CI candidate,
  product hashes, viewport matrix, and screenshots; and
- harness changes must not modify `helix-plugin/orcacal/` product behavior or
  weaken the deferred Moonraker/G-code/print/writeback boundary.

## Issue #4 Temperature round-trip authority

Issue #4 replaces the earlier unlaunched interactive-picker plan. First qualify
the fixed 2026-10-11 Windows x64 Orca nightly at commit
`210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3` in a separate `--datadir`. The
qualification must run in the actual Windows GUI and prove the existing
read-only context plugin, saved versus edited/effective profile values,
lifecycle payloads, an Orca-owned dock panel, and a normally prepared/exported
Temperature file. Linux, Wine, source-only, or headless CI evidence cannot pass
that gate.

Qualification and evidence tooling may drive the isolated Orca/Helix UIs to
reproduce operator actions and capture proof. That is test infrastructure, not
shipping product behavior. Product code must not automate Orca's UI or invoke
unsupported slicing/export APIs. Prefer an Orca-owned dock panel, but retain a
host-owned modeless-window fallback. Prefer lifecycle file association, but
retain explicit manual file selection when it is missing or ambiguous.

Do not implement the round trip until the qualification evidence passes. Once
it passes, the approved scope is one Temperature round trip using normal manual
Orca calibration preparation/export, reliable lifecycle events plus explicit
file association, and manual file selection as a fallback. Keep the original
target-profile context separate from test-only preparation settings. Receiving
a test must never start printing. Returned instructions must identify the exact
profile, setting, original value, selected value, and `not applied` state.

Use Preston's `calibration-bridge` pinned at
`ed8d0c4977873969613fcb49024109ff7df7d84e` without modifying upstream. Preserve
the accepted Helix native shell and existing harness isolation. Cover profile
switching, stale/duplicate results, and failed delivery in the isolated mock
integration setup. That setup may simulate the complete mock print lifecycle
needed to prove request delivery, progress/completion, result correlation,
failure, retry, and recovery, but it must expose no physical-printer route and
does not authorize real print control. No physical-printer access, profile
writes, public exposure, new remote access, upstream changes, custom G-code
generator, product UI automation, or expanded picker/profile-browser scope is
approved. The interactive Temperature picker remains a deferred requirement.

`plugin/helix_calibration.py` remains one dependency-free side-loaded Orca
plugin. It may read Orca's supported host APIs and write only explicit evidence
or bounded round-trip artifacts below host-provided plugin storage. Preserve
saved preset identity, the edited copy, and merged effective values as distinct
sources. Reference checkouts remain read-only.

The canonical devbox owns implementation, Git, and evidence assembly. Spare
is the intended interactive Windows qualification target; LAPTOP-EC83OFDE is
not this workstream's target. Windows is a target-validation environment reached
through the founder-approved LAN-only testing access between devbox and Spare.
Approval on 2026-10-11 permits the minimum secure command/interactive GUI route;
no Tailscale, public exposure, new account, or unnecessary security change.
Prefer the unelevated reverse worker over the existing LAN SSH connection in
`docs/SPARE_TEST_ACCESS.md`; no inbound Windows service/firewall change is
needed. Do not author or branch on Windows or broaden this access envelope.
The first local worker launch is owner-only when no execution route exists;
the agent owns subsequent setup, qualification, and evidence collection.

## Issue #6 display-only private-LAN increment

[Issue #6](https://github.com/bigstupid007/helix-orca-calibration/issues/6)
authorizes a narrow increment beyond Issue #4 for the owner-confirmed Voron on
the existing private LAN. It permits normal Orca preparation and **Upload**
file transfer, a permissionless HelixScreen display plugin, and one transient
Moonraker agent event whose only effect is a receipt that the user can dismiss.
It does not permit Upload and Print, print start or queue, heat, motion, homing,
macros, calibration completion claims, result application, profile writeback,
firmware or service changes, Moonraker configuration changes, new credentials,
unknown-host trust bypass, public access, or production deployment.

Keep the Issue #4 mock bridge, event namespace, artifacts, and beta.4 harness
unchanged. The physical display path uses plugin ID `helix-orca-display`, event
`helix_orca_display.available.v1`, schema `helix-orca-display/v1`, and required
`display_only: true`. It must never emit `helixcal.*`. The plugin has no
permissions, widgets, settings, print controls, or network calls. It displays
the retained original Orca context, exact transferred file identity, original
effective temperature, prepared range, and request-scoped
`Received · not printed · not applied` state, with Dismiss as its only action.

Before an actual display event, use normal Orca's explicit Upload-only action,
prove `print=false` and no printer-start route, read the uploaded file back,
and bind those exact bytes through the native retained-context file chooser.
Recheck target identity and idle print state immediately before transfer/event.
Stage only the uniquely owned plugin folder through HelixScreen's supported
`config/helixscreen/plugins/<id>/` route. HelixScreen never auto-enables a new
plugin; the owner enables it on the physical screen. Rollback removes only that
owned folder after the plugin is disabled. Do not write Helix enabled-state or
printer configuration files remotely.

Before founder acceptance, keep the Issue #6 candidate unmerged. Freeze one
bounded candidate, obtain a fresh-context read-only GPT-5.6 Sol / High review,
resolve material findings, and leave one guided-review pull request. Exact
Windows and physical-screen observations are required for the surfaces they
claim; Linux/source evidence cannot be relabeled as Windows or hardware
qualification.

Founder accepted Issue #6 and PR #7 on 2026-10-15 (America/Chicago) as the
completed display-only real-HelixScreen milestone and explicitly authorized
governed merge, main verification, and Issue closure. This supersedes the
prior keep-unmerged gate for PR #7 only. Acceptance covers normal Orca
Upload-only transfer, exact file/context binding, the permissionless display
plugin, one transient receipt event, and owner-observed Dismiss. It does not
authorize a real result-return path, print, queue, heating, motion, profile
writeback, service/security changes, public access, release, or deployment.
Visual polish is deferred until the complete integration workflow functions;
the accepted shell, profiles, and mock harness remain preserved.

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

## Issue #4 candidate review

The governing Issue requires one fresh-context read-only independent reviewer
at the frozen candidate boundary. Use that bounded reviewer under the current
shared Development System authority; only the lead integrates corrections.
The frozen candidate completed independent review and AI Product Preflight.
Founder accepted Issue #4 and PR #5 as a completed mock-only technical proof of
concept on 2026-10-12 (America/Chicago), explicitly authorizing governed merge,
main verification and Issue closure. This supersedes the prior keep-unmerged
gate for PR #5 only. Additional UX polish is deferred in `docs/backlog.md`.
Hardware access, production transport, real-print control, profile writes,
release and deployment remain prohibited; acceptance grants none of them.

## Issue #8 bidirectional communication candidate

The initiating founder instruction on 2026-10-16 and
[Build Program #8](https://github.com/bigstupid007/helix-orca-calibration/issues/8)
authorize one correlated real Temperature request and simulated-selection
return, without printing. Preserve accepted source/evidence: generate the new
beta.9 `orcacal` derivative from the unchanged chooser/detail baseline and the
new single-file Orca derivative from the unchanged qualified October 15 source.
Keep the Issue #4 mock bridge, beta.4 harness, and Issue #6 display plugin and
namespace unchanged. Do not introduce another native shell.

The native candidate requests only `storage`. Its request and acknowledgement
events use the separate `helix_orca_temperature.*.v1` namespace. Storage return
is read through only its exact existing config-file path, then relayed through
the existing authenticated Spare worker. The Orca plugin performs only bounded
local artifact I/O below host-provided storage during supported UI callbacks;
it has no networking, process execution, background threads or profile writes.
Only an originating-companion committed receipt may acknowledge delivery.

The physical-hop security decision remains pending: existing trusted-LAN HTTP
is not encrypted or per-message cryptographically authenticated. No new
physical event/write may occur until that boundary is explicitly resolved.
New credentials/services, security/configuration changes, unknown-host bypass,
print/queue/heat/motion/homing/macros, firmware, profile writes, public access,
merge, release and deployment remain outside this candidate's authority.
Owner storage consent/enablement must never be written remotely.

Use the exact beta.9 native matrix and October 15 Windows build for claims on
those surfaces. Preserve private target data and disclose isolated versus
physical evidence honestly. One fresh-context independent candidate review, AI
Product Preflight, reconciled documentation and one unmerged PR are required;
never label an AI run Founder acceptance.
