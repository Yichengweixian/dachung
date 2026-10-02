# U11R09 实施计划

1. 读README、STATUS、roadmap、顺序台账和R06—R08设计/判据/结果；核验R08主解与审计链，
   记录本地基线及全部输入SHA-256，生成本单元freeze.json后才实现和正式求解。
2. tests/test_u11r09_fixed_weights.py先覆盖：完整矩阵/共同N、严格边界、零通道、权重不能更改、
   先汇总电量后求比例、防覆盖、来源不齐和求解失败保存；先观察缺失实现失败，再实现。
3. src/fixed_weight_dispatch.py只读来源、验证D、执行保存日解并汇总；
   根入口run_u11r09_fixed_weights.py支持--run-id，以完整冻结计划运行252+9次调度。
4. scripts/audit_u11r09_fixed_weights.py另进程仅用标准库和既有独立物理检查复核，
   不调用新实现的聚合/判定函数，不调用任何求解器。scripts/finalize_u11r09.py核验报告哈希
   并写completion.json。独立审查检查实现和科学表述。
5. 运行专项测试后执行python run_u11r09_fixed_weights.py --run-id U11R09-v01；
   python scripts/audit_u11r09_fixed_weights.py --run-id U11R09-v01；
   全量python -m unittest discover -s tests -v，保存日志与求解调用计数。
6. 生成findings.md和docs/u11r09_fixed_weight_dual_threshold.md，更新README.md、
   instructions/STATUS.md、instructions/specs/roadmap.md、instructions/sequence_status_v02.md。
   复核历史文件无改动，提交并尝试推送；无写权限则如实说明。完成本单元即停止。
