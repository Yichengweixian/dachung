# 无储能电力电量平衡模型

第3阶段读取已有data/input_24h.csv，不生成或调整输入数据。风光出力均是可用功率。每个小时独立计算，新能源优先满足负荷，火电补充剩余缺口。

## 规则与模型边界

记负荷为L，风光总可用出力为R，火电上限为Pmax。所有逐时功率单位为MW。

```text
R = wind + solar
新能源实际消纳 U = min(R, L)
弃风弃光功率 C = R - U
火电出力 G = min(L - U, Pmax)
失负荷功率 D = L - U - G
```

R等于L时，新能源正好满足负荷，火电、弃电和失负荷均为零。每小时满足U + G + D = L、U + C = R。D代表未满足需求，不是真正发电；实际供给为U + G。

config/no_storage.json设置thermal_max_MW，当前为120 MW。config/simulation.json设置时间步数24、时间步长1小时；程序检查其与输入数据行数及小时间隔一致。

火电允许在0至120 MW之间任意调节。本阶段按用户指定规则，不考虑最小技术出力、爬坡、启停、备用、网损、外送和储能，也不计算运行成本。所得结果是这个简化边界下的规则调度结果。

## 程序分工

| 文件 | 作用 |
|---|---|
| run_no_storage.py | 读取配置并组织计算、保存、检查及绘图 |
| src/data_loader.py | 读取CSV，检查字段、非负数、缺失值与时间连续性 |
| src/balance_model.py | 按优先消纳规则计算各时段功率与弃电、失负荷电量 |
| src/metrics.py | 乘时间步长，汇总电量并计算百分比 |
| src/validation.py | 检查守恒关系、调度规则、容量边界与汇总结果 |
| src/plot_results.py | 绘制供给组成、负荷、风光可用出力及弃电、失负荷曲线 |
| tests/test_no_storage.py | 用手算边界案例检查规则，包含实际数据未触发的失负荷分支 |

## 输出字段

results/no_storage_hourly.csv保留hour、load、wind、solar，新增以下列。

| 字段 | 含义 | 单位 |
|---|---|---|
| renewable | 风光总可用出力 | MW |
| renewable_used | 新能源实际消纳功率 | MW |
| curtailment | 弃风弃光功率 | MW |
| thermal | 火电出力 | MW |
| unserved | 失负荷功率 | MW |
| curtailment_MWh | 该时段弃风弃光电量 | MWh |
| unserved_MWh | 该时段失负荷电量 | MWh |
| balance_error_MW | 消纳功率加火电、失负荷减负荷的残差 | MW |

results/no_storage_summary.csv保存一行汇总。num_steps、time_step_hours、thermal_max_MW记录本次配置，其余字段如下。

| 字段 | 含义 |
|---|---|
| total_load_MWh | 全天负荷电量 |
| renewable_available_MWh | 全天新能源可发电量，即风光输入功率积分 |
| renewable_used_MWh | 全天新能源实际消纳电量 |
| curtailment_MWh | 全天弃风弃光电量 |
| thermal_generation_MWh | 全天火电发电量 |
| unserved_MWh | 全天失负荷电量 |
| renewable_utilization_pct | 新能源消纳量 / 新能源可发电量 × 100 |
| curtailment_rate_pct | 弃风弃光量 / 新能源可发电量 × 100 |

本阶段“全天新能源发电量”按照输入wind + solar计算，即弃电前的可发电量；实际被系统接纳的发电量另列为renewable_used_MWh。不要将二者混用。时段电量等于平均功率乘时间步长；1小时步长下数值相同，单位不同。全年或周尺度扩展后，上述total表示完整输入时段合计，不再称为全天。

若新能源可发电量为0，两个比例输出空值，表示不适用。pct列是百分数，如89.63表示89.63%，不是0.8963。CSV保留8位小数以保留校验精度；展示电量可取两位小数。

figures/no_storage_balance.png上图用堆叠色块表示新能源实际消纳和火电出力，并叠加负荷及风光总可用出力曲线；下图显示弃风弃光和失负荷功率。

## 运行与验证

在项目目录运行：

```powershell
.\.venv\Scripts\python.exe run_no_storage.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_no_storage.py" -v
```

也可以在VSCode中选中.venv解释器，直接运行run_no_storage.py。输出使用固定文件名，重复运行会更新本阶段结果，不改写输入CSV或申请书。

程序在保存前和读回CSV后检查逐时功率守恒、风光消纳与弃电守恒、火电上限、优先消纳、非负性、失负荷分支、步长换算与全天汇总。检查失败会报错并停止，不能把结果当作通过验证的结论。

## 本次运行结果与验证记录

当前24小时输入、火电上限120 MW、步长1小时的结果如下；修改输入或参数后，以重新运行输出的CSV为准。

| 指标 | 数值 |
|---|---:|
| 全天负荷电量 | 2924.00 MWh |
| 新能源可发电量 | 2175.84 MWh |
| 新能源实际消纳电量 | 1950.16 MWh |
| 弃风弃光电量 | 225.68 MWh |
| 火电发电量 | 973.84 MWh |
| 失负荷电量 | 0.00 MWh |
| 新能源消纳率 | 89.62791382% |
| 弃风弃光率 | 10.37208618% |

10至14小时有弃电。最大火电出力118.59 MW，未达到120 MW上限，因此本算例未触发失负荷。这个结果不代表其他输入或火电容量下也不会失负荷。

21项自动数值检查通过，读回CSV后再次通过，最大逐时功率平衡残差为0 MW。独立手算得到新能源可发电量等于消纳量加弃电量：2175.84 = 1950.16 + 225.68；负荷电量等于新能源消纳量加火电发电量：2924.00 = 1950.16 + 973.84。

5项自动测试通过。其中负荷200 MW、风光30 MW、火电上限120 MW的测试得到失负荷50 MW，验证了正式24小时数据未触发的分支；测试还覆盖新能源恰好等于负荷、零负荷、零新能源、零火电、0.5小时步长、非法输入和错误结果识别。
