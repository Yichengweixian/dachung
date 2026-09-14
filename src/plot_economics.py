"""绘制已给定容量场景的综合成本曲线，突出样本内最低值。"""

import numpy as np

from .plot_results import plt, font_manager


def plot_capacity_cost(summary, output_path, initial_soc):
    data = summary.sort_values("energy_capacity_MWh")
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    chinese = next((f for f in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if f in fonts), None)
    plt.rcParams["font.family"] = chinese or "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    x = data.energy_capacity_MWh.to_numpy()
    y = data.total_cost_CNY.to_numpy() / 10000
    lowest = np.isclose(data.total_cost_CNY, data.total_cost_CNY.min(), atol=1e-6, rtol=0)
    hours = ", ".join(f"{h:g}" for h in sorted(set(data.simulation_hours)))
    powers = ", ".join(f"{p:g}" for p in sorted(set(data.loc[data.energy_capacity_MWh > 0, "power_capacity_MW"])))
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    ax.plot(x, y, color="#286E9E", marker="o", linewidth=2.5, markersize=7,
            label="综合成本" if chinese else "Total cost")
    ax.scatter(x[lowest], y[lowest], color="#167D65", s=100, zorder=4,
               label="给定场景中的最低成本" if chinese else "Lowest among supplied scenarios")
    for xx, yy in zip(x, y):
        ax.annotate(f"{yy:.3f}", (xx, yy), xytext=(0, 12), textcoords="offset points",
                    ha="center", fontsize=12, color="#245977")
    margin = max(float(np.ptp(y)) * 0.35, 0.1)
    ax.set_ylim(max(0, y.min() - margin), y.max() + margin)
    ax.set_xticks(x)
    ax.set_xlabel("储能能量容量 / MWh" if chinese else "Storage energy capacity / MWh", fontsize=12)
    ax.set_ylabel("仿真时段综合成本 / 万元" if chinese else "Period total cost / 10,000 CNY", fontsize=12)
    ax.set_title(f"储能容量与{hours}小时综合成本" if chinese else f"Storage capacity vs {hours}-hour total cost", fontsize=19, pad=17)
    ax.grid(axis="y", color="#DFE4E9", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False)
    footer = (f"模型测试参数；非零容量功率 {powers} MW；包含投资折算与运维。\n"
              f"初始SOC {initial_soc:.0%}，期末未强制归位；最低样本点不代表最优配置。" if chinese else
              f"Synthetic test parameters; nonzero storage power {powers} MW; allocated investment and O&M included.\n"
              f"Initial SOC {initial_soc:.0%}; no terminal target. Sample minimum is not an optimal sizing result.")
    fig.supxlabel(footer, fontsize=10, color="#596675")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white")
    plt.close(fig)
    return output_path
