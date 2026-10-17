"""Join native storage intent, the one-shot coordinator and originating Orca.

No command line, service or automatic authorization is provided. The caller
must supply the existing bounded event/artifact transports; physical permit
issuance remains separate and absent during this readiness program.
"""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import types

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('_print_companion_parts',ROOT/'scripts/temperature-print-companion.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
protocol=types.ModuleType('_print_readiness_protocol')
exec(generator.generated_parts().split('COMMUNICATION_ACTION_NAME')[0],protocol.__dict__)
IDENTITY=('request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer')

class ControllerError(ValueError):pass

class NativePrintController:
    def __init__(self,coordinator,outbox,qualification,*,event_sink,write_inbox,authorize_intent=None):
        self.outbox=protocol.validate_outbox(outbox,now=int(coordinator.wall_time()))
        self.request=copy.deepcopy(self.outbox['payload'])
        self.coordinator=coordinator
        self.coordinator.bind_request(self.request,qualification)
        self.event_sink=event_sink;self.write_inbox=write_inbox
        self.authorize_intent=authorize_intent
        self.sequence=0;self.committed_result=None
    def _identity(self):return {k:self.request[k] for k in IDENTITY}
    def offer(self):
        sample=self.coordinator.adapter.snapshot()
        if not sample.connected or not sample.ready or sample.state!='standby' or sample.queue_job_ids:
            raise ControllerError('Printer is not available for a request')
        remaining=self.request['expires_at']-self.coordinator.wall_time()
        if not 0<remaining<=3600:raise ControllerError('Request expired')
        self.event_sink('helix_orca_temperature_print.request.v1',{'session':copy.deepcopy(self.request),
            'lease':{'issued_eventtime':sample.eventtime,'expires_eventtime':sample.eventtime+remaining}})
        return self._publish()
    def _publish(self):
        state=self.coordinator.status();sample=self.coordinator.adapter.snapshot()
        phase=state.phase
        if phase=='awaiting_start':native='ready' if self.authorize_intent else 'received'
        elif phase in ('start_dispatch_intent','start_dispatched'):native='starting'
        elif phase=='printing':native='printing'
        elif phase in ('cancel_dispatch_intent','cancel_dispatched'):native='cancelling'
        elif phase=='completed' and state.result_available:native='complete'
        elif phase=='cancelled':native='cancelled'
        elif 'uncertain' in phase or phase=='completed':native='uncertain'
        else:native='failed'
        self.sequence+=1
        data=dict(self._identity(),schema='helix-orca-temperature-print-status/v1',state=native,
            eventtime=sample.eventtime,sequence=self.sequence)
        if native=='ready':
            data.update(authorized=True,estimated_duration_s=self.coordinator._qualification_from_state().estimated_duration_s)
        if native=='complete':
            data.update(job_id=state.job_id,completion_sha256=state.completion_proof_sha256)
        self.event_sink('helix_orca_temperature_print.status.v1',data)
        return state
    def step(self,native_storage):
        session=native_storage.get('print_session') if isinstance(native_storage,dict) else None
        if not isinstance(session,dict) or session.get('request')!=self.request:
            raise ControllerError('Native storage does not bind the originating request')
        state=self.coordinator.status()
        intent=session.get('start_intent')
        if intent and state.phase=='awaiting_start':
            if self.authorize_intent is None:raise ControllerError('Separate physical authorization is absent')
            parsed=self.coordinator.parse_start_intent(intent)
            permit=self.authorize_intent(self.coordinator,parsed)
            self.coordinator.start(parsed,permit=permit)
        cancel=session.get('cancel_intent')
        if cancel and self.coordinator.status().phase=='printing':
            check=dict(cancel)
            if check.get('schema')!='helix-orca-temperature-cancel/v1':raise ControllerError('Invalid native cancellation')
            check['schema']='helix-orca-temperature-start/v1'
            parsed=self.coordinator.parse_start_intent(check)
            sample=self.coordinator.adapter.snapshot()
            if not parsed.eventtime<=sample.eventtime<parsed.expires_eventtime:
                raise ControllerError('Stale native cancellation')
            self.coordinator.cancel()
        self.coordinator.poll()
        state=self.coordinator.status()
        result=session.get('result')
        if result:
            if not state.result_available or not state.completion_proof_sha256:
                raise ControllerError('A result requires independent successful completion')
            selected=protocol.validate_selection_result(self.request,result,now=int(self.coordinator.wall_time()))
            if selected['job_id']!=state.job_id or selected['completion_sha256']!=state.completion_proof_sha256:
                raise ControllerError('Result completion evidence does not match the monitored job')
            if self.committed_result is not None and selected!=self.committed_result:
                raise ControllerError('The first selected result is immutable')
            self.write_inbox(copy.deepcopy(selected));self.committed_result=selected
        return self._publish()
    def acknowledge(self,receipt):
        if self.committed_result is None:raise ControllerError('No result has been returned')
        expected=protocol.make_ack(self.committed_result)
        if receipt!=expected:raise ControllerError('Receipt differs from originating committed result')
        self.event_sink('helix_orca_temperature_print.ack.v1',copy.deepcopy(receipt))
