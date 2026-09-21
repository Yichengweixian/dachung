---
unit: U08
status: complete
verdict: supported
rule_commit: null
code_commit: null
run_ids: [U08-master-v01]
completed_at: null
---

# U08 结果与判定

U08-master-v01：12场景全部Optimal，读回独立检查通过，反序重复指标最大差0。
弃电随风光系数不减、消纳率随储能不减、40到80增益不超过0到40三项全部成立。
证据results/penetration/U08-master-v01/summary.csv、marginal.csv、run_manifest.json。
这是24h构造算例观察，非真实电网结论。

## A. 有效性闸门

参数与冻结一致，24次Optimal，保存CSV独立检查通过。

## B. 主结果

三项预设趋势全部成立，supported。

## C. 稳健性

反序重跑差0；四系数下边际增益递减均成立。

## D. 登记

结果见results/penetration/U08-master-v01/，图见figures/penetration/U08-master-v01/，分析见docs/penetration_analysis_v02.md；无claims。

## E. 意外发现与规格修订建议

无需要修改冻结规则的发现；不得把风光出力系数称作实测装机比例。
