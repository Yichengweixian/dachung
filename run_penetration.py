"""U08: solve, validate and summarize the frozen 4x3 scenario matrix."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np
import pandas as pd
import pulp
from src.economic_model import EconomicParameters, evaluate_system_costs, validate_cost_results
from src.optimization_model import solve_dispatch
from src.optimization_validation import validate, summarize
from src.plot_penetration import plot_matrix
from scripts.audit_u07 import check

ROOT=Path(__file__).resolve().parent
UNIT=ROOT/'instructions/studies/U08-penetration-matrix'
OUT=ROOT/'results/penetration/U08-20260913-01'
FIG=ROOT/'figures/penetration/U08-20260913-01'
COMPARE=['renewable_utilization_pct','curtailment_rate_pct','curtailment_MWh','thermal_generation_MWh',
         'unserved_MWh','charge_MWh','discharge_MWh','operating_cost_CNY','total_cost_CNY']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def main():
    frozen=json.loads((UNIT/'freeze.json').read_text(encoding='utf-8'))
    for p,h in frozen['sha256'].items(): assert sha(ROOT/p)==h,p
    OUT.mkdir(parents=True,exist_ok=False); FIG.mkdir(parents=True,exist_ok=False)
    try:
        cfg=frozen['config']; base=pd.read_csv(ROOT/'data/input_24h.csv'); scenarios=pd.read_csv(ROOT/'data/scenarios/penetration_scenarios.csv')
        assert len(scenarios)==12 and scenarios.scenario.nunique()==12
        c=cfg['economics.json']['parameters']; ep=EconomicParameters(**c); dt=cfg['simulation.json']['time_step_hours']
        t={'min':cfg['optimization.json']['thermal_min_MW'],'max':cfg['no_storage.json']['thermal_max_MW'],
           'ramp':cfg['optimization.json']['thermal_ramp_MW_per_h']}
        records=[]; details={}; saved={}
        def solve(row,save):
            data=base.copy(); data.wind*=row.wind_factor; data.solar*=row.solar_factor
            storage=dict(cfg['storage.json'],energy_capacity_MWh=float(row.energy_capacity_MWh),power_capacity_MW=float(row.power_capacity_MW))
            q,info=solve_dispatch(data,storage,t,c,dt,True)
            residuals=validate(q,data,storage,t,dt,True); check(q,storage,t,dt,True)
            result=summarize(q,c,dt); available=float((q.wind_available+q.solar_available).sum()*dt)
            dispatch=pd.DataFrame([{'scenario':row.scenario,'energy_capacity_MWh':row.energy_capacity_MWh,
                'power_capacity_MW':row.power_capacity_MW,'num_steps':len(q),'time_step_hours':dt,
                'thermal_generation_MWh':result['thermal_generation_MWh'],'curtailment_MWh':result['curtailment_MWh'],
                'load_shedding_MWh':result['unserved_MWh'],'storage_discharge_MWh':result['discharge_MWh'],
                'renewable_utilization_pct':result['renewable_utilization_pct'],
                'curtailment_rate_pct':100*result['curtailment_MWh']/available,'initial_inventory_supply_MWh':0.}])
            costs=evaluate_system_costs(dispatch,ep); validate_cost_results(costs,ep)
            aggregate={**result,'curtailment_rate_pct':float(costs.curtailment_rate_pct.iloc[0]),
                       'total_cost_CNY':float(costs.total_cost_CNY.iloc[0])}
            assert abs(result['operating_cost_CNY']-(float(costs.thermal_cost_CNY.iloc[0])+float(costs.curtailment_cost_CNY.iloc[0])+
                float(costs.load_shedding_cost_CNY.iloc[0])+float(costs.storage_variable_om_CNY.iloc[0])))<1e-6
            if save:
                path=OUT/f'{row.scenario}_hourly.csv'; q.to_csv(path,index=False,float_format='%.17g')
                read=pd.read_csv(path); validate(read,data,storage,t,dt,True); check(read,storage,t,dt,True)
                rec={'scenario':row.scenario,'renewable_factor':row.wind_factor,'energy_capacity_MWh':row.energy_capacity_MWh,
                     'power_capacity_MW':row.power_capacity_MW,**aggregate}
                records.append(rec); saved[row.scenario]=np.array([aggregate[k] for k in COMPARE])
                details[row.scenario]={'solver_status':info['status'],'objective_CNY':info['objective_CNY'],
                    'max_residual':max(residuals.values()),'precision_evidence':info['precision_evidence']}
            return np.array([aggregate[k] for k in COMPARE])
        for row in scenarios.itertuples(index=False): solve(row,True)
        repeat={}
        for row in reversed(list(scenarios.itertuples(index=False))):
            delta=np.abs(solve(row,False)-saved[row.scenario]); repeat[row.scenario]=dict(zip(COMPARE,delta.tolist()))
            assert max(delta)<1e-6
        summary=pd.DataFrame(records).sort_values(['renewable_factor','energy_capacity_MWh'])
        marginal=[]
        for factor,g in summary.groupby('renewable_factor'):
            g=g.set_index('energy_capacity_MWh')
            for a,b in [(0,40),(40,80)]:
                marginal.append({'renewable_factor':factor,'from_MWh':a,'to_MWh':b,
                    'utilization_gain_percentage_points':g.loc[b,'renewable_utilization_pct']-g.loc[a,'renewable_utilization_pct'],
                    'curtailment_change_MWh':g.loc[b,'curtailment_MWh']-g.loc[a,'curtailment_MWh'],
                    'total_cost_change_CNY':g.loc[b,'total_cost_CNY']-g.loc[a,'total_cost_CNY']})
        marginal=pd.DataFrame(marginal)
        trend={'curtailment_rate_non_decreasing_with_factor':True,'utilization_non_decreasing_with_capacity':True,'marginal_gain_non_increasing':True}
        for _,g in summary.groupby('energy_capacity_MWh'):
            trend['curtailment_rate_non_decreasing_with_factor'] &= bool((np.diff(g.sort_values('renewable_factor').curtailment_rate_pct)>=-1e-6).all())
        for factor,g in summary.groupby('renewable_factor'):
            trend['utilization_non_decreasing_with_capacity'] &= bool((np.diff(g.sort_values('energy_capacity_MWh').renewable_utilization_pct)>=-1e-6).all())
            gains=marginal[marginal.renewable_factor==factor].sort_values('from_MWh').utilization_gain_percentage_points.to_numpy()
            trend['marginal_gain_non_increasing'] &= bool(gains[1]<=gains[0]+1e-6)
        verdict='supported' if all(trend.values()) else ('inconclusive' if trend['curtailment_rate_non_decreasing_with_factor'] and trend['utilization_non_decreasing_with_capacity'] else 'refuted')
        boundary=summary.query("scenario == 'R140_E000'").iloc[0]
        scaled=base.copy(); scaled[['wind','solar']]*=1.4
        cap_shortage=float(np.maximum(scaled.load-scaled.wind-scaled.solar-t['max'],0).sum()*dt)
        boundary_check={'actual_unserved_MWh':float(boundary.unserved_MWh),'capacity_only_lower_bound_MWh':cap_shortage,
                        'note':'If actual exceeds lower bound, ramping/intertemporal constraints may contribute.'}
        summary.to_csv(OUT/'matrix_summary.csv',index=False,float_format='%.12g'); marginal.to_csv(OUT/'marginal_changes.csv',index=False,float_format='%.12g')
        plot_matrix(summary,FIG)
        for p,h in frozen['sha256'].items(): assert sha(ROOT/p)==h,p
        dump(OUT/'run_manifest.json',{'run_id':OUT.name,'frozen':frozen,'python':sys.version,'platform':platform.platform(),
            'packages':{'pulp':pulp.__version__,'numpy':np.__version__,'pandas':pd.__version__},'cases':details,
            'repeat_absolute_differences':repeat,'trend_checks':trend,'boundary_check':boundary_check,'verdict':verdict})
        print(summary[['scenario','renewable_utilization_pct','curtailment_rate_pct','unserved_MWh','total_cost_CNY']].to_string(index=False))
        print(marginal.to_string(index=False)); print('trend',trend,'verdict',verdict)
    except Exception as exc:
        dump(OUT/'failure.json',{'error':repr(exc),'verdict':'invalid'}); raise

if __name__=='__main__': main()
