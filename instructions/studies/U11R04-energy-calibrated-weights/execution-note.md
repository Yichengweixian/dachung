# 执行登记（冻结前）

用户2026-09-24“同意”批准原方案，“怎么不继续”要求处理工程阻塞并继续。

旧源码快照通过scripts/audit_u11_isolated.py重建：只在隔离目录恢复旧材料检查器，并按旧SHA-256验证；未改主项目或旧manifest。v01因遗漏运行后新增的审计入口失败，完整保留；v02恢复该入口（哈希来自旧独立审计记录）后通过，复核365日基准及252日代表解和成本，没有调用求解器。

新增实现路径：src/energy_calibrated_weights.py、run_energy_calibrated_days.py、scripts/audit_energy_calibrated_days.py、tests/test_energy_calibrated_weights.py。不修改旧聚类、调度或CBC封装。权重LP使用已有FullPrecisionCBC（PuLP/CBC、原生双精度读回），不改其数值设置。保存各LP模型、状态、目标、权重及日志。实现文件的最终版本由StudyRun源哈希记录。

执行顺序：seed=42,7,2026；各seed中N=12,24,48；每组主权重计算、重复权重计算、N个日调度。每次权重计算先最差相对电量误差，再相对簇天数L1偏离，再按UTC日期升序逐权重最小化。原设计和容差不变，非Optimal或数值异常即停。

冻结环境：Python 3.13.14；PuLP 3.3.0、NumPy 2.5.3、pandas 3.0.5、scikit-learn 1.9.1、SciPy 1.18.1、threadpoolctl 3.7.0。运行前复核版本。

原研究代码应匹配旧manifest；已知材料检查器变动由隔离历史副本审计证据解释，不作为计算代码替代。新运行同时锁定当前相关源码和隔离审计报告；所有原计算代码和旧输入产物都应继续符合原哈希，不能借此忽略其他漂移。
