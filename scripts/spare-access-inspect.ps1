$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class Issue4Inspect {
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
 [DllImport("user32.dll", SetLastError=true)] public static extern IntPtr OpenInputDesktop(uint f, bool inherit, uint access);
 [DllImport("user32.dll")] public static extern bool CloseDesktop(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool GetUserObjectInformation(IntPtr h, int idx, StringBuilder s, int length, out int needed);
}
'@
$Foreground = [Issue4Inspect]::GetForegroundWindow()
[uint32]$ForegroundPid = 0
$Thread = [Issue4Inspect]::GetWindowThreadProcessId($Foreground, [ref]$ForegroundPid)
$Desktop = [Issue4Inspect]::OpenInputDesktop(0, $false, 1)
$Name = [Text.StringBuilder]::new(256)
[int]$Needed = 0
$DesktopName = 'unavailable'
if ($Desktop -ne [IntPtr]::Zero) {
 [Issue4Inspect]::GetUserObjectInformation($Desktop, 2, $Name, 512, [ref]$Needed) | Out-Null
 $DesktopName = $Name.ToString()
 [Issue4Inspect]::CloseDesktop($Desktop) | Out-Null
}
$Orca = @(Get-CimInstance Win32_Process -Filter "Name='orca-slicer.exe'" | Select-Object ProcessId, ExecutablePath, CommandLine)
@{hostname=$env:COMPUTERNAME; session_id=[Diagnostics.Process]::GetCurrentProcess().SessionId; foreground_pid=$ForegroundPid; foreground_process=if($ForegroundPid){(Get-Process -Id $ForegroundPid).ProcessName}else{'unavailable'}; input_desktop=$DesktopName; orca_processes=$Orca; local_appdata=$env:LOCALAPPDATA; free_system_disk_gb=[Math]::Round((Get-PSDrive C).Free / 1GB,2)} | ConvertTo-Json -Compress -Depth 4
