"""无储能规则调度：新能源优先、火电补缺、剩余缺口记为失负荷。"""

import numpy as np

from .data_loader import validate_input_data


def calculate_no_storage_balance(data, thermal_max_MW=120.0, time_step_hours=1.0):
    """返回新表，不修改输入。每个时段独立计算，不考虑爬坡或最小出力。"""
    validate_input_data(data, time_step_hours=time_step_hours)
    if not np.isfinite(thermal_max_MW) or thermal_max_MW < 0:
        raise ValueError("火电最大出力必须为有限非负数。")
    result = data[["hour", "load", "wind", "solar"]].copy()
    result["renewable"] = result["wind"] + result["solar"]
    result["renewable_used"] = np.minimum(result["renewable"], result["load"])
    result["curtailment"] = result["renewable"] - result["renewable_used"]
    deficit = result["load"] - result["renewable_used"]
    result["thermal"] = np.minimum(deficit, thermal_max_MW)
    result["unserved"] = deficit - result["thermal"]
    # 上述字段是MW；下述两个字段是每个时段的MWh。
    result["curtailment_MWh"] = result["curtailment"] * time_step_hours
    result["unserved_MWh"] = result["unserved"] * time_step_hours
    result["balance_error_MW"] = (
        result["renewable_used"] + result["thermal"] + result["unserved"] - result["load"]
    )
    return result
