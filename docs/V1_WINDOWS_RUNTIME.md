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
runtime lock. The CLI additionally holds storage-scoped `coordinator.lock`, preventing a
separate direct invocation using a different journal directory.

The default transport remains offline. `-MoonrakerEvents` is a separate explicit
opt-in passed to the reviewed coordinator; it still requires the existing
trusted-LAN acknowledgment in the private configuration. The wrapper opens no
inbound listener and never supplies or creates credentials. It does not turn
existing trusted-LAN proof into production security qualification. It never
enables a physical action adapter.

## Optional future local deployment authorization

The wrapper accepts optional `-DeploymentAuthorization <exact-existing-path>`.
The current review invocation omits it and keeps physical actions disabled. The
wrapper never authors an approval record or treats a native event/configuration
flag as authorization. A future owner-made record requires separate explicit
deployment approval before use.

The supplied path must be an existing ordinary local file, with no reparse
points, owned only by the current user and granting no other principal access.
Its size must be 1..65536 bytes. The wrapper retains the exact normalized path
and SHA-256 in its private lifecycle record and rechecks ownership, path and hash
before child launch. It passes only the fixed typed CLI argument
`--deployment-authorization <path>`. A changed/missing/shared file blocks launch;
it is neither repaired nor rewritten. The review-only startup plan retains the
proposed argument/path/hash but still creates no registration or approval.

The coordinator independently validates the exact local record schema
`helix-orca-v1-local-deployment/v1`, `approved: true`, `native_start_only: true`,
a nonempty approval reference, the canonical private-configuration digest and
runtime closure fingerprint. That fingerprint binds the CLI, all
`integration/v1_*.py` modules and the existing WebSocket framing source
`scripts/helix-display-request.py`; it is not merely the thin CLI entry's file
hash. Merely supplying a path is insufficient. The
separate private owned-job configuration and deliberate native Confirm/Start
remain required. When an authorization path is supplied, wrapper Status reports
its presence and leaves `actions_enabled` unknown (`null`); only the coordinator's
validated health can establish action state. No authorization file was created
or supplied during the current offline Windows qualification.

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

Actual Windows execution on October 18, 2026 passed in fresh isolated
LocalApplicationData qualification directories using existing **PowerShell 5.1**
and **Python 3.13.9**. The installed Orca GUI process retained its exact PID/start
time/executable/command line. Synthetic storage contained no calibration context
or request. Every invocation used the default offline channel, supplied no
deployment authorization, and reported physical actions disabled.

Two historical source-bound stages separated component behavior from the then-current routed entry:

| Stage | Actual Windows checks |
| --- | --- |
| Current wrapper component (`qualification-7b4427c20ec6`) | AST; review-only plan with no registration; detached Start/healthy; duplicate Start same run/PIDs; graceful Stop; new-nonce restart/healthy; graceful Stop; private-file ctypes acceptance and shared-file refusal; exact cleanup |
| Final unified-router runtime (`qualification-d8a9f56c3d38`) | AST; detached Start/healthy with matching run ID/PID; graceful Stop; exit 0; no stage-owned Python/supervisor processes; no error logs; every staged source hash unchanged; runtime closure fingerprint checked |

The actual Windows private-file check read an existing owner-private synthetic
wrapper record and an existing shared synthetic generator configuration. The
first passed and the second was refused. It created no deployment grant and
changed no ACL. The tested validator source is identical in both stages.

The qualified wrapper SHA-256 is
`271f34ab005856368507061580f5a7192e1fa600cbdf332d1f79ebb63c5babee`.
The historical routed CLI SHA-256 was
`72be0f52730699b79f07996d94cda759a02c977f388f63285421378b1e617c54`.
The historical routed runtime closure fingerprint was
`fa31bf21a2186eadf5906013cbe28ef4782cc083bee1bca2e54d2efc01a1b3d0`.
The final curated source ZIP SHA-256 is
`08cfa5be91297dcbd0975958631874464afa108f04d334d4b729e0eb6d69c88c`;
the component-stage ZIP SHA-256 is
`3f6984f28141acae7753fc8c95d9db32e47647daebfc4c88ddc35ea7f50fa772`.

Historical staged source inventory (all entries were rehashed on Windows after
shutdown and matched the retained ZIP manifest):

| Relative source | SHA-256 |
| --- | --- |
| `integration/v1-native-build-tools.py` | `7ebee9eb02c35879de35171f6c556641d1858deef13f50fb1ebf2dc82ef5304d` |
| `integration/v1_contract.py` | `27fab88b4b501777fc4a8a8282802538f986584582ec86acecabab8e7034d75d` |
| `integration/v1_deployment.py` | `c4d1e9134404f3c02d9d55a96f62e63302c4b8a40279ad6db96fcfce7013c1aa` |
| `integration/v1_engine.py` | `0831c50f7c1d5d97f8d1aecd87ae744b4568b157c5292dad400efc531840b482` |
| `integration/v1_generation.py` | `de4e8021038cd48997ac25785896c62817476858eaa6db1bdccf4495c61bb657` |
| `integration/v1_jobs.py` | `18dede8d87f7c8e63dcdc68104371049ecf0ce1b549248ec71d082816e8103eb` |
| `integration/v1_orca_extension.py` | `599da475ecb1bdc197c98b33792df29a384f9ee55cb2dc377bac7b07b5c78dec` |
| `integration/v1_parity.py` | `e8709c26687c318fe9455c472b96b5ec078d524f4723ff08d67b9160958213d0` |
| `integration/v1_private_file.py` | `c16f2eb6af4b18d3bb400cb3e2b074e4bb7a5b94dd85ed43a20943cfa94a6308` |
| `integration/v1_routing.py` | `636c2ffe1450e7afdca37e5779984582eeae86ad9e38b8fe47806e2b25955a7a` |
| `integration/v1_runtime.py` | `0b982a99e719c186d07c0a27f0692788bfbbc67775802d59d1b162b232001b70` |
| `integration/v1_transport.py` | `85ecf76101eb87cc185da6148643ac803f54b754e86005ea4b104fcd04104600` |
| `scripts/helix-display-request.py` | `82bc033cd9d54404a54b816385b729bfb84f9db316613090bbdf1ad0412157fd` |
| `scripts/v1-runtime-windows.ps1` | `271f34ab005856368507061580f5a7192e1fa600cbdf332d1f79ebb63c5babee` |
| `scripts/v1-runtime.py` | `72be0f52730699b79f07996d94cda759a02c977f388f63285421378b1e617c54` |

Full source manifests, lifecycle records and Windows responses remain private in
XDG state under `v1/windows-runtime/qualification-7b4427c20ec6-*` and
`v1/windows-runtime/qualification-d8a9f56c3d38-*`. These preserve exact process
identity without publishing user paths or SIDs. The existing testing bridge was
used only to launch and inspect qualification. Ordinary runtime operation calls
the reviewed wrapper directly and has no testing-worker dependency.

Earlier isolated trials exposed a Windows PowerShell 5.1 `File.Replace` null
backup-path incompatibility, inherited output-pipe handles, and a process-exit
race during CIM owner inspection. They were corrected using a unique owned
backup path, explicit STARTUPINFOEX handle allowlisting, and an absence/reused-PID
check that still rejects unavailable identity for a live unchanged process.
Failed stages and shutdown audits were preserved privately.

The worker authoring suite passed **279 tests**, with two Windows-specific checks
skipped on Linux; the separate actual Windows parse and private/shared ACL checks
above passed. This proof covers the exact inventory above. Later engine-source
changes or built binaries were not exercised by it. No calibration generation,
G-code dispatch, engine execution, physical transport security, hostile ACL or
stale-PID injection, high-volume log rotation, interruption during generation,
or paths-with-spaces launcher cycle was qualified. These remain explicit
validation limits. No startup registration, install, physical test,
profile/configuration mutation or printer connection occurred. Original
settings, Temperature evidence and rollback material remain preserved.

## Current integrated closure — qualification-044ff4216374

The later integrated runtime was requalified on actual Windows using the same
existing Python 3.13.9 and PowerShell 5.1, default offline transport and new
synthetic storage. The review-only plan registered nothing. Detached Start
reported healthy with no test-worker dependency; duplicate Start retained the
same run and process identities. Existing private-file acceptance and shared-file
refusal passed without an ACL change. Graceful Stop returned stopped / exit 0.
All staged source hashes matched afterward; no owned process or error log
remained, and the marked Orca GUI retained its exact identity. No deployment
authorization or physical adapter was supplied.

Current CLI SHA-256:
`31e75a9fe94ae05030f7cd16a6de00a89aae40fb2e33193ca85493819ca85426`.
Current complete Python runtime fingerprint:
`ddd6132628c88603461f69a0cb9832c45d1ad78b07e670bdd60239373ffa3dd8`.
Source-only ZIP SHA-256:
`146674089eb13797919e74ecc9296b4c0a8438970d4f2a89c3bc98faa1c2f2e2`.
The wrapper remains the hash-qualified `271f34ab…` source.
[The bounded current inventory](evidence/issue-14/windows-runtime-current.json)
retains every source-file digest and the check outcomes without private paths,
profile payloads, owner SID or process command lines. This stage supersedes
the older closure checks for these exact bytes; it does not prove physical
transport security, printer execution or a Windows-native engine build.
