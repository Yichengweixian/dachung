"""U08 matrix figures from saved summary data."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_matrix(summary, output_dir):
    output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    specs=[('renewable_utilization_pct','Renewable utilization (%)','renewable_utilization.png'),
           ('curtailment_rate_pct','Curtailment rate (%)','curtailment_rate.png'),
           ('total_cost_CNY','24-hour total cost (10,000 CNY)','total_cost.png')]
    paths=[]
    for metric,label,name in specs:
        fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
        for capacity,group in summary.groupby('energy_capacity_MWh'):
            y=group.sort_values('renewable_factor')[metric]
            if metric=='total_cost_CNY': y=y/10000
            ax.plot(sorted(group.renewable_factor),y,marker='o',linewidth=2,label=f'{capacity:g} MWh')
        ax.set_xlabel('Wind and solar output factor'); ax.set_ylabel(label)
        ax.grid(alpha=.3); ax.legend(title='Storage'); ax.set_xticks([.8,1.,1.2,1.4])
        path=output_dir/name; fig.savefig(path,dpi=180,facecolor='white'); plt.close(fig); paths.append(path)
    return paths
