"""U09 figures drawn only from saved CSV results."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


def _font():
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    chinese = next((f for f in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if f in fonts), None)
    plt.rcParams["font.family"] = chinese or "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    return chinese


def plot_heatmap(summary, metric, output_path):
    """Plot the positive-storage 10x10 grid; zero storage is not replicated."""
    chinese = _font()
    grid = summary[summary.energy_capacity_MWh > 0].pivot(
        index="power_capacity_MW", columns="energy_capacity_MWh", values=metric
    ).sort_index(ascending=True)
    if grid.shape != (10, 10) or grid.isna().any().any():
        raise ValueError("Heatmap requires the complete saved 10x10 positive-storage grid")
    values = grid.to_numpy()
    scale = 10000 if metric == "total_cost_CNY" else 1
    shown = values / scale
    fig, ax = plt.subplots(figsize=(10, 7), layout="constrained")
    image = ax.imshow(shown, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(grid.columns)), [f"{x:g}" for x in grid.columns])
    ax.set_yticks(range(len(grid.index)), [f"{x:g}" for x in grid.index])
    ax.set_xlabel("能量容量 E / MWh" if chinese else "Energy capacity E (MWh)")
    ax.set_ylabel("功率容量 P / MW" if chinese else "Power capacity P (MW)")
    if metric == "total_cost_CNY":
        title = "24小时综合成本热力图" if chinese else "24-hour total-cost heatmap"
        label = "综合成本 / 万元" if chinese else "Total cost (10,000 CNY)"
    else:
        title = "新能源消纳率热力图" if chinese else "Renewable-utilization heatmap"
        label = "消纳率 / %" if chinese else "Renewable utilization (%)"
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label=label)
    zero = summary[summary.energy_capacity_MWh == 0].iloc[0]
    footer = (f"零储能基准：{zero[metric]/scale:.3f}{' 万元' if metric == 'total_cost_CNY' else '%'}；"
              "构造算例，非真实电网数据。") if chinese else (
              f"Zero-storage baseline: {zero[metric]/scale:.3f}. Synthetic example, not measured grid data.")
    fig.supxlabel(footer, fontsize=9, color="#596675")
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white"); plt.close(fig)


def plot_best_dispatch(dispatch, best, storage, output_path, dt):
    chinese = _font()
    hour = dispatch.hour.to_numpy()
    boundaries = np.r_[hour[0], hour + dt]
    states = np.r_[dispatch.energy_start_MWh.iloc[0], dispatch.energy_MWh.to_numpy()] / best.energy_capacity_MWh * 100
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=False, layout="constrained")
    supply, flow, soc = axes
    supply.stackplot(hour, dispatch.wind_used + dispatch.solar_used, dispatch.thermal, dispatch.discharge,
                     labels=["新能源", "火电", "储能放电"] if chinese else ["Renewables", "Thermal", "Storage discharge"],
                     colors=["#71BFA3", "#E2B15F", "#D37A35"], alpha=.85)
    supply.plot(hour, dispatch.load + dispatch.charge, color="#24364B", linewidth=2,
                label="负荷+充电" if chinese else "Load + charging")
    flow.bar(hour-.18, dispatch.charge, width=.36, label="充电" if chinese else "Charge", color="#2479B5")
    flow.bar(hour+.18, dispatch.discharge, width=.36, label="放电" if chinese else "Discharge", color="#D28B32")
    soc.plot(boundaries, states, color="#624B9A", marker="o", markersize=3)
    soc.axhspan(storage["soc_min"]*100, storage["soc_max"]*100, color="#ECE8F3", alpha=.5)
    supply.set_ylabel("MW"); flow.set_ylabel("MW"); soc.set_ylabel("SOC / %")
    soc.set_xlabel("小时" if chinese else "Hour")
    for ax in axes:
        ax.grid(axis="y", alpha=.3); ax.spines[["top", "right"]].set_visible(False)
        handles, labels = ax.get_legend_handles_labels()
        if handles: ax.legend(loc="upper left", ncol=3, frameon=False)
    fig.suptitle((f"样本网格最低成本组合：{best.energy_capacity_MWh:g} MWh / {best.power_capacity_MW:g} MW"
                  if chinese else f"Lowest-cost sampled pair: {best.energy_capacity_MWh:g} MWh / {best.power_capacity_MW:g} MW"), fontsize=16)
    fig.supxlabel(("构造的24小时算例，不代表真实工程最优配置。" if chinese else
                   "Synthetic 24-hour example; not a real-project optimum."), fontsize=9, color="#596675")
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white"); plt.close(fig)

