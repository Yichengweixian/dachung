# U08 设计：渗透率 × 储能场景矩阵

## 场景定义

- 系数：0.8 / 1.0 / 1.2 / 1.4，同时乘 wind 与 solar 列（负荷、火电不变）
- 储能：0 / 40 / 80 MWh；功率 = 容量 × 0.5（0 / 20 / 40 MW）；SOC 初值 0.5、范围 0.1–0.9、效率 0.95（storage.json 口径）
- 命名：`R080_E000` … `R140_E080`，共 12 场景
- 配置表：`data/scenarios/penetration_scenarios.csv`（scenario, wind_factor, solar_factor, energy_capacity_MWh, power_capacity_MW），由入口读取，不在代码里硬编码

## 计算流程

1. 读 `data/input_24h.csv`，按系数缩放风/光
2. 每个场景独立调用 U06 的 LP 建模函数（`src/optimization_model.py`，只允许复用、不允许复制一份改参数）
3. 每个场景执行 U06 的全部约束检查 + U07 独立检查（对 CSV 读回结果）
4. 汇总矩阵 `results/penetration/matrix_summary.csv`：消纳率、弃电率、弃电量、火电发电量、失负荷量、储能充放电、综合成本（U05 口径）
5. 边际计算：同一系数下 0→40、40→80 的消纳率增益与成本变化
6. 图：系数×储能 消纳率/弃电率/成本 分组对比（figures/penetration/）

## 输出与文档

- `results/penetration/`（矩阵 CSV、12 份逐时、run_manifest.json）
- `docs/renewable_penetration_analysis.md`：结果表、边际表、趋势解释、**不得预设结论**；若出现与预期方向相反的结果，如实分析原因
