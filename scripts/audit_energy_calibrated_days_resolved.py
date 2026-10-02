"""Read-only, separate-process audit of U11R08 full matrix and CBC evidence."""
import argparse
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path
import struct
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_study_artifacts import audit
from scripts.diagnose_u11r06_serialization import decimal_residuals, read_mps
from run_energy_calibrated_days_resolved import baseline_guard, CHANNELS
from run_budgeted_ga import saved_cost
from src.annual_clustering import annual_metrics
from src.energy_calibrated_weights_resolved import BAND, check_stage
from src.optimization_validation import summarize_dispatch
from src.representative_days import cluster_real_days, input_energy_errors, passing_sizes
from src.study_runtime import sha


def audit_solver_evidence(directory, record):
    process = json.loads((directory/'process.json').read_text(encoding='utf-8'))
    expected = ['model.mps', '-primalTolerance', '1e-9', '-integerTolerance', '1e-9',
                '-ratioGap', '0', '-allowableGap', '0', '-threads', '0', '-presolve', 'off', '-branch',
                '-printingOptions', 'all', '-solution', 'solution.txt', '-saveSolution', 'solution.bin', '-quit']
    if process['command'][1:] != expected or process['returncode'] != 0 or process['timeout_seconds'] != 60:
        raise ValueError('CBC command or exit mismatch')
    if sha(Path(process['command'][0])) != sha(ROOT/'.venv/Lib/site-packages/pulp/solverdir/cbc/win/i64/cbc.exe'):
        raise ValueError('CBC executable mismatch')
    if (directory/'stdout.txt').read_text(encoding='utf-8') != record['log']:
        raise ValueError('CBC log mismatch')
    if not (directory/'solution.txt').read_text(encoding='utf-8').startswith('Optimal'):
        raise ValueError('CBC text status not Optimal')
    mapping = json.loads((directory/'mapping.json').read_text(encoding='utf-8'))
    raw = (directory/'solution.bin').read_bytes()
    rows, columns = struct.unpack_from('=ii', raw)
    if rows != mapping['rows'] or columns != mapping['columns'] or len(raw) != 16+16*(rows+columns):
        raise ValueError('CBC native layout mismatch')
    native_objective = struct.unpack_from('=d', raw, 8)[0]
    primal = struct.unpack_from(f'={columns}d', raw, 16+16*rows)
    if not np.isfinite(primal).all() or abs(native_objective-record['objective']) >= 1e-6:
        raise ValueError('CBC native objective mismatch')
    values = dict(zip(mapping['original_variable_order'], primal))
    expected_values = {f'w_{i:03d}': x for i, x in enumerate(record['weights'])}
    expected_values.update({f'd_{i:03d}': x for i, x in enumerate(record['deviations'])})
    expected_values['worst_relative_error'] = record['t']
    if values != expected_values:
        raise ValueError('CBC native variables differ from exported stage')
    mr, rhs, senses, bounds = read_mps(directory/'model.mps')
    if len(mr)-1 != rows or len(bounds) != columns:
        raise ValueError('MPS dimensions mismatch')
    mapped = {mapping['variables'][name]: Decimal.from_float(x) for name, x in values.items()}
    residuals = decimal_residuals(mr, rhs, senses, mapped, bounds)
    total_days = mapping['constraints']['total_days']
    for row in residuals:
        tolerance = Decimal('1e-6') if row['row'] == total_days or row['sense'] == 'bounds' else Decimal('1e-7')
        if Decimal(row['violation']) > tolerance:
            raise ValueError('Saved MPS solution residual: '+str(row))
    return float(max(Decimal(r['violation']) for r in residuals))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run_id')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    folder = ROOT/'results/annual'/args.run_id
    report = audit(folder/'run_manifest.json')
    if not report['passed'] or report['source_drift_since_run']:
        raise ValueError(str(report))
    record = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    cfg, s, t, e = baseline_guard()
    data = pd.read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv', float_precision='round_trip')
    full = pd.read_csv(ROOT/'results/annual/U11R02-v01/full_annual.csv', float_precision='round_trip').iloc[0]
    old = pd.read_csv(ROOT/'results/annual/U11R03-v01/comparison.csv', float_precision='round_trip')
    compare = pd.read_csv(folder/'comparison.csv', float_precision='round_trip')
    if sorted(zip(compare.N, compare.seed)) != sorted((n, seed) for n in [12, 24, 48] for seed in [42, 7, 2026]):
        raise ValueError('Incomplete or duplicated matrix')
    if record.get('weight_lp_settings') != dict(fixed_band=1e-6, presolve='off', primal_tolerance=1e-9) or BAND != 1e-6:
        raise ValueError('Frozen numerical settings mismatch')
    lp_count = dispatch_count = 0
    max_cost_diff = max_residual = 0.
    max_mps_residual = max_weight_bound_residual = max_lp_normalized_residual = 0.
    for result in compare.to_dict('records'):
        n, seed = int(result['N']), int(result['seed'])
        prefix = f'N{n}_seed{seed}'
        days, reps, labels = cluster_real_days(data, n, seed)
        saved = pd.read_csv(folder/(prefix+'_representatives.csv'), float_precision='round_trip')
        pd.testing.assert_frame_equal(reps, saved[reps.columns], atol=1e-12, rtol=0)
        np.testing.assert_array_equal(labels, pd.read_csv(folder/(prefix+'_labels.csv')).cluster)
        a = np.array([[d[c].sum() for d in days] for c in CHANNELS])
        b = data[CHANNELS].sum().to_numpy()
        c = reps.days.to_numpy()
        stage_names = ['primary', 'secondary']+[f'lex_{i:03d}' for i in sorted(range(n), key=lambda i: reps.date_UTC.iloc[i])]
        endings = []
        for label in ['main', 'repeat']:
            pins, t_limit, l_limit = [], None, None
            for index, stage in enumerate(stage_names):
                q = json.loads((folder/(prefix+'_'+label+'_'+stage+'.json')).read_text(encoding='utf-8'))
                if q['status'] != 'Optimal' or q.get('error') or q['solution_status'] != 1:
                    raise ValueError('Invalid LP stage')
                if 'Option for presolve changed from on to off' not in q['log']:
                    raise ValueError('Weight LP presolve-off evidence missing')
                if q.get('band') != BAND:
                    raise ValueError('Changed stage fixed band')
                if q['stage'] != stage or q['pins'] != pins or q['t_limit'] != t_limit or q['l_limit'] != l_limit:
                    raise ValueError('Changed lexicographic bands/order')
                checked = check_stage(a, b, c, q)
                max_weight_bound_residual = max(max_weight_bound_residual, checked['bounds_residual'])
                max_lp_normalized_residual = max(max_lp_normalized_residual, checked['normalized_residual'])
                directory = folder/(prefix+'_'+label+'_models')/(stage+'_cbc')
                max_mps_residual = max(max_mps_residual, audit_solver_evidence(directory, q))
                objective = q['t'] if index == 0 else (sum(q['deviations']) if index == 1 else q['weights'][int(stage[4:])])
                if abs(q['objective']-objective) > 1e-7:
                    raise ValueError('LP objective mismatch')
                if index == 0:
                    t_limit = objective+BAND
                elif index == 1:
                    l_limit = objective+BAND
                else:
                    i = int(stage[4:])
                    pins.append(dict(index=i, lower=max(.5*c[i], objective-BAND), upper=min(2*c[i], objective+BAND)))
                lp_count += 1
            endings.append(q['weights'])
        np.testing.assert_allclose(endings[0], endings[1], atol=1e-6, rtol=0)
        np.testing.assert_array_equal(saved.effective_days, endings[0])
        np.testing.assert_array_equal(saved.repeat_days, endings[1])
        np.testing.assert_allclose(saved.effective_probability, saved.effective_days/365, atol=1e-15, rtol=0)
        exported = pd.read_csv(folder/(prefix+'_inputs.csv'), float_precision='round_trip')
        summary = pd.read_csv(folder/(prefix+'_summary.csv'), float_precision='round_trip')
        rows = []
        for k, day in enumerate(days):
            np.testing.assert_allclose(exported[exported.cluster == k][day.columns], day, atol=1e-12, rtol=0)
            path = folder/(prefix+f'_cluster{k}_hourly.csv')
            cost, residual = saved_cost(path, day, s, t, e)
            q = pd.read_csv(path, float_precision='round_trip')
            row = summarize_dispatch(q, asdict(e)).iloc[0].to_dict()
            row['total_cost_CNY'] = cost
            for key in ['renewable_available_MWh', 'renewable_used_MWh', 'curtailment_MWh', 'total_load_MWh', 'thermal_generation_MWh', 'unserved_MWh', 'total_cost_CNY']:
                if abs(row[key]-summary.iloc[k][key]) >= 1e-6:
                    raise ValueError('Daily reconstruction mismatch: '+key)
            rows.append(row)
            max_cost_diff = max(max_cost_diff, abs(cost-summary.iloc[k].total_cost_CNY))
            max_residual = max(max_residual, residual)
            dispatch_count += 1
        metrics = annual_metrics(rows, saved.effective_days)
        controls = annual_metrics(rows, reps.days)
        prior = old[(old.N == n) & (old.seed == seed)].iloc[0]
        for key, value in controls.items():
            if abs(value-prior[key]) >= 1e-6 or abs(value-result['control_'+key]) >= 1e-6:
                raise ValueError('Historical control mismatch')
        errors = input_energy_errors(data, days, saved.effective_days)
        for key, value in {**metrics, **errors}.items():
            if abs(value-result[key]) >= 1e-6:
                raise ValueError('Annual reconstruction mismatch: '+key)
        E = max(abs(metrics[k]-full[k]) for k in ['renewable_utilization_pct', 'curtailment_rate_pct'])
        if abs(E-result['worst_error_pp']) >= 1e-6:
            raise ValueError('E mismatch')
    passing = passing_sizes(compare)
    if lp_count != 540 or dispatch_count != 252 or record['lp_calls'] != lp_count or record['dispatch_calls'] != dispatch_count:
        raise ValueError('Call count mismatch')
    if record['verdict'] != ('supported' if passing else 'inconclusive') or record['details']['passing_N'] != passing:
        raise ValueError('Verdict mismatch')
    result = dict(passed=True, hashes=report, weight_lp_calls=lp_count, dispatch_calls=dispatch_count,
                  max_residual=max_residual, max_cost_difference=max_cost_diff, passing_N=passing,
                  max_weight_bound_residual=max_weight_bound_residual, max_lp_normalized_residual=max_lp_normalized_residual,
                  max_mps_residual=max_mps_residual, fixed_band=BAND, new_solver_calls=0,
                  verdict=record['verdict'], audit_source_sha256=sha(Path(__file__)),
                  run_manifest_sha256=sha(folder/'run_manifest.json'))
    with (ROOT/args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
