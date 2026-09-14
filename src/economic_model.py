"""对已有调度结果进行成本核算；不改变调度，不搜索储能容量。"""

from dataclasses import dataclass, fields
from math import expm1, isfinite, log1p

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EconomicParameters:
    """所有示例数值只在config/economics.json中定义，字段名标明单位。"""

    thermal_cost_CNY_per_MWh: float
    storage_energy_capex_CNY_per_kWh: float
    storage_power_capex_CNY_per_kW: float
    storage_lifetime_years: float
    discount_rate: float
    storage_fixed_om_fraction_per_year: float
    storage_variable_om_CNY_per_MWh_discharged: float
    curtailment_penalty_CNY_per_MWh: float
    load_shedding_penalty_CNY_per_MWh: float
    hours_per_year: float

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{field.name}必须为有限非负数。")
        if self.storage_lifetime_years <= 0 or self.hours_per_year <= 0:
            raise ValueError("储能寿命与全年小时数必须大于0。")
        if self.storage_fixed_om_fraction_per_year > 1:
            raise ValueError("固定运维年费率应使用0至1的比例。")


def capital_recovery_factor(discount_rate, lifetime_years):
    """CRF=r/[1-(1+r)^(-n)]；r=0时退化为1/n。"""
    if not isfinite(discount_rate) or discount_rate < 0:
        raise ValueError("折现率必须为有限非负数。")
    if not isfinite(lifetime_years) or lifetime_years <= 0:
        raise ValueError("寿命必须为有限正数。")
    if discount_rate == 0:
        return 1.0 / lifetime_years
    # expm1/log1p避免极小折现率下相减造成的数值精度损失。
    return discount_rate / -expm1(-lifetime_years * log1p(discount_rate))


def evaluate_system_costs(dispatch_summary, parameters):
    """按各场景实际仿真时长折算投资；电量列已含步长，不再次乘Δt。"""
    p = parameters
    required = ["scenario", "energy_capacity_MWh", "power_capacity_MW", "num_steps",
                "time_step_hours", "thermal_generation_MWh", "curtailment_MWh",
                "load_shedding_MWh", "storage_discharge_MWh", "renewable_utilization_pct",
                "curtailment_rate_pct", "initial_inventory_supply_MWh"]
    missing = set(required) - set(dispatch_summary.columns)
    if missing:
        raise ValueError(f"成本核算缺少字段：{sorted(missing)}")
    if dispatch_summary.empty:
        raise ValueError("成本核算至少需要一个场景。")
    result = dispatch_summary[required].copy()
    numeric = [c for c in required if c not in (
        "scenario", "renewable_utilization_pct", "curtailment_rate_pct")]
    if not np.isfinite(result[numeric].to_numpy(dtype=float)).all() or (result[numeric] < 0).any().any():
        raise ValueError("容量、电量及时间字段必须为有限非负数。")
    if (result.num_steps <= 0).any() or (result.time_step_hours <= 0).any():
        raise ValueError("仿真步数及时间步长必须大于0。")
    if (result.num_steps % 1 != 0).any():
        raise ValueError("仿真步数必须为整数。")
    if result.scenario.duplicated().any():
        raise ValueError("场景名称不能重复。")
    if ((result.energy_capacity_MWh == 0) & (result.power_capacity_MW != 0)).any():
        raise ValueError("无储能场景的功率容量必须为0。")

    result["simulation_hours"] = result.num_steps * result.time_step_hours
    fraction = result.simulation_hours / p.hours_per_year
    crf = capital_recovery_factor(p.discount_rate, p.storage_lifetime_years)
    # MW、MWh分别转换成kW、kWh，与投资单价保持一致。
    result["storage_capex_CNY"] = (
        result.energy_capacity_MWh * 1000 * p.storage_energy_capex_CNY_per_kWh
        + result.power_capacity_MW * 1000 * p.storage_power_capex_CNY_per_kW
    )
    result["capital_recovery_factor"] = crf
    result["year_fraction"] = fraction
    result["storage_annualized_investment_CNY_per_year"] = result.storage_capex_CNY * crf
    result["storage_annual_fixed_om_CNY_per_year"] = result.storage_capex_CNY * p.storage_fixed_om_fraction_per_year
    result["storage_investment_allocated_CNY"] = result.storage_annualized_investment_CNY_per_year * fraction
    result["storage_fixed_om_CNY"] = result.storage_annual_fixed_om_CNY_per_year * fraction
    result["storage_variable_om_CNY"] = result.storage_discharge_MWh * p.storage_variable_om_CNY_per_MWh_discharged
    result["storage_om_cost_CNY"] = result.storage_fixed_om_CNY + result.storage_variable_om_CNY
    result["storage_cost_CNY"] = result.storage_investment_allocated_CNY + result.storage_om_cost_CNY
    result["thermal_cost_CNY"] = result.thermal_generation_MWh * p.thermal_cost_CNY_per_MWh
    result["curtailment_cost_CNY"] = result.curtailment_MWh * p.curtailment_penalty_CNY_per_MWh
    result["load_shedding_cost_CNY"] = result.load_shedding_MWh * p.load_shedding_penalty_CNY_per_MWh
    result["total_cost_CNY"] = (result.thermal_cost_CNY + result.storage_cost_CNY
                                + result.curtailment_cost_CNY + result.load_shedding_cost_CNY)
    result["operating_cost_excluding_investment_CNY"] = result.total_cost_CNY - result.storage_investment_allocated_CNY
    # 仅作为初始库存影响的参考估值，既不是额外收费，也不加进Total Cost。
    result["initial_inventory_thermal_value_CNY"] = result.initial_inventory_supply_MWh * p.thermal_cost_CNY_per_MWh
    first = ["scenario", "energy_capacity_MWh", "power_capacity_MW", "total_cost_CNY",
             "thermal_cost_CNY", "storage_cost_CNY", "curtailment_cost_CNY",
             "load_shedding_cost_CNY", "renewable_utilization_pct", "curtailment_rate_pct"]
    return result[first + [c for c in result.columns if c not in first]]


def validate_cost_results(result, parameters, tolerance=1e-6):
    """核对费用加总、投资单位换算、时间折算与电量计费；返回检查名称。"""
    p = parameters
    checks = {}

    def check(name, actual, expected):
        if not np.allclose(actual, expected, atol=tolerance, rtol=1e-10):
            raise ValueError(f"经济性校验失败：{name}")
        checks[name] = True

    cost_columns = [c for c in result if c.endswith("_CNY")]
    values = result[cost_columns].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < -tolerance).any():
        raise ValueError("成本必须为有限非负数。")
    checks["finite_nonnegative_costs"] = True
    check("simulation_hours", result.simulation_hours, result.num_steps * result.time_step_hours)
    check("allocation_fraction", result.year_fraction, result.simulation_hours / p.hours_per_year)
    check("investment_units", result.storage_capex_CNY,
          1000 * (result.energy_capacity_MWh * p.storage_energy_capex_CNY_per_kWh
                  + result.power_capacity_MW * p.storage_power_capex_CNY_per_kW))
    check("crf", result.capital_recovery_factor, capital_recovery_factor(p.discount_rate, p.storage_lifetime_years))
    check("annual_investment", result.storage_annualized_investment_CNY_per_year,
          result.storage_capex_CNY * result.capital_recovery_factor)
    check("annual_fixed_om", result.storage_annual_fixed_om_CNY_per_year,
          result.storage_capex_CNY * p.storage_fixed_om_fraction_per_year)
    check("allocated_investment", result.storage_investment_allocated_CNY,
          result.storage_annualized_investment_CNY_per_year * result.year_fraction)
    check("fixed_om", result.storage_fixed_om_CNY, result.storage_annual_fixed_om_CNY_per_year * result.year_fraction)
    check("variable_om", result.storage_variable_om_CNY,
          result.storage_discharge_MWh * p.storage_variable_om_CNY_per_MWh_discharged)
    check("storage_om_total", result.storage_om_cost_CNY, result.storage_fixed_om_CNY + result.storage_variable_om_CNY)
    check("storage_total", result.storage_cost_CNY, result.storage_investment_allocated_CNY + result.storage_om_cost_CNY)
    check("thermal", result.thermal_cost_CNY, result.thermal_generation_MWh * p.thermal_cost_CNY_per_MWh)
    check("curtailment", result.curtailment_cost_CNY, result.curtailment_MWh * p.curtailment_penalty_CNY_per_MWh)
    check("load_shedding", result.load_shedding_cost_CNY, result.load_shedding_MWh * p.load_shedding_penalty_CNY_per_MWh)
    check("total", result.total_cost_CNY, result.thermal_cost_CNY + result.storage_cost_CNY
          + result.curtailment_cost_CNY + result.load_shedding_cost_CNY)
    check("operating_excludes_capital", result.operating_cost_excluding_investment_CNY,
          result.thermal_cost_CNY + result.storage_om_cost_CNY + result.curtailment_cost_CNY + result.load_shedding_cost_CNY)
    check("inventory_reference", result.initial_inventory_thermal_value_CNY,
          result.initial_inventory_supply_MWh * p.thermal_cost_CNY_per_MWh)
    zero = result.loc[result.energy_capacity_MWh == 0]
    check("no_storage_zero_cost", zero.storage_cost_CNY, np.zeros(len(zero)))
    return checks
