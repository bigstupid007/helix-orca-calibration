# Temperature communication contract

This directory defines the transport-neutral Issue #8 contract embedded by
`scripts/temperature-communication-companion.py`. The generated Orca plugin is
one dependency-free Python file. It keeps all accepted October 15 capabilities
and adds **Helix Temperature Communication (no printing)**. The accepted
`plugin/helix_calibration.py` and `scripts/orca-oct15-plugin.py` remain immutable.

All shared artifacts live under the `communication` child of the directory
returned by `orca.host.plugin.storage()`. On the qualified isolated Windows
runtime this is `orca_plugins\plugin_data\helix_calibration\communication`.
No absolute path is part of a payload.

| File | Owner | Contract |
| --- | --- | --- |
| `outbox.json` | Orca companion | `{schema: "helix-orca-temperature-outbox/v1", target, payload}` |
| `inbox.json` | Relay | Exact `helix-orca-temperature-selection/v1` result |
| `receipt.json` | Orca companion | Exact result fields with schema `helix-orca-temperature-ack/v1` |
| `state.json` | Orca companion | Canonical private recovery state |
| `delivery.json` | Relay, optional | Exact correlated `helix-orca-temperature-delivery/v1` status |

The session payload has exactly these keys:

`schema`, `simulation_only`, `not_applied`, `request_id`, `origin_id`,
`context_sha256`, `file_sha256`, `file`, `file_bytes`, `printer`, `filament`,
`process`, `nozzle_mm`, `saved_current`, `edited_current`, `current`, `setting`,
`choices`, `expires_at`, and `ttl_seconds`.

The protocol binds every flattened context value back to the immutable full
target and its digest. The result contains exactly `schema`, `simulation_only`,
`not_applied`, `request_id`, `origin_id`, `context_sha256`, `file_sha256`,
`file`, `file_bytes`, `setting`, and `value`. Receipt fields are identical.

The reusable API is:

- `validate_forward_payload`, `validate_outbox`, `validate_selection_result`,
  `make_ack`, and `validate_ack` for exact schema checks;
- `bounded_read_json` and `atomic_write_json` for fixed-name bounded artifacts;
- `make_forward_payload` for secure correlated request creation; and
- `TemperatureCommunicationState` for durable new-calibration, file selection,
  send/retry, restart recovery, inbox polling, local commit, and acknowledgement.

Optional delivery status contains exactly `schema`, `request_id`, `origin_id`,
`context_sha256`, and `phase`. Phase is one of `delivering`,
`waiting_selection`, `waiting_companion`, `delivered`, `retrying`, or `failed`.
The companion maps those values to fixed local text. It displays no relay error,
hostname, or other untrusted status text. Invalid or stale status cannot replace
the last validated status, pending target, or committed result instructions.

State is flushed before an outbox is published. A validated result is flushed
to canonical local state before `receipt.json` is written. Retry reuses the
same immutable request. A locally committed result does not free the live
communication slot: the panel keeps polling until the relay's exact correlated
`delivered` phase proves the native acknowledgement was persisted. That
terminal fact is stored in canonical local state and cannot regress due to a
later waiting, retry, or failure artifact.

Only the user's **Keep original profile** action starts a new origin and clears
prior communication artifacts. It is locked while the slot is unexpired and
not delivered, including after local result commit. At the original absolute
expiry, the user may explicitly retire that slot and begin another; expiry
never silently clears or mutates the old request, receipt, or NOT APPLIED
instructions. Stale, mismatched, malformed, and conflicting returns are
rejected without changing the committed result or writing a new receipt.
