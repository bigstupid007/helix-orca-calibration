# Separate local deployment boundary

The V1 program builds code and isolated evidence. It does not authorize physical
activation, installation on the printer, another print, profile writeback,
credentials/access changes or startup registration. The default CLI and Windows
wrapper use no action-enabled job adapter. All current review operation stays
within that boundary.

`--deployment-authorization` is implemented for a later separately approved
local deployment. No helper creates or signs an operational approval, and this program has not
created an operational approval record. Unit tests use synthetic records against
local fixtures only. A native request, result, configuration flag
or parity report alone cannot enable the adapter.

The exact local record schema is `helix-orca-v1-local-deployment/v1`, with only
`schema`, `approved`, `native_start_only`, `approval_reference`, `config_sha256`
and `runtime_sha256`. Both booleans must be true and the reference must identify
separate explicit owner approval. The record must be an existing ordinary
absolute owner-private file of 1..65536 bytes. All ancestor links/reparse points,
network/device paths, alternate streams and shared/foreign ACLs are refused.
Direct CLI validation enforces privacy independently of the Windows wrapper.
This is a trusted local owner control, not a cryptographic authorization service.

`config_sha256` is the canonical digest of the exact private configuration.
`runtime_sha256` is `integration.v1_deployment.runtime_fingerprint(entry)`: the
canonical manifest digest of the actual CLI, local `integration/v1_*.py` code,
and the existing WebSocket framing source. Changes to the runtime or its
configuration invalidate that record. The Windows wrapper separately retains
and rechecks the exact approval file bytes/path before child launch.

Construction additionally requires `owned_jobs.actions_enabled:true`, validated
physical/configuration pins, the reviewed Orca machine/nozzle context and the
explicit native event channel pointing at that same origin/version. No action
is dispatched at construction. Every actual job still needs independently
verified native parity, accepted target macro signature, exact immutable bytes,
empty queue/idle preflight, native Confirm and a distinct deliberate native Start.
Cancellation has its own separately confirmed native intent and owned-job checks.

Activation remains pending Founder acceptance and separate deployment authority.
The candidate's native/Orca review notices, exact deployed product hashes,
private storage/access envelope, transport-security limitations, matching target
configuration and original profile preservation must all be reconciled at that
boundary. Current synthetic UI/HTTP and Windows lifecycle proof must never be
presented as a new physical print or production security qualification.
