# 执行记录（追加式）

2026-09-13 | U06-20260913-01 | 用户批准MILP修订后冻结、实现及求解；主场景/归因/半小时/零储能通过，零新能源残差5e-6超过1e-6，立即停止 | blocked / invalid | U06 freeze.json、milp-amendment.md、results/optimization/U06-20260913-01/failure.json；未进入U07，未推送

每完成一个研究单元（或一次独立审计/重规划）追加一条，只增不改。字段：

`日期 | 单元 | 动作 | 判定/结果 | 关键文件`

---

（尚无记录。U00 执行后写入第一条。）

2026-09-13 | U00 | 用户批准当前环境修订后冻结，保留初始提交与已有重跑差异，运行25项测试及清单覆盖/重复性检查 | complete / supported，仅当前环境工程基线；Windows未验证；未推送 | baseline_freeze.json、baseline_environment.txt、baseline_tests.txt、baseline_manifest.json、baseline_preexisting_changes.patch；run_id=U00-baseline-20260913-01

2026-09-13 | U06-20260913-02 | 用户指示继续；定位CBC文本舍入，读取同次求解二进制原值；7场景通过、最大残差7.37e-12，28项测试通过 | complete / supported；01失败保留，判据/输入不变，未进入U07，未推送 | src/cbc_precision.py、tests/test_optimization.py、results/optimization/U06-20260913-02、docs/optimization_model.md

2026-09-13 | U07-20260913-01 | 冻结并独立审计；32测试通过，另进程4项重跑通过；原归因残差超门槛 | complete / inconclusive | docs/model_validation_report.md、U07/freeze.json、scripts/audit_u07.py、tests/test_optimization_validation.py；未进入U08，未推送

2026-09-13 | U07R-20260913-01 | 新建冻结单元，8组合及反序重跑、Shapley双公式和闭合验证通过 | complete / supported；旧U07不改 | results/attribution/U07R-20260913-01、docs/factorial_attribution_report.md；未进入U08，未推送

2026-09-13 | U07事后复核 | 用户要求返回检查；确认83.33%算术值正确但归因设计漏计储能并混用方法 | 数值验证supported；归因设计invalid；U07整体更正为invalid，不表示U06无效 | U07/post-audit-correction.md、docs/model_validation_report.md

2026-09-13 | U08-20260913-01 | 用户批准前置修订；12场景MILP、两套验证、CSV读回、反序重跑、边际及图表 | complete / supported；36项测试通过 | results/penetration/U08-20260913-01、figures/penetration/U08-20260913-01、docs/renewable_penetration_analysis.md；未进入U09，未推送

2026-09-13 | U09-20260913-01 | 冻结前纠正网格组合数101及前置依赖；主网格101、反序101、高投资101次MILP与两套检查 | complete / supported；唯一内部样本最低点70 MWh/25 MW，高投资下70 MWh/20 MW，42项测试通过 | results/grid_search/U09-20260913-01、figures/grid_search/U09-20260913-01、docs/grid_search_analysis.md；未进入U10，未推送
