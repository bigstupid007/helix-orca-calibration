#!/usr/bin/env python3
"""Separate, LAN-reviewed native mock Temperature proof. Never uses a real printer."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('helix_dev', ROOT / 'scripts/helix_dev.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
NAME = 'helix-orca-temperature-proof'
LABEL = 'helix-orca.issue4.mock-proof'
STATE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'helix-orca-calibration/temperature-roundtrip'
BRIDGE = ROOT / 'integration/calibration-bridge'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def prepare(request_path, gcode):
    request = json.loads(request_path.read_text())
    if request.get('schema') != 'helix-orca-temperature-request/v1' or request.get('mock_only') is not True:
        raise ValueError('Only an explicitly mock-only Orca request is accepted')
    target = request['target']; file = request['file']
    if request['wizard'] != 'temp_tower' or request['choices'] != list(range(230,189,-5)):
        raise ValueError('Temperature choices must match the Windows-qualified nine bands')
    if request['context_sha256'] != canonical(target):
        raise ValueError('Context digest mismatch')
    identifier = canonical({'context': request['context_sha256'], 'file': file, 'created_at': request['created_at_utc']})[:32]
    if request['request_id'] != identifier or request['bridge_file'] != f'helix-temp-{identifier}.gcode':
        raise ValueError('Request identity mismatch')
    if target['runtime'] != {'version':'2.5.0-dev','build':'210bc927'}:
        raise ValueError('Request must come from the qualified Windows nightly')
    if gcode.stat().st_size != file['size'] or digest(gcode) != file['sha256'] or gcode.name != file['name']:
        raise ValueError('Actual exported file bytes/name differ from the request')
    if not 0 < file['size'] <= 20000000:
        raise ValueError('Exported file exceeds the bounded proof size')
    bands = list(dict.fromkeys(int(v) for v in re.findall(r'^M10[49]\s+S(\d+)(?:\s|$)', gcode.read_text(), re.M) if int(v)>0))
    if bands != request['choices'] or file['bands'] != bands:
        raise ValueError('Actual file bands differ from request')
    return request, {'mock_only': True, 'wizard':'temp_tower', 'request_id':identifier,
        'context_sha256':request['context_sha256'], 'file_sha256':file['sha256'],
        'file':request['bridge_file'], 'choices':bands,
        'printer':target['printer']['selected_saved']['name'],
        'filament':target['filament']['selected_saved']['name'],
        'nozzle_mm':target['nozzle_mm'], 'current':target['effective_temperature'],
        'saved_current':target['saved_temperature']}


def mount_scaffold():
    # Nested read-only mounts need pre-existing mountpoints. Never add directories
    # to the accepted product or the verified runtime cache.
    cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache')) / 'helix-orca-calibration/temperature-proof-mounts' / h.HELIX_SOURCE_COMMIT
    runtime = cache/'runtime'
    if not runtime.exists():
        cache.mkdir(parents=True, exist_ok=True)
        shutil.copytree(h.runtime_path(),runtime,copy_function=os.link,symlinks=True)
    (runtime/'assets/test_gcodes').mkdir(parents=True,exist_ok=True)
    plugins = cache/'plugins'
    (plugins/'orcacal').mkdir(parents=True,exist_ok=True)
    (plugins/'calibration-bridge').mkdir(exist_ok=True)
    return runtime,plugins


def inspect(name=NAME):
    result = h.run(['docker','inspect',name], capture=True, check=False)
    if result.returncode:
        return None
    info = json.loads(result.stdout)[0]
    expected = {'/binary','/helix','/plugin','/plugin/orcacal','/plugin/calibration-bridge','/helix/assets/test_gcodes','/state'}
    mounts = info['Mounts']
    if (info['Config']['Labels'].get(LABEL) != 'true' or info['HostConfig']['NetworkMode'] != 'none'
        or not info['HostConfig']['ReadonlyRootfs'] or info['Config']['Image'] != h.IMAGE
        or '--test' not in info['Args'] or '--real' in info['Args']
        or {m['Destination'] for m in mounts} != expected
        or any(m['RW'] for m in mounts if m['Destination'] != '/state')
        or info['HostConfig'].get('PortBindings') or info['HostConfig']['Privileged']):
        raise ValueError('Refusing access to a container outside the isolated mock contract')
    state = next(m['Source'] for m in mounts if m['Destination']=='/state')
    if not Path(state).is_relative_to(STATE) or not (Path(state)/'.mock-only').is_file():
        raise ValueError('Unmarked or unexpected state directory')
    return info


def start(request_path,gcode,entry,fail_first=False):
    request, payload = prepare(request_path,gcode)
    if inspect():
        raise ValueError('Proof container exists; use down explicitly before a new proof')
    h.verify_assets(); h.image_metadata()
    runtime,plugins = mount_scaffold()
    label,width,height,layout,dpi=entry
    work=STATE / (time.strftime('%Y%m%d-%H%M%S')+'-'+label)
    work.mkdir(parents=True,mode=0o700); (work/'.mock-only').write_text('Issue #4 network-none native mock only\n')
    (work/'home').mkdir(); (work/'files').mkdir()
    shutil.copyfile(gcode,work/'files'/request['bridge_file'])
    os.chmod(work/'files'/request['bridge_file'],0o400)
    (work/'request.json').write_text(json.dumps(payload,sort_keys=True,separators=(',',':')))
    bridge=work/'bridge';shutil.copytree(BRIDGE,bridge)
    storage=work/'config/plugin-data/calibration-bridge.json'
    storage.parent.mkdir(parents=True,exist_ok=True)
    if not fail_first:storage.write_text(json.dumps({'request':payload}))
    (work/'orca-request.json').write_bytes(request_path.read_bytes())
    config=h.seed_settings(work/'config')
    settings=json.loads(config.read_text());settings['plugins']['enabled']['calibration-bridge']={'permissions':['storage','moonraker_write'],'version':'0.1.0'}
    h.json_write(config,settings)
    args=h._container_args(NAME,work,width,height,layout,dpi)
    args[args.index(f'{h.runtime_path()}:/helix:ro')]=f'{runtime}:/helix:ro'
    args[args.index(f'{h.PLUGIN_ROOT}:/plugin:ro')]=f'{plugins}:/plugin:ro'
    idx=args.index(h.IMAGE)
    args[idx:idx]=['--label',LABEL+'=true','-v',f'{h.PLUGIN_DIR}:/plugin/orcacal:ro','-v',f'{bridge}:/plugin/calibration-bridge:ro','-v',f'{work}/files:/helix/assets/test_gcodes:ro']
    h.run(args,capture=True); info=inspect(); h.wait_ready(NAME)
    (STATE/'current.json').write_text(json.dumps({'work':str(work),'viewport':entry,'request_id':request['request_id']},indent=2))
    (work/'isolation.json').write_text(json.dumps({'network':info['HostConfig']['NetworkMode'],'test':True,'readonly_root':True,'mounts':[{'destination':m['Destination'],'rw':m['RW']} for m in info['Mounts']], 'binary_sha256':h.sha256(h.binary_path()),'product_hashes':h._plugin_hashes(),'bridge_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sorted(BRIDGE.rglob('*')) if p.is_file()}},indent=2))
    return work


def ctl(*args):
    inspect()
    try:return h.ctl(NAME,*args)
    except subprocess.CalledProcessError as exc:
        raise ValueError((exc.stderr or exc.stdout or 'Native control failed').strip()) from exc


def await_state(value,timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if ctl('get','calibration-bridge__state')['value']==value:return
        time.sleep(.15)
    raise ValueError(f'Native bridge did not reach state {value}')


def tap(name,width,height):
    ctl('scroll',name); ctl('wait_idle')
    widget=h._visible_widget_geometry(ctl('geom',name,'0'),name,width,height)
    x=str(int(widget['x'])+int(widget['w'])//2);y=str(int(widget['y'])+int(widget['h'])//2)
    ctl('press',x,y);ctl('release',x,y);ctl('wait_idle')


def run_capture(request,gcode,entry,fail_first=False):
    work=start(request,gcode,entry,fail_first)
    _,width,height,_,_=entry
    try:
        if fail_first:
            end=time.monotonic()+10
            while time.monotonic()<end:
                status=ctl('get','calibration-bridge__status_line')['value']
                if 'failed' in status:break
                time.sleep(.1)
            else:raise ValueError('Native request failure was not visible')
            h._screenshot(NAME,work,'request-retry.png')
            storage=work/'config/plugin-data/calibration-bridge.json'
            storage.write_text(json.dumps({'request':json.loads((work/'request.json').read_text())}))
            # Reload clears the native storage cache after real artifact delivery.
            (work/'bridge/.delivery-reload.lua').write_text('-- test-only delivery reload\n')
        await_state(1)
        end=time.monotonic()+5
        while time.monotonic()<end:
            geometry=h.ctl(NAME,'geom','calibration-bridge__ask_content','8',check=False)
            try:
                if not geometry:raise ValueError('Overlay pending')
                h._assert_horizontal_fit(geometry,width)
                break
            except (ValueError,h.HarnessError):time.sleep(.1)
        else:raise ValueError('Available overlay did not finish native navigation')
        ctl('freeze')
        h._screenshot(NAME,work,'available.png')
        if ctl('get','print_state')['value']=='printing':raise ValueError('Receiving a request started printing')
        h._assert_horizontal_fit(ctl('geom','calibration-bridge__ask_content','8'),width)
        ctl('unfreeze')
        tap('calibration-bridge__start',width,height)
        await_state(2)
        end=time.monotonic()+10
        while time.monotonic()<end:
            if ctl('get','print_state_enum')['value']==1 and ctl('get','print_state')['value']=='printing':break
            time.sleep(.15)
        else:raise ValueError('Native mock start never published a printing state')
        ctl('freeze')
        h._screenshot(NAME,work,'printing.png')
        ctl('set','print_progress','50')
        if ctl('get','calibration-bridge__progress_line')['value'] != 'Mock progress: 50%':raise ValueError('Mock progress not visible')
        ctl('screenshot','/state/progress.png')
        ctl('set','print_progress','100')
        ctl('set','print_state_enum','3')
        ctl('set','print_state','complete')
        await_state(3)
        end=time.monotonic()+5
        while time.monotonic()<end:
            geometry=h.ctl(NAME,'geom','calibration-bridge__pick','0',check=False)
            if geometry and geometry.get('widgets'):break
            time.sleep(.1)
        ctl('screenshot','/state/completion.png')
        # Native dropdown selection emits its real LVGL value-changed event.
        modal=h.ctl(NAME,'geom','print_completion_modal','2',check=False)
        if modal and modal.get('widgets'):
            ctl('click','btn_primary')
        (work/'completion-state.json').write_text(json.dumps(ctl('current'),indent=2))
        ctl('scroll','calibration-bridge__pick')
        ctl('set_value','calibration-bridge__pick','5')
        if ctl('get','calibration-bridge__choice_idx')['value'] != 5:raise ValueError('Native dropdown did not select 205 C')
        h._screenshot(NAME,work,'choice.png')
        storage=work/'config/plugin-data/calibration-bridge.json'
        if fail_first:os.chmod(storage.parent,0o500)
        ctl('scroll','calibration-bridge__next');ctl('wait_idle')
        h._visible_widget_geometry(ctl('geom','calibration-bridge__next','0'),'calibration-bridge__next',width,height)
        ctl('click','calibration-bridge__next')
        if fail_first:
            await_state(3)
            h._screenshot(NAME,work,'result-retry.png')
            os.chmod(storage.parent,0o700)
            ctl('scroll','calibration-bridge__next');ctl('wait_idle')
            h._visible_widget_geometry(ctl('geom','calibration-bridge__next','0'),'calibration-bridge__next',width,height)
            ctl('click','calibration-bridge__next')
        await_state(4)
        result=json.loads(storage.read_text())['result']
        (work/'result.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':')))
        if result['request_id']!=json.loads(request.read_text())['request_id'] or result['value']!=205:raise ValueError('Native result mismatch')
        h._screenshot(NAME,work,'returned.png')
        (work/'logs.txt').write_text(h.run(['docker','logs',NAME],capture=True).stdout)
        h._assert_horizontal_fit(ctl('geom','calibration-bridge__ask_content','8'),width)
        return work
    finally:
        storage=work/'config/plugin-data/calibration-bridge.json'
        if storage.parent.exists():os.chmod(storage.parent,0o700)
        if inspect():
            logs=h.run(['docker','logs',NAME],capture=True,check=False)
            (work/'logs.txt').write_text(logs.stdout+'\n'+logs.stderr)
            h.run(['docker','rm','--force',NAME],capture=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['up','down','status','capture','matrix','serve'])
    p.add_argument('--request',type=Path);p.add_argument('--gcode',type=Path);p.add_argument('--fail-first',action='store_true');p.add_argument('--viewport',default='medium_800x480')
    a=p.parse_args()
    if a.command=='down':
        if inspect():h.run(['docker','rm','--force',NAME],capture=True)
    elif a.command=='status':print(json.dumps(inspect(),indent=2))
    elif a.command=='serve':
        if not inspect():raise ValueError('No isolated proof runtime')
        current=json.loads((STATE/'current.json').read_text());h.CONTAINER=NAME;h.REVIEW_BIND=h.REVIEW_HOST;h.state_root=lambda:Path(current['work']);h.serve()
    else:
        if not a.request or not a.gcode:raise ValueError('--request and --gcode are required')
        entry=next(e for e in h.VIEWPORTS if e[0]==a.viewport)
        if a.command=='up':print(start(a.request,a.gcode,entry,a.fail_first))
        elif a.command=='capture':print(run_capture(a.request,a.gcode,entry,a.fail_first))
        else:
            records=[]
            for entry in h.VIEWPORTS:
                work=run_capture(a.request,a.gcode,entry,True)
                records.append({'viewport':entry,'work':str(work),'result_sha256':digest(work/'result.json')})
                print('PASS',entry[0],flush=True)
            (STATE/'matrix.json').write_text(json.dumps(records,indent=2))

if __name__=='__main__':
    main()
