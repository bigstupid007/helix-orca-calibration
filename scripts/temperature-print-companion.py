#!/usr/bin/env python3
"""Generate a separate, nightly-only three-band readiness companion; local I/O only."""
import argparse
import hashlib
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def generated_parts():
    protocol=(ROOT/'integration/temperature-communication/protocol.py').read_text()
    extension=(ROOT/'integration/temperature-communication/orca_extension.py').read_text()
    protocol=protocol.replace('helix-orca-temperature-', 'helix-orca-temperature-print-')
    protocol=protocol.replace('simulation_only','physical_calibration')
    protocol=protocol.replace('CHOICES = [230, 225, 220, 215, 210, 205, 200, 195, 190]','CHOICES = [225, 220, 215]')
    protocol=protocol.replace('TTL_SECONDS = 900','TTL_SECONDS = 3600')
    original='    if value["setting"] != SETTING or value["choices"] != CHOICES'
    if protocol.count(original)!=1: raise ValueError('Accepted context validation anchor changed')
    protocol=protocol.replace(original, '    if value["current"] != 220:\n        raise CommunicationProtocolError("Original effective nozzle temperature must be 220 C.")\n'+original)
    protocol=protocol.replace('"effective_temperature": 1,','"effective_temperature": 220,')
    # A result is accepted only for the exact retained payload and mandatory
    # completed-job proof. Its Start deadline is not a print-duration limit.
    original='def validate_selection_result(payload, value, now=None):\n    payload = validate_forward_payload(payload, now=now)'
    replacement='def validate_selection_result(payload, value, now=None):\n    structural_now = payload["expires_at"] - payload["ttl_seconds"]\n    payload = validate_forward_payload(payload, now=structural_now)'
    if protocol.count(original)!=1: raise ValueError('Accepted result freshness anchor changed')
    protocol=protocol.replace(original,replacement)
    protocol=protocol.replace('/ "communication"','/ "print-readiness"')
    extra_phases={
        "received":"Request received; nothing started.",
        "ready":"Ready for separately authorized native Start.",
        "starting":"Start requested; confirming the same printer job.",
        "printing":"Calibration is printing; monitor on HelixScreen.",
        "confirming":"Print ended; verifying independent completion.",
        "cancelling":"Cancellation requested; awaiting confirmation.",
        "complete":"Successful calibration; waiting for the selected band.",
        "uncertain":"Printer state is uncertain; the original calibration is retained.",
        "cancelled":"Calibration cancelled; no result is available.",
    }
    anchor='\n\nclass CommunicationProtocolError'
    if protocol.count(anchor)!=1: raise ValueError('Accepted delivery phase anchor changed')
    protocol=protocol.replace(anchor,'\nDELIVERY_MESSAGES.update('+repr(extra_phases)+')\nDELIVERY_MESSAGES["failed"]="Calibration failed; no result is available."\nDELIVERY_PHASES=frozenset(DELIVERY_MESSAGES)'+anchor)
    original='        return self.payload is None or self.delivery_delivered or self.is_expired()'
    replacement=\
        '        if self.payload is None or self.delivery_delivered:\n            return True\n'\
        '        try:\n            self.poll_delivery()\n        except Exception:\n            return False\n'\
        '        if self.delivery_phase in {"starting","printing","confirming","cancelling","complete","uncertain"}:\n            return False\n'\
        '        return self.delivery_delivered or self.delivery_phase in {"failed","cancelled"} or self.is_expired()'
    if protocol.count(original)!=1: raise ValueError('Accepted slot retirement anchor changed')
    protocol=protocol.replace(original,replacement)
    protocol=protocol.replace('waiting for a simulated HelixScreen selection.','waiting for authorized physical Start and independently confirmed completion.')
    protocol=protocol.replace('"file", "file_bytes", "setting", "value",','"file", "file_bytes", "setting", "value", "job_id", "completion_sha256",')
    anchor='    if type(value["value"]) is not int or value["value"] not in payload["choices"]:'
    if protocol.count(anchor)!=1: raise ValueError('Accepted result validation anchor changed')
    protocol=protocol.replace(anchor,'    _text(value["job_id"], "completed job", 64)\n    _hex(value["completion_sha256"], HEX64, "independent completion proof")\n'+anchor)
    replacements={
      'Helix Temperature Communication (no printing)':'Helix Miniature Temperature Readiness',
      'Temperature communication (no printing)':'Miniature Temperature readiness',
      'Temperature communication':'Miniature Temperature readiness',
      'Simulated selection only · no printing · no setting is applied.':'Three bands: 225 → 220 → 215 °C. Sending never starts a print. Separate physical-test authorization is required.',
      'Simulated selection':'Selected temperature',
      'simulated selection':'selected temperature',
      'The selected value is simulated; it is not a measured outcome.':'Selection is available only after independently confirmed successful completion.',
      'Review the simulated result':'Review the completed calibration result',
      '[230,225,220,215,210,205,200,195,190]':'[225,220,215]',
      'validate_temperature_file':'validate_print_temperature_file',
      'no printing or profile write is available.':'sending never starts a print or changes profiles.',
    }
    for a,b in replacements.items():
      if a not in extension: raise ValueError('Accepted panel anchor changed: '+a)
      extension=extension.replace(a,b)
    validator='''\ndef validate_print_temperature_file(value):
    if not isinstance(value, dict) or value.get("bands") != [225,220,215]:
        raise CommunicationProtocolError("Exactly three descending 225/220/215 bands are required.")
    TemperatureCommunicationState._validate_file_descriptor(value)
    return {k:value[k] for k in ("name","size","sha256","bands")}
\n'''
    return protocol+'\n'+validator+extension

def generate():
    spec=importlib.util.spec_from_file_location('accepted_communication_for_print',ROOT/'scripts/temperature-communication-companion.py')
    base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    source=base.generate()
    start=source.index('# BEGIN GENERATED TEMPERATURE COMMUNICATION')
    end=source.index('# END GENERATED TEMPERATURE COMMUNICATION',start)+len('# END GENERATED TEMPERATURE COMMUNICATION')
    source=source[:start]+generated_parts()+source[end:]
    for old,new in [('# version = "0.5.0"','# version = "0.6.1"'),('EXPORTER_VERSION = "0.5.0"','EXPORTER_VERSION = "0.6.1"')]:
      if source.count(old)!=1: raise ValueError('Version anchor changed')
      source=source.replace(old,new)
    return source

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('output',type=Path); a=p.parse_args()
    if a.output.exists(): raise ValueError('Refusing to replace an existing companion')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    code=generate(); a.output.write_text(code)
    print(hashlib.sha256(code.encode()).hexdigest())
