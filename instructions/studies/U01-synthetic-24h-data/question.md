---
unit: U01
mode: 历史基线（判据事后整理）
status: complete
verdict: 基线证据，不进入 claims
---

# 单元问题（回顾登记）：24 小时构造数据（项目第 2 阶段）

## 原问题

构造一组可复现、通过 13 项校验的 24 小时风光荷数据，并绘制输入曲线。本单元于执行包建立前已由 Codex 完成，此处只登记证据，不重新执行、不补写判据。

## 登记要点

- 入口：`run_data_24h.py`；生成逻辑：`src/generate_data.py`；参数：`config/data_24h.json`（seed 20260910，风 100 MW、光 150 MW、峰荷 162 MW）
- 输出：`data/input_24h.csv`、`figures/input_24h_profiles.png`
- 说明文档：`docs/data_description.md`
