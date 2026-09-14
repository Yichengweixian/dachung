"""MILP dispatch; no result files or validation logic in this module."""
import numpy as np
import pandas as pd
import pulp
from .data_loader import validate_input_data
from .storage_model import StorageParameters
from .cbc_precision import PreciseCBC


def solve_dispatch(data, storage, thermal, economics, dt=1., terminal=True):
    validate_input_data(data, time_step_hours=dt)
    s = StorageParameters(**storage)
    minimum, maximum, ramp = (thermal[k] for k in ('min', 'max', 'ramp'))
    if not (np.isfinite([minimum, maximum]).all() and 0 <= minimum <= maximum):
        raise ValueError('Invalid thermal bounds')
    if ramp is not None and (not np.isfinite(ramp) or ramp < 0):
        raise ValueError('Invalid ramp')
    costs = [economics[k] for k in ('thermal_cost_CNY_per_MWh', 'curtailment_penalty_CNY_per_MWh',
                                   'load_shedding_penalty_CNY_per_MWh', 'storage_variable_om_CNY_per_MWh_discharged')]
    if not np.isfinite(costs).all() or min(costs) < 0:
        raise ValueError('Invalid costs')
    n = len(data)
    m = pulp.LpProblem('U06_dispatch', pulp.LpMinimize)
    v = {k: [pulp.LpVariable(f'{k}_{i}', lowBound=0) for i in range(n)]
         for k in ['thermal', 'wind_used', 'solar_used', 'wind_curt', 'solar_curt', 'charge', 'discharge', 'unserved']}
    energy = [pulp.LpVariable(f'energy_{i}', s.soc_min*s.energy_capacity_MWh,
                             s.soc_max*s.energy_capacity_MWh) for i in range(n+1)]
    mode = [pulp.LpVariable(f'charge_mode_{i}', cat='Binary') for i in range(n)]
    m += energy[0] == s.soc_initial*s.energy_capacity_MWh
    if terminal:
        m += energy[-1] == energy[0]
    for i, row in enumerate(data.itertuples(index=False)):
        x = {k: vals[i] for k, vals in v.items()}
        m += x['thermal'] >= minimum
        m += x['thermal'] <= maximum
        if i and ramp is not None:
            m += x['thermal']-v['thermal'][i-1] <= ramp*dt
            m += v['thermal'][i-1]-x['thermal'] <= ramp*dt
        m += x['wind_used']+x['wind_curt'] == row.wind
        m += x['solar_used']+x['solar_curt'] == row.solar
        m += x['unserved'] <= row.load
        m += x['charge'] <= s.power_capacity_MW*mode[i]
        m += x['discharge'] <= s.power_capacity_MW*(1-mode[i])
        m += energy[i+1] == energy[i]+s.eta_charge*x['charge']*dt-x['discharge']*dt/s.eta_discharge
        m += x['wind_used']+x['solar_used']+x['thermal']+x['discharge']+x['unserved'] == row.load+x['charge']
    m += pulp.lpSum(dt*(costs[0]*v['thermal'][i]+costs[1]*(v['wind_curt'][i]+v['solar_curt'][i])
                       +costs[2]*v['unserved'][i]+costs[3]*v['discharge'][i]) for i in range(n))
    solver = PreciseCBC(msg=False, gapRel=0, gapAbs=0, threads=1,
                               options=['primalTolerance 1e-9', 'integerTolerance 1e-9'])
    m.solve(solver)
    status = pulp.LpStatus[m.status]
    if status != 'Optimal' or m.sol_status != pulp.LpSolutionOptimal:
        raise RuntimeError(f'Solver did not prove Optimal: {status}, {m.sol_status}')
    out = data.rename(columns={'wind': 'wind_available', 'solar': 'solar_available'}).reset_index(drop=True).copy()
    for k, vals in v.items():
        out[k] = [pulp.value(x) for x in vals]
    out['energy_start_MWh'] = [pulp.value(x) for x in energy[:-1]]
    out['energy_MWh'] = [pulp.value(x) for x in energy[1:]]
    out['soc'] = out.energy_MWh/s.energy_capacity_MWh if s.energy_capacity_MWh else np.nan
    out['balance_error_MW'] = out.wind_used+out.solar_used+out.thermal+out.discharge+out.unserved-out.load-out.charge
    return out, {'status': status, 'objective_CNY': pulp.value(m.objective), 'cbc_path': solver.path,
                 'precision_evidence':solver.precision_evidence}
