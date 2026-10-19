from pathlib import Path
import tempfile
import unittest

from integration.v1_contract import ContractError
from integration.v1_generation import GenerationBlocked
from integration.v1_routing import capabilities, generate, routes
from test_v1_runtime import context, request


class RoutingTests(unittest.TestCase):
    def test_no_build_never_advertises_native_generation(self):
        result=capabilities({})
        self.assertEqual(len(result),5)
        self.assertTrue(all(set(row)=={'id','available','reason'} for row in result))
        self.assertTrue(all(row['available'] is False for row in result))
        self.assertEqual(routes({})['pressure_advance_pattern'],'native-engine')
        self.assertEqual(routes({})['flow_ratio_yolo'],'stock-cli')

    def test_unknown_route_is_rejected_without_fallback(self):
        for config in ({'routes':{'temperature':'python-generator'}},{'routes':{'unknown':'stock-cli'}},{'routes':[]}):
            with self.assertRaises(ContractError): routes(config)

    def test_missing_native_receipt_blocks_before_any_output(self):
        from integration.v1_contract import digest
        original=context()
        req=request(dict(request_id='2'*32,origin_id=original['origin_id'],context_sha256=digest(original),created_at=100,expires_at=3700))
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'must-not-exist'
            with self.assertRaises(GenerationBlocked):
                generate(req,original,output,dict(routes=dict(temperature='native-engine'),native_engine=dict(now=100)))
            self.assertFalse(output.exists())
