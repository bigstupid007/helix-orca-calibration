#!/usr/bin/env python3
"""Capture a bounded native UI region directly, avoiding personal artifact paths."""
import argparse
import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('review',Path(__file__).with_name('orca-windows-review.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--handle',type=int,required=True);p.add_argument('--name',required=True)
    for field in ('left','top','width','height'):p.add_argument('--'+field,type=int,required=True)
    a=p.parse_args()
    if min(a.left,a.top)<0 or min(a.width,a.height)<=0 or not a.name.replace('-','').replace('_','').isalnum():raise ValueError('Invalid bounded capture')
    source=Path(__file__).with_name('orca-windows-ui.ps1').read_text()
    needle="  $Dir=Join-Path $Stage 'screenshots';"
    # The original guard first validates the exact nightly, data marker, browser
    # isolation, window ownership, full-window screen bounds, and occlusion.
    region=f"  if({a.left}+{a.width} -gt $Width -or {a.top}+{a.height} -gt $Height){{throw 'Region outside target.'}}\n  $r.left+={a.left};$r.top+={a.top};$Width={a.width};$Height={a.height}\n"
    region+="  $p.x=$r.left+[int]($Width/2);$p.y=$r.top+[int]($Height/2)\n  if($Allowed -notcontains [Issue4Native]::Owner([Issue4Native]::GetAncestor([Issue4Native]::WindowFromPoint($p),2))){throw 'Region is occluded.'}\n"
    source=source.replace(needle,region+needle)
    # Remove comment-only lines to remain inside the bounded worker command size.
    source='\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#'))
    command='& {\n'+source+'\n} -Op capture -Handle '+str(a.handle)+' -Name '+r.quote(a.name)
    if len(command)>8192:raise ValueError('Capture exceeds the worker command bound')
    result=r.invoke(command,'native-region')
    destination=r.access.state_dir()/'evidence'/(a.name+'.png')
    ps="$K=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\windows-access\\devbox_known_hosts'; & scp.exe -o BatchMode=yes -o StrictHostKeyChecking=yes -o ClearAllForwardings=yes -o ('UserKnownHostsFile='+$K) "+r.quote(result['file'])+' '+r.quote('dev@192.168.1.114:'+str(destination))+"; if($LASTEXITCODE -ne 0){throw 'Transfer failed'}; @{ok=$true}|ConvertTo-Json -Compress"
    r.invoke(ps,'region-transfer')
    if r.hashlib.sha256(destination.read_bytes()).hexdigest()!=result['sha256']:raise ValueError('Capture digest mismatch')
    result['local_file']=str(destination);result['region']=[a.left,a.top,a.width,a.height]
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
