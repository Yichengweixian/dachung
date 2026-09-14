---
unit: U12
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：遗传算法/粒子群增强（可选）

## 要回答的可判定问题

遗传算法（或粒子群）以 U09 同一目标函数搜索 (E,P)，能否以**更少评估次数**找到与网格最优成本误差 <0.5% 的解？算法结果对随机种子是否稳健？

## 上游证据

U09（网格基准与评价函数）、specs/methods.md 方法路线

## 范围

- 目标函数与 U09 为同一实现（import 复用，禁止复制）
- 只做 GA（时间允许再 PSO）；不替换网格搜索结论——网格结果仍是"可解释基准"
- 不登记 claims（exploratory）

## 预期结果与可能作废原因

- 预期：GA 以远少于 111 次评估逼近网格最优；E/P 为连续域时可能找到网格之间的更优解（如实报告与网格口径差异）
- 可能 invalid：目标函数不一致；评估次数未统计；种子未固定
