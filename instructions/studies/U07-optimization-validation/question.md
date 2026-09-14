---
unit: U07
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：优化模型独立验证与规则调度对照

## 要回答的可判定问题

U06 的 LP 调度结果能否通过**独立于模型实现代码**的数值检查（残差、边界、守恒）？与规则调度基线（U05）的差异能否按最小出力、爬坡、期末 SOC 归位三因素数值归因？

## 对应上层子问题

specs/methods.md"验证方法"的落实；申报书第三阶段"验证模型逻辑"。

## 上游证据

- U06 findings（LP 结果）、U05 基线（规则调度五组）、U02（无储能规则）
- `docs/metric_definitions.md` 口径

## 范围

- 只验证与对照，不新增场景、不改模型
- 检查脚本必须独立实现（不 import 模型代码中的校验函数），避免自查自证
- 不登记 claims（exploratory）

## 预期结果与可能作废原因

- 预期：全部检查通过；三因素量化影响合计能解释与 U05 的主要差异
- 可能 invalid：检查脚本与模型实现共用代码路径；对照使用了不同输入或参数
