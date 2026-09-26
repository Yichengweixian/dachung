"""Read-only, separate-process audit of U11R04 LP and dispatch artifacts."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_study_artifacts import audit
from run_energy_calibrated_days_presolve_off import baseline_guard, CHANNELS
from run_budgeted_ga import saved_cost
from src.annual_clustering import annual_metrics
from src.energy_calibrated_weights_presolve_off import BAND, check_stage
from src.optimization_validation import summarize_dispatch
from src.representative_days import cluster_real_days, input_energy_errors, passing_sizes
from src.study_runtime import sha


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
    lp_count = dispatch_count = 0
    max_cost_diff = max_residual = 0.
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
                if q['stage'] != stage or q['pins'] != pins or q['t_limit'] != t_limit or q['l_limit'] != l_limit:
                    raise ValueError('Changed lexicographic bands/order')
                check_stage(a, b, c, q)
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
                  verdict=record['verdict'], audit_source_sha256=sha(Path(__file__)),
                  run_manifest_sha256=sha(folder/'run_manifest.json'))
    with (ROOT/args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

