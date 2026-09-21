"""Continuous LP dispatch following the original master U06 specification."""

from pathlib import Path
import tempfile

import numpy as np
import pandas as pd
import pulp

from .data_loader import validate_input_data
from .storage_model import StorageParameters


class DispatchSolveError(RuntimeError):
    def __init__(self, status, log):
        super().__init__(f"CBC did not prove Optimal: {status}")
        self.status = status
        self.log = log


def solve_dispatch(data, storage, thermal, economics, time_step_hours=1.0, terminal=True,
                   mutual_exclusion=False):
    """Return dispatch and solver evidence; do not apply physical acceptance tests."""
    validate_input_data(data, time_step_hours=time_step_hours)
    s = StorageParameters(**storage)
    dt = time_step_hours
    minimum = thermal["thermal_min_MW"]
    maximum = thermal["thermal_max_MW"]
    ramp = thermal["thermal_ramp_MW_per_h"]
    if not np.isfinite([minimum, maximum]).all() or not 0 <= minimum <= maximum:
        raise ValueError("Invalid thermal output bounds")
    if ramp is not None and (not np.isfinite(ramp) or ramp < 0):
        raise ValueError("Invalid thermal ramp limit")
    names = ("thermal_cost_CNY_per_MWh", "curtailment_penalty_CNY_per_MWh",
             "load_shedding_penalty_CNY_per_MWh", "storage_variable_om_CNY_per_MWh_discharged")
    coefficients = [economics[name] for name in names]
    if not np.isfinite(coefficients).all() or min(coefficients) < 0:
        raise ValueError("Costs must be finite and nonnegative")

    model = pulp.LpProblem("U06_master_continuous_LP", pulp.LpMinimize)
    count = len(data)
    fields = ("thermal", "wind_used", "solar_used", "wind_curt", "solar_curt",
              "charge", "discharge", "unserved")
    variables = {field: [pulp.LpVariable(f"{field}_{i:04d}", lowBound=0) for i in range(count)]
                 for field in fields}
    modes = [pulp.LpVariable(f"charge_mode_{i:04d}", cat="Binary") for i in range(count)] if mutual_exclusion else None
    energy = [pulp.LpVariable(f"energy_{i:04d}", lowBound=s.soc_min * s.energy_capacity_MWh,
                             upBound=s.soc_max * s.energy_capacity_MWh) for i in range(count + 1)]
    model += energy[0] == s.soc_initial * s.energy_capacity_MWh
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
        model += v["charge"] <= s.power_capacity_MW
        model += v["discharge"] <= s.power_capacity_MW
        if modes is not None:
            model += v["charge"] <= s.power_capacity_MW * modes[i]
            model += v["discharge"] <= s.power_capacity_MW * (1 - modes[i])
        model += energy[i + 1] == (energy[i] + s.eta_charge * v["charge"] * dt
                                  - v["discharge"] * dt / s.eta_discharge)
        model += (v["wind_used"] + v["solar_used"] + v["thermal"] + v["discharge"]
                  + v["unserved"] == row.load + v["charge"])
    model += pulp.lpSum(
        dt * (coefficients[0] * variables["thermal"][i]
              + coefficients[1] * (variables["wind_curt"][i] + variables["solar_curt"][i])
              + coefficients[2] * variables["unserved"][i]
              + coefficients[3] * variables["discharge"][i]) for i in range(count)
    )
    with tempfile.TemporaryDirectory(prefix="master-u06-") as folder:
        log_path = Path(folder) / "cbc.log"
        if mutual_exclusion:
            from .cbc_full_precision import FullPrecisionCBC
            solver = FullPrecisionCBC(msg=False)
        else:
            solver = pulp.PULP_CBC_CMD(msg=False, threads=1, options=["primalTolerance 1e-9"],
                                       logPath=str(log_path))
        model.solve(solver)
        log = solver.log if mutual_exclusion else log_path.read_text(encoding="utf-8", errors="replace")
    status = pulp.LpStatus[model.status]
    if status != "Optimal" or model.sol_status != pulp.LpSolutionOptimal:
        raise DispatchSolveError(status, log)
    result = data.rename(columns={"wind": "wind_available", "solar": "solar_available"}).copy()
    for name in fields:
        result[name] = [pulp.value(variable) for variable in variables[name]]
    result["energy_start_MWh"] = [pulp.value(variable) for variable in energy[:-1]]
    result["energy_MWh"] = [pulp.value(variable) for variable in energy[1:]]
    result["soc"] = result.energy_MWh / s.energy_capacity_MWh if s.energy_capacity_MWh > 0 else np.nan
    result["balance_error_MW"] = (result.wind_used + result.solar_used + result.thermal
                                   + result.discharge + result.unserved - result.load - result.charge)
    return result, {"solver_status": status, "objective_CNY": pulp.value(model.objective),
                    "pulp_version": pulp.__version__, "cbc_path": solver.path, "cbc_log": log,
                    "model_class": "MILP" if mutual_exclusion else "LP",
                    "integer_variable_count": sum(v.isInteger() for v in model.variables()),
                    "precision": getattr(solver, "precision", None)}
