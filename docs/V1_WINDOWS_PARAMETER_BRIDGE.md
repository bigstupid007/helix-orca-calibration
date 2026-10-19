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

## Approved bounded native metadata relay

The Founder explicitly approved a bounded test relay in the program chat.
`scripts/v1-windows-parameter-relay.py` is a separate foreground qualification
wrapper; it leaves the live `v1-native-review.py` source unchanged and starts no
listener/service. The lead schedules it only after the native review's serial
release. It imports that review's exact owned-session verifier and transport-only
fragment delivery hook, checks the frozen source/fixture hashes and active exact
ManagedRun container, and requires the local review coordinator to remain idle
with its same fresh offer and no retained request. Windows owns the actual
trial offers; the local review coordinator cannot consume their different nonces.

The relay sends only actual saved native `v1_session` metadata through the
existing approved Windows test bridge. Its PowerShell command is bounded to8192
characters, base64-encodes at most5000 bytes, creates a new owned Windows session
file and invokes the pinned public bridge in the foreground. The existing
worker deadline and at-most45-second generator deadline remain in force.
The relay itself runs at most900 seconds and ends before the active native
review's lifecycle deadline. It never rewrites native storage, queues a print,
creates a Windows service or relays Confirm/Start. Actual pre-start Cancel may
be relayed to its real coordinator.

Windows stdout now includes independently read actual DirectoryEvents request
and event digest, a separately reread coordinator-journal request/digest, and
actual source-file hashes. The relay requires all three request objects/digests
to match the original native request and verifies the event including any actual
Cancel intent. The exact real status is delivered back through the approved
transport hook. It requires saved native phase/sequence/prepared readback and a
visible native job overlay plus captured terminal frame before the next offer.
Use Windows trial order Temperature, PA Pattern, Retraction, MVS, then Flow.
The final qualified Flow `review` completes the parameter trial only after exact
native status readback, visible job overlay and real frame capture. The relay
then exits with `result_completion:"final-qualified-review-no-start"`, retaining
both coordinators' real states and issuing no Cancel, Start or next offer.
A nonfinal qualified Review never advances automatically. The current native
product has no pre-start Cancel; adding one solely for this test is outside this
correction's scope. This exception completes parameter proof, not a print or job.

Private bounded invocation/result metadata is retained under the managed
review's XDG-state `view/windows-parameter-relay/`; independent request/event/
journal/status/source traces are written to `view/parameter-traces/<request_id>.json`
for the existing viewer's read-only proof endpoint. Full profiles, configuration,
G-code, projects and raw parity reports never move from Windows.

Lead-only invocation after staging the final bridge bytes **before any offer**:

```bash
python3 scripts/v1-windows-parameter-relay.py \
  --windows-python 'C:\existing\python.exe' \
  --windows-source 'C:\existing\qualification\parameter-source' \
  --windows-root 'C:\existing\qualification\new-parameter-bridge' \
  --windows-context 'C:\existing\qualification\original-context.json' \
  --windows-config 'C:\existing\qualification\private-generator-config.json' \
  --bridge-sha256 '<exact staged bridge SHA-256>' --seconds 600 --trials 5
```

All paths are explicit existing approved local Windows paths. `--trials 0` means
wait within the same hard deadline; at most10 completed trials may be requested.
A new native review run is needed if frozen sources change. Implementing this
wrapper is not evidence that it ran; source-only tests exercise no Windows or
native target and establish no qualification.

The separate relay's `parameter-traces` include explicit
`actual_windows_coordinator:true`, `actual_windows_transport:"DirectoryEvents"`,
`actual_windows_bridge_sha256`, `actual_windows_config_file_sha256`,
`actual_windows_offer_sha256`, `actual_windows_context_sha256`,
`actual_windows_source_files`, `actual_windows_metadata_sha256`, and
`actual_windows_qualified`/`qualified`. The PowerShell wrapper hashes the private
config and public bridge independently before/after the operation and returns
only those digests beside the unchanged raw bridge JSON. It never reserializes
request numbers through PowerShell JSON conversion. The envelope is retained in
XDG state and its canonical digest binds the trace. Request/event/DirectoryEvents/
journal hashes are checked independently before status delivery. These fields
let the final operator driver reject local-coordinator-shaped traces.
