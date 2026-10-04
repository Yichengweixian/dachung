# 固定设计

## 数据与身份（不变项）

- 年度输入：`results/annual/U11R02-v01/input_8760h.csv`（2023 年 8760h，NASA 气象转换 + 构造负荷）。
- 代表日集合：`results/annual/U11R12-v01/N48_seed{42,7,2026}_representatives.csv`（48 日，含 day/date_UTC/days）。
- 簇成员与计数：`results/annual/U11R08B-v01/N48_seed{seed}_labels.csv`；计数 c_i = 簇内实际天数，Σc_i = 365。
- 保存调度：`results/annual/U11R12-v01/N48_seed{seed}_cluster{k}_hourly.csv` 与 `_summary.csv`（144 日，U11R12 已审计）。
- 全年基准：`results/annual/U11R02-v01/full_annual.csv`、`daily_summary.csv`。
- 火电上限 120 MW；第四通道与 R12 选日代理同定义：
  `p_d = Σ_h max(load_h − wind_h − solar_h − 120 MW, 0) × 1h`；全年目标为 365 个**实际日** p 之和。
  **该代理不是实际缺供**，忽略储能、爬坡与火电下限。

## 模型（每 seed 一次，逐级字典序）

变量：w_i（48 个日权重）、t ≥ 0、d_i ≥ 0（L1 规则）、u ≥ 0（L∞ 规则）。
公共约束：`0.5 c_i ≤ w_i ≤ 2 c_i`、`Σ w_i = 365`；对四个通道 k（T_k > 0）
`|Σ_i a_ki w_i / T_k − 1| ≤ t`（两条不等式）；T_k = 0 时要求代表输入全为 0。

- L1 规则（主判定）：(a) `min t` → t*；(b) 固定 `t ≤ t* + BAND`，`min Σ d_i`，其中
  `d_i ≥ (w_i − c_i)/c_i`、`d_i ≥ (c_i − w_i)/c_i` → s*；(c) 固定 `Σ d_i ≤ s* + BAND`，
  按 `date_UTC` 升序对 i 求解 `min w_i` 得 v_i，并把 `w_i` 钉在
  `[max(0.5c_i, v_i − BAND), min(2c_i, v_i + BAND)]`。
- L∞ 规则（对照变体，不参与判定）：(b′) 固定 `t ≤ t* + BAND`，`min u`，`u ≥ |w_i − c_i|/c_i`；其余同上。

BAND = 1e-6（沿用 U11R08B）。两规则共用同一首级 t*。

## 求解配置与预算

- HiGHS 主路径：`scipy.optimize.linprog(method='highs-ds')`，presolve=True，
  primal/dual feasibility tolerance 1e-9，time_limit 60s，逐级在进程内求解并把每级目标/残差/日志写入 run 目录；
  每个种子另用**独立子进程**重解首级 minimax，核对目标与权重一致（另进程证据）。
- CBC 交叉路径：`src/cbc_weight_evidence.EvidenceCBC`（原生双精度留证、presolve off、primalTolerance 1e-9），
  重复 L1 全部 50 级；L∞ 只做顶层两级（primary + secondary）。
- 预算：HiGHS 3×50（L1）+ 3×50（L∞）+ 3（另进程首级）= 303；CBC 3×50（L1）+ 3×2（L∞）= 156；
  合计 **459 次 LP、0 次调度 MILP**。任何一次非 Optimal 或数值异常 → 立即停止、保留证据、判 invalid。
- 环境：numpy 2.5.3、pandas 3.0.5、scipy 1.18.1、pulp 3.3.0 与 U11R14 冻结一致；不安装/升级依赖。

## 证据与证书

- 首级 minimax 沿用 U11R08 的通道数无关精确证书：从原 CSV 十进制 `Fraction` 重算四通道系数，
  依据 HiGHS 对偶构造有理弱对偶下界，原权重仅用于有理边界投影与总和修复得上界（修复 ≤ 1e-7，不替换主权重）。
- 次级与打钉级：按冻结带核对（`t ≤ t*+BAND`、`Σd ≤ s*+BAND`、每级 `w_i` 在钉区间内），
  并保存每级目标、残差与权重；沿用 U11R08 `check_stage` 的残差口径（边界 ≤1e-6、归一化 ≤1e-7）。
- 交叉路径同一级目标差 ≤ 1e-8；两路径最终权重差 ≤ 1e-4 天（48 级 × 2 × BAND = 9.6e-5 的上界）。

## 诊断（不参与拟合与选择）

对每条规则的三组确定性权重，用 U11R12 保存的 144 个代表日调度与 R02 全年基准计算：
E（1 个百分点门槛）、四通道输入相对误差（2% 门槛）、年度成本与缺供的有符号误差；
并列出原簇计数权重、U11R14 的 HiGHS/CBC 两极值解作为对照（全部由保存结果重算，不复制旧数字）。
结构量：被移动天数、触及 0.5c/2c 边界的天数、Σ|w_i−c_i|/365、L1 与 L∞ 值 —— 用于检验"L1 是否给出打满边界的顶点解"。

## 边界

结论限于该年度、该 48 日集合、该四通道输入口径与 40 MWh/20 MW 单配置的保存调度；
不验证跨年、任意容量、真实电网、跨日 SOC、极端日；日独立 SOC 重置、无跨日耦合；
数据为 NASA 气象转换 + 构造负荷/示例成本，非真实电网数据。无 PPT。
