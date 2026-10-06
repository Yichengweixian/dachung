"""Checks for the continuous joint E/P sizing MILP."""

from dataclasses import asdict
import unittest

import numpy as np
import pandas as pd

from src.economic_model import EconomicParameters, evaluate_system_costs
from src.joint_capacity_optimization import solve_joint_capacity_dispatch
from src.optimization_model import solve_dispatch
from src.optimization_validation import audit_dispatch, summarize_dispatch


class JointCapacityOptimizationTests(unittest.TestCase):
    def test_joint_solution_obeys_existing_dispatch_audit_and_cost_basis(self):
        data = pd.DataFrame({"hour": [0.0, 1.0], "load": [30.0, 40.0],
                             "wind": [40.0, 0.0], "solar": [0.0, 0.0]})
        storage = {"energy_capacity_MWh": 40.0, "power_capacity_MW": 20.0,
                   "soc_initial": .5, "soc_min": .1, "soc_max": .9,
                   "eta_charge": 1.0, "eta_discharge": 1.0}
        thermal = {"thermal_min_MW": 0.0, "thermal_max_MW": 120.0,
                   "thermal_ramp_MW_per_h": 30.0}
        economics = EconomicParameters(
            thermal_cost_CNY_per_MWh=350, storage_energy_capex_CNY_per_kWh=800,
            storage_power_capex_CNY_per_kW=300, storage_lifetime_years=15,
            discount_rate=.05, storage_fixed_om_fraction_per_year=.02,
            storage_variable_om_CNY_per_MWh_discharged=10,
            curtailment_penalty_CNY_per_MWh=200, load_shedding_penalty_CNY_per_MWh=10000,
            hours_per_year=8760,
        )
        result, info = solve_joint_capacity_dispatch(
            data, storage, thermal, asdict(economics), energy_capacity_upper_MWh=40,
            power_capacity_upper_MW=20,
        )
        selected = dict(storage, energy_capacity_MWh=info["energy_capacity_MWh"],
                        power_capacity_MW=info["power_capacity_MW"])
        self.assertEqual(info["solver_status"], "Optimal")
        self.assertLessEqual(info["energy_capacity_MWh"], 40)
        self.assertLessEqual(info["power_capacity_MW"], 20)
        self.assertTrue(audit_dispatch(result, data, selected, thermal)["passed"])
        self.assertFalse(((result.charge > 1e-6) & (result.discharge > 1e-6)).any())
        summary = summarize_dispatch(result, asdict(economics)).iloc[0].to_dict()
        summary.update(scenario="joint", energy_capacity_MWh=info["energy_capacity_MWh"],
                       power_capacity_MW=info["power_capacity_MW"], num_steps=len(data),
                       time_step_hours=1.0, load_shedding_MWh=summary["unserved_MWh"],
                       storage_discharge_MWh=summary["discharge_MWh"], initial_inventory_supply_MWh=0.0)
        total = evaluate_system_costs(pd.DataFrame([summary]), economics).total_cost_CNY.iloc[0]
        self.assertAlmostEqual(info["objective_CNY"], total, places=6)

    def test_fixed_capacity_bounds_match_existing_dispatch(self):
        data = pd.DataFrame({"hour": [0.0, 1.0], "load": [30.0, 40.0],
                             "wind": [40.0, 0.0], "solar": [0.0, 0.0]})
        storage = {"energy_capacity_MWh": 40.0, "power_capacity_MW": 20.0,
                   "soc_initial": .5, "soc_min": .1, "soc_max": .9,
                   "eta_charge": 1.0, "eta_discharge": 1.0}
        thermal = {"thermal_min_MW": 0.0, "thermal_max_MW": 120.0,
                   "thermal_ramp_MW_per_h": 30.0}
        economics = EconomicParameters(
            thermal_cost_CNY_per_MWh=350, storage_energy_capex_CNY_per_kWh=800,
            storage_power_capex_CNY_per_kW=300, storage_lifetime_years=15,
            discount_rate=.05, storage_fixed_om_fraction_per_year=.02,
            storage_variable_om_CNY_per_MWh_discharged=10,
            curtailment_penalty_CNY_per_MWh=200, load_shedding_penalty_CNY_per_MWh=10000,
            hours_per_year=8760,
        )
        joint, info = solve_joint_capacity_dispatch(
            data, storage, thermal, asdict(economics), energy_capacity_lower_MWh=40,
            energy_capacity_upper_MWh=40, power_capacity_lower_MW=20,
            power_capacity_upper_MW=20,
        )
        fixed, _ = solve_dispatch(data, storage, thermal, asdict(economics), mutual_exclusion=True)
        self.assertAlmostEqual(info["energy_capacity_MWh"], 40, places=9)
        self.assertAlmostEqual(info["power_capacity_MW"], 20, places=9)
        for column in ("thermal", "charge", "discharge", "unserved", "energy_start_MWh",
                       "energy_MWh", "soc"):
            np.testing.assert_allclose(joint[column], fixed[column], atol=1e-8, rtol=1e-10)
        np.testing.assert_allclose(joint.wind_used + joint.solar_used,
                                   fixed.wind_used + fixed.solar_used, atol=1e-8, rtol=1e-10)
        np.testing.assert_allclose(joint.wind_curt + joint.solar_curt,
                                   fixed.wind_curt + fixed.solar_curt, atol=1e-8, rtol=1e-10)
        joint_summary = summarize_dispatch(joint, asdict(economics)).iloc[0].to_dict()
        fixed_summary = summarize_dispatch(fixed, asdict(economics)).iloc[0].to_dict()
        for key in ("unserved_MWh", "curtailment_MWh", "thermal_generation_MWh",
                    "charge_MWh", "discharge_MWh"):
            self.assertAlmostEqual(joint_summary[key], fixed_summary[key], places=8)
        for summary in (joint_summary, fixed_summary):
            summary.update(scenario="fixed_equivalence", energy_capacity_MWh=40,
                           power_capacity_MW=20, num_steps=len(data), time_step_hours=1.0,
                           load_shedding_MWh=summary["unserved_MWh"],
                           storage_discharge_MWh=summary["discharge_MWh"],
                           initial_inventory_supply_MWh=0.0)
        joint_total = evaluate_system_costs(pd.DataFrame([joint_summary]), economics).total_cost_CNY.iloc[0]
        fixed_total = evaluate_system_costs(pd.DataFrame([fixed_summary]), economics).total_cost_CNY.iloc[0]
        self.assertAlmostEqual(joint_total, fixed_total, places=8)


if __name__ == "__main__":
    unittest.main()
