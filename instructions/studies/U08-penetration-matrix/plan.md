# U08 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录输入 SHA-256、U06/U07 输出哈希、场景配置表哈希、判据哈希
- [ ] 0.2 确认 U07 verdict 为 supported；确认场景表内容与 design.md 一致
- [ ] 0.3 冻结场景表与判据

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U08：新能源渗透率场景矩阵。先读 `instructions/studies/U08-penetration-matrix/design.md` 和 U06/U07 的 findings.md，然后：
>
> 1. 新建 `data/scenarios/penetration_scenarios.csv`（12 场景，字段按 design.md）。
> 2. 新建 `run_penetration.py`：读场景表 → 逐场景缩放风/光 → 调用 `src/optimization_model.py` 的建模函数求解（复用，不复制）→ 每个场景对读回 CSV 执行 U06 约束检查与 U07 独立检查 → 写 `results/penetration/`（矩阵 CSV、逐时 CSV、run_manifest.json 含全部场景求解状态）。
> 3. 任一场景求解状态非 Optimal：停止并报告该场景，不得继续。
> 4. 计算边际表（0→40、40→80），绘制三张分组对比图（消纳率、弃电率、综合成本），写 `docs/renewable_penetration_analysis.md`：结果表、边际表、趋势与原因分析、异常说明。不得为了得到单调结果修改数据或参数；不得预设结论。
> 5. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) 12 场景全部 Optimal；2) 每个场景约束检查与独立检查均通过；3) 矩阵 CSV 与逐时 CSV 求和一致；4) 边际表由未舍入的 CSV 数值计算；5) 分析文档如实描述了与预期方向不符的结果（如有）。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
