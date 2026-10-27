# Architecture

> **Current V1 architecture:** Issue #14's October 25 amendment layers a
> beta.12-native five-calibration product, current Orca build/route-qualified
> generation, printer-neutral exact-job execution, official originating-preset
> transactions, and an owner-local runtime on top of the preserved Issue #1/#12
> foundations below. [Current architecture authority](V1_CURRENT_UPSTREAM_REBASE.md).

## Issue #1 HelixScreen foundation

`helix-plugin/orcacal/` is an independent permissionless Lua plugin for the
stock framework introduced in HelixScreen `v1.1.0-beta.4`.

The runtime flow is:

1. Helix owns and renders the `orcacal__tile` home widget.
2. The tile's `open` event pushes `orcacal__wizard` through
   `helix.ui.overlay()`.
3. The chooser reads the local `CALIBRATIONS` registry and its Temperature row
   pushes `orcacal__temperature` as a second native overlay.
4. Helix's inherited Back control pops Temperature to the chooser and the
   chooser to Home.
5. **Start** calls only `helix.ui.toast("Calibration request test")`.

The registry maps a calibration ID to a plugin-owned detail component.
Temperature is the only current entry. The chooser's shared context is a
compact, non-interactive two-line card above the dominant calibration list.
Future modules add registry entries and native detail components to this same
shell; they do not introduce alternate navigation, application chrome, or
speculative workflow UI.

The XML uses only beta.4's plugin allowlist: native `overlay_panel`, `ui_card`,
semantic text, built-in icons, `lv_*` objects, and Helix design tokens.
`overlay_panel` owns the header, Back behavior, full-height surface, and native
navigation integration. Each plugin overlay owns one flexible vertical
scroller; horizontal overflow is not used.

The fixed development context is presentation data only. The plugin requests
no permissions and has no Moonraker, G-code, HTTP, storage, slicing, print,
monitoring, result, or Orca communication path.

The exact capability/viewport contract is in
[`../helix-plugin/CAPABILITY_PREFLIGHT.md`](../helix-plugin/CAPABILITY_PREFLIGHT.md),
and native runtime evidence is in
[`../helix-plugin/PREFLIGHT.md`](../helix-plugin/PREFLIGHT.md).

## Issue #2 native development boundary

`scripts/helix-dev` is development infrastructure around the accepted plugin;
it is not another product surface. Its bootstrap verifies a pinned beta.4
source tag/commit, developer binary, release-data archive, and image labels,
then retains them in the user cache.

Interactive mode has two processes:

1. The official beta.4 developer binary runs in an immutable Ubuntu container
   with Helix `--test`, SDL dummy rendering, a private Unix control socket, the
   current plugin mounted read-only through `HELIX_PLUGIN_DIR`, and Docker
   networking disabled.
2. A dependency-free host viewer on reserved trusted-LAN port `8540` requests
   native Helix screenshots and forwards only bounded tap/Home/Back/capture
   actions to that private control socket.

The viewer draws no imitation Orca or Helix interface. Product pixels,
navigation, callbacks, layout, and input dispatch all remain owned by the real
runtime. The host listener cannot connect the container to Moonraker and does
not expose a shell or arbitrary helixctl command.

Capture mode gives every target size its own config and control socket, drives
the complete accepted flow, and records capture-time candidate, product, and
frame hashes to prove exactly what ran and that the product plugin was not
changed. Generated artifacts stay in durable XDG state by default; explicit
promotion retains only the report, matrix, and one final native frame per target
under `docs/evidence/issue-2/`.

GitHub CI covers deterministic Python/XML/manifest/harness policy and verifies
the bounded promoted evidence against the checked-out candidate. Native runtime
capture remains a devbox gate because an exact source build and eleven native
viewport runs are intentionally too heavy for proportionate per-commit CI.

## Issue #4 qualification and host boundary

The canonical implementation checkout remains
`/home/dev/Projects/personal/helix-orca-calibration` on devbox. The existing
`codex/issue-4-temperature-round-trip` worktree isolates Issue #4 from unrelated
canonical changes. Spare is the intended Windows runtime-validation target;
LAPTOP-EC83OFDE is outside this workstream.

Windows setup, isolated runtime execution, and capture use the founder-approved
LAN-only access envelope. A prepared unelevated Windows worker carries command
requests through the existing outbound SSH connection to a private devbox Unix
socket. It needs no Windows listener, service, firewall change, or Tailscale.
The worker executes inside the visible desktop. Commands and a native GUI click
were proven there. The restarted worker passed an actual inherited-pipe capture
regression in 2.11 seconds and remained connected. Transport details
and operational boundaries are in [`SPARE_TEST_ACCESS.md`](SPARE_TEST_ACCESS.md). Source/tests and
devbox execution cannot satisfy the Windows gate. The fixed nightly must use
its own portable directory and marked `--datadir`, preserving the normal Orca
installation and profiles. `WEBVIEW2_USER_DATA_FOLDER` is set only in the
nightly child environment: `--datadir` alone reused normal Orca browser data.
Separate browser process ancestry and data storage were verified after relaunch.
The qualification gate passed after the supported offline local bundle importer
resolved the System-name collision with unchanged fixture JSON. Runtime context
records the original printer's bundle identity and `is_system=false`, while
saved 220, edited 217 and merged 217 remain separate. Normal Temperature
preparation used a separately retained temporary context. Manual selection of
the actual export is required because the lifecycle path is temporary slicing
output. All 1,429 normal settings/profile files remained unchanged after close.

Prefer the Orca-owned dock panel and lifecycle file association. If necessary,
qualify a host-owned modeless window and explicit manual file selection under
the approved Issue #4 fallback authority. UI driving belongs only to isolated
evidence tooling. The mock-only Temperature round trip now proceeds from the completed
actual Windows observations in
[`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md).

## Issue #4 bounded round-trip implementation

The self-contained Orca `0.4.0` companion freezes the original supported-API
context separately from live selection/settings, verifies a manually selected
file in its host-owned browser, and explicitly writes one immutable request
under plugin storage. Returned JSON must match request, context, file, printer,
filament, current/saved values and setting; duplicates are idempotent, conflicts
and stale results are rejected. Instructions state **not applied**. There is no
network, process/thread, slice hook, UI automation or preset-write path in the
Orca plugin. Lifecycle callbacks notify the page; host reads run through its
supported UI message callback. Modeless fallback remains available.

The separately mounted development bridge uses pinned native overlays,
subjects, plugin storage and mock print APIs. Beta.4 forbids HTTP to local
printer-host addresses, so the proof preserves that protection and transports
real artifacts through existing SSH and supported native storage. Native
request receipt never starts printing. Docker `--network none` and `--test`
prevent any physical route. The accepted product and ordinary harness are
unchanged. All eleven sizes and actual Spare result reception pass; see
[TEMPERATURE_ROUND_TRIP.md](TEMPERATURE_ROUND_TRIP.md).

The separate proof viewer adds bounded native drag input and a single guarded
mock-completion action. Completion requires an already started request in the
owned `--test`, network-none container; it cannot start printing. Native context
labels identify effective values explicitly. Evidence binds the executed
source-built binary and provenance, per-viewport binary hashes, and the imported
ordinary harness in addition to the round-trip sources.


The consolidated Founder Review repair supplies a proof-only native Home resume
tile and restores the stock print-status card, while preserving normal native
Home/Back semantics. Native Finish writes a correlated storage action; the
owned mock driver validates and consumes it. The viewer makes the same existing
completion action prominent and responsive. This changes only mock integration
and review infrastructure, never the accepted shell or upstream navigation.

The proof parks beta.4's synthetic clock before the remote pointer is created,
after a stable entry frame. This keeps completion from being overwritten by
later simulator snapshots. Navigation/update/render queues and the later-created
remote input sampler stay live; pre-existing periodic timers and animations are
paused only in this test runtime. Fresh browser proof verifies both Finish
surfaces and native Home/Back/task return through the terminal 205°C result.


The companion presentation now leads with the validated result and manual
update steps. Calibration-start effective temperature remains separate from
the live current effective value and its currently selected filament. A
selection/settings warning prevents interpreting another profile's live value
as the original target. Preparation/import controls and diagnostic provenance
remain in expandable sections; no reader, callback, request/result guard or
write boundary changed. The focused companion report binds current source and
actual Windows reception, while retaining the original native capture hashes.
An AST contract check permits only the companion HTML assignment to differ
from the qualified plugin. No Helix matrix recapture is implied by this UI-only
change.

Founder accepted the completed Issue #4 / PR #5 mock-only technical proof on
2026-10-12 (America/Chicago) and authorized governed merge and closeout. This
documentation-only closeout changes no architecture or runtime boundary.
Additional UX polish is deferred in `backlog.md`; physical-printer routes,
production use, real-print control and Orca profile writes remain prohibited.

## Issue #6 display-only physical delivery

Issue #6 adds a separate physical display path without changing the accepted
Issue #4 mock bridge, `helixcal.*` event contract, or beta.4 harness. The pinned
October 15 Orca derivative adds only the exact qualified build identity. Normal
Orca performs the Upload-only transfer, and the retained request binds the
original profile context to a readback of the exact transferred bytes.

`integration/helix-orca-display/` is a permissionless HelixScreen plugin with
no widgets, settings, network calls, or printer actions. It subscribes only to
`helix_orca_display.available.v1`, requires the `helix-orca-display/v1` schema
and `display_only: true`, renders a native receipt, and exposes Dismiss as its
only action. The short-lived client enforces exact-host and nonactive preflight,
bounded file readback, an absolute transport deadline, bounded frames, and an
RPC allowlist limited to identification and the one display event.

After independent review, the approved path transferred one file through
normal Orca, staged the permissionless plugin through HelixScreen's supported
plugin directory, and sent exactly one display-only event. The owner observed
the expected receipt and Dismiss behavior. This proves the bounded physical
display path only. Print, queue, heating, motion, measurement, profile
writeback, service/security changes, and public access remain outside the
architecture, while the real result-return path remains mock-only.

Founder accepted Issue #6 and PR #7 on 2026-10-15 (America/Chicago) and
authorized governed merge and closeout. Receipt and workflow polish is deferred
until the complete Orca-to-Helix-to-Orca integration functions.

## Issue #8 accepted communication boundary

The accepted source trees remain immutable. New generators derive an Orca
`0.5.0` single-file plugin and beta.9 `orcacal` runtime outside the repository.
The native derivative extends the existing chooser/Temperature shell and
requests only `storage`; it adds no print lifecycle, new module, second shell
or network permission. The Orca derivative retains all accepted capabilities
and adds an Orca-owned communication dock/modeless fallback. Its JavaScript
posts poll messages; Python callbacks read/write fixed local artifacts below
host plugin storage. It opens no network/process/thread and never writes a
profile.

The bounded route is originating Orca outbox -> existing authenticated
Spare worker -> transient Moonraker request event -> native Temperature detail
-> plugin-owned storage -> exact Moonraker config-file GET -> Spare inbox.
Orca validates and commits the exact result before producing the receipt used
for the native acknowledgement. Request/origin IDs, full retained-context
digest, flattened source equality, filename/size/SHA-256, prepared choices,
expiry and immutable first selection are checked independently.

The existing physical HTTP hop relies on trusted-client LAN authorization.
Correlation and replay checks do not provide encryption or malicious-LAN
authentication. The founder explicitly approved the existing trusted-LAN
boundary for this proof, as recorded in
[Issue #8's program](BUILD_PROGRAM_TEMPERATURE_COMMUNICATION.md). The existing
SSH worker protects the Spare hop; no new service, port or credential is part
of this candidate. Details and recovery are in
[TEMPERATURE_COMMUNICATION.md](TEMPERATURE_COMMUNICATION.md).

The immutable session is wrapped in a target-eventtime lease. Native receive,
recovery, Return and ACK requery finite eventtime and nonactive print state; a
bounded latency charge and remaining-time margin protect deferred writes.
Retries and restarts may only shorten the stored deadline. Local Orca result
commit preserves the slot until exact native acknowledgement is confirmed
and durably recorded, or explicit retirement after original absolute expiry.

The initial production attempt exposed beta.9's per-file settings symlink:
native storage stays under installation config, outside the shared config
route. The owner explicitly approved and applied one real shared directory and
one exact file link to native `orcacal.json`. Existing authenticated GET now
observes native atomic replacements, including the fresh actual persisted
return and ACK. No directory-wide link, access-mode, service, credential or
plugin permission change was made. See the
[storage amendment](TEMPERATURE_COMMUNICATION_STORAGE_GATE.md).

Receipt-driven redelivery is bounded to five sends across restart and stops on
exact native persistence. Lua omits a pending nil result; only unacknowledged
received state may omit that key. Final actual evidence proves the same
immutable request/result/receipt across both directions and completed delivery
before expiry. The completed relay exits; this is bounded qualification
infrastructure, not a new installed service.

Founder accepted the actual original-profile 220°C / simulated 205°C /
NOT APPLIED result on 2026-10-16 and authorized PR #9 merge/main verification/
Issue #8 closure. [The acceptance record](ISSUE_8_ACCEPTANCE.md) separates that
product decision from the prior technical/AI proof. Closeout changes docs only;
no runtime architecture, transport permission, profile behavior or hardware
capability changes. Deferred UX is backlog work, with no broader deployment.


## Issue #10 isolated Alpha compatibility layer

The accepted October 15 implementation and physical relay remain unchanged.
`scripts/orca-alpha-companion.py` derives an Alpha-only `0.5.1` single-file
artifact from hash-verified accepted `0.5.0` bytes. It changes target metadata,
exact runtime admission and the embedded runtime-validation/probe constants;
request/result schemas, original-context digest binding, UI behavior and
receipt/recovery guards remain intact. `scripts/orca-alpha-windows-review.py`
reuses pinned native review guards for only the new Alpha executable/datadir.
It creates no service, access route or physical-printer transport.

Source compatibility does not override runtime gates. The accepted physical
relay deliberately rejects an Alpha outbox; this qualification neither changes
that gate nor repeats physical communication. [Qualification status](ORCA_ALPHA_QUALIFICATION.md)
records passed actual Windows/context/export/result/recovery checks, the isolated
native fixture and the distinction from the accepted physical workflow. Native
return selection and Alpha receipt use unchanged v1 contracts; no fresh physical
ACK/delivery or baseline adoption is implied.

Founder accepted this qualification on 2026-10-16. October 15 nightly remains
the preferred development and physical-integration baseline; Alpha with
companion 0.5.1 is a qualified secondary target. PR #11 merge/closeout authority
changes no runtime gate or architecture. Alpha physical integration and
production adoption remain unauthorized. See [acceptance](ISSUE_10_ACCEPTANCE.md).


## Issue #12 pre-physical readiness architecture — historical c1eee43

The new `integration/temperature-print/` path and `temperature-print-*`
generators are separate from accepted Issue #8 source. The Orca derivative
uses local `print-readiness` artifacts, a separate wire namespace and exactly
three choices. Its original saved/edited/effective target remains immutable;
results carry the independently confirmed job/proof identity and return NOT
APPLIED instructions. The native derivative reuses the accepted chooser/detail
shell and storage permission, writing one-shot Start/cancel intents only from
native UI callbacks. It never invokes a print RPC.

The transport-independent coordinator journals before any dispatch, never
retries an ambiguous start/cancel, and corroborates same-job print_stats with
Moonraker history. Physical identity is a local MCU/host binding, distinct from
the Orca saved-preset label. The future adapter pins both that identity and the
reviewed configuration and defaults to actions disabled. No live orchestration,
permit issuance, hardware activation or physical derivative installation occurs
in this build. [Readiness authority](BUILD_PROGRAM_TEMPERATURE_PRINT.md) controls
this increment; [the report](TEMPERATURE_PRINT_READINESS.md) owns current validation.
The 2026-10-17 correction fixes choices to 225/220/215°C and treats the native
estimate as information, with no print-length ceiling or combined-time input.
The filament is confirmed at normal 220°C; no new label checkpoint exists.
Request/command freshness limits remain independent of the estimate. A healthy
correlated job is not failed merely for exceeding its native time estimate.

Post-Start monitoring has no request-TTL or runner-duration cutoff. The 900-second
Start window and original request/grant expiry still prohibit late dispatch;
fresh machine/configuration/status and exact owned-job history govern an active
job, including recovery, cancellation, completion and result return. A durable
request-scoped `delivery.json` lifecycle marker is written before dispatch, so
the originating companion cannot abandon a started or uncertain session merely
because its original TTL elapsed. Only an expired unstarted or terminal slot
may retire. Post-expiry results still require the retained exact identity and
independently confirmed job/proof; they cannot retarget a newer request.

Initial print_stats may precede metadata/history. Missing or previous metadata
and an explicit 404 remain pending inside the original 30-second confirmation
deadline, without ownership, cancellation, selection or redispatch. Contradictory
proof, unexpected jobs, transport failures and deadline expiry remain locked.
Deterministic preflight/authorization rejection consumes the tap and publishes
failure; an ambiguous command publishes uncertainty. The readiness protocol and
coordinator require original effective nozzle 220°C while preserving saved and
edited values independently. Accepted communication source is unchanged.

Current readiness proof binds the actual native Windows export to its original
220°C context and uses real companion receipts with isolated synthetic native
completion. Offline suitability resolves exported commands and unchanged macro
sources from GET-only target data; it issues no live grant. Accepted Windows
state is restored after qualification. See the readiness report for exact file
identity and preservation; no physical deployment is implied.


## Historical 7cc0b4d checkpoint — Issue #12 successful physical baseline and bounded UX follow-up

The actual Founder-initiated `c1eee43` print completed with independent same-job
history and returned 220°C NOT APPLIED; it is preserved separately from synthetic
UI capture. The compact generated derivative requests a fresh 1×1 home widget,
uses a small native tune icon, full identity and short lifecycle status, and
keeps existing chooser/detail navigation. It does not mutate saved home layout.
Committed waiting/returned results ignore later statuses and liveness changes;
at the native UI boundary, an already-emitted exact acknowledgement confirms
that immutable selection independently of a later printer job. The unchanged
coordinator/relay still enforce their live correlation checks before emitting
an ACK; this does not claim new end-to-end delivery after job replacement.
Before selection, all completion/job/context guards remain.

Automatic presentation over arbitrary pages is blocked by beta.9's missing
modal-aware presentation contract. Plugin overlays can cover native modal
backdrops; the documented API cannot observe or defer safely around them.
No unsupported navigation, blind delay, upstream patch or physical deployment
is introduced. See `docs/ISSUE_12_COMPLETION_UX_API_GATE.md`.

## Issue #12 current immediate-overlay authority

The later direct Founder instruction explicitly accepts temporary overlap with
an existing native dialog for this controlled personal-printer test. The earlier
beta.9 modal-lifecycle findings remain true but no longer block immediate
`helix.ui.overlay()` use. An isolated presentation adapter now claims one attempt
only after accepted exact-job success. Runtime arming plus a persisted claim
suppresses duplicates/restart, including conservative manual recovery when a
crash may have lost a deferred claim write. Dismissal retains selection and the
normal tile → Temperature reopening path. Original live return/recovery gates,
1×1 tile, context/NOT APPLIED and physical baseline remain unchanged. Renewed
native synthetic proof is separate from real hardware success. Queued-overlay
migration remains future work. Later separately authorized deployment and
physical execution succeeded; no further deployment or physical action is
authorized by closeout. Current semantics: `ISSUE_12_COMPLETION_UX_API_GATE.md`.

The automatic component shares the exact Temperature layout/bindings/actions
with distinct owned widget names. After its successful push, only tracked plugin
preparation views retire; native pages/dialogs remain, and backing out cannot
resurface an old manual chooser. The source-bound test includes buried manual
Temperature under Print Status at every size and manual Temperature on top at
800×480. No new navigation API or notification setting is used.

## Issue #12 accepted physical outcome and stop boundary

Founder accepted the actual final print, automatic native Temperature chooser
and original-context 220°C / NOT APPLIED return on 2026-10-18. Independent job
history, bound native result and original receipt/delivery agree. Installed
f7562bf / 0.4.3-issue12-auto, owner-saved 1×1 tile and rollback material remain
preserved. Closeout is documentation/evidence only; it does not change product
or printer settings. Normal native thermal/spool/start-history accounting is
retained. Hardware observations remain separate from synthetic coverage.
See [acceptance](ISSUE_12_ACCEPTANCE.md) for exact scope and proof limits.

After merge/main verification and Issue closure, stop implementation. A fresh
Founder-led review of the overall product goal comes next; no successor build
or further physical action is implied.


## Issue #14 V1 candidate architecture

The approved V1 redesign is an isolated derivative of the accepted native shell
and self-contained October 15 Orca plugin. Native UI persists only correlated
requests/intents/results; Orca captures saved/edited/effective snapshots through
verified host APIs and performs bounded local artifact I/O. Neither plugin runs
processes, slices, networks or writes profiles. The external local coordinator
owns durable jobs, explicit generator configuration, stock subprocess execution,
parity re-verification and original-context result/receipt correlation. It does
not depend on the Spare testing worker. The review launcher supplies no action-enabled physical
adapter; direct events/storage transport is candidate code, not a
production deployment/security qualification.

Stock CLI recipes and grouped native engine reuse are separate generator
adapters, not separate product shells. Every generated job requires independent
native-UI reference provenance and matching build/profile/parameter evidence.
Slice success is not qualification. See [contracts](V1_CONTRACT.md),
[runtime](V1_RUNTIME.md), [parity](V1_GENERATION_PARITY.md) and
[native engine](V1_ENGINE_REUSE.md). Earlier accepted implementations/evidence
remain historical baseline; this candidate changes none of their installed
physical behavior or consumed physical authorizations.

The integrated correction path now binds atomic intent consumption to its durable
outcome, permits only read-only exact-job restart adoption, and reconciles native
restart without relaxing sequence checks. Same-job progress/elapsed are nullable
and cannot authorize evaluation. Windows lifecycle and local privacy checks run
against a complete source-fingerprinted closure. The bounded native reviewer is
separate test infrastructure: fixed private LAN, typed input, no physical adapter,
source/owner binding and exact managed cleanup. Its earlier synthetic completion
fixture belongs to historical evidence; current review uses the real coordinator.
Its clean-clone imports do not require the devbox lifecycle checkout.


Historical verification binds the earlier native UI to 396 frames across eleven
targets and its synthetic browser workflow to exact owner-bound cleanup. That
source-bound evidence does not qualify the changed parameter controls. The
Linux native engine uses a two-thread task arena as well as a persistent global
cap; these must agree with upstream's initialization barrier. A real PA artifact
exists but a retained-profile processor warning blocks Prepared and parity
remains false. Generator availability, actual generation, parity qualification
and physical deployment remain separate gates.


The functional parameter correction uses a plugin-owned native numeric keypad
because the pinned plugin allowlist does not expose the app text-input widget.
The shared contract defines bounds/defaults; numeric fields are not finite test
picklists. Fixed YOLO modes select separate native assets/sample sets. Submitted
parameter scalars are copied, retained and validated through preparation/results.
The bounded viewer now delivers real Coordinator/DirectoryEvents events through
an explicitly test-only fragmented hook (beta.9 subjects have 1023-byte capacity).
It creates no prepared/completion fixtures. Captured context stays outside the
container mount; normal plugin/runtime networking boundaries remain unchanged.
Historical full-size fixture proof is preserved. The current acceptance gate is
focused 800×480 operator input through unchanged transport into the actual Windows
coordinator. All five exact requests, genuine qualified Flow Review, all14 healthy
captures and final managed/source verification pass in run
`b04728721c2741bd8d05b3001a343cdf`. No prepared/status fixture or physical adapter
participates in that focused proof.
