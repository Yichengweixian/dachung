"""Run U06R01 primary, path attribution and robustness scenarios."""
import argparse
import pandas as pd
from src.study_runtime import ROOT, StudyRun, configuration

def main():
    p=argparse.ArgumentParser(); p.add_argument("--run-id",default="U06R01-v01"); a=p.parse_args()
    run=StudyRun("U06R01-mutual-exclusion","optimization",a.run_id)
    cfg,s,t,e=configuration(); data=pd.read_csv(ROOT/"data/input_24h.csv")
    cases=[("main",data,s,t,1.,True),
           ("method",data,s,dict(t,thermal_min_MW=0,thermal_ramp_MW_per_h=None),1.,False),
           ("minimum",data,s,dict(t,thermal_ramp_MW_per_h=None),1.,False),
           ("ramp",data,s,t,1.,False)]
    half=data.loc[data.index.repeat(2)].reset_index(drop=True); half.hour=half.index*.5
    cases.extend([("half_hour",half,s,t,.5,True),
                  ("zero_storage",data,dict(s,energy_capacity_MWh=0,power_capacity_MW=0),t,1.,True),
                  ("zero_renewable",data.assign(wind=0.,solar=0.),s,t,1.,True)])
    rows=[]
    for name,d,st,th,dt,end in cases:
        _,row=run.case(name,d,st,th,e,dt,end); rows.append(row)
    pd.DataFrame(rows).to_csv(run.out/"summary.csv",index=False,float_format="%.17g",encoding="utf-8")
    run.finish("supported",{"cases":len(rows),"max_residual":max(x["max_residual"] for x in rows),
                             "attribution_scope":"ordered constraint path; full-factorial audit in U07R01"})

if __name__=="__main__": main()
