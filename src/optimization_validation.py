"""Independent arithmetic audit; imports neither the optimizer nor its builder."""

import math

import numpy as np
import pandas as pd


TOLERANCE = 1e-6


def audit_dispatch(result, data, storage, thermal, time_step_hours=1.0, terminal=True):
    """Return every violation without rounding, clipping, or repairing the dispatch."""
    q = result.reset_index(drop=True)
    source = data.reset_index(drop=True)
    dt = time_step_hours
    s = storage
    if len(q) != len(source) or q.empty:
        raise ValueError("Dispatch and source lengths must match and be nonzero")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("Invalid time step")
    residuals = {}

    def equality(name, a, b):
        error = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
        residuals[name] = float(np.max(np.abs(error), initial=0)) if np.isfinite(error).all() else math.inf

    def bounds(name, values, lower, upper):
        values = np.asarray(values, dtype=float)
        if not np.isfinite(values).all():
            residuals[name] = math.inf
            return
        residuals[name] = float(max(0, np.max(np.asarray(lower) - values, initial=0),
                                    np.max(values - np.asarray(upper), initial=0)))

    for output, original in (("hour", "hour"), ("load", "load"),
                             ("wind_available", "wind"), ("solar_available", "solar")):
        equality("input_" + original, q[output], source[original])
    for name in ("thermal", "wind_used", "solar_used", "wind_curt", "solar_curt", "charge",
                 "discharge", "unserved", "energy_start_MWh", "energy_MWh"):
        bounds("nonnegative_" + name, q[name], 0, math.inf)
    equality("power_balance", q.wind_used + q.solar_used + q.thermal + q.discharge + q.unserved,
             q.load + q.charge)
    equality("wind_decomposition", q.wind_used + q.wind_curt, source.wind)
    equality("solar_decomposition", q.solar_used + q.solar_curt, source.solar)
    bounds("thermal_bounds", q.thermal, thermal["thermal_min_MW"], thermal["thermal_max_MW"])
    ramp = thermal["thermal_ramp_MW_per_h"]
    if ramp is not None:
        bounds("thermal_ramp", np.diff(q.thermal), -ramp * dt, ramp * dt)
    bounds("unserved_bounds", q.unserved, 0, source.load.to_numpy())
    bounds("charge_bounds", q.charge, 0, s["power_capacity_MW"])
    bounds("discharge_bounds", q.discharge, 0, s["power_capacity_MW"])
    for field in ("energy_start_MWh", "energy_MWh"):
        bounds("bounds_" + field, q[field], s["soc_min"] * s["energy_capacity_MWh"],
               s["soc_max"] * s["energy_capacity_MWh"])
    equality("initial_energy", q.energy_start_MWh.iloc[0], s["soc_initial"] * s["energy_capacity_MWh"])
    equality("state_continuity", q.energy_start_MWh.to_numpy()[1:], q.energy_MWh.to_numpy()[:-1])
    equality("energy_recurrence", q.energy_MWh,
             q.energy_start_MWh + s["eta_charge"] * q.charge * dt - q.discharge * dt / s["eta_discharge"])
    if terminal:
        equality("terminal_energy", q.energy_MWh.iloc[-1], q.energy_start_MWh.iloc[0])
    if s["energy_capacity_MWh"]:
        equality("soc_definition", q.soc, q.energy_MWh / s["energy_capacity_MWh"])
    else:
        residuals["zero_capacity_soc"] = 0.0 if q.soc.isna().all() else math.inf
    simultaneous = q[(q.charge > TOLERANCE) & (q.discharge > TOLERANCE)]
    failed = [name for name, value in residuals.items() if value >= TOLERANCE]
    if not simultaneous.empty:
        failed.append("simultaneous_charge_discharge")
    return {"passed": not failed, "failed_checks": failed,
            "max_residual": max(residuals.values()), "residuals": residuals,
            "simultaneous_periods": simultaneous[["hour", "charge", "discharge"]].to_dict("records")}


def summarize_dispatch(result, costs, time_step_hours=1.0):
    """Integrate the saved time series; rates are undefined for zero renewables."""
    q = result
    dt = time_step_hours
    totals = {"total_load_MWh": math.fsum(q.load) * dt,
              "renewable_available_MWh": (math.fsum(q.wind_available) + math.fsum(q.solar_available)) * dt,
              "renewable_used_MWh": (math.fsum(q.wind_used) + math.fsum(q.solar_used)) * dt,
              "curtailment_MWh": (math.fsum(q.wind_curt) + math.fsum(q.solar_curt)) * dt,
              "thermal_generation_MWh": math.fsum(q.thermal) * dt,
              "unserved_MWh": math.fsum(q.unserved) * dt,
              "charge_MWh": math.fsum(q.charge) * dt, "discharge_MWh": math.fsum(q.discharge) * dt}
    available = totals["renewable_available_MWh"]
    for name, quantity in (("renewable_utilization_pct", "renewable_used_MWh"),
                            ("curtailment_rate_pct", "curtailment_MWh")):
        totals[name] = 100 * totals[quantity] / available if available > 0 else np.nan
    totals["operating_cost_CNY"] = (
        totals["thermal_generation_MWh"] * costs["thermal_cost_CNY_per_MWh"]
        + totals["curtailment_MWh"] * costs["curtailment_penalty_CNY_per_MWh"]
        + totals["unserved_MWh"] * costs["load_shedding_penalty_CNY_per_MWh"]
        + totals["discharge_MWh"] * costs["storage_variable_om_CNY_per_MWh_discharged"])
    return pd.DataFrame([totals])
