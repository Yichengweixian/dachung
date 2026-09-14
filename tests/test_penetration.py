"""Independent checks of saved U08 scenario evidence."""
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from scripts.audit_u07 import check, sha

ROOT=Path(__file__).resolve().parent.parent
UNIT=ROOT/'instructions/studies/U08-penetration-matrix'
OUT=ROOT/'results/penetration/U08-20260913-01'

class PenetrationTests(unittest.TestCase):
    def test_frozen_scenarios_and_outputs(self):
        frozen=json.loads((UNIT/'freeze.json').read_text(encoding='utf-8'))
        for p,h in frozen['sha256'].items(): self.assertEqual(sha(ROOT/p),h,p)
        scenarios=pd.read_csv(ROOT/'data/scenarios/penetration_scenarios.csv')
        self.assertEqual(len(scenarios),12); self.assertEqual(scenarios.scenario.nunique(),12)
        np.testing.assert_allclose(scenarios.power_capacity_MW,scenarios.energy_capacity_MWh*.5,rtol=0,atol=0)
        self.assertEqual(set(scenarios.wind_factor),{.8,1.,1.2,1.4})
        self.assertTrue(np.array_equal(scenarios.wind_factor,scenarios.solar_factor))
        summary=pd.read_csv(OUT/'matrix_summary.csv'); self.assertEqual(set(summary.scenario),set(scenarios.scenario))
        manifest=json.loads((OUT/'run_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['verdict'],'supported')
        for row in scenarios.itertuples(index=False):
            q=pd.read_csv(OUT/f'{row.scenario}_hourly.csv')
            s=dict(frozen['config']['storage.json'],energy_capacity_MWh=row.energy_capacity_MWh,power_capacity_MW=row.power_capacity_MW)
            o=frozen['config']['optimization.json']; t={'min':o['thermal_min_MW'],'max':frozen['config']['no_storage.json']['thermal_max_MW'],'ramp':o['thermal_ramp_MW_per_h']}
            check(q,s,t,1.,True); saved=summary.query('scenario == @row.scenario').iloc[0]
            self.assertLess(abs(saved.curtailment_MWh-(q.wind_curt+q.solar_curt).sum()),1e-6)
            self.assertLess(abs(saved.unserved_MWh-q.unserved.sum()),1e-6)
            self.assertEqual(manifest['cases'][row.scenario]['solver_status'],'Optimal')
            self.assertLess(manifest['cases'][row.scenario]['max_residual'],1e-6)
            self.assertLess(max(manifest['repeat_absolute_differences'][row.scenario].values()),1e-6)

    def test_trends_marginals_and_low_resource_shortage(self):
        q=pd.read_csv(OUT/'matrix_summary.csv'); m=pd.read_csv(OUT/'marginal_changes.csv')
        for _,g in q.groupby('energy_capacity_MWh'):
            self.assertTrue((np.diff(g.sort_values('renewable_factor').curtailment_rate_pct)>=-1e-6).all())
        for f,g in q.groupby('renewable_factor'):
            self.assertTrue((np.diff(g.sort_values('energy_capacity_MWh').renewable_utilization_pct)>=-1e-6).all())
            gains=m.query('renewable_factor == @f').sort_values('from_MWh').utilization_gain_percentage_points.to_numpy()
            self.assertLessEqual(gains[1],gains[0]+1e-6)
        d=pd.read_csv(ROOT/'data/input_24h.csv'); expected=np.maximum(d.load-.8*(d.wind+d.solar)-120,0).sum()
        actual=q.query("scenario == 'R080_E000'").unserved_MWh.iloc[0]
        self.assertLess(abs(actual-expected),1e-6)
        for name in ['renewable_utilization.png','curtailment_rate.png','total_cost.png']:
            self.assertGreater((ROOT/'figures/penetration/U08-20260913-01'/name).stat().st_size,10000)
