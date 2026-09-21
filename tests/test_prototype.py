from io import BytesIO
import unittest
from dataclasses import asdict
import json
import pandas as pd
from src.study_runtime import ROOT,configuration
from src.prototype_service import read_input,dispatch,parameters_from_json

class PrototypeTests(unittest.TestCase):
    def test_input_rejection_and_parameter_roundtrip(self):
        for raw in [b'',b'hour,load,wind,solar\n',b'hour,load,wind,solar\n0,-1,0,0\n']:
            with self.assertRaises(ValueError):read_input(BytesIO(raw))
        _,s,t,e=configuration();s2,t2,e2=parameters_from_json(json.dumps(dict(storage=s,thermal=t,economics=asdict(e))))
        self.assertEqual(s,s2);self.assertEqual(t,t2);self.assertEqual(e,e2)
    def test_rule_service_matches_baseline(self):
        _,s,t,e=configuration();q,_=dispatch('规则',read_input(ROOT/'data/input_24h.csv'),s,t,e)
        pd.testing.assert_frame_equal(q,pd.read_csv(ROOT/'results/capacity_sensitivity/E40_P20_hourly.csv'),check_dtype=False,check_exact=False,atol=1e-6,rtol=0)
        with self.assertRaises(ValueError):dispatch('规则',read_input(ROOT/'data/input_24h.csv'),dict(s,energy_capacity_MWh=-1),t,e)
