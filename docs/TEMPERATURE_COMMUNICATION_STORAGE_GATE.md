# Issue #8 production storage gate

Status: **single-file exposure approved for owner execution; not yet applied**.
The one candidate remains [draft PR #9](https://github.com/bigstupid007/helix-orca-calibration/pull/9).
The earlier technically reviewed isolated pass does not establish a completed
physical return or full AI Product Preflight.

## What the physical attempt established

The owner enabled `Orca Calibration 0.3.0-issue8-native`. Read-only retrieval of
the actual manifest and recorded enabled grant showed exactly `storage`.
Beta.9 describes that permission as keeping the plugin's own data on the screen,
up to 256 KB; it does not use the literal label “Storage” in the consent body.

A fresh originating Orca Send action emitted a new correlated request after
retaining the actual original context and exact already-uploaded file. The
owner reported that the original context appeared on the actual HelixScreen
and that simulated 205°C and Return were selected. This establishes the real
forward route and native interaction/clock gate. It does **not** prove durable
selection bytes, return delivery, originating-companion commit or native ACK.
The approved Moonraker storage route remained 404; Spare had no inbox or
receipt for that origin. The relay was stopped, its request/journal retained,
and a read-only postcheck found the printer nonactive. No configuration,
permission, service, firmware or hardware action was used as a workaround.

## Why the assumed return route is unavailable

The exact beta.9 deployment runs from its installation directory with lexical
`config/settings.json`. Its installer links that individual settings file to
the printer-data config tree. It does not link the whole config directory or
manage a `plugin-data` link. Native storage uses the lexical settings parent's
`plugin-data/<id>.json`, so the two paths are different:

```text
Native write:   <INSTALL_DIR>/config/plugin-data/orcacal.json
Relay GET:      <MOONRAKER_CONFIG>/helixscreen/plugin-data/orcacal.json
```

The isolated container placed its settings path directly in the writable test
config tree; therefore its passing storage proof did not expose this deployed
layout difference. `helix.storage.set` schedules a deferred write and cannot
establish successful persistence by itself. The successful visual Return must
not be relabeled as an observed durable return file.

Pinned primary sources:

- [beta.9 storage path and deferred writer](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/plugin/lua_bind_io.cpp)
- [beta.9 installer settings-file links](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/scripts/lib/installer/platform.sh)
- [beta.9 runtime config path](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/include/runtime_config.h)
- [beta.9 plugin-host settings path](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/application/printer_session.cpp)

## Narrow amendment — approved for owner execution, not yet applied

Permit the owner, using existing local access, to expose **one file**:

```text
<MOONRAKER_CONFIG>/helixscreen/plugin-data/orcacal.json
    -> <verified INSTALL_DIR>/config/plugin-data/orcacal.json
```

The proposal leaves the native write path and application binaries unchanged.
It adds no HTTP permission, Moonraker-write permission, account, credential,
listener, service, public access, profile write or firmware patch. It would
create the real shared `plugin-data` directory if absent, then the one file
link. It must not create a directory-wide link, change access modes, overwrite
an existing file,
restart a service or bypass a file-access rejection.

The founder explicitly approved “Approve this owner-run single-file exposure”
in the program chat. The owner confirmed an existing local terminal and the
installation directory. This amendment authorizes only the real shared
`plugin-data` directory and exact file link described above. It does not grant
the agent new SSH access, credentials, host trust, permissions or service
changes. Execution remains owner-run; no target mutation has occurred yet.

The reviewed [owner utility](../scripts/temperature-communication-storage-link.py)
defaults to a dry run. Seven temporary-filesystem tests and independent review
cover its boundary. It checks that the
installation and shared settings refer to the same file, the staged manifest
is the exact storage-only candidate, and the bounded native JSON belongs to
the retained proof request. Apply mode would create the real shared `plugin-data` directory if absent
and only the exact file link, refusing an unrelated destination. It has been exercised only in a temporary
local filesystem; nothing ran on the printer.

The deployed Moonraker revision serves authenticated config JSON through its
static file handler. Current file handling follows a file link, while reserved
path checks resolve its target. That is existing version-specific behavior,
not a formal guarantee that every outside-root file is readable. The native
file must exist and be readable by the Moonraker process; verify using the
existing authenticated GET, and stop if policy denies it. Do not repair access
modes or widen the exposed scope by inference.

Sources: [deployed Moonraker file handler](https://github.com/Arksine/moonraker/blob/d5ee17128bb88434aacdab90c2e9e990e2b64e4a/moonraker/components/application.py),
[reserved paths and link listing](https://github.com/Arksine/moonraker/blob/d5ee17128bb88434aacdab90c2e9e990e2b64e4a/moonraker/components/file_manager/file_manager.py).
Native atomic replacement preserves a separate config-side link to the target
filename; never put the link at the native writer's destination instead.

Rollback would remove only the exact verified config-side link, preserving the
native file, request, result and journal. No broad cleanup is authorized.

## Required continuation after a decision

Under the approved bounded amendment, first verify actual paths,
ownership/readability and exact link identity through the existing owner
access route. After readback works, explicitly retire any expired proof slot
and use a fresh originating request. Do not replay an expired result under new
IDs. Repeat actual Send -> physical original context -> simulated 205°C/Return
-> automatic Spare result/receipt -> persisted native ACK/delivered unlock,
then verify original NOT APPLIED instructions, idle state, exact native files
and normal Windows profile preservation. Complete the same-path AI Product
Preflight and reconcile the existing PR before Founder Review.

If the current envelope is retained, leave the PR draft and the physical return
gate blocked. The owner-observed forward interaction remains valid partial
evidence; it is not bidirectional communication acceptance.
