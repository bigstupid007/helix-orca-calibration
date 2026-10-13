# Qualification tooling only: normal Orca is never an input/capture target.
param([ValidateSet('windows','capture','click','keys','tree','resize')][string]$Op='windows', [long]$Handle=0, [int]$X=0, [int]$Y=0, [string]$Keys='', [string]$Name='frame')
$ErrorActionPreference='Stop'
$Stage=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\issue-4-windows'
$Exe=Join-Path $Stage 'nightly\orca-slicer.exe'
$Data=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\issue-4-nightly-210bc927'
if (-not (Test-Path (Join-Path $Data '.helix-orca-issue-4-qualification'))) {throw 'Missing isolated data marker.'}
$Candidates=@(Get-CimInstance Win32_Process -Filter "Name='orca-slicer.exe'" | Where-Object {$_.ExecutablePath -eq $Exe})
if ($Candidates.Count -ne 1) {throw 'Expected one test Orca.'}
$Target=$Candidates[0]
if ($Target.CommandLine -notlike ('*--datadir*'+$Data+'*')) {throw 'Nightly process isolation arguments mismatch.'}
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class Issue4Native {
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [StructLayout(LayoutKind.Sequential)] public struct RECT {public int left,top,right,bottom;}
 [StructLayout(LayoutKind.Sequential)] public struct POINT {public int x,y;}
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Callback f,IntPtr p);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out RECT r);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT p);
 [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h,uint flags);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h,IntPtr after,int x,int y,int w,int height,uint flags);
 [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h,int idx);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,UIntPtr e);
 public static IntPtr[] Windows(uint wanted) {
  var found=new List<IntPtr>(); EnumWindows((h,p)=>{uint id;GetWindowThreadProcessId(h,out id); if(id==wanted && IsWindowVisible(h))found.Add(h);return true;},IntPtr.Zero);return found.ToArray();
 }
 public static uint Owner(IntPtr h){uint p;GetWindowThreadProcessId(h,out p);return p;}
}
'@
[Issue4Native]::SetProcessDPIAware()|Out-Null
# Permit WebView file pickers only under the isolated process/storage.
$All=@(Get-CimInstance Win32_Process)
if(-not($All|Where-Object {$_.ParentProcessId -eq $Target.ProcessId -and $_.Name -eq 'msedgewebview2.exe' -and $_.CommandLine -like ('*--user-data-dir=*'+$Data+'\webview2*')})){throw 'Missing isolated WebView2 process/storage'}
$Allowed=@([uint32]$Target.ProcessId)
foreach($Browser in @($All|Where-Object {$_.Name -eq 'msedgewebview2.exe'})) {
 $ParentId=$Browser.ParentProcessId
 for($Depth=0;$Depth -lt 8;$Depth++) {
  if($ParentId -eq $Target.ProcessId){$Allowed += [uint32]$Browser.ProcessId;break}
  $Parent=@($All|Where-Object {$_.ProcessId -eq $ParentId})
  if($Parent.Count -ne 1 -or $Parent[0].Name -ne 'msedgewebview2.exe'){break}
  $ParentId=$Parent[0].ParentProcessId
 }
}
$Handles=@($Allowed|ForEach-Object {[Issue4Native]::Windows($_)})
$Windows=@($Handles | ForEach-Object {
 $r=[Issue4Native+RECT]::new();[Issue4Native]::GetWindowRect($_,[ref]$r)|Out-Null
 $s=[Text.StringBuilder]::new(512);[Issue4Native]::GetWindowText($_,$s,512)|Out-Null
 @{handle=$_.ToInt64();title=$s.ToString();x=$r.left;y=$r.top;width=$r.right-$r.left;height=$r.bottom-$r.top}
})
if($Op -eq 'windows') { @{pid=$Target.ProcessId;windows=$Windows}|ConvertTo-Json -Compress -Depth 5;return }
if($Handle -eq 0){$Handle=($Windows|Sort-Object { $_.width*$_.height } -Descending|Select-Object -First 1).handle}
$H=[IntPtr]::new($Handle)
if($Allowed -notcontains [Issue4Native]::Owner($H)){throw 'Wrong window owner.'}
if($Op -eq 'tree') {
 Add-Type -AssemblyName UIAutomationClient
 $Root=[Windows.Automation.AutomationElement]::FromHandle($H)
 $Nodes=$Root.FindAll([Windows.Automation.TreeScope]::Descendants,[Windows.Automation.Condition]::TrueCondition)
 $Rows=@(for($i=0;$i -lt [Math]::Min($Nodes.Count,160);$i++){try{$n=$Nodes[$i].Current;@{name=$n.Name;type=$n.ControlType.ProgrammaticName;id=$n.AutomationId;rect=$n.BoundingRectangle.ToString();enabled=$n.IsEnabled}}catch{}})
 @{pid=$Target.ProcessId;nodes=$Rows}|ConvertTo-Json -Compress -Depth 5;return
}
$WasTop=([Issue4Native]::GetWindowLong($H,-20) -band 8) -ne 0
$Original=[Windows.Forms.Cursor]::Position
try {
 if($Op -eq 'resize'){[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-1),40,40,1320,900,16)|Out-Null}
 else{[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-1),0,0,0,0,19)|Out-Null}
 Start-Sleep -Milliseconds 250
 $r=[Issue4Native+RECT]::new();[Issue4Native]::GetWindowRect($H,[ref]$r)|Out-Null
 if($Op -eq 'click') {
  if($X -lt 0 -or $Y -lt 0 -or $X -ge $r.right-$r.left -or $Y -ge $r.bottom-$r.top){throw 'Click outside target window.'}
  $p=[Issue4Native+POINT]::new();$p.x=$r.left+$X;$p.y=$r.top+$Y
  if($Allowed -notcontains [Issue4Native]::Owner([Issue4Native]::GetAncestor([Issue4Native]::WindowFromPoint($p),2))){throw 'Click is occluded.'}
  [Issue4Native]::SetCursorPos($p.x,$p.y)|Out-Null
  [Issue4Native]::mouse_event(2,0,0,0,[UIntPtr]::Zero);[Issue4Native]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 300
 } elseif($Op -eq 'keys') {
  if($Allowed -notcontains [Issue4Native]::Owner([Issue4Native]::GetForegroundWindow())){throw 'Test Orca is not foreground.'}
  [Windows.Forms.SendKeys]::SendWait($Keys)
 } elseif($Op -eq 'capture') {
  if($Name -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Invalid evidence name.'}
  $Width=$r.right-$r.left;$Height=$r.bottom-$r.top
  $Bounds=[Windows.Forms.SystemInformation]::VirtualScreen
  if($r.left -lt $Bounds.Left -or $r.top -lt $Bounds.Top -or $r.right -gt $Bounds.Right -or $r.bottom -gt $Bounds.Bottom){throw 'Target extends beyond visible desktop.'}
  $p=[Issue4Native+POINT]::new();$p.x=$r.left+[int]($Width/2);$p.y=$r.top+[int]($Height/2)
  if($Allowed -notcontains [Issue4Native]::Owner([Issue4Native]::GetAncestor([Issue4Native]::WindowFromPoint($p),2))){throw 'Capture is occluded.'}
  $Dir=Join-Path $Stage 'screenshots';New-Item -ItemType Directory -Path $Dir -Force|Out-Null
  $Path=Join-Path $Dir ($Name+'.png')
  $Bitmap=[Drawing.Bitmap]::new($Width,$Height);$Graphics=[Drawing.Graphics]::FromImage($Bitmap)
  try{$Graphics.CopyFromScreen([Drawing.Point]::new($r.left,$r.top),[Drawing.Point]::Empty,[Drawing.Size]::new($Width,$Height));$Bitmap.Save($Path,[Drawing.Imaging.ImageFormat]::Png)}finally{$Graphics.Dispose();$Bitmap.Dispose()}
  @{file=$Path;sha256=(Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant();pid=$Target.ProcessId;handle=$Handle;title=($Windows|Where-Object {$_.handle -eq $Handle}).title;width=$Width;height=$Height}|ConvertTo-Json -Compress;return
 }
 @{op=$Op;pid=$Target.ProcessId;handle=$Handle;foreground_pid=[Issue4Native]::Owner([Issue4Native]::GetForegroundWindow())}|ConvertTo-Json -Compress
} finally {
 [Windows.Forms.Cursor]::Position=$Original
 if(-not $WasTop){[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-2),0,0,0,0,19)|Out-Null}
}
