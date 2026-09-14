---
unit: NEW_UNIT
freeze_status: draft
freeze_commit: null
freeze_sha256: null
---

# 判定规则模板（执行前冻结，冻结后不得修改）

## A. 有效性闸门

填写：前置/后置条件、规则与阈值、证据要求、失败处理。原则：检验设计失效为 `invalid`；被测对象真实表现差为有效否定 `refuted`。

## B. 主判据

必须在执行前填入 supported / refuted / inconclusive 的**互斥条件**与优先级；写明数值阈值与效应量。未执行一律 verdict: null。

## C. 稳健性

填写：扰动或变体、通过标准、整体要求。

## D. 论断映射

confirmatory 单元填写预写措辞与 artifact/脚本；exploratory 不登记 claims。

## E. 禁止事后修改

冻结后不得修改：变量、场景、候选、阈值、参数、主要方向；需要改变 → 新建单元并在旧 findings 记录原因。
