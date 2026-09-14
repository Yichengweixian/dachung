---
unit: U05
mode: 历史基线（判据事后整理）
status: complete
verdict: 基线证据，不进入 claims
---

# 单元问题（回顾登记）：简单经济性评价（项目第 6 阶段）

## 原问题

对五组容量规则调度结果核算综合成本（火电 + 储能投资年化分摊 + 运维 + 弃电惩罚 + 失负荷惩罚），给定五组中成本最低的是哪组？是否存在内部经济最优？本单元已由 Codex 完成，只登记证据。

## 登记要点

- 入口：`run_economics.py`；核心：`src/economic_model.py`（EconomicParameters、CRF、分项成本、19 项费用校验）、`src/plot_economics.py`
- 配置：`config/economics.json`（标注"人为设置的模型测试参数，非文献数据"：火电 350 元/MWh、能量 800 元/kWh、功率 300 元/kW、寿命 15 年、折现 5%、弃电 200、失负荷 10000、可变运维 10 元/MWh 放电侧）
- 输出：`results/economics/`（summary.csv 17 位有效数字、dispatch_summary.csv、五份逐时、run_manifest.json）、`figures/economics/capacity_vs_total_cost.png`
- 测试：`tests/test_economics.py`（7 项新增，总计 25 项）
- 初始库存影响单列 initial_inventory_supply_MWh 与 initial_inventory_thermal_value_CNY，不计入 Total Cost
