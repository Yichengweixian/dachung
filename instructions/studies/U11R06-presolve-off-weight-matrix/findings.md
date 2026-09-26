---
unit: U11R06
status: blocked
verdict: invalid
run_ids: [U11R06-v01]
---

# U11R06 结果（2026-09-26）

按冻结规则将 CBC 权重 LP 设为 `-presolve off`，保留原数据、日集合、权重界限、目标层级、调度模型与双门槛。73 项全量单元测试通过，其中新专项 3 项含真实 CBC 小模型调用；正式矩阵与测试调用分开计数。

正式 `U11R06-v01` 在第 44 次权重 LP（N24、seed42、主计算 `lex_014`）报告 Infeasible，立即停止，未重试、未修改容差或换参数。此前 43 次 LP Optimal、12 次 N12/seed42 日调度 Optimal。九组未完成，verdict=invalid，不能报告 supported 或 inconclusive。

唯一完成组 N12/seed42：E=1.5615946626977184 个百分点，D=0.00020550860413116564；D 达标，E 不达标，且单组不构成完整矩阵结论。失败 LP CBC 日志明确记载 presolve 从 on 到 off。上阶段已验收解代入下一阶段固定带的只读诊断，归一化残差约 2.998e-9，低于原 1e-7 验收量级但非严格零；不能据此断言数学可行或 CBC 缺陷根因。

独立只读部分审计见 `results/annual/U11R06-v01-partial-audit.json`：150 项冻结/产物哈希一致，源码无漂移；44 个 LP 阶段日志均确认 presolve off，43 个 Optimal 阶段残差通过，12 个调度日成本/能量及已完成年度汇总重建通过。审计未调用求解器；`not_complete` 是预期失败运行状态，不是完整矩阵审计通过。

U11R04 的 invalid 与 U11R05 的单模型 supported 均不改变。此证据表明单实例成功不足以保证全矩阵数值稳定；下一方向若调整 LP 固定带、求解器容差、算法或模型，应另立单元并预先冻结，不在 U11R06 原地补考。项目研究仍未完成，不制作 PPT。
