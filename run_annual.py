"""U11R02: fixed historical year, 365 independent daily MILPs, typical-day checks."""
import argparse
import importlib.metadata
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.download_nasa_power import download
from scripts.independent_dispatch_audit import audit_file
from src.convert_weather import read_weather,convert_weather,SOLAR
from src.annual_clustering import cluster_days,annual_metrics
from src.data_loader import load_input_data
from src.study_runtime import ROOT,StudyRun,configuration,dump,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U11R02-v01');a=p.parse_args()
    run=StudyRun('U11R02-annual-coherent','annual',a.run_id);cfg,s,t,e=configuration();c=cfg['study_sequence_v02']['U11']
    run.manifest['packages'].update({x:importlib.metadata.version(x) for x in ['scikit-learn','scipy','threadpoolctl']})
    try:
        raw=ROOT/'data/raw'/a.run_id/'main/response.json'
        if not raw.exists():raw=download(raw.parent,'20230101','20231231')
        w,meta=read_weather(raw,'20230101','20231231')
        if not np.allclose(meta['geometry']['coordinates'][:2],[114.3,30.59],rtol=0,atol=1e-8):raise ValueError('Wrong coordinates')
        data=convert_weather(w,pd.read_csv(ROOT/'data/input_24h.csv').load,c['solar_limit_MW'])
        data.to_csv(run.out/'input_8760h.csv',index=False,float_format='%.2f',encoding='utf-8');data=load_input_data(run.out/'input_8760h.csv',8760)
        loss=np.maximum(w[SOLAR].to_numpy()*.15-c['solar_limit_MW'],0)
        pd.DataFrame(dict(timestamp_UTC=w.timestamp_UTC,uncapped_MW=w[SOLAR]*.15,cap_loss_MWh=loss)).loc[loss>0].to_csv(run.out/'solar_cap_events.csv',index=False,encoding='utf-8')
        run.manifest['input_sha256']=sha(run.out/'input_8760h.csv');run.manifest['raw_sha256']=sha(raw);run.manifest['raw_request_sha256']=sha(raw.parent/'request.json')
        rows=[]
        for day in range(365):
            q=data.iloc[day*24:(day+1)*24].copy();q.hour=np.arange(24)
            name=f'day_{day:03d}';_,row=run.case(name,q,s,t,e);audit_file(run.out/(name+'_hourly.csv'),s,t)
            rows.append(row)
            if day%30==0:print('Annual days',day+1,'/365',flush=True)
        pd.DataFrame(rows).to_csv(run.out/'daily_summary.csv',index=False,float_format='%.17g',encoding='utf-8')
        full=annual_metrics(rows,np.ones(365));pd.DataFrame([full]).to_csv(run.out/'full_annual.csv',index=False,float_format='%.17g',encoding='utf-8')
        comparisons=[];typical_tables={}
        for seed in c['seeds']:
            for n in c['clusters']:
                days,counts,labels,stats=cluster_days(data,n,seed,c['n_init']);prefix=f'N{n}_seed{seed}'
                pd.DataFrame(dict(day=np.arange(365),cluster=labels)).to_csv(run.out/(prefix+'_labels.csv'),index=False)
                pd.DataFrame(dict(cluster=np.arange(n),days=counts,weight=counts/365)).to_csv(run.out/(prefix+'_weights.csv'),index=False,float_format='%.17g')
                outputs=[];centers=[]
                for k,day in enumerate(days):
                    name=prefix+f'_cluster{k}';_,row=run.case(name,day,s,t,e);audit_file(run.out/(name+'_hourly.csv'),s,t)
                    outputs.append(row);centers.append(day.assign(cluster=k))
                centers=pd.concat(centers);centers.to_csv(run.out/(prefix+'_centers.csv'),index=False,float_format='%.17g');typical_tables[seed,n]=centers
                pd.DataFrame(outputs).to_csv(run.out/(prefix+'_summary.csv'),index=False,float_format='%.17g')
                metrics=annual_metrics(outputs,counts)
                for name in ['renewable_utilization_pct','curtailment_rate_pct']:metrics[name+'_error_pp']=abs(metrics[name]-full[name])
                comparisons.append(dict(seed=seed,N=n,**stats,**metrics));print(prefix,metrics['renewable_utilization_pct_error_pp'],flush=True)
        compare=pd.DataFrame(comparisons);compare['worst_error_pp']=compare[['renewable_utilization_pct_error_pp','curtailment_rate_pct_error_pp']].max(axis=1)
        compare.to_csv(run.out/'comparison.csv',index=False,float_format='%.17g',encoding='utf-8')
        primary=compare[compare.seed==42].sort_values('N');best=primary.sort_values(['worst_error_pp','N']).iloc[0];n=int(best.N)
        main=bool(best.worst_error_pp<=1);robust=bool(compare[(compare.seed==7)&(compare.N==n)].worst_error_pp.iloc[0]<=1)
        monotone=bool(np.all(np.diff(primary.worst_error_pp)<=1e-12))
        run.fig.mkdir(parents=True,exist_ok=False)
        fig,ax=plt.subplots(figsize=(8,4))
        for seed,table in compare.groupby('seed'):ax.plot(table.N,table.worst_error_pp,marker='o',label=f'seed {seed}')
        ax.axhline(1,color='black',ls='--',label='1 percentage-point threshold');ax.set(xlabel='Typical days',ylabel='Annual error (percentage points)');ax.legend();fig.tight_layout();fig.savefig(run.fig/'annual_error.png',dpi=140);plt.close(fig)
        fig,axes=plt.subplots(n,1,figsize=(10,n*1.5),sharex=True)
        for k,ax in enumerate(axes):
            center=typical_tables[42,n];center=center[center.cluster==k]
            for name in ['load','wind','solar']:ax.plot(center.hour,center[name],label=name)
            ax.set_ylabel(f'C{k} MW')
        axes[0].legend(ncol=3);axes[-1].set_xlabel('Hour (UTC)');fig.tight_layout();fig.savefig(run.fig/'typical_days.png',dpi=120);plt.close(fig)
        run.finish('supported' if main and robust and monotone else 'inconclusive',dict(hours=8760,days=365,solves=len(run.manifest['cases']),main_passed=main,
            selected_N=n,best_error_pp=float(best.worst_error_pp),seed7_passed=robust,nonincreasing_error=monotone,solar_capped_hours=int((loss>0).sum()),solar_cap_loss_MWh=float(loss.sum())))
    except Exception as exc:
        run.manifest.update(status='blocked',verdict='invalid',error=repr(exc));dump(run.out/'failure.json',dict(error=repr(exc)));dump(run.out/'run_manifest.json',run.manifest);raise

if __name__=='__main__':main()
