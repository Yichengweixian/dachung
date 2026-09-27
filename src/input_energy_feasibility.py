"""U11R08: one minimax LP per saved representative-day set; no dispatch."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import traceback

import numpy as np
import pandas as pd
import scipy
import scipy.optimize as optimize

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ['load', 'wind', 'solar']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def read_csv(path):
    return pd.read_csv(path, float_precision='round_trip')


def create_run_directory(base, run_id):
    if not re.fullmatch(r'U11R08-[A-Za-z0-9_-]+', run_id):
        raise ValueError('run_id must be a simple U11R08-... name')
    out = Path(base) / run_id
    out.mkdir(parents=True, exist_ok=False)
    return out


def build_model(energy, target, counts):
    a, b, c = (np.asarray(x, dtype=float) for x in (energy, target, counts))
    if c.ndim != 1 or not len(c) or a.shape != (3, len(c)) or b.shape != (3,):
        raise ValueError('Invalid model dimensions')
    if not all(np.isfinite(x).all() for x in (a, b, c)) or (a < 0).any() or (b < 0).any():
        raise ValueError('Nonfinite or negative input energy')
    if (c <= 0).any() or not np.equal(c, np.floor(c)).all() or math.fsum(c) != 365:
        raise ValueError('Counts must be positive integer days totaling 365')
    if np.any(a[b == 0] != 0):
        raise ValueError('Zero annual channel has nonzero representative energy')
    rows, rhs = [], []
    for k in range(3):
        if b[k] > 0:
            rows.extend([np.r_[a[k] / b[k], -1].tolist(), np.r_[-a[k] / b[k], -1].tolist()])
            rhs.extend([1., -1.])
    return dict(energy=a.tolist(), target=b.tolist(), counts=c.tolist(), channels=CHANNELS,
                objective=[0.] * len(c) + [1.], A_ub=rows, b_ub=rhs,
                A_eq=[[1.] * len(c) + [0.]], b_eq=[365.],
                bounds=[[.5 * v, 2 * v] for v in c] + [[0., None]])


def check_solution(model, weights, t):
    c = np.asarray(model['counts'])
    w = np.asarray(weights, dtype=float)
    if w.shape != c.shape or not np.isfinite(w).all() or not math.isfinite(t):
        raise ValueError('Incomplete or nonfinite weights/t')
    weighted = [math.fsum(float(a) * float(v) for a, v in zip(row, w)) for row in model['energy']]
    signed = []
    for value, target in zip(weighted, model['target']):
        if target == 0:
            if value != 0:
                raise ValueError('Nonzero energy for zero target')
            signed.append(0.)
        else:
            signed.append(value / target - 1.)
    errors = [abs(x) for x in signed]
    bound = max(0., float(np.max(.5 * c - w)), float(np.max(w - 2 * c)))
    total = math.fsum(w)
    normalized = max(0., -t, max(errors) - t)
    report = dict(passed=bound <= 1e-7 and abs(total - 365) <= 1e-7 and normalized <= 1e-8,
                  bound_residual=bound, sum_residual=abs(total - 365), weight_sum=total,
                  normalized_residual=normalized, weighted_MWh=weighted,
                  signed_relative_errors=signed, absolute_relative_errors=errors,
                  max_input_relative_error=max(errors))
    if not report['passed']:
        raise ValueError('Constraint audit failed: ' + str(report))
    return report


def solve_lp(model):
    result = optimize.linprog(model['objective'], A_ub=model['A_ub'] or None,
                              b_ub=model['b_ub'] or None, A_eq=model['A_eq'], b_eq=model['b_eq'],
                              bounds=model['bounds'], method='highs-ds',
                              options={'presolve': True, 'primal_feasibility_tolerance': 1e-9,
                                       'dual_feasibility_tolerance': 1e-9, 'time_limit': 60., 'disp': True})
    record = dict(success=bool(result.success), status=int(result.status), message=result.message,
                  iterations=int(result.nit), scipy_version=scipy.__version__)
    if result.success and result.status == 0:
        record.update(weights=result.x[:-1].tolist(), t=float(result.x[-1]), objective=float(result.fun),
                      inequality_marginals=result.ineqlin.marginals.tolist(),
                      equality_marginals=result.eqlin.marginals.tolist(),
                      lower_marginals=result.lower.marginals.tolist(), upper_marginals=result.upper.marginals.tolist())
    return record


def invoke_worker(model_path, solution_path):
    command = [sys.executable, str(ROOT / 'run_u11r08_feasibility.py'),
               '--worker', str(model_path), '--solution', str(solution_path)]
    try:
        process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                                 errors='replace', timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        log = process.stdout + process.stderr
        if process.returncode != 0 or not solution_path.exists():
            return dict(success=False, status=-1, message=f'Worker exit {process.returncode}'), log
        return json.loads(solution_path.read_text('utf-8')), log
    except subprocess.TimeoutExpired as exc:
        def decode(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        return dict(success=False, status=-1, message='Worker timeout'), decode(exc.stdout) + decode(exc.stderr)


def save_weights(path, counts, weights, days, dates):
    frame = pd.DataFrame(dict(cluster=range(len(counts)), day=days, date_UTC=dates, c=counts, w=weights))
    frame.to_csv(path, index=False, float_format='%.17g', lineterminator='\n')
    readback = read_csv(path).w.to_numpy()
    if not np.array_equal(readback, np.asarray(weights)):
        raise ValueError('Native weights changed in CSV round trip')
    return readback


def execute_case(model, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    stage = 'model'
    try:
        dump(out / 'model.json', model)
        c = model['counts']
        original_t = max(abs(math.fsum(x * w for x, w in zip(a, c)) / b - 1) if b else 0.
                         for a, b in zip(model['energy'], model['target']))
        original = check_solution(model, c, original_t)
        dump(out / 'original_feasible_point.json', dict(weights=c, t=original_t, audit=original))
        stage = 'primary_lp'
        solution, log = invoke_worker(out / 'model.json', out / 'solution.json')
        (out / 'solver.log').write_text(log, encoding='utf-8')
        dump(out / 'solution.json', solution)
        if solution.get('status') != 0 or solution.get('success') is not True:
            raise RuntimeError('Primary LP not reliably Optimal: ' + str(solution))
        stage = 'native_solution_audit'
        checks = check_solution(model, solution['weights'], solution['t'])
        stage = 'csv_readback'
        readback = save_weights(out / 'weights.csv', c, solution['weights'],
                                model.get('days', list(range(len(c)))), model.get('dates', [''] * len(c)))
        reread = check_solution(model, readback, solution['t'])
        dump(out / 'constraints.json', dict(original=original, solution=checks, readback=reread))
        pd.DataFrame(dict(channel=CHANNELS, target_MWh=model['target'], weighted_MWh=reread['weighted_MWh'],
                          signed_relative_error=reread['signed_relative_errors'],
                          absolute_relative_error=reread['absolute_relative_errors'])).to_csv(
                              out / 'energy_errors.csv', index=False, float_format='%.17g', lineterminator='\n')
        return solution, checks
    except Exception as exc:
        dump(out / 'failure.json', dict(category='numerical_or_implementation_problem', stage=stage,
                                       error=repr(exc), traceback=traceback.format_exc(),
                                       mathematical_unreachability_claim=False))
        raise


def load_saved_groups(root=ROOT):
    """Verify saved membership and hourly curves without invoking clustering."""
    annual_path = root / 'results/annual/U11R02-v01/input_8760h.csv'
    full = read_csv(annual_path)
    values = full[CHANNELS].to_numpy()
    if len(full) != 8760 or not np.array_equal(full.hour, np.arange(8760)):
        raise ValueError('Annual hour axis must be 0..8759')
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Invalid annual data')
    targets = [math.fsum(full[k]) for k in CHANNELS]
    source = root / 'results/annual/U11R03-v01'
    groups = []
    for n in [12, 24, 48]:
        for seed in [42, 7, 2026]:
            prefix = f'N{n}_seed{seed}'
            reps = read_csv(source / f'{prefix}_representatives.csv')
            inputs = read_csv(source / f'{prefix}_inputs.csv')
            labels = read_csv(source / f'{prefix}_labels.csv')
            if len(reps) != n or not np.array_equal(reps.cluster, np.arange(n)) or len(inputs) != n * 24:
                raise ValueError('Incomplete representative set: ' + prefix)
            if len(labels) != 365 or not np.array_equal(labels.day, np.arange(365)):
                raise ValueError('Invalid labels: ' + prefix)
            if set(labels.cluster) != set(range(n)) or len(set(reps.day)) != n:
                raise ValueError('Invalid cluster/day identity: ' + prefix)
            energy = np.zeros((3, n))
            for rep in reps.itertuples():
                if int(rep.day) != rep.day or not 0 <= rep.day < 365 or labels.cluster.iloc[int(rep.day)] != rep.cluster:
                    raise ValueError('Representative outside saved cluster')
                expected_date = (pd.Timestamp('2023-01-01') + pd.Timedelta(days=int(rep.day))).strftime('%Y-%m-%d')
                if rep.date_UTC != expected_date or int((labels.cluster == rep.cluster).sum()) != rep.days:
                    raise ValueError('Date/count mismatch')
                if abs(rep.weight - rep.days / 365) > 1e-15:
                    raise ValueError('Original probability differs from cluster days')
                day = inputs[inputs.cluster == rep.cluster]
                if len(day) != 24 or not np.array_equal(day.hour, np.arange(24)):
                    raise ValueError('Representative hour axis mismatch')
                original = values[int(rep.day) * 24:(int(rep.day) + 1) * 24]
                if not np.array_equal(day[CHANNELS].to_numpy(), original):
                    raise ValueError('Saved curve differs from annual original')
                energy[:, rep.cluster] = [math.fsum(day[k]) for k in CHANNELS]
            model = build_model(energy, targets, reps.days)
            model.update(N=n, seed=seed, dates=reps.date_UTC.tolist(), days=reps.day.tolist(), unit='MWh', time_step_hours=1.)
            groups.append(model)
    return groups


def saved_dispatch_diagnostic(model, weights, root=ROOT):
    source = root / 'results/annual/U11R03-v01'
    prefix = f"N{model['N']}_seed{model['seed']}"
    summary = read_csv(source / f'{prefix}_summary.csv')
    totals = {key: [] for key in ['renewable_available_MWh', 'renewable_used_MWh', 'curtailment_MWh']}
    for i in range(model['N']):
        q = read_csv(source / f'{prefix}_cluster{i}_hourly.csv')
        if len(q) != 24 or summary.iloc[i].solver_status != 'Optimal':
            raise ValueError('Incomplete saved dispatch')
        for k, qcol in [('load', 'load'), ('wind', 'wind_available'), ('solar', 'solar_available')]:
            if abs(math.fsum(q[qcol]) - model['energy'][CHANNELS.index(k)][i]) > 1e-8:
                raise ValueError('Saved dispatch input energy mismatch')
        for key, cols in [('renewable_available_MWh', ['wind_available', 'solar_available']),
                          ('renewable_used_MWh', ['wind_used', 'solar_used']),
                          ('curtailment_MWh', ['wind_curt', 'solar_curt'])]:
            value = math.fsum(float(v) for col in cols for v in q[col])
            if abs(value - summary.iloc[i][key]) >= 1e-6:
                raise ValueError('Saved dispatch summary mismatch')
            totals[key].append(value)
    weighted = {key: math.fsum(x * w for x, w in zip(values, weights)) for key, values in totals.items()}
    available = weighted['renewable_available_MWh']
    if available <= 0:
        raise ValueError('Supplementary renewable ratio undefined')
    ratios = dict(renewable_utilization_pct=100 * weighted['renewable_used_MWh'] / available,
                  curtailment_rate_pct=100 * weighted['curtailment_MWh'] / available)
    baseline = read_csv(root / 'results/annual/U11R02-v01/full_annual.csv').iloc[0]
    daily = read_csv(root / 'results/annual/U11R02-v01/daily_summary.csv')
    base_avail = math.fsum(daily.renewable_available_MWh)
    for key, energy in [('renewable_utilization_pct', 'renewable_used_MWh'), ('curtailment_rate_pct', 'curtailment_MWh')]:
        if abs(100 * math.fsum(daily[energy]) / base_avail - baseline[key]) >= 1e-6:
            raise ValueError('Saved annual ratio reconstruction mismatch')
    error = float(max(abs(ratios[key] - baseline[key]) for key in ratios))
    return dict(**weighted, **ratios, worst_error_pp=error, ratio_pass=error <= 1., dispatch_solves=0)
