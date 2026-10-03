import ast
from dataclasses import asdict
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.cost_unserved_attribution import COSTS, METRICS, close, cost_check, decompose, effect, hypothesis, top_contributors


class AttributionTests(unittest.TestCase):
    def fixture(self):
        counts = np.array([8]*29+[7]*19)
        labels = np.repeat(np.arange(48), counts)
        full = pd.DataFrame(np.ones((365,len(METRICS))), columns=METRICS)
        reps = pd.DataFrame(np.ones((48,len(METRICS))), columns=METRICS)
        reps.loc[0,:] = 2.
        weights = counts.astype(float)
        weights[0] -= 1
        weights[1] += 1
        return full,reps,labels,counts,weights

    def fees(self):
        return pd.DataFrame([dict(capacity_scenario=s,seed=seed,metric=k,total=10. if k == "load_shedding_cost_CNY" else 1.)
                             for s in ("E0_P0","E40_P20","E80_P20") for seed in (42,7,2026) for k in COSTS])

    def test_hand_decomposition_negative_adjustment_and_cancellation(self):
        annual,clusters,residual = decompose(*self.fixture())
        self.assertEqual(len(annual),14)
        self.assertEqual(len(clusters),672)
        self.assertEqual(residual,0.)
        row = annual.iloc[0]
        self.assertEqual((row.full,row.control,row.calibrated,row.replacement,row.adjustment,row.total),(365.,373.,372.,8.,-1.,7.))
        self.assertEqual(row.weight_effect,"reduced")
        self.assertEqual(row.cancellation_fraction,0.)
        data=list(self.fixture())
        data[1].loc[1,:]=0.
        annual,_,_=decompose(*data)
        row=annual.iloc[0]
        self.assertGreater(row.cancellation_fraction,0.)
        self.assertLess(row.cancellation_fraction,1.)

    def test_nonfinite_missing_members_and_invalid_weights_fail(self):
        for index,mutation in ((0,lambda q:q.assign(unserved_MWh=np.nan)),
                               (2,lambda q:q[:-1]),(3,lambda q:q+1),(4,lambda q:q*2)):
            args=list(self.fixture())
            args[index]=mutation(args[index])
            with self.assertRaises(ValueError): decompose(*args)
        with self.assertRaises(ValueError): close(np.nan,0.,"nonfinite")
        with self.assertRaises(ValueError): close(0.,2e-6,"strict arithmetic guard")

    def test_six_fee_and_shortage_coefficient_identity(self):
        rows=[]
        for metric in METRICS:
            values=dict(full=2.,control=3.,calibrated=4.,replacement=1.,adjustment=1.,total=2.)
            if metric=="total_cost_CNY": values={k:6*v for k,v in values.items()}
            if metric=="unserved_MWh": values={k:v/10000 for k,v in values.items()}
            rows.append(dict(metric=metric,**values))
        annual=pd.DataFrame(rows)
        self.assertLess(cost_check(annual,10000),1e-6)
        annual.loc[annual.metric=="total_cost_CNY","total"]+=1.
        with self.assertRaises(ValueError): cost_check(annual,10000)

    def test_hypothesis_dominant_refuted_tie_and_complete_matrix(self):
        fees=self.fees()
        self.assertEqual(hypothesis(fees)[0],"supported")
        mask=(fees.capacity_scenario=="E80_P20") & (fees.seed==7) & (fees.metric=="thermal_cost_CNY")
        fees.loc[mask,"total"]=-11.
        self.assertEqual(hypothesis(fees)[0],"refuted")
        fees.loc[mask,"total"]=-10.
        self.assertEqual(hypothesis(fees)[0],"inconclusive")
        with self.assertRaises(ValueError): hypothesis(fees.iloc[:-1])
        fees.loc[0,"total"]=np.inf
        with self.assertRaises(ValueError): hypothesis(fees)

    def test_weight_effect_and_top_tie_break(self):
        self.assertEqual(effect(-2.,1.),"reduced")
        self.assertEqual(effect(1.,-2.),"increased")
        self.assertEqual(effect(1.,1.+1e-7),"unchanged")
        table=pd.DataFrame([dict(capacity_scenario="E0_P0",seed=7,metric="unserved_MWh",cluster=k,total=(-1)**k)
                            for k in reversed(range(8))])
        self.assertEqual(list(top_contributors(table).cluster),list(range(5)))

    def test_saved_metrics_two_implementations_match_no_solve(self):
        import run_cost_unserved_attribution as runner
        from scripts.audit_cost_unserved_attribution import detailed_metrics, read_csv
        from src.fixed_weights_capacity_transfer import source_day
        from src.study_runtime import ROOT, configuration
        folder=ROOT/"results/annual/U11R10-v01"
        manifest=json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
        reps=read_csv(ROOT/"results/annual/U11R08B-v01/N48_seed7_representatives.csv")
        day=int(reps[0]["day"])
        cfg,base,thermal,economics=configuration()
        storage=dict(base,energy_capacity_MWh=80.,power_capacity_MW=20.)
        name="E80_P20_N48_seed7_cluster0"
        path=folder/(name+"_hourly.csv")
        data=pd.read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv",float_precision="round_trip")
        with patch("src.study_runtime.solve_dispatch",side_effect=AssertionError("no new optimization")):
            first,_=runner.rebuild(path,source_day(data,day),storage,thermal,economics,manifest["cases"][name])
            second,_=detailed_metrics(path,read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")[day*24:(day+1)*24],storage,thermal,asdict(economics),manifest["cases"][name])
        for key in METRICS: self.assertLess(close(first[key],second[key],key),1e-6)
        calls=[n for n in ast.walk(ast.parse(inspect.getsource(runner))) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in ("case","solve") for n in calls))

    def test_first_analysis_error_preserved_and_no_cases(self):
        import run_cost_unserved_attribution as runner
        with tempfile.TemporaryDirectory(prefix="u11r11-test-") as directory:
            class FailedRun:
                out=Path(directory)
                manifest=dict(cases={})
            with patch.object(runner,"StudyRun",return_value=FailedRun()), patch.object(runner,"configuration",side_effect=ValueError("input drift")),patch("sys.argv",["runner"]):
                with self.assertRaises(ValueError): runner.main()
            manifest=json.loads((Path(directory)/"run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"],"blocked")
            self.assertEqual(manifest["verdict"],"invalid")
            self.assertEqual(manifest["cases"],{})
            self.assertEqual(manifest["new_solver_calls"],0)
            self.assertTrue((Path(directory)/"failure.json").is_file())


if __name__=="__main__":
    unittest.main()
