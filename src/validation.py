"""独立检查无储能模型的功率、电量与优先消纳规则。"""

import numpy as np


def validate_no_storage_result(result, summary, thermal_max_MW, time_step_hours=1.0, tolerance=1e-6):
    def close(left, right):
        return np.allclose(left, right, atol=tolerance, rtol=0)

    fields = ["renewable", "renewable_used", "curtailment", "thermal", "unserved"]
    values = result[fields].to_numpy()
    checks = {
        "结果有限且非负": bool(np.isfinite(values).all() and (values >= -tolerance).all()),
        "新能源可用出力分解": close(result.renewable, result.wind + result.solar),
        "新能源消纳与弃电守恒": close(result.renewable_used + result.curtailment, result.renewable),
        "逐时功率平衡": close(result.renewable_used + result.thermal + result.unserved, result.load),
        "火电上限": bool((result.thermal <= thermal_max_MW + tolerance).all()),
        "新能源优先消纳": bool(((result.curtailment <= tolerance) | (result.thermal <= tolerance)).all()),
        "消纳不超过负荷": bool((result.renewable_used <= result.load + tolerance).all()),
        "弃电与失负荷不并存": bool(((result.curtailment <= tolerance) | (result.unserved <= tolerance)).all()),
        "失负荷时火电已达上限": bool(((result.unserved <= tolerance) | (abs(result.thermal - thermal_max_MW) <= tolerance)).all()),
        "逐时弃电电量": close(result.curtailment_MWh, result.curtailment * time_step_hours),
        "逐时失负荷电量": close(result.unserved_MWh, result.unserved * time_step_hours),
    }
    row = summary.iloc[0]
    for metric, column in {
        "total_load_MWh": "load", "renewable_available_MWh": "renewable",
        "renewable_used_MWh": "renewable_used", "curtailment_MWh": "curtailment",
        "thermal_generation_MWh": "thermal", "unserved_MWh": "unserved",
    }.items():
        checks[metric + "汇总"] = close(row[metric], sum(result[column]) * time_step_hours)
    checks["全天电量平衡"] = close(row.renewable_used_MWh + row.thermal_generation_MWh + row.unserved_MWh, row.total_load_MWh)
    if row.renewable_available_MWh > 0:
        checks["新能源消纳率"] = close(row.renewable_utilization_pct, 100 * row.renewable_used_MWh / row.renewable_available_MWh)
        checks["弃电率"] = close(row.curtailment_rate_pct, 100 * row.curtailment_MWh / row.renewable_available_MWh)
        checks["比例合计"] = close(row.renewable_utilization_pct + row.curtailment_rate_pct, 100)
    else:
        checks["零新能源比例为空"] = bool(np.isnan(row.renewable_utilization_pct) and np.isnan(row.curtailment_rate_pct))
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("无储能结果检查失败：" + "、".join(failed))
    return checks
