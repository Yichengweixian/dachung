"""含储能的逐时规则调度，所有充放电功率均在电网侧计量。"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data_loader import validate_input_data


@dataclass(frozen=True)
class StorageParameters:
    energy_capacity_MWh: float = 40.0
    power_capacity_MW: float = 20.0
    soc_initial: float = 0.50
    soc_min: float = 0.10
    soc_max: float = 0.90
    eta_charge: float = 0.95
    eta_discharge: float = 0.95

    def __post_init__(self):
        if not all(np.isfinite(value) for value in vars(self).values()):
            raise ValueError("储能参数必须为有限数值。")
        if self.energy_capacity_MWh < 0 or self.power_capacity_MW < 0:
            raise ValueError("能量容量和功率容量不能为负。")
        if self.energy_capacity_MWh == 0 and self.power_capacity_MW != 0:
            raise ValueError("零能量容量场景的功率容量必须为零。")
        if not 0 <= self.soc_min < self.soc_max <= 1:
            raise ValueError("SOC上下限须满足0 <= soc_min < soc_max <= 1。")
        if not self.soc_min <= self.soc_initial <= self.soc_max:
            raise ValueError("初始SOC必须处于上下限之间。")
        if not 0 < self.eta_charge <= 1 or not 0 < self.eta_discharge <= 1:
            raise ValueError("充放电效率必须位于(0, 1]。")


def calculate_storage_balance(data, storage, thermal_max_MW=120.0, time_step_hours=1.0):
    """按时间顺序更新电量；soc为每个时段结束时的比例，无期末归位约束。"""
    validate_input_data(data, time_step_hours=time_step_hours)
    if not np.isfinite(thermal_max_MW) or thermal_max_MW < 0:
        raise ValueError("火电最大出力必须为有限非负数。")
    capacity = storage.energy_capacity_MWh
    minimum = capacity * storage.soc_min
    maximum = capacity * storage.soc_max
    energy = capacity * storage.soc_initial
    dt = time_step_hours
    records = []
    for row in data.itertuples(index=False):
        renewable = row.wind + row.solar
        start_energy = energy
        charge = discharge = thermal = curtailment = shedding = 0.0
        if renewable > row.load:
            surplus = renewable - row.load
            # 电网侧充电功率上限：余量/(充电效率*步长)。
            charge = min(surplus, storage.power_capacity_MW,
                         max(0.0, maximum - start_energy) / (storage.eta_charge * dt))
            curtailment = surplus - charge
        elif renewable < row.load:
            deficit = row.load - renewable
            # 电网侧可放功率：(剩余电量-最低电量)*放电效率/步长。
            discharge = min(deficit, storage.power_capacity_MW,
                            max(0.0, start_energy - minimum) * storage.eta_discharge / dt)
            thermal = min(deficit - discharge, thermal_max_MW)
            shedding = deficit - discharge - thermal
        energy = start_energy + storage.eta_charge * charge * dt - discharge * dt / storage.eta_discharge
        # 不靠截断SOC掩盖错误，容量边界由上面的功率约束保证。
        records.append({
            "hour": row.hour, "load": row.load, "wind": row.wind, "solar": row.solar,
            "renewable": renewable, "thermal": thermal,
            "storage_charge": charge, "storage_discharge": discharge,
            "soc": energy / capacity if capacity > 0 else np.nan,
            "curtailment": curtailment, "load_shedding": shedding,
            "renewable_used": renewable - curtailment,
            "soc_start": start_energy / capacity if capacity > 0 else np.nan,
            "energy_start_MWh": start_energy, "energy_end_MWh": energy,
            "balance_error_MW": renewable - curtailment + thermal + discharge + shedding - row.load - charge,
        })
    return pd.DataFrame(records)
