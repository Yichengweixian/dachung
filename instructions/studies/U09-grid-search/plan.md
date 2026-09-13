# U09 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录输入 SHA-256、U06/U07 输出哈希、economics.json 快照、判据哈希
- [ ] 0.2 确认 U07 verdict 为 supported；确认评价函数与 U05 一致（同一函数对象）
- [ ] 0.3 冻结网格定义（E/P 档位、组合规则）与判据

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U09：储能容量-功率网格搜索。先读 `instructions/studies/U09-grid-search/design.md`、U06/U07 findings 与 `docs/economics_analysis.md`，然后：
>
> 1. 新建 `src/grid_search.py`：生成 111 个 (E,P) 组合，逐组合调用 `src/optimization_model.py` 求解 + `src/economic_model.py` 评价（复用函数，禁止复制逻辑），记录每个组合的求解状态。
> 2. 新建 `run_grid_search.py` 入口：运行全部组合；任一组合非 Optimal 必须记录并停止后续统计（先报告，不静默跳过）；写 `results/grid_search/` 全部输出（summary、best_dispatch、run_manifest）。
> 3. 绘制三张图（热力图×2 + 最优组合运行曲线），中文字体沿用 `src/plot_results.py` 的处理方式。
> 4. 写 `docs/grid_search_analysis.md`：最优 (E\*,P\*) 与目标值、是否在网格内部、相邻网格边际变化、最优组合的消纳率与利用率、明确声明"结果只在 24h 构造数据与示例参数下成立，不构成真实项目结论"。
> 5. 完成后停止，等待下一步指令。不要使用遗传算法。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) 组合总数 111 且无重复；2) 全部组合求解状态清单（Optimal 数量）；3) 最优组合的约束检查与独立检查通过；4) 热力图数据与 summary.csv 一致；5) 分析文档没有把样本内最优写成全局最优或经济结论。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
