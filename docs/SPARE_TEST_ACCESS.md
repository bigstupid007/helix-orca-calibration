# Spare LAN-only testing access

## Approval and status

On 2026-10-11 the founder explicitly approved minimum LAN-only remote command
and interactive GUI testing access between devbox and Spare for Issue #4.
The approval is recorded in the current GitHub Issue. No Tailscale, public
exposure, new account, or unnecessary security change is authorized.

The reverse SSH worker was launched on Spare. Command execution and a real
native button click were proven in session 1 as unelevated
`AzureAD\ChrisDeMichael`. The agent inspected the temporary-window screenshot,
SHA-256 `43c8f20c4aa69a03eb46df2d70f7b18035d5771f9cfd5a1c9389e6793f5fd327`.
A later launch exposed an unbounded output-pipe EOF wait when a descendant
retained a handle; the transport expired. The worker now bounds each EOF wait
to 750 milliseconds and reports incomplete capture. The owner restarted the repaired worker. A harmless inherited-pipe command
returned bounded incomplete capture in 2.11 seconds, and the following probe
succeeded. This is access infrastructure,
not a completed Orca qualification or product behavior. The exact
nightly qualification gate remains in
[`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md).

## Minimum route

An unelevated PowerShell worker on Spare's signed-in desktop uses its existing
SSH client/key to connect to `dev@192.168.1.114`. It pins the existing devbox
Ed25519 host key in a dedicated public known-hosts file below
`%LOCALAPPDATA%\HelixOrcaCalibration\windows-access`, preserving normal SSH
configuration. The transport disables forwarding and password prompts and
fails closed on host-key or authentication errors.

The devbox end accepts only a worker identifying Spare, with an interactive
session ID and unelevated user, arriving from `192.168.1.155` to devbox's LAN
SSH listener. Local requests use a mode-0600 Unix socket in a mode-0700
XDG-state directory. There is no new TCP listener, Windows service, RDP/WinRM
configuration, firewall rule, scheduled task, or elevation. SSH is the only
network path and uses the already established Spare-to-devbox direction.

The worker allows agent-owned testing commands in the signed-in user's normal
security context. It is an authenticated command channel, not an OS sandbox.
All commands remain subject to Issue #4: preserve normal Orca settings and
installation, do not access a physical printer, and keep GUI automation in
isolated testing only. The initial GUI smoke test uses only its own temporary
native topmost window, verifies that the click point belongs to that window,
and requires it to be foreground before capture. This avoids treating
SetForegroundWindow permission as proof of input access.

Requests are serialized, correlated by unique IDs, limited to 8192 script
characters and 60 seconds, and output-bounded. Timeout kills only the direct
command child; it never performs a broad process kill. A stale response ends
the access session. Logs retain operation/ID/script hash, not command contents
or returned data. Caller-owned evidence must stay in private XDG state.

## Prepare and first launch

From the existing Issue #4 worktree on devbox:

```sh
python3 scripts/spare-access.py prepare
```

This freezes all three access scripts and their hashes in the user cache at
`~/.cache/helix-orca-calibration/windows-access/<bundle hash>/`. Runtime code
never depends on an Issue-specific `/tmp` worktree. Repeat preparation verifies
the existing bundle rather than overwriting altered files.

Since no target-side execution channel exists yet, the first launch is an
unavoidable owner-only action. In ordinary, unelevated PowerShell on Spare,
fetch the prepared `spare-access.ps1` using the existing strictly verified LAN
SSH connection and invoke that script block. The agent supplies the exact
frozen path. Keep that window open. Do not ask the owner to configure SSH,
install software, change a firewall, qualify Orca, or collect evidence.

If existing client authentication or host trust fails, stop and diagnose the
specific failure; do not enable password fallback or relax host verification.
No new credential is created or transferred by this route.

## Agent-operated validation and continuation

On devbox:

```sh
python3 scripts/spare-access.py status
python3 scripts/spare-access.py probe
python3 scripts/spare-access.py exec --script-file scripts/spare-gui-smoke.ps1
```

The probe must report Spare, the actual Windows user, an interactive session,
and unelevated execution. The GUI smoke test must report a real native button
click and return its own cropped-window PNG/hash. Save and inspect that PNG
privately; do not claim GUI success from a payload alone. A locked desktop or
foreground failure requires the precise owner-only unlock/access action.

Then the agent verifies actual Windows runtime/process/path state, stages the
pinned portable nightly and exact candidate in separate test directories, and
executes the existing qualification checklist. Only a complete pass permits
mock Temperature round-trip implementation. No normal Orca process is forcibly
closed, and no normal installation/profile data is selected for the test.

To close access:

```sh
python3 scripts/spare-access.py stop
```

Alternatively close the worker window or press Ctrl+C on Spare. Closing the
worker ends access; no access service remains installed. The server removes
its active socket/session record on ordinary disconnect. If interrupted by a
hard process kill, inspect the recorded PID and remove only a confirmed stale
access socket before reconnecting. Frozen scripts and hash-only request logs
remain in user cache/state for reproducibility.

## October 11 nightly staging checkpoint

- The 230,435,783-byte transfer archive was hash-verified on Spare as
  `f151331dbc1246a0a543c7ca34a25cf1001123b1f7517cdeef120c149e1b3a05`.
- The staged executable and DLL match the fixed Issue #4 hashes. Qualification
  inputs match transfer SHA-256
  `5e6a594db134042091fb8496c036287b5e0f660b6c6ef3466c2701ffc05b90c1`.
- A baseline fingerprint of 1429 normal Orca settings/profile files was retained
  privately; content was not used by the plugin. The ordinary installed Orca
  process `40056` was still running in the last completed observation.
- The first test launch included `--no-single-instance` and crashed with Windows
  event exception `0xc0000409` in `ucrtbase.dll`. Exact source review then showed
  that CLI registration is commented out, despite an internal parser helper.
  The flag was removed; no upstream or normal installation was modified.
- A retry with only `--datadir` and the portable working directory was issued,
  but its result was lost when output capture timed out. Reconnection confirmed
  PID 36236 and the real setup wizard. That retry ran successfully.
- Native UI tooling in `orca-windows-review.py` / `orca-windows-ui.ps1` verifies
  the isolated executable, marked data directory, launch arguments, window PID,
  and pointer/capture ownership before any interaction. Normal Orca is excluded.
  Actual runtime testing exposed embedded WebView/popup ownership, display
  scaling, and queued input. Guards now check isolated top-level ownership,
  validated WebView descendant ancestry, DPI-aware coordinates, and completion
  before restoring the cursor. Native manual selection was proven.

## Verified runtime continuation and isolation repair

The fixed nightly installed/activated all three local `.py` capabilities. Its
context window and dock read real profiles and unsaved values, and normal
Temperature preparation/slicing/manual export completed. The manual picker
verified the actual export SHA-256
`0f70497ac2237d34838a648c72299855d4d64d35073ebbd0655842ecdd83f06d`.

`--datadir` alone did not isolate WebView2: its browser and native file picker
reused the ordinary Orca browser process/data folder. The input guard refused
that picker. The test nightly alone was restarted with the documented
`WEBVIEW2_USER_DATA_FOLDER` child-environment override. PID 17420 then owned its
own browser PID 36352 under `issue-4-nightly-210bc927\webview2\EBWebView`;
normal Orca PID 40056 and browser PID 11436 remained separate and running.
No registry, user/machine environment, service, firewall, or normal browser
configuration changed. Prior pre-repair captures do not prove browser isolation.

A later complete run (test PID 32504) passed the Windows gate with separate
browser storage. Orca's supported offline local bundle importer accepted all six
unchanged original JSON files, resolving the System-name collision. The original
printer is a local bundle leaf with `is_system=false`. The new manually exported
file is 3,619,569 bytes, SHA-256
`24594869ed17ec6d26c920ff684329c087487d20cbffddaf849c1afd4cdf271b`; native manual
selection verified the same bytes/hash and nine choices. The test project and
unsaved calibration edits were discarded, leaving normal Orca PID 40056 running.
No owner access action is pending; the worker remains available for bounded
qualification/integration testing. See
[`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md).

Normal Orca preservation was checked after GUI testing: all 1429 settings/profile
files matched the pre-test aggregate SHA-256
`ed4cd00fff296723223ede35beabcacb41a64d2046c8c30a60513aa1de3bd0f0`.
`scripts/spare-normal-preservation.ps1` records the exact hash-only recipe and
excludes cache, logs, and plugin data. This establishes normal profile/settings
preservation, while the earlier shared browser-cache gap remains disclosed.
