"""Source-only recipe guards; no Windows, slicer or target calls."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[1]/'scripts/v1-windows-yolo-perfectionist.py'
spec = importlib.util.spec_from_file_location('perfectionist_recipe',PATH)
recipe = importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)


class PerfectionistRecipe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.context = dict(schema='helix-orca-v1-context/v1',origin_id='a'*32,
                            runtime=recipe.p.PINS[recipe.PIN],effective={'test':'synthetic'},nozzle_mm=.4)
        for role in ('printer','process','filament'):
            self.context[role] = {state:dict(name='fixture',config={'test':'synthetic'}) for state in ('saved','edited')}
        self.native = self.root/'native.gcode';self.native.write_text('; synthetic provenance fixture, not native proof\nG90\n')
        evidence = []
        for name in ('context.json','dialog.png','export.png'):
            path = self.root/name;path.write_text('synthetic evidence, not acceptance')
            evidence.append(dict(path=str(path),artifact=recipe.p.file_record(path)))
        request = dict(calibration='flow_ratio_yolo',parameters={'pass':2},context_sha256=recipe.c.digest(self.context))
        self.inputs = recipe.p.generation_inputs(request,self.context,recipe.PIN)
        self.manifest = dict(schema='helix-orca-v1-native-reference/v1',method='native_orca_ui',
            imported_candidate=False,inputs_sha256=recipe.c.digest(self.inputs),source_commit=recipe.PIN,
            runtime=self.context['runtime'],artifact=recipe.p.file_record(self.native),evidence=evidence)

    def test_reference_is_bound_to_exact_mode_and_retained_evidence(self):
        request,inputs = recipe.validate_reference(self.context,self.native,self.manifest,100)
        self.assertEqual(request['parameters'],{'pass':2});self.assertEqual(inputs,self.inputs)
        recommended = copy.deepcopy(self.inputs);recommended['parameters']={'pass':1}
        bad = copy.deepcopy(self.manifest);bad['inputs_sha256']=recipe.c.digest(recommended)
        with self.assertRaisesRegex(recipe.Refused,'perfectionist_reference'):
            recipe.validate_reference(self.context,self.native,bad,100)
        Path(self.manifest['evidence'][1]['path']).write_text('changed')
        with self.assertRaisesRegex(recipe.Refused,'evidence_changed'):
            recipe.validate_reference(self.context,self.native,self.manifest,100)

    def test_duplicate_evidence_cannot_replace_distinct_native_actions(self):
        bad = copy.deepcopy(self.manifest);bad['evidence'][2]=bad['evidence'][1]
        with self.assertRaisesRegex(recipe.Refused,'distinct_native'):
            recipe.validate_reference(self.context,self.native,bad,100)

    def test_wrong_platform_refuses_before_any_file_or_generator_access(self):
        with mock.patch.object(recipe.os,'name','posix'),mock.patch.object(recipe.g,'generate') as generate:
            with self.assertRaisesRegex(recipe.Refused,'windows_execution_required'):
                recipe.run(None)
            generate.assert_not_called()

    def test_digest_argument_accepts_only_exact_lowercase_hex(self):
        self.assertEqual(recipe.digest_arg('f'*64),'f'*64)
        for value in ('F'*64,'f'*63,'secret/profile/path'):
            with self.assertRaises(recipe.Refused):recipe.digest_arg(value)
