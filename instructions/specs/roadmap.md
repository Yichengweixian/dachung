# 总路线图

## 单元一览

| 单元 | 内容 | 模式 | 状态 | 依赖 | 交付物 |
|---|---|---|---|---|---|
| U00 | 版本基线与产物清单冻结 | exploratory | partial（T1清单/环境/47项测试补证；补证时未提交，后续发布不追溯改判） | — | results/baseline/U00-T1-v02/；最终快照v03 |
| U01 | 阶段2 24h 构造数据 | — | 基线登记 | — | 证据见 findings |
| U02 | 阶段3 无储能规则平衡 | — | 基线登记 | — | 证据见 findings |
| U03 | 阶段4 固定储能规则调度 | — | 基线登记 | — | 证据见 findings |
| U04 | 阶段5 容量敏感性 | — | 基线登记 | — | 证据见 findings |
| U05 | 阶段6 经济性评价 | — | 基线登记 | — | 证据见 findings |
| U06 | LP 时序优化模型（PuLP+CBC） | exploratory | blocked / invalid（历史保留） | U00, U05 | U06-master-v01 同时充放电验收失败 |
| U06R01 | 充放电互斥修订（MILP） | exploratory | complete / supported | U06 | results/optimization/U06R01-v03/ |
| U07 | 优化模型独立验证与规则对照 | exploratory | 由 U07R01 覆盖 | U06R01 | — |
| U07R01 | 全因子归因与独立进程审计 | exploratory | complete / supported | U06R01 | results/validation/U07R01-v01/ |
| U08 | 渗透率场景矩阵（4×3=12 场景） | exploratory | complete / supported | U07R01 | results/penetration/U08-master-v01/ |
| U09 | 储能容量-功率网格搜索 (E×P) | exploratory | 由 U09R01 覆盖 | U07R01 | — |
| U09R01 | 101 候选网格、反序与高投资稳健性 | exploratory | complete / supported | U07R01 | results/grid_search/U09R01-v01/ |
| U10 | 真实气象数据管线（NASA POWER→168h） | exploratory | complete / supported | U00 | results/real_data/U10-master-v01/ |
| U11 | 8760h 仿真与 k-means 典型日聚类 | exploratory | 由 U11R02 覆盖 | U10, U09R01 | — |
| U11R01 | 年度光伏转换输出上限修订 | exploratory | 规格草案（未实施） | 实际U11转换基线、原始年度数据及U10历史证据 | — |
| U11R02 | 全年逐日仿真与典型日对照 | exploratory | complete / inconclusive | U11R01、U10 | results/annual/U11R02-v01/ |
| U11R03 | 幅值保留与真实代表日 | exploratory | complete / inconclusive | U11R02 | results/annual/U11R03-v01/ |
| U12 | 遗传算法/粒子群增强 | exploratory | 由 U12R01 覆盖 | U09R01 | — |
| U12R01 | 三种子 GA 与网格对照 | exploratory | complete / inconclusive | U09R01 | results/ga/U12R01-v01/ |
| U12R02 | 固定89次预算GA及10种子验证 | exploratory | complete / supported | U09R01、U12R01 | results/ga/U12R02-v02/ |
| U13 | 决策软件原型（Streamlit） | exploratory | 由 U13R01 覆盖 | U09R01 | — |
| U13R01 | 原型一致性、真实浏览器与独立审计 | exploratory | complete / supported（人工验收已确认） | U06R01、U09R01 | results/prototype/U13R01-v01/ 等 |
| U14 | 成果凝练（报告/PPT/论文/专利） | — | complete（材料单元不设 verdict） | 全部前序 | docs/ 六份材料 + 数字核对表 |

## 最小汇报路径

U00 → U06 → U07 → U08。完成后即可支撑一次有"优化模型 + 渗透率矩阵"的阶段汇报。

## 完整路径

继续 U09 → U10 → U11 → U12 → U13 → U14。U09 是本项目核心创新点；U10/U11 把结论从构造数据搬到真实数据与全年尺度。

## Backlog（意外发现与暂缓项，进入前先在本表登记）

- 2026-09-23 T4材料同步完成：最新入口docs/revisions/U14-T4-v01/README.md，86行出处、check04核对通过及56项测试；原docs材料不覆盖。外部换人抽查10个数字、正式PPT排版、文献与claims登记仍待办。U11R03误差不能单独归因于无跨日耦合，全年基准采用相同假设；后续电量权重/极端日改进需新单元。U12R02仅验证固定预算，跨数据稳健性、墙钟计时及UI集成需另行安排。

- 2026-09-23 U12R02完成：10/10主种子均89次且质量达标，独立重复轨迹差0，总979次；supported仅限固定构造算例。v01路径错误在求解前失败，v02修正后完整运行。下一阶段T4将U11R03/U12R02结果同步到六份材料及数字出处；旧研究判定不改。

- 2026-09-22 U11R03完成：252次Optimal、51项测试及另进程产物复核通过；全部9组风电输入电量误差超过2%，结论inconclusive。比例改善不代表电量、成本或缺供保真。电量守恒权重或极端日研究需另立单元；本轮不追加实验。用户要求阶段完成即提交和推送，已登记为持续发布偏好。下方2026-09-17草案状态是历史记录。

- 2026-09-17 T2草案待确认：U11R03采用固定MW尺度特征、中心最近真实日、N=12/24/48，拟要求同一N在42/7/2026均满足1个百分点与2%年度输入电量偏差。U12R02采用12个体/7代、89次目标调用、10固定种子，拟至少9个达到不劣于网格0.5%的质量。两套均未冻结、未实现、未运行；确认后一次推进一个单元。旧不确定结果不追溯改判。

- 2026-09-17 U00/T1：非提交补证已完成v02检查，最终台账快照v03结果见manifest。原U00正式完成仍需明确工作区提交授权、444.docx入库确认、清单自引用与输出路径口径。未改旧判据以宣称supported。

- 2026-09-16新增进度见../sequence_status_v02.md：U06R01/U07R01/U08/U09R01/U10完成，原始冲突通过新单元解决，旧记录保留。
- U14材料单元已完成：材料内数字用【ID】标签指向 docs/number_sources.csv，由 scripts/check_materials_numbers.py 回溯到 CSV/JSON/findings 并生成核对表；PPT仅交付md大纲，pptx排版、claims登记、以及decision-rule C的换人抽查仍待办。
- U13R01原型验收：自动化、真实浏览器（Chrome CDP）检查和独立审计通过，用户随后已完成人工操作确认，当前verdict=supported。原型网格寻优仅24h、年度用独立日近似、无跨日耦合，均已在界面与冻结边界中注明；年度/长时段寻优与连续容量寻优需另立单元。
- U11R02已取得完整2023年NASA输入，425次Optimal；典型日最好误差6.434640个百分点，未通过1个百分点标准。更大N、幅值特征或k-medoids比较待新单元预注册，不回改当前冻结规则。年数据光伏150MW封顶触发0小时。

- 2026-09-15 master U06：连续 LP 正式算例 Optimal 但 11 个时段同时充放电，违反 plan 组2第5项。
  原判据和失败记录保留；互斥方案必须以新修订单元定稿/冻结，不改变本次参数或门槛。
- U09 草案冲突：按现有档位和唯一 (0,0) 特例共 101 组合，design/plan/decision-rule 却写 111；
  supported 的 P<=50 与 inconclusive 的 P=50 重叠，“严格内部”也与允许 P=5 冲突。
  首次运行前须明确这些规则，不能添加虚构候选或运行后修订判据。
- U11：本分支没有年度原始气象、8760h 输入或转换/聚类代码；U11R01 引用的是另一工作副本的待核实证据。
  design 的权重定义为天数/365（和为1），plan 却检查和为365，必须区分比例权重与天数权重。
- U13：原型要求调用 U06 LP，却以 U04 规则调度 E40_P20 为逐值一致性基准；两者火电最小出力、爬坡、
  期末SOC条件不同，不能只凭 E/P 相同认定同模型。原型首次验收前应分别指定规则模式与优化模式的基准。

- 已建立U11R01规格草案：处理“线性光伏估算超过150 MW”导致年度转换停止的问题。该反馈来自尚未提交进度的另一工作副本；原始数据质量和超限次数须在该副本独立核对，不预填“2小时”。保留旧U11规则/失败记录，只修订转换并发布年度输入，后续全年研究需另行指令与新输入冻结记录。本表未据此改写U10/U11的历史状态。

- 火电启停二元变量（MILP 机组组合）
- 备用容量约束
- 需求响应建模
- 峰谷电价与储能套利收益（需真实电价数据）
- 碳减排价值、容量支撑价值
- 可靠性指标 LOLP/LOLE/EENS（需蒙特卡洛或多场景）
- 多目标优化（成本 vs 消纳率 Pareto 前沿）
- 园区综合能源、新能源基地外送专项场景
- 季节性长时储能与周级电量平衡
