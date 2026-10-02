"""Frozen U11R09 matrix; all R08 weights are read-only."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import traceback

import numpy as np
import pandas as pd

from src.fixed_weight_dispatch import (
    ROOT, TOTALS, CHANNELS, dump, sha, read_csv, create_output, verify_hashes, load_sources,
    configuration, baseline, run_case, aggregate, decision,
)


def run(run_id):
    out=create_output(ROOT/'results/annual',run_id)
    unit=ROOT/'instructions/studies/U11R09-fixed-weight-dual-threshold'
    sources=list((ROOT/'src').glob('*.py'))+[ROOT/'run_u11r09_fixed_weights.py',
            ROOT/'scripts/audit_u11r09_fixed_weights.py',ROOT/'scripts/finalize_u11r09.py',
            ROOT/'scripts/independent_dispatch_audit.py']
    counter={'dispatch_calls':0}
    m=dict(run_id=run_id,unit=unit.name,started_at=datetime.now(timezone.utc).isoformat(),
           status='in_progress',verdict=None,cases={},dispatch_calls=0,weight_lp_calls=0,
           python=sys.version,platform=platform.platform(),
           git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
           source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sources if p.exists()},
           packages={k:importlib.metadata.version(k) for k in ['numpy','pandas','pulp','scipy']})
    stage='preflight'
    try:
        freeze=json.loads((unit/'freeze.json').read_text('utf-8'))
        m.update(freeze=freeze,freeze_sha256=sha(unit/'freeze.json'))
        dump(out/'run_manifest.json',m)
        verify_hashes(ROOT,freeze['sha256'])
        groups=load_sources()
        dump(out/'input_checks.json',[dict(N=g['N'],seed=g['seed'],**g['input_check']) for g in groups])
        s,t,e=configuration(freeze)
        full,base_report=baseline(s,t,e)
        dump(out/'baseline_audit.json',base_report)
        print('R08 weights and 365-day baseline verified; no solver calls yet',flush=True)
        comparisons,errors,repeats,history=[],[],[],[]
        for g in groups:
            prefix=f"N{g['N']}_seed{g['seed']}"
            old=ROOT/'results/annual/U11R08-v02'/prefix
            shutil.copyfile(old/'weights.csv',out/(prefix+'_weights.csv'))
            shutil.copyfile(ROOT/'results/annual/U11R03-v01'/(prefix+'_inputs.csv'),out/(prefix+'_inputs.csv'))
            inputs=read_csv(out/(prefix+'_inputs.csv'))
            historical=read_csv(ROOT/'results/annual/U11R03-v01'/(prefix+'_summary.csv'))
            rows=[]; first=None
            for i in range(g['N']):
                stage=prefix+f'_cluster{i}'
                day=inputs.loc[inputs.cluster==i,['hour',*CHANNELS]].reset_index(drop=True)
                q,row,info=run_case(out,stage,day,s,t,e,counter)
                m['cases'][stage]=info; rows.append(row)
                if i==0: first=(q,row,info,day)
                history.append(dict(group=prefix,cluster=i,
                    energy_difference=max(abs(float(row[k])-float(historical.iloc[i][k])) for k in TOTALS if k!='total_cost_CNY'),
                    cost_difference=abs(float(row['total_cost_CNY'])-float(historical.iloc[i].total_cost_CNY))))
                m['dispatch_calls']=counter['dispatch_calls']
                dump(out/'run_manifest.json',m)
            pd.DataFrame(rows).to_csv(out/(prefix+'_summary.csv'),index=False,float_format='%.17g')
            stage=prefix+'_repeat_cluster0'
            q2,row2,info2=run_case(out,stage,first[3],s,t,e,counter)
            m['cases'][stage]=info2
            repeat=dict(group=prefix,cluster=0,hourly_difference=float(np.max(np.abs(q2.to_numpy()-first[0].to_numpy()))),
                        objective_difference=abs(info2['objective_CNY']-first[2]['objective_CNY']),
                        summary_difference=max(abs(float(row2[k])-float(first[1][k])) for k in TOTALS))
            dump(out/(prefix+'_repeatability.json'),repeat)
            if max(repeat[k] for k in ['hourly_difference','objective_difference','summary_difference'])>1e-6:
                raise ValueError('Repeatability gate failed: '+prefix)
            repeats.append(repeat)
            metrics=aggregate(read_csv(out/(prefix+'_summary.csv')).to_dict('records'),g['weights'])
            E=max(abs(metrics[k]-full[k]) for k in ['renewable_utilization_pct','curtailment_rate_pct'])
            D=g['input_check']['D']
            row=dict(N=g['N'],seed=g['seed'],D=D,E_pp=E,passed=bool(D<=.02 and E<=1.),**metrics,
                     **{k+'_relative_error':v for k,v in zip(CHANNELS,g['input_check']['relative_errors'])})
            comparisons.append(row)
            for i,k in enumerate(CHANNELS):
                errors.append(dict(group=prefix,channel=k,target_MWh=g['target'][i],
                    weighted_MWh=g['input_check']['weighted_MWh'][i],relative_error=g['input_check']['relative_errors'][i]))
            print(prefix,'D=',repr(D),'E_pp=',repr(E),'calls=',counter['dispatch_calls'],flush=True)
        pd.DataFrame(comparisons).to_csv(out/'comparison.csv',index=False,float_format='%.17g')
        pd.DataFrame(errors).to_csv(out/'input_energy_errors.csv',index=False,float_format='%.17g')
        dump(out/'repeatability.json',repeats)
        dump(out/'historical_comparison.json',history)
        if counter['dispatch_calls']!=261 or len(m['cases'])!=261: raise ValueError('Incomplete solver matrix')
        provisional,passing=decision(comparisons)
        verify_hashes(ROOT,freeze['sha256'])
        verify_hashes(ROOT,m['source_sha256'])
        m.update(status='awaiting_independent_audit',verdict=None,details=dict(provisional_verdict=provisional,
                 passing_N=passing,main_dispatch_calls=252,repeat_dispatch_calls=9,
                 weight_lp_calls=0,clustering_calls=0,baseline_days=365),finished_at=datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        m.update(status='blocked',verdict='invalid',error=repr(exc),failure_stage=stage)
        if not (out/'failure.json').exists():
            dump(out/'failure.json',dict(stage=stage,error=repr(exc),traceback=traceback.format_exc(),verdict='invalid',
                                         dispatch_calls=counter['dispatch_calls'],weight_lp_calls=0))
        raise
    finally:
        m['dispatch_calls']=counter['dispatch_calls']
        m['artifacts']={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*'))
                        if p.is_file() and p.name!='run_manifest.json'}
        dump(out/'run_manifest.json',m)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',default='U11R09-v01')
    print(run(parser.parse_args().run_id))
