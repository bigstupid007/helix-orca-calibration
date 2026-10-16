# Issue #8 production storage amendment

Status: **resolved for the explicitly approved owner-run single-file bridge**.
The owner applied the amendment; authenticated readback, a fresh actual return,
originating receipt and persisted native ACK are verified. One unmerged
[PR #9](https://github.com/bigstupid007/helix-orca-calibration/pull/9) awaits
Founder Review. [Actual evidence](evidence/issue-8/physical/qualification.json)
and [AI Product Preflight](ISSUE_8_PRODUCT_PREFLIGHT.md) record the completed path.

## Initial deployment finding

The owner enabled `Orca Calibration 0.3.0-issue8-native`. Read-only manifest and
enabled-grant retrieval confirmed exactly `storage`. Beta.9 describes that as
keeping the plugin's own data on the screen, up to 256 KB; it does not use the
literal label “Storage” in the consent body.

The first actual request displayed original context and the owner selected
simulated 205°C/Return, but config-root GET remained 404 and no Spare inbox or
receipt appeared. The relay stopped, preserving its request/journal. This was
partial forward evidence, never a completed return claim.

Beta.9 runs with lexical `config/settings.json` under its installation. The
installer links that individual settings file into printer-data config, not
the whole directory. Storage uses the lexical settings parent's plugin-data:

```text
Native write:   <INSTALL_DIR>/config/plugin-data/orcacal.json
Relay GET:      <MOONRAKER_CONFIG>/helixscreen/plugin-data/orcacal.json
```

The isolated test layout put settings directly in its writable config tree,
so it did not reveal the deployed mismatch. Storage writes are atomic but
deferred; a successful Lua call alone cannot prove persistence or delivery.
Pinned primary sources: [storage path/writer](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/plugin/lua_bind_io.cpp),
[installer file links](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/scripts/lib/installer/platform.sh),
[runtime config path](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/include/runtime_config.h),
[plugin-host settings path](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/application/printer_session.cpp).

## Explicit owner authority and execution

The founder approved “Approve this owner-run single-file exposure” after the
scope was disclosed. The owner confirmed an existing local terminal and the
installation directory, then executed the pinned, hash-checked
[reviewed utility](../scripts/temperature-communication-storage-link.py).
Dry run reported no change; apply reported creation of only the real shared
plugin-data directory and this exact file link:

```text
<MOONRAKER_CONFIG>/helixscreen/plugin-data/orcacal.json
    -> <verified INSTALL_DIR>/config/plugin-data/orcacal.json
```

Utility commit: `1d4543ba489f87a24916c143fdae8f79babbc305`; SHA-256:
`045d2a578f869eaa761a7168a3155af44785b9baadb677a85f5af3e9aa95a00f`.
It defaults to dry run and checks shared/native settings identity, exact
storage-only manifest, bounded state/request identity and a nonconflicting
file destination. Seven temporary-filesystem tests and independent review
cover its boundary. The owner ran this exact code in memory through existing
local access; the agent acquired no printer SSH access.

The amendment changes no native write path, binary, access mode, account,
credential, listener, service, plugin permission, profile or firmware. It
creates no directory-wide link, overwrites no unrelated destination and
restarts no service. It authorizes no wider configuration change. The
physical HTTP hop remains the separately approved trusted-LAN boundary.

## Observed readback and fresh return

Existing authenticated GET matched the historical request/205°C result, now
expired. That result was preserved and never forwarded or retargeted. After
explicit retirement, a fresh originating Orca Send persisted exact native
context through the bridge. Native atomic replacement preserved the separate
config-side link to the filename. Owner selection on this fresh request then
completed exact Spare inbox/receipt, persisted native returned/acknowledged
state and delivered status before original expiry. All nine native/display
files, ready/standby postcheck and normal Windows profile fingerprint pass.

The deployed Moonraker revision's static file handler follows a file link,
while reserved-path checks resolve its target. This is observed version-specific
behavior, not a guarantee for every external-root file. Existing config API
policy still applies; this link must not be described as a newly enforced
read-only network permission. Sources: [file handler](https://github.com/Arksine/moonraker/blob/d5ee17128bb88434aacdab90c2e9e990e2b64e4a/moonraker/components/application.py),
[reserved paths/link listing](https://github.com/Arksine/moonraker/blob/d5ee17128bb88434aacdab90c2e9e990e2b64e4a/moonraker/components/file_manager/file_manager.py).
A future policy denial requires stopping, not chmod or wider exposure.

## Recovery boundary

Never put the link at the native writer's destination. Owner rollback removes
only this exact config-side link after checking its target, preserving native
data and all request/result/journal evidence. No broad cleanup is authorized.
The completed bounded relay has exited. A fresh Founder Review uses
[the documented agent-prepared window](TEMPERATURE_COMMUNICATION.md#founder-review),
not an expired result under new IDs. Founder acceptance, merge and deployment
remain open; this approved setup grants none of them.
