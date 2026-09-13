# U06 设计：LP 时序优化调度

## 求解器与依赖

- **PuLP + 自带 CBC**。安装：`.\.venv\Scripts\python.exe -m pip install pulp`，运行后记录 `pulp.__version__` 与 CBC 版本到 `run_manifest.json`
- 不需要为 LP 引入二进制变量；CBC 对 24 步连续 LP 足够

## 决策变量（每个时段 t=0..23；储能状态 25 个边界）

| 变量 | 含义 | 下界/上界 |
|---|---|---|
| thermal[t] | 火电出力 MW | [30, 120] |
| wind_used[t], solar_used[t] | 风光消纳 MW | [0, 可用出力] |
| wind_curt[t], solar_curt[t] | 弃风/弃光 MW | [0, 可用出力] |
| charge[t], discharge[t] | 储能充/放电（电网侧）MW | [0, 20] |
| energy[t] | 储能电量（电池侧，25 个边界）MWh | [0.1E, 0.9E] |
| unserved[t] | 失负荷 MW | [0, 负荷] |

## 目标函数（运行成本最小，逐时求和）

min Σ_t [ 350×thermal[t] + 200×(wind_curt[t]+solar_curt[t]) + 10000×unserved[t] + 10×discharge[t] ] × dt

系数全部读取 `config/economics.json`，不在代码里写死。dt 读取 `config/simulation.json`。

## 约束

1. **功率平衡**（每时）：wind_used + solar_used + thermal + discharge + unserved = load + charge
2. **风光分解**（每时）：used + curt = 可用出力（wind、solar 各自成立）
3. **火电爬坡**：|thermal[t] − thermal[t−1]| ≤ 30（t=1..23；t=0 不设）
4. **储能 SOC 递推**：energy[t+1] = energy[t] + 0.95×charge[t]×dt − discharge[t]×dt/0.95
5. **SOC 上下限**：0.1E ≤ energy[t] ≤ 0.9E（全部 25 个边界）
6. **期末归位**：energy[24] = energy[0] = 0.5E（SOC 初始 0.5，来自 `config/storage.json`）
7. **充电功率上限**：charge[t] ≤ 20（`power_capacity_MW`）

## 参数集中（新增 `config/optimization.json`）

```json
{
  "thermal_min_MW": 30.0,
  "thermal_max_MW": 120.0,
  "thermal_ramp_MW_per_h": 30.0,
  "objective_terms": ["thermal", "curtailment", "load_shedding", "storage_variable_om"]
}
```

成本系数仍从 `config/economics.json` 读取；thermal_max 与 `config/no_storage.json` 保持同一来源（实现时二者只取一处，避免双份漂移）。

## 代码结构与输出

- `src/optimization_model.py`：建模 + 求解 + 返回 DataFrame（与现有 `src/*` 风格一致：计算模块不写文件）
- `run_optimization.py`：入口——读配置 → 读 `data/input_24h.csv` → 建模求解 → 自查 → 存 `results/optimization/`（`dispatch_hourly.csv`、`summary.csv`、`run_manifest.json`）→ 读回再校验
- 复用：`src/data_loader.py`（读入校验）、`src/storage_validation.py`（结果校验）、`src/metrics.py` 的汇总口径
- 输出字段沿用 `docs/metric_definitions.md`：hour、load、wind_available、solar_available、wind_used、solar_used、wind_curt、solar_curt、thermal、charge、discharge、energy_MWh、soc、unserved、balance_error_MW
- 模型必须兼容 E=P=0（零储能场景）：储能项全部为 0，SOC 相关约束自动退化（U07 稳健性要用）

## 已知的数值预期（写进判据，不写进结论）

规则调度下：夜间第 1–4 时火电需求 < 30 MW（最小出力将强迫弃风约 30+ MWh）；第 16→17 时火电需爬 44.79 MW（超 30 上限，LP 须在第 16 时提前多弃风光垫高火电）；期末归位使储能只转移当日充电量（放电 ≈ 0.9025×充电）。因此**方向性预期**：消纳率低于规则基线 89.63%–91.18% 区间，具体数值以求解结果为准，不得预填或凑数。
