"""U10 frozen week, four coordinate checks and a fresh-process repeat."""
import argparse
import subprocess
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.download_nasa_power import download
from src.convert_weather import read_weather,convert_weather,SOLAR,WIND
from src.data_loader import load_input_data
from src.study_runtime import ROOT,StudyRun,configuration,dump,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U10-master-v01');a=p.parse_args()
    run=StudyRun('U10-real-weather-data','real_data',a.run_id)
    cfg,_,_,_=configuration();c=cfg['study_sequence_v02']['U10'];base=ROOT/'data/raw'/a.run_id
    try:
        raw=base/'main/response.json'
        if not raw.exists():raw=download(base/'main',c['start'],c['end'],c['latitude'],c['longitude'])
        w,meta=read_weather(raw,c['start'],c['end']);shape=pd.read_csv(ROOT/'data/input_24h.csv').load
        q=convert_weather(w,shape);q.to_csv(run.out/'input_168h.csv',index=False,float_format='%.2f',encoding='utf-8')
        load_input_data(run.out/'input_168h.csv',168)
        subprocess.run([sys.executable,'-m','src.convert_weather','--raw',str(raw),'--start',c['start'],'--end',c['end'],'--output',str(run.out/'repeat.csv')],cwd=ROOT,check=True)
        if sha(run.out/'input_168h.csv')!=sha(run.out/'repeat.csv'):raise ValueError('Repeat differs')
        rows=[]
        for name,dlat,dlon in [('north',.1,0),('south',-.1,0),('east',0,.1),('west',0,-.1)]:
            r=download(base/name,c['start'],c['end'],c['latitude']+dlat,c['longitude']+dlon)
            w2,_=read_weather(r,c['start'],c['end']);q2=convert_weather(w2,shape)
            for variable in ['wind','solar']:
                for stat in ['mean','max']:
                    ref=float(getattr(q[variable],stat)());value=float(getattr(q2[variable],stat)())
                    delta=abs(value-ref)/ref if ref else (0. if value==0 else 1.)
                    rows.append(dict(coordinate=name,variable=variable,stat=stat,reference=ref,value=value,relative_difference=delta,passed=delta<.1))
        robustness=pd.DataFrame(rows);robustness.to_csv(run.out/'robustness.csv',index=False,encoding='utf-8')
        run.fig.mkdir(parents=True,exist_ok=False)
        fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True)
        axes[0].plot(q.hour,w[SOLAR]);axes[0].set_ylabel('Solar (Wh/m²)')
        axes[1].plot(q.hour,w[WIND]);axes[1].set_ylabel('Wind (m/s)');axes[1].set_xlabel('Hour (UTC)')
        fig.tight_layout();fig.savefig(run.fig/'weather.png',dpi=140);plt.close(fig)
        fig,ax=plt.subplots(figsize=(12,4))
        for name in ['load','wind','solar']:ax.plot(q.hour,q[name],label=name)
        ax.set(xlabel='Hour (UTC)',ylabel='Power (MW)',title='NASA-derived wind/PV; constructed load');ax.legend();fig.tight_layout();fig.savefig(run.fig/'power.png',dpi=140);plt.close(fig)
        processed=ROOT/'data/processed'/a.run_id;processed.mkdir(parents=True,exist_ok=False)
        (processed/'input_168h.csv').write_bytes((run.out/'input_168h.csv').read_bytes())
        run.manifest['raw_sha256']={f.relative_to(ROOT).as_posix():sha(f) for f in base.rglob('*.json')}
        run.finish('supported' if robustness.passed.all() else 'inconclusive',dict(main_passed=True,hours=168,repeat_identical=True,
                   robustness_passed=bool(robustness.passed.all()),max_relative_difference=float(robustness.relative_difference.max()),units=meta['parameters']))
    except Exception as exc:
        run.manifest.update(status='blocked',verdict='inconclusive' if isinstance(exc,OSError) else 'invalid',error=repr(exc))
        dump(run.out/'failure.json',dict(error=repr(exc)));dump(run.out/'run_manifest.json',run.manifest);raise

if __name__=='__main__':main()
