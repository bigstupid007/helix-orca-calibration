# Helix-Orca Calibration

The functional parameter correction is implemented: editable native numeric
controls, both fixed YOLO modes, explicit PA defaults and retained request values.
Independent native800×480 input verified all five edited requests unchanged at
the actual Windows coordinator. All14 fresh captures and complete managed cleanup
pass; Perfectionist reaches genuine parity-qualified Review. Full Product Design
work remains deferred.
The historical 396-frame matrix and synthetic browser workflow do not qualify the
changed controls. [Current correction and acceptance gate](docs/V1_PARAMETER_CORRECTION.md).

## Active: integrated V1 Build Program #14

The Founder launched [V1 Build Program #14](https://github.com/bigstupid007/helix-orca-calibration/issues/14)
on 2026-10-18. It approves five calibrations, a Helix-first workflow, supporting
Orca companion, programmatic preparation, mandatory independent native-UI
G-code parity and a coordinator without Codex test-worker dependencies.
This supersedes the earlier stop-after-Temperature instruction for this program.
The accepted physical Temperature installation and evidence below remain intact.

V1 is an **integrated Founder Review candidate with verified functional controls**,
with blocking generator limits.
Stock Flow Ratio YOLO Recommended and Perfectionist pass strict executable and
calibration-invariant parity against separate independent October 15 Windows
references for their exact retained profiles and mode-specific parameters.
Temperature native geometry has a reproducible source-bound repair; direct
native generation still has material motion differences (net nine executable
commands) under investigation. The old stock candidate retains material differences.
The [grouped actual-generation diagnostic](docs/V1_GENERATOR_BLOCKER_CHECKPOINT.md#grouped-actual-generation-diagnostic)
uses four fresh independent Windows native UI references for a separately
captured, deliberately selected unsaved 50°C bed context. All four native and
Linux candidate invariant checks pass; PA Pattern, Retraction and Max Volumetric
Speed have exact executable digests. These diagnostics qualify no generator.
Actual Windows package execution and the complete unchanged parity harness
remain mandatory. The original bed 60°C / filament threshold 55°C combination
still produces legitimate warning `1000C001` and remains unsupported without
changing its profiles. The actual Windows package CI build is the next shared
infrastructure gate. The first actual Windows build completed all 25 dependencies
then exposed an Expat configuration conflict; the Windows-only repair and strict
explicit dependency checkpoint have independent source review and focused
checks. No new native generator is yet qualified.

The earlier native matrix passed all eleven sizes and 396 frames; its synthetic
browser workflow and exact browser/listener/container cleanup are retained as
historical evidence. They do not establish the new parameter controls. Earlier
combined source review and Windows runtime lifecycle evidence retain their exact
source scope. The current focused [parameter evidence](docs/evidence/issue-14/parameters/README.md)
and independent correction review pass separately.
The ordinary coordinator runs without a Codex test worker and keeps physical
actions disabled; no operational deployment grant exists. Normal Orca's 1429
settings/profile files retain their pre-V1 fingerprint. No new physical test or
merge occurred.

The [candidate status and future Founder review guide](docs/V1_FOUNDER_REVIEW.md),
[program scope](docs/BUILD_PROGRAM_V1.md), [shared contracts](docs/V1_CONTRACT.md),
[generation/parity](docs/V1_GENERATION_PARITY.md), [grouped engine status](docs/V1_ENGINE_REUSE.md),
and [runtime operations](docs/V1_RUNTIME.md) record the implementation and limits.
PR #15 remains draft and unmerged pending Founder acceptance;
this is not a qualified five-calibration release.

## Issue #12 — accepted physical Temperature calibration

Founder accepted [Issue #12](https://github.com/bigstupid007/helix-orca-calibration/issues/12)
/ [PR #13](https://github.com/bigstupid007/helix-orca-calibration/pull/13) on
2026-10-18. The installed **0.4.3-issue12-auto** at reviewed `f7562bf` completed
the final Founder-started **225/220/215°C** print, presented Temperature
automatically on the actual HelixScreen, and returned **220°C / NOT APPLIED**
to the original Orca context. Independent completed-job history, exact native
result/receipt and delivered status agree; original profiles remain unchanged.
The physical **1×1** icon/identity/status tile and native navigation are verified.

[Founder acceptance and closeout](docs/ISSUE_12_ACCEPTANCE.md) records the real
outcome, deployment/rollback preservation and governed merge boundary.
[Final physical evidence](docs/evidence/issue-12/physical-final/README.md) is separate
from the unchanged [first-print baseline](docs/evidence/issue-12/physical-first/README.md)
and synthetic eleven-size native capture. Dismiss/reopen/restart/duplicate and
rejection coverage remains accurately scoped to its source of proof.

The temporary native-dialog overlap limitation is accepted for this personal
printer. Conservative crash recovery may suppress an unseen popup and retain
manual recovery after fresh verification. No queued API, delay workaround,
notification change, upstream patch or profile writeback is introduced.
October 15 nightly remains preferred; Alpha has no physical adoption.

The Issue #12 closeout stopped implementation pending a new Founder launch.
The V1 program above supersedes that stop for approved development only. New
physical tests, firmware/printer configuration changes and profile writeback
remain outside this approval.

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

## Issue #8 — accepted bidirectional communication milestone

[Build Program #8](https://github.com/bigstupid007/helix-orca-calibration/issues/8)
authorizes one real Temperature request/selection return without printing. The
candidate generates a beta.9 derivative of the accepted `orcacal` chooser and
Temperature detail, a self-contained October 15 Orca companion derivative, and
a bounded relay using existing access. Accepted Issue #1, #4 and #6 sources and
the beta.4 harness remain unchanged.

The candidate passes 181 tests, corrected eleven-viewport native evidence,
isolated Windows validation, independent review and AI Product Preflight. A
fresh actual Orca request reached the physical HelixScreen; the owner selected
simulated 205°C and Return. Spare committed the exact result and receipt, native
storage persisted its acknowledgement, and Orca displayed original-context
**NOT APPLIED** instructions. [Actual proof](docs/evidence/issue-8/physical/qualification.json)
also records completion before expiry, unchanged native/display files, ready/
standby postchecks and the unchanged 1,429-file normal Orca profile fingerprint.

The founder approved the disclosed trusted-LAN boundary, which remains
unencrypted and without per-message cryptographic authentication. A narrowly
reviewed owner utility creates one real shared directory and one file link,
exposing only `orcacal.json` through the existing config API. This amendment is
approved and was executed through existing owner local access only. See the
[storage gate](docs/TEMPERATURE_COMMUNICATION_STORAGE_GATE.md),
[program](docs/BUILD_PROGRAM_TEMPERATURE_COMMUNICATION.md), and
[operations and exact Founder Review path](docs/TEMPERATURE_COMMUNICATION.md#founder-review).
Founder accepted Issue #8 and PR #9 on 2026-10-16 (America/Chicago), after
reviewing the actual original-profile 220°C / simulated 205°C / NOT APPLIED
Orca result, and authorized governed merge, main verification and Issue closure.
[Acceptance and closeout](docs/ISSUE_8_ACCEPTANCE.md) records the precise scope;
the PR/Issue own final merge and verification state. The completed relay has
exited. [UX polish remains deferred](docs/backlog.md#deferred-ux-batch-after-the-accepted-bidirectional-proof);
no printing, automatic profile update, release or broader deployment is authorized.


## Official OrcaSlicer 2.5.0 Alpha qualification

Founder accepted [Issue #10](https://github.com/bigstupid007/helix-orca-calibration/issues/10)
and PR #11 on 2026-10-16 for official `v2.5.0-alpha` (`3880f2c5`) against the
accepted October 15 nightly. Source comparison and official artifact verification pass; Alpha is
staged separately on Spare. A generated `0.5.1` companion admits only the exact
Alpha identity without changing accepted `0.5.0` source, protocol or relay.
Actual Windows installation, context/unsaved values, normal Temperature export,
exact file association, isolated native 205°C return, duplicate/stale handling,
profile switching and process-restart recovery pass. Normal profiles and the
accepted nightly are unchanged. October 15 remains the preferred development
and physical-integration baseline; Alpha with companion 0.5.1 is a qualified
secondary target. Alpha physical integration and production adoption remain
unauthorized. [Founder acceptance and closeout](docs/ISSUE_10_ACCEPTANCE.md)
authorize PR #11 merge, main verification and Issue #10 closure only; GitHub
records the final outcome. See the [qualification report](docs/ORCA_ALPHA_QUALIFICATION.md).

V1 runtime lifecycle and recovery details are maintained in
[the coordinator guide](docs/V1_RUNTIME.md) and
[the Windows lifecycle package](docs/V1_WINDOWS_RUNTIME.md). These are development
candidate instructions; physical activation and generator qualification remain
separate gates.
