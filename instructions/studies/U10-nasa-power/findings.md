---
unit: U10
status: complete
verdict: supported
rule_commit: null
code_commit: null
run_ids: [U10-20260914T125454Z]
completed_at: 2026-09-14
---

# U10 结果与判定

已于 2026-09-14 运行一次冻结的 NASA POWER 请求；没有重试、没有改动冻结参数、没有安装依赖或运行调度/优化。负荷仍为 24 小时构造形状的七天循环，非真实负荷。

## 执行后必须填写的证据表

| 项目 | 记录值（当前） | 验收依据 |
|---|---|---|
| 运行 ID 与时间 | `U10-20260914T125454Z`；请求 `2026-09-14T12:54:54.636277Z`，响应 `2026-09-14T12:54:55.825648Z` | UTC 记录 |
| 冻结请求 | HTTP 200；武汉 `30.5900,114.3000`；`ALLSKY_SFC_SW_DWN,WS50M`；UTC `20200101`—`20200107` | 与冻结端点及参数完全一致 |
| 请求与原始文件 | `data/raw/U10-20260914T125454Z/`；SHA-256 `66eb140842a767efd840c03f958ab66285049735f3f18f4d8c1a2a19d6b6956d` | request JSON 与 `.sha256` 均可复算 |
| 时间窗 | `2020-01-01T00:00Z` 至 `2020-01-07T23:00Z`，`hour=0…167`，168 条 | 唯一连续 UTC 小时 |
| 单位与质量计数 | 辐照度 `Wh/m^2`（逐小时间隔，等价于规则的 `Wh/m²/h` 数值口径）、风速 `m/s`；missing/duplicate/unparseable/nonfinite/fill/range 均为 0 | `quality_report.json` 的 `passed=true` |
| 转换文件 | `data/processed/U10-20260914T125454Z_input_168h_wuhan_20200101T0000Z_20200107T2300Z.csv`；SHA-256 `cea7505e933f2b68775a8a5fd05e473af0d5d28ba23904f33cc813d686bac07f` | 风 `0—54.083843 MW`；光 `0—51.780000 MW` |
| 输入契约 | `validate_input_data(..., 168, 1.0)` 通过 | 四列完整、有限非负、小时连续 |
| 重复转换 | 临时目录离线重放 SHA-256 同为 `cea7505e933f2b68775a8a5fd05e473af0d5d28ba23904f33cc813d686bac07f` | 相同原始证据与参数逐字节一致 |
| 最终 verdict | `supported` | 所有 `decision-rule.md` 有效性闸门通过 |

证据文件为 `data/raw/U10-20260914T125454Z/`、`data/processed/U10-20260914T125454Z_quality_report.json` 和 `data/processed/U10-20260914T125454Z_run_manifest.json`。该 `supported` 仅支持“冻结数据管线满足输入契约”；不登记 claim，也不外推至真实负荷、经济性、可靠性或容量最优。
