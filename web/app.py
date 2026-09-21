"""Local-only research interface; model equations live in src, never here."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from src.study_runtime import ROOT,configuration
from src.economic_model import EconomicParameters
from src.prototype_service import (BUILTINS,read_input,parameters_from_json,validate_parameters,dispatch,search_grid,csv_bytes,dispatch_figure,png_bytes,grid_figure)

st.set_page_config(page_title='风光储 · 研究工作台',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.stApp{background:#f4f3ed;color:#193b43} [data-testid="stSidebar"]{background:#e5eae4;border-right:1px solid #b8c8be}
h1,h2,h3{font-family:"Microsoft YaHei",serif!important;letter-spacing:.035em} .block-container{padding-top:2.3rem;max-width:1440px}
[data-testid="stMetric"]{border-top:3px solid #257265;padding:12px 4px;background:transparent}
.eyebrow{font:600 12px Consolas,monospace;color:#287368;letter-spacing:.17em}.lede{color:#5b6e6b;max-width:850px;font-size:16px}
</style>''',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">DACHUANG / ENERGY BALANCE LAB</div>',unsafe_allow_html=True)
st.title('风光储 · 研究工作台')
st.markdown('<p class="lede">从逐时平衡到储能容量配置。保留约束、核对结果，再讨论结论。</p>',unsafe_allow_html=True)
st.caption('研究原型 · 构造算例（非真实电网数据） · NASA输入仅气象估计，负荷仍为构造形状')
_,s,t,e=configuration()
st.sidebar.header('实验设置')
source=st.sidebar.selectbox('数据来源',list(BUILTINS)+['上传 CSV'],key='source')
upload=st.sidebar.file_uploader('风光荷 CSV',type=['csv'],key='data_upload') if source=='上传 CSV' else None
with st.sidebar.expander('导入参数 JSON'):
    imported=st.file_uploader('会话参数',type=['json'],key='parameter_upload')
    if imported:
        try:
            s,t,e=parameters_from_json(imported.getvalue())
            import_id=hashlib.sha256(imported.getvalue()).hexdigest()
            if st.session_state.get('parameter_import_id')!=import_id:
                for key,value in {**s,**t,**asdict(e)}.items():st.session_state[key]=float(value)
                st.session_state['parameter_import_id']=import_id
        except (ValueError,KeyError,TypeError) as exc:st.error(f'参数文件无效：{exc}');st.stop()
mode=st.sidebar.radio('调度模式',['MILP','规则'],horizontal=True,key='mode')
with st.sidebar.expander('储能容量与状态',expanded=True):
    labels={'energy_capacity_MWh':'能量容量 (MWh)','power_capacity_MW':'功率容量 (MW)','soc_initial':'初始 SOC','soc_min':'最低 SOC','soc_max':'最高 SOC','eta_charge':'充电效率','eta_discharge':'放电效率'}
    s={k:st.number_input(label,value=float(s[k]),format='%.4f',key=k) for k,label in labels.items()}
with st.sidebar.expander('火电约束'):
    labels={'thermal_min_MW':'最低出力 (MW)','thermal_max_MW':'最高出力 (MW)','thermal_ramp_MW_per_h':'爬坡 (MW/h)'}
    t={k:st.number_input(label,value=float(t[k]),key=k) for k,label in labels.items()}
with st.sidebar.expander('经济参数（示例值）'):
    costs={k:st.number_input(k,value=float(v),format='%.6f',key=k) for k,v in asdict(e).items()}
try:
    e=EconomicParameters(**costs);validate_parameters(s,t,e)
    if source=='上传 CSV' and upload is None:st.info('请上传包含 hour、load、wind、solar 的 CSV。');st.stop()
    data=read_input(upload if source=='上传 CSV' else ROOT/BUILTINS[source])
except Exception as exc:
    st.error(f'输入校验失败：{exc}');st.stop()
payload=dict(storage=s,thermal=t,economics=asdict(e));parameter_json=json.dumps(payload,ensure_ascii=False,indent=2)
st.sidebar.download_button('导出当前参数',parameter_json,'parameters.json','application/json')
st.sidebar.caption('参数只作用于本次会话，不修改冻结配置。')
signature=hashlib.sha256(csv_bytes(data)+parameter_json.encode()+mode.encode()).hexdigest()
if st.session_state.get('signature')!=signature:
    st.session_state['signature']=signature;st.session_state.pop('dispatch_result',None);st.session_state.pop('grid_result',None)
st.session_state.setdefault('comparisons',[])
tabs=st.tabs(['01 / 调度验证','02 / 容量寻优','03 / 方案对比','04 / 数据与说明'])
with tabs[0]:
    left,right=st.columns([3,1]);left.subheader('逐时调度与约束校验')
    right.caption(f'{len(data)} 小时 · {mode} · 本机计算')
    if mode=='规则':st.info('规则模式无火电最低出力、爬坡及期末归位约束，不与MILP混作同一基准。')
    elif len(data)>168:st.info('独立日模式：每天初末SOC归位，无跨日储能耦合。')
    else:st.caption('MILP：火电上下限与爬坡、充放电互斥、整段初末SOC归位。')
    if st.button('计算调度',type='primary',key='solve'):
        st.session_state.pop('dispatch_result',None)
        bar=st.progress(0)
        try:
            with st.spinner('求解并进行物理与成本校验…'):result=dispatch(mode,data,s,t,e,bar.progress)
            st.session_state['dispatch_result']=result;bar.progress(1.)
        except Exception as exc:st.error(f'计算停止，未发布结果：{exc}')
    if 'dispatch_result' in st.session_state:
        q,row=st.session_state['dispatch_result'];st.success(str(row['solver_status']))
        cols=st.columns(4)
        for col,label,key,suffix in zip(cols,['新能源消纳率','弃电量','缺供电量','总成本'],['renewable_utilization_pct','curtailment_MWh','load_shedding_MWh' if 'load_shedding_MWh' in row else 'unserved_MWh','total_cost_CNY'],['%',' MWh',' MWh',' 元']):
            col.metric(label,f"{row[key]:,.3f}{suffix}")
        fig=dispatch_figure(q);st.pyplot(fig);picture=png_bytes(fig);plt.close(fig)
        a,b,c,d=st.columns(4)
        a.download_button('逐时 CSV',csv_bytes(q),'dispatch.csv','text/csv')
        b.download_button('汇总 CSV',csv_bytes(pd.DataFrame([row])),'summary.csv','text/csv')
        c.download_button('调度图 PNG',picture,'dispatch.png','image/png')
        if d.button('加入方案对比',key='add_comparison'):
            st.session_state['comparisons'].append(dict(source=source,mode=mode,input_parameters_sha256=signature,parameters_json=parameter_json,**row));st.success('已加入当前会话对比。')
        with st.expander('逐时原始结果'):st.dataframe(q,hide_index=True)
with tabs[1]:
    st.subheader('容量 × 功率联合寻优')
    st.caption('固定101候选：无储能(0,0)及容量10—100MWh、功率5—50MW的离散组合。仅支持24h，不声称连续全局最优。')
    if st.button('运行 101 点网格',key='grid',disabled=len(data)!=24):
        st.session_state.pop('grid_result',None)
        bar=st.progress(0)
        try:
            with st.spinner('逐候选调用相同MILP和成本核算…'):st.session_state['grid_result']=search_grid(data,s,t,e,bar.progress)
        except Exception as exc:st.error(f'网格计算停止：{exc}')
    if len(data)!=24:st.info('长时段网格未纳入本次验证，请选择24h输入。')
    if 'grid_result' in st.session_state:
        table=st.session_state['grid_result'];best=table.loc[table.total_cost_CNY.idxmin()]
        st.success(f'网格最优：{best.energy_capacity_MWh:g} MWh / {best.power_capacity_MW:g} MW · {best.total_cost_CNY:,.2f} 元/24h')
        fig=grid_figure(table);st.pyplot(fig);picture=png_bytes(fig);plt.close(fig)
        st.download_button('网格 CSV',csv_bytes(table),'grid.csv','text/csv');st.download_button('网格图 PNG',picture,'grid.png','image/png')
        st.dataframe(table,hide_index=True)
with tabs[2]:
    st.subheader('保留假设，再比较结果')
    st.warning('不同输入长度、参数和调度模式不能直接作优劣结论；总成本按各自仿真时段计。')
    if st.session_state['comparisons']:
        table=pd.DataFrame(st.session_state['comparisons']);st.dataframe(table,hide_index=True)
        st.bar_chart(table[['total_cost_CNY']]);st.download_button('对比 CSV',csv_bytes(table),'comparison.csv','text/csv')
    else:st.info('计算调度后，点击“加入方案对比”保存当前结果。')
with tabs[3]:
    st.subheader('输入与研究边界');st.dataframe(data,hide_index=True);st.download_button('输入 CSV',csv_bytes(data),'input.csv','text/csv')
    st.markdown('功率单位 MW，hour 连续且步长为1h。NASA数据使用UTC；负荷为构造形状，不是实测负荷。年度数据采用逐日独立近似。')
    st.markdown('典型日近似未通过1个百分点标准；GA成本接近网格，但未体现评估次数加速。原型不构成实际电网投资建议。')
    st.caption('失败不显示为成功；修改输入或参数后，旧调度和旧网格结果自动失效。人工操作验收仍待用户完成。')
