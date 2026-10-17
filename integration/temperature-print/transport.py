"""Bounded Moonraker adapter; physical mutations disabled unless locally activated.

No CLI, listener, credential setup, upload, arbitrary RPC or G-code route is
provided. This program must instantiate it with the default actions=False.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote
from urllib.request import Request

ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    if name in sys.modules:return sys.modules[name]
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module);return module
lc=load('_temperature_print_lifecycle',Path(__file__).with_name('lifecycle.py'))
accepted=load('_temperature_print_accepted_relay',ROOT/'scripts/temperature-communication-relay.py')

class MoonrakerPrintAdapter:
    def __init__(self,base_url,expected_host,expected_version,physical_identity,*,configuration_sha256,api_key=None,actions=False):
        self.reader=accepted.PhysicalAdapter(base_url,expected_host,expected_version,api_key)
        if not re.fullmatch('[a-f0-9]{64}',physical_identity):raise ValueError('Exact physical identity digest required')
        if not re.fullmatch('[a-f0-9]{64}',configuration_sha256):raise ValueError('Exact reviewed configuration digest required')
        self.expected_configuration=configuration_sha256
        self.expected_identity=physical_identity
        if type(actions) is not bool:raise TypeError('actions is a local activation switch')
        self.actions=actions
    def _get(self,path):
        value=self.reader._json_get(path)
        if not isinstance(value,dict) or not isinstance(value.get('result'),dict):raise lc.SafetyViolation('Missing Moonraker result')
        return value['result']
    def _identity(self):
        info=self._get('/machine/system_info')['system_info']
        config=self._get('/printer/objects/query?configfile')['status']['configfile']['settings']
        actual=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if actual!=self.expected_configuration:raise lc.SafetyViolation('Reviewed printer configuration changed')
        mcu=config.get('mcu',{})
        kind='serial' if mcu.get('serial') else 'canbus_uuid'
        serial=mcu.get(kind)
        macs=sorted(x['mac_address'] for x in info['network'].values() if x.get('mac_address'))
        if not isinstance(serial,str) or not serial.strip() or not macs:raise lc.SafetyViolation('Physical identity unavailable')
        digest=hashlib.sha256(json.dumps({'mcu_kind':kind,'mcu_identity':serial,'macs':macs},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if digest!=self.expected_identity:raise lc.SafetyViolation('Physical identity changed')
        return digest
    def snapshot(self):
        began=time.monotonic()
        server=self._get('/server/info')
        if server.get('moonraker_version')!=self.reader.expected_version or server.get('klippy_state')!='ready' or server.get('failed_components'):
            raise lc.SafetyViolation('Moonraker identity/readiness changed')
        identity=self._identity()
        queue=self._get('/server/job_queue/status')
        jobs=queue['queued_jobs']
        if not isinstance(jobs,list) or queue.get('queue_state') not in ('paused','ready'):
            raise lc.SafetyViolation('Queue transition or malformed queue')
        queued=tuple(str(j['job_id']) for j in jobs)
        first=self._get('/printer/objects/query?print_stats')
        stats=first['status']['print_stats']
        filename=stats.get('filename') or None
        job_id=start=None
        if filename:
            lc._file_name(filename)
            metadata=self._get('/server/files/metadata?filename='+quote(filename,safe=''))
            job_id=metadata.get('job_id');start=metadata.get('print_start_time')
        final=self._get('/printer/objects/query?print_stats')
        current=final['status']['print_stats']
        if current.get('filename')!=stats.get('filename') or current.get('state')!=stats.get('state'):
            raise lc.SafetyViolation('Printer job changed during snapshot')
        if time.monotonic()-began>5:raise lc.SafetyViolation('Printer snapshot exceeded its freshness bound')
        return lc.PrinterSnapshot(connected=True,ready=True,eventtime=final['eventtime'],state=current['state'],
            filename=filename,job_id=job_id,start_time=start,queue_job_ids=queued,printer_identity=identity,configuration_sha256=self.expected_configuration,moonraker_version=server['moonraker_version'])
    def read_file_bytes(self,filename):
        lc._file_name(filename)
        request=Request(self.reader.base_url+'/server/files/gcodes/'+quote(filename,safe=''),headers=self.reader._headers('application/octet-stream'))
        with self.reader.opener.open(request,timeout=5) as response:data=response.read(20_000_001)
        if not 0<len(data)<=20_000_000:raise lc.SafetyViolation('G-code readback exceeded bound')
        return data
    def history(self,job_id=None):
        if job_id is None:
            values=self._get('/server/history/list?limit=1&order=desc')['jobs']
            if not isinstance(values,list):raise lc.SafetyViolation('History unavailable')
            if not values:return None
            item=values[0]
        else:
            if not re.fullmatch('[0-9A-Fa-f]{6,64}',job_id):raise lc.SafetyViolation('Invalid Moonraker job ID')
            item=self._get('/server/history/job?uid='+quote(job_id,safe=''))['job']
        phase={'in_progress':'printing','completed':'completed','cancelled':'cancelled','error':'failed','interrupted':'failed','klippy_shutdown':'failed','klippy_disconnect':'failed'}.get(item.get('status'))
        if phase is None:raise lc.SafetyViolation('Unknown history outcome')
        return lc.HistoryRecord(job_id=item['job_id'],filename=item['filename'],status=phase,start_time=item['start_time'],end_time=item.get('end_time'))
    def _post(self,path):
        if not self.actions:raise lc.SafetyViolation('Physical actions are disabled; separate Founder authorization required')
        req=Request(self.reader.base_url+path,data=b'',method='POST',headers=self.reader._headers('application/json'))
        with self.reader.opener.open(req,timeout=5) as response:
            value=json.loads(response.read(65537))
        if value.get('result')!='ok':raise lc.SafetyViolation('Printer command acknowledgement unavailable')
    def start_print(self,filename):
        lc._file_name(filename)
        self._post('/printer/print/start?filename='+quote(filename,safe=''))
    def cancel_print(self):self._post('/printer/print/cancel')
