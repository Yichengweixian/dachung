"""第5阶段入口：五组容量试算、检查、汇总与绘图；分析另见docs。"""

import hashlib
import json
import platform
from importlib.metadata import version

import pandas as pd

from src.paths import CONFIG_DIR, PROJECT_ROOT, RESULTS_DIR, FIGURES_DIR
from src.data_loader import load_input_data
from src.storage_model import StorageParameters
from src.capacity_sensitivity import run_capacity_scenarios, calculate_marginal_changes
from src.storage_validation import validate_storage_result
from src.plot_capacity_sensitivity import plot_capacity_sensitivity


def main():
    configs = {}
    for name in ["storage.json", "simulation.json", "no_storage.json", "capacity_sensitivity.json"]:
        configs[name] = json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))
    settings = configs["capacity_sensitivity.json"]
    time_config = configs["simulation.json"]
    base_storage = StorageParameters(**configs["storage.json"])
    dt = time_config["time_step_hours"]
    thermal_max = configs["no_storage.json"]["thermal_max_MW"]
    input_path = PROJECT_ROOT / "data/input_24h.csv"
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    data = load_input_data(input_path, time_config["num_steps"], dt)
    summary, scenarios = run_capacity_scenarios(
        data, base_storage, settings["energy_capacities_MWh"],
        settings["fixed_power_capacity_MW"], thermal_max, dt,
    )
    output_dir = RESULTS_DIR / "capacity_sensitivity"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.csv"
    summary.to_csv(summary_path, index=False, float_format="%.10f", encoding="utf-8", na_rep="")
    saved_summary = pd.read_csv(summary_path)
    pd.testing.assert_frame_equal(summary, saved_summary, check_dtype=False, atol=1e-6, rtol=0)
    for name, (storage, dispatch) in scenarios.items():
        path = output_dir / f"{name}_hourly.csv"
        dispatch.to_csv(path, index=False, float_format="%.10f", encoding="utf-8", na_rep="")
        saved = pd.read_csv(path)
        row = saved_summary.loc[saved_summary.scenario == name]
        validate_storage_result(saved, row, storage, thermal_max, dt)
    # 从已保存的汇总表计算相邻容量增量，避免依赖显示四舍五入后的数字。
    marginal = calculate_marginal_changes(saved_summary)
    marginal.to_csv(output_dir / "marginal_changes.csv", index=False, float_format="%.10f", encoding="utf-8")
    paths = plot_capacity_sensitivity(saved_summary, FIGURES_DIR / "capacity_sensitivity")
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != input_hash:
        raise RuntimeError("输入CSV在本次运行期间发生变化，请检查后重新运行。")
    manifest = {
        "input_file": "data/input_24h.csv", "input_sha256": input_hash,
        "configs": configs, "python_version": platform.python_version(),
        "packages": {name: version(name) for name in ["numpy", "pandas", "matplotlib"]},
        "power_rule": "Fixed power for nonzero energy capacity; zero power for zero capacity.",
        "terminal_soc_target": None,
        "storage_utilization_definition": "Fraction of hours with charging or discharging power > 1e-6 MW.",
        "all_scenarios_validated_before_and_after_csv_export": True,
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("第5阶段完成，所有场景及CSV读回检查通过。")
    print(saved_summary.iloc[:, :11].to_string(index=False))
    print("相邻容量边际变化：")
    print(marginal.to_string(index=False))
    print(f"汇总：{summary_path}")
    for path in paths:
        print(f"图：{path}")
    print("研究分析独立存放于docs/capacity_sensitivity_analysis.md，本入口不生成优化结论。")


if __name__ == "__main__":
    main()
