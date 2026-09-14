# 按单元执行

适用全局策略：[execution-policy.md](../specs/execution-policy.md)。代码一律由 Codex 编写（用户手动粘贴），Claude 只读审查；一次只推进一个单元。

> 请执行研究单元 UXX 的 plan.md 剩余任务组。每次先说明单元与组号；核对上游证据与 decision-rule 的实际冻结记录（哈希一致）后才动手。
>
> 组0 前置闸门未满足时暂停依赖部分；组2 的自查任何一项失败即停止并报告，不得继续；求解器状态非 Optimal 必须停止。
>
> 运行后完整保存失败、未完成与通过记录，更新 findings.md、RUNLOG.md、STATUS.md、specs/roadmap.md 以及适用的 claims。完成后停止，等待用户指令，不得自动进入下一单元。
