# 总路线图

## 单元一览

| 单元 | 内容 | 模式 | 状态 | 依赖 | 交付物 |
|---|---|---|---|---|---|
| U00 | 版本基线与产物清单冻结 | exploratory | not_started | — | git 仓库、清单、环境记录 |
| U01 | 阶段2 24h 构造数据 | — | 基线登记 | — | 证据见 findings |
| U02 | 阶段3 无储能规则平衡 | — | 基线登记 | — | 证据见 findings |
| U03 | 阶段4 固定储能规则调度 | — | 基线登记 | — | 证据见 findings |
| U04 | 阶段5 容量敏感性 | — | 基线登记 | — | 证据见 findings |
| U05 | 阶段6 经济性评价 | — | 基线登记 | — | 证据见 findings |
| U06 | LP 时序优化模型（PuLP+CBC） | exploratory | not_started | U00, U05 | `src/optimization_model.py`、`run_optimization.py` |
| U07 | 优化模型独立验证与规则对照 | exploratory | not_started | U06 | tests、验证报告 |
| U08 | 渗透率场景矩阵（4×3=12 场景） | exploratory | not_started | U07 | 矩阵 CSV、对比图、分析文档 |
| U09 | 储能容量-功率网格搜索 (E×P) | exploratory | not_started | U07 | 热力图、最优方案、(E\*,P\*) |
| U10 | 真实气象数据管线（NASA POWER→168h） | exploratory | not_started | U00 | 原始数据、转换脚本、168h 输入 |
| U11 | 8760h 仿真与 k-means 典型日聚类 | exploratory | not_started | U10, U09 | 聚类结果、年度仿真、误差对照 |
| U12 | 遗传算法/粒子群增强 | exploratory | not_started | U09 | GA 实现与网格对照表 |
| U13 | 决策软件原型（Streamlit） | exploratory | not_started | U09 | 可运行原型 |
| U14 | 成果凝练（报告/PPT/论文/专利） | — | not_started | 全部前序 | 各材料初稿 |

## 最小汇报路径

U00 → U06 → U07 → U08。完成后即可支撑一次有"优化模型 + 渗透率矩阵"的阶段汇报。

## 完整路径

继续 U09 → U10 → U11 → U12 → U13 → U14。U09 是本项目核心创新点；U10/U11 把结论从构造数据搬到真实数据与全年尺度。

## Backlog（意外发现与暂缓项，进入前先在本表登记）

- 火电启停二元变量（MILP 机组组合）
- 备用容量约束
- 需求响应建模
- 峰谷电价与储能套利收益（需真实电价数据）
- 碳减排价值、容量支撑价值
- 可靠性指标 LOLP/LOLE/EENS（需蒙特卡洛或多场景）
- 多目标优化（成本 vs 消纳率 Pareto 前沿）
- 园区综合能源、新能源基地外送专项场景
- 季节性长时储能与周级电量平衡
