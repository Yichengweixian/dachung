---
unit: U09
mode: exploratory
branch: null
opened: 2026-09-13
closed: null
status: not_started
verdict: null
---

# 单元问题：储能容量-功率网格搜索（核心创新点）

## 要回答的可判定问题

在 E ∈ {0,10,…,100} MWh、P ∈ {5,10,…,50} MW（E=0 时 P=0）的 **101 个**候选组合上，以 24h 综合成本（U05 口径，含投资折算）最小为目标，是否存在**内部**最优组合 (E\*, P\*)？最优组合的消纳率、储能利用率与成本热力图形态如何？

## 上游证据

U06（MILP 模型 supported）、U07（独立数值验证 supported）、U07R（修订归因 supported）、U05（成本评价函数 `src/economic_model.py`）、`config/economics.json`

## 范围

- 只做网格搜索（枚举），**不用**遗传算法（U12 再做）
- 仿真/评价/寻优三层分离：仿真=U06 MILP；评价=U05 evaluate_system_costs；寻优=网格循环
- 不登记 claims（exploratory）；结果只在 24h 构造数据 + 示例参数下成立

## 预期结果与可能作废原因

- 预期：存在内部最优点；P 偏小时充放功率成为瓶颈，E 偏大时投资摊薄收益；最优组合的边际收益趋近于零
- 可能 invalid：任一组合非 Optimal；评价函数与 U05 不一致；网格参数与冻结值不符
