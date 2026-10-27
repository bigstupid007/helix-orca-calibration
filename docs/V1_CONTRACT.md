# V1 shared wire contract — Build Program #14

> **Current contract authority:** the October 25 amendment adds explicit V2
> schemas alongside immutable historical V1 records. V2 binds an originating
> 1-based filament slot/preset, build-level route qualification, structured
> warnings, exact-job completion, and Orca's official dirty/unsaved preset
> transaction. It does not silently reinterpret historical `not_applied` or
> exact-request evidence. [Amendment record](V1_CURRENT_UPSTREAM_REBASE.md).

Status: v1 foundation; not qualification or physical authorization. Lead owns
`integration/v1_contract.py`, runtime, companion and integration. Stock worker
owns `integration/v1_generation.py`, `integration/v1_parity.py`, generation CLI
and focused tests. Engine worker owns `integration/v1_engine.py` and source
capability findings. Native worker owns `integration/v1-native/` and V1-only
builder/capture/test scripts. Accepted sources/evidence remain unchanged.

## Human workflow and fidelity

The launch instruction explicitly approves choose, configure, request generation,
confirm prepared job, deliberate Start, monitor, evaluate and return on native
Helix, with selected profiles/preparation/result on Orca. These are the only
required human steps. Technical IDs, receipts, hashes and qualification are
internal; do not turn them into required user input. Historical V1 results
remain `NOT APPLIED`; current V2 results use only the official originating
filament transaction and remain dirty/unsaved until the owner chooses Orca's
normal Save. No implementation may invent direct profile-file writeback or a
physical-test grant beyond the exact amendment authority.

## Common objects

All JSON is UTF-8, finite, bounded to 1 MiB per message, canonicalized with
sorted keys and compact separators for SHA-256. Unknown schema/fields reject.
IDs are lowercase 32-hex and hashes 64-hex. Numbers exclude booleans and NaN.

- **Context** `helix-orca-v1-context/v1`: `origin_id`, `runtime` (version/build),
  `printer`, `process`, `filament` (each saved/edited identities and serialized
  resolved config maps), `effective` (merged serialized map), `nozzle_mm`.
  A missing saved/edited/effective read remains unavailable; generation fails
  rather than replacing one with another. Full snapshots stay on the Orca host.
  Context digest covers this complete immutable object. UI receives names and
  relevant values; profile changes never retarget an existing job/result.
- **Request** `helix-orca-v1-request/v1`: `request_id`, `origin_id`,
  `context_sha256`, `calibration`, `parameters`, `created_at`, `expires_at`,
  `not_applied: true`. IDs: `temperature`, `flow_ratio_yolo`,
  `pressure_advance_pattern`, `retraction`, `max_volumetric_speed`.
  Parameters use numeric native units and are validated per verified native
  behavior; generators must additionally enforce their supported envelope.
- **Prepared job** `helix-orca-v1-prepared/v1`: `request_id`, `origin_id`,
  `context_sha256`, `request_sha256`, `calibration`, `parameters`,
  `artifact` (`name`, `size`, `sha256`), `generator` (`build`, `route`),
  `parity` (`qualified`, `report_sha256`, `reason`), `not_applied: true`.
  Artifact may be null only for a blocked job. Generated-but-unqualified output
  never means Ready. Qualified requires independently verified exact inputs,
  actual artifact bytes and retained matching native-UI comparison report.
  Report must bind request-independent generation inputs (calibration,
  parameters, context/runtime/profile digests) and both executable artifacts.
- **Intent** `helix-orca-v1-intent/v1`: `request_id`, `origin_id`,
  `prepared_sha256`, `action` (`confirm`, `start`, `cancel`), `intent_id`.
  Confirm and Start are separate actions. Request receipt cannot synthesize
  either. Start is bound to exact preparation and a later explicit screen tap;
  production action adapter additionally requires local enablement, exact
  printer/config qualification and existing one-shot safeguards.
- **Status** `helix-orca-v1-status/v1`: `request_id`, `origin_id`, `sequence`,
  `phase`, `message`, `prepared` (object or null), `job_id` (string or null).
  Phases: `requested`, `preparing`, `blocked`, `review`, `confirmed`, `starting`,
  `printing`, `verifying`, `complete`, `cancelled`, `failed`, `uncertain`,
  `returning`, `delivered`. Sequence strictly increases for changed status.
  Duplicates are harmless; stale status cannot reverse terminal/retained result.
  Optional `monitor` contains independently nullable `elapsed_s` (0 through 31 days)
  and `progress` (0 through 1), both finite. It is informational only: completion
  and evaluation require exact-job independent successful history, even at 100%.
  Missing or invalid monitoring data is unavailable, never estimated.
- **Result** `helix-orca-v1-result/v1`: `request_id`, `origin_id`,
  `context_sha256`, `prepared_sha256`, `job_id`, `completion_sha256`,
  `setting`, `value`, `not_applied: true`. Exact-job independent successful
  completion is mandatory. Setting/value depend on calibration. Immutable after
  selection; late events cannot replace it. Receipt binds canonical result
  digest and original origin; only originating Orca commits delivery.

## Native contract and transport

Native plugin ID remains `orcacal` in a separately generated derivative. Native
subjects/events use only documented beta.9 APIs. V1 forward events:
`helix_orca_v1.context.v1`, `.status.v1`, `.ack.v1` (full prefix on each).
Storage key `v1_session` contains `request`, `intent`, `result`, `receipt`.
Native request/intent/result are read by the coordinator from storage; receipt
is sent to native only after originating Orca durably commits exact result.
No test worker, arbitrary shell or command execution is a product protocol.

Native context payload: `{schema:"helix-orca-v1-offer/v1", origin_id,
context_sha256, printer, process, filament, nozzle_mm, capabilities:[{id,
available, reason}], defaults:{id:{...}}}`. Names are plain text. Availability
means generator can attempt preparation, not prequalified G-code. Native
request is emitted only by Generate; confirmation only by Confirm; Start only
by a later Start tap while confirmed and qualified. Status/prepared validation
must bind request/origin/context/parameters. No physical Start adapter is
activated in this Build Program. Offline fixtures must be labeled as such.

## Python adapter interfaces

`integration/v1_contract.py`: `canonical(value) -> bytes`, `digest(value)`,
`validate_request(value, now=None)`, `validate_context(value)`,
`validate_prepared(value, request)`, `CALIBRATIONS`, `DEFAULTS`, `ContractError`.

Generation: `generate(request, snapshot, output_dir, config) -> prepared`.
It may raise a specific `GenerationBlocked` or return artifact-null blocked
preparation. Runner executable/profile/asset paths are explicit configuration,
never hidden runtime reads of normal user settings. No network in generators.
Parity has independent reference provenance and never accepts a caller's bare
`qualified: true`. Runtime verifies report/artifact binding, rehashes bytes,
persists before publishing and fails closed on crash/uncertain side effects.

## Verified beta.9 wire adaptation

Beta.9 Lua has no wall-clock or SHA-256 API. The offer additionally carries
runtime-generated single-use `request_id`, `created_at`, `expires_at`; the
coordinator enforces expiration. Status additionally carries `prepared_sha256`,
`completion_sha256` (nullable) and `evaluation` (nullable, `{setting,options,unit}`).
The plugin structurally matches every request/prepared identity and retains the
coordinator-supplied digest token; it does not claim to compute a hash.
ACK `helix-orca-v1-ack/v1` carries `request_id`, `origin_id`, `result_sha256`,
`result` (the exact committed result object), `not_applied:true`. Native compares
all retained result fields before accepting. This preserves the Founder flow
without an unsupported Lua clock/hash API. The trusted coordinator verifies
all digests and independently owned successful completion; native events alone
are not physical qualification or action authority.

## Functional parameter correction

The current [parameter correction](V1_PARAMETER_CORRECTION.md) is controlling for
editable setup controls and operator acceptance. YOLO `pass` is integer1 Recommended
or2 Perfectionist; fixed additive sample sets differ and require distinct parity.
The offer may include `extruder_type` (`direct_drive`, `bowden`, `unavailable`) to
select source-verified PA defaults from effective context only. This is setup metadata,
not a printer/preset write or execution flag. Required numeric fields use free entry
inside explicit V1 bounds; invalid input remains visible with a correctable error.
A valid request for a known blocked capability is still retained by the coordinator
with exact selected values and the actual blocker. No qualification bypass is added.
