---
unit: U11R08
freeze_status: approved_for_freeze
user_approval: explicit_2026-09-27
---

# 冻结判定规则

每组报告原生完整精度D_min=t*、D_min-0.02、有理数上下界和三通道误差。
门槛严格为0.02，不加容差；显示舍入不参与判定。

有效性：输入哈希和代表日逐值一致；原簇点可行；主/复核LP均Optimal；
原生与CSV读回一致；权重界与和残差≤1e-7天，归一化不等式残差≤1e-8；
主/独立目标差≤1e-8，有理数上下界宽度≤1e-8，原生t距该区间≤1e-8。
|D_min-0.02|≤1e-8标为uncertain，需要更强精确最优证书；此范围只增加不确定性，
不放宽门槛。其余情况下，严格上界≤0.02且D_min≤0.02为reachable；
严格下界>0.02且D_min>0.02为unreachable；证据不足为uncertain。

任一非Optimal、数值异常、来源不一致或审计失败：立即停止，保存模型、日志、
failure.json与失败位置；工程blocked、verdict=invalid（数值或实现问题），
不得以Infeasible断言2%数学不可达，不换参数补考。独立审计证据不足而非算术错误
时只标uncertain/inconclusive，并说明缺少的证据。

完整九组有效且至少一个共同N在三seed均reachable：supported（仅输入电量问题）。
完整有效且每个N至少有一个已证unreachable：refuted（仅当前数据、日集合和边界）。
否则inconclusive。未运行verdict=null。禁止跨seed拼接N。
附加比例门槛仍为1.0个百分点；完整报告所有组，不以附加结果宣布U11完成。

正式主LP预算9，独立CBC LP预算9，新增调度MILP为0；实际、失败和测试调用分开登记。
冻结后不修改研究输入、算法、求解参数、候选、门槛或方向。代码修错需保存失败记录。
