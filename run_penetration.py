"""U08 frozen twelve-scenario study with repeat and independent CSV checks."""
import argparse
import pandas as pd
from scripts.independent_dispatch_audit import audit_file
from src.study_runtime import ROOT, StudyRun, configuration
from src.plot_studies import penetration_plots

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U08-master-v01');a=p.parse_args()
    run=StudyRun('U08-penetration-matrix','penetration',a.run_id)
    cfg,s,t,e=configuration(); data=pd.read_csv(ROOT/'data/input_24h.csv')
    scenarios=pd.read_csv(ROOT/'data/scenarios/penetration_scenarios.csv')
    rows=[];repeat=[]
    for again in (False,True):
        for sc in (scenarios if not again else scenarios.iloc[::-1]).itertuples(index=False):
            d=data.assign(wind=data.wind*sc.wind_factor,solar=data.solar*sc.solar_factor)
            st=dict(s,energy_capacity_MWh=sc.energy_capacity_MWh,power_capacity_MW=sc.power_capacity_MW)
            name=('repeat_' if again else '')+sc.scenario
            _,row=run.case(name,d,st,t,e)
            audit_file(run.out/(name+'_hourly.csv'),st,t)
            row.update(scenario=sc.scenario,factor=sc.wind_factor);(repeat if again else rows).append(row)
    table=pd.DataFrame(rows); rep=pd.DataFrame(repeat)
    cols=['renewable_utilization_pct','curtailment_rate_pct','total_cost_CNY','thermal_generation_MWh','unserved_MWh']
    diff=float((table.set_index('scenario')[cols]-rep.set_index('scenario')[cols]).abs().to_numpy().max())
    if diff>=1e-6:raise ValueError('Repeat mismatch')
    one=all((g.sort_values('factor').curtailment_rate_pct.diff().dropna()>=-1e-6).all() for _,g in table.groupby('energy_capacity_MWh'))
    two=all((g.sort_values('energy_capacity_MWh').renewable_utilization_pct.diff().dropna()>=-1e-6).all() for _,g in table.groupby('factor'))
    marginal=[]
    for factor,g in table.groupby('factor'):
        g=g.sort_values('energy_capacity_MWh'); gain=g.renewable_utilization_pct.diff().iloc[1:].tolist()
        marginal.append(dict(factor=factor,gain_0_40_pp=gain[0],gain_40_80_pp=gain[1],diminishing=gain[1]<=gain[0]+1e-6))
    three=all(x['diminishing'] for x in marginal)
    table.to_csv(run.out/'summary.csv',index=False,float_format='%.17g',encoding='utf-8')
    pd.DataFrame(marginal).to_csv(run.out/'marginal.csv',index=False,encoding='utf-8')
    penetration_plots(run.out/'summary.csv',run.fig)
    verdict='supported' if one and two and three else ('inconclusive' if one and two else 'refuted')
    run.finish(verdict,dict(scenarios=12,repeat_difference=diff,trend_curtailment=bool(one),trend_storage=bool(two),diminishing=bool(three)))

if __name__=='__main__':main()
