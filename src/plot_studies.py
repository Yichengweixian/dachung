"""Plots derived from saved study tables; headless and reproducible."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"font.sans-serif":["Microsoft YaHei","SimHei","DejaVu Sans"],"axes.unicode_minus":False})

def penetration_plots(summary_path, destination):
    q=pd.read_csv(summary_path); destination.mkdir(parents=True,exist_ok=True)
    for metric,label in [('renewable_utilization_pct','新能源消纳率 (%)'),('curtailment_rate_pct','弃电率 (%)'),('total_cost_CNY','综合成本 (元/24h)')]:
        fig,ax=plt.subplots(figsize=(7,4.5))
        for e,g in q.groupby('energy_capacity_MWh'):
            ax.plot(g.factor,g[metric],marker='o',label=f'{e:g} MWh')
        ax.set(xlabel='风光出力系数',ylabel=label); ax.legend(); ax.grid(alpha=.2);fig.tight_layout()
        fig.savefig(destination/(metric+'.png'),dpi=160);plt.close(fig)

def grid_plots(summary_path, dispatch_path, destination):
    q=pd.read_csv(summary_path); d=pd.read_csv(dispatch_path);destination.mkdir(parents=True,exist_ok=True)
    for metric,label in [('total_cost_CNY','综合成本 (元/24h)'),('renewable_utilization_pct','消纳率 (%)')]:
        table=q[q.energy_capacity_MWh>0].pivot(index='energy_capacity_MWh',columns='power_capacity_MW',values=metric)
        fig,ax=plt.subplots(figsize=(7,5)); im=ax.imshow(table,origin='lower',aspect='auto',cmap='viridis')
        ax.set_xticks(range(len(table.columns)),[f'{v:g}' for v in table.columns]);ax.set_yticks(range(len(table.index)),[f'{v:g}' for v in table.index])
        ax.set(xlabel='储能功率 (MW)',ylabel='储能容量 (MWh)',title=label);fig.colorbar(im,ax=ax);fig.tight_layout()
        fig.savefig(destination/(metric+'_heatmap.png'),dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True)
    for c,label in [('load','负荷'),('thermal','火电'),('charge','充电'),('discharge','放电')]:axes[0].plot(d.hour,d[c],label=label)
    axes[0].set_ylabel('功率 (MW)');axes[0].legend(ncol=4);axes[0].grid(alpha=.2)
    energy=d.energy_start_MWh.iloc[0]/.5
    axes[1].plot(list(d.hour)+[d.hour.iloc[-1]+1],list(d.energy_start_MWh/energy)+[d.energy_MWh.iloc[-1]/energy])
    axes[1].set(xlabel='时刻 (h)',ylabel='SOC');axes[1].grid(alpha=.2);fig.tight_layout()
    fig.savefig(destination/'best_dispatch.png',dpi=160);plt.close(fig)
