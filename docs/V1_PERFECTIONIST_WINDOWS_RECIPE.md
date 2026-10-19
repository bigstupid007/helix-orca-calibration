# Bounded Windows-local YOLO Perfectionist validation

This is a lead-executed qualification recipe, not executed evidence. It uses
only the existing isolated October 15 Windows target/access. Full context,
profiles, native projects, G-code, raw reports and logs remain on Windows.
Recommended R8 artifacts and `v1-windows-stock-yolo.py` remain unchanged.

1. Verify the existing marked V1 datadir/process and October 15 executable SHA
   `e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759`.
   Use a new source/output directory below the existing V1 qualification root.
   Stage only the current `integration/v1_contract.py`, `v1_generation.py`,
   `v1_parity.py`, plus `scripts/v1-native-reference.py`, `v1-windows-parity.py`
   and `v1-windows-yolo-perfectionist.py`, preserving directory structure.
   Retain the archive/file hashes. Use the existing explicitly identified Python
   installation with `-I -S`; install nothing. Preserve the pre-run normal
   settings fingerprint and original isolated profile selections.
2. Before native calibration, confirm the supported plugin snapshot matches the
   retained original context, canonical SHA
   `3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c`.
   Saved identity, edited copy and effective configuration stay distinct. Do not
   use the post-calibration recipe edits as the original context.
3. In the actual isolated native GUI choose **Calibration → Flow ratio**.
   Source entry: `MainFrame.cpp:3592–3594` calls `run_calibration(FlowRatio)`;
   `4618–4624` opens the native **Flow Ratio Calibration** dialog. The existing
   automation entry is `scripts/v1-windows-review.py`: guarded `windows`, `tree`,
   `click`, `keys`, `capture`, `resize`, with `--passive-menu` for native menus.
   It exposes no symbolic calibration function. The menu uses `wxID_ANY`, so
   do not invent a stable numeric command ID or call `Plater` from Python.
   Inspect current native frames/tree before choosing coordinates or keys.
4. Select the fourth test choice, **YOLO (Perfectionist)**, native zero-based
   index 3, and **Archimedean Chords**, index 0. Capture a Windows-local PNG
   showing both selections before pressing OK. `calib_dlg.cpp:1872–1883`
   dispatches `calib_flowrate(true,2,ipArchimedeanChords)`. Slice through native
   **Slice plate**, then **Export G-code** to a new Windows-local filename.
   Retain a second distinct PNG showing the native preparation/export action,
   exported G-code and optional native 3MF. Never import a generated candidate
   as this reference. Do not invoke upload, print or hardware actions.
5. Register/inspect the independent reference locally using the commands below.
   The native inspector requires the complete original context and two distinct
   actual PNGs. Stop if native invariants fail. Expected patch set is sixteen
   offsets −0.04 through +0.035 by 0.005; do not assume symmetric endpoints.
6. Use the existing public runtime asset or stage its public bytes separately:
   `resources/calib/filament_flow/Orca-LinearFlow_fine.3mf`, exact SHA
   `15f3e750122e466389932c0c4242299ef26d8a416dc4ac0673b8864960c151dd`.
   Do not substitute Recommended's asset. Run the new production helper below.
   It rehashes the executable, public asset, independent reference, manifest
   and every evidence file; provenance must bind `{pass:2}` and original inputs.
   It calls real `v1_generation.generate` with 45-second slicing and a new
   job-local datadir, then requires the unchanged exact executable comparison
   and both invariant checks. No injected runner, remote qualification flag,
   warning waiver or geometry approximation is accepted.
7. Retain all local outputs. Return only the helper's bounded scalar summary,
   exact digests and controlled failure code, never full profiles/G-code/raw
   report or exception text. Exit 0 means qualified exact parity; exit 2 means
   blocked/unqualified and retained differences remain authoritative. Restore
   only the isolated transient native test state and verify original selections
   and normal settings fingerprint remain unchanged. No physical readiness,
   deployment or merge follows from a parity pass.

Example commands below use explicitly bound Windows-local paths. `$Python`,
`$Source`, `$Context`, `$Native`, `$DialogPng`, `$ExportPng`, `$ReferenceDir`,
`$Executable`, `$FineAsset` and `$Output` must be assigned by the lead from the
existing isolated target. Reference/output directories must not already exist.

```powershell
$Parameters = Join-Path (Split-Path $Native) 'perfectionist-parameters.json'
[IO.File]::WriteAllText($Parameters, '{"pass":2}', [Text.Encoding]::ASCII)
& $Python -I -S (Join-Path $Source 'scripts\v1-native-reference.py') `
  --calibration flow_ratio_yolo --parameters $Parameters `
  --context $Context --native $Native `
  --native-evidence $DialogPng --native-evidence $ExportPng `
  --output-dir $ReferenceDir
# Inspect bounded summary: invariants_passed must be true; qualified stays false.
$Manifest = Join-Path $ReferenceDir 'native-reference.json'
$NativeSha = (Get-FileHash -LiteralPath $Native -Algorithm SHA256).Hash.ToLowerInvariant()
$ManifestSha = (Get-FileHash -LiteralPath $Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
& $Python -I -S (Join-Path $Source 'scripts\v1-windows-yolo-perfectionist.py') `
  --context $Context --executable $Executable --asset $FineAsset `
  --native $Native --native-sha256 $NativeSha `
  --native-manifest $Manifest --native-manifest-sha256 $ManifestSha `
  --output-dir $Output
```

The previously used `v1-windows-generation.ps1` is unsuitable for this check:
it fixes `--arrange 1`, whereas the corrected production YOLO recipe preserves
its native group via job-local build-item translation and `--arrange 0`.
The new helper keeps those production semantics and binds the layout, model,
invocation, request, prepared object, source files and parity report in local
`generation-provenance.json`. This recipe authorizes no additional target work;
the lead schedules its actual execution inside the existing approved boundary.
