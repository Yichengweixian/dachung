"""手算案例验证储能边界、效率、调度顺序及无储能退化。"""

import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

from src.balance_model import calculate_no_storage_balance
from src.storage_model import StorageParameters, calculate_storage_balance
from src.storage_metrics import summarize_storage
from src.storage_validation import validate_storage_result


def profile(load, renewable, dt=1.0):
    return pd.DataFrame({"hour": np.arange(len(load)) * dt, "load": load,
                         "wind": renewable, "solar": np.zeros(len(load))})


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = StorageParameters()

    def check(self, data, storage=None, thermal=120.0, dt=1.0):
        s = storage or self.storage
        result = calculate_storage_balance(data, s, thermal, dt)
        summary = summarize_storage(result, s, dt)
        validate_storage_result(result, summary, s, thermal, dt)
        return result, summary.iloc[0]

    def test_energy_limited_charging_and_full_battery(self):
        r, summary = self.check(profile([0, 0], [100, 100]))
        np.testing.assert_allclose(r.storage_charge, [16 / 0.95, 0])
        np.testing.assert_allclose(r.energy_end_MWh, [36, 36])
        self.assertAlmostEqual(summary.storage_charge_MWh, 16 / 0.95)
        self.assertAlmostEqual(summary.storage_utilization_pct, 50)

    def test_power_limited_charging(self):
        r, _ = self.check(profile([0, 0, 0], [100, 100, 100]), replace(self.storage, soc_initial=0.1))
        np.testing.assert_allclose(r.storage_charge, [20, 13 / 0.95, 0])
        np.testing.assert_allclose(r.energy_end_MWh, [23, 36, 36])

    def test_discharge_efficiency_lower_bound_and_shedding(self):
        r, summary = self.check(profile([200, 200], [0, 0]))
        np.testing.assert_allclose(r.storage_discharge, [15.2, 0])
        np.testing.assert_allclose(r.thermal, [120, 120])
        np.testing.assert_allclose(r.load_shedding, [64.8, 80])
        np.testing.assert_allclose(r.soc, [0.1, 0.1])
        self.assertAlmostEqual(summary.storage_discharge_MWh, 15.2)

    def test_power_limited_discharge(self):
        r, _ = self.check(profile([100, 100], [0, 0]), replace(self.storage, soc_initial=0.9))
        np.testing.assert_allclose(r.storage_discharge, [20, 10.4])
        np.testing.assert_allclose(r.thermal, [80, 89.6])

    def test_equal_supply_and_small_gap_priority(self):
        r, _ = self.check(profile([10, 10, 10], [10, 15, 8]))
        np.testing.assert_allclose(r.storage_charge, [0, 5, 0])
        np.testing.assert_allclose(r.storage_discharge, [0, 0, 2])
        np.testing.assert_allclose(r.thermal, 0)
        self.assertAlmostEqual(r.soc.iloc[0], 0.5)

    def test_half_hour_step_and_energy_conservation(self):
        r, summary = self.check(profile([0, 200], [100, 0], 0.5), dt=0.5)
        np.testing.assert_allclose(r.storage_charge, [20, 0])
        np.testing.assert_allclose(r.storage_discharge, [0, 20])
        self.assertAlmostEqual(r.energy_end_MWh.iloc[0], 29.5)
        self.assertAlmostEqual(r.energy_end_MWh.iloc[1], 29.5 - 10 / 0.95)
        self.assertAlmostEqual(summary.storage_charge_MWh, 10)
        self.assertAlmostEqual(summary.storage_discharge_MWh, 10)
        self.assertAlmostEqual(summary.storage_active_hours, 1)

    def test_zero_capacity_matches_no_storage(self):
        data = profile([10, 200, 0], [20, 0, 0])
        r, summary = self.check(data, replace(self.storage, energy_capacity_MWh=0, power_capacity_MW=0))
        base = calculate_no_storage_balance(data)
        for left, right in [("thermal", "thermal"), ("curtailment", "curtailment"),
                            ("load_shedding", "unserved"), ("renewable_used", "renewable_used")]:
            np.testing.assert_allclose(r[left], base[right])
        self.assertTrue(r.soc.isna().all())
        self.assertTrue(np.isnan(summary.storage_utilization_pct))

    def test_zero_power_and_zero_renewables(self):
        r, summary = self.check(profile([20, 30], [0, 0]), replace(self.storage, power_capacity_MW=0))
        np.testing.assert_allclose(r.soc, 0.5)
        self.assertEqual(summary.storage_utilization_pct, 0)
        self.assertTrue(np.isnan(summary.renewable_utilization_pct))

    def test_invalid_parameters(self):
        for field, value in [("eta_charge", 0), ("eta_discharge", 1.1), ("soc_initial", 0.95),
                             ("soc_min", -0.1), ("soc_max", 1.1), ("energy_capacity_MWh", -1),
                             ("power_capacity_MW", np.inf), ("eta_charge", np.nan)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                replace(self.storage, **{field: value})
        with self.assertRaises(ValueError):
            calculate_storage_balance(profile([1], [0]), self.storage, -1)

    def test_validator_detects_broken_soc_recurrence(self):
        r, _ = self.check(profile([100, 100], [0, 0]))
        r.loc[1, "energy_start_MWh"] += 1
        with self.assertRaises(ValueError):
            validate_storage_result(r, summarize_storage(r, self.storage), self.storage, 120)


if __name__ == "__main__":
    unittest.main()
