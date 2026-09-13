# 第4阶段储能规则模型与对比结果

本阶段读取原有data/input_24h.csv，加入固定40 MWh、20 MW储能，以简单逐时规则进行调度。无储能基准使用相同输入、相同120 MW火电上限、相同1小时步长重新计算。本阶段不进行容量优化、价格调度或成本评价。

## 参数与电量边界

参数集中在config/storage.json，SOC使用0至1的比例。

| 参数 | 当前值 |
|---|---:|
| 额定能量容量 | 40 MWh |
| 最大充电功率 | 20 MW |
| 最大放电功率 | 20 MW |
| 初始SOC | 50% |
| SOC下限 | 10% |
| SOC上限 | 90% |
| 充电效率 | 0.95 |
| 放电效率 | 0.95 |

初始电量20 MWh，最低电量4 MWh，最高电量36 MWh，可用电量窗口32 MWh。充放电功率在电网侧计量，储能内部电量在电池侧计量。

## 逐时调度与效率处理

记当前时段开始电量为E_start，风光可用功率为R，负荷为L，步长为dt小时。

当R > L时，先满足负荷，再以富余新能源充电：

```text
storage_charge = min(R - L, Power_capacity,
                     (E_max - E_start) / (eta_charge * dt))
curtailment = R - L - storage_charge
storage_discharge = thermal = load_shedding = 0
```

当R < L时，储能优先补充缺口，之后才调用火电：

```text
storage_discharge = min(L - R, Power_capacity,
                        (E_start - E_min) * eta_discharge / dt)
thermal = min(L - R - storage_discharge, P_thermal_max)
load_shedding = L - R - storage_discharge - thermal
storage_charge = curtailment = 0
```

R = L时不充电、不放电、不调用火电。每个时段结束电量按下式更新，并传递到下一个时段：

```text
E_end = E_start + eta_charge * storage_charge * dt
                - storage_discharge * dt / eta_discharge
soc = E_end / Energy_capacity
```

例如初始电量20 MWh、最低4 MWh时，即使放电功率允许20 MW，一小时最多只能向电网放出(20 - 4) × 0.95 = 15.2 MWh。充电输入20 MWh时，电池仅增加19 MWh。

代码通过计算可充放功率保证电量边界，不在计算后强行截断SOC。互斥分支确保不同时充电和放电，不使用火电给储能充电。火电继续允许0至120 MW任意调节，不考虑爬坡、启停及最小出力。

## 输出文件与字段

| 文件 | 作用 |
|---|---|
| results/storage_hourly.csv | 按要求输出24行储能逐时结果 |
| results/storage_summary.csv | 储能场景电量、比例、使用程度、损耗与参数 |
| results/storage_baseline_hourly.csv | 本次使用相同数据重新计算的无储能参考结果 |
| results/storage_comparison.csv | no_storage与with_storage两行指标对比 |
| figures/storage_comparison.png | 火电、弃电、储能充放电及SOC对比图 |

storage_hourly.csv前11列依次为hour、load、wind、solar、renewable、thermal、storage_charge、storage_discharge、soc、curtailment、load_shedding。

除hour及soc外，这11列中的数值均为MW；soc为0至1比例。curtailment、load_shedding表示时段平均功率，求电量时需乘dt，汇总表中相应列单位为MWh。

追加的renewable_used表示风光实际接纳功率，等于renewable - curtailment，包含用于储能充电的部分；soc_start、energy_start_MWh、energy_end_MWh保留时段初末状态；balance_error_MW记录电网功率守恒残差。

hour=0表示00:00至01:00时段。因此该行soc是01:00状态，并不等于00:00的初始SOC。SOC图显示0至24时刻共25个状态点，含初始50%和所有时段结束状态。

## 指标口径

- 新能源消纳率：sum(renewable_used) / sum(renewable) × 100%。按接纳口径统计，包含用于充电的新能源，不等于储能损耗后最终送达负荷的新能源电量。初始库存的来源未追踪，不计入本日风光可发电量。
- 弃风弃光率：sum(curtailment) / sum(renewable) × 100%。新能源可发电量为零时，两项比例为空值。
- 储能充电量：sum(storage_charge) × dt，电网侧输入电量，字段storage_charge_MWh。
- 储能放电量：sum(storage_discharge) × dt，电网侧输出电量，字段storage_discharge_MWh。
- 储能利用率：本阶段定义为充电或放电功率大于1e-6 MW的活跃时长 / 总时长 × 100%，字段storage_utilization_pct。它描述运行时间占比，不是SOC、往返效率或容量最优程度。当前6个活跃时段，6 / 24 = 25%。
- 放电周转比：电网侧放电量 / 额定能量容量，字段discharge_turnover_ratio；当前1.14，可大于1，不等同于完整电池循环次数。
- 失负荷量：sum(load_shedding) × dt，字段load_shedding_MWh。

无储能对比行的充放电量为0，SOC、储能效率参数、储能利用率和放电周转比留空表示不适用。pct结尾字段直接使用百分数，例如91.176表示91.176%。

## 本次结果

| 指标 | 无储能 | 40 MWh / 20 MW储能 |
|---|---:|---:|
| 全天负荷电量 MWh | 2924.00 | 2924.00 |
| 风光可发电量 MWh | 2175.84 | 2175.84 |
| 新能源消纳量 MWh | 1950.16 | 1983.84421053 |
| 新能源消纳率 | 89.62791382% | 91.17601526% |
| 弃风弃光率 | 10.37208618% | 8.82398474% |
| 弃风弃光量 MWh | 225.68 | 191.99578947 |
| 火电发电量 MWh | 973.84 | 928.24 |
| 储能充电量 MWh | 0 | 33.68421053 |
| 储能放电量 MWh | 0 | 45.60 |
| 储能利用率 活跃时长占比 | 不适用 | 25.00% |
| 失负荷量 MWh | 0 | 0 |

新增消纳33.68421053 MWh，消纳率提高约1.5481个百分点。储能10、11小时充电，0、15、16、17小时放电，其余小时空闲。本规则有缺口即放电，18至19小时晚高峰时已降至SOC下限，没有提前为晚高峰保留能量。

## 初末电量与比较边界

按当前用户要求，不强制期末SOC回到初始50%。本次期末为10%，电量从20 MWh降至4 MWh，净减少16 MWh。充电损耗1.68421053 MWh，放电损耗2.4 MWh，合计4.08421053 MWh。守恒关系为：

```text
初始电量 + 充电输入 = 期末电量 + 放电输出 + 总损耗
20 + 33.68421053 = 4 + 45.6 + 4.08421053
```

放电量大于当日充电量来自初始库存下降，不是效率超过100%。火电减少45.6 MWh包含初始库存净释放带来的15.2 MWh电网侧供给；当日新增充电经过往返效率0.95 × 0.95后提供30.4 MWh。因此不能把全部火电减少量归因于当日弃电回收，也不能将本日改善量直接重复外推全年。

## 运行与代码分工

在项目目录运行：

```powershell
.\.venv\Scripts\python.exe run_storage.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

VSCode中选择.venv解释器后，可直接运行run_storage.py，或F5选择“第4阶段 储能规则调度与对比”。原始输入、申请书及第3阶段输出不改写；重复运行更新本阶段输出。

src/storage_model.py负责参数检查及逐时规则；src/storage_metrics.py负责统计与对比；src/storage_validation.py负责物理守恒与指标校验；src/plot_storage.py负责绘图。run_storage.py只组织流程，继续使用pandas、numpy、matplotlib和Python标准库。

本次15项自动测试通过，包含原有5项无储能测试与10项储能测试。储能结果通过40项数值检查，保存并读回CSV后再次校验；覆盖充放电功率、初始状态、相邻时段衔接、SOC边界、效率与能量守恒、不同时充放电、规则优先级、火电上限、失负荷及汇总。测试包含满电、最低SOC、零容量、零功率、零新能源、0.5小时步长和无储能退化。对比图已检查。

这些数值是当前输入与配置的运行记录。改变配置后应重新运行，并以新的CSV为准；本阶段在此停止，不执行容量寻优。
