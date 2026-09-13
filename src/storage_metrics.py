"""储能电量与使用程度统计，以及相同输入下的无储能对比表。"""

import numpy as np
import pandas as pd

from .metrics import summarize_no_storage

ACTIVE_POWER_TOLERANCE_MW = 1e-6


def summarize_storage(result, storage, time_step_hours=1.0):
    if not np.isfinite(time_step_hours) or time_step_hours <= 0:
        raise ValueError("时间步长必须为有限正数。")
    dt = time_step_hours
    available = float(result.renewable.sum() * dt)
    charge = float(result.storage_charge.sum() * dt)
    discharge = float(result.storage_discharge.sum() * dt)
    active = (result.storage_charge > ACTIVE_POWER_TOLERANCE_MW) | (
        result.storage_discharge > ACTIVE_POWER_TOLERANCE_MW
    )
    charge_loss = (1 - storage.eta_charge) * charge
    discharge_loss = (1 / storage.eta_discharge - 1) * discharge
    initial = float(result.energy_start_MWh.iloc[0])
    final = float(result.energy_end_MWh.iloc[-1])
    used = float(result.renewable_used.sum() * dt)
    curtailed = float(result.curtailment.sum() * dt)
    return pd.DataFrame([{
        "total_load_MWh": float(result.load.sum() * dt),
        "renewable_available_MWh": available,
        "renewable_used_MWh": used,
        "curtailment_MWh": curtailed,
        "thermal_generation_MWh": float(result.thermal.sum() * dt),
        "load_shedding_MWh": float(result.load_shedding.sum() * dt),
        "renewable_utilization_pct": 100 * used / available if available > 0 else np.nan,
        "curtailment_rate_pct": 100 * curtailed / available if available > 0 else np.nan,
        "storage_charge_MWh": charge,
        "storage_discharge_MWh": discharge,
        "storage_active_hours": float(active.sum() * dt),
        "storage_utilization_pct": 100 * float(active.mean()) if storage.energy_capacity_MWh > 0 else np.nan,
        "discharge_turnover_ratio": discharge / storage.energy_capacity_MWh if storage.energy_capacity_MWh > 0 else np.nan,
        "initial_soc": float(result.soc_start.iloc[0]),
        "final_soc": float(result.soc.iloc[-1]),
        "initial_energy_MWh": initial,
        "final_energy_MWh": final,
        "energy_change_MWh": final - initial,
        "charge_loss_MWh": charge_loss,
        "discharge_loss_MWh": discharge_loss,
        "storage_loss_MWh": charge_loss + discharge_loss,
    }])


def compare_storage_to_baseline(baseline, storage_summary, storage, thermal_max_MW, time_step_hours):
    """baseline必须用同一输入与同一火电上限重新计算，不读取历史缓存结果。"""
    base = summarize_no_storage(baseline, time_step_hours).rename(columns={"unserved_MWh": "load_shedding_MWh"})
    for col in storage_summary.columns:
        if col not in base:
            base[col] = np.nan if col in (
                "storage_utilization_pct", "discharge_turnover_ratio", "initial_soc", "final_soc",
                "soc_initial", "soc_min", "soc_max", "eta_charge", "eta_discharge"
            ) else 0.0
    with_storage = storage_summary.copy()
    base.insert(0, "scenario", "no_storage")
    with_storage.insert(0, "scenario", "with_storage")
    base["energy_capacity_MWh"] = base["power_capacity_MW"] = 0.0
    with_storage["energy_capacity_MWh"] = storage.energy_capacity_MWh
    with_storage["power_capacity_MW"] = storage.power_capacity_MW
    comparison = pd.concat([base, with_storage], ignore_index=True)
    comparison["thermal_max_MW"] = thermal_max_MW
    comparison["num_steps"] = len(baseline)
    comparison["time_step_hours"] = time_step_hours
    return comparison
