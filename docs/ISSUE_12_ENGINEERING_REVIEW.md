# Issue #12 engineering review and validation

Authority is [Issue #12](https://github.com/bigstupid007/helix-orca-calibration/issues/12),
accepted Issue #8 bidirectional communication and Issue #10 baseline policy.
Shared Development System main was verified at
`2328bc55709d6dd1705fdec339d4a3982a81ffe2`; application main baseline is
`89165d15993ccfcd065b299e1980bb19749fdcaf`. Work occurred in a separate worktree,
preserving the dirty canonical checkout.

## Independent code review

A fresh-context independent reviewer reviewed the candidate. Safety-heavy
lifecycle/transport work and independent review used higher reasoning effort
because mistaken state or identity handling could later dispatch a real command.

Exact-code verdicts: **runtime/runner PASS at `0fe55cf`** and **qualification
driver PASS at `dbd3a6e`**, with no remaining material safety or contract
findings. The reviewer independently ran all **41 focused fake-only tests** at
the final driver commit and checked whitespace for the correction range.
Review covered the final request/file/configuration/machine/
version binding, receipt-only behavior, explicit native Start, one-shot journal,
status/history normalization, dual completion proof, failure/cancellation,
recovery and original-context result/receipt contract.

Material findings corrected before that verdict included macro argument values,
recovered journal and sequence binding, history-lag handling, disconnected
publication, native waiting/terminal restart, replay retirement, original Start
window and authorization ordering. The final runner binds one immutable private
grant digest before offering a request. Awaiting Start requires that same live
grant; expiry durably fails and publishes a terminal state. Replacement grants
cannot inherit old taps, and a tap cannot precede the authorized offer.
Post-dispatch recovery accepts the same expired grant only for observation and
never redispatches Start.

The native evidence driver uses the existing private Unix control socket and
native synthetic pointer APIs within Docker `--network none`. Its prompt
press/release pair avoids host process-launch delays becoming long presses.
Pinned beta.9 defers writes by 500 ms. Positive checks wait for actual persisted
state; negative invariants must remain true throughout a five-second settling
window. The independently reviewed final driver is `dbd3a6e`, including a
regression for delayed forbidden writes. Neither
change modifies the accepted harness or introduces a hardware route.

## Required checks

The full repository suite passes: **230 tests**. The focused 41 are included in
that total. Accepted beta.4 evidence (11 targets), accepted Issue #8 communication
evidence (11 targets / 33 frames), shell syntax and static harness contracts
also pass unchanged. The final source-bound beta.9 readiness matrix passes
all eleven targets with 88 frames and eleven persisted storage snapshots;
its promoted source/fixture/runtime/hash verifier passes.
[AI Product Preflight](ISSUE_12_PRODUCT_PREFLIGHT.md) also passes for the isolated
native flow and actual Windows UI with synthetic job/completion inputs.
[The readiness report](TEMPERATURE_PRINT_READINESS.md) owns that status.

A separate offline evidence workflow verifies the new matrix and retained
communication proof on PRs. The accepted CI workflow remains byte-identical
because its hash is part of the retained beta.4 evidence contract.

## Limits and disposition

Code review, native mock success and Windows NOT APPLIED return do not prove a
physical print. The exact native export has a 12-minute model estimate, but
all opaque printer macro overhead—including cold startup and normal end
behavior—must be bounded in the final proposed total. That total remains
unqualified; no physical qualification/grant was issued. Exact-spool label
confirmation and separate Founder review/authorization remain required.

No physical print, heating, motion, macro execution, file upload/queue,
printer configuration/firmware change, profile writeback, physical derivative install,
Alpha adoption, merge or release occurred. The existing trusted-LAN limitation
and private evidence boundary remain unchanged.
