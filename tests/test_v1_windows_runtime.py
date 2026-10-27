"""Windows lifecycle packaging boundaries; execution evidence remains separate."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'scripts/v1-runtime-windows.ps1'
class WindowsRuntimePackagingTests(unittest.TestCase):
    def test_fixed_lifecycle_actions_and_nonce_stop_protocol(self):
        text=SOURCE.read_text()
        actions=re.search(r"\[ValidateSet\(([^)]+)\)\]\[string\]\$Action",text).group(1)
        self.assertEqual(re.findall(r"'([^']+)'",actions),
            ['install','start','status','stop','restart','rollback','uninstall','plan','supervise'])
        self.assertIn("schema='helix-orca-v1-stop/v1'; run_id=$record.run_id",text)
        self.assertIn("$status.state -eq 'attention-required'",text)
        self.assertIn("-not (Test-Identity $record.python)",text)
        self.assertIn("-not (Test-Identity $record.supervisor)",text)
        self.assertIn("Set-FinalState $record.run_id 'stopped' $record.exit_code",text)
        self.assertIn('no owned process remained, and journals were retained.',text)
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
        self.assertIn("@('-B','-u',$Record.entry",text)

    def test_versioned_manifest_install_rollback_and_uninstall_are_bounded(self):
        text=SOURCE.read_text()
        for required in ("schema -ne 'helix-orca-v1-runtime-manifest/v1'",
                         "'versions'", 'active_candidate', 'previous_candidate',
                         'active_manifest_sha256', 'Assert-InstalledVersion',
                         "schema='helix-orca-v1-windows-installation/v2'",
                         'candidate_bindings', 'Get-CandidateBinding',
                         'storage=$storagePath',
                         "$script:DeploymentAuthorizationBound=$PSBoundParameters.ContainsKey('DeploymentAuthorization')",
                         'Installed candidate lacks one exact config/authorization binding.',
                         'Installed candidate binding changed while Start was being prepared.',
                         'Get-RuntimeManifest', "'scripts/v1-runtime.py'",
                         'Installed candidate contains an unlisted file.',
                         'Partial installed candidate contains an unlisted file.',
                         'Partial installed candidate file differs from the exact manifest.',
                         '[IO.File]::Copy($sourceFile,$target,$false)',
                         '[IO.FileAttributes]::ReadOnly',
                         "state='uninstalled'; journals_retained=$true",
                         "Stop the exact owned runtime before rollback",
                         "Stop the exact owned runtime before uninstall",
                         'Installed candidate changed while Start was being prepared.'):
            self.assertIn(required,text)
        self.assertGreaterEqual(text.count('$operationLock=Open-ControlLock'),3)
        self.assertIn("$Action='start'",text)
        self.assertIn('Remove-InstalledVersion $candidate $hash',text)
        self.assertNotIn('[IO.Directory]::Delete($script:Root',text)

    def test_installation_is_per_user_and_creates_no_ambient_machine_state(self):
        text=SOURCE.read_text()
        self.assertIn("GetFolderPath('LocalApplicationData')",text)
        self.assertIn("SetAccessRuleProtection($true,$false)",text)
        for forbidden in ('New-LocalUser','net user','cmdkey','New-NetFirewallRule',
                          'New-Service','Register-ScheduledTask','HttpListener','TcpListener'):
            self.assertNotIn(forbidden,text)
    def test_optional_deployment_file_is_local_private_pinned_and_fixed_argument(self):
        text=SOURCE.read_text()
        for required in ('[string]$DeploymentAuthorization', 'function Get-PrivateAuthorization',
                         'if ($script:DeploymentAuthorizationBound)',
                         '$path=Get-ExistingPath $Value $false', 'Assert-PrivateFile $path',
                         '$size -lt 1 -or $size -gt 65536',
                         "@('--deployment-authorization',$authorization)",
                         "@('-DeploymentAuthorization',$authorizationPath)",
                         'deployment_authorization_sha256=$authorizationHash',
                         '$record.deployment_authorization_sha256 -cne (Get-FileHash',
                         'deployment_authorization_supplied='):
            self.assertIn(required,text)
        self.assertNotIn("approved=$true",text)
        self.assertNotIn("'--deployment-authorized'",text)
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

    @unittest.skipUnless(os.name=='nt' and (shutil.which('powershell.exe') or shutil.which('pwsh.exe')),'Actual Windows lifecycle unavailable')
    def test_actual_install_second_candidate_rollback_restores_its_config_and_authorization(self):
        host=shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        acl_probe=subprocess.run([host,'-NoProfile','-NonInteractive','-Command',
            "$ErrorActionPreference='Stop';Import-Module Microsoft.PowerShell.Security;"
            "[void](Get-Command Set-Acl -ErrorAction Stop)"],capture_output=True,text=True,timeout=30)
        if acl_probe.returncode:
            self.skipTest('Actual Windows ACL provider unavailable: '+(acl_probe.stderr or acl_probe.stdout).strip()[:200])
        runtime=Path(os.environ['LOCALAPPDATA'])/('helix-orca-lifecycle-test-'+uuid.uuid4().hex)
        self.addCleanup(lambda: shutil.rmtree(runtime,ignore_errors=True))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            def package(name,token):
                package_root=root/name;(package_root/'scripts').mkdir(parents=True)
                entry=package_root/'scripts/v1-runtime.py';entry.write_text('# lifecycle fixture\n')
                payload=entry.read_bytes()
                manifest={'schema':'helix-orca-v1-runtime-manifest/v1','candidate_sha256':token*64,
                    'files':[{'path':'scripts/v1-runtime.py','size':len(payload),
                              'sha256':hashlib.sha256(payload).hexdigest()}]}
                path=package_root/'runtime-manifest.json';path.write_text(json.dumps(manifest,separators=(',',':')))
                config=root/(name+'.json');config.write_text(json.dumps({'candidate':token}))
                authorization=root/(name+'.authorization.json');authorization.write_text(json.dumps({'candidate':token}))
                storage=root/(name+'.storage');storage.mkdir()
                quoted=str(authorization).replace("'","''")
                command=("$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;"
                         "$acl=New-Object Security.AccessControl.FileSecurity;"
                         "$acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false);"
                         "$rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','Allow');"
                         "$acl.AddAccessRule($rule);Set-Acl -LiteralPath '"+quoted+"' -AclObject $acl")
                locked=subprocess.run([host,'-NoProfile','-NonInteractive','-Command',command],
                                      capture_output=True,text=True,timeout=30)
                self.assertEqual(locked.returncode,0,locked.stdout+locked.stderr)
                return package_root,path,config,authorization,storage
            first=package('first','a');second=package('second','b')
            def invoke(action,*extra):
                command=[host,'-NoProfile','-NonInteractive','-File',str(SOURCE),'-Action',action,
                         '-RuntimeRoot',str(runtime),*map(str,extra)]
                result=subprocess.run(command,capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return json.loads(result.stdout)
            for package_root,manifest,config,authorization,storage in (first,second):
                invoke('install','-PythonExe',sys.executable,'-Storage',storage,'-Config',config,
                       '-DeploymentAuthorization',authorization,'-PackageRoot',package_root,'-Manifest',manifest)
            rolled=invoke('rollback')
            self.assertEqual(rolled['active_candidate'],'a'*64)
            binding=[item for item in rolled['candidate_bindings'] if item['candidate_sha256']=='a'*64]
            self.assertEqual(len(binding),1)
            self.assertEqual(Path(binding[0]['config']),first[2])
            self.assertEqual(Path(binding[0]['deployment_authorization']),first[3])
            self.assertEqual(Path(binding[0]['storage']),first[4])
            self.assertEqual(Path(rolled['storage']),first[4])
            plan=invoke('plan')
            self.assertEqual(Path(plan['deployment_authorization']),first[3])
            self.assertIn(str(first[2]),plan['arguments'])
            invoke('uninstall')
