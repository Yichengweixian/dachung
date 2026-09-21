"""Frozen 101 candidates, reverse repeat and high-investment robustness."""
import argparse
from dataclasses import replace
import pandas as pd
from scripts.independent_dispatch_audit import audit_file
from src.grid_search import generate_candidates
from src.study_runtime import ROOT,StudyRun,configuration
from src.plot_studies import grid_plots

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U09R01-v01');a=p.parse_args()
    run=StudyRun('U09R01-grid-clarification','grid_search',a.run_id)
    cfg,s,t,e=configuration();grid=cfg['study_sequence_v02']['U09'];data=pd.read_csv(ROOT/'data/input_24h.csv')
    candidates=generate_candidates(grid['energies'],grid['powers']);all_tables={}
    for kind in ['main','repeat','robustness']:
        costs=replace(e,storage_energy_capex_CNY_per_kWh=grid['robust_energy_capex'],storage_power_capex_CNY_per_kW=grid['robust_power_capex']) if kind=='robustness' else e
        rows=[]
        for index,(energy,power) in enumerate(reversed(candidates) if kind=='repeat' else candidates):
            st=dict(s,energy_capacity_MWh=energy,power_capacity_MW=power)
            scenario=f'E{energy:03d}_P{power:02d}'; name=kind+'_'+scenario
            _,row=run.case(name,data,st,t,costs);audit_file(run.out/(name+'_hourly.csv'),st,t)
            row['scenario']=scenario;rows.append(row)
            if index%25==0:print(kind,index+1,'/ 101',flush=True)
        table=pd.DataFrame(rows).sort_values('scenario');all_tables[kind]=table
        table.to_csv(run.out/(kind+'_summary.csv'),index=False,float_format='%.17g',encoding='utf-8')
    table=all_tables['main'];other=all_tables['repeat'];robust=all_tables['robustness']
    cols=['total_cost_CNY','renewable_utilization_pct','curtailment_MWh','thermal_generation_MWh','unserved_MWh']
    diff=float((table.set_index('scenario')[cols]-other.set_index('scenario')[cols]).abs().to_numpy().max())
    if diff>=1e-6:raise ValueError('Repeat mismatch')
    best=table.loc[table.total_cost_CNY.idxmin()];rb=robust.loc[robust.total_cost_CNY.idxmin()]
    ties=table[(table.total_cost_CNY-best.total_cost_CNY).abs()<1e-6]
    internal=bool(((ties.energy_capacity_MWh>0)&(ties.energy_capacity_MWh<100)&(ties.power_capacity_MW>5)&(ties.power_capacity_MW<50)).all())
    direction=bool(rb.energy_capacity_MWh<=best.energy_capacity_MWh and rb.power_capacity_MW<=best.power_capacity_MW)
    table.to_csv(run.out/'summary.csv',index=False,float_format='%.17g',encoding='utf-8')
    pd.read_csv(run.out/('main_'+best.scenario+'_hourly.csv')).to_csv(run.out/'best_dispatch.csv',index=False,float_format='%.17g',encoding='utf-8')
    neighbors=table[((table.energy_capacity_MWh-best.energy_capacity_MWh).abs()==10)&(table.power_capacity_MW==best.power_capacity_MW) | ((table.power_capacity_MW-best.power_capacity_MW).abs()==5)&(table.energy_capacity_MWh==best.energy_capacity_MWh)].copy()
    neighbors['cost_difference_CNY']=neighbors.total_cost_CNY-best.total_cost_CNY
    neighbors.to_csv(run.out/'neighbors.csv',index=False,encoding='utf-8')
    grid_plots(run.out/'summary.csv',run.out/'best_dispatch.csv',run.fig)
    run.finish('supported' if internal and direction else 'inconclusive',dict(candidates=101,solves=303,repeat_difference=diff,
                best=dict(energy=float(best.energy_capacity_MWh),power=float(best.power_capacity_MW),cost=float(best.total_cost_CNY)),
                robust_best=dict(energy=float(rb.energy_capacity_MWh),power=float(rb.power_capacity_MW),cost=float(rb.total_cost_CNY)),
                tie_count=len(ties),strictly_internal=internal,high_investment_direction=direction))

if __name__=='__main__':main()
