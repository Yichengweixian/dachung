"""使用matplotlib绘制输入曲线；后续可扩展调度与SOC图。"""

import matplotlib

matplotlib.use("Agg")  # 保存图片，无需弹出桌面窗口。
import matplotlib.pyplot as plt
from matplotlib import font_manager


def plot_input_profiles(data, output_path):
    """从CSV读回的数据绘制四条曲线，确保图片与数据一致。"""
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    chinese = next((f for f in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if f in fonts), None)
    plt.rcParams["font.family"] = chinese or "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    labels = ["负荷", "风电可用出力", "光伏可用出力", "风光总可用出力"] if chinese else [
        "Load", "Available wind", "Available solar", "Wind + solar"
    ]
    fig, ax = plt.subplots(figsize=(12, 6.5), layout="constrained")
    total = data.wind + data.solar
    curves = [data.load, data.wind, data.solar, total]
    colors = ["#24364B", "#2479B5", "#DD8B13", "#15816B"]
    for i, (curve, color, label) in enumerate(zip(curves, colors, labels)):
        ax.plot(data.hour, curve, color=color, label=label, linewidth=2.3,
                marker="o" if i < 3 else "D", markersize=4,
                linestyle="--" if i == 3 else "-")
    ax.set_title("24小时风光荷基础测试数据" if chinese else "24-hour synthetic power profiles", fontsize=17, pad=18)
    ax.set_xlabel("小时（0—23）" if chinese else "Hour (0-23)", fontsize=12)
    ax.set_ylabel("功率 / MW" if chinese else "Power / MW", fontsize=12)
    ax.set_xticks(range(24))
    ax.set_xlim(-0.3, 23.3)
    ax.set_ylim(0, max(data.load.max(), total.max()) * 1.20)
    ax.grid(axis="y", color="#DCE1E7", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=10)
    fig.supxlabel("构造算例 · 非真实电网数据 · 每个数据点代表1小时平均功率" if chinese else
                  "Synthetic example, not measured grid data. Each point represents one-hour average power.", fontsize=10, color="#596675")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white")
    plt.close(fig)


def plot_no_storage_balance(result, output_path, thermal_max_MW):
    """上图显示实际供给组成，下图单列弃电与失负荷功率。"""
    fonts = {font.name for font in font_manager.fontManager.ttflist}
    chinese = next((f for f in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if f in fonts), None)
    plt.rcParams["font.family"] = chinese or "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    fig, (ax, gaps) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                  height_ratios=[2.2, 1], layout="constrained")
    hour = result.hour.to_numpy()
    ax.stackplot(hour, result.renewable_used, result.thermal,
                 labels=["新能源实际消纳", "火电出力"] if chinese else ["Renewable used", "Thermal"],
                 colors=["#8CCFB5", "#E8B86B"], alpha=0.85)
    ax.plot(hour, result.load, color="#23354B", marker="o", markersize=3.5,
            linewidth=2.2, label="负荷" if chinese else "Load")
    ax.plot(hour, result.renewable, color="#267CAD", linestyle="--", linewidth=2,
            label="风光总可用出力" if chinese else "Available wind + solar")
    ax.set_title("实际供给组成与负荷（色块之和为实际供给）" if chinese else
                 "Supply composition and load (stacked areas = supplied power)", fontsize=12, loc="left")
    ax.set_ylim(0, max(result.load.max(), result.renewable.max(), 1) * 1.22)
    ax.legend(ncol=2, loc="upper left", frameon=False, fontsize=10)
    gaps.plot(hour, result.curtailment, color="#C06C23", marker="o", markersize=3.5,
              linewidth=2, label="弃风弃光功率" if chinese else "Curtailment")
    gaps.fill_between(hour, 0, result.curtailment, color="#E8B86B", alpha=0.2)
    gaps.plot(hour, result.unserved, color="#B73A57", marker="x", markersize=4,
              linewidth=2, linestyle="--", label="失负荷功率" if chinese else "Unserved load")
    gaps.set_ylim(-max(result.curtailment.max(), result.unserved.max(), 1) * 0.04,
                  max(result.curtailment.max(), result.unserved.max(), 1) * 1.25)
    gaps.legend(loc="upper left", frameon=False, ncol=2)
    for axis in (ax, gaps):
        axis.set_ylabel("功率 / MW" if chinese else "Power / MW")
        axis.grid(axis="y", color="#DCE1E7", linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
    if len(hour) <= 48:
        gaps.set_xticks(hour)
    gaps.set_xlim(hour[0] - 0.2, hour[-1] + 0.2)
    gaps.set_xlabel("小时" if chinese else "Hour")
    fig.suptitle(f"无储能电力平衡  火电上限 {thermal_max_MW:g} MW" if chinese else
                 f"Power balance without storage  Thermal limit {thermal_max_MW:g} MW", fontsize=17)
    fig.supxlabel("构造算例 · 新能源优先消纳 · 失负荷为未满足需求，不计入实际供给" if chinese else
                  "Synthetic example. Renewables first. Unserved demand is not part of actual supply.",
                  fontsize=10, color="#596675")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white")
    plt.close(fig)
