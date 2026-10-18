#Requires -Version 5.1
<#
V1 per-user lifecycle wrapper. It never installs startup entries, services or listeners.
The internal supervisor starts only the fixed repository coordinator with typed paths.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('start','status','stop','plan','supervise')][string]$Action,
    [Parameter(Mandatory=$true)][string]$RuntimeRoot,
    [string]$PythonExe,
    [string]$RepoRoot,
    [string]$Storage,
    [string]$Config,
    [switch]$MoonrakerEvents,
    [ValidateRange(1,30)][int]$WaitSeconds=10,
    [ValidatePattern('^[a-f0-9]{32}$')][string]$RunId
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows is required; no action was performed.' }
$script:Sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$script:Utf8=New-Object Text.UTF8Encoding($false)
$script:LogBytes=1048576

function Get-FullLocalPath([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -match '[\x00-\x1f"]' -or $Value.StartsWith('\\')) { throw 'An explicit ordinary local absolute path is required.' }
    if (-not [IO.Path]::IsPathRooted($Value) -or $Value -notmatch '^[A-Za-z]:\\') { throw 'Drive-relative and network paths are unsupported.' }
    $full=[IO.Path]::GetFullPath($Value)
    if ($full.Length -gt 3) { return $full.TrimEnd('\') }
    return $full
}
function Assert-NoReparse([string]$Path) {
    $cursor=$Path
    while (-not [string]::IsNullOrEmpty($cursor)) {
        if ([IO.File]::Exists($cursor) -or [IO.Directory]::Exists($cursor)) {
            if (([IO.File]::GetAttributes($cursor) -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse points are unsupported in lifecycle paths.' }
        }
        $next=[IO.Path]::GetDirectoryName($cursor)
        if ($next -eq $cursor) { break }
        $cursor=$next
    }
}
function Get-ExistingPath([string]$Value,[bool]$Directory) {
    $path=Get-FullLocalPath $Value
    Assert-NoReparse $path
    if ($Directory -and -not [IO.Directory]::Exists($path)) { throw 'An explicit existing directory is required.' }
    if (-not $Directory -and -not [IO.File]::Exists($path)) { throw 'An explicit existing file is required.' }
    return $path
}
function Assert-PrivateRoot([bool]$Create) {
    $local=Get-FullLocalPath ([Environment]::GetFolderPath('LocalApplicationData'))
    if (-not $script:Root.StartsWith($local+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'RuntimeRoot must be a new dedicated directory below this user LocalApplicationData.' }
    Assert-NoReparse $script:Root
    if (-not [IO.Directory]::Exists($script:Root)) {
        if (-not $Create) { return $false }
        [void][IO.Directory]::CreateDirectory($script:Root)
        $acl=New-Object Security.AccessControl.DirectorySecurity
        $acl.SetOwner($script:Sid)
        $acl.SetAccessRuleProtection($true,$false)
        $inherit=[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
        $rule=New-Object Security.AccessControl.FileSystemAccessRule($script:Sid,'FullControl',$inherit,'None','Allow')
        $acl.AddAccessRule($rule)
        Set-Acl -LiteralPath $script:Root -AclObject $acl
    }
    $actual=(Get-Acl -LiteralPath $script:Root)
    if ($actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:Sid.Value -or -not $actual.AreAccessRulesProtected) { throw 'Existing RuntimeRoot is not an owner-private dedicated directory; its ACL was not changed.' }
    foreach ($rule in $actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -ne $script:Sid.Value) { throw 'Existing RuntimeRoot grants another principal access; its ACL was not changed.' }
    }
    return $true
}
function Assert-PrivateFile([string]$Path) {
    Assert-NoReparse $Path
    if ([IO.File]::Exists($Path)) {
        $acl=(Get-Acl -LiteralPath $Path)
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:Sid.Value) { throw 'Lifecycle file owner differs.' }
        foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
            if ($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -ne $script:Sid.Value) { throw 'Lifecycle file is not private.' }
        }
    }
}
function Read-Control([string]$Path) {
    Assert-PrivateFile $Path
    if (-not [IO.File]::Exists($Path) -or (Get-Item -LiteralPath $Path).Length -gt 65536) { throw 'Bounded regular lifecycle record required.' }
    return ([IO.File]::ReadAllText($Path,$script:Utf8) | ConvertFrom-Json)
}
function Write-Control([string]$Path,$Value) {
    Assert-PrivateFile $Path
    $bytes=$script:Utf8.GetBytes(($Value | ConvertTo-Json -Depth 12 -Compress))
    if ($bytes.Length -gt 65536) { throw 'Lifecycle record exceeds 64KiB.' }
    $temporary=Join-Path $script:Root ('.write-'+[Guid]::NewGuid().ToString('N'))
    $backup=Join-Path $script:Root ('.replace-'+[Guid]::NewGuid().ToString('N'))
    $replaced=$false
    try {
        $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
        if ([IO.File]::Exists($Path)) { [IO.File]::Replace($temporary,$Path,$backup); $replaced=$true }
        else { [IO.File]::Move($temporary,$Path) }
    } finally {
        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
        if ($replaced -and [IO.File]::Exists($backup)) { [IO.File]::Delete($backup) }
    }
}
function Open-ControlLock {
    $path=Join-Path $script:Root 'control.lock'
    Assert-NoReparse $path
    $until=[DateTime]::UtcNow.AddSeconds(10)
    do {
        try { return [IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }
        catch [IO.IOException] { if ([DateTime]::UtcNow -ge $until) { throw 'Another lifecycle operation is active.' }; Start-Sleep -Milliseconds 50 }
    } while ($true)
}
function Quote-Argument([string]$Value) {
    # Windows CommandLineToArgvW/CRT quoting, including trailing backslashes.
    $escaped=[regex]::Replace($Value,'(\\*)"','$1$1\"')
    $escaped=[regex]::Replace($escaped,'(\\+)$','$1$1')
    return '"'+$escaped+'"'
}
function Join-Arguments([string[]]$Values) { return (($Values | ForEach-Object { Quote-Argument $_ }) -join ' ') }
function Get-RecordPath { return (Join-Path $script:Root 'current.json') }
function Assert-Record($Record) {
    if ($Record.schema -ne 'helix-orca-v1-windows-runtime/v1' -or $Record.run_id -notmatch '^[a-f0-9]{32}$' -or $Record.owner_sid -ne $script:Sid.Value) { throw 'Lifecycle ownership record is malformed or foreign.' }
    $expected=Join-Path $script:Root ('stop.'+$Record.run_id+'.json')
    if ($Record.stop_file -cne $expected) { throw 'Stop-file ownership differs.' }
}
function Get-ProcessIdentity([int]$ProcessId,[string]$ExpectedExe,[string]$ExpectedCommand) {
    $process=Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $null }
    try { $started=$process.StartTime.ToUniversalTime().Ticks.ToString() }
    catch {
        if ($null -eq (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return $null }
        throw
    }
    try {
        $cim=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$ProcessId) -OperationTimeoutSec 3
        if ($null -eq $cim -or [string]::IsNullOrEmpty($cim.ExecutablePath) -or [string]::IsNullOrEmpty($cim.CommandLine)) { throw 'Process identity is unavailable; no process will be adopted or terminated.' }
        $owner=Invoke-CimMethod -InputObject $cim -MethodName GetOwnerSid -OperationTimeoutSec 3
        if ($owner.ReturnValue -ne 0 -or $owner.Sid -ne $script:Sid.Value) { throw 'Process owner differs; no process will be adopted or terminated.' }
    } catch {
        # Graceful exit can race either CIM call. Only absence or a replaced PID
        # resolves that race; unavailable identity for the same process still fails.
        $again=Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($null -eq $again -or $again.StartTime.ToUniversalTime().Ticks.ToString() -cne $started) { return $null }
        throw
    }
    if (-not [string]::Equals($cim.ExecutablePath,$ExpectedExe,[StringComparison]::OrdinalIgnoreCase) -or $cim.CommandLine -cne $ExpectedCommand) { return $null }
    return [ordered]@{ pid=$ProcessId; started_utc_ticks=$started; executable=$cim.ExecutablePath; command_line=$cim.CommandLine; owner_sid=$owner.Sid }
}
function Start-DetachedSupervisor([string]$Exe,[string]$Arguments,[string]$Directory) {
    # Explicit handle allowlist: the supervisor inherits NUL only, never the
    # calling terminal/test worker's output pipes or any unrelated open handle.
    if (-not ('HelixOrcaV1.NativeLaunch' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
namespace HelixOrcaV1 {
 public static class NativeLaunch {
  [StructLayout(LayoutKind.Sequential)] struct Security {
   public int length; public IntPtr descriptor; [MarshalAs(UnmanagedType.Bool)] public bool inherit;
  }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup {
   public int cb; public string reserved, desktop, title;
   public int x,y,width,height,countX,countY,fill,flags;
   public short show, reservedBytes; public IntPtr reservedData, input, output, error;
  }
  [StructLayout(LayoutKind.Sequential)] struct Extended { public Startup startup; public IntPtr attributes; }
  [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr process, thread; public int pid, tid; }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern IntPtr CreateFileW(string name,uint access,uint share,ref Security security,uint creation,uint flags,IntPtr template);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool InitializeProcThreadAttributeList(IntPtr list,int count,int flags,ref IntPtr size);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool UpdateProcThreadAttribute(IntPtr list,uint flags,IntPtr attribute,IntPtr value,IntPtr size,IntPtr previous,IntPtr returned);
  [DllImport("kernel32.dll")] static extern void DeleteProcThreadAttributeList(IntPtr list);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern bool CreateProcessW(string app,StringBuilder command,IntPtr processSecurity,IntPtr threadSecurity,bool inherit,uint flags,IntPtr environment,string directory,ref Extended startup,out ProcessInfo info);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
  static void Check(bool ok) { if(!ok) throw new Win32Exception(Marshal.GetLastWin32Error()); }
  public static Process Launch(string exe,string command,string directory) {
   var security=new Security { length=Marshal.SizeOf(typeof(Security)),inherit=true };
   IntPtr nul=CreateFileW("NUL",0xC0000000,3,ref security,3,0x80,IntPtr.Zero);
   if(nul==new IntPtr(-1)) throw new Win32Exception(Marshal.GetLastWin32Error());
   IntPtr list=IntPtr.Zero, handles=IntPtr.Zero; bool initialized=false;
   var info=new ProcessInfo();
   try {
    IntPtr size=IntPtr.Zero;
    InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);
    list=Marshal.AllocHGlobal(size); Check(InitializeProcThreadAttributeList(list,1,0,ref size)); initialized=true;
    handles=Marshal.AllocHGlobal(IntPtr.Size); Marshal.WriteIntPtr(handles,nul);
    Check(UpdateProcThreadAttribute(list,0,new IntPtr(0x20002),handles,new IntPtr(IntPtr.Size),IntPtr.Zero,IntPtr.Zero));
    var startup=new Extended(); startup.startup.cb=Marshal.SizeOf(typeof(Extended));
    startup.startup.flags=0x100; startup.startup.input=nul; startup.startup.output=nul; startup.startup.error=nul; startup.attributes=list;
    Check(CreateProcessW(exe,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,true,0x08080000,IntPtr.Zero,directory,ref startup,out info));
    return Process.GetProcessById(info.pid);
   } finally {
    if(info.thread!=IntPtr.Zero) CloseHandle(info.thread);
    if(info.process!=IntPtr.Zero) CloseHandle(info.process);
    if(initialized) DeleteProcThreadAttributeList(list);
    if(list!=IntPtr.Zero) Marshal.FreeHGlobal(list);
    if(handles!=IntPtr.Zero) Marshal.FreeHGlobal(handles);
    CloseHandle(nul);
   }
  }
 }
}
'@
    }
    return [HelixOrcaV1.NativeLaunch]::Launch($Exe,((Quote-Argument $Exe)+' '+$Arguments),$Directory)
}
function Get-NewIdentity($Process,[string]$Exe,[string]$Command) {
    $until=[DateTime]::UtcNow.AddSeconds(2)
    do {
        try {
            $identity=Get-ProcessIdentity $Process.Id $Exe $Command
            if ($null -ne $identity) { return $identity }
        } catch { if ([DateTime]::UtcNow -ge $until) { throw } }
        if ($Process.HasExited) { throw 'New process exited before identity verification.' }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $until)
    throw 'New process identity did not become available.'
}
function Test-Identity($Identity) {
    if ($null -eq $Identity) { return $false }
    $actual=Get-ProcessIdentity ([int]$Identity.pid) $Identity.executable $Identity.command_line
    return ($null -ne $actual -and $actual.started_utc_ticks -ceq $Identity.started_utc_ticks -and $actual.owner_sid -eq $Identity.owner_sid)
}
function Test-StopRequest($Record) {
    if (-not [IO.File]::Exists($Record.stop_file)) { return $false }
    $request=Read-Control $Record.stop_file
    $names=@($request.PSObject.Properties.Name | Sort-Object)
    if (($names -join ',') -cne 'run_id,schema' -or $request.schema -ne 'helix-orca-v1-stop/v1' -or $request.run_id -cne $Record.run_id) { throw 'Existing stop file is not this exact owned stop request.' }
    return $true
}
function Get-Status {
    if (-not [IO.File]::Exists((Get-RecordPath))) { return [ordered]@{ state='not-started'; actions_enabled=$false; test_worker_required=$false } }
    $record=Read-Control (Get-RecordPath); Assert-Record $record
    $pythonAlive=Test-Identity $record.python
    $supervisorAlive=Test-Identity $record.supervisor
    $state=if ($pythonAlive) { if (Test-StopRequest $record) { 'stopping' } else { 'running' } } elseif ($supervisorAlive) { if (Test-StopRequest $record) { 'stopping' } elseif ($null -ne $record.python) { 'finishing' } else { 'starting' } } elseif ($record.state -eq 'attention-required') { 'attention-required' } else { 'stopped' }
    return [ordered]@{ state=$state; run_id=$record.run_id; python_pid=if ($pythonAlive) { $record.python.pid } else { $null }; supervisor_pid=if ($supervisorAlive) { $record.supervisor.pid } else { $null }; last_recorded_state=$record.state; exit_code=$record.exit_code; actions_enabled=$false; test_worker_required=$false; logs=Join-Path $script:Root 'stdout.log' }
}
function Write-BoundedLog([string]$Name,[string]$Text) {
    if ($Name -notin @('stdout','stderr','supervisor')) { throw 'Unknown owned log.' }
    $path=Join-Path $script:Root ($Name+'.log'); $backup=Join-Path $script:Root ($Name+'.1.log')
    Assert-PrivateFile $path; Assert-PrivateFile $backup
    foreach ($existing in @($path,$backup)) {
        if ([IO.File]::Exists($existing) -and (Get-Item -LiteralPath $existing).Length -gt $script:LogBytes) { throw 'Unexpected oversized log was preserved; archive it manually before restarting.' }
    }
    $data=$script:Utf8.GetBytes($Text)
    if ($data.Length -gt $script:LogBytes) { $data=$data[($data.Length-$script:LogBytes)..($data.Length-1)] }
    if ([IO.File]::Exists($path) -and (Get-Item -LiteralPath $path).Length+$data.Length -gt $script:LogBytes) {
        if ([IO.File]::Exists($backup)) { [IO.File]::Delete($backup) }
        [IO.File]::Move($path,$backup)
    }
    $stream=[IO.File]::Open($path,[IO.FileMode]::Append,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $stream.Write($data,0,$data.Length) } finally { $stream.Dispose() }
}
function Get-PythonArguments($Record) {
    $arguments=@('-u',$Record.entry,'--storage',$Record.storage,'--config',$Record.config,'--state',$Record.coordinator_state,'--run-id',$Record.run_id,'--stop-file',$Record.stop_file)
    if ($Record.moonraker_events) { $arguments+='--moonraker-events' }
    return (Join-Arguments $arguments)
}
function Set-FinalState([string]$Id,[string]$State,$ExitCode,[string]$Message) {
    $lock=Open-ControlLock
    try {
        $record=Read-Control (Get-RecordPath); Assert-Record $record
        if ($record.run_id -cne $Id) { throw 'Lifecycle identity changed during supervision.' }
        $record.state=$State; $record.exit_code=$ExitCode; $record.message=$Message
        Write-Control (Get-RecordPath) $record
    } finally { $lock.Dispose() }
}
function Invoke-Supervisor {
    $storageLock=$null; $process=$null; $owned=$false
    try {
        $lock=Open-ControlLock
        try {
            $record=Read-Control (Get-RecordPath); Assert-Record $record
            if ($record.run_id -cne $RunId -or $record.launcher_sha256 -cne (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -or -not (Test-Identity $record.supervisor)) { throw 'Supervisor identity differs from the explicit launch.' }
            if ($record.supervisor.pid -ne $PID) { throw 'This supervisor does not own the recorded process.' }
            $fixedEntry=Get-ExistingPath (Join-Path (Get-ExistingPath $record.repo $true) 'scripts\v1-runtime.py') $false
            if ($record.entry -cne $fixedEntry -or $record.coordinator_state -cne (Join-Path $script:Root 'coordinator')) { throw 'Only the fixed repository coordinator and owned journal path may run.' }
            [void](Get-ExistingPath $record.python_exe $false); [void](Get-ExistingPath $record.storage $true); [void](Get-ExistingPath $record.config $false)
            if ($record.entry_sha256 -cne (Get-FileHash -LiteralPath $record.entry -Algorithm SHA256).Hash.ToLowerInvariant() -or $record.config_sha256 -cne (Get-FileHash -LiteralPath $record.config -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'Reviewed launch inputs changed before start.' }
            $storageLockPath=Join-Path $record.storage '.v1-windows-launcher.lock'; Assert-NoReparse $storageLockPath
            $storageLock=[IO.File]::Open($storageLockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
            if (Test-StopRequest $record) { $record.state='stopped'; $record.exit_code=0; Write-Control (Get-RecordPath) $record; return }
            $start=New-Object Diagnostics.ProcessStartInfo
            $start.FileName=$record.python_exe; $start.Arguments=Get-PythonArguments $record
            $start.WorkingDirectory=$record.repo; $start.UseShellExecute=$false; $start.CreateNoWindow=$true
            $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
            $process=New-Object Diagnostics.Process; $process.StartInfo=$start
            [void]$process.Start()
            $expected=(Quote-Argument $record.python_exe)+' '+$start.Arguments
            $identity=Get-NewIdentity $process $record.python_exe $expected
            if ($null -eq $identity) { throw 'New Python process identity could not be verified; it will not be force-terminated.' }
            $owned=$true; $record.python=$identity; $record.state='running'
            Write-Control (Get-RecordPath) $record
        } finally { $lock.Dispose() }
        $outBuffer=New-Object char[] 4096; $errBuffer=New-Object char[] 4096
        $outTask=$process.StandardOutput.ReadAsync($outBuffer,0,$outBuffer.Length)
        $errTask=$process.StandardError.ReadAsync($errBuffer,0,$errBuffer.Length)
        $drainDeadline=$null
        while (-not $process.HasExited -or $null -ne $outTask -or $null -ne $errTask) {
            if ($process.HasExited -and $null -eq $drainDeadline) { $drainDeadline=[DateTime]::UtcNow.AddSeconds(5) }
            if ($null -ne $drainDeadline -and [DateTime]::UtcNow -ge $drainDeadline) {
                Write-BoundedLog 'supervisor' "Coordinator exited; trailing pipe drain ended after five seconds. No descendant was signaled.`r`n"
                $process.StandardOutput.Dispose(); $process.StandardError.Dispose(); break
            }
            if ($null -ne $outTask -and $outTask.IsCompleted) {
                $count=$outTask.GetAwaiter().GetResult()
                if ($count -eq 0) { $outTask=$null } else { Write-BoundedLog 'stdout' (-join $outBuffer[0..($count-1)]); $outTask=$process.StandardOutput.ReadAsync($outBuffer,0,$outBuffer.Length) }
            }
            if ($null -ne $errTask -and $errTask.IsCompleted) {
                $count=$errTask.GetAwaiter().GetResult()
                if ($count -eq 0) { $errTask=$null } else { Write-BoundedLog 'stderr' (-join $errBuffer[0..($count-1)]); $errTask=$process.StandardError.ReadAsync($errBuffer,0,$errBuffer.Length) }
            }
            Start-Sleep -Milliseconds 100
        }
        $process.WaitForExit()
        Set-FinalState $RunId 'stopped' $process.ExitCode 'Coordinator exited; journals and original profiles were retained.'
    } catch {
        Write-BoundedLog 'supervisor' ($_.Exception.Message+"`r`n")
        # Graceful request only. An identity/logging failure never becomes permission to kill.
        if ($null -ne $process -and $null -ne $record) {
            if (-not [IO.File]::Exists($record.stop_file)) { Write-Control $record.stop_file ([ordered]@{ schema='helix-orca-v1-stop/v1'; run_id=$record.run_id }) }
        }
        Set-FinalState $RunId 'attention-required' $null 'Supervisor failed; inspect owned logs and process identity before retrying.'
        throw
    } finally {
        if ($null -ne $storageLock) { $storageLock.Dispose() }
        if ($null -ne $process) { $process.Dispose() }
    }
}

$script:Root=Get-FullLocalPath $RuntimeRoot
if (-not (Assert-PrivateRoot ($Action -in @('start','plan')))) {
    if ($Action -eq 'status' -or $Action -eq 'stop') { [ordered]@{ state='not-started'; actions_enabled=$false } | ConvertTo-Json; exit 0 }
    throw 'A private runtime directory is required.'
}
if ($Action -eq 'supervise') { if ([string]::IsNullOrEmpty($RunId)) { throw 'Supervisor requires its recorded run id.' }; Invoke-Supervisor; exit 0 }
if ($Action -eq 'status') { Get-Status | ConvertTo-Json -Depth 8; exit 0 }
if ($Action -eq 'stop') {
    $lock=Open-ControlLock
    try {
        $status=Get-Status
        if ($status.state -eq 'stopped' -or $status.state -eq 'not-started') { $status | ConvertTo-Json -Depth 8; exit 0 }
        $record=Read-Control (Get-RecordPath); Assert-Record $record
        if (-not (Test-StopRequest $record)) { Write-Control $record.stop_file ([ordered]@{ schema='helix-orca-v1-stop/v1'; run_id=$record.run_id }) }
    } finally { $lock.Dispose() }
    $until=[DateTime]::UtcNow.AddSeconds($WaitSeconds)
    do { $status=Get-Status; if ($status.state -eq 'stopped') { break }; Start-Sleep -Milliseconds 200 } while ([DateTime]::UtcNow -lt $until)
    $status | ConvertTo-Json -Depth 8
    exit 0
}
$python=Get-ExistingPath $PythonExe $false
$repo=Get-ExistingPath $RepoRoot $true
$storagePath=Get-ExistingPath $Storage $true
$configPath=Get-ExistingPath $Config $false
$entry=Get-ExistingPath (Join-Path $repo 'scripts\v1-runtime.py') $false
if ([IO.Path]::GetFileName($python) -notin @('python.exe','python3.exe')) { throw 'An explicit installed Python executable is required.' }
$hostExe=Get-ExistingPath (Join-Path $PSHOME ([IO.Path]::GetFileName([Diagnostics.Process]::GetCurrentProcess().MainModule.FileName))) $false
if ([IO.Path]::GetFileName($hostExe) -notin @('powershell.exe','pwsh.exe')) { throw 'Use the normal PowerShell console host.' }
$publicArgs=@('-NoProfile','-NonInteractive','-File',$PSCommandPath,'-Action','start','-RuntimeRoot',$script:Root,'-PythonExe',$python,'-RepoRoot',$repo,'-Storage',$storagePath,'-Config',$configPath)
if ($MoonrakerEvents) { $publicArgs+='-MoonrakerEvents' }
if ($Action -eq 'plan') {
    $plan=[ordered]@{ schema='helix-orca-v1-windows-startup-plan/v1'; review_only=$true; registered=$false; target=$hostExe; arguments=(Join-Arguments $publicArgs); suggested_shortcut=(Join-Path ([Environment]::GetFolderPath('Startup')) 'Helix Orca V1.lnk'); actions_enabled=$false; instructions='Review these exact paths and arguments. No shortcut/startup entry was created. Manual registration requires separate explicit owner action.' }
    Write-Control (Join-Path $script:Root 'startup-plan.json') $plan
    $plan | ConvertTo-Json -Depth 8; exit 0
}
$lock=Open-ControlLock
try {
    $status=Get-Status
    if ($status.state -in @('running','starting','stopping','finishing')) { $status | ConvertTo-Json -Depth 8; exit 0 }
    if ($status.state -eq 'attention-required') { throw 'Previous ambiguous instance requires review; no replacement was launched.' }
    if ([IO.File]::Exists((Get-RecordPath))) {
        $previous=Read-Control (Get-RecordPath); Assert-Record $previous
        Write-Control (Join-Path $script:Root 'previous.json') $previous
        if (Test-StopRequest $previous) { [IO.File]::Delete($previous.stop_file) }
    }
    $id=[Guid]::NewGuid().ToString('N')
    $record=[ordered]@{ schema='helix-orca-v1-windows-runtime/v1'; run_id=$id; owner_sid=$script:Sid.Value; state='starting'; exit_code=$null; message='Starting fixed local coordinator'; python=$null; supervisor=$null; python_exe=$python; repo=$repo; entry=$entry; storage=$storagePath; config=$configPath; coordinator_state=(Join-Path $script:Root 'coordinator'); stop_file=(Join-Path $script:Root ('stop.'+$id+'.json')); moonraker_events=[bool]$MoonrakerEvents; launcher_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant(); entry_sha256=(Get-FileHash -LiteralPath $entry -Algorithm SHA256).Hash.ToLowerInvariant(); config_sha256=(Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant() }
    Write-Control (Get-RecordPath) $record
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$hostExe; $start.Arguments=Join-Arguments @('-NoProfile','-NonInteractive','-File',$PSCommandPath,'-Action','supervise','-RuntimeRoot',$script:Root,'-RunId',$id)
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true; $start.WorkingDirectory=$repo
    $supervisor=Start-DetachedSupervisor $hostExe $start.Arguments $repo
    $identity=Get-NewIdentity $supervisor $hostExe ((Quote-Argument $hostExe)+' '+$start.Arguments)
    if ($null -eq $identity) { throw 'Supervisor identity could not be verified; no process was force-terminated.' }
    $record.supervisor=$identity; Write-Control (Get-RecordPath) $record
} finally { $lock.Dispose() }
$until=[DateTime]::UtcNow.AddSeconds($WaitSeconds)
do { $status=Get-Status; if ($status.state -ne 'starting') { break }; Start-Sleep -Milliseconds 200 } while ([DateTime]::UtcNow -lt $until)
$status | ConvertTo-Json -Depth 8
