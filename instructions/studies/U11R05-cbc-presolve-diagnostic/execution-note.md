# 冻结前执行登记

用户已确认本单元。实现使用src/cbc_presolve_diagnostic.py、run_cbc_presolve_diagnostic.py、scripts/audit_cbc_presolve_diagnostic.py、tests/test_cbc_presolve_diagnostic.py；不改已有CBC封装和U11R04实现。

Python 3.13.14、PuLP 3.3.0、CBC 2.10.3。CBC路径为.venv/Lib/site-packages/pulp/solverdir/cbc/win/i64/cbc.exe，SHA-256为fb4642eca630f6263c365975aca7e87917cbe82ed7e6ccb79804e2f1f812419c；冻结二进制哈希而非向Git上传依赖。

每次求解目录独立，模型逐字节复制；全部命令行、stdout/stderr、退出码、文本解和原生二进制保留。先读文本状态与日志，非Optimal不继续解码为有效解、不重复求解；首轮原生解与映射/残差完整验证后才执行第二轮。文本解只用于状态与舍入差记录，验收使用原生双精度和独立Decimal逐约束核对。

模型读取复用已测试的只读MPS解析器及映射；原生布局与旧FullPrecisionCBC一致。原生目标与MPS重算目标差需小于1e-6（沿用旧封装完整性检查），并报告文本目标/变量舍入差。有效性按原U11R04原单位检查，不增大1e-9固定带。新源码最终哈希由本次run_manifest记录。

原始失败与只读诊断均保留；单模型诊断通过也不能直接恢复原9组实验。
