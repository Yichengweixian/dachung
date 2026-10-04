---
unit: U11R15
freeze_status: approved_for_freeze
user_approval: continuation_2026-10-05
---

# 冻结判据

范围/design/预算固定；先 freeze 后实现/求解；未运行 verdict=null。冻结后不得修改本文件；
需要改变规则、门槛或预算 → 新建修订单元，并在本单元 findings 记录原因。

## 1 规则（预注册，与结果无关）

L1 规则（H1 主判定）：(a) `min t`（四通道 minimax）；(b) 在 `t ≤ t* + BAND` 下 `min Σ_i d_i`，
`d_i ≥ |w_i − c_i|/c_i`；(c) 在 `Σ d_i ≤ s* + BAND` 下，按 `date_UTC` 升序对 i 依次 `min w_i` 得 v_i，
并把 `w_i` 钉在 `[max(0.5c_i, v_i − BAND), min(2c_i, v_i + BAND)]`。
L∞ 规则（对照变体，不参与判定）：(b′) 在 `t ≤ t* + BAND` 下 `min u`，`u ≥ |w_i − c_i|/c_i`；其余同上。
BAND = 1e-6；`0.5c_i ≤ w_i ≤ 2c_i`；`Σ w_i = 365`；c_i 为原簇实际天数。

## 2 预算与求解

HiGHS（`highs-ds`，presolve=True，primal/dual 1e-9，time_limit 60）：L1 3×(1+1+48)=150、L∞ 3×50=150、
每 seed 另进程重解首级 3 次。CBC（`EvidenceCBC` 原生双精度，presolve off，primalTolerance 1e-9）：
L1 3×50=150、L∞ 顶层 3×2=6。**合计 459 次 LP、0 次调度 MILP**；任何非 Optimal/非有限立即停止并保留（invalid）。

## 3 闸门（沿用 U11R08/U11R14，不放宽）

边界/总和残差 ≤ 1e-7；通道/t 归一化残差 ≤ 1e-8；精确有理证书 gap ≤ 1e-8、原生权重→证明权重修复 ≤ 1e-7；
两路径同级目标差 ≤ 1e-8；两路径最终权重差 ≤ 1e-4 天（48×(2×BAND)=9.6e-5 上界）；
首级分类：`abs(t−0.02) ≤ 1e-8` 为 uncertain，否则按精确上界/下界判 reachable/unreachable。
年度加权诊断的数值一致性：保存 CSV 读回差 ≤ 1e-6；源日物理残差 ≤ 1e-6。

## 4 判定

**H1（主）**：三 seed 的 L1 确定性权重，首级分类均为 reachable，四通道 |相对误差| ≤ 2%，
且 E ≤ 1.0 个百分点（E = max|加权代表日 − 全年基准|，取 renewable_utilization_pct 与 curtailment_rate_pct）
→ **supported**；任一 seed E > 1.0 pp 且超出 1e-6 判定余量 → **refuted**；
E 落在 1.0±1e-6 pp、或首级分类 uncertain、或两路径最终权重差 > 1e-4 天 → **inconclusive**。

**H2（次，独立报告，不影响 H1）**：三 seed 的 L1 权重 |成本误差| 与 |缺供误差| 均不大于同期"原簇计数权重"基线
→ supported；任一 seed 超出 → refuted；与门槛相差 ≤1e-6 或基线不可比 → inconclusive。

**诊断（不参与判定与选择）**：L∞ 对照变体的 E/D/成本/缺供；U11R14 两极值解；权重结构量
（移动天数、触界天数、Σ|w_i−c_i|/365、L1、L∞）——用于检验 L1 是否给出打满边界的顶点解。

**invalid**：非 Optimal、非有限、状态/身份/预算/哈希/证书/重建异常、依赖或源码漂移。
invalid 不是数学不可行结论；不得据此改写 U11R12/R13/R14 的判定。

## 5 独立审计要求

另进程、仅标准库 + `Fraction`，不导入本单元模型/运行/判定代码；从原始 CSV 重算四通道系数与年度目标、
逐级目标值与钉区间并核对保存权重、独立重算首级有理弱对偶证书与分类、独立实现年度加权聚合核对
E/D/成本/缺供、重建 509 源日物理与成本、核对全量哈希与预算计数；
审计自身禁止 `subprocess`/`pulp`/`scipy.optimize`，零求解调用。

## 6 边界与不变项

supported/refuted 仅限本年度、该 48 日集合、四通道输入口径与 40 MWh/20 MW 保存调度；
不代表跨年、任意容量、真实电网、跨日 SOC、极端日或项目整体完成。
不改旧 1 个百分点/2% 门槛；不引用申报书历史数字；不使用已求得成本/缺供拟合权重；
U11R12 refuted、U11R13 supported、U11R14 supported 与全部旧冻结文件/失败证据保持原样。
