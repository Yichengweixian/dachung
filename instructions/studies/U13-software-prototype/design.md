# U13 设计：Streamlit 软件原型

## 功能模块（申报书研究内容 6 映射）

| 模块 | 页面/组件 | 复用 |
|---|---|---|
| 数据导入 | 上传 CSV 或选择内置算例（input_24h / input_168h / 8760） | `src/data_loader.py` |
| 参数设置 | 侧栏表单：火电上下限/爬坡、储能 E/P/SOC/效率、成本系数 | `config/*.json` 读写 |
| 平衡计算 | 一键运行 LP（U06），显示求解状态与关键指标 | `src/optimization_model.py` |
| 储能寻优 | 网格搜索（U09），显示 (E\*,P\*) 与热力图 | `src/grid_search.py` |
| 方案对比 | 多场景指标表与对比图 | `results/*/summary.csv` 聚合 |
| 图表展示 | 调度曲线、SOC、平衡图（matplotlib 内嵌） | `src/plot_*.py` |
| 报告导出 | 汇总表导出 CSV、图导出 PNG | 纯 I/O |

## 技术要求

- 依赖新增 `streamlit`（记录版本入 requirements.txt）；运行方式 `.\.venv\Scripts\python.exe -m streamlit run web/app.py`
- 目录：`web/app.py`（页面）——逻辑全部在 `src/`，web 层只做输入采集与结果展示
- 中文界面；异常输入必须给出提示而不是崩溃（try/except 包裹模型调用，显示错误信息）
- 演示一致性验收：内置算例 + 默认参数运行后，各指标与 `results/capacity_sensitivity/summary.csv`（E40_P20 行）等既有结果逐值一致（容差 1e-6）

## 输出

- `web/app.py`（或拆分页面）、`docs/software_manual.md`（使用说明，软著材料用）
- 演示截图（用户手动操作后保存，代码不伪造截图）
