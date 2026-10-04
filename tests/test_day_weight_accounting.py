import ast
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.cost_unserved_attribution import METRICS
from src.day_weight_accounting import hypothesis, paths, path_cost_check


class DayWeightAccountingTests(unittest.TestCase):
    def inputs(self):
        counts = np.array([8]*29+[7]*19)
        old = pd.DataFrame(np.ones((48,len(METRICS))),columns=METRICS)
        new = old.copy()
        new.loc[0,:] = 2.
        w0 = counts.astype(float)
        w1 = w0.copy()
        w1[0] += 1
        w1[1] -= 1
        return old,new,counts,w0,w1

    def test_hand_calculated_two_paths_and_interaction(self):
        annual,clusters,residual = paths(*self.inputs())
        self.assertEqual((len(annual),len(clusters),residual),(14,672,0.))
        row = annual.iloc[0]
        self.assertEqual([row[k] for k in ("Y00","Y10","Y01","Y11")],[365.,373.,365.,374.])
        self.assertEqual([row[k] for k in ("delta","day_first","weight_after_day","weight_first","day_after_weight","interaction","day_average","weight_average")],[9.,8.,1.,0.,9.,1.,8.5,.5])

    def test_reverse_endpoints_negates_average_and_delta(self):
        old,new,c,w0,w1 = self.inputs()
        forward,_,_ = paths(old,new,c,w0,w1)
        reverse,_,_ = paths(new,old,c,w1,w0)
        for key in ("delta","day_average","weight_average"):
            np.testing.assert_array_equal(forward[key],-reverse[key])
        np.testing.assert_array_equal(forward.interaction,reverse.interaction)

    def test_identical_days_or_weights_remove_interaction(self):
        old,new,c,w0,w1 = self.inputs()
        for args in ((old,old,c,w0,w1),(old,new,c,w0,w0)):
            annual,_,_ = paths(*args)
            self.assertTrue((annual.interaction == 0).all())

    def test_invalid_dimensions_finiteness_and_bounds(self):
        for failure in ("missing","nan","weights","counts"):
            args = list(self.inputs())
            if failure == "missing": args[0] = args[0].iloc[:-1]
            elif failure == "nan": args[1].iloc[0,0] = np.nan
            elif failure == "weights": args[4] *= 2
            else: args[2][0] += 1
            with self.assertRaises(ValueError): paths(*args)

    def test_fee_path_identity_and_bad_fee(self):
        table = pd.DataFrame([dict(metric=k,Y00=2.,Y10=3.,Y01=4.,Y11=5.,delta=3.,day_first=1.,weight_after_day=2.,weight_first=2.,day_after_weight=1.,interaction=0.,day_average=1.,weight_average=2.) for k in METRICS])
        numeric = list(table.columns[1:])
        table.loc[table.metric == "total_cost_CNY",numeric] *= 6.
        table.loc[table.metric == "unserved_MWh",numeric] /= 10000.
        self.assertLess(path_cost_check(table,10000.),1e-6)
        table.loc[table.metric == "load_shedding_cost_CNY","delta"] += 1
        with self.assertRaises(ValueError): path_cost_check(table,10000.)

    def hypothesis_table(self):
        return pd.DataFrame([dict(day_set=side,seed=seed,metric=k,replacement=-1.,total=3.)
                             for side in ("old","new") for seed in (42,7,2026) for k in ("total_cost_CNY","unserved_MWh")])

    def test_retrospective_hypothesis_complete_refuted_and_tie(self):
        table = self.hypothesis_table()
        self.assertEqual(hypothesis(table)[0],"supported")
        mask = (table.day_set == "new") & (table.seed == 42) & (table.metric == "unserved_MWh")
        table.loc[mask,"total"] = .1
        self.assertEqual(hypothesis(table)[0],"refuted")
        table.loc[mask,"total"] = -1.
        self.assertEqual(hypothesis(table)[0],"inconclusive")
        with self.assertRaises(ValueError): hypothesis(table.iloc[:-1])
        table.loc[mask,"total"] = np.inf
        with self.assertRaises(ValueError): hypothesis(table)

    def test_runner_and_audit_have_no_solve_calls(self):
        import run_day_weight_accounting as runner
        import scripts.audit_day_weight_accounting as auditor
        for module in (runner,auditor):
            calls = [n for n in ast.walk(ast.parse(inspect.getsource(module))) if isinstance(n,ast.Call)]
            self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr in ("case","solve","solve_dispatch") for n in calls))

    def test_analysis_failure_keeps_zero_budget_and_evidence(self):
        import run_day_weight_accounting as runner
        with tempfile.TemporaryDirectory(prefix="u11r13-test-") as directory:
            class FailedRun:
                out = Path(directory)
                manifest = dict(cases={})
            with patch.object(runner,"StudyRun",return_value=FailedRun()), patch.object(runner,"configuration",side_effect=ValueError("input drift")),patch("sys.argv",["runner"]):
                with self.assertRaises(ValueError): runner.main()
            m = json.loads((Path(directory)/"run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual((m["status"],m["verdict"],m["cases"],m["new_solver_calls"]),("blocked","invalid",{},0))
            self.assertTrue((Path(directory)/"failure.json").is_file())


if __name__ == "__main__":
    unittest.main()
