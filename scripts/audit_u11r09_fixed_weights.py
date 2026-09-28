"""Read-only R09 evidence audit. Standard library only; never invokes a solver."""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

if __package__:
    from .independent_dispatch_audit import audit_file
else:
    from independent_dispatch_audit import audit_file

ROOT = Path(__file__).resolve().parents[1]
UNIT = 'U11R09-fixed-weight-dual-threshold'
NS = (12, 24, 48)
SEEDS = (42, 7, 2026)
CHANNELS = ('load', 'wind', 'solar')
RATES = ('renewable_utilization_pct', 'curtailment_rate_pct')
ENERGY = {'total_load_MWh': ('load',), 'renewable_available_MWh': ('wind_available', 'solar_available'),
          'renewable_used_MWh': ('wind_used', 'solar_used'), 'curtailment_MWh': ('wind_curt', 'solar_curt'),
          'thermal_generation_MWh': ('thermal',), 'unserved_MWh': ('unserved',),
          'charge_MWh': ('charge',), 'discharge_MWh': ('discharge',)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def safe_path(root, relative):
    root = Path(root).resolve()
    result = (root / relative).resolve()
    require(result.is_relative_to(root), f'Path outside evidence root: {relative}')
    return result


def verify_hashes(root, hashes):
    require(bool(hashes), 'Empty hash inventory')
    for relative, digest in hashes.items():
        path = safe_path(root, relative)
        require(path.is_file() and sha(path) == digest, f'Hash mismatch: {relative}')
    return len(hashes)


def close(actual, expected, label, tolerance=1e-6):
    actual, expected = float(actual), float(expected)
    require(math.isfinite(actual) and math.isfinite(expected) and abs(actual - expected) < tolerance,
            f'{label}: {actual!r} != {expected!r}')


def aggregate(rows, weights):
    require(len(rows) == len(weights) and bool(rows), 'Mismatched aggregate rows/weights')
    require(all(math.isfinite(w) and w >= 0 for w in weights), 'Invalid weights')
    keys = [k for k in rows[0] if k.endswith('_MWh') or k.endswith('_CNY')]
    totals = {k: math.fsum(float(row[k]) * w for row, w in zip(rows, weights)) for k in keys}
    require(all(math.isfinite(v) for v in totals.values()), 'Nonfinite aggregate')
    available = totals['renewable_available_MWh']
    require(available > 0, 'Renewable rates undefined with zero available energy')
    totals[RATES[0]] = 100 * totals['renewable_used_MWh'] / available
    totals[RATES[1]] = 100 * totals['curtailment_MWh'] / available
    return totals


def relative_error(energy, weights, target):
    require(len(energy) == len(weights), 'Mismatched input energy')
    require(math.isfinite(target) and target >= 0 and all(math.isfinite(x) and x >= 0 for x in energy),
            'Invalid input energy')
    total = math.fsum(w * a for w, a in zip(weights, energy))
    if target == 0:
        require(all(a == 0 for a in energy), 'Nonzero representative channel with zero target')
        return total, 0.
    return total, abs(total / target - 1.)


def decide(rows):
    expected = {(n, seed) for n in NS for seed in SEEDS}
    keys = [(int(r['N']), int(r['seed'])) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        return 'invalid', []
    if any(not math.isfinite(float(r[k])) or float(r[k]) < 0 for r in rows for k in ('D', 'E_pp')):
        return 'invalid', []
    if any(float(r['D']) > .02 for r in rows):
        return 'invalid', []
    passing = [n for n in NS if all(float(r['E_pp']) <= 1. for r in rows if int(r['N']) == n)]
    return ('supported' if passing else 'inconclusive'), passing


def summarize(rows, storage, costs, dt=1.):
    require(len(rows) == 24 and dt == 1., 'Expected 24 one-hour dispatch steps')
    q = [{k: float(v) for k, v in row.items()} for row in rows]
    require(all(math.isfinite(v) for row in q for v in row.values()), 'Nonfinite saved dispatch')
    totals = {key: math.fsum(math.fsum(r[c] for r in q) for c in columns) * dt
              for key, columns in ENERGY.items()}
    totals = aggregate([totals], [1.])
    capex = 1000 * (storage['energy_capacity_MWh'] * costs['storage_energy_capex_CNY_per_kWh']
                    + storage['power_capacity_MW'] * costs['storage_power_capex_CNY_per_kW'])
    rate, years = costs['discount_rate'], costs['storage_lifetime_years']
    crf = rate / -math.expm1(-years * math.log1p(rate)) if rate else 1 / years
    allocated = capex * crf * 24 / costs['hours_per_year']
    fixed = capex * costs['storage_fixed_om_fraction_per_year'] * 24 / costs['hours_per_year']
    variable = totals['discharge_MWh'] * costs['storage_variable_om_CNY_per_MWh_discharged']
    thermal = totals['thermal_generation_MWh'] * costs['thermal_cost_CNY_per_MWh']
    curtailment = totals['curtailment_MWh'] * costs['curtailment_penalty_CNY_per_MWh']
    shedding = totals['unserved_MWh'] * costs['load_shedding_penalty_CNY_per_MWh']
    totals.update(operating_cost_CNY=thermal + curtailment + shedding + variable,
                  total_cost_CNY=thermal + allocated + fixed + variable + curtailment + shedding,
                  thermal_cost_CNY=thermal, curtailment_cost_CNY=curtailment,
                  load_shedding_cost_CNY=shedding, storage_cost_CNY=allocated + fixed + variable,
                  storage_investment_allocated_CNY=allocated, storage_fixed_om_CNY=fixed,
                  storage_variable_om_CNY=variable, storage_om_cost_CNY=fixed + variable)
    return totals


def verify_inputs(rows, inputs, label):
    require(len(rows) == len(inputs) == 24, f'{label}: input length')
    for q, source in zip(rows, inputs):
        for output, original in (('hour', 'hour'), ('load', 'load'), ('wind_available', 'wind'),
                                 ('solar_available', 'solar')):
            require(float(q[output]) == float(source[original]), f'{label}: input {original} changed')


def verify_daily(folder, name, info, inputs, storage, thermal, costs, new=False):
    require(info['storage'] == storage and info['thermal'] == thermal and info['dt'] == 1.
            and info['terminal'] is True, f'{name}: configuration mismatch')
    require(info['solver_status'] == 'Optimal' and info['model_class'] == 'MILP'
            and info['integer_variable_count'] == 24, f'{name}: invalid solver metadata')
    path = folder / (name + '_hourly.csv')
    rows = read_csv(path)
    verify_inputs(rows, inputs, name)
    residual = audit_file(path, storage, thermal, 1., True)
    require(float(info['max_residual']) < 1e-6, f'{name}: reported residual')
    log = (folder / (name + '_cbc.log')).read_text(encoding='utf-8')
    require('Result - Optimal solution found' in log, f'{name}: CBC status missing')
    if new:
        require(re.search(r'24 integer \(24 of which binary\)', log) is not None,
                f'{name}: CBC integer count missing')
        lp = (folder / (name + '_model.lp')).read_text(encoding='utf-8')
        mps = (folder / (name + '_model.mps')).read_text(encoding='utf-8')
        require('Binaries' in lp and 'INTORG' in mps, f'{name}: MILP model evidence missing')
        binaries = lp.split('Binaries', 1)[1].split('End', 1)[0].split()
        require(set(binaries) == {f'charge_mode_{i:04d}' for i in range(24)} and len(binaries) == 24,
                f'{name}: binary variable inventory')
        checks = read_json(folder / (name + '_checks.json'))
        require(checks['passed'] is True and checks['max_residual'] < 1e-6, f'{name}: checks failed')
    totals = summarize(rows, storage, costs)
    close(totals['operating_cost_CNY'], info['objective_CNY'], name + ': objective')
    if new:
        close(totals['operating_cost_CNY'], info['precision']['native_objective'], name + ': native objective')
    return rows, totals, residual


def audit(root, run_id):
    root = Path(root)
    require(re.fullmatch(r'U11R09-v\d+', run_id) is not None, 'Invalid run ID')
    out = root / 'results/annual' / run_id
    manifest_path = out / 'run_manifest.json'
    manifest_hash = sha(manifest_path)
    manifest = read_json(manifest_path)
    require(manifest['status'] == 'awaiting_independent_audit' and manifest['verdict'] is None,
            'Main run must await independent audit')
    require(manifest['run_id'] == run_id and manifest['unit'] == UNIT, 'Run identity mismatch')
    freeze_path = root / 'instructions/studies' / UNIT / 'freeze.json'
    freeze = read_json(freeze_path)
    require(manifest['freeze_sha256'] == sha(freeze_path) and manifest['freeze'] == freeze,
            'Freeze mismatch')
    hashes = {'freeze': verify_hashes(root, freeze['sha256']),
              'source': verify_hashes(root, manifest['source_sha256']),
              'artifacts': verify_hashes(out, manifest['artifacts'])}
    require(hashes['freeze'] == 1644, 'Incomplete frozen source inventory')
    required_sources = {p.relative_to(root).as_posix() for p in (root / 'src').glob('*.py')}
    required_sources |= {'run_u11r09_fixed_weights.py', 'scripts/audit_u11r09_fixed_weights.py',
                         'scripts/finalize_u11r09.py', 'scripts/independent_dispatch_audit.py'}
    require(required_sources <= set(manifest['source_sha256']), 'Missing source hashes')
    actual = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()
              and p.name not in ('run_manifest.json', 'completion.json')}
    require(actual == set(manifest['artifacts']), 'Main artifact inventory incomplete')
    r08 = root / 'results/annual/U11R08-v02'
    prior = read_json(r08 / 'run_manifest.json')
    report = read_json(r08 / 'independent_audit/report.json')
    require(report['main_manifest_sha256'] == sha(r08 / 'run_manifest.json'), 'R08 manifest link')
    require(report['freeze_sha256'] == sha(root / 'instructions/studies/U11R08-input-energy-feasibility/freeze.json'),
            'R08 freeze link')
    require(report['audit_source_sha256'] == sha(root / 'scripts/audit_u11r08_feasibility.py'), 'R08 audit source')
    hashes['R08_artifacts'] = verify_hashes(r08, prior['artifacts'])
    hashes['R08_audit_artifacts'] = verify_hashes(r08 / 'independent_audit', report['artifacts'])
    require(hashes['R08_audit_artifacts'] == 72, 'R08 audit inventory incomplete')
    require(report['verdict'] == 'supported' and len(report['groups']) == 9 and {(g['N'], g['seed']) for g in report['groups']} ==
            {(n, s) for n in NS for s in SEEDS} and all(g['status'] == 'reachable' for g in report['groups']),
            'R08 groups not reachable')
    r02 = root / 'results/annual/U11R02-v01'
    r03 = root / 'results/annual/U11R03-v01'
    base_manifest = read_json(r02 / 'run_manifest.json')
    config = base_manifest['freeze']['config']
    other_config = read_json(r03 / 'run_manifest.json')['freeze']['config']
    storage = config['storage.json']
    thermal = {k: config['optimization.json'][k] for k in ('thermal_min_MW', 'thermal_ramp_MW_per_h')}
    thermal['thermal_max_MW'] = config['no_storage.json']['thermal_max_MW']
    costs = config['economics.json']['parameters']
    for name in ('storage.json', 'economics.json', 'no_storage.json', 'optimization.json'):
        require(config[name] == other_config[name] == freeze['config'][name] == read_json(root / 'config' / name),
                f'Config {name}')
    current_opt = read_json(root / 'config/optimization.json')
    for key in ('thermal_min_MW', 'thermal_ramp_MW_per_h'):
        require(thermal[key] == other_config['optimization.json'][key] == current_opt[key], f'Config {key}')
    full_inputs = read_csv(r02 / 'input_8760h.csv')
    require(len(full_inputs) == 8760 and all(int(r['hour']) == i for i, r in enumerate(full_inputs)),
            'Incomplete annual inputs')
    targets = {c: math.fsum(float(r[c]) for r in full_inputs) for c in CHANNELS}
    base_summaries = read_csv(r02 / 'daily_summary.csv')
    require(len(base_summaries) == 365, 'Incomplete baseline summary')
    baseline_totals, baseline_residuals = [], {}
    for day in range(365):
        name = f'day_{day:03d}'
        inputs = [{**r, 'hour': h} for h, r in enumerate(full_inputs[day * 24:(day + 1) * 24])]
        _, total, residual = verify_daily(r02, name, base_manifest['cases'][name], inputs, storage, thermal, costs)
        require(base_summaries[day]['scenario'] == name, f'Baseline summary ordering: {name}')
        for key, value in total.items():
            close(base_summaries[day][key], value, f'{name}: {key}')
        baseline_totals.append(total)
        baseline_residuals[name] = residual
    baseline = aggregate(baseline_totals, [1.] * 365)
    full_annual = read_csv(r02 / 'full_annual.csv')
    require(len(full_annual) == 1, 'Invalid full_annual')
    for key, value in full_annual[0].items():
        close(value, baseline[key], 'Baseline annual ' + key)
    baseline_saved = read_json(out / 'baseline_audit.json')
    require(baseline_saved['passed'] is True and baseline_saved['days'] == 365
            and baseline_saved['max_residual'] < 1e-6 and baseline_saved['annual_difference'] < 1e-6,
            'Main baseline audit failed')
    for key, value in baseline_saved['annual'].items():
        close(value, baseline[key], 'Main baseline annual ' + key)
    expected_cases = {f'N{n}_seed{s}_cluster{i}' for n in NS for s in SEEDS for i in range(n)}
    expected_cases |= {f'N{n}_seed{s}_repeat_cluster0' for n in NS for s in SEEDS}
    require(set(manifest['cases']) == expected_cases, 'Incomplete dispatch matrix')
    comparisons = read_csv(out / 'comparison.csv')
    require(len(comparisons) == 9 and {(int(r['N']), int(r['seed'])) for r in comparisons}
            == {(n, s) for n in NS for s in SEEDS}, 'Incomplete comparisons')
    comparisons = {(int(r['N']), int(r['seed'])): r for r in comparisons}
    errors_saved = read_csv(out / 'input_energy_errors.csv')
    require(len(errors_saved) == 27, 'Incomplete input errors')
    errors_saved = {(r['group'], r['channel']): r for r in errors_saved}
    require(len(errors_saved) == 27, 'Duplicate input errors')
    input_checks = read_json(out / 'input_checks.json')
    require(len(input_checks) == 9, 'Incomplete input checks')
    input_checks = {(r['N'], r['seed']): r for r in input_checks}
    require(set(input_checks) == set(comparisons), 'Input checks group identity')
    repeats_saved = read_json(out / 'repeatability.json')
    require(len(repeats_saved) == 9, 'Incomplete repeatability')
    repeats_saved = {r['group']: r for r in repeats_saved}
    history_saved = read_json(out / 'historical_comparison.json')
    require(len(history_saved) == 252, 'Incomplete historical comparison')
    history_saved = {(r['group'], r['cluster']): r for r in history_saved}
    require(len(history_saved) == 252, 'Duplicate historical comparison')
    groups, physical, repeats, old_differences = [], {}, {}, {}
    for n in NS:
        for seed in SEEDS:
            group = f'N{n}_seed{seed}'
            weights_path = r08 / group / 'weights.csv'
            require((out / (group + '_weights.csv')).read_bytes() == weights_path.read_bytes(), group + ': weight copy')
            input_path = r03 / (group + '_inputs.csv')
            require((out / input_path.name).read_bytes() == input_path.read_bytes(), group + ': input copy')
            weights_rows = read_csv(weights_path)
            weights = read_json(r08 / group / 'solution.json')['weights']
            model = read_json(r08 / group / 'model.json')
            representatives = read_csv(r03 / (group + '_representatives.csv'))
            labels = read_csv(r03 / (group + '_labels.csv'))
            require(len(labels) == 365 and {int(r['day']) for r in labels} == set(range(365))
                    and {int(r['cluster']) for r in labels} == set(range(n)), group + ': labels')
            require(len(weights) == len(weights_rows) == len(representatives) == n, group + ': weight length')
            require([float(r['w']) for r in weights_rows] == weights, group + ': native weight precision')
            require(abs(math.fsum(weights) - 365) <= 1e-7, group + ': weight sum')
            require(math.fsum(float(r['c']) for r in weights_rows) == 365, group + ': original counts')
            inputs_all = read_csv(input_path)
            require(len(inputs_all) == 24 * n and {int(r['cluster']) for r in inputs_all} == set(range(n)),
                    group + ': input cluster matrix')
            summaries = read_csv(out / (group + '_summary.csv'))
            require(len(summaries) == n, group + ': summary length')
            daily_totals, input_energy = [], {c: [] for c in CHANNELS}
            saved_main = None
            for cluster, (w, record, rep) in enumerate(zip(weights, weights_rows, representatives)):
                name = group + f'_cluster{cluster}'
                require(int(record['cluster']) == int(rep['cluster']) == cluster and
                        record['date_UTC'] == rep['date_UTC'] == model['dates'][cluster] and
                        int(record['day']) == int(rep['day']) == model['days'][cluster] and
                        float(record['c']) == float(rep['days']) == model['counts'][cluster], name + ': identity')
                count = float(record['c'])
                require(count > 0 and count.is_integer() and
                        sum(int(r['cluster']) == cluster for r in labels) == count and
                        next(int(r['cluster']) for r in labels if int(r['day']) == int(record['day'])) == cluster,
                        name + ': cluster count/membership')
                require(record['date_UTC'] == (date(2023, 1, 1) + timedelta(days=int(record['day']))).isoformat(),
                        name + ': date/day mismatch')
                require(math.isfinite(w) and .5 * count - 1e-7 <= w <= 2 * count + 1e-7, name + ': bound')
                inputs = [r for r in inputs_all if int(r['cluster']) == cluster]
                day = int(record['day'])
                require(0 <= day < 365, name + ': day range')
                annual_day = full_inputs[day * 24:(day + 1) * 24]
                require(len(inputs) == 24, name + ': hours')
                for hour, (a, b) in enumerate(zip(inputs, annual_day)):
                    require(int(a['hour']) == hour and all(float(a[c]) == float(b[c]) for c in CHANNELS),
                            name + ': annual input provenance')
                for c in CHANNELS:
                    input_energy[c].append(math.fsum(float(r[c]) for r in inputs))
                rows, total, residual = verify_daily(out, name, manifest['cases'][name], inputs, storage, thermal, costs, True)
                require(summaries[cluster]['scenario'] == name, name + ': summary identity')
                for key, value in total.items():
                    close(summaries[cluster][key], value, name + ': ' + key)
                old_total = summarize(read_csv(r03 / (name + '_hourly.csv')), storage, costs)
                old_differences[name] = {key: total[key] - old_total[key] for key in total}
                historical = history_saved[(group, cluster)]
                compare_keys = ('renewable_available_MWh', 'renewable_used_MWh', 'curtailment_MWh',
                                'total_load_MWh', 'thermal_generation_MWh', 'unserved_MWh')
                close(historical['energy_difference'], max(abs(old_differences[name][k]) for k in compare_keys),
                      name + ': historical energy difference')
                close(historical['cost_difference'], abs(old_differences[name]['total_cost_CNY']),
                      name + ': historical cost difference')
                daily_totals.append(total)
                physical[name] = residual
                if cluster == 0:
                    saved_main = rows
                    repeat_name = group + '_repeat_cluster0'
                    repeated, repeat_total, repeat_residual = verify_daily(out, repeat_name, manifest['cases'][repeat_name],
                                                                          inputs, storage, thermal, costs, True)
                    hourly_diff = max(abs(float(a[k]) - float(b[k])) for a, b in zip(saved_main, repeated) for k in a)
                    energy_diff = max(abs(total[k] - repeat_total[k]) for k in ENERGY)
                    objective_diff = abs(manifest['cases'][name]['objective_CNY'] - manifest['cases'][repeat_name]['objective_CNY'])
                    require(max(hourly_diff, energy_diff, objective_diff) <= 1e-6, group + ': repeatability')
                    repeats[group] = {'hourly_max_diff': hourly_diff, 'energy_max_diff': energy_diff,
                                      'objective_diff': objective_diff}
                    recorded = repeats_saved[group]
                    require(recorded == read_json(out / (group + '_repeatability.json'))
                            and recorded['cluster'] == 0, group + ': repeat record identity')
                    close(recorded['hourly_difference'], hourly_diff, group + ': repeat hourly')
                    close(recorded['objective_difference'], objective_diff, group + ': repeat objective')
                    summary_keys = ('renewable_available_MWh', 'renewable_used_MWh', 'curtailment_MWh',
                                    'total_load_MWh', 'thermal_generation_MWh', 'unserved_MWh', 'total_cost_CNY')
                    summary_diff = max(abs(total[k] - repeat_total[k]) for k in summary_keys)
                    close(recorded['summary_difference'], summary_diff, group + ': repeat summary')
                    require(max(recorded[k] for k in ('hourly_difference', 'objective_difference',
                                                     'summary_difference')) <= 1e-6, group + ': repeat record gate')
                    physical[repeat_name] = repeat_residual
            total = aggregate(daily_totals, weights)
            errors = {}
            for index, c in enumerate(CHANNELS):
                close(model['target'][index], targets[c], group + ': target ' + c)
                for a, b in zip(input_energy[c], model['energy'][index]):
                    close(a, b, group + ': original model energy')
                weighted, errors[c] = relative_error(input_energy[c], weights, targets[c])
                record = errors_saved[(group, c)]
                for key, value in (('target_MWh', targets[c]), ('weighted_MWh', weighted), ('relative_error', errors[c])):
                    close(record[key], value, group + ': input error ' + key)
            d = max(errors.values())
            check = input_checks[(n, seed)]
            close(check['D'], d, group + ': input check D')
            require((check['D'] <= .02) == (d <= .02), group + ': input check threshold conflict')
            close(check['weight_sum'], math.fsum(weights), group + ': recorded weight sum')
            require(check['sum_residual'] <= 1e-7 and check['bound_residual'] <= 1e-7,
                    group + ': input check residual')
            for i, c in enumerate(CHANNELS):
                close(check['target_MWh'][i], targets[c], group + ': input check target')
                close(check['weighted_MWh'][i], float(errors_saved[(group, c)]['weighted_MWh']),
                      group + ': input check weighted energy')
                close(check['relative_errors'][i], errors[c], group + ': input check relative error')
            e = max(abs(total[k] - baseline[k]) for k in RATES)
            result = {'N': n, 'seed': seed, 'D': d, 'E_pp': e, **total,
                      **{c + '_relative_error': errors[c] for c in CHANNELS}, 'passed': d <= .02 and e <= 1.}
            saved = comparisons[(n, seed)]
            for key in result:
                if key not in ('N', 'seed', 'passed') and key in saved:
                    close(saved[key], result[key], group + ': comparison ' + key)
            require(all(k in saved for k in ('D', 'E_pp', *RATES, 'total_cost_CNY')), group + ': comparison fields')
            require((float(saved['D']) <= .02) == (d <= .02) and (float(saved['E_pp']) <= 1.) == (e <= 1.),
                    group + ': threshold arithmetic conflict')
            require(str(saved['passed']).lower() == str(result['passed']).lower(), group + ': pass conflict')
            groups.append(result)
    verdict, passing = decide(groups)
    require(verdict != 'invalid', 'Validity or D gate failed')
    details = manifest['details']
    require(details['main_dispatch_calls'] == 252 and details['repeat_dispatch_calls'] == 9
            and details['weight_lp_calls'] == 0 and details['clustering_calls'] == 0
            and manifest['dispatch_calls'] == 261 and manifest['weight_lp_calls'] == 0, 'Wrong solver counts')
    require(details['provisional_verdict'] == verdict and details['passing_N'] == passing, 'Verdict conflict')
    require(sha(manifest_path) == manifest_hash, 'Manifest changed during audit')
    return {'passed': True, 'status': 'complete', 'run_id': run_id, 'verdict': verdict,
            'passing_N': passing, 'selected_N': min(passing) if passing else None,
            'groups': groups, 'hash_checks': hashes, 'physical_residuals': physical,
            'baseline': {'days': 365, 'annual': baseline, 'physical_residuals': baseline_residuals},
            'repeatability': repeats, 'R03_differences': old_differences,
            'main_dispatch_calls': 252, 'repeat_dispatch_calls': 9, 'audit_solver_calls': 0,
            'main_manifest_sha256': manifest_hash, 'freeze_sha256': sha(freeze_path),
            'audit_source_sha256': sha(Path(__file__)),
            'physical_audit_source_sha256': sha(root / 'scripts/independent_dispatch_audit.py'),
            'timestamp': datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'U11R09-v\d+', args.run_id) is not None, 'Invalid run ID')
    report_path = ROOT / 'results/annual' / (args.run_id + '-independent-audit.json')
    failure_path = report_path.with_name(args.run_id + '-audit-failure.json')
    require(not report_path.exists() and not failure_path.exists(), 'Audit evidence already exists')
    import subprocess
    from unittest.mock import patch
    try:
        with patch.object(subprocess, 'Popen', side_effect=RuntimeError('Independent audit prohibits external processes')):
            result = audit(ROOT, args.run_id)
        write_new(report_path, result)
        print(json.dumps({'passed': True, 'verdict': result['verdict'], 'passing_N': result['passing_N'],
                          'report': str(report_path), 'solver_calls': 0}))
    except Exception as exc:
        write_new(failure_path, {'passed': False, 'status': 'failed', 'verdict': 'invalid',
                                'run_id': args.run_id, 'error': repr(exc), 'audit_solver_calls': 0})
        raise


if __name__ == '__main__':
    main()
