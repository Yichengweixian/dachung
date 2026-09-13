"""使用手算算例检查规则分支、时间步长与异常输入；不依赖额外测试框架。"""

import unittest

import numpy as np
import pandas as pd

from src.balance_model import calculate_no_storage_balance
from src.data_loader import validate_input_data
from src.metrics import summarize_no_storage
from src.validation import validate_no_storage_result


class NoStorageTests(unittest.TestCase):
    def setUp(self):
        # 富余、恰好匹配、火电补缺、火电不足、零负荷五个独立时段。
        self.data = pd.DataFrame({
            "hour": [0, 1, 2, 3, 4], "load": [10, 10, 10, 200, 0],
            "wind": [8, 4, 2, 20, 5], "solar": [7, 6, 3, 10, 0],
        })

    def test_dispatch_branches_and_hand_calculated_totals(self):
        result = calculate_no_storage_balance(self.data, 120)
        np.testing.assert_allclose(result.renewable_used, [10, 10, 5, 30, 0])
        np.testing.assert_allclose(result.curtailment, [5, 0, 0, 0, 5])
        np.testing.assert_allclose(result.thermal, [0, 0, 5, 120, 0])
        np.testing.assert_allclose(result.unserved, [0, 0, 0, 50, 0])
        summary = summarize_no_storage(result)
        row = summary.iloc[0]
        for metric, expected in {
            "total_load_MWh": 230, "renewable_available_MWh": 65,
            "renewable_used_MWh": 55, "curtailment_MWh": 10,
            "thermal_generation_MWh": 125, "unserved_MWh": 50,
            "renewable_utilization_pct": 100 * 55 / 65,
        }.items():
            self.assertAlmostEqual(row[metric], expected)
        validate_no_storage_result(result, summary, 120)
        self.assertEqual(list(self.data.columns), ["hour", "load", "wind", "solar"])

    def test_half_hour_energy_scaling(self):
        self.data["hour"] = self.data["hour"] * 0.5
        result = calculate_no_storage_balance(self.data, 120, 0.5)
        summary = summarize_no_storage(result, 0.5)
        self.assertEqual(summary.iloc[0].total_load_MWh, 115)
        self.assertEqual(summary.iloc[0].unserved_MWh, 25)
        validate_no_storage_result(result, summary, 120, 0.5)

    def test_zero_renewables_and_zero_thermal(self):
        self.data[["wind", "solar"]] = 0
        result = calculate_no_storage_balance(self.data, 0)
        summary = summarize_no_storage(result)
        self.assertTrue(np.isnan(summary.iloc[0].renewable_utilization_pct))
        self.assertTrue(np.isnan(summary.iloc[0].curtailment_rate_pct))
        np.testing.assert_allclose(result.unserved, self.data.load)
        validate_no_storage_result(result, summary, 0)

    def test_invalid_inputs(self):
        for value in (-1, np.inf, np.nan):
            with self.subTest(thermal_max=value), self.assertRaises(ValueError):
                calculate_no_storage_balance(self.data, value)
        for change in ("negative", "missing", "duplicate", "length"):
            bad = self.data.copy()
            if change == "negative": bad.loc[0, "wind"] = -1
            if change == "missing": bad.loc[0, "solar"] = np.nan
            if change == "duplicate": bad.loc[1, "hour"] = 0
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_input_data(bad, num_steps=24 if change == "length" else 5)

    def test_validator_detects_incorrect_dispatch(self):
        result = calculate_no_storage_balance(self.data, 120)
        result.loc[3, "thermal"] = 121
        with self.assertRaises(ValueError):
            validate_no_storage_result(result, summarize_no_storage(result), 120)


if __name__ == "__main__":
    unittest.main()
