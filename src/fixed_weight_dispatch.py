"""U11R09: dispatch with immutable, audited R08 main weights."""
from dataclasses import asdict
import json
import math
from pathlib import Path
import re
import subprocess
import traceback
from unittest.mock import patch

import numpy as np
import pandas as pd
import pulp

from .cbc_full_precision import FullPrecisionCBC
from .economic_model import EconomicParameters, evaluate_system_costs
from .input_energy_feasibility import load_saved_groups
from .optimization_validation import audit_dispatch, summarize_dispatch
from .study_runtime import ROOT, dump, sha, evaluate_case

SIZES = [12, 24, 48]
SEEDS = [42, 7, 2026]
CHANNELS = ['load', 'wind', 'solar']
TOTALS = ['renewable_available_MWh', 'renewable_used_MWh', 'curtailment_MWh',
          'total_load_MWh', 'thermal_generation_MWh', 'unserved_MWh', 'total_cost_CNY']


def read_csv(path):
    return pd.read_csv(path, float_precision='round_trip')


def create_output(base, run_id):
    if not re.fullmatch(r'U11R09-[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run_id')
    out = Path(base)/run_id
    out.mkdir(parents=True, exist_ok=False)
    return out


def recover_weights(folder, counts, days, dates):
    solution = json.loads((folder/'solution.json').read_text('utf-8'))
    table = read_csv(folder/'weights.csv')
    w = np.asarray(solution['weights'], dtype=float)
    if solution.get('status') != 0 or solution.get('success') is not True:
        raise ValueError('R08 formal main solution is not Optimal')
    if len(table) != len(counts) or w.shape != (len(counts),) or not np.isfinite(w).all():
        raise ValueError('Incomplete native weights')
    for col, expected in [('cluster', range(len(counts))), ('c', counts), ('day', days), ('date_UTC', dates)]:
        if list(table[col]) != list(expected):
            raise ValueError('R08 weight identity mismatch: '+col)
    if not np.array_equal(w, table.w.to_numpy()):
        raise ValueError('Native weights differ from saved CSV; no repair permitted')
    return w


def energy_check(energy, target, counts, weights):
    a, b, c, w = map(lambda x: np.asarray(x, dtype=float), (energy, target, counts, weights))
    if c.ndim != 1 or not len(c) or a.shape != (3,len(c)) or b.shape != (3,) or w.shape != c.shape:
        raise ValueError('Energy/weights dimension mismatch')
    if not all(np.isfinite(x).all() for x in (a,b,c,w)) or (a<0).any() or (b<0).any() or (c<=0).any():
        raise ValueError('Invalid energy or weights')
    if math.fsum(c) != 365 or not np.equal(c, np.floor(c)).all():
        raise ValueError('Invalid original cluster counts')
    bound = max(0., float(np.max(.5*c-w)), float(np.max(w-2*c)))
    total = math.fsum(w)
    if bound>1e-7 or abs(total-365)>1e-7:
        raise ValueError('Fixed weights violate bounds or sum')
    amounts, errors = [], []
    for row, t in zip(a,b):
        amount = math.fsum(float(v)*float(x) for v,x in zip(row,w))
        if t == 0:
            if np.any(row != 0): raise ValueError('Nonzero representative energy for zero annual channel')
            error = 0.
        else:
            error = abs(amount/float(t)-1.)
        amounts.append(amount); errors.append(error)
    if max(errors)>.02:
        raise ValueError('Recovered fixed weights fail strict 2% input gate')
    return dict(D=max(errors), relative_errors=errors, weighted_MWh=amounts, target_MWh=b.tolist(),
                weight_sum=total, sum_residual=abs(total-365), bound_residual=bound)


def aggregate(rows, weights):
    if not rows or len(rows)!=len(weights) or not np.isfinite(weights).all() or np.any(np.asarray(weights)<0):
        raise ValueError('Invalid aggregation weights')
    keys = [k for k in TOTALS if k in rows[0]]
    totals = {k:math.fsum(float(row[k])*float(w) for row,w in zip(rows,weights)) for k in keys}
    if not all(math.isfinite(v) for v in totals.values()) or totals['renewable_available_MWh']<=0:
        raise ValueError('Invalid annual renewable denominator or totals')
    totals['renewable_utilization_pct'] = 100*totals['renewable_used_MWh']/totals['renewable_available_MWh']
    totals['curtailment_rate_pct'] = 100*totals['curtailment_MWh']/totals['renewable_available_MWh']
    return totals


def decision(rows):
    expected = {(n,s) for n in SIZES for s in SEEDS}
    if len(rows)!=9 or {(r['N'],r['seed']) for r in rows}!=expected:
        return 'invalid', []
    if any(not math.isfinite(r[k]) or r[k]<0 for r in rows for k in ['D','E_pp']):
        return 'invalid', []
    if any(r['D']>.02 for r in rows):
        return 'invalid', []
    passing = [n for n in SIZES if all(r['D']<=.02 and r['E_pp']<=1. for r in rows if r['N']==n)]
    return ('supported' if passing else 'inconclusive'), passing


def verify_hashes(base, hashes):
    for path, expected in hashes.items():
        if sha(base/path)!=expected: raise ValueError('Hash mismatch: '+str(base/path))
    return len(hashes)


def load_sources(root=ROOT):
    old = root/'results/annual/U11R08-v02'
    manifest = json.loads((old/'run_manifest.json').read_text('utf-8'))
    report = json.loads((old/'independent_audit/report.json').read_text('utf-8'))
    if sha(old/'run_manifest.json')!=report['main_manifest_sha256']:
        raise ValueError('R08 independent audit refers to another main manifest')
    if sha(root/'scripts/audit_u11r08_feasibility.py')!=report['audit_source_sha256']:
        raise ValueError('R08 audit implementation drift')
    verify_hashes(old, manifest['artifacts'])
    verify_hashes(old/'independent_audit', report['artifacts'])
    if len(report['groups'])!=9 or {(g['N'],g['seed']) for g in report['groups']}!={(n,s) for n in SIZES for s in SEEDS}:
        raise ValueError('Incomplete R08 audit matrix')
    if report['verdict']!='supported' or any(g['status']!='reachable' for g in report['groups']):
        raise ValueError('R08 input gate not established')
    groups = load_saved_groups(root)
    for m in groups:
        prefix = f"N{m['N']}_seed{m['seed']}"
        old_model = json.loads((old/prefix/'model.json').read_text('utf-8'))
        for k in ['N','seed','counts','days','dates','energy','target']:
            if old_model[k]!=m[k]: raise ValueError('R08/R03 identity or energy differs: '+k)
        w = recover_weights(old/prefix,m['counts'],m['days'],m['dates'])
        m['weights'] = w.tolist()
        m['input_check'] = energy_check(m['energy'],m['target'],m['counts'],w)
    return groups


def configuration(freeze):
    cfg = freeze['config']
    for run in ['U11R02-v01','U11R03-v01']:
        old = json.loads((ROOT/'results/annual'/run/'run_manifest.json').read_text('utf-8'))['freeze']['config']
        for name in ['storage.json','optimization.json','no_storage.json','economics.json']:
            if cfg[name]!=old[name]: raise ValueError('Configuration mismatch: '+run+' '+name)
    s = cfg['storage.json']
    t = {k:cfg['optimization.json'][k] for k in ['thermal_min_MW','thermal_ramp_MW_per_h']}
    t['thermal_max_MW'] = cfg['no_storage.json']['thermal_max_MW']
    return s,t,EconomicParameters(**cfg['economics.json']['parameters'])


def baseline(s,t,e):
    folder = ROOT/'results/annual/U11R02-v01'
    m = json.loads((folder/'run_manifest.json').read_text('utf-8'))
    verify_hashes(folder,m['artifacts'])
    source = read_csv(folder/'input_8760h.csv')
    saved = read_csv(folder/'daily_summary.csv').set_index('scenario')
    rows, residuals = [], []
    for day in range(365):
        name=f'day_{day:03d}'
        q=read_csv(folder/(name+'_hourly.csv'))
        data=source.iloc[day*24:(day+1)*24].copy(); data.hour=np.arange(24)
        checks=audit_dispatch(q,data,s,t)
        if not checks['passed']: raise ValueError('Baseline physics failed: '+name)
        row=summarize_dispatch(q,asdict(e)).iloc[0].to_dict()
        row.update(scenario=name,energy_capacity_MWh=s['energy_capacity_MWh'],power_capacity_MW=s['power_capacity_MW'],
                   num_steps=24,time_step_hours=1.,load_shedding_MWh=row['unserved_MWh'],
                   storage_discharge_MWh=row['discharge_MWh'],initial_inventory_supply_MWh=0.)
        row.update(evaluate_system_costs(pd.DataFrame([row]),e).iloc[0].to_dict())
        if max(abs(float(row[k])-float(saved.loc[name,k])) for k in TOTALS)>=1e-6:
            raise ValueError('Baseline daily reconstruction failed: '+name)
        rows.append(row); residuals.append(checks['max_residual'])
    annual=aggregate(rows,[1.]*365)
    old=read_csv(folder/'full_annual.csv').iloc[0]
    difference=max(abs(v-float(old[k])) for k,v in annual.items())
    if difference>=1e-6: raise ValueError('Baseline annual reconstruction failed')
    return annual,dict(passed=True,days=365,max_residual=max(residuals),annual_difference=difference,annual=annual)


def run_case(out, name, data, storage, thermal, economics, counter):
    """Capture evidence around the unchanged native CBC implementation."""
    log_path=out/(name+'_cbc.log')
    class RecordedCBC(FullPrecisionCBC):
        def actualSolve(self, lp, **kwargs):
            lp.writeLP(str(out/(name+'_model.lp')))
            lp.writeMPS(str(out/(name+'_model.mps')),rename=1)
            if sum(v.isInteger() for v in lp.variables())!=24:
                raise ValueError('Expected existing 24-hour mutual-exclusion MILP')
            counter['dispatch_calls']+=1
            try:
                return super().actualSolve(lp,**kwargs)
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
                text=(exc.stdout or b'')
                if isinstance(text,bytes): text=text.decode('utf-8',errors='replace')
                extra=exc.stderr or ''
                if isinstance(extra,bytes): extra=extra.decode('utf-8',errors='replace')
                self.log=text+extra
                raise
            finally:
                log_path.write_text(getattr(self,'log','CBC failed before output was available'),encoding='utf-8')
    try:
        with patch('src.cbc_full_precision.FullPrecisionCBC',RecordedCBC):
            q,row,info=evaluate_case(data,storage,thermal,economics)
        if info['solver_status']!='Optimal' or info['model_class']!='MILP':
            raise ValueError('Dispatch not reliably Optimal MILP')
        q.to_csv(out/(name+'_hourly.csv'),index=False,float_format='%.17g')
        saved=read_csv(out/(name+'_hourly.csv'))
        if not np.array_equal(q.to_numpy(),saved.to_numpy(),equal_nan=True):
            raise ValueError('Native dispatch CSV roundtrip changed values')
        checks=audit_dispatch(saved,data,storage,thermal)
        if not checks['passed']: raise ValueError('Saved physics audit failed')
        dump(out/(name+'_checks.json'),checks)
        info.pop('cbc_log',None)
        info.update(storage=storage,thermal=thermal,dt=1.,terminal=True,max_residual=checks['max_residual'])
        row['scenario']=name
        return saved,row,info
    except Exception as exc:
        if not log_path.exists(): log_path.write_text(str(getattr(exc,'log',repr(exc))),encoding='utf-8')
        dump(out/'failure.json',dict(verdict='invalid',case=name,error=repr(exc),traceback=traceback.format_exc(),
                                    dispatch_calls=counter['dispatch_calls'],weight_lp_calls=0))
        raise
