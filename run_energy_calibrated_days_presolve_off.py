"""Execute U11R04 without modifying any historical experiment directory."""
import argparse
import importlib.metadata
import json
from time import perf_counter
import numpy as np
import pandas as pd
from run_budgeted_ga import saved_cost
from src.annual_clustering import annual_metrics
from src.data_loader import load_input_data
from src.energy_calibrated_weights_presolve_off import calibrate
from src.representative_days import cluster_real_days, input_energy_errors, passing_sizes
from src.study_runtime import ROOT, StudyRun, configuration, dump, sha

CHANNELS = ['load', 'wind', 'solar']
PRECHECK = 'results/annual/U11R04-isolated-preflight-v02/audit.json'


def baseline_guard():
    evidence = json.loads((ROOT/PRECHECK).read_text(encoding='utf-8'))
    if not evidence['passed'] or not evidence['representatives']['passed']:
        raise ValueError('Isolated baseline audit not passed')
    if evidence['baseline']['audit']['annual_difference'] >= 1e-6 or evidence['costs']['max_cost_difference'] >= 1e-6:
        raise ValueError('Baseline reconstruction failed')
    restored = {r['path'] for r in evidence['restored']}
    if restored != {'scripts/check_materials_numbers.py'}:
        raise ValueError('Unexpected historical restoration')
    for rel, expected in evidence['required_sha256'].items():
        # This one non-computational source was audited, hash-exact, in isolation.
        # Its current version is separately pinned in this run's source_sha256.
        if rel not in restored and sha(ROOT/rel) != expected:
            raise ValueError('Historical input/computation drift: '+rel)
    cfg, s, t, e = configuration()
    for run_id in ['U11R02-v01', 'U11R03-v01']:
        manifest = json.loads((ROOT/'results/annual'/run_id/'run_manifest.json').read_text(encoding='utf-8'))
        for key in ['storage', 'optimization', 'no_storage', 'economics']:
            if cfg[key] != manifest['freeze']['config'][key+'.json']:
                raise ValueError('Historical configuration mismatch: '+key)
    return cfg, s, t, e


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='U11R06-v01')
    args = parser.parse_args()
    run = StudyRun('U11R06-presolve-off-weight-matrix', 'annual', args.run_id)
    start = perf_counter()
    lp_calls = dispatch_calls = 0
    try:
        cfg, s, t, e = baseline_guard()
        packages = {p: importlib.metadata.version(p) for p in ['numpy', 'pandas', 'pulp', 'scikit-learn', 'scipy', 'threadpoolctl']}
        expected = dict(numpy='2.5.3', pandas='3.0.5', pulp='3.3.0', **{'scikit-learn':'1.9.1', 'scipy':'1.18.1', 'threadpoolctl':'3.7.0'})
        if packages != expected:
            raise ValueError('Frozen environment version mismatch')
        run.manifest['packages'].update(packages)
        data = load_input_data(ROOT/'results/annual/U11R02-v01/input_8760h.csv', 8760)
        full = pd.read_csv(ROOT/'results/annual/U11R02-v01/full_annual.csv', float_precision='round_trip').iloc[0]
        old = pd.read_csv(ROOT/'results/annual/U11R03-v01/comparison.csv', float_precision='round_trip')
        comparisons = []
        for seed in [42, 7, 2026]:
            for n in [12, 24, 48]:
                group_start = perf_counter()
                prefix = f'N{n}_seed{seed}'
                days, reps, labels = cluster_real_days(data, n, seed)
                original = ROOT/'results/annual/U11R03-v01'
                pd.testing.assert_frame_equal(reps, pd.read_csv(original/(prefix+'_representatives.csv')), check_exact=False, atol=1e-12, rtol=0)
                np.testing.assert_array_equal(labels, pd.read_csv(original/(prefix+'_labels.csv')).cluster)
                a = np.array([[day[c].sum() for day in days] for c in CHANNELS])
                b = data[CHANNELS].sum().to_numpy()
                pd.concat([day.assign(cluster=k) for k, day in enumerate(days)]).to_csv(run.out/(prefix+'_inputs.csv'), index=False, float_format='%.17g')
                pd.DataFrame(dict(day=np.arange(365), cluster=labels)).to_csv(run.out/(prefix+'_labels.csv'), index=False)
                weights = []
                for label in ['main', 'repeat']:
                    directory = run.out/(prefix+'_'+label+'_models')
                    directory.mkdir()
                    def record_stage(record):
                        nonlocal lp_calls
                        lp_calls += 1
                        dump(run.out/(prefix+'_'+label+'_'+record['stage']+'.json'), record)
                        run.manifest['lp_calls'] = lp_calls
                        dump(run.out/'run_manifest.json', run.manifest)
                    w, records = calibrate(a, b, reps.days.to_numpy(), reps.date_UTC.tolist(), record_stage, directory)
                    weights.append(w)
                difference = float(np.max(np.abs(weights[0]-weights[1])))
                if difference > 1e-6:
                    raise ValueError('Nonrepeatable calibrated weights')
                w = weights[0]
                reps = reps.assign(effective_days=w, effective_probability=w/365, repeat_days=weights[1])
                reps.to_csv(run.out/(prefix+'_representatives.csv'), index=False, float_format='%.17g')
                rows = []
                for k, day in enumerate(days):
                    name = prefix+f'_cluster{k}'
                    dispatch_calls += 1
                    _, row = run.case(name, day, s, t, e)
                    cost, _ = saved_cost(run.out/(name+'_hourly.csv'), day, s, t, e)
                    if abs(cost-row['total_cost_CNY']) >= 1e-6:
                        raise ValueError('Exported cost mismatch')
                    rows.append(row)
                summary = run.out/(prefix+'_summary.csv')
                pd.DataFrame(rows).to_csv(summary, index=False, float_format='%.17g')
                rows = pd.read_csv(summary, float_precision='round_trip').to_dict('records')
                control = annual_metrics(rows, reps.days)
                prior = old[(old.N == n) & (old.seed == seed)].iloc[0]
                delta = max(abs(control[k]-prior[k]) for k in control)
                if delta >= 1e-6:
                    raise ValueError('Uncalibrated control differs from U11R03')
                metrics = annual_metrics(rows, w)
                errors = input_energy_errors(data, days, w)
                signed = {c+'_signed_relative_error': float((a[k] @ w-b[k])/b[k]) if b[k] else 0. for k, c in enumerate(CHANNELS)}
                result = dict(N=n, seed=seed, **metrics, **errors, **signed,
                              worst_error_pp=max(abs(metrics[k]-full[k]) for k in ['renewable_utilization_pct', 'curtailment_rate_pct']),
                              cost_error_CNY=metrics['total_cost_CNY']-full['total_cost_CNY'],
                              unserved_error_MWh=metrics['unserved_MWh']-full['unserved_MWh'],
                              control_max_difference=delta, repeat_max_difference=difference,
                              lower_bound_count=int(np.sum(np.abs(w-.5*reps.days.to_numpy()) <= 1e-6)),
                              upper_bound_count=int(np.sum(np.abs(w-2*reps.days.to_numpy()) <= 1e-6)),
                              max_weight_ratio=float(np.max(w/reps.days.to_numpy())),
                              effective_sample_size=float(w.sum()**2/(w@w)), seconds=perf_counter()-group_start)
                result.update({'control_'+k:v for k,v in control.items()})
                result.update({'control_'+k:v for k,v in input_energy_errors(data, days, reps.days).items()})
                comparisons.append(result)
                pd.DataFrame(comparisons).to_csv(run.out/'comparison.csv', index=False, float_format='%.17g')
                print(prefix, 'E_pp=', result['worst_error_pp'], 'D=', errors['max_input_relative_error'], flush=True)
        table = pd.DataFrame(comparisons)
        passing = passing_sizes(table)
        if lp_calls != 540 or dispatch_calls != 252:
            raise ValueError('Wrong solve budget')
        run.finish('supported' if passing else 'inconclusive', dict(lp_calls=lp_calls, dispatch_calls=dispatch_calls,
                   passing_N=passing, selected_N=min(passing) if passing else None, seconds=perf_counter()-start))
    except Exception as exc:
        run.manifest.update(status='blocked', verdict='invalid', error=repr(exc))
        dump(run.out/'failure.json', dict(error=repr(exc), lp_calls=lp_calls, dispatch_calls=dispatch_calls))
        raise
    finally:
        run.manifest.update(lp_calls=lp_calls, dispatch_calls=dispatch_calls, elapsed_seconds=perf_counter()-start)
        run.manifest['artifacts'] = {p.relative_to(run.out).as_posix(): sha(p) for p in run.out.rglob('*') if p.is_file() and p.name != 'run_manifest.json'}
        dump(run.out/'run_manifest.json', run.manifest)


if __name__ == '__main__':
    main()

