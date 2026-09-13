---
unit: U06
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：24 小时时序优化调度模型（LP）

## 要回答的可判定问题

在火电**最小出力 30 MW**、**爬坡 ±30 MW/h**、**期末 SOC = 初始 SOC** 三类约束加入后，24 小时算例的线性规划（LP）调度能否求解至 Optimal 并满足全部约束？与规则调度（U03/U05 基线）相比，新能源消纳率、弃电量和火电发电量如何变化，差异能否归因到上述三类约束？

## 对应上层子问题

申报书研究内容 2（多时间尺度时序平衡模型）中"常规电源约束 + 储能 SOC 约束"的正式实现；回答导师问题"你们究竟优化了什么"的最小版本。

## 上游证据

- U03/U05 规则调度基线：`results/capacity_sensitivity/summary.csv`（消纳率 89.63%–92.72%）、`results/economics/summary.csv`
- 输入数据：`data/input_24h.csv`（SHA-256 在 U00 冻结时记录）
- 参数口径：`specs/data.md`、`specs/methods.md`、项目 `docs/metric_definitions.md`
- 成本参数：`config/economics.json`（火电 350 元/MWh、弃电惩罚 200、失负荷 10000、储能可变运维 10 元/MWh 放电侧）

## 范围

- 只做 40 MWh / 20 MW 单场景（基准储能配置），不做容量扫描（那是 U09）
- 不引入机组启停二元变量（火电保持在线）、备用约束、需求响应、网损
- 不改变输入数据；不新增惩罚项之外的目标分量
- 不登记 claims（exploratory）

## 预期结果与可能作废原因

- 预期：存在 Optimal 解；消纳率相对规则调度**下降**（最小出力迫使夜间弃风、爬坡迫使第 16–17 时附近预调），储能对消纳的改善被约束成本部分抵消；期末 SOC 归位使储能放电量小于规则调度（不再消耗初始库存）
- 可能 invalid：求解器非 Optimal、约束写错、参数与冻结值不一致、输入数据在运行期间变化
