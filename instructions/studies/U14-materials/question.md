---
unit: U14
mode: 材料整理（非实验单元）
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：成果凝练（报告/PPT/论文初稿/专利交底书）

## 要回答的可判定问题

基于项目**已真实生成**的数据、代码、测试与仿真结果，能否产出：阶段报告、10 页左右 PPT、5 分钟汇报稿、论文初稿、专利交底书初稿与软著材料清单，且材料中每一个数字都能在 `results/` 或单元 findings 中找到出处并逐项核对一致？

## 上游证据

全部前序单元 findings、`results/`、`figures/`、`docs/`、444.docx（申报书）、`specs/claims.md`

## 范围

- 只整理与撰写，不新增实验、不改代码
- 材料必须区分：构造数据 vs 真实数据、已支持结论 vs 探索性观察 vs 计划
- 本单元是材料单元，不设 verdict；完成标准按 decision-rule 的核对项执行

## 预期结果与可能作废原因

- 预期：材料齐全、数字一致、局限如实
- 可能 invalid：引用数字在 results 中不存在；把计划写成已完成；把构造数据写成真实数据
