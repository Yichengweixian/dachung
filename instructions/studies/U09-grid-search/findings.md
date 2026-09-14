---
unit: U09
status: complete
verdict: supported
rule_commit: null
code_commit: null
run_ids: [U09-20260913-01]
completed_at: 2026-09-13
---

# U09 结果与判定

U09 在首次求解前修正草案组合数（1+10×10=101）及前置条件，然后冻结。主网格、反序重跑、高投资参数网格各 101 次 MILP 均 Optimal，两套约束检查通过。

## A. 有效性闸门

101 个主网格组合全部 Optimal；最优调度的存盘 CSV 通过 U06 验证器和 U07 独立检查器。评价直接复用 `src.economic_model.evaluate_system_costs`。

## B. 主结果

101 个离散候选中唯一最低点为 70 MWh / 25 MW，24 h 综合成本 486358.647740 CNY，消纳率 83.466027%，弃电 359.752795 MWh，储能活跃时间占比 79.166667%，失负荷 0。该点在 E 与 P 网格均为严格内部，故按冻结判据 verdict=supported。

## C. 稳健性

反序重跑六项指标最大绝对差为 0。能量投资 800→1200 CNY/kWh、功率投资 300→500 CNY/kW 后，最低点为 70 MWh / 20 MW，容量保持、功率减小，方向检查通过。

## D. 登记

artifact：`results/grid_search/U09-20260913-01/`、`figures/grid_search/U09-20260913-01/`、`docs/grid_search_analysis.md`。本单元 exploratory，不登记 claims，未推送 GitHub。

## E. 意外发现与规格修订建议

草案将 1+10×10 误写为 111，冻结前已纠正为 101；候选值未变。当前最低点不在网格边界，但仍只是 24 h 构造数据的离散样本最低点，不能宣称真实或连续空间全局最优。
