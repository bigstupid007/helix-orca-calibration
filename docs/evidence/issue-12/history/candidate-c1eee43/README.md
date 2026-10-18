# Preserved successful physical baseline native checkpoint

This preserves the complete synthetic native evidence at
`c1eee4374fb0286e1a3973d8e29107bfc64ee99f` byte-for-byte: eleven viewports,
88 frames and eleven storage snapshots. It predates the compact 1×1 widget and
pending-result preservation corrections. Verify it with that commit's verifier,
not the current source-bound verifier.

This capture uses synthetic job/authorization/clock/completion inputs. The later
real Founder-initiated physical success at the same baseline is separately
recorded under `../../physical-first/`; this native capture is not hardware proof.
The baseline commit and private generated/rollback artifacts remain recoverable.
