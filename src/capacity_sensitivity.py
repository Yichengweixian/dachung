"""储能能量容量批量试算及相邻场景增量统计，不做最优容量搜索。"""

from dataclasses import replace

import numpy as np
import pandas as pd

from .storage_model import calculate_storage_balance
from .storage_metrics import summarize_storage
from .storage_validation import validate_storage_result


def run_capacity_scenarios(data, base_storage, capacities, fixed_power_MW=20.0,
                           thermal_max_MW=120.0, time_step_hours=1.0):
    """每组从同一初始SOC比例重新开始；不继承上一场景的期末电量。"""
    if not capacities or any(not np.isfinite(e) or e < 0 for e in capacities):
        raise ValueError("容量列表不能为空，且每个容量必须为有限非负数。")
    if len(set(capacities)) != len(capacities):
        raise ValueError("容量场景不能重复。")
    if not np.isfinite(fixed_power_MW) or fixed_power_MW <= 0:
        raise ValueError("非零容量场景的固定功率必须为有限正数。")
    summaries, scenarios = [], {}
    for energy in sorted(capacities):
        storage = replace(base_storage, energy_capacity_MWh=float(energy),
                          power_capacity_MW=float(fixed_power_MW) if energy > 0 else 0.0)
        result = calculate_storage_balance(data, storage, thermal_max_MW, time_step_hours)
        summary = summarize_storage(result, storage, time_step_hours)
        checks = validate_storage_result(result, summary, storage, thermal_max_MW, time_step_hours)
        name = f"E{energy:g}_P{storage.power_capacity_MW:g}".replace(".", "p")
        summary.insert(0, "scenario", name)
        summary.insert(1, "energy_capacity_MWh", float(energy))
        summary.insert(2, "power_capacity_MW", storage.power_capacity_MW)
        summary["thermal_max_MW"] = thermal_max_MW
        summary["num_steps"] = len(data)
        summary["time_step_hours"] = time_step_hours
        summary["validation_checks_passed"] = len(checks)
        # 这部分电量来自初始库存净减少，不能归因于本日新能源充电。
        summary["initial_inventory_supply_MWh"] = (
            summary.initial_energy_MWh - summary.final_energy_MWh
        ).clip(lower=0) * storage.eta_discharge
        summaries.append(summary)
        scenarios[name] = (storage, result)
    combined = pd.concat(summaries, ignore_index=True)
    first = ["scenario", "energy_capacity_MWh", "power_capacity_MW",
             "renewable_utilization_pct", "curtailment_rate_pct", "curtailment_MWh",
             "thermal_generation_MWh", "load_shedding_MWh", "storage_charge_MWh",
             "storage_discharge_MWh", "storage_utilization_pct"]
    return combined[first + [c for c in combined.columns if c not in first]], scenarios


def calculate_marginal_changes(summary):
    """相邻容量区间的实际差分；正值表示消纳提高、弃电或火电减少。"""
    ordered = summary.sort_values("energy_capacity_MWh")
    rows = []
    for i in range(1, len(ordered)):
        before, after = ordered.iloc[i - 1], ordered.iloc[i]
        step = after.energy_capacity_MWh - before.energy_capacity_MWh
        if step <= 0:
            raise ValueError("边际统计要求容量严格递增。")
        utilization_gain = after.renewable_utilization_pct - before.renewable_utilization_pct
        curtailment_reduction = before.curtailment_MWh - after.curtailment_MWh
        thermal_reduction = before.thermal_generation_MWh - after.thermal_generation_MWh
        rows.append({
            "from_capacity_MWh": before.energy_capacity_MWh,
            "to_capacity_MWh": after.energy_capacity_MWh,
            "capacity_increment_MWh": step,
            "utilization_gain_percentage_points": utilization_gain,
            "curtailment_reduction_MWh": curtailment_reduction,
            "thermal_reduction_MWh": thermal_reduction,
            "utilization_gain_pp_per_MWh_capacity": utilization_gain / step,
            "curtailment_reduction_MWh_per_MWh_capacity": curtailment_reduction / step,
            "thermal_reduction_MWh_per_MWh_capacity": thermal_reduction / step,
        })
    return pd.DataFrame(rows)
