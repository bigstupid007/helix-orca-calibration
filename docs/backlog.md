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
- [x] Pass the seven committed Helix unit/policy tests and `git diff --check`.

The closeout matrix covers 480x272, 272x480, 480x320, 480x400, 800x480,
480x800, 1024x600, 1280x720, 1080x2400 at 405 DPI, 1920x480, and 320x1480.

This chooser/detail structure is the baseline for future calibration modules.
Future modules extend the registry and add their own native detail component;
they do not redesign the accepted Helix shell.

The closeout note's “25 tests” was the result from this dirty canonical
checkout: the seven committed Issue #1 tests plus 18 unrelated, uncommitted
Orca diagnostic tests. The product acceptance evidence is unchanged; this
corrects the provenance of the count.

## Completed: Issue #2 — native Helix mock-printer UX harness

Founder accepted the native development harness and missing-tile repair on
2026-10-10. PR #3 is the closeout authority.

- [x] Pin and verify beta.4 source, recursive submodules, release data, binary
  provenance/hash, Docker bases, and durable source-build recipe; treat the
  expiring developer artifact only as an optional accelerator.
- [x] Provide `bootstrap`, `up`, `status`, `reload`, `capture`, `promote`,
  `verify-evidence`, and `down` through one repository-owned command.
- [x] Run the real Helix beta.4 binary with the mock printer, direct plugin
  mount, dark 800x480 default, private control socket, and no container network.
- [x] Make the real native frame and pointer interaction reachable at the
  reserved trusted-LAN URL `http://192.168.1.114:8540/`.
- [x] Prove independent read access from the authorized Mac mini.
- [x] Prove beta.4 `PluginDirWatcher` reload without restarting Helix or
  changing product content.
- [x] Capture the actual visible Home landing, chooser, Temperature, and Start
  toast at all eleven target sizes while asserting native pointer interaction,
  accepted navigation, and fit.
- [x] Retain full generated artifacts in durable XDG state and promote a
  bounded versioned matrix/report with landing and final-frame evidence.
- [x] Bind evidence to capture-time candidate/product/matrix/frame hashes and
  add proportionate GitHub CI for that integrity check, the dependency-free
  policy suite, static harness contract, wrapper syntax, and whitespace.
- [x] Preserve every `helix-plugin/orcacal/` product file byte-for-byte.

The merged change contains 22 tests (seven product-policy plus fifteen harness
tests). The present dirty canonical checkout reports 40 because the 18
unrelated Orca diagnostic tests remain uncommitted and untouched. Native
runtime evidence is in [`evidence/issue-2/`](evidence/issue-2/) and the operator
contract is [`HELIX_DEV_HARNESS.md`](HELIX_DEV_HARNESS.md).

## Accepted: Issue #4 — mock-only Temperature technical proof of concept

Issue #4 supersedes the deferred interactive Temperature-picker item. Source
qualification has pinned the successful 2026-10-11 Windows nightly at commit
`210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3` and verified `app_info`, host-owned
dock panels, `--datadir`, preset/dirty lifecycle events, and G-code-export
events in that exact source.

- [x] Record the bounded workstream in one GitHub work item.
- [x] Pin the nightly run, artifact digest, executable/DLL hashes, and source.
- [x] Build a hash-verifying launcher that stages the read-only probe in an
  isolated test settings tree without selecting the existing installation.
- [x] Add a small host-owned qualification panel and retained JSON evidence.
- [x] Pass the interactive Windows qualification checklist with a real unsaved
  value, profile switching, normal Temperature preparation, and actual export.
- [x] After that gate, implement and prove the bounded mock-only round trip.
- [x] Freeze, independently review, and complete AI Product Preflight.
- [x] Receive Founder acceptance and explicit governed merge/closeout authority.

Spare command and native GUI access are proven through the founder-approved
LAN-only worker, including the repaired bounded-pipe regression. The exact
nightly has run in the marked settings tree with separate WebView2 browser data.
Real context, unsaved values, dock/preset/dirty events, manual Temperature export,
and byte/hash-verified manual selection have been observed. Export lifecycle
payloads identify the temporary slicing file, so manual selection is required.

The Windows gate passed at 2026-10-12 01:14 UTC. The supported offline bundle
namespace accepts the original supplied printer leaf with unchanged JSON bytes,
separately from the stock System preset. Real original context and unsaved values
were retained before normal Temperature preparation in a separate temporary
context. The new export/manual selection hashes agree, and all 1,429 normal
settings/profile files remain unchanged. The report is in
[`evidence/issue-4/windows/`](evidence/issue-4/windows/). Mock-only implementation
has passed at all eleven native sizes and returned 205°C with original-profile
**not applied** instructions. Duplicate/stale/conflicting results and artifact
delivery failure/retry are proven. See [the proof](TEMPERATURE_ROUND_TRIP.md).
Founder Review rejected the earlier navigation and
simulation experience; that disposition supersedes the earlier AI preflight.
The navigation/simulation repair passed the native matrix and fresh browser
operator paths. Founder subsequently confirmed the 205°C return but rejected
the companion’s diagnostic-first primary screen. Its result-first repair
retains the working transport and exposes the original profile, live effective
value, selected temperature, exact manual steps and prominent NOT APPLIED.
Focused Windows/browser proof, fresh independent review and affected AI
Product Preflight pass; Founder accepted the completed mock-only technical proof
of concept on 2026-10-12 (America/Chicago), authorizing PR #5 merge and Issue #4
closeout. They are tracked in
[AI Product Preflight](ISSUE_4_PRODUCT_PREFLIGHT.md), with exact candidate and
CI identity recorded in the governing Issue checkpoint. Windows qualification
is complete and has not been restarted for this repair.

The exact gate and agent-operated runbook are in
[`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md). Linux-only
evidence alone cannot replace this completed Windows observation.

The round trip exercises start/progress/completion/result states only in the
separately isolated mock lifecycle. Qualification UI driving is test evidence,
not supported product automation. Retain the host-owned modeless-window and
manual-file-selection fallbacks. The interactive Temperature picker remains a
separate deferred requirement.

## Future UX polish — deferred after Founder acceptance

Founder explicitly deferred additional UX polish beyond the accepted technical
proof. A future approved increment may refine the companion's preparation,
result explanation and manual-update flow, and the mock review experience.
Retain the result-first facts, prominent NOT APPLIED status, immediate mock
Finish control, normal Home/Back and active-task return. This entry creates no
new completion gate or implementation authority. The interactive Temperature
picker remains separately deferred. No production, hardware or automatic
profile application is included.

## Deferred — requires new approval

- Moonraker coordination or networking.
- G-code generation, modification, upload, or execution.
- Print start, monitoring, results, or calibration scoring.
- Orca preset mutation or writeback.
- Additional calibration modules beyond a separately approved increment.
- Picker/profile-browser expansion beyond the bounded Issue #4 flow.
