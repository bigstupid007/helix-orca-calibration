# Spare LAN-only testing access

## Approval and status

On 2026-10-11 the founder explicitly approved minimum LAN-only remote command
and interactive GUI testing access between devbox and Spare for Issue #4.
The approval is recorded in the current GitHub Issue. No Tailscale, public
exposure, new account, or unnecessary security change is authorized.

The reverse SSH worker is prepared and its local protocol/isolation tests pass.
Actual Windows command execution and GUI input remain **unproven** until its
first launch on Spare and the agent-operated smoke test. This is access
infrastructure, not qualification evidence or product behavior. The exact
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
native window and refuses input/capture when that window is not foreground.

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
