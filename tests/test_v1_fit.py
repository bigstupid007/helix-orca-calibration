"""Source-bound printer-neutral beta.12 fit checks; no host is contacted."""
import unittest

from integration.v1_contract import ContractError
from integration.v1_fit import (analysis_record, authorize_findings, check_fit,
    fit_file, machine_limits, require_machine_limits, validate_helix_status,
    warning_binding)
from integration.v1_jobs import IDENTITY_V1, IDENTITY_V2, physical_identity


class PrinterNeutralFitTests(unittest.TestCase):
    def test_voron_corexy_limits_and_ad5x_direct_file_facts_are_generic(self):
        settings = {
            'printer': {'kinematics': 'corexy'},
            'stepper_x': {'position_min': 0., 'position_max': 300.},
            'stepper_y': {'position_min': 0., 'position_max': 300.},
            'stepper_z': {'position_min': -5., 'position_max': 290.},
            'extruder': {'max_temp': 280., 'nozzle_diameter': .4},
            'heater_bed': {'max_temp': 110.},
        }
        machine = require_machine_limits(machine_limits(settings))
        # Facts describe the resulting direct-M190/M109/move AD5X-shaped stream;
        # no macro name or ABI participates in this checker.
        facts = dict(print={'min': [50., 50., .25], 'max': [200., 220., 12.]},
            travel={'min': [50., 50., .25], 'max': [200., 220., 12.]},
            max_hotend_temp=220., max_bed_temp=60., tools=[0],
            nozzle_diameters=[.4], printer_model='Flashforge AD5X')
        findings = check_fit(machine, facts)
        self.assertEqual([item['kind'] for item in findings], [])
        self.assertEqual(authorize_findings(findings), [])

    def test_cartesian_delta_dual_carriage_temperature_and_warning_rules(self):
        cartesian = machine_limits({'printer': {'kinematics': 'cartesian'},
            'stepper_x': {'position_max': 220.}, 'stepper_y': {'position_max': 220.},
            'stepper_z': {'position_max': 220.},
            'dual_carriage': {'axis': 'x', 'position_min': -10., 'position_max': 230.},
            'extruder': {'max_temp': 260., 'nozzle_diameter': .4},
            'heater_bed': {'max_temp': 100.}})
        self.assertEqual(cartesian['axis_min'][0], -10.)
        self.assertEqual(cartesian['axis_max'][0], 230.)
        delta = require_machine_limits(machine_limits({'printer': {'kinematics': 'delta', 'print_radius': 100.},
            'stepper_a': {'position_endstop': 250.}, 'stepper_b': {'position_endstop': 249.},
            'stepper_c': {'position_endstop': 251.},
            'extruder': {'max_temp': 250., 'nozzle_diameter': .4}}))
        facts = dict(print=None, travel={'min': [-101., -2., 0.], 'max': [2., 2., 12.]},
            max_hotend_temp=251., max_bed_temp=None, tools=[0],
            nozzle_diameters=[.6], printer_model=None)
        findings = check_fit(delta, facts)
        self.assertEqual([(item['kind'], item['severity']) for item in findings],
            [('out_of_bounds', 'block'), ('temp_over_max', 'block'), ('nozzle_mismatch', 'warn')])
        with self.assertRaises(ContractError): authorize_findings(findings)

    def test_analysis_is_current_exact_file_or_closed(self):
        record = dict(schema=1, filename='owned.gcode', file_size=123, file_mtime=4.5,
            bounds=dict(print=None, travel=dict(min=[0.,0.,0.], max=[1.,1.,1.]),
                        max_hotend_temp=220., max_bed_temp=60.),
            header=dict(nozzle_diameters=[.4], printer_model='Fixture'), tools=[dict(tool=0)])
        reply = dict(filename='owned.gcode', status='ready', analysis=record)
        self.assertEqual(fit_file(analysis_record(reply, 'owned.gcode', {'size':123, 'modified':4.5}))['tools'], [0])
        for changed in (dict(reply, status='pending'),
                        dict(filename='other.gcode', status='ready', analysis=record),
                        dict(filename='owned.gcode', status='ready', analysis=dict(record, filename='other.gcode')),
                        dict(filename='owned.gcode', status='ready', analysis=dict(record, file_size=124)),
                        dict(filename='owned.gcode', status='ready', analysis=dict(record, file_mtime=5.))):
            with self.assertRaises(ContractError):
                analysis_record(changed, 'owned.gcode', {'size':123, 'modified':4.5})

    def test_warning_acknowledgement_is_exact_job_bound_and_blocks_never_pass(self):
        warnings = [dict(kind='nozzle_mismatch', severity='warn',
            detail=dict(tool=0, file=.6, printer=.4))]
        binding = warning_binding(warnings, target_id='voron-24', request_id='1'*32,
            prepared_sha256='2'*64, file_sha256='3'*64)
        acknowledgement = dict(binding, schema='helix-orca-v1-fit-warning-ack/v1',
            action='acknowledge-fit-warnings')
        with self.assertRaises(ContractError):
            authorize_findings(warnings, binding=binding)
        with self.assertRaises(ContractError):
            authorize_findings(warnings, dict(acknowledgement, file_sha256='4'*64), binding=binding)
        self.assertEqual(authorize_findings(warnings, acknowledgement, binding=binding), warnings)
        blocked = warnings + [dict(kind='temp_over_max', severity='block', detail={})]
        blocked_binding = warning_binding(blocked, target_id='voron-24', request_id='1'*32,
            prepared_sha256='2'*64, file_sha256='3'*64)
        with self.assertRaises(ContractError):
            authorize_findings(blocked,
                dict(blocked_binding, schema='helix-orca-v1-fit-warning-ack/v1',
                     action='acknowledge-fit-warnings'), binding=blocked_binding)

    def test_helixprint_source_contract_is_pinned(self):
        qualification = {'helixprint_version':'1.4.0', 'file_analysis_schema':1}
        status = dict(enabled=True, version='1.4.0', api=2,
            features={'file_analysis':dict(version=1, available=True, enabled=True, reason=None)})
        validate_helix_status(status, qualification)
        for changed in (dict(status, version='1.3.0'), dict(status, api=1),
                        dict(status, features={'file_analysis':dict(version=1, available=False, enabled=False, reason='missing')})):
            with self.assertRaises(ContractError): validate_helix_status(changed, qualification)

    def test_multi_mcu_identity_v2_preserves_distinct_historical_v1(self):
        config = {'mcu': {'serial':'main'}, 'mcu toolhead': {'canbus_uuid':'tool'}}
        system = {'network': {'eth0': {'mac_address':'bb'}, 'wlan0': {'mac_address':'aa'}}}
        historical = physical_identity(config, system, IDENTITY_V1)
        current = physical_identity(config, system, IDENTITY_V2)
        self.assertNotEqual(historical, current)
        self.assertEqual(current, physical_identity(dict(reversed(list(config.items()))), system, IDENTITY_V2))
        with self.assertRaises(ContractError): physical_identity(config, system, 'invented/v3')


if __name__ == '__main__':
    unittest.main()
