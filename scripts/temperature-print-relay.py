#!/usr/bin/env python3
"""One-request physical-test runner. Default is offline preflight, never execution.

No authorization artifact is created by this tool. A future --execute run
requires separate explicit Founder authorization, staged native candidate and
the exact privately reviewed grant; this readiness program must never use it.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    if name in sys.modules:return sys.modules[name]
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
transport=load('_print_runner_transport',ROOT/'integration/temperature-print/transport.py')
controller=load('_print_runner_controller',ROOT/'integration/temperature-print/controller.py')

class PrintEvents:
    EVENTS={'helix_orca_temperature_print.request.v1','helix_orca_temperature_print.status.v1','helix_orca_temperature_print.ack.v1'}
    def __init__(self,physical):self.physical=physical
    def send(self,event,data):
        if event not in self.EVENTS or not isinstance(data,dict):raise ValueError('Unexpected event')
        origin=urlparse(self.physical.reader.base_url)
        ws=self.physical.reader.display.WebSocket(origin.hostname,origin.port or 80,'/websocket')
        try:
            identify={'client_name':'helix-orca-temperature-print','version':'0.1.0','type':'agent','url':'https://github.com/bigstupid007/helix-orca-calibration/issues/12'}
            if self.physical.reader.api_key:identify['api_key']=self.physical.reader.api_key
            for n,method,params in [(1,'server.connection.identify',identify),(2,'connection.send_event',{'event':event,'data':data})]:
                body=json.dumps({'jsonrpc':'2.0','method':method,'params':params,'id':n},separators=(',',':'),allow_nan=False).encode()
                if len(body)>65536:raise ValueError('Event exceeds bound')
                ws.send_frame(1,body)
                for _ in range(17):
                    reply=ws.receive_json()
                    if isinstance(reply,dict) and reply.get('id')==n:
                        if 'error' in reply or (n==2 and reply.get('result')!='ok'):raise ValueError('Event rejected')
                        break
                else:raise ValueError('Event response unavailable')
        finally:ws.close()

class PrintArtifacts:
    def __init__(self,directory):
        # Isolated module instance: only the approved exact local child changes.
        module=load('_print_only_artifact_source',ROOT/'scripts/temperature-communication-relay.py')
        module.COMMUNICATION_RELATIVE='orca_plugins\\plugin_data\\helix_calibration\\print-readiness'
        self.source=module.SpareAdapter(directory)
    def read_json(self,name):return self.source.read_json(name)
    def write_json(self,name,value):return self.source.write_json(name,value)

def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>262144:raise ValueError('Bounded private JSON file required')
    return json.loads(path.read_text())

def validate_grant(grant,payload,qualification,now,*,allow_expired=False):
    required={'schema','founder_authorization_reference','authorized','native_screen_start_only','request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer','physical_printer_identity','printer_config_sha256','qualification_sha256','moonraker_version','expires_at'}
    if not isinstance(grant,dict) or set(grant)!=required or grant['schema']!='helix-orca-physical-test-authorization/v1':raise ValueError('Exact private physical authorization required')
    if grant['authorized'] is not True or grant['native_screen_start_only'] is not True:raise ValueError('Physical test is not authorized')
    digest=hashlib.sha256(json.dumps(qualification,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if grant['qualification_sha256']!=digest:raise ValueError('Authorization qualification digest differs')
    reference=grant['founder_authorization_reference']
    if not isinstance(reference,str) or not reference.strip() or len(reference)>512:raise ValueError('Explicit Founder instruction reference required')
    for k in ('request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer'):
        if type(grant[k]) is not type(payload[k]) or grant[k]!=payload[k]:raise ValueError('Authorization request binding differs')
    for k in ('physical_printer_identity','printer_config_sha256','moonraker_version'):
        if grant[k]!=qualification[k]:raise ValueError('Authorization qualification binding differs')
    created=payload['expires_at']-payload['ttl_seconds']
    if type(grant['expires_at']) is not int or not created<grant['expires_at']<=payload['expires_at'] or (not allow_expired and now>=grant['expires_at']):raise ValueError('Authorization expired or exceeds request lifetime')
    return copy.deepcopy(grant)

def require_live_authorization(coordinator,grant,payload,qualification,now):
    try:return validate_grant(grant,payload,qualification,now)
    except ValueError:
        if coordinator.status().phase=='awaiting_start':
            coordinator._fail('failed','Physical authorization expired or changed before Start')
        raise

def bind_authorization(coordinator,grant,payload,qualification,now,*,resume):
    # One immutable grant per request/journal. A later authorization requires a
    # fresh request and physical tap; it cannot revive an earlier persisted tap.
    phase=coordinator.status().phase
    if phase=='awaiting_start':require_live_authorization(coordinator,grant,payload,qualification,now)
    else:validate_grant(grant,payload,qualification,now,allow_expired=resume)
    digest=hashlib.sha256(json.dumps(grant,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    previous=coordinator._state.get('founder_grant_sha256')
    if (resume and previous is None) or (previous is not None and previous!=digest):
        if phase=='awaiting_start':coordinator._fail('failed','Recovered Founder authorization differs')
        raise ValueError('Recovered Founder grant differs; use a fresh request and native Start')
    if previous is None:
        coordinator._state['founder_grant_sha256']=digest;coordinator._persist()

def validate_tap_after_offer(coordinator,intent):
    lease=coordinator._state.get('native_envelope',{}).get('lease',{})
    issued=lease.get('issued_eventtime')
    if type(issued) not in (int,float) or intent.eventtime<issued:
        raise ValueError('Native Start predates the separately authorized offer')

def execute(args,outbox,qualification):
    if args.trusted_lan_ack!=transport.accepted.TRUSTED_LAN_ACK:raise ValueError('Existing trusted-LAN limitation acknowledgement required')
    grant=validate_grant(read(args.founder_authorization),outbox['payload'],qualification,time.time(),allow_expired=args.resume)
    if args.journal.exists()!=args.resume:raise ValueError('Existing journal requires --resume; a new run requires a new journal')
    physical=transport.MoonrakerPrintAdapter(args.moonraker,args.expected_host,qualification['moonraker_version'],
        qualification['physical_printer_identity'],configuration_sha256=qualification['printer_config_sha256'],actions=True)
    artifacts=PrintArtifacts(args.communication_dir);events=PrintEvents(physical)
    if artifacts.read_json('outbox.json')!=outbox:raise ValueError('Originating Orca outbox differs')
    # A request file alone never grants a run. Only a validated native intent can
    # cause a local permit to be issued, bound to that exact tap and original job.
    def authorize(c,intent):
        require_live_authorization(c,grant,outbox['payload'],qualification,time.time())
        validate_tap_after_offer(c,intent)
        if artifacts.read_json('outbox.json')!=outbox:raise ValueError('Originating request changed before native Start')
        return c.issue_local_permit(intent,authorization_id=outbox['payload']['request_id'],
            deadline_monotonic=time.monotonic()+min(30,grant['expires_at']-time.time()))
    with transport.lc.TemperaturePrintLifecycle(args.journal,physical) as lifecycle:
        session=controller.NativePrintController(lifecycle,outbox,qualification,event_sink=events.send,
            write_inbox=lambda value:artifacts.write_json('inbox.json',value),
            write_delivery=lambda value:artifacts.write_json('delivery.json',value),authorize_intent=authorize)
        try:
            bind_authorization(lifecycle,grant,outbox['payload'],qualification,time.time(),resume=args.resume)
            if lifecycle.status().phase=='awaiting_start':session.offer()
            last_forward=time.monotonic()
            while True:
                if lifecycle.status().phase=='awaiting_start':
                    require_live_authorization(lifecycle,grant,outbox['payload'],qualification,time.time())
                    created=outbox['payload']['expires_at']-outbox['payload']['ttl_seconds']
                    if time.time()>=created+900:
                        lifecycle._fail('failed','Original physical Start window expired')
                        session._publish()
                        raise ValueError('Original physical Start window expired')
                stored=physical.reader.read_native_storage()
                if stored.get('print_session',{}).get('request')!=outbox['payload']:
                    if lifecycle.status().phase=='awaiting_start' and time.monotonic()-last_forward>=2:
                        session.offer();last_forward=time.monotonic()
                    elif lifecycle.status().phase!='awaiting_start':
                        lifecycle.poll();session._publish()
                if stored.get('print_session',{}).get('request')==outbox['payload']:
                    status=session.step(stored)
                    receipt=artifacts.read_json('receipt.json')
                    if receipt is not None and session.committed_result is not None:
                        session.acknowledge(receipt)
                    native=physical.reader.read_native_storage().get('print_session',{})
                    if native.get('state')=='returned' and native.get('result')==session.committed_result and session.committed_result:
                        artifacts.write_json('delivery.json',dict(schema=controller.protocol.DELIVERY_SCHEMA,
                            request_id=outbox['payload']['request_id'],origin_id=outbox['payload']['origin_id'],
                            context_sha256=outbox['payload']['context_sha256'],phase='delivered'))
                        return
                    if status.phase not in ('awaiting_start','start_dispatch_intent','start_dispatched','printing','completion_pending','completed','cancel_dispatch_intent','cancel_dispatched'):
                        raise ValueError('Physical lifecycle stopped in '+status.phase)
                time.sleep(1)
        except (ValueError,transport.lc.LifecycleError):
            session._publish()
            raise

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outbox',type=Path,required=True);p.add_argument('--qualification',type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--founder-authorization',type=Path)
    p.add_argument('--moonraker');p.add_argument('--expected-host');p.add_argument('--expected-version',help='Optional compatibility assertion; must equal the qualification pin')
    p.add_argument('--communication-dir');p.add_argument('--journal',type=Path);p.add_argument('--trusted-lan-ack')
    a=p.parse_args();raw=read(a.outbox)
    validation_time=raw['payload']['expires_at']-raw['payload']['ttl_seconds'] if a.resume else time.time()
    outbox=controller.protocol.validate_outbox(raw,now=validation_time);qualification=read(a.qualification)
    q=transport.lc.GcodeQualification.from_mapping(qualification)
    q.assert_matches(transport.lc.BoundRequest.from_mapping(outbox['payload'],validation_time))
    if not a.execute:
        print(json.dumps({'offline_preflight':True,'physical_actions':False,'qualified_duration_s':q.estimated_duration_s}));return
    if not all((a.founder_authorization,a.moonraker,a.expected_host,a.communication_dir,a.journal)):
        p.error('Execution requires separate explicit Founder authorization and every exact private target binding')
    if a.expected_version is not None and a.expected_version!=qualification['moonraker_version']:raise ValueError('CLI version differs from reviewed qualification')
    execute(a,outbox,qualification)

if __name__=='__main__':main()
