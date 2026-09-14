# 当前状态

## U10最新状态

U10 complete / supported：运行 `U10-20260914T125454Z` 的 NASA POWER 冻结请求返回 HTTP 200，武汉 `30.5900,114.3000`、UTC `20200101`—`20200107`、`ALLSKY_SFC_SW_DWN,WS50M` 均与冻结参数一致。168 条 UTC 时点连续无重复，缺失/重复/不可解析/非有限/填充值/范围违规计数均为 0；离线重放输入 SHA-256 一致。原始响应：`data/raw/U10-20260914T125454Z/nasa_power_hourly_wuhan_20200101_20200107_utc.json`，SHA-256 `66eb140842a767efd840c03f958ab66285049735f3f18f4d8c1a2a19d6b6956d`；输入：`data/processed/U10-20260914T125454Z_input_168h_wuhan_20200101T0000Z_20200107T2300Z.csv`（规范副本 `data/processed/input_168h.csv`），SHA-256 `cea7505e933f2b68775a8a5fd05e473af0d5d28ba23904f33cc813d686bac07f`；质量报告和 manifest 分别为 `data/processed/U10-20260914T125454Z_quality_report.json`、`data/processed/U10-20260914T125454Z_run_manifest.json`。该结论仅支持数据输入契约，不支持经济性、可靠性或容量最优结论。

## U09最新状态

U09 complete / supported：主网格、反序重跑和高投资稳健性网格各 101 次 MILP 全部 Optimal，两套验证及 42 项测试通过。主网格唯一最低点为 70 MWh / 25 MW，位于冻结网格内部；高投资下为 70 MWh / 20 MW。这是 24 h 构造算例与示例成本下的离散样本最低点，非真实工程全局最优。未推送。

## U08最新状态

U08 complete / supported：12场景全部Optimal、反序重跑一致，两套验证及36项当时测试通过；三项冻结趋势成立。系数1.2/1.4下80相对40 MWh综合成本略升。

## U07R最新状态

U07R complete / supported：8约束组合+反序8重跑通过，采用Shapley模型内会计分配；它不证明因果，也不修复U07原公式。

## U07最新状态

U07 complete / invalid（归因设计）：独立数值审计supported，4小时手算和32项测试通过；原归因公式漏计储能及跨时段交互而无效。该标签不表示U06模型无效。

## U06修复后最终状态（优先于下方历史）

U06 complete / supported，02运行7场景全部通过，最大残差7.37e-12；28项测试通过。修复CBC文本解舍入，判据与参数不变；01失败记录保留。下一步U07，尚未执行；未推送GitHub。

## U06 最新状态

U06：blocked / invalid，已实现MILP和独立数值校验。主场景及部分变体通过；零新能源功率平衡残差5e-6 MW超过冻结门槛，立即停止，保留failure.json及部分CSV。尚未进入U07，未推送。下方U06未开始状态为历史记录。

## 2026-09-13 U00 更新（优先于下方历史快照）

- U00：complete / supported（当前 Linux 环境工程基线；不代表优化模型完成）。
- 既有初始提交 df5b172d2f11166614fa81bdba6f7dbba5fccf45 保留；仅本地操作，未推送。
- 25项测试本轮全部通过；环境、冻结哈希、既有重跑差异、完整清单见 instructions/baseline_*。
- U01—U05仍为规则模型历史基线；此条为 2026-09-13 历史说明，U10 已于其后完成，U11—U14未开始。
- 用户Windows .venv及PowerShell/Git Bash兼容性未验证。下一步U06需独立冻结。
- 下方“尚未是git仓库”等为2026-09-12历史状态，不再代表当前状态。

更新时间：2026-09-12。范围：本执行包建立时的项目真实状态核对（只读，未改代码）。

| 项目 | 状态 | 已有证据 / 下一步 |
|---|---|---|
| 第 1—6 阶段代码与结果 | complete（历史基线） | 入口 run_data_24h.py / run_no_storage.py / run_storage.py / run_capacity_sensitivity.py / run_economics.py；结果与测试见 U01—U05 findings |
| 现有测试 | complete / passed（历史） | 25 项 unittest 通过（5+5+8+7 按阶段分布）；U00 将全量重跑记录 |
| 版本控制 | not_started | 项目尚未是 git 仓库；U00 负责建立版本基线 |
| 执行说明包 | complete | 本包（specs/studies/prompts 齐备），仅为说明包验收 |
| U00 基线冻结 | not_started | verdict=null，decision-rule 未冻结 |
| U01—U05 基线登记 | complete（事后整理） | 判据为事后整理，不进入 claims |
| U06—U14 未来单元 | U10 complete / supported；U11—U14 not_started | U10 证据见本页最新状态与 U10 findings；其余单元 verdict=null |
| 优化求解器依赖 | not_started | scipy / PuLP 均未安装；U06 安装并锁定版本 |
| 真实数据（NASA POWER） | complete / supported | `U10-20260914T125454Z`；原始与 168h 输入哈希见本页 U10最新状态 |

状态字段与科研判定分开：工程可用 `not_started / in_progress / blocked / complete`；`complete` 只代表工作做完，不自动表示研究结论 supported。
