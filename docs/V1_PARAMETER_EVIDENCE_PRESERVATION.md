# Preserved parameter-control evidence across generator changes

The accepted Program #14 functional-control proof remains bound to commit
`66bfaf6bb8df9a453c1ee85fbb43ba827daeda5b`. It establishes actual 800×480
native pointer, drag and keypad operation; the five changed parameter requests;
unchanged DirectoryEvents and Windows Coordinator request objects; and the
action-free review boundary. It does not qualify a later generator build.

Generator-only work changes `integration/v1_engine.py` and native engine inputs,
so the original verifier's intentionally broad all-`v1_*.py` current-source
comparison no longer describes the useful retained claim. Rerunning the UI only
because an engine module changed would add no evidence about native controls.
Relabeling the old blocked statuses as current generator results would be equally
incorrect.

`scripts/v1-parameter-preservation.py` therefore applies two separate gates:

1. It requires exact SHA-256 bytes for the accepted verifier, promoted report,
   operator record and Windows parity record. It rechecks their fixed run,
   request/digest, action, lifecycle, private-frame-attestation and historical
   396-frame semantics.
2. It requires the current complete `integration/v1-native/` UI/catalog
   inventory, request contract, runtime, DirectoryEvents transport, routing,
   review harness and operator driver to match the accepted source manifest.

Generator, parity, deployment, owned-job and companion implementation files are
outside the current-equivalence claim. Changes there require current source,
build, artifact and strict native-parity evidence. The old Temperature, PA,
Retraction and MVS blocked records and the old Flow prepared record remain exact
observations at `66bfaf6`; this preservation gate makes no current disposition
claim for any of them.

Run the dependency-free gate with:

```sh
python3 scripts/v1-parameter-preservation.py
```

Focused negative tests change each immutable/equivalent boundary, add or remove
native UI files, and confirm that the current generator-only engine difference
does not invalidate the retained control-selection proof.
