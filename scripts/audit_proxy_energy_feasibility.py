"""Independent original-decimal / native-MPS replay; optimizer calls are trapped."""
import argparse
from datetime import date, timedelta
from decimal import Decimal as D
from fractions import Fraction as F
import json
import math
from pathlib import Path
import struct
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_cost_unserved_attribution import METRICS, detailed_metrics
from scripts.audit_fixed_weights_capacity_transfer import read_csv, check_close, annual, sha
from scripts.audit_u11r08_feasibility import certificate, residuals, check_residuals
from scripts.diagnose_u11r06_serialization import read_mps, decimal_residuals

SEEDS = (42,7,2026)
CHANNELS = ['load','wind','solar','excess_proxy']


def amounts(rows):
    values = [[F(r[ch]) for ch in CHANNELS[:3]] for r in rows]
    if any(x < 0 for row in values for x in row): raise ValueError('Negative original input')
    return [sum(row[k] for row in values) for k in range(3)]+[sum(max(row[0]-row[1]-row[2]-120,F(0)) for row in values)]


def state(t,proof):
    lower,upper = F(proof['lower']),F(proof['upper'])
    if upper-lower > F('1e-8') or abs(t-.02) <= 1e-8: return 'uncertain'
    if upper <= F('.02') and t <= .02: return 'reachable'
    if lower > F('.02') and t > .02: return 'unreachable'
    return 'uncertain'


def native(folder,model,solution,frozen):
    mapping = json.loads((folder/'mapping.json').read_text())
    process = json.loads((folder/'process.json').read_text())
    exe = '.venv/Lib/site-packages/pulp/solverdir/cbc/win/i64/cbc.exe'
    command = [str(ROOT/exe),'model.mps','-primalTolerance','1e-9','-integerTolerance','1e-9','-ratioGap','0',
               '-allowableGap','0','-threads','0','-presolve','off','-branch','-printingOptions','all',
               '-solution','solution.txt','-saveSolution','solution.bin','-quit']
    if Path(process['command'][0]).resolve() != Path(command[0]).resolve() or process['command'][1:] != command[1:] or process['returncode'] != 0 or process['timeout_seconds'] != 60 or sha(ROOT/exe) != frozen['sha256'][exe]:
        raise ValueError('CBC process/runtime mismatch')
    if (folder/'stdout.txt').read_text() != solution['log'] or (folder/'stderr.txt').read_text() or not (folder/'solution.txt').read_text().startswith('Optimal'):
        raise ValueError('CBC log/status evidence mismatch')
    raw = (folder/'solution.bin').read_bytes()
    rows,columns = struct.unpack_from('=ii',raw)
    names = [f'w_{k:03d}' for k in range(48)]+['worst_relative_error']
    constraints = ['total_days']+[f'channel_{k}' for k in range(len(model['A_ub']))]
    if rows != len(constraints) or columns != 49 or len(raw) != 16+16*(rows+columns) or mapping['rows'] != rows or mapping['columns'] != columns or set(mapping['variables']) != set(names) or set(mapping['constraints']) != set(constraints) or mapping['original_variable_order'] != sorted(names):
        raise ValueError('Native layout/mapping mismatch')
    values = dict(zip(mapping['original_variable_order'],struct.unpack_from(f'={columns}d',raw,16+16*rows)))
    if any(not math.isfinite(v) for v in values.values()) or [values[f'w_{k:03d}'] for k in range(48)] != solution['weights'] or values['worst_relative_error'] != solution['t']:
        raise ValueError('Native primal mismatch')
    objective = struct.unpack_from('=d',raw,8)[0]
    check_close(objective,solution['objective'],'native objective')
    if solution['precision']['native_objective'] != objective: raise ValueError('Native objective report mismatch')
    text_values = {}
    for line in (folder/'solution.txt').read_text().splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 3 and fields[1] in mapping['variables'].values(): text_values[fields[1]] = float(fields[2])
    rounding = max(abs(text_values[renamed]-values[name]) for name,renamed in mapping['variables'].items())
    if rounding != solution['precision']['max_text_rounding']: raise ValueError('Text rounding report mismatch')
    mr,mh,ms,mb = read_mps(folder/'model.mps')
    if set(mb) != set(mapping['variables'].values()) or {key for key,value in ms.items() if value != 'N'} != set(mapping['constraints'].values()): raise ValueError('MPS inventory mismatch')
    reverse = {renamed:name for name,renamed in mapping['constraints'].items()}
    for name,renamed in mapping['variables'].items():
        index = names.index(name)
        expected = model['bounds'][index]
        if mb[renamed] != [None if x is None else D(str(x)) for x in expected]: raise ValueError('MPS bounds mismatch')
    for name,renamed in mapping['constraints'].items():
        coefficients = model['A_eq'][0] if name == 'total_days' else model['A_ub'][int(name.split('_')[1])]
        rhs = 365. if name == 'total_days' else model['b_ub'][int(name.split('_')[1])]
        if ms[renamed] != ('E' if name == 'total_days' else 'L') or abs(mh[renamed]-D(str(rhs))) > D('1e-12'): raise ValueError('MPS row definition mismatch')
        expected = {mapping['variables'][key]:D.from_float(float(v)) for key,v in zip(names,coefficients) if v}
        if set(mr[renamed]) != set(expected) or any(abs(mr[renamed][key]-v) > D('1e-12') for key,v in expected.items()): raise ValueError('MPS coefficient mismatch')
    objectives = [row for row,sense in ms.items() if sense == 'N']
    if len(objectives) != 1 or mr[objectives[0]] != {mapping['variables']['worst_relative_error']:D(1)}: raise ValueError('MPS objective mismatch')
    report = decimal_residuals(mr,mh,ms,{mapping['variables'][key]:D.from_float(v) for key,v in values.items()},mb)
    for r in report:
        tolerance = D('1e-6') if r['row'].startswith('bound:') or reverse.get(r['row']) == 'total_days' else D('1e-7')
        if D(r['violation']) > tolerance: raise ValueError('Native MPS violation: '+str(r))
    return float(D(report[0]['violation']))


def audit(folder):
    m = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    frozen = ROOT/'instructions/studies/U11R14-proxy-energy-feasibility/freeze.json'
    if m['status'] != 'complete' or m['unit'] != 'U11R14-proxy-energy-feasibility' or m['cases'] or m['lp_calls'] != 6 or m['dispatch_calls'] != 0: raise ValueError('Formal status/budget mismatch')
    if sha(frozen) != m['freeze_sha256'] or json.loads(frozen.read_text(encoding='utf-8')) != m['freeze']: raise ValueError('Freeze identity mismatch')
    hashes = 1
    for entries,base in ((m['freeze']['sha256'],ROOT),(m['source_sha256'],ROOT),(m['artifacts'],folder)):
        for path,digest in entries.items():
            if sha(base/path) != digest: raise ValueError('Hash mismatch: '+path)
            hashes += 1
    if {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name != 'run_manifest.json'} != set(m['artifacts']): raise ValueError('Artifact inventory mismatch')
    expected = dict(N=48,seeds=list(SEEDS),channels=CHANNELS,thermal_max_MW=120,threshold=.02,primary_lp_budget=3,cross_lp_budget=3,dispatch_budget=0,secondary_objectives=0)
    if m['parameters'] != expected or any(m['packages'][key] != value for key,value in dict(numpy='2.5.3',pandas='3.0.5',scipy='1.18.1',pulp='3.3.0').items()): raise ValueError('Runtime/parameter mismatch')
    cfg = m['freeze']['config']
    storage = cfg['storage.json']
    thermal = {key:cfg['optimization.json'][key] for key in ('thermal_min_MW','thermal_ramp_MW_per_h')}
    thermal['thermal_max_MW'] = cfg['no_storage.json']['thermal_max_MW']
    economics = cfg['economics.json']['parameters']
    if storage['energy_capacity_MWh'] != 40 or storage['power_capacity_MW'] != 20 or thermal['thermal_max_MW'] != 120: raise ValueError('Frozen capacity mismatch')
    preflight = json.loads((ROOT/'results/annual/U11R14-predecessor-audit-v01.json').read_text(encoding='utf-8'))
    if not preflight['passed'] or preflight['run_manifest_sha256'] != sha(ROOT/'results/annual/U11R13-v01/run_manifest.json'): raise ValueError('Preflight identity mismatch')
    source = read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv')
    if len(source) != 8760 or [F(r['hour']) for r in source] != list(range(8760)): raise ValueError('Original hourly axis mismatch')
    target = amounts(source)
    old_folders = {key:ROOT/'results/annual'/key for key in ('U11R02-v01','U11R12-v01')}
    old = {key:json.loads((path/'run_manifest.json').read_text(encoding='utf-8')) for key,path in old_folders.items()}
    for record in old.values():
        if record['status'] != 'complete' or any(record['freeze']['config'][key] != cfg[key] for key in ('storage.json','optimization.json','no_storage.json','economics.json')): raise ValueError('Predecessor identity mismatch')
    comparisons = read_csv(folder/'comparison.csv')
    diagnostics = read_csv(folder/'diagnostics.csv')
    if [int(r['seed']) for r in comparisons] != list(SEEDS) or any(int(r['N']) != 48 for r in comparisons) or [(int(r['seed']),r['solver']) for r in diagnostics] != [(s,q) for s in SEEDS for q in ('highs','cbc')]: raise ValueError('Output matrix/order mismatch')
    maximum = physical = mps_max = objective_difference = 0.
    count = 0

    def check(a,b,label):
        nonlocal maximum
        maximum = max(maximum,check_close(a,b,label))

    def read_case(key,name,day,saved):
        nonlocal physical,count
        row,r = detailed_metrics(old_folders[key]/(name+'_hourly.csv'),source[day*24:(day+1)*24],storage,thermal,economics,old[key]['cases'][name])
        for metric in METRICS: check(row[metric],saved[metric],'source daily '+metric)
        physical = max(physical,r)
        count += 1
        return row

    full_summary = read_csv(old_folders['U11R02-v01']/'daily_summary.csv')
    if [r['scenario'] for r in full_summary] != [f'day_{d:03d}' for d in range(365)]: raise ValueError('Full dispatch inventory mismatch')
    full = annual([read_case('U11R02-v01',r['scenario'],d,r) for d,r in enumerate(full_summary)],[1.]*365)
    saved_full = read_csv(old_folders['U11R02-v01']/'full_annual.csv')[0]
    for key,value in full.items(): check(value,saved_full[key],'full annual')
    classifications,proofs,diagnostic_rows = [],[],[]
    for seed,comparison in zip(SEEDS,comparisons):
        prefix = f'N48_seed{seed}'
        group = folder/prefix
        reps = read_csv(old_folders['U11R12-v01']/(prefix+'_representatives.csv'))
        labels = read_csv(ROOT/'results/annual/U11R08B-v01'/(prefix+'_labels.csv'))
        if len(reps) != 48 or len(labels) != 365 or [int(r['day']) for r in labels] != list(range(365)): raise ValueError('Fixed clustering dimensions/order')
        labs = [int(r['cluster']) for r in labels]
        counts = [labs.count(k) for k in range(48)]
        days = [int(r['day']) for r in reps]
        dates = [(date(2023,1,1)+timedelta(days=d)).isoformat() for d in days]
        if set(labs) != set(range(48)) or len(set(days)) != 48 or any(not 0 <= d < 365 or labs[d] != k or int(r['cluster']) != k or float(r['days']) != counts[k] or r['date_UTC'] != dates[k] for k,(d,r) in enumerate(zip(days,reps))): raise ValueError('Fixed representative metadata mismatch')
        energy = list(map(list,zip(*(amounts(source[d*24:(d+1)*24]) for d in days))))
        model = json.loads((group/'model.json').read_text())
        if len(model['energy']) != 4 or any(len(row) != 48 for row in model['energy']) or len(model['target']) != 4: raise ValueError('Model coefficient dimensions')
        if model['counts'] != counts or model['channels'] != CHANNELS or model['days'] != days or model['dates'] != dates or model['seed'] != seed or model['N'] != 48 or model['unit'] != 'MWh': raise ValueError('Model metadata mismatch')
        for a,b in zip(target,model['target']): check(float(a),b,'original target')
        for exact,saved in zip(energy,model['energy']):
            for a,b in zip(exact,saved): check(float(a),b,'original daily amount')
        rows,rhs = [],[]
        for row,total in zip(model['energy'],model['target']):
            if total:
                rows.extend([[x/total for x in row]+[-1.],[-x/total for x in row]+[-1.]])
                rhs.extend([1.,-1.])
            elif any(row): raise ValueError('Zero channel target mismatch')
        if model['A_ub'] != rows or model['b_ub'] != rhs or model['A_eq'] != [[1.]*48+[0.]] or model['b_eq'] != [365.] or model['bounds'] != [[c/2.,2.*c] for c in counts]+[[0.,None]] or model['objective'] != [0.]*48+[1.]: raise ValueError('Model algebra mismatch')
        exact_rows = [[float(sign*a/total) for a in row]+[-1.] for row,total in zip(energy,target) if total for sign in (1,-1)]
        if len(rows) != len(exact_rows) or any(abs(a-b) > 1e-12 for exact,saved in zip(exact_rows,rows) for a,b in zip(exact,saved)): raise ValueError('Original decimal normalized coefficient mismatch')
        feasible = json.loads((group/'count_feasible_point.json').read_text())
        if feasible['weights'] != counts: raise ValueError('Count witness mismatch')
        check_residuals(residuals(energy,target,counts,counts,feasible['t']))
        primary = json.loads((group/'highs/solution.json').read_text())
        cross = json.loads((group/'cbc/solution.json').read_text())
        process = json.loads((group/'highs/process.json').read_text())
        command = [str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'run_proxy_energy_feasibility.py'),'--worker',str(group/'model.json'),'--solution',str(group/'highs/solution.json')]
        if process['command'] != command or process['returncode'] != 0 or process['timeout_seconds'] != 90 or primary['success'] is not True or primary['status'] != 0 or primary['scipy_version'] != '1.18.1' or 'Optimal' not in (group/'highs/solver.log').read_text(): raise ValueError('HiGHS runtime/status mismatch')
        if cross['status'] != 'Optimal' or cross['solution_status'] != 1: raise ValueError('CBC status mismatch')
        mps_max = max(mps_max,native(group/'cbc/native',model,cross,m['freeze']))
        objective_difference = max(objective_difference,abs(primary['objective']-cross['objective']))
        if objective_difference > 1e-8 or primary['objective'] != primary['t'] or cross['objective'] != cross['t']: raise ValueError('LP objective agreement mismatch')
        proof = certificate(energy,target,counts,primary['weights'],primary['inequality_marginals'],primary['equality_marginals'])
        if proof != json.loads((group/'certificate.json').read_text()) or F(proof['gap']) > F('1e-8'): raise ValueError('Exact certificate mismatch/gap')
        classification = state(primary['t'],proof)
        if classification != comparison['classification']: raise ValueError('Exact classification mismatch')
        for key,value in dict(primary_t=primary['t'],cbc_t=cross['t'],exact_lower=proof['lower_float'],exact_upper=proof['upper_float']).items(): check(value,comparison[key],'comparison')
        classifications.append(classification)
        proofs.append(dict(seed=seed,classification=classification,lower=proof['lower'],upper=proof['upper'],gap=proof['gap'],max_repair=proof['max_repair']))
        summary = read_csv(old_folders['U11R12-v01']/(prefix+'_summary.csv'))
        if [r['scenario'] for r in summary] != [prefix+f'_cluster{k}' for k in range(48)]: raise ValueError('Saved representative dispatch inventory')
        dispatch = [read_case('U11R12-v01',r['scenario'],d,r) for d,r in zip(days,summary)]
        for solver,solution in (('highs',primary),('cbc',cross)):
            weights = read_csv(group/(solver+'_weights.csv'))
            if len(weights) != 48 or [float(r['w']) for r in weights] != solution['weights'] or any(int(r['cluster']) != k or int(r['day']) != days[k] or r['date_UTC'] != dates[k] or float(r['c']) != counts[k] for k,r in enumerate(weights)): raise ValueError('Native weight CSV/metadata mismatch')
            w,t = solution['weights'],solution['t']
            check_residuals(residuals(energy,target,counts,w,t))
            reported = json.loads((group/'highs/checks.json').read_text()) if solver == 'highs' else solution['checks']
            signed = [math.fsum(a*x for a,x in zip(row,w))/b-1 if b else 0. for row,b in zip(model['energy'],model['target'])]
            if reported['passed'] is not True: raise ValueError('Saved feasibility flag mismatch')
            for k,value in enumerate(signed):
                check(value,reported['signed_relative_errors'][k],'signed input check')
                check(abs(value),reported['absolute_relative_errors'][k],'absolute input check')
                check(math.fsum(a*x for a,x in zip(model['energy'][k],w)),reported['weighted_MWh'][k],'weighted input check')
            metrics = annual(dispatch,w)
            E = max(abs(metrics[k]-full[k]) for k in ('renewable_utilization_pct','curtailment_rate_pct'))
            diagnostic = dict(seed=seed,solver=solver,**metrics,worst_error_pp=E,max_input_relative_error=max(map(abs,signed[:3])),proxy_relative_error=abs(signed[3]),cost_error_CNY=metrics['total_cost_CNY']-full['total_cost_CNY'],unserved_error_MWh=metrics['unserved_MWh']-full['unserved_MWh'])
            saved = next(r for r in diagnostics if int(r['seed']) == seed and r['solver'] == solver)
            for key,value in diagnostic.items():
                if key not in ('seed','solver'): check(value,saved[key],'diagnostic '+key)
            if (saved['passes_ED'] == 'True') != (E <= 1 and diagnostic['max_input_relative_error'] <= .02): raise ValueError('Diagnostic E/D mismatch')
            diagnostic_rows.append(diagnostic)
    verdict = 'refuted' if 'unreachable' in classifications else 'inconclusive' if 'uncertain' in classifications else 'supported'
    if count != 509 or m['verdict'] != verdict or any(m['details'][key] != value for key,value in dict(primary_lp_calls=3,cross_lp_calls=3,dispatch_calls=0,groups=3,classification=classifications).items()): raise ValueError('Verdict/details/source budget mismatch')
    return dict(passed=True,new_solver_calls=0,formal_lp_calls=6,dispatch_calls=0,source_dispatches=count,checked_hashes=hashes,
                max_readback_difference=maximum,max_physical_residual=physical,max_mps_violation=mps_max,max_objective_difference=objective_difference,
                verdict=verdict,certificates=proofs,diagnostics=diagnostic_rows,run_manifest_sha256=sha(folder/'run_manifest.json'),audit_source_sha256=sha(__file__))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_id')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    try:
        with patch('subprocess.run',side_effect=AssertionError('No subprocess in audit')), patch('pulp.LpProblem.solve',side_effect=AssertionError('No optimization in audit')), patch('scipy.optimize.linprog',side_effect=AssertionError('No LP in audit')):
            report = audit(ROOT/'results/annual'/args.run_id)
    except Exception as exc: report = dict(passed=False,error=repr(exc),new_solver_calls=0,audit_source_sha256=sha(__file__))
    with (ROOT/args.output).open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps({key:value for key,value in report.items() if key != 'diagnostics'},ensure_ascii=False),flush=True)
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
