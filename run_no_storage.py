"""第3阶段入口：读取已有CSV，执行无储能平衡、统计、校验及绘图。"""

import json

import pandas as pd

from src.paths import CONFIG_DIR, PROJECT_ROOT, RESULTS_DIR, FIGURES_DIR
from src.data_loader import load_input_data
from src.balance_model import calculate_no_storage_balance
from src.metrics import summarize_no_storage
from src.validation import validate_no_storage_result
from src.plot_results import plot_no_storage_balance


def main():
    with (CONFIG_DIR / "simulation.json").open(encoding="utf-8") as file:
        time_config = json.load(file)
    with (CONFIG_DIR / "no_storage.json").open(encoding="utf-8") as file:
        model_config = json.load(file)
    dt = time_config["time_step_hours"]
    maximum = model_config["thermal_max_MW"]
    data = load_input_data(PROJECT_ROOT / "data" / "input_24h.csv", time_config["num_steps"], dt)
    result = calculate_no_storage_balance(data, maximum, dt)
    summary = summarize_no_storage(result, dt)
    checks = validate_no_storage_result(result, summary, maximum, dt)
    summary.insert(0, "num_steps", len(data))
    summary.insert(1, "time_step_hours", dt)
    summary.insert(2, "thermal_max_MW", maximum)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    hourly_path = RESULTS_DIR / "no_storage_hourly.csv"
    summary_path = RESULTS_DIR / "no_storage_summary.csv"
    result.to_csv(hourly_path, index=False, float_format="%.8f", encoding="utf-8")
    summary.to_csv(summary_path, index=False, float_format="%.8f", encoding="utf-8", na_rep="")
    # 用保存后的数值校验并绘图，避免CSV与图片使用不同数据。
    saved = pd.read_csv(hourly_path)
    saved_summary = pd.read_csv(summary_path)
    validate_no_storage_result(saved, saved_summary, maximum, dt)
    image_path = FIGURES_DIR / "no_storage_balance.png"
    plot_no_storage_balance(saved, image_path, maximum)
    print(f"无储能模型完成，{len(checks)}项数值检查通过。火电上限：{maximum:g} MW。")
    print(summary.to_string(index=False))
    print(f"最大功率平衡误差：{saved.balance_error_MW.abs().max():.2e} MW")
    print(f"逐时CSV：{hourly_path}\n汇总CSV：{summary_path}\n电力平衡图：{image_path}")


if __name__ == "__main__":
    main()
