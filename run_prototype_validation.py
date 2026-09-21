"""AppTest plus saved-source comparisons; human acceptance explicitly pending."""
import argparse
from io import BytesIO
import importlib.metadata
import json
import os
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
import numpy as np
import pandas as pd
from PIL import Image
from streamlit.testing.v1 import AppTest
from src.study_runtime import ROOT,StudyRun,configuration,dump,sha
from src.prototype_service import BUILTINS,read_input,dispatch,csv_bytes,dispatch_figure,png_bytes,parameters_from_json
import matplotlib.pyplot as plt

def equal(a,b):
    pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,atol=1e-6,rtol=0)
    numeric=a.select_dtypes(include='number').columns.intersection(b.select_dtypes(include='number').columns)
    return float(np.nanmax(np.abs(a[numeric].to_numpy()-b[numeric].to_numpy())))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='U13R01-v01');a=p.parse_args()
    run=StudyRun('U13R01-consistent-prototype','prototype',a.run_id);_,s,t,e=configuration();checks={}
    run.manifest['packages']['streamlit']=importlib.metadata.version('streamlit');run.manifest['source_sha256']['web/app.py']=sha(ROOT/'web/app.py')
    try:
        app=AppTest.from_file(str(ROOT/'web/app.py'),default_timeout=180).run()
        if app.exception:raise AssertionError(str(app.exception))
        app.button(key='solve').click().run()
        if app.exception or app.error:raise AssertionError(str(app.exception)+str(app.error))
        q,row=app.session_state['dispatch_result'];checks['milp_24h_max_diff']=equal(q,pd.read_csv(ROOT/'results/optimization/U06R01-v03/main_hourly.csv'))
        q.to_csv(run.out/'ui_milp_24h.csv',index=False,float_format='%.17g')
        app.button(key='add_comparison').click().run();checks['comparison_rows']=len(app.session_state['comparisons'])
        fig=dispatch_figure(q);raw=png_bytes(fig);plt.close(fig);(run.out/'dispatch_export.png').write_bytes(raw)
        with Image.open(BytesIO(raw)) as im:im.verify()
        checks['csv_roundtrip_max_diff']=equal(q,pd.read_csv(BytesIO(csv_bytes(q))))
        app.radio(key='mode').set_value('规则').run();app.button(key='solve').click().run()
        q,row=app.session_state['dispatch_result'];checks['rule_24h_max_diff']=equal(q,pd.read_csv(ROOT/'results/capacity_sensitivity/E40_P20_hourly.csv'))
        baseline=pd.read_csv(ROOT/'results/capacity_sensitivity/summary.csv').set_index('scenario').loc['E40_P20']
        cols=['renewable_utilization_pct','curtailment_rate_pct','curtailment_MWh','thermal_generation_MWh','load_shedding_MWh','storage_charge_MWh','storage_discharge_MWh','storage_utilization_pct']
        error=max(abs(row[c]-baseline[c]) for c in cols)
        if error>=1e-6:raise ValueError('Rule summary differs')
        checks['rule_summary_max_diff']=float(error)
        app.number_input(key='energy_capacity_MWh').set_value(-1).run()
        if not app.error or app.exception:raise AssertionError('Negative capacity not handled')
        checks['negative_capacity_prompt']=True
        app.number_input(key='energy_capacity_MWh').set_value(40).run()
        for raw in [b'',b'hour,load,wind,solar\n']:
            try:read_input(BytesIO(raw))
            except (ValueError,pd.errors.EmptyDataError):pass
            else:raise AssertionError('Empty CSV accepted')
        checks['empty_csv_rejected']=True
        for name in BUILTINS:checks['input_rows_'+name]=len(read_input(ROOT/BUILTINS[name]))
        app.radio(key='mode').set_value('MILP').run();app.selectbox(key='source').set_value('168h 气象估计').run();app.button(key='solve').click().run()
        if app.exception or app.error:raise AssertionError(str(app.exception)+str(app.error))
        q,row=app.session_state['dispatch_result'];reference,_=run.case('cli_168h',read_input(ROOT/BUILTINS['168h 气象估计']),s,t,e)
        checks['milp_168h_max_diff']=equal(q,reference);q.to_csv(run.out/'ui_milp_168h.csv',index=False,float_format='%.17g')
        if not app.button(key='grid').disabled:raise AssertionError('Long grid not disabled')
        app.selectbox(key='source').set_value('24h 构造算例').run();app.button(key='grid').click().run(timeout=180)
        if app.exception or app.error:raise AssertionError(str(app.exception)+str(app.error))
        grid=app.session_state['grid_result'];grid.to_csv(run.out/'ui_grid.csv',index=False,float_format='%.17g')
        baseline=pd.read_csv(ROOT/'results/grid_search/U09R01-v01/summary.csv')
        cols=['energy_capacity_MWh','power_capacity_MW','total_cost_CNY','renewable_utilization_pct','curtailment_MWh']
        order=['energy_capacity_MWh','power_capacity_MW']
        checks['grid_max_diff']=equal(grid[cols].sort_values(order).reset_index(drop=True),baseline[cols].sort_values(order).reset_index(drop=True))
        checks['png_verified']=True;checks['manual_user_confirmation']=False;checks['actual_browser_confirmation']=False
        dump(run.out/'checks.json',checks)
        run.finish('inconclusive',checks)
    except Exception as exc:
        run.manifest.update(status='blocked',verdict='invalid',error=repr(exc));dump(run.out/'failure.json',dict(error=repr(exc)));dump(run.out/'run_manifest.json',run.manifest);raise

if __name__=='__main__':main()
