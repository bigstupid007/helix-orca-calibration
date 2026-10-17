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

def validate_grant(grant,payload,qualification,now):
    required={'schema','founder_authorization_reference','authorized','native_screen_start_only','request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer','physical_printer_identity','printer_config_sha256','qualification_sha256','expires_at'}
    if not isinstance(grant,dict) or set(grant)!=required or grant['schema']!='helix-orca-physical-test-authorization/v1':raise ValueError('Exact private physical authorization required')
    if grant['authorized'] is not True or grant['native_screen_start_only'] is not True:raise ValueError('Physical test is not authorized')
    digest=hashlib.sha256(json.dumps(qualification,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if grant['qualification_sha256']!=digest:raise ValueError('Authorization qualification digest differs')
    reference=grant['founder_authorization_reference']
    if not isinstance(reference,str) or not reference.strip() or len(reference)>512:raise ValueError('Explicit Founder instruction reference required')
    for k in ('request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer'):
        if type(grant[k]) is not type(payload[k]) or grant[k]!=payload[k]:raise ValueError('Authorization request binding differs')
    for k in ('physical_printer_identity','printer_config_sha256'):
        if grant[k]!=qualification[k]:raise ValueError('Authorization qualification binding differs')
    if type(grant['expires_at']) is not int or not now<grant['expires_at']<=payload['expires_at']:raise ValueError('Authorization expired or exceeds request lifetime')
    return copy.deepcopy(grant)

def execute(args,outbox,qualification):
    if args.trusted_lan_ack!=transport.accepted.TRUSTED_LAN_ACK:raise ValueError('Existing trusted-LAN limitation acknowledgement required')
    grant=validate_grant(read(args.founder_authorization),outbox['payload'],qualification,time.time())
    if args.journal.exists()!=args.resume:raise ValueError('Existing journal requires --resume; a new run requires a new journal')
    physical=transport.MoonrakerPrintAdapter(args.moonraker,args.expected_host,args.expected_version,
        qualification['physical_printer_identity'],configuration_sha256=qualification['printer_config_sha256'],actions=True)
    artifacts=PrintArtifacts(args.communication_dir);events=PrintEvents(physical)
    if artifacts.read_json('outbox.json')!=outbox:raise ValueError('Originating Orca outbox differs')
    # A request file alone never grants a run. Only a validated native intent can
    # cause a local permit to be issued, bound to that exact tap and original job.
    def authorize(c,intent):
        validate_grant(grant,outbox['payload'],qualification,time.time())
        if artifacts.read_json('outbox.json')!=outbox:raise ValueError('Originating request changed before native Start')
        return c.issue_local_permit(intent,authorization_id=outbox['payload']['request_id'],
            deadline_monotonic=time.monotonic()+min(30,grant['expires_at']-time.time()))
    with transport.lc.TemperaturePrintLifecycle(args.journal,physical) as lifecycle:
        session=controller.NativePrintController(lifecycle,outbox,qualification,event_sink=events.send,
            write_inbox=lambda value:artifacts.write_json('inbox.json',value),authorize_intent=authorize)
        if lifecycle.status().phase=='awaiting_start':session.offer()
        deadline=time.monotonic()+3600
        last_forward=time.monotonic()
        while time.monotonic()<deadline:
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
        raise ValueError('Bounded test window expired; inspect real printer state before any further action')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outbox',type=Path,required=True);p.add_argument('--qualification',type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--founder-authorization',type=Path)
    p.add_argument('--moonraker');p.add_argument('--expected-host');p.add_argument('--expected-version')
    p.add_argument('--communication-dir');p.add_argument('--journal',type=Path);p.add_argument('--trusted-lan-ack')
    a=p.parse_args();outbox=controller.protocol.validate_outbox(read(a.outbox));qualification=read(a.qualification)
    q=transport.lc.GcodeQualification.from_mapping(qualification)
    q.assert_matches(transport.lc.BoundRequest.from_mapping(outbox['payload'],time.time()))
    if not a.execute:
        print(json.dumps({'offline_preflight':True,'physical_actions':False,'qualified_duration_s':q.estimated_duration_s}));return
    if not all((a.founder_authorization,a.moonraker,a.expected_host,a.expected_version,a.communication_dir,a.journal)):
        p.error('Execution requires separate explicit Founder authorization and every exact private target binding')
    execute(a,outbox,qualification)

if __name__=='__main__':main()
