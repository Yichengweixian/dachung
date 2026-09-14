"""U09 storage energy-power grid enumeration.

The search layer delegates dispatch and cost accounting to the frozen U06 and
U05 implementations.  It contains no dispatch constraints or copied cost
formulae.
"""

from dataclasses import replace

import numpy as np
import pandas as pd

from .economic_model import EconomicParameters, evaluate_system_costs, validate_cost_results
from .optimization_model import solve_dispatch
from .optimization_validation import summarize, validate


def generate_candidates(grid):
    """Return the frozen E-P candidates, including one zero-storage case."""
    energies = list(grid["energy_capacities_MWh"])
    powers = list(grid["power_capacities_MW"])
    zero_power = grid["zero_storage_power_MW"]
    if energies != list(range(0, 101, 10)) or powers != list(range(5, 51, 5)) or zero_power != 0:
        raise ValueError("Grid does not match the frozen U09 candidate set")
    candidates = [(0.0, 0.0)] + [(float(e), float(p)) for e in energies if e > 0 for p in powers]
    if len(candidates) != 101 or len(set(candidates)) != 101:
        raise ValueError("U09 grid must contain 101 unique candidates")
    return candidates


def scenario_name(energy_MWh, power_MW):
    return f"E{int(energy_MWh):03d}_P{int(power_MW):02d}"


def solve_candidate(data, base_storage, thermal, economic_parameters, dt, energy_MWh, power_MW,
                    independent_check=None):
    """Solve one candidate and evaluate it with the shared U05 cost function."""
    storage = dict(base_storage, energy_capacity_MWh=float(energy_MWh), power_capacity_MW=float(power_MW))
    cost_dict = {name: getattr(economic_parameters, name) for name in economic_parameters.__dataclass_fields__}
    dispatch, info = solve_dispatch(data, storage, thermal, cost_dict, dt=dt, terminal=True)
    residuals = validate(dispatch, data, storage, thermal, dt, terminal=True)
    if independent_check is not None:
        independent_check(dispatch, storage, thermal, dt, True)
    physical = summarize(dispatch, cost_dict, dt)
    available = float((dispatch.wind_available + dispatch.solar_available).sum() * dt)
    active = (dispatch.charge > 1e-6) | (dispatch.discharge > 1e-6)
    utilization = 100 * float(active.mean()) if energy_MWh > 0 else np.nan
    name = scenario_name(energy_MWh, power_MW)
    cost_input = pd.DataFrame([{
        "scenario": name,
        "energy_capacity_MWh": float(energy_MWh),
        "power_capacity_MW": float(power_MW),
        "num_steps": len(dispatch),
        "time_step_hours": dt,
        "thermal_generation_MWh": physical["thermal_generation_MWh"],
        "curtailment_MWh": physical["curtailment_MWh"],
        "load_shedding_MWh": physical["unserved_MWh"],
        "storage_discharge_MWh": physical["discharge_MWh"],
        "renewable_utilization_pct": physical["renewable_utilization_pct"],
        "curtailment_rate_pct": 100 * physical["curtailment_MWh"] / available,
        "initial_inventory_supply_MWh": 0.0,
    }])
    costs = evaluate_system_costs(cost_input, economic_parameters)
    validate_cost_results(costs, economic_parameters)
    row = costs.iloc[0].to_dict()
    row.update({
        "solver_status": info["status"],
        "storage_utilization_pct": utilization,
        "storage_charge_MWh": physical["charge_MWh"],
        "operating_objective_CNY": info["objective_CNY"],
        "max_constraint_residual": max(residuals.values()),
    })
    return row, dispatch, info


def run_grid(data, base_storage, thermal, economic_parameters, dt, grid, independent_check=None,
             candidates=None):
    """Enumerate candidates in the supplied order and return summary and dispatches."""
    candidates = generate_candidates(grid) if candidates is None else list(candidates)
    if set(candidates) != set(generate_candidates(grid)) or len(candidates) != 101:
        raise ValueError("Candidate order may change, but candidate membership may not")
    rows, dispatches, details = [], {}, {}
    for energy, power in candidates:
        row, dispatch, info = solve_candidate(
            data, base_storage, thermal, economic_parameters, dt, energy, power, independent_check
        )
        name = row["scenario"]
        rows.append(row)
        dispatches[name] = dispatch
        details[name] = {
            "solver_status": info["status"],
            "objective_CNY": info["objective_CNY"],
            "max_constraint_residual": row["max_constraint_residual"],
            "precision_evidence": info["precision_evidence"],
        }
    summary = pd.DataFrame(rows).sort_values(["energy_capacity_MWh", "power_capacity_MW"]).reset_index(drop=True)
    if len(summary) != 101 or summary.scenario.nunique() != 101 or set(summary.solver_status) != {"Optimal"}:
        raise RuntimeError("U09 did not produce 101 unique Optimal candidates")
    return summary, dispatches, details


def with_robustness_costs(parameters, overrides):
    unknown = set(overrides) - set(parameters.__dataclass_fields__)
    if unknown:
        raise ValueError(f"Unknown economic overrides: {sorted(unknown)}")
    return replace(parameters, **overrides)


def select_best(summary):
    """Select the exact sampled minimum; expose all numerical ties to the caller."""
    minimum = float(summary.total_cost_CNY.min())
    tied = summary[np.isclose(summary.total_cost_CNY, minimum, atol=1e-6, rtol=0)].copy()
    best = tied.sort_values(["energy_capacity_MWh", "power_capacity_MW"]).iloc[0]
    return best, tied

