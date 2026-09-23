# U14 数字一致性核对表（脚本生成，勿手改）

生成脚本：`scripts/check_materials_numbers.py`；出处表：`docs/revisions/U14-T4-v01/number_sources.csv`；共 86 行；判定：**consistency_failed**。

| ID | 材料中数值 | 单位 | 出处 | 选择器 | 列/字段 | 核对 |
|---|---|---|---|---|---|---|
| P01 ✔ | 40 | MWh | `config/storage.json` | `key=energy_capacity_MWh` | `` | 一致 |
| P02 ✔ | 20 | MW | `config/storage.json` | `key=power_capacity_MW` | `` | 一致 |
| P03 ✔ | 0.5 | - | `config/storage.json` | `key=soc_initial` | `` | 一致 |
| P04 ✔ | 0.1 | - | `config/storage.json` | `key=soc_min` | `` | 一致 |
| P05 ✔ | 0.9 | - | `config/storage.json` | `key=soc_max` | `` | 一致 |
| P06 ✔ | 0.95 | - | `config/storage.json` | `key=eta_charge` | `` | 一致 |
| P07 ✔ | 0.95 | - | `config/storage.json` | `key=eta_discharge` | `` | 一致 |
| P08 ✔ | 30 | MW | `config/optimization.json` | `key=thermal_min_MW` | `` | 一致 |
| P09 ✔ | 30 | MW/h | `config/optimization.json` | `key=thermal_ramp_MW_per_h` | `` | 一致 |
| P10 ✔ | 120 | MW | `config/no_storage.json` | `key=thermal_max_MW` | `` | 一致 |
| P11 ✔ | 350 | 元/MWh | `config/economics.json` | `key=parameters.thermal_cost_CNY_per_MWh` | `` | 一致 |
| P12 ✔ | 800 | 元/kWh | `config/economics.json` | `key=parameters.storage_energy_capex_CNY_per_kWh` | `` | 一致 |
| P13 ✔ | 300 | 元/kW | `config/economics.json` | `key=parameters.storage_power_capex_CNY_per_kW` | `` | 一致 |
| P14 ✔ | 200 | 元/MWh | `config/economics.json` | `key=parameters.curtailment_penalty_CNY_per_MWh` | `` | 一致 |
| P15 ✔ | 10000 | 元/MWh | `config/economics.json` | `key=parameters.load_shedding_penalty_CNY_per_MWh` | `` | 一致 |
| P16 ✔ | 15 | 年 | `config/economics.json` | `key=parameters.storage_lifetime_years` | `` | 一致 |
| P17 ✔ | 0.05 | - | `config/economics.json` | `key=parameters.discount_rate` | `` | 一致 |
| P18 ✔ | 10 | 元/MWh | `config/economics.json` | `key=parameters.storage_variable_om_CNY_per_MWh_discharged` | `` | 一致 |
| P19 ✔ | 8760 | 小时/年 | `config/economics.json` | `key=parameters.hours_per_year` | `` | 一致 |
| N01 ✔ | 81.8231 | % | `results/optimization/U06R01-v03/summary.csv` | `scenario=main` | `renewable_utilization_pct` | 一致 |
| N02 ✔ | 395.5002 | MWh | `results/optimization/U06R01-v03/summary.csv` | `scenario=main` | `curtailment_MWh` | 一致 |
| N03 ✔ | 0 | MWh | `results/optimization/U06R01-v03/summary.csv` | `scenario=main` | `unserved_MWh` | 一致 |
| N04 ✔ | 496637.54 | 元/24h | `results/optimization/U06R01-v03/summary.csv` | `scenario=main` | `total_cost_CNY` | 一致 |
| N05 ✔ | 7.3736572403504397e-12 | - | `results/optimization/U06R01-v03/summary.csv` | `scenario=main` | `max_residual` | 一致 |
| N06 ✔ | 7 | 场景 | `results/optimization/U06R01-v03/summary.csv` | `count` | `` | 一致 |
| N07 ✔ | 91.2939 | % | `results/optimization/U06R01-v03/summary.csv` | `scenario=method` | `renewable_utilization_pct` | 一致 |
| N08 ✔ | 78.2654 | % | `results/optimization/U06R01-v03/summary.csv` | `scenario=zero_storage` | `renewable_utilization_pct` | 一致 |
| N09 ✔ | 17 | 场景 | `instructions/studies/U07R01-factorial-audit/findings.md` | `text` | `共17场景` | 一致 |
| N10 ✔ | 1.4551915228366852e-11 | - | `instructions/studies/U07R01-factorial-audit/findings.md` | `text` | `1.4551915228366852e-11` | 一致 |
| N11 ✔ | 87.1135 | % | `results/penetration/U08-master-v01/summary.csv` | `scenario=R080_E000` | `renewable_utilization_pct` | 一致 |
| N12 ✔ | 62.9123 | % | `results/penetration/U08-master-v01/summary.csv` | `scenario=R140_E000` | `renewable_utilization_pct` | 一致 |
| N13 ✔ | 3.557695 | pp | `results/penetration/U08-master-v01/marginal.csv` | `factor=1.0` | `gain_0_40_pp` | 一致 |
| N14 ✔ | 2.004261 | pp | `results/penetration/U08-master-v01/marginal.csv` | `factor=1.0` | `gain_40_80_pp` | 一致 |
| N15 ✔ | 12 | 场景 | `results/penetration/U08-master-v01/summary.csv` | `count` | `` | 一致 |
| N16 ✔ | 486358.65 | 元/24h | `results/grid_search/U09R01-v01/summary.csv` | `scenario=E070_P25` | `total_cost_CNY` | 一致 |
| N17 ✔ | 83.4660 | % | `results/grid_search/U09R01-v01/summary.csv` | `scenario=E070_P25` | `renewable_utilization_pct` | 一致 |
| N18 ✔ | 359.7528 | MWh | `results/grid_search/U09R01-v01/summary.csv` | `scenario=E070_P25` | `curtailment_MWh` | 一致 |
| N19 ✔ | 496610.8326 | 元/24h | `results/grid_search/U09R01-v01/robustness_summary.csv` | `scenario=E070_P20` | `total_cost_CNY` | 一致 |
| N20 ✔ | 101 | 候选 | `results/grid_search/U09R01-v01/summary.csv` | `count` | `` | 一致 |
| N21 ✔ | 303 | 次 | `instructions/studies/U09R01-grid-clarification/findings.md` | `text` | `共303次` | 一致 |
| N22 ✔ | 168 | 小时 | `results/real_data/U10-master-v01/input_168h.csv` | `count` | `` | 一致 |
| N23 ✔ | 16 | 统计量 | `results/real_data/U10-master-v01/robustness.csv` | `count` | `` | 一致 |
| N24 ✔ | 0 | - | `results/real_data/U10-master-v01/robustness.csv` | `max:relative_difference` | `` | 一致 |
| N25 ✔ | 30.59 | °N | `config/study_sequence_v02.json` | `key=U10.latitude` | `` | 一致 |
| N26 ✔ | 114.3 | °E | `config/study_sequence_v02.json` | `key=U10.longitude` | `` | 一致 |
| N27 ✔ | 6.4346 | pp | `results/annual/U11R02-v01/comparison.csv` | `seed=42;N=12` | `worst_error_pp` | 一致 |
| N28 ✔ | 6.7137 | pp | `results/annual/U11R02-v01/comparison.csv` | `seed=42;N=8` | `worst_error_pp` | 一致 |
| N29 ✔ | 6.6054 | pp | `results/annual/U11R02-v01/comparison.csv` | `seed=7;N=12` | `worst_error_pp` | 一致 |
| N30 ✔ | 365 | 天 | `results/annual/U11R02-v01/daily_summary.csv` | `count` | `` | 一致 |
| N31 ✔ | 425 | 次 | `instructions/studies/U11R02-annual-coherent/findings.md` | `text` | `425次Optimal` | 一致 |
| N32 ✔ | 8760 | 小时 | `results/annual/U11R02-v01/input_8760h.csv` | `count` | `` | 一致 |
| N33 ✔ | 0 | 小时 | `instructions/studies/U11R02-annual-coherent/findings.md` | `text` | `触发0小时` | 一致 |
| N34 ✔ | 1 | pp | `instructions/studies/U11R02-annual-coherent/findings.md` | `text` | `均超过1个百分点` | 一致 |
| N35 ✔ | 1480 | 次 | `results/ga/U12R01-v01/summary.csv` | `seed=42` | `evaluations` | 一致 |
| N36 ✔ | 4440 | 次 | `instructions/studies/U12R01-ga-baseline/findings.md` | `text` | `共4440次` | 一致 |
| N37 ✔ | 485969.51 | 元/24h | `results/ga/U12R01-v01/summary.csv` | `seed=42` | `cost` | 一致 |
| N38 ✔ | 0.0800103 | % | `results/ga/U12R01-v01/summary.csv` | `seed=42` | `relative_error` | 一致 |
| N39 ✔ | 0.0793060 | % | `results/ga/U12R01-v01/summary.csv` | `seed=7` | `relative_error` | 一致 |
| N40 ✔ | 0.0777284 | % | `results/ga/U12R01-v01/summary.csv` | `seed=2026` | `relative_error` | 一致 |
| N41 ✔ | 0.5 | % | `instructions/studies/U12R01-ga-baseline/findings.md` | `text` | `全部低于0.5%` | 一致 |
| N42 ✔ | 101 | 次 | `instructions/studies/U12R01-ga-baseline/findings.md` | `text` | `评估次数均超过101` | 一致 |
| N43 ✔ | 1.4210854715202004e-14 | - | `results/prototype/U13R01-v01/checks.json` | `key=milp_24h_max_diff` | `` | 一致 |
| N44 ✔ | 4.2105180453333446e-11 | - | `results/prototype/U13R01-v01/checks.json` | `key=rule_24h_max_diff` | `` | 一致 |
| N45 ✔ | 5.820766091346741e-11 | - | `results/prototype/U13R01-v01/checks.json` | `key=grid_max_diff` | `` | 一致 |
| N46 ✔ | 44 | 项 | `results/prototype/audit_v01/unit_tests_20260916.txt` | `text` | `Ran 44 tests` | 一致 |
| N47 ✔ | 0 | 个 | `results/prototype/browser_check_v02/browser_checks.json` | `count:console_error_events` | `` | 一致 |
| N48 ✔ | 5 | 步 | `results/prototype/browser_check_v02/browser_checks.json` | `count:steps` | `` | 一致 |
| N49 ✔ | 91.1760 | % | `results/capacity_sensitivity/summary.csv` | `scenario=E40_P20` | `renewable_utilization_pct` | 一致 |
| N50 ✔ | 1200 | 元/kWh | `config/study_sequence_v02.json` | `key=U09.robust_energy_capex` | `` | 一致 |
| N51 ✔ | 500 | 元/kW | `config/study_sequence_v02.json` | `key=U09.robust_power_capex` | `` | 一致 |
| N52 ✔ | 0.8 | - | `config/study_sequence_v02.json` | `key=U08.factors.0` | `` | 一致 |
| N53 ✔ | 1.4 | - | `config/study_sequence_v02.json` | `key=U08.factors.3` | `` | 一致 |
| N54 ✔ | 252 | 次 | `results/annual/U11R03-v01/run_manifest.json` | `key=details.solves` | `` | 一致 |
| N55 ✔ | 0.013143 | 百分点 | `results/annual/U11R03-v01/comparison.csv` | `N=48;seed=42` | `worst_error_pp` | 一致 |
| N56 ✔ | 0.077019 | 百分点 | `results/annual/U11R03-v01/comparison.csv` | `N=48;seed=7` | `worst_error_pp` | 一致 |
| N57 ✔ | 0.234675 | 百分点 | `results/annual/U11R03-v01/comparison.csv` | `N=48;seed=2026` | `worst_error_pp` | 一致 |
| N58 ✔ | 7.123600 | % | `results/annual/U11R03-v01/comparison.csv` | `N=48;seed=42` | `wind_relative_error` | 一致 |
| N59 ✔ | 10.303090 | % | `results/annual/U11R03-v01/comparison.csv` | `N=48;seed=7` | `wind_relative_error` | 一致 |
| N60 ✔ | 3.225039 | % | `results/annual/U11R03-v01/comparison.csv` | `N=48;seed=2026` | `wind_relative_error` | 一致 |
| N61 ✔ | 89 | 次 | `results/ga/U12R02-v02/summary.csv` | `seed=42` | `evaluations` | 一致 |
| N62 ✔ | 10 | 个 | `results/ga/U12R02-v02/run_manifest.json` | `key=details.successful_seeds` | `` | 一致 |
| N63 ✔ | 890 | 次 | `results/ga/U12R02-v02/run_manifest.json` | `key=details.primary_calls` | `` | 一致 |
| N64 ✔ | 979 | 次 | `results/ga/U12R02-v02/run_manifest.json` | `key=details.total_calls` | `` | 一致 |
| N65 ✔ | 11.881188 | % | `results/ga/U12R02-v02/run_manifest.json` | `key=details.evaluation_reduction_fraction` | `` | 一致 |
| N66 ✔ | 0 | 元 | `results/ga/U12R02-v02-independent-audit.json` | `key=repeat_difference` | `` | 一致 |
| N67 ✔ | 2 | % | `instructions/studies/U11R03-amplitude-representative-days/decision-rule.md` | `text` | `新增2%` | 一致 |

## 外部审计抽样（decision-rule C：换人随机抽查 10 个数字）

- P16：15 年 ← `config/economics.json` 选择器 `key=parameters.storage_lifetime_years` 列 ``
- N22：168 小时 ← `results/real_data/U10-master-v01/input_168h.csv` 选择器 `count` 列 ``
- N46：44 项 ← `results/prototype/audit_v01/unit_tests_20260916.txt` 选择器 `text` 列 ``
- N47：0 个 ← `results/prototype/browser_check_v02/browser_checks.json` 选择器 `count:console_error_events` 列 ``
- N64：979 次 ← `results/ga/U12R02-v02/run_manifest.json` 选择器 `key=details.total_calls` 列 ``
- P14：200 元/MWh ← `config/economics.json` 选择器 `key=parameters.curtailment_penalty_CNY_per_MWh` 列 ``
- N10：1.4551915228366852e-11 - ← `instructions/studies/U07R01-factorial-audit/findings.md` 选择器 `text` 列 ``
- N58：7.123600 % ← `results/annual/U11R03-v01/comparison.csv` 选择器 `N=48;seed=42` 列 `wind_relative_error`
- N61：89 次 ← `results/ga/U12R02-v02/summary.csv` 选择器 `seed=42` 列 `evaluations`
- N53：1.4 - ← `config/study_sequence_v02.json` 选择器 `key=U08.factors.3` 列 ``
