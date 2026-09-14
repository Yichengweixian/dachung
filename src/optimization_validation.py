"""Independent numerical checks; deliberately imports no modeling code."""
import numpy as np


def validate(q, data, s, thermal, dt, terminal=True):
    if len(q) != len(data) or len(q) == 0:
        raise ValueError('Result length mismatch')
    residuals = {}
    def eq(name, a, b):
        residuals[name] = float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    def upper(name, a, b):
        residuals[name] = float(max(0., np.max(np.asarray(a)-np.asarray(b))))
    cols = ['thermal','wind_used','solar_used','wind_curt','solar_curt','charge','discharge','unserved','energy_start_MWh','energy_MWh']
    if not np.isfinite(q[cols].to_numpy()).all():
        raise ValueError('Nonfinite results')
    upper('nonnegative', 0, q[cols].to_numpy())
    for dest, source in [('hour','hour'),('load','load'),('wind_available','wind'),('solar_available','solar')]:
        eq('input_'+dest, q[dest], data[source])
    eq('balance', q.wind_used+q.solar_used+q.thermal+q.discharge+q.unserved, data.load.to_numpy()+q.charge)
    eq('wind_split', q.wind_used+q.wind_curt, data.wind)
    eq('solar_split', q.solar_used+q.solar_curt, data.solar)
    upper('thermal_min', thermal['min'], q.thermal)
    upper('thermal_max', q.thermal, thermal['max'])
    if len(q)>1 and thermal['ramp'] is not None:
        upper('ramp', np.abs(np.diff(q.thermal)), thermal['ramp']*dt)
    upper('unserved', q.unserved, data.load)
    for c in ['charge','discharge']:
        upper(c+'_limit', q[c], s['power_capacity_MW'])
    upper('mutual_exclusion', np.minimum(q.charge, q.discharge), 0)
    for c in ['energy_start_MWh','energy_MWh']:
        upper(c+'_low', s['soc_min']*s['energy_capacity_MWh'], q[c])
        upper(c+'_high', q[c], s['soc_max']*s['energy_capacity_MWh'])
    eq('initial', q.energy_start_MWh.iloc[0], s['soc_initial']*s['energy_capacity_MWh'])
    if len(q)>1:
        eq('continuity', q.energy_start_MWh.to_numpy()[1:], q.energy_MWh.to_numpy()[:-1])
    eq('recurrence', q.energy_MWh, q.energy_start_MWh+s['eta_charge']*q.charge*dt-q.discharge*dt/s['eta_discharge'])
    if terminal:
        eq('terminal', q.energy_MWh.iloc[-1], s['soc_initial']*s['energy_capacity_MWh'])
    if s['energy_capacity_MWh']:
        eq('soc', q.soc, q.energy_MWh/s['energy_capacity_MWh'])
    elif not q.soc.isna().all():
        raise ValueError('Zero storage SOC must be undefined')
    if any(not np.isfinite(x) or x >= 1e-6 for x in residuals.values()):
        raise ValueError(f'Constraint validation failed: {residuals}')
    return residuals


def summarize(q, c, dt):
    available = float((q.wind_available+q.solar_available).sum()*dt)
    used = float((q.wind_used+q.solar_used).sum()*dt)
    curt = float((q.wind_curt+q.solar_curt).sum()*dt)
    thermal, lost, discharge = (float(q[k].sum()*dt) for k in ['thermal','unserved','discharge'])
    return {'renewable_utilization_pct': 100*used/available if available else None,
            'curtailment_MWh': curt, 'thermal_generation_MWh': thermal, 'unserved_MWh': lost,
            'charge_MWh': float(q.charge.sum()*dt), 'discharge_MWh': discharge,
            'operating_cost_CNY': thermal*c['thermal_cost_CNY_per_MWh']+curt*c['curtailment_penalty_CNY_per_MWh']
              +lost*c['load_shedding_penalty_CNY_per_MWh']+discharge*c['storage_variable_om_CNY_per_MWh_discharged']}
