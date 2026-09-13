"""从summary.csv中的实际数值绘制四张容量敏感性图。"""

import numpy as np

from .plot_results import plt, font_manager


def plot_capacity_sensitivity(summary, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    data = summary.sort_values("energy_capacity_MWh")
    x = data.energy_capacity_MWh.to_numpy()
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    chinese = next((f for f in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if f in fonts), None)
    plt.rcParams["font.family"] = chinese or "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    xlabel = "储能能量容量 / MWh" if chinese else "Storage energy capacity / MWh"
    powers = sorted(set(data.loc[data.energy_capacity_MWh > 0, "power_capacity_MW"]))
    power_text = ", ".join(f"{p:g}" for p in powers)
    initial_socs = sorted(set(data.loc[data.energy_capacity_MWh > 0, "initial_soc"].dropna()))
    soc_text = ", ".join(f"{soc * 100:g}%" for soc in initial_socs)
    footer = (f"非零容量场景功率固定 {power_text} MW；初始SOC {soc_text}，期末未强制归位。" if chinese else
              f"Nonzero storage power: {power_text} MW. Initial SOC {soc_text}; no terminal target.")

    def style(ax, ylabel):
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.grid(axis="y", color="#DFE4E9", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)

    charts = [
        ("renewable_utilization_pct", "fig1_renewable_utilization.png", "新能源消纳率", "Renewable utilization", "%", "#167E69"),
        ("curtailment_rate_pct", "fig2_curtailment_rate.png", "弃风弃光率", "Curtailment rate", "%", "#C07726"),
        ("thermal_generation_MWh", "fig3_thermal_generation.png", "火电发电量", "Thermal generation", "MWh", "#3179AA"),
    ]
    paths = []
    for index, (column, filename, zh, en, unit, color) in enumerate(charts, 1):
        title = zh if chinese else en
        fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
        y = data[column].to_numpy()
        ax.plot(x, y, color=color, marker="o", markersize=7, linewidth=2.5)
        for xx, yy in zip(x, y):
            ax.annotate(f"{yy:.2f}", (xx, yy), xytext=(0, 10), textcoords="offset points",
                        ha="center", color=color, fontsize=11)
        margin = max(float(np.ptp(y)) * 0.32, 0.5)
        ax.set_ylim(max(0, y.min() - margin), y.max() + margin)
        ax.set_title(f"图{index}  储能容量与{title}" if chinese else f"Figure {index}  Capacity vs {title.lower()}", fontsize=16, pad=15)
        style(ax, f"{title} / {unit}")
        fig.supxlabel(footer, fontsize=9, color="#596675")
        path = output_dir / filename
        fig.savefig(path, dpi=180, facecolor="white")
        plt.close(fig)
        paths.append(path)

    # 不将百分比与MWh放进同一纵轴，不虚构综合评分。八个指标按单位分面。
    fig, axes = plt.subplots(2, 4, figsize=(17, 9), layout="constrained")
    panels = [
        ("renewable_utilization_pct", "新能源消纳率", "Renewable utilization", "%"),
        ("curtailment_rate_pct", "弃风弃光率", "Curtailment rate", "%"),
        ("curtailment_MWh", "弃风弃光电量", "Curtailed energy", "MWh"),
        ("thermal_generation_MWh", "火电发电量", "Thermal generation", "MWh"),
        ("load_shedding_MWh", "失负荷量", "Unserved energy", "MWh"),
        ("storage_charge_MWh", "储能充电量", "Storage charge", "MWh"),
        ("storage_discharge_MWh", "储能放电量", "Storage discharge", "MWh"),
        ("storage_utilization_pct", "储能利用率（活跃时长）", "Storage active-time ratio", "%"),
    ]
    colors = plt.get_cmap("Blues")(np.linspace(0.35, 0.9, len(data)))
    positions = np.arange(len(data))
    for ax, (column, zh, en, unit) in zip(axes.flat, panels):
        values = data[column].to_numpy()
        mask = np.isfinite(values)
        ax.bar(positions[mask], values[mask], width=0.65, color=colors[mask], zorder=3)
        maximum = max(float(np.nanmax(values)) if mask.any() else 0, 1)
        ax.set_ylim(0, maximum * 1.25)
        for i, value in enumerate(values):
            label = f"{value:.2f}" if np.isfinite(value) else ("不适用" if chinese else "n/a")
            ax.text(i, (value if np.isfinite(value) else 0) + maximum * 0.03,
                    label, ha="center", va="bottom", fontsize=8)
        ax.set_title(zh if chinese else en, fontsize=12, pad=12)
        ax.set_xticks(positions, [f"{e:g}" for e in x])
        ax.set_xlabel("容量 / MWh" if chinese else "Capacity / MWh")
        ax.set_ylabel(unit)
        ax.grid(axis="y", color="#DFE4E9", linewidth=0.8, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("图4  不同储能容量的八项指标对比" if chinese else "Figure 4  Storage capacity comparison across eight metrics", fontsize=19)
    fig.supxlabel(footer, fontsize=10, color="#596675")
    path = output_dir / "fig4_comprehensive_bars.png"
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)
    paths.append(path)
    return paths
