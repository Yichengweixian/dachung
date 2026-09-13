---
unit: U13
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：决策软件原型（Streamlit）

## 要回答的可判定问题

基于现有 src 模块的 Streamlit 原型能否实现申报书要求的七大功能（数据导入、参数设置、平衡计算、储能寻优、方案对比、图表展示、报告导出），且对同一输入输出与 `results/` 中既有结果逐值一致？

## 上游证据

U06—U09（模型与寻优核心）、申报书研究内容 6（软件功能清单）、`src/` 全部可复用模块

## 范围

- 软件是**原型**：本地运行、用于答辩演示与软著材料，不做生产级部署
- 软件必须调用现有 `src/` 模块，禁止复制一份逻辑到 web 层
- 不登记 claims（exploratory）

## 预期结果与可能作废原因

- 预期：七模块可用；演示算例（24h 数据 + 40/20 储能）与 `results/` 数字一致
- 可能 invalid：web 层复制了调度逻辑；同输入输出与既有结果不一致；异常输入导致崩溃
