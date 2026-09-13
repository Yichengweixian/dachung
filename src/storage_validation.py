"""储能规则调度的物理守恒、边界和汇总检查。"""

import numpy as np

from .storage_metrics import ACTIVE_POWER_TOLERANCE_MW


def validate_storage_result(result, summary, storage, thermal_max_MW, time_step_hours=1.0, tolerance=1e-6):
    def close(a, b):
        return bool(np.allclose(a, b, atol=tolerance, rtol=0))

    s = storage
    dt = time_step_hours
    q = result
    lo, hi = s.energy_capacity_MWh * s.soc_min, s.energy_capacity_MWh * s.soc_max
    charge, discharge = q.storage_charge, q.storage_discharge
    start, end = q.energy_start_MWh, q.energy_end_MWh
    values = q[["renewable", "thermal", "storage_charge", "storage_discharge",
                "curtailment", "load_shedding", "renewable_used", "energy_start_MWh", "energy_end_MWh"]].to_numpy()
    surplus = (q.renewable - q.load).clip(lower=0)
    deficit = (q.load - q.renewable).clip(lower=0)
    charge_limit = np.minimum(s.power_capacity_MW, np.maximum(0, hi - start) / (s.eta_charge * dt))
    discharge_limit = np.minimum(s.power_capacity_MW, np.maximum(0, start - lo) * s.eta_discharge / dt)
    checks = {
        "有限非负结果": bool(np.isfinite(values).all() and (values >= -tolerance).all()),
        "风光总可用出力": close(q.renewable, q.wind + q.solar),
        "新能源消纳与弃电守恒": close(q.renewable_used + q.curtailment, q.renewable),
        "电网功率平衡": close(q.renewable_used + q.thermal + discharge + q.load_shedding, q.load + charge),
        "初始电量": close(start.iloc[0], s.energy_capacity_MWh * s.soc_initial),
        "相邻时段电量衔接": close(start.to_numpy()[1:], end.to_numpy()[:-1]),
        "储能能量递推": close(end, start + s.eta_charge * charge * dt - discharge * dt / s.eta_discharge),
        "初末电量边界": bool(((start >= lo - tolerance) & (start <= hi + tolerance)
                                & (end >= lo - tolerance) & (end <= hi + tolerance)).all()),
        "充电功率上限": bool((charge <= s.power_capacity_MW + tolerance).all()),
        "放电功率上限": bool((discharge <= s.power_capacity_MW + tolerance).all()),
        "不同时充放电": bool(((charge <= tolerance) | (discharge <= tolerance)).all()),
        "只用富余新能源充电": bool((charge <= surplus + tolerance).all()),
        "放电不超过负荷缺口": bool((discharge <= deficit + tolerance).all()),
        "有富余尽可能充电": close(charge, np.minimum(surplus, charge_limit)),
        "有缺口尽可能放电": close(discharge, np.minimum(deficit, discharge_limit)),
        "火电补充剩余缺口": close(q.thermal, np.minimum(np.maximum(0, deficit - discharge), thermal_max_MW)),
        "火电上限": bool((q.thermal <= thermal_max_MW + tolerance).all()),
        "失负荷时火电满出力": bool(((q.load_shedding <= tolerance) | (abs(q.thermal - thermal_max_MW) <= tolerance)).all()),
        "弃电与失负荷不并存": bool(((q.curtailment <= tolerance) | (q.load_shedding <= tolerance)).all()),
    }
    if s.energy_capacity_MWh > 0:
        checks["SOC与电量一致"] = close(q.soc_start * s.energy_capacity_MWh, start) and close(q.soc * s.energy_capacity_MWh, end)
    else:
        checks["零容量SOC为空"] = bool(q.soc.isna().all() and q.soc_start.isna().all())
    row = summary.iloc[0]
    mappings = {
        "total_load_MWh": "load", "renewable_available_MWh": "renewable",
        "renewable_used_MWh": "renewable_used", "curtailment_MWh": "curtailment",
        "thermal_generation_MWh": "thermal", "load_shedding_MWh": "load_shedding",
        "storage_charge_MWh": "storage_charge", "storage_discharge_MWh": "storage_discharge",
    }
    for metric, col in mappings.items():
        checks[metric + "汇总"] = close(row[metric], sum(q[col]) * dt)
    checks["汇总初始与期末电量"] = close(row.initial_energy_MWh, start.iloc[0]) and close(row.final_energy_MWh, end.iloc[-1])
    checks["净电量变化"] = close(row.energy_change_MWh, end.iloc[-1] - start.iloc[0])
    checks["充电损耗"] = close(row.charge_loss_MWh, (1 - s.eta_charge) * row.storage_charge_MWh)
    checks["放电损耗"] = close(row.discharge_loss_MWh, (1 / s.eta_discharge - 1) * row.storage_discharge_MWh)
    checks["损耗合计"] = close(row.storage_loss_MWh, row.charge_loss_MWh + row.discharge_loss_MWh)
    checks["全天储能能量守恒"] = close(row.storage_charge_MWh - row.storage_discharge_MWh, row.energy_change_MWh + row.storage_loss_MWh)
    checks["全天电网能量守恒"] = close(row.renewable_used_MWh + row.thermal_generation_MWh + row.storage_discharge_MWh + row.load_shedding_MWh, row.total_load_MWh + row.storage_charge_MWh)
    if row.renewable_available_MWh > 0:
        checks["消纳率与弃电率"] = close(row.renewable_utilization_pct, 100 * row.renewable_used_MWh / row.renewable_available_MWh) and close(row.curtailment_rate_pct, 100 * row.curtailment_MWh / row.renewable_available_MWh)
    else:
        checks["零新能源比例为空"] = bool(np.isnan(row.renewable_utilization_pct) and np.isnan(row.curtailment_rate_pct))
    active = (charge > ACTIVE_POWER_TOLERANCE_MW) | (discharge > ACTIVE_POWER_TOLERANCE_MW)
    checks["活跃时长"] = close(row.storage_active_hours, active.sum() * dt)
    if s.energy_capacity_MWh > 0:
        checks["储能利用率口径"] = close(row.storage_utilization_pct, 100 * active.mean())
        checks["放电周转比"] = close(row.discharge_turnover_ratio, row.storage_discharge_MWh / s.energy_capacity_MWh)
        checks["初末SOC汇总"] = close(row.initial_soc, q.soc_start.iloc[0]) and close(row.final_soc, q.soc.iloc[-1])
    else:
        checks["零容量利用率为空"] = bool(np.isnan(row.storage_utilization_pct) and np.isnan(row.discharge_turnover_ratio))
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("储能模型检查失败：" + "、".join(failed))
    return checks
