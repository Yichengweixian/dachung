---
unit: U01
status: complete（历史基线）
verdict: 基线证据（判据事后整理，不进入 claims）
completed_at: 2026-09-10（约）
---

# U01 基线证据登记

## 已有证据

| 项 | 证据 |
|---|---|
| 数据文件 | `data/input_24h.csv`（24 行，hour/load/wind/solar，两位小数） |
| 生成脚本 | `src/generate_data.py` + `run_data_24h.py`（可重复生成，seed 20260910） |
| 校验 | 13 项：字段、0—23 连续、非负有限、不超装机、夜间光伏为 0、12 点光伏峰值、负荷早晚双峰、风电波动且相邻变化 ≤15 MW、富余与不足并存 |
| 图 | `figures/input_24h_profiles.png`（四条曲线） |
| 文档 | `docs/data_description.md`（构造方法、假设、边界） |

## 声明

判据为执行包建立后整理，仅作后续单元的输入基线；不据此登记 claims。输入 SHA-256 以 U00 冻结记录为准。
