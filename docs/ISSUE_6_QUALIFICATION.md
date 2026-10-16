# Issue #6 release and display-only qualification

## Current disposition

This is a bounded qualification checkpoint for [Issue #6](https://github.com/bigstupid007/helix-orca-calibration/issues/6), not a completed real-printer candidate. It preserves the accepted beta.4 harness, October 11 Orca runtime, normal Orca installation and profiles, and all Issue #4 evidence. Exact new pins and current machine observations are locked in [`evidence/issue-6/release-lock.json`](evidence/issue-6/release-lock.json).

The beta.9 official x86 desktop artifact passed network-disconnected startup, accepted `orcacal` plugin loading, native Home placement, and timed screenshot capture. Its release build reports no mock backends and no remote-control support, so it cannot run the accepted interactive mock matrix. The beta.4 harness remains the behavioral regression authority until a beta.9-capable isolated test build is separately qualified.

The October 15 Windows portable archive, executable, and main DLL were independently hash-verified on Spare in a dedicated Issue #6 directory. Native runtime qualification uses [`scripts/orca-oct15-qualify.ps1`](../scripts/orca-oct15-qualify.ps1), a distinct `--datadir`, and child-only WebView2 storage. Staging is complete; the runtime result must be recorded after the actual Windows GUI run. Source/Linux observations do not pass that gate.

## Compatibility decisions

Beta.9 remains compatible with the accepted permissionless `orcacal` manifest (`helix_version >=1.1.0-beta.4`). The plugin loaded unchanged. Beta.9 adds useful plugin validation, overlay update and event-handling improvements, but they are candidates only after the display-only adaptation is proven in isolation.

The newer official Calibration Bridge is rejected unchanged. Its manifest requests `http` and `moonraker_write`; its handlers can start and cancel a print and POST a result to a companion URL. Issue #6 permits a repository-owned adaptation, but only the event validation, finite-number checks, bounded choices, overlay updates and display state may be reused. The adapted manifest must have no `http` or `moonraker_write`, and the implementation must contain no print start/cancel, G-code, heating, motion, macro, queue or result-network call.

The October 15 Orca source is 150 commits beyond the accepted baseline. Source comparison found no changes under the plugin host, Calibration GUI, Send-to-Printer, or Plugins UI surfaces used by Issue #4. General fixes include cloud-plugin TLS verification and a G-code-file-open crash fix. These are source findings only until the Windows run proves the existing read-only plugin, original/saved/edited context distinctions, ordinary Temperature preparation/export, and explicit file fallback.

## Supported transient event path

The actual target reports Moonraker `v0.10.0-31-gd5ee171`; exact upstream commit `d5ee17128bb88434aacdab90c2e9e990e2b64e4a` matches the observed short revision. Its `connection.send_event` endpoint is WebSocket-only and accepts only a connection identified as `type: agent`. Registration is in-memory, the event becomes `notify_agent_event` for connected clients, and the agent is removed on disconnect. A short-lived client therefore needs no service, plugin, Moonraker configuration, new credential or persistent registration when the existing trusted-LAN authorization applies.

No event has been sent to the actual target. Before that step, an offline test must prove that the client exposes only `server.connection.identify` and `connection.send_event`, sends the single bounded `helixcal.available` schema, closes immediately, and has no printer-control method. Target plugin staging must use an already supported Helix plugin path with a precise rollback. Unknown SSH host trust must not be bypassed.

## Native and target boundary

Read-only exact-host calls established that the owner-confirmed target is reachable, Klippy is ready, Moonraker has no failed components, and no companion agent was persistently registered. The owner reports beta.9 installed. No SSH connection, plugin install, event, service restart, configuration change, print, queue, heat, motion, homing, macro, profile writeback or other printer mutation has occurred.

The official desktop screenshot SHA-256 is `a7302dda30ed6f38a1300c8bc4c0cd91986435845addd965906343849ec0fcb9`. It is retained in private temporary evidence because the release artifact cannot produce the complete interactive matrix. Promote target evidence only after the display-only separation and actual target route pass.

