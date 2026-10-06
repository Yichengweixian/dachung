"""Joint storage energy/power sizing with the established continuous dispatch MILP."""

import numpy as np
import pandas as pd
import pulp

from .cbc_full_precision import FullPrecisionCBC
from .data_loader import validate_input_data
from .economic_model import EconomicParameters, capital_recovery_factor
from .optimization_model import DispatchSolveError
from .storage_model import StorageParameters


def solve_joint_capacity_dispatch(data, storage, thermal, economics, *,
                                  energy_capacity_upper_MWh, power_capacity_upper_MW,
                                  energy_capacity_lower_MWh=0.0, power_capacity_lower_MW=0.0,
                                  time_step_hours=1.0, terminal=True):
    """Optimize E and P within fixed ex-ante bounds and return dispatch evidence.

    The dispatch equations, costs, SOC limits, terminal rule, and charge/discharge
    mutual exclusion match ``solve_dispatch``.  Investment and fixed O&M are
    allocated to the simulated horizon exactly as ``evaluate_system_costs`` does.
    """
    validate_input_data(data, time_step_hours=time_step_hours)
    s = StorageParameters(**storage)
    p = EconomicParameters(**economics)
    dt = time_step_hours
    e_lower = float(energy_capacity_lower_MWh)
    e_upper = float(energy_capacity_upper_MWh)
    p_lower = float(power_capacity_lower_MW)
    p_upper = float(power_capacity_upper_MW)
    if (not np.isfinite([e_lower, e_upper, p_lower, p_upper]).all()
            or e_lower < 0 or p_lower < 0 or e_lower > e_upper or p_lower > p_upper):
        raise ValueError("Joint capacity bounds must be finite, nonnegative, and ordered")
    minimum = thermal["thermal_min_MW"]
    maximum = thermal["thermal_max_MW"]
    ramp = thermal["thermal_ramp_MW_per_h"]
    if not np.isfinite([minimum, maximum]).all() or not 0 <= minimum <= maximum:
        raise ValueError("Invalid thermal output bounds")
    if ramp is not None and (not np.isfinite(ramp) or ramp < 0):
        raise ValueError("Invalid thermal ramp limit")

    model = pulp.LpProblem("joint_storage_capacity_MILP", pulp.LpMinimize)
    count = len(data)
    energy_capacity = pulp.LpVariable("energy_capacity_MWh", lowBound=e_lower, upBound=e_upper)
    power_capacity = pulp.LpVariable("power_capacity_MW", lowBound=p_lower, upBound=p_upper)
    fields = ("thermal", "wind_used", "solar_used", "wind_curt", "solar_curt",
              "charge", "discharge", "unserved")
    variables = {field: [pulp.LpVariable(f"{field}_{i:04d}", lowBound=0) for i in range(count)]
                 for field in fields}
    modes = [pulp.LpVariable(f"charge_mode_{i:04d}", cat="Binary") for i in range(count)]
    energy = [pulp.LpVariable(f"energy_{i:04d}", lowBound=0) for i in range(count + 1)]
    for state in energy:
        model += state >= s.soc_min * energy_capacity
        model += state <= s.soc_max * energy_capacity
    model += energy[0] == s.soc_initial * energy_capacity
    if terminal:
        model += energy[-1] == energy[0]

    for i, row in enumerate(data.itertuples(index=False)):
        v = {name: variables[name][i] for name in fields}
        model += v["thermal"] >= minimum
        model += v["thermal"] <= maximum
        if i > 0 and ramp is not None:
            change = v["thermal"] - variables["thermal"][i - 1]
            model += change <= ramp * dt
            model += change >= -ramp * dt
        model += v["wind_used"] + v["wind_curt"] == row.wind
        model += v["solar_used"] + v["solar_curt"] == row.solar
        model += v["unserved"] <= row.load
        model += v["charge"] <= power_capacity
        model += v["discharge"] <= power_capacity
        # P is a decision variable, so these fixed upper-bound constraints are
        # the linear big-M counterpart of the existing fixed-P mode constraints.
        model += v["charge"] <= p_upper * modes[i]
        model += v["discharge"] <= p_upper * (1 - modes[i])
        model += energy[i + 1] == (energy[i] + s.eta_charge * v["charge"] * dt
                                  - v["discharge"] * dt / s.eta_discharge)
        model += (v["wind_used"] + v["solar_used"] + v["thermal"] + v["discharge"]
                  + v["unserved"] == row.load + v["charge"])

    horizon_fraction = count * dt / p.hours_per_year
    annualized_and_fixed_rate = capital_recovery_factor(p.discount_rate, p.storage_lifetime_years)
    annualized_and_fixed_rate += p.storage_fixed_om_fraction_per_year
    energy_investment_cost = 1000 * p.storage_energy_capex_CNY_per_kWh * horizon_fraction * annualized_and_fixed_rate
    power_investment_cost = 1000 * p.storage_power_capex_CNY_per_kW * horizon_fraction * annualized_and_fixed_rate
    model += (energy_investment_cost * energy_capacity + power_investment_cost * power_capacity
              + pulp.lpSum(dt * (
                  p.thermal_cost_CNY_per_MWh * variables["thermal"][i]
                  + p.curtailment_penalty_CNY_per_MWh * (variables["wind_curt"][i] + variables["solar_curt"][i])
                  + p.load_shedding_penalty_CNY_per_MWh * variables["unserved"][i]
                  + p.storage_variable_om_CNY_per_MWh_discharged * variables["discharge"][i]
              ) for i in range(count)))

    solver = FullPrecisionCBC(msg=False)
    model.solve(solver)
    log = solver.log
    status = pulp.LpStatus[model.status]
    if status != "Optimal" or model.sol_status != pulp.LpSolutionOptimal:
        raise DispatchSolveError(status, log)

    selected_energy = pulp.value(energy_capacity)
    selected_power = pulp.value(power_capacity)
    result = data.rename(columns={"wind": "wind_available", "solar": "solar_available"}).copy()
    for name in fields:
        result[name] = [pulp.value(variable) for variable in variables[name]]
    result["energy_start_MWh"] = [pulp.value(variable) for variable in energy[:-1]]
    result["energy_MWh"] = [pulp.value(variable) for variable in energy[1:]]
    result["soc"] = result.energy_MWh / selected_energy if selected_energy > 0 else np.nan
    result["balance_error_MW"] = (result.wind_used + result.solar_used + result.thermal
                                   + result.discharge + result.unserved - result.load - result.charge)
    return result, {"solver_status": status, "objective_CNY": pulp.value(model.objective),
                    "energy_capacity_MWh": selected_energy, "power_capacity_MW": selected_power,
                    "pulp_version": pulp.__version__, "cbc_path": solver.path, "cbc_log": log,
                    "integer_variable_count": sum(v.isInteger() for v in model.variables()),
                    "precision": solver.precision,
                    "energy_capacity_lower_MWh": e_lower, "energy_capacity_upper_MWh": e_upper,
                    "power_capacity_lower_MW": p_lower, "power_capacity_upper_MW": p_upper}
