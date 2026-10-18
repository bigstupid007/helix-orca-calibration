# Isolated qualification infrastructure. Never uploads or controls a printer.
param([Parameter(Mandatory=$true)][string]$Bundle,
      [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$BundleSha256,
      [ValidatePattern('^[a-z0-9-]{1,64}$')][string]$RunName='candidate-temperature-r4')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Base=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration'
$Stage=Join-Path $Base 'v1-qualification'
if(-not(Test-Path -LiteralPath (Join-Path $Stage 'data\.helix-orca-v1-qualification'))){throw 'V1 isolation marker missing'}
$Exe=Join-Path $Base 'issue-6-oct15-6a7763f\runtime\orca-slicer.exe'
$ExpectedExe='e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
if((Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash.ToLowerInvariant()-ne$ExpectedExe){throw 'Pinned October 15 executable differs'}
if((Get-FileHash -LiteralPath $Bundle -Algorithm SHA256).Hash.ToLowerInvariant()-ne$BundleSha256){throw 'Generation bundle digest differs'}
$Root=Join-Path $Stage $RunName
if(Test-Path -LiteralPath $Root){throw 'Refusing existing generation output directory'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip=[IO.Compression.ZipFile]::OpenRead($Bundle)
try{
 foreach($Entry in $Zip.Entries){
  if($Entry.FullName-notmatch '^[a-z-]+\.(json|stl|3mf)$'-or$Entry.Length-gt20000000){throw 'Unexpected bundle entry'}
 }
 if($Zip.Entries.Count-gt20){throw 'Too many bundle entries'}
}finally{$Zip.Dispose()}
New-Item -ItemType Directory -Path $Root|Out-Null
Expand-Archive -LiteralPath $Bundle -DestinationPath $Root
$Manifest=Get-Content -Raw -LiteralPath (Join-Path $Root 'generation-bundle.json')|ConvertFrom-Json
if($Manifest.source_commit-ne'6a7763f08d1a175a464a00ce13f0b5a815662fc4'-or$Manifest.executable_sha256-ne$ExpectedExe){throw 'Generation source/runtime differs'}
$Snapshot=Get-Content -Raw -LiteralPath (Join-Path $Root 'snapshot.json')|ConvertFrom-Json
if($Snapshot.effective.curr_bed_type-ne'High Temp Plate'){throw 'This bounded Windows case requires explicit matching High Temp Plate'}
$Models=@('model.stl','model.3mf')|Where-Object {Test-Path -LiteralPath (Join-Path $Root $_) -PathType Leaf}
if(@($Models).Count-ne1){throw 'Exactly one preserved STL or per-object 3MF model is required'}
$ModelName=@($Models)[0]
$Model=Join-Path $Root $ModelName
foreach($Name in @('orca-data','slice-output','webview2')){New-Item -ItemType Directory -Path (Join-Path $Root $Name)|Out-Null}
$Arguments=@('--datadir',(Join-Path $Root 'orca-data'),'--load-settings',((Join-Path $Root 'machine.json')+';'+(Join-Path $Root 'process.json')),
 '--load-filaments',(Join-Path $Root 'filament.json'),'--curr-bed-type','High Temp Plate','--arrange','1','--orient','0','--strict',
 '--outputdir',(Join-Path $Root 'slice-output'),'--export-settings',(Join-Path $Root 'slice-output\effective.json'),
 '--export-3mf','prepared.3mf','--slice','0',$Model)
foreach($Argument in $Arguments){if($Argument.Contains('"')-or$Argument.EndsWith('\')){throw 'Unsupported argument quoting'}}
$CommandLine=($Arguments|ForEach-Object {'"'+$_+'"'})-join' '
# This command runs inside an ephemeral qualification worker process; no user or
# machine environment is changed. Orca data and browser state are job-local.
$env:WEBVIEW2_USER_DATA_FOLDER=Join-Path $Root 'webview2'
$Out=Join-Path $Root 'stdout.log';$Err=Join-Path $Root 'stderr.log'
$Started=[DateTime]::UtcNow
$Process=Start-Process -FilePath $Exe -WorkingDirectory $Root -ArgumentList $CommandLine -PassThru -RedirectStandardOutput $Out -RedirectStandardError $Err -WindowStyle Hidden
$null=$Process.Handle # Retain the native handle before a short-lived child exits.
$Record=@{schema='helix-orca-v1-windows-cli/v1';pid=$Process.Id;started_at=$Started.ToString('o');executable_sha256=$ExpectedExe;bundle_sha256=$BundleSha256;script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant();argv=$Arguments;deadline_seconds=45;physical_actions=$false}
$Record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $Root 'invocation.json') -Encoding utf8
if(-not$Process.WaitForExit(45000)){
 # The retained Process handle identifies only our newly launched CLI child.
 $Process.Kill();[void]$Process.WaitForExit(5000)
 $Record['timeout']=$true
 $Record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $Root 'result-record.json') -Encoding utf8
 throw 'Isolated CLI exceeded its 45-second deadline'
}
$ExitCode=$Process.ExitCode
if($null-eq$ExitCode){throw 'Owned CLI exit status unavailable; output is not qualification'}
$Record['exit_code']=$ExitCode
$Record['elapsed_seconds']=([DateTime]::UtcNow-$Started).TotalSeconds
$Record['files']=@(Get-ChildItem -LiteralPath (Join-Path $Root 'slice-output') -File|ForEach-Object {@{name=$_.Name;size=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}})
$Record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $Root 'result-record.json') -Encoding utf8
$Record|ConvertTo-Json -Depth 5 -Compress
if($ExitCode-ne0){throw 'Stock Windows CLI failed; retained local logs are authoritative'}
