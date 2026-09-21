"""U12R01: all objective calls counted; no grid-initialization or cached fitness."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.genetic_search import run_ga
from src.grid_search import evaluate_candidate
from src.study_runtime import ROOT,StudyRun,configuration,dump
from scripts.independent_dispatch_audit import audit_file

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U12R01-v01');a=p.parse_args()
    run=StudyRun('U12R01-ga-baseline','ga',a.run_id);cfg,s,t,e=configuration();params=cfg['study_sequence_v02']['U12']
    data=pd.read_csv(ROOT/'data/input_24h.csv');grid=pd.read_csv(ROOT/'results/grid_search/U09R01-v01/summary.csv');benchmark=float(grid.total_cost_CNY.min())
    summaries=[]
    try:
        for seed in params['seeds']:
            count=0;start=perf_counter();executor=ThreadPoolExecutor(max_workers=4)
            def worker(item):
                name,x=item
                try:
                    q,row,info=evaluate_candidate(data,s,t,e,*x)
                    q.to_csv(run.out/(name+'_hourly.csv'),index=False,float_format='%.17g',encoding='utf-8')
                    st=dict(s,energy_capacity_MWh=float(x[0]),power_capacity_MW=float(x[1]))
                    audit_file(run.out/(name+'_hourly.csv'),st,t)
                    (run.out/(name+'_cbc.log')).write_text(info.pop('cbc_log'),encoding='utf-8')
                    return name,row,{**info,'storage':st,'thermal':t,'dt':1.,'terminal':True,'max_residual':row['max_residual']}
                except Exception as exc:
                    dump(run.out/(name+'_failure.json'),dict(error=repr(exc),energy=float(x[0]),power=float(x[1])));raise
            def batch(xs,generation):
                nonlocal count
                items=[]
                for x in xs:
                    count+=1;items.append((f'seed{seed}_eval{count:04d}',x))
                values=[]
                for name,row,info in executor.map(worker,items):
                    run.manifest['cases'][name]=info;values.append(row['total_cost_CNY'])
                return values
            def progress(generation,evaluations,best,history):
                pd.DataFrame(history).to_csv(run.out/f'seed{seed}_convergence.csv',index=False,float_format='%.17g')
                if generation%10==0:print('GA',seed,'generation',generation,'evaluations',evaluations,'best',best,flush=True)
            try:best,cost,history=run_ga(batch,params,seed,progress)
            finally:executor.shutdown(wait=True,cancel_futures=True)
            if count!=1480 or len(history)!=count:raise ValueError('Wrong evaluation count')
            if np.any(np.diff([r['best_cost'] for r in history])>0):raise ValueError('Nonmonotone incumbent')
            summaries.append(dict(seed=seed,energy=best[0],power=best[1],cost=cost,evaluations=count,relative_error=abs(cost-benchmark)/benchmark,wall_seconds=perf_counter()-start))
            pd.DataFrame(summaries).to_csv(run.out/'summary.csv',index=False,float_format='%.17g')
        table=pd.DataFrame(summaries);accurate=table.relative_error<.005;fast=table.evaluations<101
        stable=bool(table.cost.max()-table.cost.min()<benchmark*.005 and table.cost.std(ddof=0)<benchmark*.005)
        verdict='supported' if int((accurate&fast).sum())>=2 and stable else ('refuted' if not accurate.any() else 'inconclusive')
        run.fig.mkdir(parents=True,exist_ok=False);fig,ax=plt.subplots(figsize=(10,5))
        for seed in params['seeds']:
            h=pd.read_csv(run.out/f'seed{seed}_convergence.csv');ax.plot(h.evaluation,h.best_cost,label=f'seed {seed}')
        ax.axhline(benchmark,ls='--',color='black',label='101-point grid best');ax.set(xlabel='Actual objective evaluations',ylabel='Best total cost (CNY / 24 h)');ax.legend();fig.tight_layout();fig.savefig(run.fig/'convergence.png',dpi=140);plt.close(fig)
        run.finish(verdict,dict(grid_cost=benchmark,grid_evaluations=101,total_evaluations=len(run.manifest['cases']),accurate_seeds=int(accurate.sum()),fast_accurate_seeds=int((accurate&fast).sum()),seed_robustness=stable))
    except Exception as exc:
        run.manifest.update(status='blocked',verdict='invalid',error=repr(exc));dump(run.out/'failure.json',dict(error=repr(exc)));dump(run.out/'run_manifest.json',run.manifest);raise

if __name__=='__main__':main()
