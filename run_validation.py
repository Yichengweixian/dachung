"""Full-factorial constraint attribution and independent U07R01 audit."""
import argparse
import math
import subprocess
import sys
import pandas as pd
from src.study_runtime import ROOT, StudyRun, configuration
from src.storage_model import StorageParameters, calculate_storage_balance
from src.storage_metrics import summarize_storage

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U07R01-v01');a=p.parse_args()
    run=StudyRun('U07R01-factorial-audit','validation',a.run_id)
    cfg,s,t,e=configuration(); data=pd.read_csv(ROOT/'data/input_24h.csv')
    rows=[]; repeated=[]
    for repeat in (False,True):
        for mask in (range(8) if not repeat else reversed(range(8))):
            th=dict(t,thermal_min_MW=t['thermal_min_MW'] if mask&1 else 0,
                    thermal_ramp_MW_per_h=t['thermal_ramp_MW_per_h'] if mask&2 else None)
            _,row=run.case(('repeat_' if repeat else '')+f'case_{mask}',data,s,th,e,terminal=bool(mask&4))
            row['mask']=mask; (repeated if repeat else rows).append(row)
    table=pd.DataFrame(rows).set_index('mask'); other=pd.DataFrame(repeated).set_index('mask')
    metrics=['renewable_utilization_pct','curtailment_MWh','thermal_generation_MWh','operating_cost_CNY']
    maximum=float((table[metrics]-other[metrics]).abs().to_numpy().max())
    if maximum>=1e-6:raise ValueError('Repeat failed')
    rule=summarize_storage(calculate_storage_balance(data,StorageParameters(**s),t['thermal_max_MW']),StorageParameters(**s)).iloc[0]
    rule_cost=rule.thermal_generation_MWh*e.thermal_cost_CNY_per_MWh+rule.curtailment_MWh*e.curtailment_penalty_CNY_per_MWh+rule.load_shedding_MWh*e.load_shedding_penalty_CNY_per_MWh+rule.storage_discharge_MWh*e.storage_variable_om_CNY_per_MWh_discharged
    factors=[]; closure=[]
    for metric in metrics:
        contributions=[]
        for bit,name in enumerate(['minimum','ramp','terminal']):
            value=0.
            for mask in range(8):
                if mask&(1<<bit):continue
                k=mask.bit_count();weight=math.factorial(k)*math.factorial(2-k)/6
                value+=weight*(table.loc[mask|(1<<bit),metric]-table.loc[mask,metric])
            contributions.append(value); factors.append(dict(metric=metric,factor=name,contribution=value))
        base=rule_cost if metric=='operating_cost_CNY' else rule[metric]
        method=table.loc[0,metric]-base; total=table.loc[7,metric]-base
        residual=method+sum(contributions)-total
        if abs(residual)>=1e-6:raise ValueError('Attribution closure failed')
        closure.append(dict(metric=metric,method_difference=method,total_difference=total,residual=residual))
    oracle=pd.DataFrame(dict(hour=range(4),load=[40,30,90,70],wind=[60,0,0,0],solar=0))
    q,_=run.case('oracle',oracle,dict(s,energy_capacity_MWh=0,power_capacity_MW=0),t,e)
    for column,expected in {'thermal':[30,30,60,70],'wind_curt':[50,0,0,0],'unserved':[0,0,30,0]}.items():
        if max(abs(q[column]-expected))>=1e-6:raise ValueError('Hand oracle failed')
    table.to_csv(run.out/'combinations.csv',float_format='%.17g',encoding='utf-8')
    pd.DataFrame(factors).to_csv(run.out/'shapley.csv',index=False,float_format='%.17g',encoding='utf-8')
    pd.DataFrame(closure).to_csv(run.out/'closure.csv',index=False,float_format='%.17g',encoding='utf-8')
    # Save complete case parameters before invoking a separate Python process.
    from src.study_runtime import dump
    dump(run.out/'run_manifest.json',run.manifest)
    audit=subprocess.run([sys.executable,'scripts/independent_dispatch_audit.py',str(run.out)],cwd=ROOT,capture_output=True,text=True,check=True)
    (run.out/'independent_audit.json').write_text(audit.stdout,encoding='utf-8')
    run.finish('supported',dict(cases=len(run.manifest['cases']),repeat_difference=maximum,oracle='passed',closure_max=max(abs(x['residual']) for x in closure)))

if __name__=='__main__':main()
