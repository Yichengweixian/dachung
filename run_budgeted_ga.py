"""U12R02: serial 89-call searches, saved-solution cost audit and repeat."""
import argparse
from dataclasses import asdict
import json
from time import perf_counter
import numpy as np
import pandas as pd
from scripts.audit_study_artifacts import audit
from scripts.independent_dispatch_audit import audit_file
from src.budgeted_ga import SEEDS, PARAMETERS, search, decision
from src.economic_model import evaluate_system_costs, validate_cost_results
from src.grid_search import evaluate_candidate, generate_candidates
from src.optimization_validation import audit_dispatch, summarize_dispatch
from src.study_runtime import ROOT, StudyRun, configuration, dump, sha


def saved_cost(path, data, storage, thermal, economics):
    q = pd.read_csv(path, float_precision='round_trip')
    checks = audit_dispatch(q, data, storage, thermal)
    if not checks['passed']:
        raise ValueError(str(checks))
    audit_file(path, storage, thermal)
    row = summarize_dispatch(q, asdict(economics)).iloc[0].to_dict()
    row.update(scenario='audit', energy_capacity_MWh=storage['energy_capacity_MWh'],
               power_capacity_MW=storage['power_capacity_MW'], num_steps=24, time_step_hours=1.,
               load_shedding_MWh=row['unserved_MWh'], storage_discharge_MWh=row['discharge_MWh'],
               initial_inventory_supply_MWh=max(0., float(q.energy_start_MWh.iloc[0]-q.energy_MWh.iloc[-1]))*storage['eta_discharge'])
    costs = evaluate_system_costs(pd.DataFrame([row]), economics)
    validate_cost_results(costs, economics)
    return float(costs.total_cost_CNY.iloc[0]), checks['max_residual']


def baseline(data, cfg, s, t, e):
    folder = ROOT/'results/grid_search/U09R01-v01'
    report = audit(folder/'run_manifest.json')
    if not report['passed'] or report['source_drift_since_run']:
        raise ValueError(str(report))
    for rel in ['results/grid_search/U09R01-v01', 'results/ga/U12R01-v01']:
        m = json.loads((ROOT/rel/'run_manifest.json').read_text(encoding='utf-8'))
        for key in ['storage', 'optimization', 'no_storage', 'economics']:
            if cfg[key] != m['freeze']['config'][key+'.json']:
                raise ValueError('Configuration mismatch')
    grid = pd.read_csv(folder/'summary.csv', float_precision='round_trip')
    expected = set(generate_candidates(range(0, 101, 10), range(5, 51, 5)))
    if len(grid) != 101 or set(zip(grid.energy_capacity_MWh, grid.power_capacity_MW)) != expected:
        raise ValueError('Grid candidate mismatch')
    differences = []
    for row in grid.itertuples():
        st = dict(s, energy_capacity_MWh=row.energy_capacity_MWh, power_capacity_MW=row.power_capacity_MW)
        cost, _ = saved_cost(folder/('main_'+row.scenario+'_hourly.csv'), data, st, t, e)
        differences.append(abs(cost-row.total_cost_CNY))
    if max(differences) >= 1e-6:
        raise ValueError('Grid cost mismatch')
    return float(grid.total_cost_CNY.min()), dict(**report, audited_candidates=101, max_cost_difference=max(differences))


def audit_run(folder):
    cfg, s, t, e = configuration()
    data = pd.read_csv(ROOT/'data/input_24h.csv')
    hashes = audit(folder/'run_manifest.json')
    if not hashes['passed'] or hashes['source_drift_since_run']:
        raise ValueError(str(hashes))
    m = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    max_difference = 0.
    for label, seed in [(f'seed{s}', s) for s in SEEDS]+[('repeat42', 42)]:
        history = pd.read_csv(folder/(label+'_convergence.csv'), float_precision='round_trip')
        if list(history.evaluation) != list(range(1, 90)):
            raise ValueError('Sequence mismatch')
        for row in history.itertuples():
            st = dict(s, energy_capacity_MWh=row.energy, power_capacity_MW=row.power)
            cost, _ = saved_cost(folder/(f'{label}_eval{row.evaluation:04d}_hourly.csv'), data, st, t, e)
            max_difference = max(max_difference, abs(cost-row.cost))
        cursor = 0
        def replay(xs, generation):
            nonlocal cursor
            saved = history.iloc[cursor:cursor+len(xs)]
            np.testing.assert_array_equal(xs, saved[['energy', 'power']].to_numpy())
            if not (saved.generation == generation).all():
                raise ValueError('Generation mismatch')
            cursor += len(xs)
            return saved.cost.to_numpy()
        _, _, replayed = search(replay, seed)
        np.testing.assert_allclose([r['best_cost'] for r in replayed], history.best_cost, atol=1e-6, rtol=0)
    if max_difference >= 1e-6:
        raise ValueError('Saved cost mismatch')
    first = pd.read_csv(folder/'seed42_convergence.csv', float_precision='round_trip')
    repeat = pd.read_csv(folder/'repeat42_convergence.csv', float_precision='round_trip')
    np.testing.assert_array_equal(first[['energy', 'power']], repeat[['energy', 'power']])
    difference = float(np.max(np.abs(first[['cost', 'best_cost']].to_numpy()-repeat[['cost', 'best_cost']].to_numpy())))
    if difference >= 1e-6:
        raise ValueError('Independent repeat mismatch')
    table = pd.read_csv(folder/'summary.csv')
    checked, verdict = decision(table, m['details']['grid_cost'])
    if verdict != m['verdict'] or len(m['cases']) != 979:
        raise ValueError('Decision mismatch')
    for row in table.itertuples():
        h = pd.read_csv(folder/f'seed{row.seed}_convergence.csv')
        if abs(h.cost.min()-row.cost) >= 1e-6:
            raise ValueError('Summary mismatch')
    return dict(passed=True, hashes=hashes, calls=979, primary_calls=890, repeat_calls=89,
                max_cost_difference=max_difference, repeat_difference=difference,
                successful_seeds=int(checked.passed.sum()), verdict=verdict,
                audit_source_sha256=sha(__file__), manifest_sha256=sha(folder/'run_manifest.json'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', default='U12R02-v01')
    p.add_argument('--audit-output')
    a = p.parse_args()
    if a.audit_output:
        report = audit_run(ROOT/'results/ga'/a.run_id)
        with (ROOT/a.audit_output).open('x', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(report, flush=True)
        return
    run = StudyRun('U12R02-budgeted-ga', 'ga', a.run_id)
    try:
        cfg, s, t, e = configuration()
        data = pd.read_csv(ROOT/'data/input_24h.csv')
        benchmark, report = baseline(data, cfg, s, t, e)
        dump(run.out/'baseline_audit.json', report)
        run.manifest['parameters'] = dict(PARAMETERS, seeds=SEEDS, repeat_seed=42)
        summaries, trajectories = [], {}
        for label, seed in [(f'seed{s}', s) for s in SEEDS]+[('repeat42', 42)]:
            count = 0
            started = perf_counter()
            def batch(xs, generation):
                nonlocal count
                values = []
                for x in xs:
                    count += 1
                    name = f'{label}_eval{count:04d}'
                    q, row, info = evaluate_candidate(data, s, t, e, *x)
                    path = run.out/(name+'_hourly.csv')
                    q.to_csv(path, index=False, float_format='%.17g')
                    st = dict(s, energy_capacity_MWh=float(x[0]), power_capacity_MW=float(x[1]))
                    cost, residual = saved_cost(path, data, st, t, e)
                    if abs(cost-row['total_cost_CNY']) >= 1e-6:
                        raise ValueError('Cost readback mismatch')
                    (run.out/(name+'_cbc.log')).write_text(info.pop('cbc_log'), encoding='utf-8')
                    run.manifest['cases'][name] = dict(**info, storage=st, thermal=t, dt=1., terminal=True, max_residual=residual)
                    values.append(row['total_cost_CNY'])
                return values
            def progress(generation, evaluations, best, history):
                pd.DataFrame(history).to_csv(run.out/(label+'_convergence.csv'), index=False, float_format='%.17g')
            best, cost, history = search(batch, seed, progress)
            trajectories[label] = pd.DataFrame(history)
            if count != 89:
                raise ValueError('Wrong objective count')
            row = dict(seed=seed, energy=best[0], power=best[1], cost=cost, evaluations=count, wall_seconds=perf_counter()-started)
            if label != 'repeat42':
                summaries.append(row)
            else:
                dump(run.out/'repeat_summary.json', row)
            print(label, 'calls', count, 'cost', cost, flush=True)
        first, repeat = trajectories['seed42'], trajectories['repeat42']
        np.testing.assert_array_equal(first[['energy', 'power']], repeat[['energy', 'power']])
        difference = float(np.max(np.abs(first[['cost', 'best_cost']].to_numpy()-repeat[['cost', 'best_cost']].to_numpy())))
        if difference >= 1e-6:
            raise ValueError('Repeat mismatch')
        table, verdict = decision(pd.DataFrame(summaries), benchmark)
        table.to_csv(run.out/'summary.csv', index=False, float_format='%.17g')
        run.finish(verdict, dict(grid_cost=benchmark, successful_seeds=int(table.passed.sum()),
                   primary_calls=890, repeat_calls=89, total_calls=len(run.manifest['cases']), repeat_difference=difference,
                   mean_cost=float(table.cost.mean()), median_cost=float(table.cost.median()),
                   range_cost=float(table.cost.max()-table.cost.min()), evaluation_reduction_fraction=12/101))
    except Exception as exc:
        run.manifest.update(status='blocked', verdict='invalid', error=repr(exc))
        dump(run.out/'failure.json', dict(error=repr(exc)))
        dump(run.out/'run_manifest.json', run.manifest)
        raise


if __name__ == '__main__':
    main()
