"""UI-facing services; reuse verified dispatch and cost implementations."""
from dataclasses import asdict
from io import BytesIO
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .data_loader import load_input_data,validate_input_data
from .storage_model import StorageParameters,calculate_storage_balance
from .storage_metrics import summarize_storage
from .storage_validation import validate_storage_result
from .economic_model import EconomicParameters,evaluate_system_costs,validate_cost_results
from .study_runtime import ROOT,evaluate_case
from .grid_search import generate_candidates,evaluate_candidate
from .annual_clustering import annual_metrics

BUILTINS={'24h 构造算例':'data/input_24h.csv','168h 气象估计':'data/processed/U10-master-v01/input_168h.csv','8760h 年度独立日':'results/annual/U11R02-v01/input_8760h.csv'}

def read_input(source):
    q=load_input_data(source)[['hour','load','wind','solar']]
    if len(q)>8760:raise ValueError('原型最多支持8760行，请先划分研究时段。')
    return q

def parameters_from_json(raw):
    p=json.loads(raw)
    s=p['storage'];t=p['thermal'];e=EconomicParameters(**p['economics'])
    validate_parameters(s,t,e)
    return s,t,e

def validate_parameters(s,t,e):
    StorageParameters(**s)
    if not np.isfinite(list(t.values())).all() or not 0<=t['thermal_min_MW']<=t['thermal_max_MW'] or t['thermal_ramp_MW_per_h']<0:
        raise ValueError('火电上下限或爬坡参数无效。')
    EconomicParameters(**asdict(e))

def dispatch(mode,data,s,t,e,progress=None):
    validate_input_data(data);validate_parameters(s,t,e)
    if mode=='规则':
        storage=StorageParameters(**s);q=calculate_storage_balance(data,storage,t['thermal_max_MW'])
        summary=summarize_storage(q,storage);validate_storage_result(q,summary,storage,t['thermal_max_MW'])
        summary=summary.assign(scenario='rule',energy_capacity_MWh=s['energy_capacity_MWh'],power_capacity_MW=s['power_capacity_MW'],num_steps=len(data),time_step_hours=1.)
        summary['initial_inventory_supply_MWh']=(summary.initial_energy_MWh-summary.final_energy_MWh).clip(lower=0)*s['eta_discharge']
        costs=evaluate_system_costs(summary,e);validate_cost_results(costs,e)
        return q,{**summary.iloc[0].to_dict(),**costs.iloc[0].to_dict(),'solver_status':'规则校验通过'}
    if mode!='MILP':raise ValueError('未知调度模式。')
    if len(data)<=168:
        q,row,_=evaluate_case(data,s,t,e);return q,row
    if len(data)%24:raise ValueError('超过168h的MILP输入必须由完整的24h天组成。')
    outputs=[];rows=[]
    for start in range(0,len(data),24):
        day=data.iloc[start:start+24].copy();hours=day.hour.copy();day.hour=np.arange(24)
        q,row,_=evaluate_case(day,s,t,e);q.hour=hours.to_numpy();q['independent_day']=start//24
        outputs.append(q);rows.append(row)
        if progress:progress((start+24)/len(data))
    row=annual_metrics(rows,np.ones(len(rows)));row.update(solver_status='Optimal（独立日）',energy_capacity_MWh=s['energy_capacity_MWh'],power_capacity_MW=s['power_capacity_MW'],num_steps=len(data))
    return pd.concat(outputs,ignore_index=True),row

def search_grid(data,s,t,e,progress=None):
    if len(data)!=24:raise ValueError('网格寻优仅适用于24h输入，不自动截断长序列。')
    validate_parameters(s,t,e);rows=[]
    for i,(energy,power) in enumerate(generate_candidates(range(0,101,10),range(5,51,5))):
        _,row,_=evaluate_candidate(data,s,t,e,energy,power);rows.append(row)
        if progress:progress((i+1)/101)
    return pd.DataFrame(rows)

def csv_bytes(table):return table.to_csv(index=False,float_format='%.17g').encode('utf-8-sig')

def dispatch_figure(q):
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],'axes.unicode_minus':False})
    fig,axes=plt.subplots(3,1,figsize=(11,7),sharex=True,gridspec_kw={'height_ratios':[2,1,1]})
    charge='charge' if 'charge' in q else 'storage_charge';discharge='discharge' if 'discharge' in q else 'storage_discharge'
    renewable=q.wind_used+q.solar_used if 'wind_used' in q else q.renewable_used
    for name,label,color in [('load','负荷','#163b4a'),('thermal','火电','#cb7b25'),(charge,'充电','#23796b'),(discharge,'放电','#aa4850')]:
        axes[0].plot(q.hour,q[name],label=label,color=color,lw=1.5)
    axes[0].plot(q.hour,renewable,label='新能源已用',color='#719637',lw=1.3);axes[0].legend(ncol=5);axes[0].set_ylabel('功率 MW')
    axes[1].plot(q.hour,q.soc,color='#23796b');axes[1].set(ylabel='期末 SOC',ylim=(0,1))
    axes[2].plot(q.hour,q.balance_error_MW,color='#163b4a');axes[2].set(ylabel='平衡残差 MW',xlabel='小时（气象输入为UTC）')
    for ax in axes:ax.grid(alpha=.16)
    fig.tight_layout();return fig

def png_bytes(fig):
    stream=BytesIO();fig.savefig(stream,format='png',dpi=130);return stream.getvalue()

def grid_figure(table):
    q=table[table.energy_capacity_MWh>0].pivot(index='energy_capacity_MWh',columns='power_capacity_MW',values='total_cost_CNY')
    fig,ax=plt.subplots(figsize=(8,5));im=ax.imshow(q,origin='lower',aspect='auto',cmap='viridis')
    ax.set_xticks(range(len(q.columns)),[f'{x:g}' for x in q.columns]);ax.set_yticks(range(len(q.index)),[f'{x:g}' for x in q.index])
    ax.set(xlabel='功率 MW',ylabel='容量 MWh',title='总成本 元/24h（无储能点另见表格）');fig.colorbar(im,ax=ax);fig.tight_layout();return fig
