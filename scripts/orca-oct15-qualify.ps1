[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OrcaDir,
    [string]$DataDir,
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ExpectedCommit = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
$ExpectedExeSha256 = 'e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
$ExpectedDllSha256 = '3c5b2accbdc7d8ad2eab9cf21705a9b04f2e0be9961cfe3016c7376c6fadc157'
$MarkerName = '.helix-orca-issue-6-oct15-qualification'

function Resolve-FullPath([string]$Path) {
    return [IO.Path]::GetFullPath($Path).TrimEnd([IO.Path]::DirectorySeparatorChar)
}

function Assert-FileHash([string]$Path, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required nightly file is missing: $Path" }
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) { throw "SHA-256 mismatch for $Path. Expected $Expected; got $Actual." }
}

$OrcaDir = Resolve-FullPath $OrcaDir
$RepositoryRoot = Resolve-FullPath $RepositoryRoot
$ExePath = Join-Path $OrcaDir 'orca-slicer.exe'
$DllPath = Join-Path $OrcaDir 'OrcaSlicer.dll'
$PluginSource = Join-Path $RepositoryRoot 'plugin\helix_calibration.py'
Assert-FileHash $ExePath $ExpectedExeSha256
Assert-FileHash $DllPath $ExpectedDllSha256
if (-not (Test-Path -LiteralPath $PluginSource -PathType Leaf)) { throw "Qualification plugin is missing: $PluginSource" }

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA is unavailable; pass an isolated -DataDir.' }
    $DataDir = Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\issue-6-nightly-6a7763f'
}
$DataDir = Resolve-FullPath $DataDir
$Forbidden = @($OrcaDir)
if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) { $Forbidden += Join-Path $env:APPDATA 'OrcaSlicer' }
if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { $Forbidden += Join-Path $env:LOCALAPPDATA 'OrcaSlicer' }
$Forbidden = @($Forbidden | ForEach-Object { Resolve-FullPath $_ })
if ($Forbidden -contains $DataDir) { throw "Refusing to use an existing Orca installation or the nightly program directory as -DataDir: $DataDir" }

$MarkerPath = Join-Path $DataDir $MarkerName
if (Test-Path -LiteralPath $DataDir) {
    $Existing = @(Get-ChildItem -LiteralPath $DataDir -Force)
    if ($Existing.Count -gt 0 -and -not (Test-Path -LiteralPath $MarkerPath -PathType Leaf)) {
        throw "Refusing non-empty unmarked data directory: $DataDir"
    }
} else { New-Item -ItemType Directory -Path $DataDir | Out-Null }

@{purpose='Helix-Orca Issue #6 isolated October 15 Orca qualification'; source_commit=$ExpectedCommit} |
    ConvertTo-Json | Set-Content -LiteralPath $MarkerPath -Encoding utf8
$InputDir = Join-Path $DataDir 'qualification-inputs'
$PluginDir = Join-Path $InputDir 'plugin'
$OutputDir = Join-Path $DataDir 'qualification-output'
New-Item -ItemType Directory -Path $PluginDir -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
Copy-Item -LiteralPath $PluginSource -Destination (Join-Path $PluginDir 'helix_calibration.py') -Force
$ProfileSource = Join-Path $RepositoryRoot 'testdata\orca-profiles'
$ProfileDestination = Join-Path $InputDir 'orca-profiles'
if (-not (Test-Path -LiteralPath $ProfileSource -PathType Container)) { throw "Qualification profiles are missing: $ProfileSource" }
if (Test-Path -LiteralPath $ProfileDestination) { Remove-Item -LiteralPath $ProfileDestination -Recurse -Force }
Copy-Item -LiteralPath $ProfileSource -Destination $ProfileDestination -Recurse

$WebViewDir = Join-Path $DataDir 'webview2'
$Record = @{
    schema='helix-orca-oct15-launch/v1'; recorded_at_utc=[DateTime]::UtcNow.ToString('o')
    source_commit=$ExpectedCommit; executable=$ExePath; executable_sha256=$ExpectedExeSha256
    library_sha256=$ExpectedDllSha256; data_dir=$DataDir; plugin_sha256=(Get-FileHash $PluginSource -Algorithm SHA256).Hash.ToLowerInvariant()
    output_dir=$OutputDir; arguments=@('--datadir',$DataDir); webview2_user_data_folder=$WebViewDir
}
$Record | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $DataDir 'qualification-launch.json') -Encoding utf8

$Start = [Diagnostics.ProcessStartInfo]::new()
$Start.FileName = $ExePath
$Start.WorkingDirectory = $OrcaDir
$Start.Arguments = '--datadir "' + $DataDir + '"'
$Start.UseShellExecute = $false
$Start.EnvironmentVariables['WEBVIEW2_USER_DATA_FOLDER'] = $WebViewDir
$Process = [Diagnostics.Process]::Start($Start)
Write-Host "Started isolated October 15 Orca process $($Process.Id) for $ExpectedCommit."

