# 总路线图

## 单元一览

| 单元 | 内容 | 模式 | 状态 | 依赖 | 交付物 |
|---|---|---|---|---|---|
| U00 | 版本基线与产物清单冻结 | exploratory | complete / supported（当前环境） | — | git 仓库、清单、环境记录 |
| U01 | 阶段2 24h 构造数据 | — | 基线登记 | — | 证据见 findings |
| U02 | 阶段3 无储能规则平衡 | — | 基线登记 | — | 证据见 findings |
| U03 | 阶段4 固定储能规则调度 | — | 基线登记 | — | 证据见 findings |
| U04 | 阶段5 容量敏感性 | — | 基线登记 | — | 证据见 findings |
| U05 | 阶段6 经济性评价 | — | 基线登记 | — | 证据见 findings |
| U06 | MILP 时序优化模型（PuLP+CBC，用户批准互斥） | exploratory | complete / supported（02；01失败保留） | U00, U05 | 模型、独立校验、7场景、精度回归及运行记录 |
| U07 | 优化模型独立验证与规则对照 | exploratory | complete / invalid（数值supported，归因设计invalid） | U06 | 独立数值验证通过；原归因设计无效 |
| U07R | 全组合与Shapley归因修订 | exploratory | complete / supported | U06,U07 | 8组合、顺序范围、归因报告 |
| U08 | 渗透率场景矩阵（4×3=12 场景） | exploratory | complete / supported | U07数值审计,U07R | 12场景、边际表、3图、分析文档 |
| U09 | 储能容量-功率网格搜索 (E×P) | exploratory | complete / supported | U06,U07数值审计,U07R | 101组合、热力图、样本最低点70 MWh/25 MW |
| U10 | 真实气象数据管线（NASA POWER→168h） | exploratory | complete / supported | U00 | `U10-20260914T125454Z`；原始响应、转换脚本、168h 输入、质量报告、manifest |
| U11 | 8760h 仿真与 k-means 典型日聚类 | exploratory | not_started | U10, U09 | 聚类结果、年度仿真、误差对照 |
| U12 | 遗传算法/粒子群增强 | exploratory | not_started | U09 | GA 实现与网格对照表 |
| U13 | 决策软件原型（Streamlit） | exploratory | not_started | U09 | 可运行原型 |
| U14 | 成果凝练（报告/PPT/论文/专利） | — | not_started | 全部前序 | 各材料初稿 |

## U10 已完成证据

运行 `U10-20260914T125454Z` 通过冻结参数、HTTP 200、168 条连续 UTC 时间戳、零缺失/重复/物理范围违规、单位转换和离线重放哈希核验。原始响应为 `data/raw/U10-20260914T125454Z/nasa_power_hourly_wuhan_20200101_20200107_utc.json`，SHA-256 `66eb140842a767efd840c03f958ab66285049735f3f18f4d8c1a2a19d6b6956d`；转换输入为 `data/processed/U10-20260914T125454Z_input_168h_wuhan_20200101T0000Z_20200107T2300Z.csv`（规范副本 `data/processed/input_168h.csv`），SHA-256 `cea7505e933f2b68775a8a5fd05e473af0d5d28ba23904f33cc813d686bac07f`。质量报告与运行清单位于 `data/processed/U10-20260914T125454Z_quality_report.json` 和 `data/processed/U10-20260914T125454Z_run_manifest.json`。此 supported 只表示数据管线满足输入契约。

## 最小汇报路径

U00 → U06 → U07/U07R → U08 → U09。已可支撑一次有“优化模型 + 渗透率矩阵 + 容量功率网格寻优”的阶段汇报。

## 完整路径

继续 U10 → U11 → U12 → U13 → U14。U09 已建立核心网格寻优基准；U10/U11 把结论从构造数据搬到真实数据与全年尺度。

## Backlog（意外发现与暂缓项，进入前先在本表登记）

- U07事后复核：83.33%仅为错误拼合估算的算术偏差；原公式漏计储能、白天和跨时段交互，归因设计invalid。U07R仅作另行冻结的模型内会计分配。

- U06已解决：CBC文本舍入导致5e-6残差；改读同次求解二进制双精度解，最大残差7.37e-12。原失败保留，门槛不变。

- U00：Windows .venv与双shell兼容性待用户本机验证；本轮仅验证Linux。
- U00：历史manifest输入哈希与当前输入字节不一致，已保留原记录和重跑补丁；不要将历史哈希视为当前输入校验成功。图片因环境重渲染有变化，未作像素等价声明；经济表末位浮点差异保留。

- 火电启停二元变量（MILP 机组组合）
- 备用容量约束
- 需求响应建模
- 峰谷电价与储能套利收益（需真实电价数据）
- 碳减排价值、容量支撑价值
- 可靠性指标 LOLP/LOLE/EENS（需蒙特卡洛或多场景）
- 多目标优化（成本 vs 消纳率 Pareto 前沿）
- 园区综合能源、新能源基地外送专项场景
- 季节性长时储能与周级电量平衡
