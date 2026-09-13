"""第6阶段：重新运行五组规则调度，核算示例成本并保存曲线。"""

import hashlib
import json
import platform
from importlib.metadata import version

import numpy as np
import pandas as pd

from src.paths import CONFIG_DIR, PROJECT_ROOT, RESULTS_DIR, FIGURES_DIR
from src.data_loader import load_input_data
from src.storage_model import StorageParameters
from src.capacity_sensitivity import run_capacity_scenarios
from src.storage_validation import validate_storage_result
from src.economic_model import EconomicParameters, evaluate_system_costs, validate_cost_results
from src.plot_economics import plot_capacity_cost


def main():
    names = ["simulation.json", "no_storage.json", "storage.json", "capacity_sensitivity.json", "economics.json"]
    configs = {name: json.loads((CONFIG_DIR / name).read_text(encoding="utf-8")) for name in names}
    time_config = configs["simulation.json"]
    settings = configs["capacity_sensitivity.json"]
    storage = StorageParameters(**configs["storage.json"])
    economic = EconomicParameters(**configs["economics.json"]["parameters"])
    thermal_max = configs["no_storage.json"]["thermal_max_MW"]
    dt = time_config["time_step_hours"]
    input_path = PROJECT_ROOT / "data/input_24h.csv"
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    data = load_input_data(input_path, time_config["num_steps"], dt)
    dispatch_summary, scenarios = run_capacity_scenarios(
        data, storage, settings["energy_capacities_MWh"], settings["fixed_power_capacity_MW"], thermal_max, dt
    )
    costs = evaluate_system_costs(dispatch_summary, economic)
    cost_checks = validate_cost_results(costs, economic)

    output_dir = RESULTS_DIR / "economics"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.csv"
    # 保留17位有效数字：年化系数/时间比例乘大额投资时，提前舍入会放大误差。
    costs.to_csv(summary_path, index=False, float_format="%.17g", encoding="utf-8", na_rep="")
    saved_costs = pd.read_csv(summary_path, float_precision="round_trip")
    pd.testing.assert_frame_equal(costs, saved_costs, check_dtype=False, atol=1e-6, rtol=0)
    validate_cost_results(saved_costs, economic)
    dispatch_path = output_dir / "dispatch_summary.csv"
    dispatch_summary.to_csv(dispatch_path, index=False, float_format="%.17g", encoding="utf-8", na_rep="")
    saved_dispatch_summary = pd.read_csv(dispatch_path, float_precision="round_trip")
    pd.testing.assert_frame_equal(dispatch_summary, saved_dispatch_summary, check_dtype=False, atol=1e-6, rtol=0)
    # 读回电量汇总重新计价，核对保存的经济结果确实来自本次调度。
    recomputed = evaluate_system_costs(saved_dispatch_summary, economic)
    pd.testing.assert_frame_equal(saved_costs, recomputed, check_dtype=False, atol=1e-6, rtol=0)
    for name, (parameters, dispatch) in scenarios.items():
        path = output_dir / f"{name}_hourly.csv"
        dispatch.to_csv(path, index=False, float_format="%.17g", encoding="utf-8", na_rep="")
        validate_storage_result(pd.read_csv(path, float_precision="round_trip"), saved_dispatch_summary.loc[saved_dispatch_summary.scenario == name],
                                parameters, thermal_max, dt)
    plot_path = plot_capacity_cost(saved_costs, FIGURES_DIR / "economics/capacity_vs_total_cost.png", storage.soc_initial)
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != input_hash:
        raise RuntimeError("输入CSV在运行期间发生变化，请核对后重新运行。")
    minimum = float(saved_costs.total_cost_CNY.min())
    lowest = saved_costs.loc[np.isclose(saved_costs.total_cost_CNY, minimum, atol=1e-6, rtol=0)]
    manifest = {
        "input_file": "data/input_24h.csv", "input_sha256": input_hash,
        "configs": configs, "python_version": platform.python_version(),
        "packages": {name: version(name) for name in ["numpy", "pandas", "matplotlib"]},
        "cost_unit": "CNY per simulated period, including allocated capital cost",
        "capital_allocation": "capex * CRF * simulation_hours / hours_per_year",
        "total_cost_terms": ["thermal_cost_CNY", "storage_cost_CNY", "curtailment_cost_CNY", "load_shedding_cost_CNY"],
        "all_dispatch_and_cost_results_validated_after_csv_export": True,
        "cost_checks_passed": list(cost_checks),
        "lowest_supplied_scenarios": lowest.scenario.tolist(),
        "lowest_supplied_cost_CNY": minimum,
        "terminal_soc_target": None,
        "initial_inventory_valuation_included_in_total": False,
        "optimization_performed": False,
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("第6阶段完成：五组场景重新调度，成本与CSV读回检查通过。示例参数不代表文献或市场数据。")
    print(saved_costs.iloc[:, :10].to_string(index=False))
    print(f"给定场景中的最低成本：{', '.join(lowest.scenario)}，{minimum:,.2f}元/仿真时段。")
    print("该结果未约束期末SOC，仅作本次场景比较，不构成最优容量结论。")
    print(f"汇总：{summary_path}")
    print(f"图：{plot_path}")
    print("独立分析：docs/economics_analysis.md")


if __name__ == "__main__":
    main()
