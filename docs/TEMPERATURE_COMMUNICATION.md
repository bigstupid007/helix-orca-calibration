# Temperature communication candidate — Issue #8

The [governing Build Program](BUILD_PROGRAM_TEMPERATURE_COMMUNICATION.md) owns
scope and the approved existing trusted-LAN boundary. This document describes
the candidate and its review/recovery boundary. It is not physical acceptance.

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

**Production return is blocked.** The actual native sidecar path is under the
install tree, outside this config-root GET. See the
[approved owner-run exposure](TEMPERATURE_COMMUNICATION_STORAGE_GATE.md). No
new physical request is permitted before the approved single-file bridge
passes exact authenticated readback. No broader workaround is authorized.

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
proved separately on the actual target.

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

## Review path and readiness gate

From Orca’s startup home screen, choose **New Project** to enter Prepare.
The observed Windows entry is **Prepare > application menu next to File >
Plugins > expand Helix Calibration Context > Play Helix Temperature
Communication (no printing)**. Version `0.5.0` exposes five capabilities.
The right-hand Orca-owned panel has **Keep original profile**, the exact file
chooser, and **Send request**. The agent has exercised entry, original-context
capture and exact native file association on Spare.

The intended complete review scenario is: retain the named original context
and exact prepared file on Spare; Send; see that context in the existing native
Helix Temperature detail; select a simulated 205°C and Return; see the same
original profile, exact setting, separate original values, selected value and
NOT APPLIED instructions in Orca. The relay/receipt mechanics are agent-owned;
the founder should judge discoverability, naturalness, wording, hierarchy,
context trust and native navigation. No saving, printing or hardware control
is part of review.

That complete scenario is **not yet a Founder Review handoff**. Required
the actual physical return remains blocked at the deployment decision. AI Product Preflight
must prove the same real path before the PR is presented as ready. Automated,
fixture and AI inspection cannot provide founder acceptance.

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
needed. Physical rollback, if staging is later authorized, first requires the
owner to disable the generated `orcacal` candidate, then removal only of its
owned exact files/folder. Do not touch the accepted display plugin or printer
settings, services or firmware.

## Actual physical attempt and continuation

The owner observed original context and simulated 205°C/Return on the physical
screen. The relay’s GET remained 404 because the production installer links
settings.json individually and leaves plugin-data in the install tree. No
returned bytes, companion inbox/receipt or persisted ACK were observed. The
relay is stopped and its immutable request/journal is retained. This is partial
forward evidence, not a completed round trip.

Automatic receipt-driven retry is now bounded to five persisted deliveries
across relay restarts. It rechecks ready/idle state and exact file bytes, only
shortens the lease, and stops repeated request delivery on an exact recovered
native session. These isolated tests do not resolve the production exposure
gate. Do not replay an expired result under a new origin after any amendment.
