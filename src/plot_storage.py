"""储能与无储能对比图，读取已保存的逐时结果与汇总表。"""

import numpy as np

from .plot_results import plt, font_manager


def plot_storage_comparison(baseline, result, summary, storage, output_path, time_step_hours=1.0):
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    chinese = next((f for f in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if f in fonts), None)
    plt.rcParams["font.family"] = chinese or "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    names = ["无储能", "有储能"] if chinese else ["No storage", "With storage"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    thermal, curtail, flow, soc = axes.flat
    hour = result.hour.to_numpy()
    colors = ["#8491A1", "#187E69"]
    for table, label, color in zip([baseline, result], names, colors):
        thermal.plot(hour, table.thermal, label=label, color=color, linewidth=2.2, marker="o", markersize=3)
        curtail.plot(hour, table.curtailment, label=label, color=color, linewidth=2.2, marker="o", markersize=3)
    thermal.set_title("火电出力对比" if chinese else "Thermal output")
    curtail.set_title("弃风弃光功率对比" if chinese else "Curtailment")
    flow.bar(hour - 0.18, result.storage_charge, width=0.36, color="#2479B5",
             label="充电" if chinese else "Charge")
    flow.bar(hour + 0.18, result.storage_discharge, width=0.36, color="#D28B32",
             label="放电" if chinese else "Discharge")
    flow.axhline(storage.power_capacity_MW, color="#8793A0", linewidth=1, linestyle="--")
    flow.set_ylim(0, max(storage.power_capacity_MW, 1) * 1.25)
    flow.set_title("储能充放电功率（均取正值）" if chinese else "Storage power (both positive)")

    # N个功率时段有N+1个状态点；0点显示用户给定的初始SOC。
    boundaries = np.r_[hour[0], hour + time_step_hours]
    states = np.r_[result.soc_start.iloc[0], result.soc.to_numpy()] * 100
    if storage.energy_capacity_MWh > 0:
        soc.plot(boundaries, states, color="#624B9A", marker="o", markersize=4, linewidth=2,
                 label="SOC（含初始状态）" if chinese else "SOC including initial state")
        soc.axhspan(storage.soc_min * 100, storage.soc_max * 100, color="#ECE8F3", alpha=0.4)
        for bound in [storage.soc_min, storage.soc_max]:
            soc.axhline(bound * 100, color="#8793A0", linewidth=1, linestyle="--")
    else:
        soc.text(0.5, 0.5, "零容量，SOC不适用" if chinese else "Zero capacity: SOC not applicable",
                 ha="center", transform=soc.transAxes)
    soc.set_ylim(0, 100)
    soc.set_xlim(boundaries[0], boundaries[-1])
    soc.set_title("储能SOC边界时刻" if chinese else "SOC at interval boundaries")
    soc.set_ylabel("SOC / %")
    for ax in axes.flat:
        ax.set_xlabel("小时" if chinese else "Hour")
        ax.grid(axis="y", color="#DFE4E9", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc="upper left", frameon=False, fontsize=10)
        if len(hour) <= 48:
            ax.set_xticks(np.arange(hour[0], boundaries[-1] + 0.01, 2 * time_step_hours))
    for ax in [thermal, curtail, flow]:
        ax.set_ylabel("功率 / MW" if chinese else "Power / MW")
        ax.set_xlim(hour[0] - 0.6, hour[-1] + 0.6)
    for ax, values in [(thermal, baseline.thermal), (curtail, baseline.curtailment)]:
        ax.set_ylim(0, max(values.max(), 1) * 1.25)
    baseline_shed = baseline.unserved.sum() * time_step_hours
    row = summary.iloc[0]
    title = f"无储能与 {storage.energy_capacity_MWh:g} MWh / {storage.power_capacity_MW:g} MW 储能对比"
    if not chinese:
        title = f"No storage vs {storage.energy_capacity_MWh:g} MWh / {storage.power_capacity_MW:g} MW storage"
    fig.suptitle(title, fontsize=18)
    footer = (
        f"失负荷：无储能 {baseline_shed:.2f} / 有储能 {row.load_shedding_MWh:.2f} MWh；"
        f"储能电量 {row.initial_energy_MWh:.2f} → {row.final_energy_MWh:.2f} MWh，期末未强制归位。"
        if chinese else
        f"Unserved energy: baseline {baseline_shed:.2f}, storage {row.load_shedding_MWh:.2f} MWh. "
        f"Stored energy: {row.initial_energy_MWh:.2f} to {row.final_energy_MWh:.2f} MWh; no terminal target."
    )
    fig.supxlabel(footer, fontsize=10, color="#596675")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white")
    plt.close(fig)
