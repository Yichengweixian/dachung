# U11R08 实施计划

1. 读取R03/R04/R06/R07研究文件、冻结及源码。核对最新master、旧产物原哈希。
   将本四份文件和所有引用输入/历史manifest/计算实现哈希写入freeze.json，先于实现及求解。
2. tests/test_input_energy_feasibility.py先写测试：手算可达与不可达例、权重边界和和、
   零通道、错误数据、原簇点、读回、防覆盖、模拟非Optimal失败保存。
   执行python -m unittest tests.test_input_energy_feasibility，先确认缺失实现失败。
3. src/input_energy_feasibility.py实现独立单次LP及输入读取/审计；
   run_u11r08_feasibility.py提供--run-id，原子新建目录，失败记录并停止。
   默认正式路径results/annual/U11R08-v01；不导入聚类或调度入口。
4. scripts/audit_u11r08_feasibility.py独立读回和CBC交叉求解，有理数证书、哈希、
   精度和共同N核验；独立审查代理检查代码与证据，不共享主模型计算函数。
5. 专项测试通过后python run_u11r08_feasibility.py --run-id U11R08-v01；
   python scripts/audit_u11r08_feasibility.py --run-id U11R08-v01；
   python -m unittest discover -s tests -v进行全量回归，记录测试调用数。
6. findings.md和docs/u11r08_input_energy_feasibility.md记录九组全精度结果、共同N、
   附加比例、限制及唯一下一方向。更新instructions/sequence_status_v02.md，
   保留所有旧单元文件及状态。检查git diff、提交并推送；验证远端提交。

运行环境依赖使用仓库requirements.txt加scipy（原scikit-learn间接依赖）与测试工具，
实际版本写manifest；不改旧requirements以追溯影响冻结哈希。
