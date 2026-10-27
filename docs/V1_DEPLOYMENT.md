# Separate local deployment boundary

> **Superseded deployment limitation:** the October 25 Founder amendment is the
> explicit authority for the owner-local runtime, reversible beta.12 plugin
> deployment, and controlled five-calibration physical validation after the
> required gates. The amended authorization is exact-config, exact-package, and
> exact-target bound; it creates no service, public listener, firewall rule,
> account, or credential. Older “future approval” text below is historical.
> [Amendment record](V1_CURRENT_UPSTREAM_REBASE.md).

The amendment authorizes only the controlled candidate described here: exact
SPARE package/configuration, existing trusted-LAN access, the qualified Founder
Voron identity/configuration and five native-Start-only calibration prints. It
does not authorize an automatic Start or Save, a public listener, access or
credential changes, firmware/printer configuration mutation, unrelated work,
startup registration, service installation, or another printer. The default
CLI remains action-disabled unless all typed target and owner-private approval
bindings agree.

`--deployment-authorization` is the separate local gate. For this one amended
run, a private helper may materialize the record from the Founder's explicit
Issue #14 comment `6401570758`; it may not infer or broaden that authority. A
native request, result, configuration flag or qualification report alone cannot
enable the adapter.

The current exact local record schema is `helix-orca-v1-local-deployment/v2`.
It binds `approved`, `native_start_only`, `approval_reference`, `config_sha256`,
`runtime_sha256`, and `package_manifest_sha256`. Both booleans must be true and
the reference must identify explicit owner approval. The record must be an existing ordinary
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
is dispatched at construction. Every current job still needs the exact qualified
build/route and installed-package closure, processor-ready output, exact immutable
bytes, current exact-file target-fit analysis, any required warning acknowledgement,
empty queue/idle preflight, native Confirm and a distinct deliberate native Start.
No universal target macro signature is required.
Cancellation has its own separately confirmed native intent and owned-job checks.

Activation remains gated on the current Windows/build/runtime and target
qualifications recorded in the completion ledger. Once they pass, the amendment
is the separate deployment authority for exactly five controlled calibrations.
Each physical receipt stays distinct from synthetic UI/HTTP and lifecycle proof;
none of this is a general production-security qualification.
