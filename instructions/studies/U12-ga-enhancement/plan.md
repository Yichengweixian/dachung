# U12 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录判据哈希；确认 U09 verdict 为 supported 或 inconclusive（有网格基准可对照）
- [ ] 0.2 冻结：GA 参数（种群 30/代数 50/种子 {42,7,2026}）、变量范围、误差阈值 0.5%

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U12：遗传算法增强。先读 `instructions/studies/U12-ga-enhancement/design.md` 与 U09 的 findings.md，然后：
>
> 1. 新建 `src/ga_search.py`：目标函数封装 U09 的"LP 求解 + 评价"（import 复用，禁止复制实现），每次评估计数；实现 GA（参数按 design.md）。
> 2. 新建 `run_ga.py`：三个种子各跑一次，保存收敛曲线、最终解与评估次数到 `results/ga/`。
> 3. 写 `docs/ga_comparison.md`：与 U09 网格基准的成本相对误差、评估次数对比、连续域与离散网格的口径差异说明；失败运行完整保留，不删除。
> 4. 时间允许再实现 PSO 并同样对比（可选，不影响本单元判定）。
> 5. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) 目标函数与 U09 为同一实现（贴出 import 位置）；2) 每次运行评估次数统计准确；3) 三次种子运行的最优成本与收敛曲线完整保存；4) 文档区分了"网格基准"与"GA 结果"口径。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
