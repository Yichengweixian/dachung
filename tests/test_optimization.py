"""Hand-calculated LP cases and independent rejection of invalid dispatches."""

import unittest

import numpy as np
import pandas as pd

from src.optimization_model import DispatchSolveError, solve_dispatch
from src.optimization_validation import audit_dispatch, summarize_dispatch


class OptimizationTests(unittest.TestCase):
    def test_milp_full_precision_oracle(self):
        data = self.data([30, 40], [40, 0])
        result, info = solve_dispatch(data, self.storage, self.thermal, self.costs, mutual_exclusion=True)
        np.testing.assert_allclose(result.charge, [10, 0], atol=1e-9)
        np.testing.assert_allclose(result.discharge, [0, 10], atol=1e-9)
        self.assertAlmostEqual(info['objective_CNY'], 10600, places=7)
        self.assertEqual(info['integer_variable_count'], 2)
        self.assertTrue(audit_dispatch(result, data, self.storage, self.thermal)['passed'])

    def test_milp_blocks_loss_dumping(self):
        data = self.data([50] * 4, [100] * 4)
        storage = dict(self.storage, eta_charge=.95, eta_discharge=.95)
        result, info = solve_dispatch(data, storage, self.thermal, self.costs, mutual_exclusion=True)
        self.assertEqual(info['solver_status'], 'Optimal')
        self.assertFalse(((result.charge > 1e-6) & (result.discharge > 1e-6)).any())
        self.assertTrue(audit_dispatch(result, data, storage, self.thermal)['passed'])

    def test_milp_infeasible_fails_closed(self):
        thermal = dict(self.thermal, thermal_min_MW=30)
        with self.assertRaises(DispatchSolveError):
            solve_dispatch(self.data([0], [0]), dict(self.storage, energy_capacity_MWh=0, power_capacity_MW=0),
                           thermal, self.costs, mutual_exclusion=True)

    def setUp(self):
        self.storage = dict(energy_capacity_MWh=40, power_capacity_MW=20,
                            soc_initial=0.5, soc_min=0.1, soc_max=0.9, eta_charge=1, eta_discharge=1)
        self.thermal = dict(thermal_min_MW=0, thermal_max_MW=120, thermal_ramp_MW_per_h=30)
        self.costs = dict(thermal_cost_CNY_per_MWh=350, curtailment_penalty_CNY_per_MWh=200,
                          load_shedding_penalty_CNY_per_MWh=10000,
                          storage_variable_om_CNY_per_MWh_discharged=10)

    def data(self, load, wind, dt=1.0):
        return pd.DataFrame(dict(hour=np.arange(len(load)) * dt, load=load, wind=wind, solar=0))

    def test_two_hour_hand_oracle(self):
        data = self.data([30, 40], [40, 0])
        result, info = solve_dispatch(data, self.storage, self.thermal, self.costs)
        np.testing.assert_allclose(result.charge, [10, 0], atol=1e-6)
        np.testing.assert_allclose(result.discharge, [0, 10], atol=1e-6)
        np.testing.assert_allclose(result.thermal, [0, 30], atol=1e-6)
        self.assertAlmostEqual(info["objective_CNY"], 10600)
        self.assertEqual(info["integer_variable_count"], 0)
        self.assertTrue(audit_dispatch(result, data, self.storage, self.thermal)["passed"])

    def test_zero_storage_and_shedding(self):
        storage = dict(self.storage, energy_capacity_MWh=0, power_capacity_MW=0)
        data = self.data([150], [0])
        result, info = solve_dispatch(data, storage, self.thermal, self.costs)
        self.assertEqual(result.thermal.iloc[0], 120)
        self.assertEqual(result.unserved.iloc[0], 30)
        self.assertTrue(result.soc.isna().all())
        self.assertTrue(audit_dispatch(result, data, storage, self.thermal)["passed"])
        self.assertAlmostEqual(info["objective_CNY"], 342000)

    def test_half_hour_oracle(self):
        data = self.data([30, 40], [40, 0], dt=0.5)
        thermal = dict(self.thermal, thermal_ramp_MW_per_h=60)
        result, info = solve_dispatch(data, self.storage, thermal, self.costs, 0.5)
        self.assertAlmostEqual(info["objective_CNY"], 5300)
        self.assertTrue(audit_dispatch(result, data, self.storage, thermal, 0.5)["passed"])
        self.assertEqual(summarize_dispatch(result, self.costs, 0.5).total_load_MWh.iloc[0], 35)

    def test_infeasible_stops_without_dispatch(self):
        data = self.data([0], [0])
        storage = dict(self.storage, energy_capacity_MWh=0, power_capacity_MW=0)
        thermal = dict(self.thermal, thermal_min_MW=30)
        with self.assertRaises(DispatchSolveError) as context:
            solve_dispatch(data, storage, thermal, self.costs)
        self.assertEqual(context.exception.status, "Infeasible")

    def test_invalid_inputs(self):
        data = self.data([30], [0])
        for bad in (-1, np.nan, np.inf):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                solve_dispatch(data, self.storage, dict(self.thermal, thermal_ramp_MW_per_h=bad), self.costs)
        with self.assertRaises(ValueError):
            solve_dispatch(data, dict(self.storage, power_capacity_MW=-1), self.thermal, self.costs)

    def test_auditor_rejects_changed_input_and_state(self):
        data = self.data([30, 40], [40, 0])
        result, _ = solve_dispatch(data, self.storage, self.thermal, self.costs)
        for column in ("wind_available", "thermal", "energy_MWh"):
            broken = result.copy()
            broken.loc[0, column] += 1
            self.assertFalse(audit_dispatch(broken, data, self.storage, self.thermal)["passed"])

    def test_continuous_lp_cycling_is_detected_not_accepted(self):
        # A one-hour terminal constraint requires discharge = 0.95**2 * charge.
        # Curtailment savings (390) exceed variable O&M (180.5), favoring cycling.
        data = self.data([30], [100])
        storage = dict(self.storage, eta_charge=0.95, eta_discharge=0.95)
        thermal = dict(self.thermal, thermal_min_MW=30)
        result, _ = solve_dispatch(data, storage, thermal, self.costs)
        self.assertAlmostEqual(result.charge.iloc[0], 20)
        self.assertAlmostEqual(result.discharge.iloc[0], 18.05)
        audit = audit_dispatch(result, data, storage, thermal)
        self.assertFalse(audit["passed"])
        self.assertIn("simultaneous_charge_discharge", audit["failed_checks"])


if __name__ == "__main__":
    unittest.main()
