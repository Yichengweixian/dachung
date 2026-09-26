"""U11R04 frozen, bounded lexicographic calibration of effective day counts."""
from time import perf_counter
import numpy as np
import pulp
from .cbc_presolve_off import FullPrecisionCBC

BAND = 1e-9


def validate_inputs(energy, target, counts, dates):
    a, b, c = (np.asarray(x, dtype=float) for x in (energy, target, counts))
    if (a.shape != (3, len(c)) or b.shape != (3,) or c.ndim != 1 or not len(c)
            or len(dates) != len(c) or len(set(dates)) != len(c)):
        raise ValueError('Invalid dimensions/dates')
    if not all(np.isfinite(x).all() for x in (a, b, c)) or (a < 0).any() or (b < 0).any() or (c <= 0).any():
        raise ValueError('Invalid energy/counts')
    if abs(c.sum() - 365) > 1e-12 or not np.equal(c, np.floor(c)).all():
        raise ValueError('Counts must be integer days totaling 365')
    if np.any(a[b == 0] != 0):
        raise ValueError('Zero annual channel has nonzero representative input')
    return a, b, c


def check_stage(a, b, c, record):
    """Recompute primal and frozen-band residuals from exported values."""
    w = np.asarray(record['weights'], dtype=float)
    t, deviations = float(record['t']), np.asarray(record['deviations'], dtype=float)
    if (len(w) != len(c) or len(deviations) != len(c)
            or not np.isfinite(np.r_[w, t, deviations]).all()):
        raise ValueError('Nonfinite or incomplete LP solution')
    bounds = max(float(np.max(.5*c-w)), float(np.max(w-2*c)), abs(float(w.sum())-365), 0.)
    errors = [max(0., -t), max(0., float(np.max(-deviations))),
              max(0., float(np.max(np.abs(w-c)/c-deviations)))]
    for k in np.flatnonzero(b > 0):
        errors.append(max(0., abs(float(a[k] @ w / b[k]-1))-t))
    if record['t_limit'] is not None:
        errors.append(max(0., t-record['t_limit']))
    if record['l_limit'] is not None:
        errors.append(max(0., float(deviations.sum())-record['l_limit']))
    for pin in record['pins']:
        errors.append(max(0., pin['lower']-w[pin['index']], w[pin['index']]-pin['upper']))
    if bounds > 1e-6 or max(errors) > 1e-7:
        raise ValueError(f'Weight LP residuals: bounds={bounds}, normalized={max(errors)}')
    return dict(bounds_residual=bounds, normalized_residual=max(errors))


def calibrate(energy, target, counts, dates, on_stage=None, model_directory=None):
    a, b, c = validate_inputs(energy, target, counts, dates)
    model = pulp.LpProblem('U11R06_energy_weights', pulp.LpMinimize)
    w = [pulp.LpVariable(f'w_{i:03d}', .5*v, 2*v) for i, v in enumerate(c)]
    d = [pulp.LpVariable(f'd_{i:03d}', 0) for i in range(len(c))]
    t = pulp.LpVariable('worst_relative_error', 0)
    model += pulp.lpSum(w) == 365, 'total_days'
    for i in range(len(c)):
        model += d[i] >= (w[i]-c[i])/c[i]
        model += d[i] >= (c[i]-w[i])/c[i]
    for k in np.flatnonzero(b > 0):
        relative = pulp.lpSum(float(a[k, i]/b[k])*w[i] for i in range(len(c)))-1
        model += relative <= t
        model += -relative <= t
    records, pins = [], []
    t_limit = l_limit = None

    def solve(label, objective):
        model.setObjective(objective)
        if model_directory is not None:
            model.writeLP(str(model_directory / (label+'.lp')))
        solver = FullPrecisionCBC(msg=False)
        record = dict(stage=label, t_limit=t_limit, l_limit=l_limit,
                      pins=[dict(p) for p in pins], status='attempted')
        start = perf_counter()
        try:
            model.solve(solver)
            record.update(status=pulp.LpStatus[model.status], solution_status=model.sol_status,
                          seconds=perf_counter()-start, log=getattr(solver, 'log', ''))
            if model.status != pulp.LpStatusOptimal or model.sol_status != pulp.LpSolutionOptimal:
                raise RuntimeError('Weight CBC did not prove Optimal: '+record['status'])
            record.update(weights=[float(pulp.value(v)) for v in w], t=float(pulp.value(t)),
                          deviations=[float(pulp.value(v)) for v in d],
                          objective=float(pulp.value(objective)))
            record.update(check_stage(a, b, c, record))
        except Exception as exc:
            record.update(error=repr(exc), seconds=perf_counter()-start, log=getattr(solver, 'log', ''))
            raise
        finally:
            records.append(record)
            if on_stage is not None:
                on_stage(record)
        return record

    primary = solve('primary', t)
    t_limit = primary['objective'] + BAND
    model += t <= t_limit, 'primary_optimum_band'
    secondary = solve('secondary', pulp.lpSum(d))
    l_limit = secondary['objective'] + BAND
    model += pulp.lpSum(d) <= l_limit, 'secondary_optimum_band'
    for i in sorted(range(len(c)), key=lambda j: dates[j]):
        record = solve(f'lex_{i:03d}', w[i])
        value = record['weights'][i]
        pin = dict(index=i, lower=max(.5*c[i], value-BAND), upper=min(2*c[i], value+BAND))
        pins.append(pin)
        model += w[i] >= pin['lower']
        model += w[i] <= pin['upper']
    return np.asarray(records[-1]['weights']), records

