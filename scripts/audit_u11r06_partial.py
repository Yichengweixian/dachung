"""Verify a stopped U11R06 run without resuming or re-solving it."""
import argparse
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
from src.energy_calibrated_weights_presolve_off import check_stage
from src.representative_days import input_energy_errors
from src.study_runtime import sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_id')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    folder = ROOT/'results/annual'/args.run_id
    m = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    hashes = audit(folder/'run_manifest.json')
    if hashes['errors'] != ['not_complete'] or hashes['source_drift_since_run']:
        raise ValueError('Unexpected integrity failure: '+str(hashes))
    if m['status'] != 'blocked' or m['verdict'] != 'invalid':
        raise ValueError('Not a stopped invalid run')
    _, storage, thermal, economics = baseline_guard()
    data = pd.read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv', float_precision='round_trip')
    full = pd.read_csv(ROOT/'results/annual/U11R02-v01/full_annual.csv', float_precision='round_trip').iloc[0]
    comparison = pd.read_csv(folder/'comparison.csv', float_precision='round_trip')
    b = data[CHANNELS].sum().to_numpy()
    stages, failed, residuals = [], [], []
    group_evidence = []
    for input_path in sorted(folder.glob('N*_inputs.csv')):
        prefix = input_path.name.removesuffix('_inputs.csv')
        inputs = pd.read_csv(input_path, float_precision='round_trip')
        reps = pd.read_csv(ROOT/'results/annual/U11R03-v01'/(prefix+'_representatives.csv'), float_precision='round_trip')
        days = [inputs[inputs.cluster == i].drop(columns='cluster').reset_index(drop=True) for i in range(len(reps))]
        a = np.array([[d[c].sum() for d in days] for c in CHANNELS])
        for label in ['main', 'repeat']:
            records = []
            for stage in ['primary', 'secondary']+[f'lex_{i:03d}' for i in sorted(range(len(reps)), key=lambda i: reps.date_UTC.iloc[i])]:
                path = folder/(prefix+'_'+label+'_'+stage+'.json')
                if not path.exists():
                    break
                record = json.loads(path.read_text(encoding='utf-8'))
                stages.append(path.name)
                if 'Option for presolve changed from on to off' not in record.get('log', ''):
                    raise ValueError('Missing presolve-off evidence: '+path.name)
                if record.get('error'):
                    failed.append(dict(file=path.name, status=record['status'], error=record['error']))
                    if records:
                        # Read-only witness diagnostic: last accepted solution under the next bands.
                        witness = dict(records[-1], pins=record['pins'], t_limit=record['t_limit'], l_limit=record['l_limit'])
                        try:
                            failed[-1]['previous_solution_in_next_bands'] = check_stage(a, b, reps.days.to_numpy(), witness)
                        except ValueError as exc:
                            failed[-1]['previous_solution_in_next_bands'] = str(exc)
                    break
                if record['status'] != 'Optimal':
                    raise ValueError('Unrecorded nonoptimal status')
                residuals.append(check_stage(a, b, reps.days.to_numpy(), record))
                records.append(record)
        saved_reps = folder/(prefix+'_representatives.csv')
        if not saved_reps.exists():
            continue
        weights = pd.read_csv(saved_reps, float_precision='round_trip')
        np.testing.assert_allclose(weights.effective_days, weights.repeat_days, rtol=0, atol=1e-6)
        summary = pd.read_csv(folder/(prefix+'_summary.csv'), float_precision='round_trip')
        for i, day in enumerate(days):
            name = prefix+f'_cluster{i}'
            if name not in m['cases']:
                raise ValueError('Case not recorded')
            cost, physical_residual = saved_cost(folder/(name+'_hourly.csv'), day, storage, thermal, economics)
            if abs(cost-summary.iloc[i].total_cost_CNY) >= 1e-6:
                raise ValueError('Cost reconstruction mismatch')
            q = pd.read_csv(folder/(name+'_hourly.csv'), float_precision='round_trip')
            totals = dict(renewable_available_MWh=(q.wind_available+q.solar_available).sum(),
                          renewable_used_MWh=(q.wind_used+q.solar_used).sum(),
                          curtailment_MWh=(q.wind_curt+q.solar_curt).sum(), total_load_MWh=q.load.sum(),
                          thermal_generation_MWh=q.thermal.sum(), unserved_MWh=q.unserved.sum())
            for key, value in totals.items():
                if abs(value-summary.iloc[i][key]) >= 1e-6:
                    raise ValueError('Hourly total mismatch')
        n, seed = (int(x) for x in prefix.replace('N', '').split('_seed'))
        row = comparison[(comparison.N == n) & (comparison.seed == seed)].iloc[0]
        metrics = annual_metrics(summary.to_dict('records'), weights.effective_days)
        errors = input_energy_errors(data, days, weights.effective_days)
        for key, value in {**metrics, **errors}.items():
            if abs(value-row[key]) >= 1e-6:
                raise ValueError('Partial aggregate mismatch')
        epp = max(abs(metrics[k]-full[k]) for k in ['renewable_utilization_pct', 'curtailment_rate_pct'])
        if abs(epp-row.worst_error_pp) >= 1e-6:
            raise ValueError('Partial E mismatch')
        group_evidence.append(dict(N=n, seed=seed, ratio_error_pp=epp, input_energy_error=errors['max_input_relative_error'],
                                   dispatch_cases=len(days), cost_error_CNY=metrics['total_cost_CNY']-full.total_cost_CNY))
    if len(stages) != m['lp_calls'] or len(failed) != 1 or sum(g['dispatch_cases'] for g in group_evidence) != m['dispatch_calls']:
        raise ValueError('Partial call count mismatch')
    if len(list(folder.glob('N*_main_*.json'))) + len(list(folder.glob('N*_repeat_*.json'))) != len(stages):
        raise ValueError('Unaccounted LP stage')
    result = dict(evidence_integrity_passed=True, research_valid=False, research_verdict='invalid',
                  hashes=hashes, lp_attempts=len(stages), optimal_lp_stages=len(residuals),
                  dispatch_cases=m['dispatch_calls'], completed_groups=group_evidence, failures=failed,
                  max_weight_bound_residual=max(r['bounds_residual'] for r in residuals),
                  max_normalized_residual=max(r['normalized_residual'] for r in residuals),
                  new_solver_calls=0, run_manifest_sha256=sha(folder/'run_manifest.json'),
                  audit_source_sha256=sha(Path(__file__)))
    with (ROOT/args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

