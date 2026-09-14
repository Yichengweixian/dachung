---
unit: U03
mode: 历史基线（判据事后整理）
status: complete
verdict: 基线证据，不进入 claims
---

# 单元问题（回顾登记）：固定储能规则调度（项目第 4 阶段）

## 原问题

40 MWh / 20 MW 储能（SOC 10%–90%、初始 50%、效率 0.95）按"富余充电、缺电优先放电、火电补缺"规则调度，能否通过功率、SOC 与能量守恒校验？本单元已由 Codex 完成，只登记证据。

## 登记要点

- 入口：`run_storage.py`；核心：`src/storage_model.py`（StorageParameters + 时序递推）、`src/storage_metrics.py`、`src/storage_validation.py`
- 配置：`config/storage.json`
- 输出：`results/storage_hourly.csv`、`storage_summary.csv`、`storage_baseline_hourly.csv`、`storage_comparison.csv`、`figures/storage_comparison.png`
- 测试：`tests/test_storage.py`（15 项，含充放电功率、SOC 边界、效率递推、零容量退化）
- 已知边界：无期末 SOC 归位，期末 SOC 被放至下限 10%（初始库存被消耗）
