"""Run the frozen U11R03 matrix against a read-only audited annual baseline."""
import argparse
from dataclasses import asdict
import importlib.metadata
import json
from time import perf_counter
import numpy as np
import pandas as pd
from scripts.audit_study_artifacts import audit
from scripts.independent_dispatch_audit import audit_file
from src.annual_clustering import annual_metrics
from src.data_loader import load_input_data
from src.economic_model import evaluate_system_costs, validate_cost_results
from src.optimization_validation import audit_dispatch, summarize_dispatch
from src.representative_days import cluster_real_days, input_energy_errors, passing_sizes
from src.study_runtime import ROOT, StudyRun, configuration, dump


def check_baseline(data, cfg, s, t, e):
    folder = ROOT/'results/annual/U11R02-v01'
    report = audit(folder/'run_manifest.json')
    if not report['passed'] or report['source_drift_since_run']:
        raise ValueError(str(report))
    old = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    for name in ['storage', 'optimization', 'no_storage', 'economics']:
        if cfg[name] != old['freeze']['config'][name+'.json']:
            raise ValueError('Baseline configuration drift: '+name)
    rows, residuals = [], []
    saved_summary = pd.read_csv(folder/'daily_summary.csv').set_index('scenario')
    for d in range(365):
        name = f'day_{d:03d}'
        path = folder/(name+'_hourly.csv')
        q = pd.read_csv(path)
        source = data.iloc[d*24:(d+1)*24].copy()
        source.hour = np.arange(24)
        checks = audit_dispatch(q, source, s, t)
        if not checks['passed']:
            raise ValueError(str(checks))
        residuals.append(audit_file(path, s, t))
        row = summarize_dispatch(q, asdict(e)).iloc[0].to_dict()
        row.update(scenario=name, energy_capacity_MWh=s['energy_capacity_MWh'],
                   power_capacity_MW=s['power_capacity_MW'], num_steps=24, time_step_hours=1.,
                   load_shedding_MWh=row['unserved_MWh'], storage_discharge_MWh=row['discharge_MWh'],
                   initial_inventory_supply_MWh=max(0., float(q.energy_start_MWh.iloc[0]-q.energy_MWh.iloc[-1]))*s['eta_discharge'])
        costs = evaluate_system_costs(pd.DataFrame([row]), e)
        validate_cost_results(costs, e)
        row.update(costs.iloc[0].to_dict())
        for key in ['total_cost_CNY', 'renewable_available_MWh', 'renewable_used_MWh', 'curtailment_MWh',
                    'total_load_MWh', 'thermal_generation_MWh', 'unserved_MWh']:
            if abs(row[key]-saved_summary.loc[name, key]) >= 1e-6:
                raise ValueError('Daily aggregate mismatch: '+name+' '+key)
        rows.append(row)
    full = annual_metrics(rows, np.ones(365))
    saved = pd.read_csv(folder/'full_annual.csv').iloc[0]
    difference = max(abs(full[k]-saved[k]) for k in full)
    if difference >= 1e-6:
        raise ValueError('Annual aggregate mismatch')
    return full, dict(**report, audited_days=365, max_residual=max(residuals), annual_difference=difference)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='U11R03-v01')
    args = parser.parse_args()
    run = StudyRun('U11R03-amplitude-representative-days', 'annual', args.run_id)
    try:
        cfg, s, t, e = configuration()
        run.manifest['packages'].update({x:importlib.metadata.version(x) for x in ['scikit-learn', 'scipy', 'threadpoolctl']})
        data = load_input_data(ROOT/'results/annual/U11R02-v01/input_8760h.csv', 8760)
        full, report = check_baseline(data, cfg, s, t, e)
        dump(run.out/'baseline_audit.json', report)
        print('365-day baseline audit passed', flush=True)
        comparisons = []
        for seed in [42, 7, 2026]:
            for n in [12, 24, 48]:
                started = perf_counter()
                days, reps, labels = cluster_real_days(data, n, seed)
                clustering_seconds = perf_counter()-started
                prefix = f'N{n}_seed{seed}'
                reps.to_csv(run.out/(prefix+'_representatives.csv'), index=False, float_format='%.17g')
                pd.DataFrame(dict(day=np.arange(365), cluster=labels)).to_csv(run.out/(prefix+'_labels.csv'), index=False)
                pd.concat([day.assign(cluster=k) for k, day in enumerate(days)]).to_csv(run.out/(prefix+'_inputs.csv'), index=False, float_format='%.17g')
                rows = []
                for k, day in enumerate(days):
                    name = prefix+f'_cluster{k}'
                    _, row = run.case(name, day, s, t, e)
                    audit_file(run.out/(name+'_hourly.csv'), s, t)
                    rows.append(row)
                summary_path = run.out/(prefix+'_summary.csv')
                pd.DataFrame(rows).to_csv(summary_path, index=False, float_format='%.17g')
                metrics = annual_metrics(rows, reps.days)
                readback = annual_metrics(pd.read_csv(summary_path).to_dict('records'), reps.days)
                if max(abs(metrics[k]-readback[k]) for k in metrics) >= 1e-6:
                    raise ValueError('Summary readback mismatch')
                error = max(abs(metrics[k]-full[k]) for k in ['renewable_utilization_pct', 'curtailment_rate_pct'])
                comparisons.append(dict(N=n, seed=seed, clustering_seconds=clustering_seconds,
                                        worst_error_pp=error, cost_error_CNY=metrics['total_cost_CNY']-full['total_cost_CNY'],
                                        unserved_error_MWh=metrics['unserved_MWh']-full['unserved_MWh'],
                                        **metrics, **input_energy_errors(data, days, reps.days)))
                print(prefix, 'error_pp=', error, 'energy_error=', comparisons[-1]['max_input_relative_error'], flush=True)
        comparison = pd.DataFrame(comparisons)
        comparison.to_csv(run.out/'comparison.csv', index=False, float_format='%.17g')
        passing = passing_sizes(comparison)
        if len(run.manifest['cases']) != 252:
            raise ValueError('Wrong solve count')
        run.finish('supported' if passing else 'inconclusive', dict(solves=252, passing_N=passing,
                   selected_N=min(passing) if passing else None, baseline=report,
                   max_residual=max(c['max_residual'] for c in run.manifest['cases'].values())))
    except Exception as exc:
        run.manifest.update(status='blocked', verdict='invalid', error=repr(exc))
        dump(run.out/'failure.json', dict(error=repr(exc)))
        dump(run.out/'run_manifest.json', run.manifest)
        raise


if __name__ == '__main__':
    main()
