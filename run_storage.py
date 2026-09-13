"""第4阶段：固定40 MWh/20 MW储能规则调度及无储能对比，不做容量优化。"""

import json

import pandas as pd

from src.paths import CONFIG_DIR, PROJECT_ROOT, RESULTS_DIR, FIGURES_DIR
from src.data_loader import load_input_data
from src.balance_model import calculate_no_storage_balance
from src.metrics import summarize_no_storage
from src.validation import validate_no_storage_result
from src.storage_model import StorageParameters, calculate_storage_balance
from src.storage_metrics import summarize_storage, compare_storage_to_baseline
from src.storage_validation import validate_storage_result
from src.plot_storage import plot_storage_comparison


def read_config(name):
    with (CONFIG_DIR / name).open(encoding="utf-8") as file:
        return json.load(file)


def main():
    time_config = read_config("simulation.json")
    storage = StorageParameters(**read_config("storage.json"))
    thermal_max = read_config("no_storage.json")["thermal_max_MW"]
    dt = time_config["time_step_hours"]
    data = load_input_data(PROJECT_ROOT / "data/input_24h.csv", time_config["num_steps"], dt)

    baseline = calculate_no_storage_balance(data, thermal_max, dt)
    baseline_summary = summarize_no_storage(baseline, dt)
    validate_no_storage_result(baseline, baseline_summary, thermal_max, dt)
    result = calculate_storage_balance(data, storage, thermal_max, dt)
    summary = summarize_storage(result, storage, dt)
    checks = validate_storage_result(result, summary, storage, thermal_max, dt)
    for name, value in vars(storage).items():
        summary[name] = value
    summary["thermal_max_MW"] = thermal_max
    summary["num_steps"] = len(data)
    summary["time_step_hours"] = dt
    comparison = compare_storage_to_baseline(baseline, summary, storage, thermal_max, dt)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "storage_hourly.csv": result,
        "storage_summary.csv": summary,
        "storage_baseline_hourly.csv": baseline,
        "storage_comparison.csv": comparison,
    }
    for name, table in outputs.items():
        table.to_csv(RESULTS_DIR / name, index=False, float_format="%.10f", encoding="utf-8", na_rep="")
    saved = pd.read_csv(RESULTS_DIR / "storage_hourly.csv")
    saved_summary = pd.read_csv(RESULTS_DIR / "storage_summary.csv")
    saved_baseline = pd.read_csv(RESULTS_DIR / "storage_baseline_hourly.csv")
    saved_comparison = pd.read_csv(RESULTS_DIR / "storage_comparison.csv")
    validate_storage_result(saved, saved_summary, storage, thermal_max, dt)
    validate_no_storage_result(saved_baseline, summarize_no_storage(saved_baseline, dt), thermal_max, dt)
    expected_comparison = compare_storage_to_baseline(saved_baseline, saved_summary, storage, thermal_max, dt)
    pd.testing.assert_frame_equal(saved_comparison, expected_comparison, check_dtype=False, atol=1e-6, rtol=0)
    image_path = FIGURES_DIR / "storage_comparison.png"
    plot_storage_comparison(saved_baseline, saved, saved_summary, storage, image_path, dt)

    print(f"第4阶段完成，储能{len(checks)}项数值检查通过，保存后再次核验通过。")
    columns = ["scenario", "renewable_utilization_pct", "curtailment_MWh", "thermal_generation_MWh",
               "storage_charge_MWh", "storage_discharge_MWh", "storage_utilization_pct", "load_shedding_MWh"]
    print(saved_comparison[columns].to_string(index=False))
    print("储能利用率口径：充电或放电功率大于1e-6 MW的时段占比。")
    row = saved_summary.iloc[0]
    print(f"初始SOC {row.initial_soc:.0%}，期末SOC {row.final_soc:.0%}；"
          f"电量净变化 {row.energy_change_MWh:.4f} MWh，损耗 {row.storage_loss_MWh:.4f} MWh。")
    print(f"逐时结果：{RESULTS_DIR / 'storage_hourly.csv'}")
    print(f"对比表：{RESULTS_DIR / 'storage_comparison.csv'}\n对比图：{image_path}")


if __name__ == "__main__":
    main()
