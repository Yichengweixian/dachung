# U11R08 冻结前登记

新路径：src/energy_calibrated_weights_resolved.py、src/cbc_weight_evidence.py、run_energy_calibrated_days_resolved.py、scripts/audit_energy_calibrated_days_resolved.py、scripts/audit_u11r08_partial.py、tests/test_resolved_weight_bands.py。复用旧CBC命令/原生精度解读逻辑与聚类/调度，不改旧文件。

运行目录results/annual/U11R08-v01。保留真实CBC MPS与原生二进制解；测试调用在正式运行外，运行manifest登记方法参数、实际Git版本、来源/产物SHA-256和依赖版本。独立审计零新增优化调用。

冻结前选择1e-6的依据仅为诊断残差/现有验收与求解精度尺度。运行中不得改带宽/门槛，也不得在失败后换参数补考。
