# Windows V1 runtime lifecycle candidate

`scripts/v1-runtime-windows.ps1` packages the local V1 coordinator as an explicit
per-user process, independently of Codex, the Spare testing worker and an open
foreground terminal. It starts one fixed repository entry point with existing
Python, repository, originating plugin storage and private configuration paths.
It neither installs Python nor copies/replaces Orca or the accepted Helix plugin.
The shipped coordinator has no action-enabled printer adapter. Packaging is not
production print or transport-security qualification.

## Review and operation

Use ordinary Windows PowerShell 5.1 or PowerShell 7 on Windows, a supported existing
Python 3.11+ installation, and an existing reviewed Windows checkout containing
`scripts/v1-runtime.py`. Give the exact originating companion's **v1 storage**
directory and the explicit V1 generator configuration. Runtime state must use a
new dedicated directory beneath the current user's LocalApplicationData, outside
normal Orca settings and accepted evidence. The wrapper creates and protects only
that new directory. It refuses inherited/shared ACLs on an existing destination;
it never repairs another directory's permissions.

Example paths below are placeholders to replace deliberately, not discovery or
permission to use normal profile/configuration directories:

```powershell
$runtime = "$env:LOCALAPPDATA\HelixOrcaCalibration\V1Runtime"
$arguments = @{
  RuntimeRoot = $runtime
  PythonExe = 'C:\ExistingPython\python.exe'
  RepoRoot = 'C:\ReviewedCheckout\helix-orca-calibration'
  Storage = 'C:\ExactOriginatingPluginStorage\v1'
  Config = 'C:\PrivateV1Configuration\generator.json'
}
.\scripts\v1-runtime-windows.ps1 -Action plan @arguments
.\scripts\v1-runtime-windows.ps1 -Action start @arguments
.\scripts\v1-runtime-windows.ps1 -Action status -RuntimeRoot $runtime
.\scripts\v1-runtime-windows.ps1 -Action stop -RuntimeRoot $runtime -WaitSeconds 10
```

`plan` writes only `startup-plan.json` with the exact proposed shortcut target,
quoted arguments and suggested current-user Startup location. It creates no
shortcut or startup registration and starts no process. No service, scheduled
task, registry, credential, execution-policy, firewall or other system change is
performed. The owner can review this reversible artifact; actual startup
registration requires a later explicit owner action. Removing a future owner-made
shortcut reverses registration without removing runtime journals or results.

Start is idempotent while the recorded instance remains live. A second launcher
for the same plugin storage cannot launch another Python coordinator: its
supervisor must hold the exclusive `.v1-windows-launcher.lock` file in that exact
v1 storage for the entire instance. The coordinator additionally owns its native
runtime lock. The CLI's storage-scoped lock should also be retained to prevent a
separate direct CLI invocation using a different journal directory.

The default transport remains offline. `-MoonrakerEvents` is a separate explicit
opt-in passed to the reviewed coordinator; it still requires the existing
trusted-LAN acknowledgment in the private configuration. The wrapper opens no
inbound listener and never supplies or creates credentials. It does not turn
existing trusted-LAN proof into production security qualification. It never
enables a physical action adapter.

## Ownership, stop and retained state

The private `current.json` record binds a random run ID, the current user SID,
Python and supervisor PID/start time/executable/exact command line, reviewed
entry/configuration hashes and the exact nonce-specific stop-file path. Windows
CIM owner inspection and process start time prevent a reused PID from being
adopted. An unavailable identity is an attention condition, not permission to
signal a process. Records are bounded UTF-8 JSON and atomically replaced. Reparse
points, UNC paths and foreign/shared lifecycle files are refused.

Stop publishes only this fixed object in the recorded private path:

```json
{"schema":"helix-orca-v1-stop/v1","run_id":"<the exact current run ID>"}
```

It never sends arbitrary commands or force-kills a process. The coordinator reads
only its own nonce-bound stop request, exits through its existing graceful loop
and retains journals, jobs, original context and NOT APPLIED results. Blocking
generation can last up to its bounded timeout. If the requested wait expires,
Stop truthfully returns `stopping`; Status remains available and no second process
is launched. A second Stop is harmless. A stale/mismatched stop file is refused. After Python
exits, trailing output drains for at most five seconds (`finishing`), without
signaling a descendant process. An ambiguous failed instance remains
`attention-required` and is never automatically replaced.

The detached supervisor receives only one explicit inherited NUL handle through
Windows STARTUPINFOEX handle-list creation. It does not inherit the launching
terminal or qualification worker output pipes. A detached per-user supervisor
drains coordinator stdout/stderr using fixed 4KiB character
buffers, preventing a verbose coordinator from filling an unread pipe. Each
`stdout`, `stderr` and `supervisor` log has one 1MiB current file plus one 1MiB
backup: **at most 6MiB of retained wrapper logs** across restarts. Only those exact
owned log files rotate. Unexpected oversized files are preserved and require
manual review. Current and previous lifecycle records are retained; coordinator
journals, calibration history, generated artifacts and accepted evidence are
never deleted by the wrapper. After shutdown, preserve these files for diagnosis
or rollback; no automatic uninstall/cleanup is provided.

## Validation status and limits

Actual Windows execution on October 18, 2026 passed in a fresh isolated
LocalApplicationData qualification directory using existing **PowerShell 5.1**
and **Python 3.13.9**. The installed Orca GUI process remained unchanged. Synthetic
storage had no context or calibration request; the coordinator used its default
offline channel with physical actions disabled.

| Check | Observed result |
| --- | --- |
| PowerShell AST parse | No errors |
| Detached Start | Running, health OK, matching run ID/Python PID; launch worker returned normally |
| Second Start | Same run ID, Python PID and supervisor PID; no second coordinator |
| Graceful Stop | Owned stop file; coordinator health `stopped: true` |
| Restart | New run ID/PIDs; health OK; old stop file did not stop the new instance |
| Final Stop and audit | Exit 0; no stage-owned Python/supervisor processes; no error logs |
| Existing Orca session | Exact PID/start time/executable/command line unchanged |

The qualified launcher SHA-256 is
`fa335f3f6c5a0dc6b56c765b4991bca0af8a884fbb65df74df4afc7cd5963cd7`.
Its exact coordinator entry SHA-256 is
`d97156ef5dc8383fa07e16fc9aff292e4734cb23c3c55c3f49271131eebf698f`.
The curated source ZIP SHA-256 is
`0d32ec7401766f6990922c727a7c8ad59d3328905275c1b19035740e0487e3fe`.
Full manifests, lifecycle records and Windows responses remain private in XDG
state under `v1/windows-runtime/qualification-f529b0529305-*`; they retain exact
process identity without publishing user paths or SIDs. The qualification used
the existing testing bridge only to launch and inspect this proof. Ordinary
operation of the reviewed package calls the wrapper directly and has no testing
worker dependency.

Earlier isolated trials exposed a Windows PowerShell 5.1 `File.Replace` null
backup-path incompatibility, inherited output-pipe handles, and a process-exit
race during CIM owner inspection. They were corrected using a unique owned
backup path, explicit STARTUPINFOEX handle allowlisting, and an absence/reused-PID
check that still rejects unavailable identity for a live unchanged process.
Their failed stages and shutdown audits were preserved privately.

The dependency-free checks cover lifecycle entry points, stop protocol,
exact-process ownership, fixed entry-point arguments, private state, detached
handle allowlisting, and absence of force-kill/system-registration operations.
The authoring suite passed 256 tests, with the Linux-host Windows AST test skipped;
the separate actual Windows parse above passed. This execution proof does not
qualify paths containing spaces, hostile ACL/stale-PID injection, high-volume log
rotation, interruption during blocked generation, physical transport security,
or physical printer execution. These remain explicit validation limits. No
startup registration, install, physical test, profile/configuration mutation or
printer connection occurred. Original settings, Temperature evidence and
rollback material remain preserved.
