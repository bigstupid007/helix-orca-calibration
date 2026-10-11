# Test only the worker's own native window. Never interact with other applications.
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ine 'Spare') { throw 'Wrong Windows host.' }
$SessionId = [Diagnostics.Process]::GetCurrentProcess().SessionId
if ($SessionId -le 0) { throw 'No interactive desktop session.' }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Issue4GuiProbe {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int x; public int y; }
  [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT p);
  [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint flag);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, UIntPtr e);
}
'@
$Form = [Windows.Forms.Form]::new()
$Form.Text = 'Helix-Orca Issue 4 GUI access test'
$Form.ClientSize = [Drawing.Size]::new(500, 140)
$Form.StartPosition = 'CenterScreen'
$Form.FormBorderStyle = 'FixedDialog'
$Form.MaximizeBox = $false
$Form.TopMost = $true
$Label = [Windows.Forms.Label]::new()
$Label.Text = 'Native desktop input: waiting'
$Label.Location = [Drawing.Point]::new(20, 20)
$Label.Size = [Drawing.Size]::new(450, 25)
$Button = [Windows.Forms.Button]::new()
$Button.Text = 'Test input'
$Button.Location = [Drawing.Point]::new(20, 65)
$Button.Size = [Drawing.Size]::new(130, 35)
$Button.Add_Click({ $Label.Text = 'Native desktop input: passed' })
$Form.Controls.AddRange(@($Label, $Button))
$OriginalCursor = [Windows.Forms.Cursor]::Position
$Bitmap = $null
$Graphics = $null
try {
    $Form.Show()
    [Windows.Forms.Application]::DoEvents()
    [Issue4GuiProbe]::SetForegroundWindow($Form.Handle) | Out-Null
    Start-Sleep -Milliseconds 300
    [Windows.Forms.Application]::DoEvents()
    $Point = $Button.PointToScreen([Drawing.Point]::new(65, 17))
    $NativePoint = [Issue4GuiProbe+POINT]::new()
    $NativePoint.x = $Point.X
    $NativePoint.y = $Point.Y
    $Hit = [Issue4GuiProbe]::WindowFromPoint($NativePoint)
    if ([Issue4GuiProbe]::GetAncestor($Hit, 2) -ne $Form.Handle) {
        throw 'Probe click point is not owned by its window; refusing input.'
    }
    [Issue4GuiProbe]::SetCursorPos($Point.X, $Point.Y) | Out-Null
    [Issue4GuiProbe]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
    [Issue4GuiProbe]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
    for ($i = 0; $i -lt 20; $i++) {
        [Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 20
    }
    if ($Label.Text -ne 'Native desktop input: passed') { throw 'Native button click failed.' }
    if ([Issue4GuiProbe]::GetForegroundWindow() -ne $Form.Handle) {
        throw 'Foreground changed; refusing screenshot.'
    }
    $Bounds = $Form.Bounds
    $Bitmap = [Drawing.Bitmap]::new($Bounds.Width, $Bounds.Height)
    $Graphics = [Drawing.Graphics]::FromImage($Bitmap)
    $Graphics.CopyFromScreen($Bounds.Location, [Drawing.Point]::Empty, $Bounds.Size)
    $Directory = Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\windows-access'
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $ImagePath = Join-Path $Directory 'native-gui-access-test.png'
    $Bitmap.Save($ImagePath, [Drawing.Imaging.ImageFormat]::Png)
    @{
        hostname = $env:COMPUTERNAME
        session_id = $SessionId
        native_click_passed = $true
        screenshot_sha256 = (Get-FileHash -LiteralPath $ImagePath -Algorithm SHA256).Hash.ToLowerInvariant()
        png_base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($ImagePath))
    } | ConvertTo-Json -Compress
} finally {
    [Windows.Forms.Cursor]::Position = $OriginalCursor
    if ($null -ne $Graphics) { $Graphics.Dispose() }
    if ($null -ne $Bitmap) { $Bitmap.Dispose() }
    $Form.Close()
    $Form.Dispose()
}
