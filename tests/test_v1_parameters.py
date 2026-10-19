"""Focused parameter defaults, validation, and coordinator preservation checks."""
import copy
from pathlib import Path
import tempfile
import unittest

from integration import v1_contract as contract
from integration.v1_runtime import Coordinator, read_json


def context(extruder=None):
    value = dict(schema='helix-orca-v1-context/v1', origin_id='1'*32,
                 runtime=dict(version='2.5.0-dev', build='6a7763f0'),
                 nozzle_mm=.4, effective={'filament_flow_ratio': '1'})
    if extruder is not None:
        value['effective']['extruder_type'] = extruder
    for role in ('printer', 'process', 'filament'):
        value[role] = {kind: dict(name=role, config={'extruder_type': 'Bowden'})
                       for kind in ('saved', 'edited')}
    return value


class ParameterTests(unittest.TestCase):
    def test_pa_defaults_use_effective_extruder_only_and_label_unknown(self):
        for serialized, expected in (('Direct Drive', 'direct_drive'), ('Bowden', 'bowden'),
                                      (None, 'unavailable'), ('unrecognized', 'unavailable')):
            value = context(serialized)
            self.assertEqual(contract.context_extruder_type(value), expected)
            actual = contract.default_parameters(value)
            self.assertEqual(actual['pressure_advance_pattern'],
                             contract.PA_DEFAULTS.get(expected, contract.PA_DEFAULTS['direct_drive']))
            with tempfile.TemporaryDirectory() as directory:
                runtime = Coordinator(directory, None, {}, [], now=lambda: 100)
                offer = runtime.offer(value)
                self.assertEqual(offer['extruder_type'], expected)
                self.assertEqual(offer['defaults'], actual)

    def test_flow_modes_have_distinct_exact_additive_choices(self):
        self.assertEqual(contract.flow_ratio_choices('1', 1),
                         [.95, .96, .97, .98, .99, 1, 1.01, 1.02, 1.03, 1.04, 1.05])
        fine = contract.flow_ratio_choices('1', 2)
        self.assertEqual(len(fine), 16)
        self.assertEqual((fine[0], fine[-1]), (.96, 1.035))
        self.assertNotIn(1.04, fine)
        self.assertEqual(contract.validate_parameters('flow_ratio_yolo', {'pass': 2}), {'pass': 2})
        for invalid in (True, 0, 3, '2'):
            with self.assertRaises(contract.ContractError):
                contract.validate_parameters('flow_ratio_yolo', {'pass': invalid})

    def test_invalid_parameters_explain_the_correctable_field_or_range(self):
        cases = [
            ('temperature', dict(start=232, end=190, step=5, scale=True), '5°C'),
            ('temperature', dict(start=230, end=190, step=10, scale=True), 'fixed'),
            ('retraction', dict(start=0, end=2, step=0), 'Step'),
            ('max_volumetric_speed', dict(start=20, end=5, step=1), 'End'),
            ('pressure_advance_pattern', dict(start=0, end=5, step=.001), '1001'),
        ]
        for kind, values, message in cases:
            with self.subTest(kind=kind, values=values):
                with self.assertRaisesRegex(contract.ContractError, message):
                    contract.validate_parameters(kind, values)

    def test_changed_values_reach_generator_and_survive_its_real_blocker(self):
        selections = {
            'temperature': dict(start=235, end=200, step=5, scale=False),
            'flow_ratio_yolo': {'pass': 2},
            'pressure_advance_pattern': dict(start=.02, end=.12, step=.01),
            'retraction': dict(start=.2, end=2.2, step=.2),
            'max_volumetric_speed': dict(start=6, end=18, step=.75),
        }
        for kind, parameters in selections.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                observed = []
                def blocked(request, *_):
                    observed.append(copy.deepcopy(request))
                    request['parameters'].clear()  # A backend cannot rewrite the frozen request.
                    raise contract.ContractError('Exact generator fixture blocker')
                runtime = Coordinator(directory, blocked, {},
                    [dict(id=k, available=True, reason='Attempt allowed') for k in contract.CALIBRATIONS],
                    now=lambda: 100)
                offer = runtime.offer(context())
                request = {key: offer[key] for key in ('request_id', 'origin_id', 'context_sha256', 'created_at', 'expires_at')}
                request.update(schema='helix-orca-v1-request/v1', calibration=kind,
                               parameters=parameters, not_applied=True)
                result = runtime.request(request)
                self.assertEqual(observed, [request])
                self.assertEqual(runtime.state['request'], request)
                self.assertEqual(read_json(runtime.path)['request'], request)
                self.assertEqual(result['phase'], 'blocked')
                self.assertIn('Exact generator fixture blocker', result['message'])
                self.assertIsNone(runtime.state['prepared'])
