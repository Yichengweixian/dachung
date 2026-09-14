# U11 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录判据哈希；确认 U10 管线可扩展全年（下载脚本重跑全年）
- [ ] 0.2 冻结：聚类特征定义、N 候选 {8,10,12}、种子 42、储能配置 40/20、口径"逐日独立 LP"
- [ ] 0.3 确认年度数据完整性（8760 行、无缺失）

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U11：8760 小时全年仿真与 k-means 典型日聚类。先读 `instructions/studies/U11-annual-clustering/design.md` 与 U10 的 findings.md，然后：
>
> 1. 用 U10 管线生成全年输入 `data/processed/input_8760h.csv`（原始数据存档，转换复用 `src/convert_weather.py`）。
> 2. 新建 `src/annual_simulation.py`：逐日独立 LP（复用 `src/optimization_model.py`，每日初 SOC=0.5 日末归位），输出 365 日逐日汇总与年度合计。
> 3. 新建 `src/typical_day_clustering.py`：按 design.md 特征做 k-means（N=8/10/12、k-means++、random_state=42），输出簇中心、权重、肘部/Silhouette 曲线。
> 4. 新建 `run_annual.py`：全仿真 + 三种 N 的聚类加权仿真，输出误差对照表与全部图，写 `docs/annual_clustering_analysis.md`（含"日间 SOC 不跨天"近似说明）。
> 5. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) 全年输入 8760 行通过校验；2) 365 个日 LP 全部 Optimal；3) 聚类可复现（同种子两次运行簇分配一致）；4) 权重之和=365；5) 误差对照表由年度合计电量计算比例后取差。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
