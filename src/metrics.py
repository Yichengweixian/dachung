"""无储能场景电量汇总与新能源消纳指标。"""

import numpy as np
import pandas as pd


def summarize_no_storage(result, time_step_hours=1.0):
    """逐时平均功率乘步长求和；比例返回0至100的百分数。"""
    if not np.isfinite(time_step_hours) or time_step_hours <= 0:
        raise ValueError("时间步长必须为有限正数。")
    columns = {
        "total_load_MWh": "load",
        "renewable_available_MWh": "renewable",
        "renewable_used_MWh": "renewable_used",
        "curtailment_MWh": "curtailment",
        "thermal_generation_MWh": "thermal",
        "unserved_MWh": "unserved",
    }
    summary = {name: float(result[col].sum() * time_step_hours) for name, col in columns.items()}
    available = summary["renewable_available_MWh"]
    summary["renewable_utilization_pct"] = (
        100 * summary["renewable_used_MWh"] / available if available > 0 else np.nan
    )
    summary["curtailment_rate_pct"] = (
        100 * summary["curtailment_MWh"] / available if available > 0 else np.nan
    )
    return pd.DataFrame([summary])
