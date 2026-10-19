# Windows-origin actual native parameter bridge

`scripts/v1-windows-parameter-bridge.py` is a lead-run qualification tool. It
uses an actual Windows `Coordinator`, real `v1_routing.generate` and capabilities,
`DirectoryEvents`, and the unchanged normal `scripts/v1-runtime.py:tick`. It
constructs no print adapter. Full profiles, configuration, private journals,
parity reports and G-code remain Windows-local. Only the real offer, exact native
request, real status, fixed trace flags and hashes are returned as metadata.
This is offline transport emulation, not physical or Moonraker qualification.

The two phases avoid adopting or fabricating a coordinator journal:

1. `--op offer` on Windows issues the actual coordinator's offer **before** native
   operator selection. The lead's approved bounded test relay delivers exactly
   the returned `offer` into the native browser proof. It does not replace any
   nonce, timestamps, profile identity, defaults or availability claims.
2. After actual native pointer/keypad/Generate input, preserve the exact saved
   `v1_session` as a Windows-local JSON file. `--op consume --native-session ...`
   checks the fresh request against the complete exact original offer and
   original context. It copies that request into the owned DirectoryEvents input
   and calls normal tick. No random new request or expiry extension is made.
3. Deliver exactly the returned `status` through the same explicitly approved
   test relay. No prepared/status payload is manufactured. An unavailable native
   Windows route retains the actual request and the genuine capability blocker;
   it reports `generator_dispatched:false`. A generated file without matching
   independent native reference remains unqualified. The tool supports all five
   calibrations and both YOLO modes through the same contract and actual routing.
4. For a new trial after `blocked`, `failed`, `cancelled` or acknowledged
   `delivered`, call `--op offer` explicitly again. Normal `Coordinator.offer`
   archives the prior immutable session and issues its new nonce. A qualified
   `review` trial must receive an actual native pre-start Cancel first; the
   bridge accepts only that native Cancel intent and rejects Confirm/Start.
   A duplicate terminal consume returns the same authoritative status without
   changing offer or dispatching again.

Keep the bridge root as a new child of the existing marked
`%LOCALAPPDATA%\HelixOrcaCalibration\v1-qualification` tree. Context, private
configuration and session inputs must be local regular files within that tree;
symlinks/reparse paths are refused. The original canonical context must remain
`3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c` and the
runtime must remain exact October 15. The bridge uses a private copy of context
and its own storage/channel; it does not overwrite originating companion state.

Stage the new public bridge script beside current `scripts/v1-runtime.py` and
these current modules: `integration/v1_contract.py`, `v1_runtime.py`,
`v1_transport.py`, `v1_routing.py`, `v1_generation.py`, `v1_parity.py`,
`v1_engine.py`. Preserve directory structure. Every source hash is retained and
must remain unchanged across offer/consume. The source-only package contains no
profiles or G-code. No target transfer or operation is performed by this document.

The private generator JSON uses real existing pinned executable/assets/receipts.
Remove the standalone recipe's test `now` field; clock and runner overrides,
physical adapter configuration and network configuration are refused. Set the
stock and optional native-engine timeout to at most45 seconds. Preserve the
actual chosen routes; missing or Windows-incompatible native builds stay
unavailable. For the default stock YOLO capability, retain `flow_asset` for
Recommended **and** add `flow_fine_asset` for Perfectionist. Both public assets
must have their exact source/hash records. Capability availability is never
widened by the bridge. Temperature requires its actual matching retained model
or full-base model; absence remains a real blocker.

An independent matching `native_reference` may be attached to the private config
between offer and consume after real native preparation/export. All other
configuration fields must remain identical to the offered configuration. The
actual generator/parity harness validates that reference against the exact
native request parameters, context, files and provenance. Omitting a reference
allows real generation but cannot qualify it. Existing Recommended R8 evidence
is never changed or reused for Perfectionist.

Example lead-only Windows-local invocation, using existing explicit `$Python`,
`$Source`, `$Root`, `$Context`, `$Config` and actual `$Session` paths:

```powershell
& $Python -I -S (Join-Path $Source 'scripts\v1-windows-parameter-bridge.py') `
  --op offer --root $Root --context $Context --config $Config
# Relay only returned offer, then collect actual native saved session locally.
& $Python -I -S (Join-Path $Source 'scripts\v1-windows-parameter-bridge.py') `
  --op consume --root $Root --context $Context --config $Config --native-session $Session
# Relay only returned actual status. New terminal trial: repeat --op offer.
```

The session file may contain the direct saved object or exactly
`{"v1_session": <saved object>}`. Initial consumption requires native
`phase:"requested"`, sequence0, no prepared/result/receipt/intent, exact request
and the full original offer. Do not edit this saved object to pass validation.
All input digests, original sessions, event copies, config versions, source
hashes and returned metadata remain under the owned per-request trial directory.
Only the qualification relay approved by the lead/user may move bounded offer,
request and status metadata; this bridge performs no network or target access.

`generator_dispatched` records the real Coordinator reaching its job-directory
and router dispatch path; it never claims an executable ran. The separate
`executable_invocation_recorded` records an actual invocation file, while
`artifact_generated` requires the actual retained artifact to pass byte/hash
verification. `qualified` additionally revalidates the independent parity report.
No call spy or bare true flag establishes execution/qualification. Source-only
unit fixtures exercise real offline capability-blocked paths and are not native
operator or Windows generation evidence.
