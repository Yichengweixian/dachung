"""读取并检查风光荷CSV，功率单位MW、时间单位小时。"""

import numpy as np
import pandas as pd


def validate_input_data(data, num_steps=None, time_step_hours=1.0):
    """允许不同时间长度；要求按等间隔连续时间排序。"""
    required = ["hour", "load", "wind", "solar"]
    if not set(required).issubset(data.columns) or data.empty:
        raise ValueError("输入不能为空，且须包含hour、load、wind、solar。")
    if not np.isfinite(time_step_hours) or time_step_hours <= 0:
        raise ValueError("时间步长必须为有限正数。")
    if num_steps is not None and (
        type(num_steps) is not int or num_steps <= 0 or len(data) != num_steps
    ):
        raise ValueError("输入行数须与配置中的正整数num_steps一致。")
    values = data[required].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("输入不能包含缺失值、无穷大或负值。")
    if not np.allclose(np.diff(values[:, 0]), time_step_hours, atol=1e-9, rtol=0):
        raise ValueError("hour必须连续、不重复，且相邻间隔等于时间步长。")


def load_input_data(path, num_steps=None, time_step_hours=1.0):
    data = pd.read_csv(path)
    for column in ("hour", "load", "wind", "solar"):
        if column not in data:
            raise ValueError(f"CSV缺少字段：{column}")
        data[column] = pd.to_numeric(data[column], errors="raise")
    validate_input_data(data, num_steps, time_step_hours)
    return data
