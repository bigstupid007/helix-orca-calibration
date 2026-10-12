# Qualification infrastructure: compare hashes only; never read profile contents as product data.
$ErrorActionPreference='Stop'
$Stage=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\issue-4-windows'
if(-not(Test-Path (Join-Path $Stage '.helix-orca-validation-stage'))){throw 'Missing validation marker'}
$Before=Get-Content -Raw (Join-Path $Stage 'normal-orca-before.json')|ConvertFrom-Json
$Root=Join-Path $env:APPDATA 'OrcaSlicer'
if($Before.normal_data_dir-ne$Root){throw 'Normal data baseline path mismatch'}
$Files=@(Get-ChildItem -LiteralPath $Root -Recurse -File|Where-Object {
 $_.Extension-in@('.json','.conf','.ini')-and$_.FullName-notmatch '\\(cache|logs?|orca_plugins|plugins)\\'
}|Sort-Object FullName)
$Rows=@($Files|ForEach-Object {$_.FullName.Substring($Root.Length)+' '+(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash})
$Sha=[Security.Cryptography.SHA256]::Create()
try{$Digest=([BitConverter]::ToString($Sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($Rows-join"`n"))))).Replace('-','').ToLowerInvariant()}finally{$Sha.Dispose()}
$Report=@{recorded_at_utc=[DateTime]::UtcNow.ToString('o');file_count=$Files.Count;aggregate_sha256=$Digest;baseline_sha256=$Before.aggregate_sha256;unchanged=($Digest-eq$Before.aggregate_sha256-and$Files.Count-eq$Before.settings_profile_file_count);scope='Normal Orca .json/.conf/.ini excluding cache, logs, plugins; relative path, space, uppercase file hash, LF, no trailing LF'}
$Report|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $Stage 'normal-orca-after.json') -Encoding utf8
$Report|ConvertTo-Json -Depth 4 -Compress
if(-not$Report.unchanged){throw 'Normal settings/profile fingerprint changed; inspect the material exception'}
