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

The founder explicitly approved “Use existing trusted-LAN boundary for this
proof” in the program chat. Existing physical-hop HTTP remains unencrypted and
without per-message cryptographic authentication; correlation protects against
accidental misdelivery, not a malicious LAN participant. This approval permits
the bounded physical proof through existing access.
New credentials/services, security/configuration changes, unknown-host bypass,
print/queue/heat/motion/homing/macros, firmware, profile writes, public access,
merge, release and deployment remain outside this candidate's authority.
Owner storage consent/enablement must never be written remotely.

Use the exact beta.9 native matrix and October 15 Windows build for claims on
those surfaces. Preserve private target data and disclose isolated versus
physical evidence honestly. One fresh-context independent candidate review, AI
Product Preflight, reconciled documentation and one unmerged PR are required;
never label an AI run Founder acceptance.

The initial Issue #8 physical attempt established forward context and owner
205°C selection only. Production sidecar storage lies outside the exposed
Moonraker config tree. The founder subsequently approved owner-run creation of one real
shared `plugin-data` directory and one `orcacal.json` file link to the existing
native state, through the existing authenticated trusted-LAN config API.
`scripts/temperature-communication-storage-link.py` implements only that
bounded amendment and defaults to a dry run. Existing owner local access is
required; this grants no agent SSH access, new credential, host-trust bypass,
access-mode change, directory-wide link, service or plugin permission.
The owner applied that exact bridge; authenticated readback and a fresh actual
round trip, persisted ACK, delivered status, independent review and AI Product
Preflight are now verified. Preserve the prior request/journal and never
retarget an expired result. This grants no wider change. Founder acceptance
and the exact PR #9 merge/closeout authority are recorded below; deployment
remains excluded. See
`docs/TEMPERATURE_COMMUNICATION_STORAGE_GATE.md` and
`docs/TEMPERATURE_COMMUNICATION.md#founder-review`.

## Issue #8 Founder acceptance and closeout

Founder accepted Issue #8 and PR #9 on 2026-10-16 (America/Chicago) as the
completed real bidirectional Temperature communication milestone. Founder
reviewed the completed actual Orca result and confirmed the exact original
profile/setting, 220°C context, simulated 205°C and NOT APPLIED instructions.
The same instruction authorizes documentation/deferred-UX reconciliation,
final safeguards, PR #9 merge, main verification and Issue #8 closure. This
supersedes the preceding unmerged/acceptance-open restriction for PR #9 only.

Closeout changes documentation only; accepted implementations, captured public
and private proof, normal Orca profiles and the canonical uncommitted work
must remain unchanged. Use the established merge-commit method, current green
checks and exact-head match; verify main in a clean detached worktree rather
than updating the dirty canonical main checkout. Preserve original evidence
and branch references; no physical rerun or cleanup is required. Record exact
merge/main outcome in the existing GitHub work items.

The trusted-LAN limitation, storage-only native permission, owner-only enablement
and exact approved single-file bridge remain unchanged. No physical printing,
queue, heating, motion, homing, macros, automatic profile update, firmware,
service/security/access change, wider exposure, new credentials, release or
broader printer deployment is authorized. Deferred UX work is backlog only.
See `docs/ISSUE_8_ACCEPTANCE.md`.

## Issue #10 official Orca Alpha compatibility qualification

The founder's 2026-10-16 instruction and Issue #10 authorize comparing official
`v2.5.0-alpha` source `3880f2c58ec392ed2bd5938ab31c9c7c496c0eb2` with qualified
October 15 nightly `6a7763f08d1a175a464a00ce13f0b5a815662fc4`. Stage only its
hash-verified portable x64 artifact in a separate marked Spare environment,
with separate settings and child-only WebView2 storage. Preserve normal Orca,
the accepted nightly, accepted source/artifacts and private operational proof.

A generated exact-runtime Alpha derivative and bounded qualification tooling
are allowed when required; retain truthful context/digest provenance and strict
v1 request/result safety. Do not weaken or modify accepted original runtime
gates, physical relay, native shell, harness or evidence. Use focused tests,
actual Windows UI proof and independent review. Reuse valid retained native/
communication evidence; do not manufacture another physical test. Separate
approval is required before consequential physical actions. No printing,
queue, heat, motion, profile writeback, new access/security change, deployment
or unrelated UX is authorized. Leave one reviewed unmerged PR and recommend
baseline policy; qualification alone does not adopt Alpha or authorize merge.
Owner-only desktop unlock remains required if Spare is locked. See
`docs/ORCA_ALPHA_QUALIFICATION.md`.

## Issue #10 Founder acceptance and closeout

Founder accepted Issue #10 and PR #11 on 2026-10-16 (America/Chicago) as the
completed OrcaSlicer 2.5.0 Alpha compatibility qualification, at reviewed head
`7c9078896a1f3dedaa91536b8388ccb29f5e4359`. The accepted policy keeps the
October 15 nightly as the preferred development and physical-integration
baseline; Alpha with companion 0.5.1 is a qualified secondary target only.
No Alpha physical integration or production adoption is authorized.

The same instruction authorizes acceptance/policy documentation, final
safeguards, PR #11 merge, main verification and Issue #10 closure. It supersedes
the earlier keep-unmerged restriction for PR #11 only. Closeout changes
documentation only: preserve accepted implementations, runtime isolation,
normal and copied profiles, private operational evidence and public capture
artifacts. Preserve the dirty canonical checkout through the existing separate
qualification worktree and a clean detached main-verification worktree.
Use the established merge-commit method, exact-head match and current green
checks without bypass. Record exact merge/main and closure results in the
existing PR/Issue; preserve branch references and earlier evidence.

The physical relay, printer configuration, security/access boundaries and
profile data must remain unchanged. No print, queue, heat, motion, homing,
macros, profile writeback, deployment, release, Alpha physical testing or
additional UX work is authorized. See `docs/ISSUE_10_ACCEPTANCE.md`.


## Issue #12 miniature physical Temperature readiness

The Founder instruction on 2026-10-16 (America/Chicago) and Issue #12 authorize
an isolated first-physical-test readiness candidate, one independently reviewed
unmerged PR, and a truthful readiness report. They authorize **no real print,
heating, motion, homing, macro execution or other consequential printer action**.
Separate explicit Founder review and physical-test authorization remain required.
No merge, deployment or production enablement is authorized.

The direct Founder correction on 2026-10-17 supersedes earlier AI constraints:
exactly THREE native Orca Temperature bands **225/220/215°C bottom to top**;
confirmed filament, normal nozzle **220°C**. Remove the hard 20-minute ceiling,
combined-time qualification requirement and spool-label approval checkpoint.
Print-time estimates are reported information, not duration gates. Preserve
request freshness, job monitoring, cancellation and failure recovery; do not fail
a healthy job merely because it exceeds the native estimate. Native Orca
preparation/slicing/export in the isolated October 15 nightly remains allowed;
no custom generator or hand-edited print G-code. Update the same Issue #12 /
PR #13 and return it reviewed, unmerged, ready for Founder Review. Physical
execution remains separately authorized. Alpha has no physical adoption.

Preserve all accepted sources/evidence, original profile context, normal Orca,
private payloads and the existing mock harness. New `temperature-print`
derivatives may extend the accepted native shell and local original-context
companion. The native plugin remains storage-only: explicit screen Start/cancel
writes a correlated intent; request receipt never dispatches a print. The
coordinator requires separate local authorization, exact reviewed configuration
and physical identity, byte-verified qualified output, a durable one-shot
intent and independent same-job status/history proof. Result selection remains
locked for failed, cancelled, disconnected, stale or uncertain jobs. Return
instructions remain NOT APPLIED; there is no profile writeback.

All implemented transports default to actions disabled. This program must not
activate the physical adapter, issue a live permit, upload/queue/start a file,
install the derivative on the printer, invoke a macro, or change access/config.
Read-only existing-target identity/status/config/history inspections are allowed
for offline suitability evidence; retain raw target data privately. Native UI
claims require the full pinned beta.9 eleven-size matrix with labeled synthetic
job/authorization/clock inputs. Do not relabel fixture success as physical proof.
See `docs/BUILD_PROGRAM_TEMPERATURE_PRINT.md` and
`docs/TEMPERATURE_PRINT_READINESS.md` for the candidate state and remaining gates.


## Issue #12 physical success and subsequent UX correction

Founder separately authorized one controlled physical test of exact PR #13
candidate `c1eee4374fb0286e1a3973d8e29107bfc64ee99f`, initiated only by the
physical HelixScreen Start. It completed with real independent same-job proof,
then returned the chosen 220°C to the original Orca context as NOT APPLIED.
Preserve that baseline, generated product/rollback files and private operational
evidence; the sanitized outcome is `docs/evidence/issue-12/physical-first/`.
This success does not authorize another physical test.

The subsequent Founder build instruction approves only two UX corrections in
Issue #12 / PR #13: automatic native Temperature result presentation after
verified owned success, respecting built-in modals/dismiss/reopen/recovery, and
a compact 1×1 native home widget retaining icon, readable identity/status and
tap-to-open. Verify exact documented beta.9 support first; no upstream patch or
unsupported navigation API is authorized. The independently verified modal-API
blocker is recorded in `docs/ISSUE_12_COMPLETION_UX_API_GATE.md`; do not substitute
a blind-delay popup. Complete and validate the independent supported widget
change without claiming the blocked automatic presentation is implemented.

Keep accepted baseline plugin sources and deployed physical components unchanged;
implement the compact widget only in the separate generated temperature-print
derivative. Synthetic native capture remains network-none/read-only and must
cover all eleven targets. Preserve committed result/receipt identity across
late statuses, duplicate delivery, disconnection and recovery. Return remains
NOT APPLIED. No new print, heat, motion, printer configuration, profile writeback,
physical deployment, upstream change, merge or release is authorized. Reconcile
documentation, the existing Issue/PR, independent review, Product Preflight and
exact-head CI, with physical evidence separated from synthetic UX proof.

## Issue #12 Founder-authorized immediate overlay test

The later direct Founder instruction supersedes the previous modal-coordination
blocker for this controlled personal-printer test. Implement automatic native
Temperature presentation through documented beta.9 `helix.ui.overlay()` after
existing independent exact-job success checks. Founder explicitly accepts the
temporary risk of appearing over an existing native dialog. Do not use a fixed
delay, change notification preferences or patch upstream. Keep the adapter
isolated for Preston's forthcoming queued-overlay API. Preserve dismiss/manual
reopen, at-most-once automatic attempts across duplicate events and recovery,
original context/NOT APPLIED, result/print safeguards and validated 1×1 tile.

The host defers storage writes; recover conservatively rather than resurrecting
a potentially presented completion. Pending results remain manually reachable
after fresh independent re-verification. Validate actual native presentation,
page independence, duplicates, dismissal/restart, lifecycle locks and all eleven
viewports; obtain fresh independent review, Product Preflight and exact-head CI.
Preserve physical baseline/evidence and prior captures. No new physical print,
deployment, firmware/configuration change, profile writeback or merge is approved.

## Issue #12 Founder acceptance and closeout

Founder accepted Issue #12 / PR #13 on 2026-10-18 as the completed physical
Temperature calibration milestone at tested `f7562bf2bd1f747f9fbc966425dec33e196e22c7`.
Founder confirms the final physical print, automatic chooser and successful
original-Orca NOT APPLIED return. Readback verifies selected 220°C and the exact
originating receipt/delivered status. The current instruction authorizes only
documentation/evidence reconciliation, required exact-head validation, governed
merge commit, clean detached main verification and Issue closure. It supersedes
the earlier keep-unmerged gate for PR #13 only; preserve branch references.

Preserve the installed 0.4.3-issue12-auto, working 1×1 saved widget, printer
configuration, original profiles/context, all accepted communication artifacts,
physical/synthetic evidence, rollback material and dirty canonical work. No
new print, upload, heat, motion, state reset, firmware/configuration/security
change, profile writeback, deployment or unrelated development is authorized.
Record normal native print accounting truthfully; never restore settings just
to make a pre-print snapshot identical. See `docs/ISSUE_12_ACCEPTANCE.md`.

After governed closeout, **stop implementation**. The next activity is a fresh
Founder-led review of the overall Helix–Orca product goal, not another build.
Deferred work remains unapproved; do not launch a new feature or calibration.
