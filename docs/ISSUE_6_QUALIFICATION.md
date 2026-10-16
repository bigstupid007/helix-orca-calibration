# Issue #6 release and display-only qualification

## Current disposition

This is a bounded qualification checkpoint for [Issue #6](https://github.com/bigstupid007/helix-orca-calibration/issues/6), not a completed real-printer candidate. It preserves the accepted beta.4 harness, October 11 Orca runtime, normal Orca installation and profiles, and all Issue #4 evidence. Exact new pins and current machine observations are locked in [`evidence/issue-6/release-lock.json`](evidence/issue-6/release-lock.json).

The beta.9 official x86 desktop artifact passed network-disconnected startup, accepted `orcacal` plugin loading, native Home placement, and timed screenshot capture. Its release build reports no mock backends and no remote-control support. The exact upstream developer artifact from successful Build run `38685014257` passed all 15 accepted assertions at each of the 11 target viewports in network-disabled, read-only containers. That artifact came from the same workflow that runs `smoke-headless` before upload, so a 64-minute local source build and 150-minute test build were unnecessary. The accepted beta.4 plugin and harness remain unchanged.

The October 15 Windows portable archive, executable, and main DLL were independently hash-verified on Spare in a dedicated Issue #6 directory. Native qualification used [`scripts/orca-oct15-qualify.ps1`](../scripts/orca-oct15-qualify.ps1), a distinct `--datadir`, and child-only WebView2 storage. The actual Windows GUI reported `2.5.0-dev` at revision `6a7763f0`, loaded the accepted local plugin with empty permissions, distinguished saved 220 °C from an unsaved 217 °C edit, restored the saved state without writing it, and completed the normal Temperature prepare, slice, export, and explicit file-selection path. The unique 3,028,194-byte export has SHA-256 `94c92b561d249ecba76fe6059af09ab89068d2fcc15a6524f5f12a832d32c387` and the ordered 230–190 °C schedule in 5 °C steps. No Upload, Device, Print, queue, or profile Save action was used. The normal Orca data tree had the same 1,429-file aggregate digest before and after the run.

## Compatibility decisions

Beta.9 is compatible with the accepted permissionless `orcacal` manifest (`helix_version >=1.1.0-beta.4`) over the isolated surfaces that were exercised. The plugin loaded unchanged and passed the accepted interactive shell matrix. Beta.9's plugin validation, overlay update, and event-handling improvements are eligible for the separate display-only adaptation, whose receipt and dismiss behavior must still pass in isolation before any target use.

The newer official Calibration Bridge is rejected unchanged. Its manifest requests `http` and `moonraker_write`; its handlers can start and cancel a print and POST a result to a companion URL. Issue #6 permits a repository-owned adaptation, but only the event validation, finite-number checks, bounded choices, overlay updates and display state may be reused. The adapted manifest must have no `http` or `moonraker_write`, and the implementation must contain no print start/cancel, G-code, heating, motion, macro, queue or result-network call.

The October 15 Orca source is 150 commits beyond the accepted baseline. Source comparison found no changes under the plugin host, Calibration GUI, Send-to-Printer, or Plugins UI surfaces used by Issue #4. General fixes include cloud-plugin TLS verification and a G-code-file-open crash fix. The native Windows run proved the existing read-only plugin, original/saved/edited context distinctions, ordinary Temperature preparation/export, and explicit file fallback. Upload-only transport remains a separate gate.

## Supported transient event path

The actual target reports Moonraker `v0.10.0-31-gd5ee171`; exact upstream commit `d5ee17128bb88434aacdab90c2e9e990e2b64e4a` matches the observed short revision. Its `connection.send_event` endpoint is WebSocket-only and accepts only a connection identified as `type: agent`. Registration is in-memory, the event becomes `notify_agent_event` for connected clients, and the agent is removed on disconnect. A short-lived client therefore needs no service, plugin, Moonraker configuration, new credential or persistent registration when the existing trusted-LAN authorization applies.

No event has been sent to the actual target. The display adaptation uses the separate plugin ID `helix-orca-display` and event `helix_orca_display.available.v1`, with schema `helix-orca-display/v1` and required `display_only: true`. The receipt carries the original effective profile temperature separately from the prepared 230–190 °C tower range, preserving the saved/edited context distinction. It must never emit the official `helixcal.*` namespace: a co-installed full Calibration Bridge could otherwise accept that event and expose its Start flow. Before target use, offline tests must prove strict payload validation, request-scoped `Received · not printed · not applied` behavior, Dismiss, and a short-lived client exposing only `server.connection.identify` and `connection.send_event`. Target plugin staging must use the supported `config/helixscreen/plugins/<id>/` route with a precise rollback. Unknown SSH host trust must not be bypassed.

## Native and target boundary

Read-only exact-host calls established that the owner-confirmed target is reachable, Klippy is ready, Moonraker has no failed components, and no companion agent was persistently registered. The owner reports beta.9 installed. No SSH connection, plugin install, event, service restart, configuration change, print, queue, heat, motion, homing, macro, profile writeback or other printer mutation has occurred.

The official desktop screenshot SHA-256 is `a7302dda30ed6f38a1300c8bc4c0cd91986435845addd965906343849ec0fcb9`. It is retained in private temporary evidence because the release artifact cannot produce the complete interactive matrix. Promote target evidence only after the display-only separation and actual target route pass.

