import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('companion',ROOT/'scripts/companion-evidence.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class CompanionEvidenceTests(unittest.TestCase):
    def test_only_companion_html_can_change_from_qualified_runtime(self):
        source=(ROOT/'plugin/helix_calibration.py').read_text()
        self.assertEqual(c.plugin_contract(source),c.BASELINE_PLUGIN_CONTRACT)
        changed=source.replace('self.instructions = instructions','self.instructions = None')
        self.assertNotEqual(c.plugin_contract(changed),c.BASELINE_PLUGIN_CONTRACT)
        changed=source.replace('def capture_temperature_target(host):','def capture_temperature_target(other):')
        self.assertNotEqual(c.plugin_contract(changed),c.BASELINE_PLUGIN_CONTRACT)

    def test_result_layout_does_not_claim_mock_application_or_hide_live_value(self):
        from test_plugin import load_plugin
        plugin,_=load_plugin()
        html=plugin.ROUND_TRIP_PAGE
        self.assertLess(html.index('id="result-card"'),html.index('id="workflow"'))
        self.assertLess(html.index('id="workflow"'),html.index('id="technical"'))
        self.assertIn('Current effective value in Orca',html)
        self.assertIn('Effective at calibration start',html)
        self.assertIn('The companion has changed no setting or profile',html)
        self.assertIn('Other layers',html)

    def test_focused_evidence_preserves_original_capture_source_identities(self):
        baseline=json.loads((ROOT/'docs/evidence/issue-4/roundtrip/report.json').read_text())
        self.assertEqual(baseline['orca_plugin_sha256'],'fd4d37b51ee61d4260f0ff5217841cc052c1210b12c14c1e46f8f6c9d371d844')
        report=json.loads((ROOT/'docs/evidence/issue-4/roundtrip/companion/report.json').read_text())
        self.assertNotEqual(report['windows_validation']['plugin_sha256'],baseline['orca_plugin_sha256'])
        self.assertEqual(report['baseline_commit'],c.BASELINE_COMMIT)
