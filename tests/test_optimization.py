import json
from pathlib import Path
import unittest
import pandas as pd
from src.optimization_model import solve_dispatch
from src.optimization_validation import validate, summarize

ROOT = Path(__file__).resolve().parent.parent

class OptimizationTests(unittest.TestCase):
    def setUp(self):
        self.s = json.loads((ROOT/'config/storage.json').read_text(encoding='utf-8'))
        self.c = json.loads((ROOT/'config/economics.json').read_text(encoding='utf-8'))['parameters']
        self.th = {'min':30.,'max':120.,'ramp':30.}

    def test_hand_calculated_zero_storage(self):
        d = pd.DataFrame({'hour':[0.,1.], 'load':[50.,60.], 'wind':[10.,10.], 'solar':[0.,0.]})
        s = dict(self.s,energy_capacity_MWh=0,power_capacity_MW=0)
        q, info = solve_dispatch(d,s,self.th,self.c)
        validate(q,d,s,self.th,1.)
        self.assertAlmostEqual(info['objective_CNY'],90*350,places=6)
        self.assertAlmostEqual(q.thermal.sum(),90,places=8)
        self.assertTrue(q.soc.isna().all())

    def test_zero_renewable_precision_regression(self):
        d = pd.read_csv(ROOT/'data/input_24h.csv'); d[['wind','solar']] = 0.
        q, info = solve_dispatch(d,self.s,self.th,self.c)
        checks = validate(q,d,self.s,self.th,1.)
        self.assertLess(max(checks.values()),1e-6)
        self.assertGreater(info['precision_evidence']['text_max_rounding'],1e-6)
        self.assertAlmostEqual(summarize(q,self.c,1.)['operating_cost_CNY'], info['precision_evidence']['binary_objective'],places=6)
        q.loc[0,'thermal'] += 0.001
        with self.assertRaises(ValueError):
            validate(q,d,self.s,self.th,1.)

    def test_infeasible_is_not_success(self):
        d = pd.DataFrame({'hour':[0.], 'load':[0.], 'wind':[0.], 'solar':[0.]})
        s = dict(self.s,energy_capacity_MWh=0,power_capacity_MW=0)
        with self.assertRaises(RuntimeError):
            solve_dispatch(d,s,self.th,self.c)
