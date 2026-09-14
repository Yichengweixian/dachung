"""U07R: freeze then run 2^3 constraint combinations and Shapley accounting."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import numpy as np
import pandas as pd
import pulp
from src.optimization_model import solve_dispatch
from src.optimization_validation import validate, summarize
from scripts.audit_u07 import check

ROOT=Path(__file__).resolve().parent
UNIT=ROOT/'instructions/studies/U07R-factorial-attribution'
OUT=ROOT/'results/attribution/U07R-20260913-01'
METRICS=['operating_cost_CNY','renewable_utilization_pct','curtailment_MWh','thermal_generation_MWh']
NAMES=['thermal_minimum','thermal_ramp','terminal_energy']

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(p,o):
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def freeze():
    target=UNIT/'freeze.json'
    if target.exists():
        raise RuntimeError('Existing freeze retained')
    files=[ROOT/'data/input_24h.csv',*sorted((ROOT/'config').glob('*.json')),
           *(UNIT/n for n in ['question.md','design.md','decision-rule.md','plan.md']),
           ROOT/'results/economics/dispatch_summary.csv',ROOT/'results/storage_hourly.csv',
           ROOT/'results/optimization/U06-20260913-02/run_manifest.json',
           ROOT/'src/optimization_model.py',ROOT/'src/cbc_precision.py',ROOT/'src/optimization_validation.py',
           ROOT/'scripts/audit_u07.py',ROOT/'run_factorial_attribution.py']
    dump(target,{'run_id':OUT.name,'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
                 'sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files},
                 'config':{p.name:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'config').glob('*.json')}})
    print('Frozen',target)

def allocation(values):
    rows=[]
    for i,name in enumerate(NAMES):
        increments=[]
        for perm in itertools.permutations(range(3)):
            mask=0
            for j in perm:
                if j==i:
                    increments.append(values[mask|1<<i]-values[mask]); break
                mask |= 1<<j
        weighted=np.zeros(len(METRICS))
        for mask in range(8):
            if not mask & (1<<i):
                k=mask.bit_count()
                weighted += math.factorial(k)*math.factorial(2-k)/6*(values[mask|1<<i]-values[mask])
        average=np.mean(increments,axis=0)
        assert np.max(np.abs(weighted-average))<1e-6
        for j,metric in enumerate(METRICS):
            rows.append({'factor':name,'metric':metric,'shapley':float(average[j]),
                         'minimum_marginal':float(np.min(increments,axis=0)[j]),
                         'maximum_marginal':float(np.max(increments,axis=0)[j])})
    return pd.DataFrame(rows)

def run():
    frozen=json.loads((UNIT/'freeze.json').read_text(encoding='utf-8'))
    for p,h in frozen['sha256'].items():
        assert sha(ROOT/p)==h,p
    OUT.mkdir(parents=True,exist_ok=False)
    try:
        cfg=frozen['config']; s=cfg['storage.json']; c=cfg['economics.json']['parameters']
        dt=cfg['simulation.json']['time_step_hours']; data=pd.read_csv(ROOT/'data/input_24h.csv')
        records=[]; details={}; values={}; repeat_diff={}
        def solve(mask,save):
            t={'min':cfg['optimization.json']['thermal_min_MW'] if mask&1 else 0.,
               'max':cfg['no_storage.json']['thermal_max_MW'],
               'ramp':cfg['optimization.json']['thermal_ramp_MW_per_h'] if mask&2 else None}
            q,info=solve_dispatch(data,s,t,c,dt,terminal=bool(mask&4))
            residuals=validate(q,data,s,t,dt,bool(mask&4)); check(q,s,t,dt,bool(mask&4))
            result=summarize(q,c,dt)
            assert abs(result['operating_cost_CNY']-info['objective_CNY'])<1e-6
            if save:
                file=OUT/f'case_{mask}_hourly.csv'; q.to_csv(file,index=False,float_format='%.17g')
                read=pd.read_csv(file); validate(read,data,s,t,dt,bool(mask&4)); check(read,s,t,dt,bool(mask&4))
                details[str(mask)]={'thermal':t,'terminal':bool(mask&4),'result':result,'residuals':residuals,**info}
                records.append({'mask':mask,'minimum_on':bool(mask&1),'ramp_on':bool(mask&2),'terminal_on':bool(mask&4),**result})
            return np.array([result[k] for k in METRICS])
        for mask in range(8):
            values[mask]=solve(mask,True)
        for mask in reversed(range(8)):
            delta=np.abs(solve(mask,False)-values[mask]); repeat_diff[str(mask)]=dict(zip(METRICS,delta.tolist()))
            assert delta[0]<1e-6, 'Objective repeat mismatch'
        for mask in range(8):
            for bit in range(3):
                if not mask & 1<<bit:
                    assert values[mask|1<<bit][0] >= values[mask][0]-1e-6
        attribution=allocation(values)
        old=pd.read_csv(ROOT/'results/economics/dispatch_summary.csv').query("scenario == 'E40_P20'").iloc[0]
        baseline=np.array([old.thermal_generation_MWh*c['thermal_cost_CNY_per_MWh']+old.curtailment_MWh*c['curtailment_penalty_CNY_per_MWh']+
                           old.load_shedding_MWh*c['load_shedding_penalty_CNY_per_MWh']+old.storage_discharge_MWh*c['storage_variable_om_CNY_per_MWh_discharged'],
                           old.renewable_utilization_pct,old.curtailment_MWh,old.thermal_generation_MWh])
        closure=[]
        for j,metric in enumerate(METRICS):
            contribution=attribution.query('metric == @metric').shapley.sum()
            error=float(values[7][j]-baseline[j]-(values[0][j]-baseline[j]+contribution))
            assert abs(error)<1e-6
            closure.append({'metric':metric,'method_change':values[0][j]-baseline[j],
                            'constraints_total':contribution,'overall_change':values[7][j]-baseline[j],'closure_error':error})
        pd.DataFrame(records).to_csv(OUT/'combinations.csv',index=False)
        attribution.to_csv(OUT/'shapley.csv',index=False)
        pd.DataFrame(closure).to_csv(OUT/'closure.csv',index=False)
        for p,h in frozen['sha256'].items():
            assert sha(ROOT/p)==h,p
        dump(OUT/'run_manifest.json',{'run_id':OUT.name,'freeze':frozen,'python':sys.version,'platform':platform.platform(),
             'packages':{'pulp':pulp.__version__,'numpy':np.__version__,'pandas':pd.__version__},'cases':details,
             'reverse_repeat_absolute_differences':repeat_diff,'verdict':'supported',
             'warning':'Accounting decomposition, not causal proof; secondary metrics may depend on selected optimum.'})
        print(attribution.to_string(index=False)); print(pd.DataFrame(closure).to_string(index=False))
        print('Max repeat difference:',max(v for d in repeat_diff.values() for v in d.values()))
    except Exception as exc:
        dump(OUT/'failure.json',{'error':repr(exc),'verdict':'invalid'}); raise

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['freeze','run'])
    {'freeze':freeze,'run':run}[p.parse_args().action]()
