import unittest
import numpy as np
import pandas as pd
from src.annual_clustering import annual_metrics

class AnnualTests(unittest.TestCase):
    def test_energy_first_not_mean_of_rates(self):
        rows=[]
        for available,used in [(10,10),(100,0)]:
            rows.append(dict(renewable_available_MWh=available,renewable_used_MWh=used,curtailment_MWh=available-used,total_load_MWh=100,
                             thermal_generation_MWh=0,unserved_MWh=0,total_cost_CNY=1))
        m=annual_metrics(rows,[1,2]);self.assertAlmostEqual(m['renewable_utilization_pct'],100*10/210)
        self.assertEqual(m['total_cost_CNY'],3)
        with self.assertRaises(ValueError):annual_metrics(rows,[1,-1])
