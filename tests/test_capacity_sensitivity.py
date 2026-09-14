"""验证批量场景独立性及边际统计，不预设真实算例应有何种趋势。"""

import unittest

import pandas as pd

from src.capacity_sensitivity import run_capacity_scenarios, calculate_marginal_changes
from src.storage_model import StorageParameters


class CapacitySensitivityTests(unittest.TestCase):
    def test_scenario_order_cannot_change_results_or_base_configuration(self):
        data = pd.DataFrame({"hour": [0, 1, 2], "load": [100, 0, 100],
                             "wind": [0, 100, 0], "solar": [0, 0, 0]})
        original = data.copy(deep=True)
        storage = StorageParameters()
        first, outputs = run_capacity_scenarios(data, storage, [0, 20, 40])
        reverse, _ = run_capacity_scenarios(data, storage, [40, 20, 0])
        pd.testing.assert_frame_equal(first, reverse)
        pd.testing.assert_frame_equal(data, original)
        self.assertEqual(storage.energy_capacity_MWh, 40)
        for _, (parameters, result) in outputs.items():
            self.assertEqual(result.energy_start_MWh.iloc[0], parameters.energy_capacity_MWh * 0.5)
            self.assertEqual(parameters.power_capacity_MW, 20 if parameters.energy_capacity_MWh else 0)

    def test_hand_calculated_marginal_values_for_unequal_steps(self):
        data = pd.DataFrame({"energy_capacity_MWh": [0, 10, 30],
                             "renewable_utilization_pct": [80, 82, 83],
                             "curtailment_MWh": [100, 90, 85],
                             "thermal_generation_MWh": [300, 280, 270]})
        marginal = calculate_marginal_changes(data)
        self.assertEqual(marginal.utilization_gain_percentage_points.tolist(), [2, 1])
        self.assertEqual(marginal.curtailment_reduction_MWh_per_MWh_capacity.tolist(), [1, 0.25])
        self.assertEqual(marginal.thermal_reduction_MWh_per_MWh_capacity.tolist(), [2, 0.5])

    def test_reject_duplicate_or_invalid_scenarios(self):
        data = pd.DataFrame({"hour": [0], "load": [1], "wind": [0], "solar": [0]})
        for capacities in [[], [0, 0], [-1, 20]]:
            with self.subTest(capacities=capacities), self.assertRaises(ValueError):
                run_capacity_scenarios(data, StorageParameters(), capacities)


if __name__ == "__main__":
    unittest.main()
