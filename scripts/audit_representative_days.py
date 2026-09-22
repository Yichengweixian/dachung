"""Read back U11R03 inputs, membership, physical solutions and decision table."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.audit_study_artifacts import audit
from scripts.independent_dispatch_audit import audit_file
from src.annual_clustering import annual_metrics
from src.optimization_validation import audit_dispatch
from src.representative_days import cluster_real_days, input_energy_errors, passing_sizes
from src.study_runtime import configuration, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_id')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    folder = ROOT/'results/annual'/args.run_id
    record = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    hashes = audit(folder/'run_manifest.json')
    if not hashes['passed'] or hashes['source_drift_since_run']:
        raise ValueError(str(hashes))
    data = pd.read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv')
    full = pd.read_csv(ROOT/'results/annual/U11R02-v01/full_annual.csv').iloc[0]
    compare = pd.read_csv(folder/'comparison.csv')
    _, s, t, _ = configuration()
    residuals = []
    for result in compare.itertuples():
        prefix = f'N{result.N}_seed{result.seed}'
        days, reps, labels = cluster_real_days(data, result.N, result.seed)
        saved_reps = pd.read_csv(folder/(prefix+'_representatives.csv'))
        pd.testing.assert_frame_equal(reps, saved_reps, check_exact=False, atol=1e-12, rtol=0)
        np.testing.assert_array_equal(labels, pd.read_csv(folder/(prefix+'_labels.csv')).cluster)
        saved_inputs = pd.read_csv(folder/(prefix+'_inputs.csv'))
        rows = pd.read_csv(folder/(prefix+'_summary.csv'))
        for k, day in enumerate(days):
            np.testing.assert_allclose(saved_inputs[saved_inputs.cluster == k][day.columns], day, atol=1e-12, rtol=0)
            path = folder/(prefix+f'_cluster{k}_hourly.csv')
            q = pd.read_csv(path)
            checks = audit_dispatch(q, day, s, t)
            if not checks['passed']:
                raise ValueError(str(checks))
            residuals.append(audit_file(path, s, t))
            for col, values in [('renewable_available_MWh', q.wind_available+q.solar_available),
                                ('renewable_used_MWh', q.wind_used+q.solar_used),
                                ('curtailment_MWh', q.wind_curt+q.solar_curt),
                                ('total_load_MWh', q.load), ('unserved_MWh', q.unserved)]:
                if abs(values.sum()-rows.iloc[k][col]) >= 1e-6:
                    raise ValueError('Hourly total mismatch')
        metrics = annual_metrics(rows.to_dict('records'), reps.days)
        for key, value in metrics.items():
            if abs(value-getattr(result, key)) >= 1e-6:
                raise ValueError('Comparison total mismatch')
        errors = input_energy_errors(data, days, reps.days)
        for key, value in errors.items():
            if abs(value-getattr(result, key)) >= 1e-6:
                raise ValueError('Input energy mismatch')
        error = max(abs(metrics[k]-full[k]) for k in ['renewable_utilization_pct', 'curtailment_rate_pct'])
        if abs(error-result.worst_error_pp) >= 1e-6:
            raise ValueError('Ratio error mismatch')
    passing = passing_sizes(compare)
    if len(residuals) != 252 or record['verdict'] != ('supported' if passing else 'inconclusive'):
        raise ValueError('Decision mismatch')
    report = dict(passed=True, hashes=hashes, solver_cases=len(residuals), max_residual=max(residuals),
                  groups=len(compare), passing_N=passing, verdict=record['verdict'],
                  audit_source_sha256=sha(Path(__file__)), run_manifest_sha256=sha(folder/'run_manifest.json'))
    with (ROOT/args.output).open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
