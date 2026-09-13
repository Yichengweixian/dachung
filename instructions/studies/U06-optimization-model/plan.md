# U06 执行计划（可直接粘贴给 Codex 的提示词）

> 使用方式：先人工完成组0核对，再把"组0确认后"的整段提示词粘贴给 Codex 执行组1—组3。每组完成后检查，再发下一组。

## 组0 前置与冻结（人工 + Codex 只读核对）

- [ ] 0.1 记录 `data/input_24h.csv` 的 SHA-256、`config/*.json` 全部内容快照、判据文件本文件的 SHA-256，写入冻结记录
- [ ] 0.2 核对 `.venv` 可用、当前 25 项测试全过（`.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`）
- [ ] 0.3 确认 PuLP 未安装（安装动作在组1，由 Codex 执行并记录版本）
- [ ] 0.4 确认以下文件存在且内容与本设计一致：`config/economics.json`、`config/storage.json`、`config/simulation.json`、`src/data_loader.py`、`src/storage_validation.py`

## 组1 实现（Codex）

> 你是本项目编程助手。项目为高比例新能源电力电量平衡研究，已完成 24 小时构造数据、无储能与含储能规则调度、容量敏感性与经济性评价。现在执行研究单元 U06：建立 24 小时时序优化调度线性规划模型。
>
> 第一步先读这些文件（不得修改）：`instructions/specs/question.md`、`instructions/specs/data.md`、`instructions/specs/methods.md`、`instructions/specs/execution-policy.md`、`instructions/studies/U06-optimization-model/question.md`、`design.md`、`decision-rule.md`，以及项目 `docs/metric_definitions.md`、`docs/no_storage_model.md`、`docs/storage_model.md`。
>
> 然后完成以下任务：
>
> 1. 安装 PuLP：`.\.venv\Scripts\python.exe -m pip install pulp`，记录版本号；把 `pulp` 加入 `requirements.txt`。
> 2. 新建 `config/optimization.json`，内容按 design.md 的"参数集中"一节；thermal_max 与 `config/no_storage.json` 保持同一来源（从后者读取，不在两份文件里重复维护）。
> 3. 新建 `src/optimization_model.py`：用 PuLP 建立 24 步 LP。决策变量、目标函数、约束严格按 design.md 实现；所有成本系数从 `config/economics.json` 读取，SOC 参数从 `config/storage.json` 读取，禁止在代码里写死数值。模型函数接受 (data, storage, thermal参数, economic参数, dt)，返回逐时结果 DataFrame；零储能（E=P=0）时模型必须自动退化为无储能问题。
> 4. 新建 `run_optimization.py` 入口：读配置与 `data/input_24h.csv`，先只运行 40 MWh / 20 MW 单场景；保存 `results/optimization/dispatch_hourly.csv`、`summary.csv`、`run_manifest.json`（含输入 SHA-256、参数快照、PuLP/CBC 版本、求解状态）；存盘后读回 CSV 再执行一次同一校验。
> 5. 求解状态不是 Optimal 时，程序必须停止并报错，不得生成图表或结论。
> 6. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请对 U06 的 40 MWh 结果执行数值自查并逐项报告通过/失败：
>
> 1. 逐时功率平衡残差绝对值 < 1e-6 MW（消纳+火电+放电+失负荷 − 负荷 − 充电）
> 2. 火电 ∈ [30, 120]，相邻小时变化 ≤ 30 MW/h
> 3. 消纳+弃电 = 可用出力（风、光各自成立），全部变量非负且有限
> 4. 储能 SOC 全程 ∈ [0.1, 0.9]，期末 energy[24] 与初始 20 MWh 之差 < 1e-6
> 5. 充电 ≤ 20 MW、放电 ≤ 20 MW；不存在同一时段充放电同时大于 1e-6
> 6. 汇总指标：消纳率、弃电率、失负荷量、火电发电量，与逐时 CSV 手工可复核
>
> 任何一项失败：停止，报告失败项与原因，不进入组3。不要为了通过检查修改数据、参数或判据。

## 组3 判定与登记（Codex 汇总，Claude 审查）

- [ ] 按 decision-rule.md 的 A/B/C 逐条判定，结果写入 `findings.md`（supported/refuted/inconclusive/invalid，未执行保持 null）
- [ ] 追加 `RUNLOG.md`，更新 `STATUS.md`、`specs/roadmap.md`（U06 状态）
- [ ] 与规则调度（U05）的差异对照分析写入 `findings.md`：最小出力、爬坡、期末归位三因素各自的量化影响
- [ ] 完成后停止，等待用户指令；不得自动进入 U07
