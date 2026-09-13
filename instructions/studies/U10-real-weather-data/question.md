---
unit: U10
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：真实气象数据管线（NASA POWER → 168h）

## 要回答的可判定问题

基于 NASA POWER 武汉坐标（30.59°N, 114.30°E）逐小时辐照度与风速数据，经可解释的物理转换模型，能否生成**可复现**的 168 小时风光输入（通过 `src/data_loader.py` 全部校验）？原始数据、转换脚本与最终输入是否完整存档？

## 上游证据

U00（产物清单与哈希规范）、specs/data.md 数据来源计划、`src/data_loader.py`（校验口径）

## 范围

- 只建数据管线，不跑调度模型、不做寻优
- 负荷仍为构造形状（24h 形状 × 7 天 ± 日间系数），**必须标注为构造负荷**
- 不登记 claims（exploratory）

## 预期结果与可能作废原因

- 预期：API 可访问时数据完整；转换后的风光出力通过校验（非负、有限、光伏夜间为 0）
- 可能 invalid/blocked：网络或 API 失败（→ 交付独立下载脚本，判 blocked，不伪造数据）；数据缺失值处理不当
