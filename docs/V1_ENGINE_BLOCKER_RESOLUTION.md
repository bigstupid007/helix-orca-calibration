# Native-engine blocker resolution

This continuation preserves the approved October 15 source, original effective
configuration, executable parity policy, and all physical safeguards. No native
engine route becomes qualified merely because its source builds or its counts
match a retained independent reference.

## Retained-profile warning

The exact baseline's `GCodeProcessor.cpp:7855–7878` checks the highest commanded
bed temperature against each used filament's retained nonzero vitrification
temperature. Warning `1000C001` is legitimate for the retained 60°C bed / 55°C
threshold combination. It is not conditional on Bambu vendor identity.

The adapter continues to reject every native warning and nonzero processor
error. Its Python transport now exposes a bounded explanation and exact warning
code instead of only “native generation failed.” Unknown warnings also remain
fatal. Raw diagnostic text is not echoed to the UI. The retained artifact gets
an unqualified parity disposition; no Prepared job is created. Neither the
threshold nor a bed command is changed to make this combination pass.

A warning-free combination requires an explicitly selected, unchanged profile
and its own matching context and independently prepared native reference. A
different profile does not qualify the original context or silently replace it.

## Preparation audit

The PA Pattern junction-deviation branch in native Plater requires Marlin
firmware. The current adapter deliberately requires Klipper, so that omitted
branch is unreachable inside its supported envelope; expanding firmware support
requires independent qualification. Retraction and MVS configuration assignments
match the exact native preparation families. Native slicing, processor checks,
and executable parity remain separate gates for every exact supported input.

## Focused validation

Fourteen synthetic transport tests pass, including warning/error rejection,
request-bound blocker provenance, no profile mutation, and malformed or linked
diagnostic rejection. These tests exercise fail-closed behavior; they are not
Windows build evidence, independent native UI evidence, or generator parity.
