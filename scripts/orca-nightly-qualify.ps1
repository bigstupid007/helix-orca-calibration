[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OrcaDir,

    [string]$DataDir,

    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedCommit = "210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3"
$ExpectedExeSha256 = "8d9db0bec8b8a8e0ad0a70485daaf7ee9fa1c88d5f1395f92eabf0430ce0339b"
$ExpectedDllSha256 = "5b71e5dbf2f6b3319d6d69f597e3aa3dbf9403f9ea63f93c3c72dc294efba0a4"
$MarkerName = ".helix-orca-issue-4-qualification"

function Resolve-FullPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
}

function Assert-FileHash([string]$Path, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required nightly file is missing: $Path"
    }
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) {
        throw "SHA-256 mismatch for $Path. Expected $Expected; got $Actual."
    }
}

$OrcaDir = Resolve-FullPath $OrcaDir
$RepositoryRoot = Resolve-FullPath $RepositoryRoot
$ExePath = Join-Path $OrcaDir "orca-slicer.exe"
$DllPath = Join-Path $OrcaDir "OrcaSlicer.dll"
$PluginSource = Join-Path $RepositoryRoot "plugin\helix_calibration.py"

Assert-FileHash $ExePath $ExpectedExeSha256
Assert-FileHash $DllPath $ExpectedDllSha256

if (-not (Test-Path -LiteralPath $PluginSource -PathType Leaf)) {
    throw "Qualification plugin is missing: $PluginSource"
}
if ([string]::IsNullOrWhiteSpace($DataDir)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw "LOCALAPPDATA is unavailable; pass an explicit isolated -DataDir."
    }
    $DataDir = Join-Path $env:LOCALAPPDATA "HelixOrcaCalibration\issue-4-nightly-210bc927"
}
$DataDir = Resolve-FullPath $DataDir

$ForbiddenDataDirs = @($OrcaDir)
if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
    $ForbiddenDataDirs += Join-Path $env:APPDATA "OrcaSlicer"
}
if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $ForbiddenDataDirs += Join-Path $env:LOCALAPPDATA "OrcaSlicer"
}
$ForbiddenDataDirs = $ForbiddenDataDirs | ForEach-Object { Resolve-FullPath $_ }
if ($ForbiddenDataDirs -contains $DataDir) {
    throw "Refusing to use an existing Orca installation or the nightly program directory as -DataDir: $DataDir"
}

$MarkerPath = Join-Path $DataDir $MarkerName
if (Test-Path -LiteralPath $DataDir) {
    $ExistingEntries = @(Get-ChildItem -LiteralPath $DataDir -Force)
    if ($ExistingEntries.Count -gt 0 -and -not (Test-Path -LiteralPath $MarkerPath -PathType Leaf)) {
        throw "Refusing non-empty unmarked data directory: $DataDir"
    }
} else {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

$MarkerPayload = @{
    purpose = "Helix-Orca Issue #4 isolated Orca nightly qualification"
    source_commit = $ExpectedCommit
} | ConvertTo-Json
Set-Content -LiteralPath $MarkerPath -Value $MarkerPayload -Encoding utf8

$PluginDir = Join-Path $DataDir "orca_plugins"
$InputDir = Join-Path $DataDir "qualification-inputs"
$OutputDir = Join-Path $DataDir "qualification-output"
New-Item -ItemType Directory -Path $PluginDir -Force | Out-Null
New-Item -ItemType Directory -Path $InputDir -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
Copy-Item -LiteralPath $PluginSource -Destination (Join-Path $PluginDir "helix_calibration.py") -Force

$ProfileSource = Join-Path $RepositoryRoot "testdata\orca-profiles"
$ProfileDestination = Join-Path $InputDir "orca-profiles"
if (-not (Test-Path -LiteralPath $ProfileSource -PathType Container)) {
    throw "Qualification profile directory is missing: $ProfileSource"
}
if (Test-Path -LiteralPath $ProfileDestination) {
    Remove-Item -LiteralPath $ProfileDestination -Recurse -Force
}
Copy-Item -LiteralPath $ProfileSource -Destination $ProfileDestination -Recurse

$PluginHash = (Get-FileHash -LiteralPath $PluginSource -Algorithm SHA256).Hash.ToLowerInvariant()
$LaunchRecord = @{
    schema = "helix-orca-nightly-launch/v1"
    recorded_at_utc = [DateTime]::UtcNow.ToString("o")
    source_commit = $ExpectedCommit
    executable = $ExePath
    executable_sha256 = $ExpectedExeSha256
    library_sha256 = $ExpectedDllSha256
    data_dir = $DataDir
    plugin_source = $PluginSource
    plugin_sha256 = $PluginHash
    output_dir = $OutputDir
    arguments = @("--datadir", $DataDir)
}
$LaunchRecordPath = Join-Path $DataDir "qualification-launch.json"
$LaunchRecord | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $LaunchRecordPath -Encoding utf8

Write-Host "Verified Orca nightly commit: $ExpectedCommit"
Write-Host "Isolated data directory: $DataDir"
Write-Host "Staged plugin SHA-256: $PluginHash"
Write-Host "Manual export directory: $OutputDir"
Write-Host "Launch record: $LaunchRecordPath"

$Process = Start-Process -FilePath $ExePath -ArgumentList @("--datadir", ('"{0}"' -f $DataDir)) -PassThru
Write-Host "Started isolated Orca process $($Process.Id). Existing Orca settings were not selected."
