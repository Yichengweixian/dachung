# U13 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录判据哈希；确认 U09 已有可调用的网格搜索函数
- [ ] 0.2 冻结：功能模块清单（七项）、演示算例（input_24h + 40/20）、一致性基准（E40_P20 行）

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U13：决策软件原型。先读 `instructions/studies/U13-software-prototype/design.md`、`specs/question.md` 与 U06—U09 的 findings.md，然后：
>
> 1. 安装 streamlit（`.\.venv\Scripts\python.exe -m pip install streamlit`，记录版本入 requirements.txt）。
> 2. 新建 `web/app.py`，实现七模块（数据导入、参数设置、平衡计算、储能寻优、方案对比、图表展示、报告导出）。所有计算逻辑必须 import `src/` 现有模块（optimization_model、grid_search、economic_model、plot_*），禁止在 web 层复制调度或成本逻辑。
> 3. 参数表单默认值读取现有 `config/*.json`；异常输入用 try/except 显示提示，不崩溃。
> 4. 写 `docs/software_manual.md`（功能说明、运行方式、软著材料用途）。全部文件 `encoding="utf-8"`。
> 5. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) web 层无复制逻辑（列出 import 清单）；2) 内置算例 + 默认参数的结果与 `results/capacity_sensitivity/summary.csv` 的 E40_P20 行逐值一致（容差 1e-6）；3) 七模块逐一可用（按 software_manual 操作路径核对）；4) 异常输入（负数容量、空 CSV）有提示不崩溃。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
