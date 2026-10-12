#!/usr/bin/env python3
"""Capture, promote and verify the bounded Issue #4 native proof artifacts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import os
import signal
import socket
import urllib.request
import struct
import subprocess
import time

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('roundtrip',ROOT/'scripts/temperature-roundtrip.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
PHASES=('request-retry','available','home-ready','printing','home-active','resume-print','progress','completion','home-choice','choice','result-retry','returned','home-result')
PUBLIC_PHASES=('available','home-active','resume-print','choice','returned')


def hashes():
    paths=[ROOT/'plugin/helix_calibration.py',ROOT/'scripts/temperature-roundtrip.py',ROOT/'scripts/helix_dev.py',ROOT/'scripts/temperature-evidence.py',ROOT/'scripts/temperature-viewer.html']
    paths.extend(p for p in (ROOT/'integration/calibration-bridge').rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)):d.digest(p) for p in sorted(paths)}


def dimensions(path):
    raw=path.read_bytes()
    if raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR':raise ValueError('Not a native PNG frame')
    return list(struct.unpack('>II',raw[16:24]))


def capture(request,gcode):
    before=hashes();runtime=d.h.verify_assets()
    subprocess.run(['python3',str(ROOT/'scripts/temperature-roundtrip.py'),'matrix','--request',str(request),'--gcode',str(gcode)],check=True)
    if hashes()!=before or d.h.verify_assets()!=runtime:raise ValueError('Runtime candidate changed during capture')
    (d.STATE/'completed-matrix-candidate.json').write_text(json.dumps({'matrix_sha256':d.digest(d.STATE/'matrix.json'),'candidate_files':before,'runtime':runtime},indent=2))


def promote(output,request):
    binding=json.loads((d.STATE/'completed-matrix-candidate.json').read_text())
    matrix=json.loads((d.STATE/'matrix.json').read_text())
    if binding['candidate_files']!=hashes() or binding['matrix_sha256']!=d.digest(d.STATE/'matrix.json'):
        raise ValueError('Native capture does not bind the current runtime candidate')
    runtime=d.h.verify_assets()
    if binding['runtime']!=runtime:raise ValueError('Captured runtime differs from the verified current binary')
    if [r['viewport'] for r in matrix]!=[list(v) for v in d.h.VIEWPORTS]:raise ValueError('Incomplete viewport capture')
    original=json.loads(request.read_text());request_hash=d.digest(request)
    if output.exists() and any(output.iterdir()) and not (output/'report.json').is_file():raise ValueError('Unmarked evidence destination')
    report={'schema':'helix-orca-temperature-proof/v1','status':'pass','recorded_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'runtime_candidate_files':hashes(),'helix_source_commit':d.h.HELIX_SOURCE_COMMIT,
        'helix_binary_sha256':runtime['binary_sha256'],'runtime':runtime,'upstream_bridge_commit':'ed8d0c4977873969613fcb49024109ff7df7d84e',
        'orca_plugin_sha256':d.digest(ROOT/'plugin/helix_calibration.py'),'request_sha256':request_hash,
        'request_id':original['request_id'],'context_sha256':original['context_sha256'],'file':original['file'],
        'transport':'Pinned LAN SSH plus native plugin-storage artifacts; beta.4 HTTP printer-host guard preserved.',
        'viewport_runs':[],'frames':{},'windows_frames':{},'assertions':['mock-only request validated','actual file digest and bands validated','request failure visible; delivery and reload recover','receipt does not start printing','visible native pointer Start calls test mock','native mock publishes printing','controlled progress 50 and complete states','native dropdown chooses 205','native result write fails then Next retries same ID','returned native result matches original request','all native bridge states fit horizontally','accepted orcacal files unchanged'],
        'limitations':['All printing is simulated in --test and --network none. No hardware execution or production transport.','The native test freeze parks the synthetic clock and existing periodic timers before remote input is created. The live remote pointer, navigation/update and rendering remain usable; animations are disabled. Progress/completion are controlled private subjects.','Request delivery retry clears beta.4 native storage cache through hot reload; this is development infrastructure.','The G-code file remains private. Its byte digest, bands and original Windows provenance are committed.']}
    report['product_hashes']=d.h._plugin_hashes()
    rows=[]
    output.mkdir(parents=True,exist_ok=True)
    for row in matrix:
        label,width,height,layout,dpi=row['viewport'];work=Path(row['work'])
        isolation=json.loads((work/'isolation.json').read_text())
        if 'isolation_contract' not in report:report['isolation_contract']=isolation
        expected_bridge={k:v for k,v in hashes().items() if k.startswith('integration/')}
        if isolation['network']!='none' or not isolation['test'] or not isolation['readonly_root'] or isolation['binary_sha256']!=runtime['binary_sha256'] or isolation['bridge_hashes']!=expected_bridge or isolation['product_hashes']!=d.h._plugin_hashes():raise ValueError('Capture isolation/source mismatch')
        if json.loads((work/'orca-request.json').read_text())!=original:raise ValueError('Request changed across native targets')
        result=json.loads((work/'result.json').read_text())
        if result['value']!=205 or result['request_id']!=original['request_id'] or d.digest(work/'result.json')!=row['result_sha256']:raise ValueError('Result changed across targets')
        frame_hashes={}
        for phase in PHASES:
            path=work/(phase+'.png')
            if dimensions(path)!=[width,height]:raise ValueError('Native frame dimensions differ')
            frame_hashes[phase]=d.digest(path)
            if phase in PUBLIC_PHASES or label=='medium_800x480':
                relative=f'native/{label}/{phase}.png';dest=output/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest);report['frames'][relative]=d.digest(dest)
        report['viewport_runs'].append({'viewport':row['viewport'],'status':'pass','network':'none','test':True,'readonly_root':True,'binary_sha256':isolation['binary_sha256'],'frames':frame_hashes,'result_sha256':row['result_sha256']})
        rows.append('\t'.join(map(str,row['viewport']))+'\tPASS')
    shutil.copyfile(request,output/'request.json')
    shutil.copyfile(Path(matrix[0]['work'])/'result.json',output/'result.json')
    report['result_sha256']=d.digest(output/'result.json')
    windows=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'helix-orca-calibration/windows-access/evidence'
    names=['roundtrip-original-retained','roundtrip-file-verified','roundtrip-instructions-native','roundtrip-result-duplicate','roundtrip-result-stale','roundtrip-result-conflicting']
    preservation=json.loads((windows/'normal-preservation-roundtrip.json').read_text())
    if preservation.get('unchanged') is not True:raise ValueError('Normal Orca preservation failed')
    report['normal_preservation']=preservation
    report['windows_validation']={'target':'Spare','orca_build':'210bc927','plugin_version':'0.4.0','profile_switch':True,'duplicate_ignored':True,'stale_id_rejected':True,'conflicting_duplicate_rejected':True,'instructions':'not applied','selected_temperature':205}
    for name in names:
        src=windows/(name+'.png');dest=output/'windows'/(name+'.png');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);report['windows_frames'][str(dest.relative_to(output))]=d.digest(dest)
    (output/'matrix.tsv').write_text('target\twidth\theight\tlayout\tdpi\tstatus\n'+'\n'.join(rows)+'\n')
    report['matrix_sha256']=d.digest(output/'matrix.tsv')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    verify(output)


def verify(output):
    report=json.loads((output/'report.json').read_text())
    if report['schema']!='helix-orca-temperature-proof/v1' or report['status']!='pass' or report['runtime_candidate_files']!=hashes():raise ValueError('Evidence is not bound to current runtime candidate')
    runtime=report['runtime'];origin=runtime['binary_origin']
    if report['helix_source_commit']!=d.h.HELIX_SOURCE_COMMIT or runtime['source_commit']!=d.h.HELIX_SOURCE_COMMIT or runtime['tag']!=d.h.HELIX_TAG or runtime['tag_object']!=d.h.HELIX_TAG_OBJECT or runtime['release_archive_sha256']!=d.h.HELIX_RELEASE_SHA256 or report['helix_binary_sha256']!=runtime['binary_sha256'] or report['isolation_contract']['binary_sha256']!=runtime['binary_sha256'] or report['product_hashes']!=d.h._plugin_hashes():raise ValueError('Native runtime/product pin mismatch')
    if origin['kind']=='actions-artifact':
        if runtime['binary_sha256']!=d.h.HELIX_ARTIFACT_BINARY_SHA256:raise ValueError('Actions binary pin mismatch')
    elif origin['kind']=='source-build':
        if origin['builder_dockerfile_sha256']!=d.digest(d.h.BUILDER_DOCKERFILE) or origin['builder_image']!=d.h.BUILDER_IMAGE or origin['source_url']!=d.h.HELIX_SOURCE_URL or len(origin['submodules'])!=d.h.HELIX_SUBMODULE_COUNT:raise ValueError('Source-built runtime provenance mismatch')
    else:raise ValueError('Unknown runtime provenance')
    if [r['viewport'] for r in report['viewport_runs']]!=[list(v) for v in d.h.VIEWPORTS]:raise ValueError('Evidence lacks the eleven targets')
    if d.digest(output/'request.json')!=report['request_sha256'] or d.digest(output/'result.json')!=report['result_sha256'] or d.digest(output/'matrix.tsv')!=report['matrix_sha256']:raise ValueError('Evidence artifact digest mismatch')
    for row in report['viewport_runs']:
        if row['status']!='pass' or row['network']!='none' or row['test'] is not True or row['readonly_root'] is not True or row['binary_sha256']!=runtime['binary_sha256'] or set(row['frames'])!=set(PHASES):raise ValueError('Incomplete native lifecycle evidence')
        for phase in PUBLIC_PHASES:
            relative=f"native/{row['viewport'][0]}/{phase}.png"
            if report['frames'].get(relative)!=row['frames'][phase] or dimensions(output/relative)!=row['viewport'][1:3]:raise ValueError('Native evidence frame missing or mismatched')
    for relative,sha in dict(report['frames'],**report['windows_frames']).items():
        path=Path(relative)
        if path.is_absolute() or '..' in path.parts or d.digest(output/path)!=sha:raise ValueError('Frame digest/path mismatch')
    print('PASS: current Temperature runtime candidate, artifacts, and all eleven native targets')


def viewer_owned():
    pidfile=d.STATE/'review-viewer.pid'
    if not pidfile.exists():return None
    pid=int(pidfile.read_text())
    command=Path(f'/proc/{pid}/cmdline')
    if not command.exists():pidfile.unlink();return None
    args=command.read_bytes().split(b'\0')
    permitted=[[b'python3',str(ROOT/script).encode(),b'serve'] for script in
        ('scripts/temperature-roundtrip.py','scripts/temperature-evidence.py')]
    if args[:3] not in permitted:
        raise ValueError('Refusing to signal an unexpected viewer process')
    return pid


def review(request,gcode):
    if viewer_owned():print('Native review already running at http://192.168.1.114:8540/');return
    probe=socket.socket()
    try:
        probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        probe.bind((d.h.REVIEW_HOST,d.h.REVIEW_PORT))
    finally:probe.close()
    info=d.inspect()
    if info:
        raise ValueError('Existing marked proof runtime: use down before a fresh review')
    d.start(request,gcode,next(v for v in d.h.VIEWPORTS if v[0]=='medium_800x480'))
    d.await_state(1)
    # Let native entry animation finish before deleting animations in freeze.
    # A stable native frame is required; state alone precedes overlay entry.
    current=json.loads((d.STATE/'current.json').read_text())
    d.h._screenshot(d.NAME,Path(current['work']),'review-entry.png')
    # Park the synthetic clock before creating the remote pointer. The pointer
    # sampler is created by first input afterward and stays live; native
    # navigation/update/render queues continue throughout review.
    d.ctl('freeze')
    log=(d.STATE/'review-viewer.log').open('ab')
    process=subprocess.Popen(['python3',str(Path(__file__).resolve()),'serve'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    log.close();(d.STATE/'review-viewer.pid').write_text(str(process.pid))
    end=time.monotonic()+10
    while time.monotonic()<end:
        if process.poll() is not None:raise ValueError('Native review listener exited; inspect its private log')
        try:
            with urllib.request.urlopen('http://192.168.1.114:8540/',timeout=1) as response:
                if response.status==200:print('Native review: http://192.168.1.114:8540/');return
        except OSError:time.sleep(.1)
    raise ValueError('Native review did not become reachable')


def drag(body):
    coordinates=[body[k] for k in ('x0','y0','x1','y1')]
    if any(type(v) is not int or not 0<=v<limit for v,limit in zip(coordinates,(800,480,800,480))):
        raise ValueError('Drag is outside the native 800x480 viewport')
    if not d.inspect():raise ValueError('No isolated proof runtime')
    x0,y0,x1,y1=coordinates
    d.ctl('press',str(x0),str(y0))
    try:
        for step in range(1,9):
            d.ctl('move',str(round(x0+(x1-x0)*step/8)),str(round(y0+(y1-y0)*step/8)))
    finally:d.ctl('release',str(x1),str(y1))
    d.ctl('wait_idle')


def finish_mock():
    d.finish_simulation()


def serve():
    if not d.inspect():raise ValueError('No isolated proof runtime')
    current=json.loads((d.STATE/'current.json').read_text());work=Path(current['work'])
    d.h.CONTAINER=d.NAME;d.h.REVIEW_BIND=d.h.REVIEW_HOST;d.h.state_root=lambda:work
    version=hashlib.sha256(json.dumps(hashes(),sort_keys=True).encode()).hexdigest()
    d.h.VIEWER_HTML=(ROOT/'scripts/temperature-viewer.html').read_text().replace('__REVIEW_VERSION__',version)
    storage=json.loads((work/'config/plugin-data/calibration-bridge.json').read_text())
    last_sequence=storage.get('review_action',{}).get('sequence',0)
    base=d.h.ViewerHandler
    class ProofViewer(base):
        def do_GET(self):
            nonlocal last_sequence
            route=self.path.split('?',1)[0]
            if route in ('/frame.png','/api/review-state'):
                with self.capture_lock:
                    try:
                        last_sequence=d.consume_review_action(work,last_sequence)
                        if route=='/api/review-state':
                            self._json({'version':version,'state':d.ctl('get','calibration-bridge__state')['value']});return
                    except Exception as exc:
                        self._json({'error':str(exc)},503);return
            return super().do_GET()
        def do_POST(self):
            with self.capture_lock:
                if not d.inspect():self._json({'error':'No isolated proof runtime'},503);return
                if self.path=='/api/finish-mock':
                    try:finish_mock();self._json({'message':'Simulation complete; choose a temperature in native Helix'})
                    except Exception as exc:self._json({'error':str(exc)},400)
                    return
                if self.path!='/api/drag':return super().do_POST()
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=4096:raise ValueError('Invalid input size')
                    drag(json.loads(self.rfile.read(length)))
                    self._json({'message':'Native drag'})
                except Exception as exc:self._json({'error':str(exc)},400)
    d.h.ViewerHandler=ProofViewer
    d.h.serve()


def down():
    pid=viewer_owned()
    if pid:
        os.kill(pid,signal.SIGTERM)
        end=time.monotonic()+5
        while Path(f'/proc/{pid}/cmdline').exists() and time.monotonic()<end:time.sleep(.1)
        (d.STATE/'review-viewer.pid').unlink(missing_ok=True)
    if d.inspect():d.h.run(['docker','rm','--force',d.NAME],capture=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['capture','promote','verify','review','down','serve']);p.add_argument('--request',type=Path);p.add_argument('--gcode',type=Path);p.add_argument('--output',type=Path,default=ROOT/'docs/evidence/issue-4/roundtrip');a=p.parse_args()
    if a.command in ('capture','promote','review') and not a.request:p.error('--request is required')
    if a.command in ('capture','review') and not a.gcode:p.error('--gcode is required')
    if a.command=='capture':capture(a.request,a.gcode)
    elif a.command=='promote':promote(a.output,a.request)
    elif a.command=='review':review(a.request,a.gcode)
    elif a.command=='down':down()
    elif a.command=='serve':serve()
    else:verify(a.output)

if __name__=='__main__':main()
