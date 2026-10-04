# U11R15 执行计划

## 组0 冻结（人工/本单元）

- 0.1 读写前核对：`git status` 干净、HEAD 与 origin/master 一致（本会话已核对：`dede56cc`）。
- 0.2 复核前置：U11R14 manifest/独立审计哈希、U11R12 保存调度清单、U11R08B 计数、R02 年度输入；
  任一不符即停止（不进入实现）。
- 0.3 冻结四份说明与依赖：`scripts/freeze_stable_weight_selection.py` 生成 `freeze.json`
  （含 U11R14 冻结闭包 + 本单元复用模块 + CBC 可执行文件 + 年度输入与保存调度）。

## 组1 实现

- 1.1 新增 `src/stable_weight_selection.py`：四通道层级模型（L1 / L∞）、HiGHS 与 CBC 两路径求解、
  逐级残差核对、精确证书与分类、确定性打钉。
- 1.2 新增 `run_stable_weight_selection.py`：读冻结输入 → 三 seed × 两规则 × 两求解器 → 预算计数 →
  保存每级权重/目标/残差/日志、证书、诊断、comparison.csv、diagnostics.csv，写 `run_manifest.json`。
- 1.3 新增 `tests/test_stable_weight_selection.py`：小规模手算核对（含 L1/L∞ 层级、打钉顺序、边界饱和判定、
  预算计数、非 Optimal 即停、E/D 门槛判定函数）。
- 1.4 不修改任何旧源码、旧冻结文件、旧数据与旧结果；需要复用的一律以只读方式导入。

## 组2 运行

- 2.1 组1 测试通过后执行 `run_stable_weight_selection.py --run-id U11R15-v01`。
- 2.2 逐级保存；任何非 Optimal 立即停止并写 `failure.json`（invalid），不重试、不换求解器补考、不放宽容差。
- 2.3 运行后核对预算计数 = 459 LP、调度调用 = 0，源码哈希无漂移。

## 组3 独立审计

- 3.1 新增 `scripts/audit_stable_weight_selection.py`：另进程、仅标准库 + `Fraction`，
  **不导入** `src/stable_weight_selection.py`、`run_stable_weight_selection.py` 或本单元判定函数。
- 3.2 审计内容：从原始 CSV 重算四通道系数与目标；重算每级目标值与打钉区间并核对保存权重；
  独立重算首级有理弱对偶上下界与分类；独立实现年度加权聚合得到 E/D/成本/缺供并核对 CSV；
  509 个保存源日（365 全年 + 144 代表日）物理与成本重建；全量哈希与预算核对。
- 3.3 审计自身禁止 `subprocess`、`pulp.LpProblem.solve`、`scipy.optimize`（沿用 U11R14 的守卫），
  零求解调用；审计报告写入 `results/annual/U11R15-v01-independent-audit.json`。

## 组4 判定与登记

- 4.1 按 `decision-rule.md` 判 H1（主）与 H2（次），写 `findings.md`（含失败与限制，不删任何证据）。
- 4.2 追加 `instructions/RUNLOG.md`；更新 `instructions/sequence_status_v02.md`、`STATUS.md`、
  `specs/roadmap.md`（单元表 + Backlog）。
- 4.3 提交并推送：提交前检查 `git diff`、无敏感信息、冻结证据与索引字节；推送后核对远端 master 与本地 HEAD 一致、
  工作区干净。**不得** force push、`reset --hard` 或清理旧失败。
- 4.4 完成后停止，等用户下一步指令。
