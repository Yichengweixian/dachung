"""构造可重复的24小时风光荷数据；所有功率均为MW。"""

import numpy as np
import pandas as pd


def generate_24h_data(config):
    """小时编号0至23；风光出力表示可用功率，不是调度后的消纳量。"""
    hour = np.arange(24)
    rng = np.random.default_rng(config["random_seed"])

    # 周期趋势叠加三点加权平滑扰动，保留随机性并避免逐时剧烈跳变。
    noise = rng.normal(0.0, config["wind_noise_std_MW"], size=26)
    smooth_noise = np.convolve(noise, [0.25, 0.50, 0.25], mode="valid")
    wind = config["wind_capacity_MW"] * (
        config["wind_mean_capacity_factor"]
        + config["wind_daily_amplitude"] * np.cos(2 * np.pi * (hour - 2) / 24)
    ) + smooth_noise
    wind = np.clip(wind, 0.0, config["wind_capacity_MW"])

    # 构造日间钟形曲线，6点及以前、18点及以后严格置零，12点达峰。
    start, end = config["solar_start_hour"], config["solar_end_hour"]
    solar = np.zeros(24)
    daylight = (hour > start) & (hour < end)
    phase = np.pi * (hour[daylight] - start) / (end - start)
    solar[daylight] = config["solar_capacity_MW"] * (
        np.sin(phase) ** config["solar_shape_exponent"]
    )
    return pd.DataFrame({
        "hour": hour,
        "load": config["load_MW"],
        "wind": np.round(wind, 2),
        "solar": np.round(solar, 2),
    })


def validate_24h_data(data, config):
    """检查本阶段算例要求，失败时停止保存与绘图。"""
    if list(data.columns) != ["hour", "load", "wind", "solar"]:
        raise ValueError("CSV字段应为hour、load、wind、solar。")
    if not np.array_equal(data["hour"].to_numpy(), np.arange(24)):
        raise ValueError("必须包含连续且不重复的0至23小时。")
    values = data[["load", "wind", "solar"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("功率存在缺失、非有限值或负数。")
    if (data["load"] <= 0).any():
        raise ValueError("本算例负荷应始终为正。")
    for field in ("wind", "solar"):
        if (data[field] > config[f"{field}_capacity_MW"] + 1e-6).any():
            raise ValueError(f"{field}超过装机容量。")
    night = (data.hour <= config["solar_start_hour"]) | (
        data.hour >= config["solar_end_hour"]
    )
    if (data.loc[night, "solar"] != 0).any() or data.solar.idxmax() != 12:
        raise ValueError("光伏应夜间为零、12点达到最大值。")
    load = data["load"].to_numpy()
    peaks = np.flatnonzero((load[1:-1] > load[:-2]) & (load[1:-1] > load[2:])) + 1
    if not any(7 <= h <= 10 for h in peaks) or not any(17 <= h <= 21 for h in peaks):
        raise ValueError("负荷应包含早高峰与晚高峰。")
    if data.wind.std() <= 0 or data.wind.diff().abs().max() > 15:
        raise ValueError("本算例风电应有波动，且相邻小时变化不超过15 MW。")
    gap = data.wind + data.solar - data.load
    if not (gap > 0).any() or not (gap < 0).any():
        raise ValueError("算例需要同时包含风光富余与不足时段。")
