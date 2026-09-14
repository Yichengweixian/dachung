---
unit: U02
mode: 历史基线（判据事后整理）
status: complete
verdict: 基线证据，不进入 claims
---

# 单元问题（回顾登记）：无储能规则平衡（项目第 3 阶段）

## 原问题

新能源优先消纳、火电补缺（上限 120 MW）、剩余缺口记失负荷的逐时规则平衡能否通过校验？本单元于执行包建立前已由 Codex 完成，此处只登记证据。

## 登记要点

- 入口：`run_no_storage.py`；核心：`src/balance_model.py`（4 行公式）、`src/metrics.py`、`src/validation.py`（21 项检查）
- 配置：`config/no_storage.json`（thermal_max 120 MW）
- 输出：`results/no_storage_hourly.csv`、`results/no_storage_summary.csv`、`figures/no_storage_balance.png`
- 测试：`tests/test_no_storage.py`（5 项，含真实数据未触发的失负荷分支）
