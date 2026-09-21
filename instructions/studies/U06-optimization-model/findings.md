---
unit: U06
status: blocked
verdict: invalid
rule_commit: 003a014ffa95a465cb2a0f0fb5874d2ccb75580f
code_commit: null
run_ids: [U06-master-v01]
completed_at: null
---

# U06 结果与判定

2026-09-15 在 master 上按原连续 LP 规格实现并执行首个 40 MWh / 20 MW 算例。
工程验收失败并停止；`completed_at` 保持 null，不表示整个单元已完成。
`code_commit` 为 null 因本次实现尚未提交；源文件哈希已记录在运行 manifest。
这是对 master 的独立实现，不引用其他分支的运行结论。

## A. 有效性闸门

原有 25 项测试通过且所有既有已跟踪文件检查前后哈希不变。
新增 7 项测试后共 32 项通过。输入、全部 config、原始计划/判据及环境已在
`results/master_revalidation_v01/u06_freeze_record.json` 外部冻结，未改旧判据正文。
freeze 中的原 findings 哈希是执行前状态快照；本结果登记不是对冻结方法的修改。

## B. 主结果

CBC 2.10.3 / PuLP 3.3.0，连续 LP（整数变量数 0），状态 Optimal。
内存及 CSV 读回检查均发现 11 个同时充放电时段：hour=0、1、2、3、4、9、10、11、12、13、14。
最大等式残差/边界违规量为 5.789473735973161e-7，功率平衡残差为约 3.0e-7 MW，
期末归位残差为 0；这些数值均低于 1e-6，唯一失败项是 simultaneous_charge_discharge。

原 design 规定连续 LP，未限制同时充放电；plan 组2第5项明确要求不存在二者同时超过 1e-6 的时段。
故按组2“任何一项失败即停止”和 decision-rule A 的设计有效性闸门记为 invalid，
不是 Infeasible 或 LP 求解失败。原判据 A/B 对求解失败的分类另有冲突，此次未触发该分支。

## C. 稳健性

尚未执行 dt=0.5 的正式等价输入、零储能和零新能源稳健性组；主算例验收失败后停止。
新增测试中的独立半小时/零储能手算小例子不替代这些正式稳健性运行。

## D. 登记

诊断证据：`results/optimization/U06-master-v01/` 中的
`dispatch_hourly.diagnostic.csv`、`checks.json`、`cbc.log`、`tests.txt`、`failure.json`、`run_manifest.json`。
没有发布通过验收的 summary、图表或 claims。原始输入、申请书和历史模型产物均保留。

## E. 与规则调度的差异归因

未执行。主算例验收未通过，不能继续三因素归因或把 LP 诊断目标值当作有效经济结论。

## F. 意外发现与规格修订建议

独立一小时手算测试验证：load=30、wind=100、thermal_min=30、期末归位、效率0.95时，
连续 LP 会选择 charge=20、discharge=18.05；净吸收1.95 MWh，少计弃电惩罚390元，
增加放电运维180.5元，目标净减少209.5元，因此同时充放电有经济动机。
这只是定位规格冲突的小算例，不是新增正式研究结论。

后续需新建修订单元明确互斥建模方法并冻结；不能在本单元上换成 MILP、放宽检查或改变成本系数。
相关问题已登记 roadmap Backlog，完整说明见 `docs/master_instruction_validation_v01.md`。
