"""用可手算的电量、投资和时长检查成本，不预设真实算例的最低容量。"""

from dataclasses import replace
import unittest

import pandas as pd

from src.economic_model import EconomicParameters, capital_recovery_factor, evaluate_system_costs, validate_cost_results


class EconomicsTests(unittest.TestCase):
    def setUp(self):
        self.parameters = EconomicParameters(
            thermal_cost_CNY_per_MWh=300, storage_energy_capex_CNY_per_kWh=100,
            storage_power_capex_CNY_per_kW=200, storage_lifetime_years=10, discount_rate=0,
            storage_fixed_om_fraction_per_year=0.01, storage_variable_om_CNY_per_MWh_discharged=4,
            curtailment_penalty_CNY_per_MWh=50, load_shedding_penalty_CNY_per_MWh=1000,
            hours_per_year=8760,
        )
        self.summary = pd.DataFrame([{
            "scenario": "hand_case", "energy_capacity_MWh": 2, "power_capacity_MW": 1,
            "num_steps": 24, "time_step_hours": 1, "thermal_generation_MWh": 10,
            "curtailment_MWh": 2, "load_shedding_MWh": 1, "storage_discharge_MWh": 3,
            "renewable_utilization_pct": 80, "curtailment_rate_pct": 20,
            "initial_inventory_supply_MWh": 0.5,
        }])

    def test_hand_calculated_costs_units_and_no_double_counting(self):
        original = self.summary.copy(deep=True)
        result = evaluate_system_costs(self.summary, self.parameters)
        row = result.iloc[0]
        self.assertEqual(row.storage_capex_CNY, 400000)  # 2000kWh*100 + 1000kW*200
        self.assertEqual(row.storage_annualized_investment_CNY_per_year, 40000)
        self.assertAlmostEqual(row.storage_investment_allocated_CNY, 40000 / 365)
        self.assertAlmostEqual(row.storage_fixed_om_CNY, 4000 / 365)
        self.assertEqual(row.storage_variable_om_CNY, 12)
        self.assertEqual(row.thermal_cost_CNY, 3000)
        self.assertEqual(row.curtailment_cost_CNY, 100)
        self.assertEqual(row.load_shedding_cost_CNY, 1000)
        self.assertAlmostEqual(row.total_cost_CNY, 4112 + 44000 / 365)
        self.assertAlmostEqual(row.operating_cost_excluding_investment_CNY, 4112 + 4000 / 365)
        self.assertEqual(row.initial_inventory_thermal_value_CNY, 150)
        validate_cost_results(result, self.parameters)
        pd.testing.assert_frame_equal(original, self.summary)

    def test_capital_recovery_zero_positive_and_tiny_discount(self):
        self.assertEqual(capital_recovery_factor(0, 10), 0.1)
        self.assertAlmostEqual(capital_recovery_factor(0.1, 2), 1.21 / 2.1)
        self.assertAlmostEqual(capital_recovery_factor(1e-12, 10), 0.1, places=10)

    def test_time_allocation_and_mwh_not_scaled_twice(self):
        half_day = self.summary.copy()
        half_day["time_step_hours"] = 0.5
        row = evaluate_system_costs(half_day, self.parameters).iloc[0]
        self.assertEqual(row.simulation_hours, 12)
        self.assertAlmostEqual(row.storage_investment_allocated_CNY, 40000 / 730)
        self.assertEqual(row.thermal_cost_CNY, 3000)  # 输入已经是MWh，不再乘0.5
        self.assertEqual(row.storage_variable_om_CNY, 12)
        annual = self.summary.copy()
        annual["num_steps"] = 8760
        row = evaluate_system_costs(annual, self.parameters).iloc[0]
        self.assertEqual(row.storage_investment_allocated_CNY, 40000)
        self.assertEqual(row.storage_fixed_om_CNY, 4000)

    def test_zero_storage_has_no_storage_cost(self):
        zero = self.summary.copy()
        zero[["energy_capacity_MWh", "power_capacity_MW", "storage_discharge_MWh", "initial_inventory_supply_MWh"]] = 0
        result = evaluate_system_costs(zero, self.parameters)
        self.assertEqual(result.storage_cost_CNY.iloc[0], 0)
        self.assertEqual(result.total_cost_CNY.iloc[0], 4100)
        validate_cost_results(result, self.parameters)

    def test_changed_parameter_changes_only_related_cost(self):
        before = evaluate_system_costs(self.summary, self.parameters).iloc[0]
        after = evaluate_system_costs(self.summary, replace(self.parameters, curtailment_penalty_CNY_per_MWh=0)).iloc[0]
        self.assertAlmostEqual(before.total_cost_CNY - after.total_cost_CNY, 100)
        self.assertEqual(before.storage_cost_CNY, after.storage_cost_CNY)
        self.assertEqual(before.thermal_cost_CNY, after.thermal_cost_CNY)

    def test_validator_detects_export_or_accounting_errors(self):
        for column in ["total_cost_CNY", "storage_capex_CNY", "storage_investment_allocated_CNY", "load_shedding_cost_CNY"]:
            result = evaluate_system_costs(self.summary, self.parameters)
            result.loc[0, column] += 1
            with self.subTest(column=column), self.assertRaises(ValueError):
                validate_cost_results(result, self.parameters)

    def test_invalid_parameters_or_summary(self):
        for changes in [{"discount_rate": -1}, {"thermal_cost_CNY_per_MWh": float("nan")},
                        {"storage_lifetime_years": 0}, {"hours_per_year": 0},
                        {"storage_fixed_om_fraction_per_year": 2}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.parameters, **changes)
        for column, value in [("num_steps", 0), ("num_steps", 1.5), ("thermal_generation_MWh", -1),
                              ("time_step_hours", float("inf")), ("energy_capacity_MWh", 0)]:
            summary = self.summary.copy()
            summary[column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                evaluate_system_costs(summary, self.parameters)


if __name__ == "__main__":
    unittest.main()
