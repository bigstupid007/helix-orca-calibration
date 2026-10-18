"""Windows lifecycle packaging boundaries; execution evidence remains separate."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'scripts/v1-runtime-windows.ps1'
class WindowsRuntimePackagingTests(unittest.TestCase):
    def test_fixed_lifecycle_actions_and_nonce_stop_protocol(self):
        text=SOURCE.read_text()
        actions=re.search(r"\[ValidateSet\(([^)]+)\)\]\[string\]\$Action",text).group(1)
        self.assertEqual(re.findall(r"'([^']+)'",actions),['start','status','stop','plan','supervise'])
        self.assertIn("schema='helix-orca-v1-stop/v1'; run_id=$record.run_id",text)
        self.assertIn("'--run-id',$Record.run_id,'--stop-file',$Record.stop_file",text)
        self.assertIn("$Record.stop_file -cne $expected",text)
        self.assertIn("'run_id,schema'",text)
        self.assertNotIn('[IO.File]::Replace($temporary,$Path,$null)',text)
        self.assertIn('[IO.File]::Replace($temporary,$Path,$backup)',text)
    def test_lifecycle_privacy_and_process_ownership_are_explicit(self):
        text=SOURCE.read_text()
        for required in ('SetAccessRuleProtection($true,$false)','Assert-PrivateFile','ReparsePoint','FileShare]::None',
                         'GetOwnerSid','started_utc_ticks','command_line','ExecutablePath','CommandLine',
                         ".v1-windows-launcher.lock",'Get-ProcessIdentity','Test-Identity','launcher_sha256'):
            self.assertIn(required,text)
    def test_child_entrypoint_and_retained_logs_are_bounded(self):
        text=SOURCE.read_text()
        self.assertIn("'scripts\\v1-runtime.py'",text)
        self.assertIn("$start.FileName=$record.python_exe",text)
        self.assertIn("$start.Arguments=Get-PythonArguments $record",text)
        self.assertIn('$script:LogBytes=1048576',text)
        self.assertEqual(text.count('New-Object char[] 4096'),2)
        self.assertIn("$Name -notin @('stdout','stderr','supervisor')",text)
        self.assertIn("$Name+'.1.log'",text)
        self.assertIn('review_only=$true; registered=$false',text)
        self.assertIn("'--moonraker-events'",text)
    def test_detached_supervisor_has_explicit_handle_allowlist(self):
        text=SOURCE.read_text()
        self.assertIn('Start-DetachedSupervisor $hostExe $start.Arguments $repo',text)
        self.assertIn('new IntPtr(0x20002)',text)  # PROC_THREAD_ATTRIBUTE_HANDLE_LIST
        self.assertIn('Marshal.WriteIntPtr(handles,nul)',text)
        self.assertIn('0x08080000',text)  # NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT
        self.assertIn('DeleteProcThreadAttributeList(list)',text)
        self.assertIn('$again.StartTime.ToUniversalTime().Ticks.ToString() -cne $started',text)
    def test_no_force_termination_listener_or_system_registration(self):
        text=SOURCE.read_text()
        forbidden=r'(?im)^\s*(Stop-Process|Register-ScheduledTask|New-Service|Set-Service|Set-ExecutionPolicy|New-NetFirewallRule|Invoke-Expression|Start-Job)\b'
        self.assertNotRegex(text,forbidden)
        for forbidden in ('.Kill(','.Terminate(',"CreateShortcut(",'HttpListener','TcpListener','Schedule.Service','WScript.Shell','-ExecutionPolicy'):
            self.assertNotIn(forbidden,text)
        self.assertNotIn('Remove-Item',text)
    @unittest.skipUnless(os.name=='nt' and (shutil.which('powershell.exe') or shutil.which('pwsh.exe')),'Actual Windows PowerShell parser unavailable')
    def test_actual_windows_powershell_ast_parses_without_executing(self):
        host=shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        path=str(SOURCE).replace("'","''")
        command="$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+path+"',[ref]$tokens,[ref]$errors);if($errors.Count){$errors | ForEach-Object {$_.Message};exit 1}"
        result=subprocess.run([host,'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
