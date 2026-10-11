# Test infrastructure only. Run once in ordinary PowerShell on Spare's desktop.
# Reuses existing LAN SSH authentication; no listener, installation, or elevation.
[CmdletBinding()]
param(
    [string]$BridgePath = '__BRIDGE_PATH__'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:COMPUTERNAME -ine 'Spare') { throw 'This worker may run only on Spare.' }
$Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$Principal = [Security.Principal.WindowsPrincipal]::new($Identity)
if ($Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Use ordinary, unelevated PowerShell in the signed-in desktop.'
}
$SessionId = [Diagnostics.Process]::GetCurrentProcess().SessionId
if ($SessionId -le 0) { throw 'A signed-in interactive Windows session is required.' }
if ($BridgePath -notmatch '^/home/dev/\.cache/helix-orca-calibration/windows-access/[a-f0-9]{64}/spare-access\.py$') {
    throw 'Unexpected devbox bridge path.'
}
$AccessDir = Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\windows-access'
New-Item -ItemType Directory -Path $AccessDir -Force | Out-Null
$KnownHosts = Join-Path $AccessDir 'devbox_known_hosts'
# Pin the existing devbox LAN host identity without changing normal SSH configuration.
$HostLine = '192.168.1.114 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFrlkyMQJErEnaCSC9EwcCdgHyZYBJPtWLVcu1bOFrkp'
[IO.File]::WriteAllText($KnownHosts, $HostLine + "`n", ([Text.UTF8Encoding]::new($false)))
$Ssh = (Get-Command ssh.exe -ErrorAction Stop).Source
$Info = New-Object Diagnostics.ProcessStartInfo
$Info.FileName = $Ssh
$Info.Arguments = '-T -o BatchMode=yes -o StrictHostKeyChecking=yes -o HostKeyAlgorithms=ssh-ed25519 -o ClearAllForwardings=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o ConnectTimeout=8 -o UserKnownHostsFile="' + $KnownHosts + '" dev@192.168.1.114 "python3 ' + $BridgePath + ' serve"'
$Info.UseShellExecute = $false
$Info.RedirectStandardInput = $true
$Info.RedirectStandardOutput = $true
$Info.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
$Transport = New-Object Diagnostics.Process
$Transport.StartInfo = $Info
if (-not $Transport.Start()) { throw 'Could not start the existing SSH client.' }
$Writer = [IO.StreamWriter]::new($Transport.StandardInput.BaseStream, [Text.UTF8Encoding]::new($false))
$Writer.AutoFlush = $true
$Hello = @{
    protocol = 'helix-orca-spare-access/v1'
    hostname = $env:COMPUTERNAME
    identity = $Identity.Name
    session_id = $SessionId
    is_admin = $false
    powershell = $PSVersionTable.PSVersion.ToString()
}
$Writer.WriteLine(($Hello | ConvertTo-Json -Compress))
Write-Host 'Spare testing access is running over LAN SSH. Keep this window open.'
Write-Host 'Only approved qualification commands are permitted. Ctrl+C closes access.'
try {
    while ($null -ne ($Line = $Transport.StandardOutput.ReadLine())) {
        if ($Line.Length -gt 1048576) { throw 'Oversized bridge message.' }
        $Request = $Line | ConvertFrom-Json
        $Response = @{ request_id = $Request.request_id; exit_code = 0 }
        if ($Request.op -eq 'probe') {
            $Response.result = $Hello
        } elseif ($Request.op -eq 'stop') {
            $Writer.WriteLine(($Response | ConvertTo-Json -Compress -Depth 6))
            break
        } elseif ($Request.op -eq 'exec') {
            if ($Request.timeout_seconds -lt 1 -or $Request.timeout_seconds -gt 60 -or $Request.script.Length -gt 8192) {
                throw 'Invalid command bound.'
            }
            # Native child remains in this visible desktop session, never Session 0.
            $Script = '$ErrorActionPreference = "Stop"; [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false); ' + $Request.script
            $Encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Script))
            $ChildInfo = New-Object Diagnostics.ProcessStartInfo
            $ChildInfo.FileName = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
            $ChildInfo.Arguments = '-NoProfile -NonInteractive -EncodedCommand ' + $Encoded
            $ChildInfo.UseShellExecute = $false
            $ChildInfo.RedirectStandardOutput = $true
            $ChildInfo.RedirectStandardError = $true
            $ChildInfo.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
            $ChildInfo.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
            $Child = New-Object Diagnostics.Process
            $Child.StartInfo = $ChildInfo
            try {
                if (-not $Child.Start()) { throw 'Could not start qualification command.' }
                $OutTask = $Child.StandardOutput.ReadToEndAsync()
                $ErrTask = $Child.StandardError.ReadToEndAsync()
                if (-not $Child.WaitForExit([int]$Request.timeout_seconds * 1000)) {
                    $Child.Kill()
                    if (-not $Child.WaitForExit(5000)) { throw 'Direct command child did not stop after timeout.' }
                    $Response.exit_code = 124
                    $Response.error = 'Qualification command exceeded its bound; its direct child was stopped.'
                } else { $Response.exit_code = $Child.ExitCode }
                # A launched GUI descendant can retain inherited pipe handles after
                # this command exits. Never wait indefinitely for pipe EOF.
                $OutComplete = $OutTask.Wait(750)
                $ErrComplete = $ErrTask.Wait(750)
                $Out = if ($OutComplete) { $OutTask.Result } else { '' }
                $Err = if ($ErrComplete) { $ErrTask.Result } else { '' }
                $Response.stdout = $Out.Substring(0, [Math]::Min($Out.Length, 100000))
                $Response.stderr = $Err.Substring(0, [Math]::Min($Err.Length, 10000))
                $Response.output_truncated = ($Out.Length -gt 100000 -or $Err.Length -gt 10000 -or -not $OutComplete -or -not $ErrComplete)
                if (-not $OutComplete -or -not $ErrComplete) {
                    $Response.exit_code = 125
                    $Response.error = 'A descendant retained an output pipe; capture was bounded and may be incomplete. Inspect target state before retrying.'
                }
            } finally { $Child.Dispose() }
        } else { throw 'Unsupported testing operation.' }
        $Writer.WriteLine(($Response | ConvertTo-Json -Compress -Depth 6))
    }
} finally {
    $Writer.Dispose()
    if (-not $Transport.HasExited) { $Transport.Kill() }
    $Transport.Dispose()
}
Write-Host 'Spare testing access is closed.'
