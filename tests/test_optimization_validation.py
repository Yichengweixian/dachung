"""Independent U07 tests. Solver imported only for the hand-derived oracle."""
import json
import unittest
import numpy as np
import pandas as pd
from scripts.audit_u07 import ROOT, RUN, UNIT, sha, check

class IndependentAuditTests(unittest.TestCase):
    def test_frozen_evidence(self):
        frozen=json.loads((UNIT/'freeze.json').read_text(encoding='utf-8'))
        for p,h in frozen['sha256'].items():
            self.assertEqual(sha(ROOT/p),h,p)

    def test_seven_saved_cases_and_summaries(self):
        m=json.loads((RUN/'run_manifest.json').read_text(encoding='utf-8'))
        original=pd.read_csv(ROOT/'data/input_24h.csv')
        cost=m['frozen']['config']['economics.json']['parameters']
        for name,item in m['cases'].items():
            with self.subTest(case=name):
                q=pd.read_csv(RUN/(name+'_hourly.csv'))
                d=original.copy()
                if name=='half_hour':
                    d=d.loc[d.index.repeat(2)].reset_index(drop=True); d['hour']=np.arange(len(d))*.5
                if name=='zero_renewables':
                    d[['wind','solar']]=0.
                np.testing.assert_allclose(q[['hour','load','wind_available','solar_available']],d[['hour','load','wind','solar']],rtol=0,atol=1e-12)
                check(q,item['storage'],item['thermal'],item['dt'],item['terminal'])
                dt=item['dt']; summary=item['summary']
                for key,x in [('curtailment_MWh',q.wind_curt+q.solar_curt),('thermal_generation_MWh',q.thermal),
                              ('unserved_MWh',q.unserved),('charge_MWh',q.charge),('discharge_MWh',q.discharge)]:
                    self.assertLess(abs(summary[key]-x.sum()*dt),1e-6)
                available=(q.wind_available+q.solar_available).sum()
                if available:
                    self.assertLess(abs(summary['renewable_utilization_pct']-100*(q.wind_used+q.solar_used).sum()/available),1e-6)
                else:
                    self.assertIsNone(summary['renewable_utilization_pct'])
                total=dt*(q.thermal.sum()*cost['thermal_cost_CNY_per_MWh']+(q.wind_curt+q.solar_curt).sum()*cost['curtailment_penalty_CNY_per_MWh']+
                    q.unserved.sum()*cost['load_shedding_penalty_CNY_per_MWh']+q.discharge.sum()*cost['storage_variable_om_CNY_per_MWh_discharged'])
                self.assertLess(abs(total-summary['operating_cost_CNY']),1e-6)
        stored=pd.read_csv(RUN/'summary.csv').iloc[0]
        for k,v in m['cases']['dispatch']['summary'].items():
            self.assertLess(abs(stored[k]-v),1e-6)

    def test_hand_derived_four_hour_oracle(self):
        from src.optimization_model import solve_dispatch
        # Unique thermal optimum [30,50,80,50]: hour 1 must pre-ramp for hour 2.
        # Wind accepted [20,0,0,0], curtailed [50,30,0,0]; cost 210*350+80*200.
        d=pd.DataFrame({'hour':[0.,1.,2.,3.],'load':[50.,50.,80.,50.],'wind':[70.,30.,0.,0.],'solar':[0.,0.,0.,0.]})
        s=json.loads((ROOT/'config/storage.json').read_text(encoding='utf-8')); s.update(energy_capacity_MWh=0,power_capacity_MW=0)
        c=json.loads((ROOT/'config/economics.json').read_text(encoding='utf-8'))['parameters']
        th={'min':30.,'max':120.,'ramp':30.}
        q,info=solve_dispatch(d,s,th,c)
        for col,expected in {'thermal':[30,50,80,50],'wind_used':[20,0,0,0],'wind_curt':[50,30,0,0],
                              'solar_used':[0]*4,'solar_curt':[0]*4,'charge':[0]*4,'discharge':[0]*4,
                              'unserved':[0]*4,'energy_start_MWh':[0]*4,'energy_MWh':[0]*4}.items():
            np.testing.assert_allclose(q[col],expected,rtol=0,atol=1e-6)
        self.assertAlmostEqual(info['objective_CNY'],89500,places=6)
        check(q,s,th,1.)

    def test_independent_checker_rejects_tampering(self):
        m=json.loads((RUN/'run_manifest.json').read_text(encoding='utf-8'))['cases']['dispatch']
        q=pd.read_csv(RUN/'dispatch_hourly.csv')
        for column in ['thermal','charge','energy_MWh','wind_curt']:
            bad=q.copy(); bad.loc[0,column]+=0.01
            with self.assertRaises(AssertionError):
                check(bad,m['storage'],m['thermal'],m['dt'])
