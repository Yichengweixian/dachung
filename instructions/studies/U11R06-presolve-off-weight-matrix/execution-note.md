# U11R06 冻结前登记

实现路径：`src/cbc_presolve_off.py`、`src/energy_calibrated_weights_presolve_off.py`、`run_energy_calibrated_days_presolve_off.py`、`scripts/audit_energy_calibrated_days_presolve_off.py`。原 U11R04 文件不可修改。运行目录 `results/annual/U11R06-v01`，若失败也保留，不覆盖。审计目录另存报告。

运行环境、历史基准守卫、组顺序、求解预算、全部物理与数值阈值继承 U11R04。CBC 原生精度求解命令仅新增 `-presolve off`，保留其余参数和 60 秒超时。冻结后实现路径或方法若需实质改变，停止并另建单元。
