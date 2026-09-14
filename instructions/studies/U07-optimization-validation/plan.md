# U07 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录 U06 输出文件 SHA-256（`results/optimization/*.csv`）与判据文件哈希
- [ ] 0.2 确认 U06 findings 已填写且 verdict 为 supported；确认 `run_optimization.py` 可重复运行且结果一致
- [ ] 0.3 冻结 U07 判据（本组清单即冻结内容）

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U07：对 U06 的 LP 优化模型做独立验证，并与规则调度基线对照。先读 `instructions/studies/U07-optimization-validation/design.md` 与 U06 的 findings.md，然后：
>
> 1. 新建 `tests/test_optimization_validation.py`，按 design.md 的 6 项检查用纯 pandas/numpy 独立实现（禁止 import src/optimization_model.py 或 src/storage_validation.py 的校验函数；可以读 `results/optimization/dispatch_hourly.csv` 做数据源）。
> 2. 新建 3–4 小时手算 oracle 测试：逐值断言最优解（参照 tests/test_no_storage.py 的写法）。
> 3. 运行全量测试，确认原有 25 项 + 新增项全部通过。
> 4. 做三因素差异归因：按 design.md 的量化方法逐项计算，与 U05 的 `results/capacity_sensitivity/summary.csv`（E40_P20 行）对照，写 `docs/model_validation_report.md`（含未解释残差）。
> 5. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) 独立检查脚本确实未 import 模型校验函数（贴出 import 清单）；2) 全量测试通过数；3) 三因素合计与 U06−U05 实际差异的对照表，未解释残差的绝对值；4) 报告中没有把相关性写成因果性、没有声称已证明任何结论。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
