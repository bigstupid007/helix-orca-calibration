# Temperature communication candidate — Issue #8

The [governing Build Program](BUILD_PROGRAM_TEMPERATURE_COMMUNICATION.md) owns
scope and the approved existing trusted-LAN boundary. This document describes
the physically validated candidate and its review/recovery boundary. AI
validation does not provide Founder acceptance.

## Generated artifacts and preserved baselines

Generate outside the repository:

```sh
python3 scripts/temperature-communication-plugin.py
python3 scripts/temperature-communication-companion.py <private-output>/helix_calibration.py
```

The native generator pins every accepted `orcacal` source hash; the companion
generator pins the accepted `.py` and October 15 generator. The generated native
candidate keeps `orcacal` and its native tile/chooser/Temperature/Back flow,
with storage-only permission. The generated Orca artifact remains a single
side-loaded dependency-free `.py`. Existing capabilities stay available.
No original source or prior evidence is overwritten.

Native storage permission needs owner consent in HelixScreen Settings > Plugins.
The agent may stage reviewed owned files for the bounded proof, but cannot
write enabled-state or settings remotely. The existing physical plugin folder
listing contained only the accepted `helix-orca-display`; no `orcacal` folder
was present at this program's read-only checkpoint. The reviewed six-file
candidate was subsequently staged and read back exactly, with the accepted
display plugin unchanged and printer still idle. Owner enablement/consent is
complete: read-only verification found exactly the reviewed version and Storage
grant. The owner reported no literal Storage label; beta.9 describes it as
keeping the plugin’s own data on the screen, up to 256 KB.

The initial deployed sidecar location was outside the config-root GET. The
owner has since applied the explicitly approved real directory and exact file
link. Authenticated GET now matches the fresh native request, returned result
and persisted acknowledgement; see the
[storage bridge](TEMPERATURE_COMMUNICATION_STORAGE_GATE.md). No broader
configuration or access change is authorized.

## Correlation and delivery

The companion retains the original full source context before temporary
preparation, including saved, edited and effective values. Its exact native
file chooser binds the normally exported/uploaded file's name, bytes, hash
and nine prepared choices. Send publishes one immutable outbox; retry retains
its request/origin IDs and expiry. One unexpired pending calibration owns the
communication slot. A new calibration may begin after completion or expiry.

A bounded relay retrieves that outbox through the existing Spare worker,
rechecks exact physical identity and idle state, reads back exact uploaded
bytes, and sends only the separate request event. It reads only the native
plugin's fixed storage JSON file. The native selection is never invented by
the relay. Orca validates/commits the selection, writes a correlated receipt,
and only then may the relay send the native acknowledgement. A native storage
call alone is not delivery proof. The slot remains locked after local result
commit until exact native delivery is confirmed, or the original absolute
expiry permits an explicit new calibration. State/outbox/inbox/receipt/status contracts
are documented in [the integration contract](../integration/temperature-communication/README.md).

The physical hop is existing private-LAN HTTP. Host equality, strict schema,
context/file binding, nonces, expiry and replay guards do not encrypt it or
protect against a malicious LAN participant. After disclosure, the founder
explicitly approved “Use existing trusted-LAN boundary for this proof.”
No credential, service or port is created by this code.

## Isolation and validation

Run focused changes during implementation, then the combined candidate suite:

```sh
python3 -m unittest discover -s tests -v
git diff --check
git diff --check origin/main...HEAD
```

The dedicated native qualification driver runs the generated beta.9 candidate
in the existing pinned test image with no container network, read-only runtime
and plugin mounts and a private control socket. It preserves the ordinary
beta.4 harness. Generated screenshots and reports stay in XDG state until a
complete passing candidate-bound report can be promoted. Fixture-triggered
native UI is isolated evidence, never a physical transport claim. The exact
beta.9 mock omits `eventtime` from its read-only query response; the generated
qualification fixture supplies only that clock prerequisite, labels it
synthetic and binds its bytes in the report. Production clock support must be
proved separately on the actual target; the completed physical round trip
provides that separate native clock/idle-gate observation.

Windows validation uses only the previously marked isolated October 15 Orca
data directory, hash-pinned executable/DLL and child-only WebView2 storage.
The candidate installation has a hash-verified `0.4.1` rollback copy. A fresh
hash-only normal-settings/profile baseline precedes this program's UI actions;
compare against that baseline after validation, since legitimate owner changes
may have occurred since the historical Issue #6 session. Do not relabel the old
fingerprint as current preservation evidence.

`temperature-communication-windows-review.py` reuses the exact accepted target
and browser/window guards. Its optional `--passive-menu` mode leaves the cursor
at the approved native point and avoids topmost changes that dismiss Orca's
transient menus. It is qualification infrastructure, not shipping product
behavior. Screenshots showing private operational file details remain private.

## Founder Review

The completed actual 205°C NOT APPLIED panel is left open in the marked,
isolated October 15 Orca on Spare. It can be reviewed immediately without a
live relay. If closed, use **New Project** from startup home to enter Prepare,
then **Prepare > application menu next to File > Plugins > expand Helix
Calibration Context > Play Helix Temperature Communication (no printing)**.
Version `0.5.0` exposes five capabilities. Close/reopen/restart recovery was
validated; opening this capability recovers the retained original result.

Representative context: **Voron Voron 2.4 300 0.4 nozzle**, **Voron 0.20 Standard -
Fast Quality**, **Generic PLA - Voron Rapido - Initial**, 0.4 mm nozzle, and
separate saved/edited/effective **220/220/220°C**. The result card must show
**205°C**, **NOT APPLIED**, and **Filament > Print temperature > Nozzle > Other
layers (nozzle_temperature)**, with optional manual instructions referring to
that exact original filament profile. Review does not include following those
save instructions.

For a fresh live review, the agent prepares another bounded window before the
founder presses Send. The previous one-request relay completed and exited; no
always-on service is installed. Agent setup rechecks exact runtime/plugin
hashes, marked data directory, existing SSH worker, owner grant, single-file
readback, target ready/idle and the already-uploaded file's exact bytes. The
agent preserves the completed artifacts, then uses the panel's **Keep original
profile** and native **Choose File** controls to associate the same private
prepared export, using the retained private setup record. No re-slicing,
upload, profile write or infrastructure change is needed. The exact
operational file identity/location remains private; the founder receives a
prepared panel, not a file-search task or transport commands.

The live sequence is:

1. In that prepared Orca panel, confirm the original context and click **Send
   request**. The agent starts the reviewed one-request relay against that exact
   outbox and retains its journal. Complete the interaction inside the original
   900-second request lifetime; restarting cannot extend it.
2. On the actual HelixScreen's automatically opened **Temperature** detail,
   confirm the original context, choose simulated **205°C**, and tap **Return
   selection**. Native Back remains available; Start remains the accepted
   inactive toast and is not part of this flow.
3. In the same originating Orca panel, observe automatic **205°C / NOT
   APPLIED** instructions for the exact original profile and setting, with
   saved/edited/effective values unchanged. There is no result-file operation,
   Save, print, heat, motion or hardware action. The agent verifies exact Spare
   receipt, persisted native ACK, delivered status, idle postchecks and normal
   profile preservation before declaring that new run complete.

Judge discoverability, wording, hierarchy, context trust, the distinction
between original and current values, and native navigation. Technical
correlation, expiry, retries, duplicate/stale rejection, recovery, byte identity
and isolation are already covered by tests, qualified native/Windows evidence
and the [actual physical proof](evidence/issue-8/physical/qualification.json).
[AI Product Preflight](ISSUE_8_PRODUCT_PREFLIGHT.md) passes this same path.
Founder acceptance, merge and deployment remain separate and are not granted.

## Recovery and rollback

Close the bounded relay to stop communication; it creates no installed service.
Leave request/result/receipt artifacts intact for exact same-request recovery
under the original expiry. Never reset IDs or substitute a current profile to
make a late return fit. Expired requests require an explicit new calibration.
Reject conflicting duplicates without replacing the first committed selection.

For Windows rollback, close only the isolated Orca through its normal UI,
verify the marked data directory and candidate source hash, and restore only
its retained hash-verified `0.4.1` source. Preserve normal Orca and all normal
profiles. Candidate test state remains private evidence; no broad deletion is
needed. Physical rollback first requires the owner to disable the generated `orcacal`
candidate, then removal only of its hash-verified owned exact files/folder.
The owner may remove only the approved config-side link after verifying its
exact target, preserving native state and the accepted display plugin. This
is not permission to remove unrelated files or alter host configuration. Do not touch the accepted display plugin or printer
settings, services or firmware.

## Completed physical qualification

The first actual attempt exposed beta.9's install-side storage path and is
retained as historical partial evidence. The owner then approved and applied
only the reviewed exact file bridge. The old expired result was read back but
never forwarded. A fresh originating request completed the actual path under
its original IDs, including exact native result/inbox/receipt, persisted native
ACK and delivered unlock before expiry. The owner's physical context/205°C/
Return observation and independently retrieved native/Spare artifacts establish
this completion; the final actual Windows panel was inspected separately.

Same-request recovery used two deliveries. Automatic receipt-driven retry is
bounded to five persisted sends across restart, rechecks ready/idle and exact
file bytes, and only shortens the lease. An exact recovered native receipt
stops repeated sends. A pending Lua nil result may be omitted only in
unacknowledged received state. Selected/acknowledged states require the result.
Final checks found all nine native/display files unchanged, target ready in
standby and normal Windows profile/settings fingerprint unchanged. The relay
exited successfully and is not running. Preserve these artifacts; another
review uses a new explicit origin, never a relabeled expired result.
