# 指标与单位约定

本文件规定项目的通用字段和单位。第3、4阶段的实际CSV简短字段及指标分别见no_storage_model.md与storage_model.md；第5阶段容量对比见capacity_sensitivity_analysis.md，第6阶段成本参数与费用组成见economics_analysis.md。
系统包含火电、风电、光伏、储能和负荷。初期24个时间步，每步1小时；后续扩展到168或8760个时间步。

## 时序字段

| 字段 | 含义 | 单位 |
|---|---|---|
| timestamp | 每个时间区间的起点，数据说明须注明时区或说明为构造时间 | 时间 |
| load_MW | 区间平均负荷功率 | MW |
| wind_available_MW | 风电可用出力 | MW |
| solar_available_MW | 光伏可用出力 | MW |
| wind_used_MW | 实际接纳的风电功率 | MW |
| solar_used_MW | 实际接纳的光伏功率 | MW |
| wind_curtailed_MW | 弃风功率 | MW |
| solar_curtailed_MW | 弃光功率 | MW |
| thermal_MW | 火电出力 | MW |
| charge_MW | 储能充电功率，取正值 | MW |
| discharge_MW | 储能放电功率，取正值 | MW |
| energy_MWh | 储能在时间边界上的剩余电量 | MWh |
| soc | 剩余电量除以额定容量 | 无量纲，0至1 |
| unserved_MW | 未满足的负荷功率 | MW |

SOC与剩余电量不能混用单位。24个功率区间对应25个储能状态边界，包含初始状态；后续结果表需明确每行状态代表区间起点还是终点。零容量场景的SOC未定义，使用空值，不进行除零计算。

## 汇总指标

设时间步长为 dt（小时），所有电量均按“区间平均功率乘dt后求和”计算。

| 指标 | 初步口径 | 单位 |
|---|---|---|
| 新能源发电量 | 明确区分可发电量与实际发电量；可发电量为可用风电与光伏出力之和的时间积分 | MWh |
| 新能源消纳量 | wind_used_MW与solar_used_MW之和的时间积分，即系统接纳电量 | MWh |
| 弃风弃光量 | 弃风功率与弃光功率之和的时间积分 | MWh |
| 弃风弃光率 | 弃风弃光量 / 新能源可发电量 | % |
| 新能源消纳率 | 新能源消纳量 / 新能源可发电量 | % |
| 火电出力 | 保留逐时出力；需要汇总时另算火电发电量 | MW；汇总为MWh |
| 储能充电功率 | charge_MW时序 | MW |
| 储能放电功率 | discharge_MW时序 | MW |
| 储能SOC | soc时序，绘图可乘100转换为百分比 | 无量纲或% |
| 失负荷量 | unserved_MW的时间积分 | MWh |
| 系统综合成本 | 第6阶段为火电、储能投资折算及运维、弃电和失负荷成本之和 | 元/仿真时段 |

新能源可发电量为0时，消纳率和弃电率均为空值，并标记“不适用”。消纳量采用接纳口径，包含接纳后用于储能充电的新能源电量，不等于最终送达负荷的新能源电量。

第6阶段total_cost_CNY采用包含投资折算与惩罚项的综合评价口径，operating_cost_excluding_investment_CNY单列不含投资折算的费用。storage_cost_CNY包含投资时段分摊、固定运维及按放电量计的可变运维；储能初始投资单价分别使用元/kWh和元/kW，换算时乘1000。参数全部为测试假设，未用于改变规则调度或求解经济最优容量。

第4阶段storage_charge、storage_discharge在电网侧计量。soc为时段结束比例，soc_start为时段开始比例。储能利用率storage_utilization_pct定义为充放电活跃时长占比，阈值1e-6 MW；放电周转比discharge_turnover_ratio为电网侧放电量除以额定容量，不作为完整循环次数。期末SOC未强制归位，统计同时记录初末电量与效率损耗。
