import json
from pathlib import Path
import unittest

import pandas as pd

from src.economic_model import EconomicParameters
from src.grid_search import generate_candidates, select_best, with_robustness_costs
from src.optimization_validation import validate
from scripts.audit_u07 import check


ROOT = Path(__file__).resolve().parents[1]


class GridSearchTests(unittest.TestCase):
    def setUp(self):
        self.grid = json.loads((ROOT / "config/grid_search.json").read_text(encoding="utf-8"))

    def test_frozen_grid_has_101_unique_candidates(self):
        candidates = generate_candidates(self.grid)
        self.assertEqual(len(candidates), 101)
        self.assertEqual(len(set(candidates)), 101)
        self.assertEqual(candidates[0], (0.0, 0.0))
        self.assertEqual(sum(e == 0 for e, _ in candidates), 1)
        self.assertTrue(all(p > 0 for e, p in candidates if e > 0))

    def test_reject_changed_grid(self):
        changed = dict(self.grid, energy_capacities_MWh=[0, 20, 40])
        with self.assertRaises(ValueError):
            generate_candidates(changed)

    def test_best_selection_and_ties_are_explicit(self):
        summary = pd.DataFrame([
            {"scenario": "a", "energy_capacity_MWh": 20, "power_capacity_MW": 10, "total_cost_CNY": 2},
            {"scenario": "b", "energy_capacity_MWh": 10, "power_capacity_MW": 15, "total_cost_CNY": 1},
            {"scenario": "c", "energy_capacity_MWh": 30, "power_capacity_MW": 5, "total_cost_CNY": 1},
        ])
        best, ties = select_best(summary)
        self.assertEqual(best.scenario, "b")
        self.assertEqual(set(ties.scenario), {"b", "c"})

    def test_robustness_overrides_only_named_costs(self):
        raw = json.loads((ROOT / "config/economics.json").read_text(encoding="utf-8"))["parameters"]
        base = EconomicParameters(**raw)
        changed = with_robustness_costs(base, self.grid["robustness_cost_overrides"])
        self.assertEqual(changed.storage_energy_capex_CNY_per_kWh, 1200)
        self.assertEqual(changed.storage_power_capex_CNY_per_kW, 500)
        self.assertEqual(changed.thermal_cost_CNY_per_MWh, base.thermal_cost_CNY_per_MWh)
        with self.assertRaises(ValueError):
            with_robustness_costs(base, {"unknown": 1})

    def test_saved_u09_grid_manifest_and_heatmap_source(self):
        run = ROOT / "results/grid_search/U09-20260913-01"
        summary = pd.read_csv(run / "summary.csv")
        robust = pd.read_csv(run / "robustness_summary.csv")
        manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((len(summary), summary.scenario.nunique()), (101, 101))
        self.assertEqual(set(summary.solver_status), {"Optimal"})
        self.assertEqual(set(robust.solver_status), {"Optimal"})
        self.assertEqual(len(manifest["main_statuses"]), 101)
        self.assertEqual(len(manifest["repeat_statuses"]), 101)
        self.assertEqual(len(manifest["robustness_statuses"]), 101)
        self.assertEqual(manifest["repeat_max_absolute_difference"], 0)
        self.assertEqual(manifest["verdict"], "supported")
        positive = summary[summary.energy_capacity_MWh > 0]
        for metric in ["total_cost_CNY", "renewable_utilization_pct"]:
            matrix = positive.pivot(index="power_capacity_MW", columns="energy_capacity_MWh", values=metric)
            self.assertEqual(matrix.shape, (10, 10))
            self.assertFalse(matrix.isna().any().any())

    def test_saved_best_dispatch_passes_both_checkers(self):
        run = ROOT / "results/grid_search/U09-20260913-01"
        manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
        dispatch = pd.read_csv(run / "best_dispatch.csv")
        frozen = manifest["frozen"]["config"]
        storage = dict(frozen["storage.json"],
                       energy_capacity_MWh=manifest["best"]["energy_capacity_MWh"],
                       power_capacity_MW=manifest["best"]["power_capacity_MW"])
        thermal = {"min": frozen["optimization.json"]["thermal_min_MW"],
                   "max": frozen["no_storage.json"]["thermal_max_MW"],
                   "ramp": frozen["optimization.json"]["thermal_ramp_MW_per_h"]}
        data = pd.read_csv(ROOT / "data/input_24h.csv")
        dt = frozen["simulation.json"]["time_step_hours"]
        validate(dispatch, data, storage, thermal, dt, True)
        self.assertTrue(check(dispatch, storage, thermal, dt, True))


if __name__ == "__main__":
    unittest.main()
