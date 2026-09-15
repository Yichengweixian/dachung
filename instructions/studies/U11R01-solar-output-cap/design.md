# U11R01设计：原始数据不变，转换输出限幅

## 1. 运行位置与冻结内容

执行地点必须是保存实际U11原始数据和失败记录的工作副本。Git远端旧STATUS不能证明该副本尚未执行，也不能用于覆盖其未提交的进度。先只读核对实际文件，不做pull/reset/checkout等覆盖工作区的动作。

组0记录：实际项目路径、父单元run_id（若存在）、Git提交和工作区差异、实际代码文件哈希、原始文件哈希、请求参数、年份/时段/时区、输入单位、配置快照、旧结果哈希，以及本单元design/plan/decision-rule的哈希。Git提交不能替代未提交代码的文件哈希。

目标为同一原始年份的8760个连续1小时时段。不自动删除闰日、补齐缺失或改选年份；若实际数据为8784小时或缺记录，报告为独立问题，本单元不擅自处理。

数值容差：功率与逐行重算采用绝对容差1e-6 MW，电量汇总采用1e-6 MWh。封顶事件定义为完整精度的P_linear > P_limit，不设固定事件次数，也不先舍入再计数。

## 2. 参数与单位

新增独立配置config/u11r01_solar_conversion.json；不覆盖U10原配置。约定至少包含：

| 字段 | 冻结值/要求 | 含义 |
|---|---|---|
| solar_reference_power_MW | 150.0 | 线性估算在参考辐照度下的功率 |
| solar_output_limit_MW | 150.0 | 本简化模型的交流侧可用输出上限 |
| reference_irradiance_W_per_m2 | 1000.0 | 参考辐照度 |
| interval_hours | 1.0 | 本次原始数据时间间隔 |
| clipping_enabled | true | 显式启用本修订方法 |
| conversion_method | linear_ac_cap_v1 | 方法版本标记 |
| source_unit | 从实际原始元数据核实后填写 | 禁止按数值大小猜单位 |

这里把参考功率与输出上限均设为150 MW，是当前简化模型的明确假设；不是声称所有150 MW组件阵列都天然具有相同交流侧限值。暂不增加温度、倾角、逆变效率或容配比模型；说明其为气象驱动的简化功率估算，不是实测电站功率。

若元数据是每时段Wh/m²，先令G_t=H_t/Δt，得到W/m²；若已是平均W/m²，直接使用。其他单位必须有明确且预先记录的换算，不能默认为这两者之一。检查缺失标记、NaN、无穷、非法负值、时间重复/缺口等后才能限幅；不得用封顶或填0掩盖异常。

## 3. 转换公式

对已通过质量检查的非负G_t：

P_linear,t = solar_reference_power_MW × G_t / reference_irradiance_W_per_m2

P_available,t = min(solar_output_limit_MW, P_linear,t)

P_clipping,t = P_linear,t − P_available,t

E_clipping = Σ P_clipping,t × Δt

只给转换后的功率设置上限，不修改原始辐照量，不把原始G_t截成1000。处理顺序为：元数据与质量检查 → 单位换算 → 线性估算 → 功率封顶 → 完整精度统计 → 输出。

手算例子：H=1010.08 Wh/m²、Δt=1 h时，G=1010.08 W/m²，P_linear=151.512 MW，P_available=150 MW，该时段封顶损失1.512 MWh。此数值是测试用例，不是对年度最大值、事件数或年度损失的预填结论。

## 4. 代码改动范围

先检查实际实现：如已有可配置封顶，则只补足配置、单位检查和验证；如目前仅有线性转换，必须修改转换实现，不能仅删除超限断言或放宽测试。

优先复用实际src/convert_weather.py，并通过显式参数/方法版本启用新方法；也可使用薄封装。U10旧入口、配置、已发布输出和原始文件保持原样，共享函数原默认行为不能被静默改变。必要的新版本接口在组0设计中写明后冻结。

新增独立、只做转换的入口scripts/convert_u11_solar_cap.py，读取已存档原始数据，不触发下载、LP求解或聚类。复用既有风电和负荷转换方法；输出这些列应与原方法的同源计算一致。调用函数名以实际代码为准，不因规格中的示例名字不存在而新造重复逻辑。

## 5. 输出与计量边界

每次运行使用唯一run_id，在results/u11r01_solar_cap/<run_id>/保存：

- input_8760h.csv：候选年度输入，至少hour/load/wind/solar，solar为封顶后可用功率；保留足够精度，显示时才舍入。
- conversion_audit.csv：全8760行，含原始timestamp及单位、原始太阳能字段、G_W_per_m2、solar_linear_MW、solar_available_MW、solar_clipping_MW、clipped。
- quality_report.json：数据完整性、实际封顶时段数及占比、封顶前后峰值、封顶损失总MWh、逐项检查结果。
- run_manifest.json：输入与输出哈希、冻结记录引用、参数快照、代码/依赖版本、run_id、方法版本、父运行引用、阶段状态及错误（如有）。

封顶次数由实际数据计算。得到2就报告2，得到其他数值就报告实际值；不以“是否等于2”判定转换正确性。时间戳要保留时区/时间标准，不能只报告第几个小时。

封顶损失属于本模型的电站输出限制，在质量报告中单列。后续调度的solar_available以封顶后功率为基准，其弃光指系统调度未接纳的电量。不得把封顶损失重复并入调度弃光，也不得隐去它后声称储能改善了全部太阳能资源利用率。跨版本对比要声明分母变化。

## 6. 通过后发布与历史保护

候选CSV写盘、读回、独立重算和全部测试通过后，才发布为data/processed/input_8760h.csv。若目标已有文件，先把旧文件完整归档到本次运行目录，记录原哈希；不删除旧文件，不覆盖旧运行目录。失败时不发布候选文件、不改变该正式路径，保留失败记录并停止。

U10保护检查：旧配置/输入/输出哈希前后一致；共享代码变更后用旧配置执行相关回归测试，临时结果单独存放，不覆盖U10已归档证据。如旧数据或环境不齐，明确记录无法完成的检查，不能宣称U10已验证不受影响。

本单元只发布年度输入。LP与聚类的后续运行需要独立指令及采用新输入哈希的冻结规格；不得直接接着执行旧U11的剩余实验。

## 方法依据

- 1000 W/m²是参考辐照度：[Sandia PVWatts说明](https://pvpmc.sandia.gov/modeling-guide/2-dc-module-iv/point-value-models/pvwatts/)。
- 输出封顶的设备模型依据：[Sandia逆变器封顶说明](https://pvpmc.sandia.gov/modeling-guide/dc-to-ac-conversion/inverter-saturation-or-clipping/)。这里采用简化限幅，不宣称实现了完整逆变器模型。
- 输入单位以实际返回元数据为准：[NASA POWER单位说明](https://power.larc.nasa.gov/docs/faqs/data/)。
