---
unit: U04
mode: 历史基线（判据事后整理）
status: complete
verdict: 基线证据，不进入 claims
---

# 单元问题（回顾登记）：储能容量敏感性（项目第 5 阶段）

## 原问题

固定功率 20 MW，容量 0/20/40/60/80 MWh 五组规则调度下，消纳率、弃电、火电与储能利用率如何随容量变化？边际增益是否递减？本单元已由 Codex 完成，只登记证据。

## 登记要点

- 入口：`run_capacity_sensitivity.py`；核心：`src/capacity_sensitivity.py`（批量场景 + 边际差分）、`src/plot_capacity_sensitivity.py`
- 配置：`config/capacity_sensitivity.json`（[0,20,40,60,80]，固定 20 MW）
- 输出：`results/capacity_sensitivity/`（summary.csv、五份逐时、marginal_changes.csv、run_manifest.json）、`figures/capacity_sensitivity/` 四图
- 测试：`tests/test_capacity_sensitivity.py`（18 项）
- 可复现性：输入 SHA-256 记录、参数快照、依赖版本入 manifest
