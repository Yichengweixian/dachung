# U11R09 设计

## 固定来源与范围

N=[12,24,48]、seed=[42,7,2026]。权重仅来自results/annual/U11R08-v02/
各组solution.json的weights，必须与同组weights.csv逐个float64完全相等。
不使用独立CBC权重或有理数证明修复权重，不重新优化、不修正总和、不缩放。
核验R08主manifest产物哈希、独立审计report.json引用的主manifest和审计源码哈希、
72项审计子产物哈希及九组reachable。R08主manifest停在awaiting_independent_audit，
其完成证据以已有独立report.json为准；不回写历史manifest。

代表日期、cluster、原簇天数、标签及曲线直接读U11R03-v01保存CSV，与R08模型记录
和U11R02-v01/input_8760h.csv对应小时逐值核对。年度目标为8760个1h输入之和；
MW×h=MWh。T=0时要求代表通道均为0、误差记0，禁止除零。数据缺失、哈希不符、
原生权重不能恢复立即停止，不能补数据、聚类或以其他权重替代。

## 调度及基准

调用现有src.optimization_model.solve_dispatch，经study_runtime.evaluate_case执行，
mutual_exclusion=True、terminal=True、dt=1h。storage/thermal/economics从U11R02
冻结配置读取并与当前配置和U11R03冻结配置一致性核验：40MWh/20MW储能，每日初末SOC归位，
原火电下限、上限、爬坡及成本保持不变。FullPrecisionCBC求解参数原样保留。
新封装仅保存模型、日志及原生精度CSV，不改变模型、目标或求解参数。

8760h全年基准是U11R02保存的365个独立日调度的加总，不是具有跨日SOC耦合的连续年优化。
重新读取365份保存日解，核对逐时输入、物理约束、日汇总、年度电量/成本及full_annual比例，
不重新求解全年。不把该比较称为跨年或真实电网验证；负荷为构造形状，风光为气象估计。

## 实际求解与重复性

主矩阵每组求N个日解，共252次MILP，无缓存复用；每组再独立重复cluster 0，共9次。
合计预算261次MILP、权重LP 0次、重新聚类0次。重复检查逐时数值、目标、日能量，
容差1e-6。所有252个主日解还与R03保存解比较目标及电量，记录差异但不强制非唯一
最优逐时解一致；R08附加E只作为历史对照，不代替新求解结果。

先按冻结权重加总可用、消纳、弃电电量再算比例，不能平均日比例。
D=max_k|sum_i(w_i*a_ki)/T_k-1|；E=max(|消纳率-全年消纳率|,|弃电率-全年弃电率|)，
比例及E均以百分数数值计算、E单位百分点。报告D实际重算值而非R08 LP的t。

## 证据输出

results/annual/U11R09-v01/下保存复制的原始权重/输入、261份逐时CSV、模型、日志、
日汇总、九组comparison.csv、输入电量误差、基准审计、重复性、物理约束检查、
输入和代码哈希、依赖及CBC版本、run_manifest.json，任何失败保存failure.json。
只读独立审计另进程重新计算，禁止优化调用；生成独立审计报告后另建completion.json，
引用主manifest及审计报告SHA-256，完整通过后才登记complete/verdict。各文件拒绝覆盖。
