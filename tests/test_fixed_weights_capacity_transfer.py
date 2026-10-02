import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.fixed_weights_capacity_transfer import decision, fixed_days, repeat_difference, source_day


class CapacityTransferTests(unittest.TestCase):
    def table(self):
        return pd.DataFrame([dict(capacity_scenario=scenario, seed=seed,
                                 worst_error_pp=1., max_input_relative_error=.02)
                             for scenario in ("E0_P0", "E80_P20") for seed in (42, 7, 2026)])

    def fixture(self):
        counts = np.array([8]*29+[7]*19)
        labels = pd.DataFrame(dict(day=np.arange(365), cluster=np.repeat(np.arange(48), counts)))
        days = np.r_[0, counts.cumsum()[:-1]]
        reps = pd.DataFrame(dict(cluster=np.arange(48), day=days, days=counts,
                                 effective_days=counts.astype(float), repeat_days=counts.astype(float),
                                 effective_probability=counts/365.,
                                 date_UTC=(pd.Timestamp("2023-01-01")+pd.to_timedelta(days, unit="D")).strftime("%Y-%m-%d")))
        data = pd.DataFrame(dict(hour=np.arange(8760), load=np.full(8760, 100.),
                                 wind=np.full(8760, 20.), solar=np.zeros(8760)))
        return data, reps, labels

    def test_exact_threshold_and_single_failure(self):
        table = self.table()
        self.assertEqual(decision(table)[0], "supported")
        table.loc[0, "worst_error_pp"] = 1.+1e-12
        self.assertEqual(decision(table)[0], "inconclusive")
        table.loc[0, "worst_error_pp"] = 1.
        table.loc[5, "max_input_relative_error"] = .02+1e-12
        self.assertEqual(decision(table)[0], "inconclusive")

    def test_incomplete_duplicate_and_nonfinite_matrix(self):
        with self.assertRaises(ValueError):
            decision(self.table().iloc[:-1])
        table = self.table()
        table.loc[5, "seed"] = 7
        with self.assertRaises(ValueError):
            decision(table)
        table = self.table()
        table.loc[0, "worst_error_pp"] = np.nan
        with self.assertRaises(ValueError):
            decision(table)

    def test_fixed_membership_weights_and_hour_reset(self):
        data, reps, labels = self.fixture()
        days, weights, residual = fixed_days(data, reps, labels)
        self.assertEqual(len(days), 48)
        self.assertEqual(weights.sum(), 365)
        self.assertEqual(residual, 0.)
        np.testing.assert_array_equal(days[-1].hour, np.arange(24))
        self.assertEqual(data.hour.iloc[-1], 8759)

    def test_tampered_membership_counts_or_repeat_rejected(self):
        for column, value in (("day", 9), ("days", 7), ("repeat_days", 9.),
                              ("effective_days", np.inf), ("effective_probability", np.nan),
                              ("day", .5), ("date_UTC", "2024-01-01")):
            data, reps, labels = self.fixture()
            if column == "day" and value == .5:
                reps[column] = reps[column].astype(float)
            reps.loc[0, column] = value
            with self.assertRaises(ValueError, msg=column):
                fixed_days(data, reps, labels)

    def test_day_boundary_and_repeat_numeric_guard(self):
        data, _, _ = self.fixture()
        for day in (-1, 365, .5):
            with self.assertRaises(ValueError):
                source_day(data, day)
        first = dict(scenario="main", total_cost_CNY=1., storage_utilization_pct=np.nan)
        self.assertEqual(repeat_difference(first, dict(first, scenario="repeat")), 0.)
        with self.assertRaises(ValueError):
            repeat_difference(first, dict(first, total_cost_CNY=1.000002))
        with self.assertRaises(ValueError):
            repeat_difference(first, dict(first, total_cost_CNY=np.nan))

    def test_first_solver_failure_stops_and_preserves_log(self):
        import run_fixed_weights_capacity_transfer as runner
        from src.optimization_model import DispatchSolveError
        with tempfile.TemporaryDirectory(prefix="u11r10-test-") as directory:
            class FailedRun:
                out = Path(directory)
                manifest = dict(cases={}, packages={})

                def case(self, *args):
                    raise DispatchSolveError("Infeasible", "retained failure log")

            with patch.object(runner, "StudyRun", return_value=FailedRun()), patch("sys.argv", ["runner"]):
                with self.assertRaises(DispatchSolveError):
                    runner.main()
            manifest = json.loads((Path(directory)/"run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["attempted_milp_calls"], 1)
            self.assertEqual(manifest["verdict"], "invalid")
            self.assertEqual(manifest["status"], "blocked")
            self.assertEqual(manifest["cases"], {})
            self.assertEqual((Path(directory)/"failed_cbc.log").read_text(encoding="utf-8"), "retained failure log")

    def test_independent_audit_matches_existing_saved_dispatch(self):
        from scripts.audit_fixed_weights_capacity_transfer import ROOT, saved_metrics, read_csv, check_close
        predecessor = ROOT/"results/annual/U11R08B-v01"
        manifest = json.loads((predecessor/"run_manifest.json").read_text(encoding="utf-8"))
        cfg = manifest["freeze"]["config"]
        reps = read_csv(predecessor/"N48_seed42_representatives.csv")
        d = int(reps[0]["day"])
        data = read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")[d*24:(d+1)*24]
        name = "N48_seed42_cluster0"
        case = manifest["cases"][name]
        totals, residual, objective = saved_metrics(predecessor/(name+"_hourly.csv"), data,
                                                   case["storage"], case["thermal"], cfg["economics.json"]["parameters"])
        summary = read_csv(predecessor/"N48_seed42_summary.csv")[0]
        for key, value in totals.items():
            self.assertLess(check_close(value, summary[key], key), 1e-6)
        self.assertLess(check_close(objective, case["objective_CNY"], "objective"), 1e-6)
        self.assertLess(residual, 1e-6)
        data[0]["wind"] = "nan"
        with self.assertRaises(ValueError):
            saved_metrics(predecessor/(name+"_hourly.csv"), data,
                          case["storage"], case["thermal"], cfg["economics.json"]["parameters"])


if __name__ == "__main__":
    unittest.main()
