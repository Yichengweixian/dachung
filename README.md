# 高比例新能源电力电量平衡研究

## master 当前执行状态（2026-09-23）

2026-09-26最新：U11R06 仅将权重 LP 改为 CBC `presolve off` 后尝试完整 9 组矩阵，但第 44 次权重 LP 在 N24/seed42 阶段 Infeasible，按冻结规则停止并保留证据；43 次 LP 与 12 次调度 Optimal，独立部分审计通过，研究判定 blocked/invalid。U11R04 invalid 与 U11R05 单模型 supported 均保持历史结论，研究仍未完成、不制作 PPT。详见[U11R06 结果](instructions/studies/U11R06-presolve-off-weight-matrix/findings.md)。

2026-09-24最新：U11R05单模型诊断complete/supported，关闭presolve后两次Optimal且重复差0，独立审计通过。此结论仅限一个重建模型，U11R04历史invalid不变，完整代表日矩阵仍待新的修订验证。详见[U11R05结果](instructions/studies/U11R05-cbc-presolve-diagnostic/findings.md)。

2026-09-24研究更新：U11R04已完成前置隔离审计并实际运行，但权重LP在N48/seed42阶段Infeasible，按冻结规则立即停止，判定invalid。101次权重LP和36次调度的证据全部保留，62项测试通过不代表研究通过。详见[instructions/studies/U11R04-energy-calibrated-weights/findings.md](instructions/studies/U11R04-energy-calibrated-weights/findings.md)。项目尚未完成，当前不制作PPT。

T4 最新六份成果材料见[修订版入口](docs/revisions/U14-T4-v01/README.md)：已同步 U11R03/U12R02，86 行数字出处核对通过，56 项测试通过。原材料保留；换人数字抽查及正式排版仍待办。

新顺序实现直接在master完成，不合并u10-complete。U06R01互斥MILP、U07R01独立审计、U08渗透矩阵、U09R01网格、U10气象管线和U13R01原型已通过各自冻结判据，U14材料整理已完成。
U11R02年度典型日和U12R01遗传算法对照均已完成，但未达到各自冻结判据，结论保持inconclusive。U11R03已完成252次真实代表日求解：比例近似改善，但风电输入电量误差仍超过2%，结论inconclusive。U12R02固定小预算GA完成，10个种子每次89次评估全部质量达标，独立重复一致，结论supported；此结论限于固定构造算例，全部研究含复现共979次评估。详细进度见[instructions/sequence_status_v02.md](instructions/sequence_status_v02.md)。
新增方法、限制和验证见[模型验证报告v02](docs/model_validation_report_v02.md)、[气象方法v02](docs/real_weather_data_method_v02.md)。
原始LP失败和旧版说明全部保留。所有结果是探索性构造算例或气象估计，不是真实电网实测验证。

## master 首次执行记录（2026-09-15，历史）

以提交 `003a014` 的 instructions 为准完成 U06 连续 LP 的实现与首次验收。
原有 25 项测试及新增 7 项测试通过；正式 24 h 算例 CBC 状态为 Optimal，
但 11 个时段同时充放电，不满足 U06/plan.md 组2第5项。工程状态为 blocked，
本次验收 invalid；不能把求解成功当作研究结论通过。

详见 [master 指令执行核验 v01](docs/master_instruction_validation_v01.md)、
[U06 结果记录](instructions/studies/U06-optimization-model/findings.md) 和
`results/optimization/U06-master-v01/`。U09、U11、U13 尚未执行，具体前置缺项见核验文档。
以下第1—6阶段文字是保留的规则模型历史说明；U06 依赖另含 `pulp==3.3.0`。

本地 `.venv` 已建立，使用本机已有数值库并安装 PuLP。复查命令：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe run_optimization.py
```

第二条命令为每次运行生成新目录；在当前冻结规格下预期验收失败并返回非零。
旧运行不会覆盖。后续需要另建修订单元明确充放电互斥方法，不能修改旧冻结判据或调低门槛。

## 第1—6阶段历史说明

本项目以简化区域电力系统为对象，研究火电、风电、光伏、储能和负荷之间的时序平衡关系。后续拟研究基于多时间尺度电力电量平衡的储能容量与功率协同优化配置方法。

当前已完成项目框架、24小时构造数据、无储能规则平衡、固定储能规则调度、容量敏感性分析，以及第6阶段简单经济性评价。main.py只检查框架，各阶段使用独立入口。尚未开展储能容量优化。444.docx是用户指定的最终申请书，保留原样。

## 第6阶段 系统经济性评价

在VSCode中选择.venv解释器，运行run_economics.py；F5可选择“第6阶段 系统经济性评价”。也可在项目目录终端运行：

```powershell
.\.venv\Scripts\python.exe run_economics.py
```

成本参数集中在config/economics.json，明确标为人为设置的测试假设，后续可替换为文献数据。综合成本为火电成本、储能成本、弃电成本和失负荷成本之和。储能成本包含按寿命及折现率年化后分摊到24小时的投资，以及固定和按放电量计的运维费用。

程序使用既有data/input_24h.csv重新运行0、20、40、60、80 MWh五组场景，功率规则与第5阶段一致。结果保存到results/economics/summary.csv，电量汇总、五份逐时结果及运行记录也保存在该目录；成本曲线为figures/economics/capacity_vs_total_cost.png。重复运行更新本阶段输出。

代码与分析分开，参数表、公式、字段说明、结果和经济权衡见docs/economics_analysis.md。本次80 MWh是给定五组中的最低成本场景，24小时综合成本约363810.54元；曲线尚未出现先降后升，且初始库存净减少影响成本比较，不能据此认定经济最优容量。

运行时验证物理约束、分项成本、投资分摊与CSV读回后的结果。当前共25项测试，可在项目目录运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## 第5阶段 储能容量敏感性分析

在VSCode中选择.venv解释器，打开run_capacity_sensitivity.py直接运行；F5可选择“第5阶段 储能容量敏感性分析”。也可在项目目录终端运行：

```powershell
.\.venv\Scripts\python.exe run_capacity_sensitivity.py
```

程序读取既有data/input_24h.csv，独立计算0、20、40、60、80 MWh五个场景。非零容量场景均配20 MW功率，0 MWh场景配0 MW。容量列表与固定功率位于config/capacity_sensitivity.json，其他参数继续读取storage.json、simulation.json和no_storage.json。每组都从初始SOC 50%重新开始，不继承上一场景的期末电量。

结果位于results/capacity_sensitivity/：summary.csv包含所要求的八项指标，五份E*_P*_hourly.csv保留逐时结果；marginal_changes.csv记录相邻容量的实际增益；run_manifest.json记录参数、输入文件校验值和运行环境。四张图位于figures/capacity_sensitivity/。重复运行更新本阶段输出。

代码与文字分析分开：docs/capacity_sensitivity_analysis.md解释指标、结果、初始电量影响和边际收益。本次0至80 MWh区间每增加20 MWh均减少约16.84 MWh弃电，尚未出现边际收益递减，分析文档如实区分仿真结果与容量继续扩大后的限制。储能利用率沿用充放电活跃时长占比；0 MWh场景该指标在CSV中留空，表示不适用。

运行时检查各场景的功率平衡、SOC、能量守恒及保存后的CSV。运行所有测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## 第4阶段 储能规则调度

在VSCode中选择.venv解释器，运行run_storage.py；F5可选择“第4阶段 储能规则调度与对比”。在项目目录终端运行：

```powershell
.\.venv\Scripts\python.exe run_storage.py
```

配置见config/storage.json：40 MWh、20 MW、SOC初值50%、范围10%至90%，充放电效率均为0.95。风光富余时充电，风光不足时储能先放电、再由火电补缺，不做优化。无储能基准由同一输入及火电参数重新计算。

输出results/storage_hourly.csv、storage_summary.csv、storage_baseline_hourly.csv、storage_comparison.csv及figures/storage_comparison.png。输入和第3阶段输出保持不变。

soc列为时段结束状态，0至1比例。储能利用率定义为充放电活跃时长占比；充放电量在电网侧计量。当前期末SOC为10%，未强制归位，初始库存下降对对比结果的影响见docs/storage_model.md。

## 第3阶段 无储能平衡

在VSCode中选择.venv解释器，打开run_no_storage.py直接运行；F5也可选择“第3阶段 无储能平衡”。或在项目目录终端运行：

```powershell
.\.venv\Scripts\python.exe run_no_storage.py
```

程序读取data/input_24h.csv，按新能源优先、火电补缺的规则逐时计算。火电上限位于config/no_storage.json，当前为120 MW；小时数及步长读取config/simulation.json。

输出results/no_storage_hourly.csv（逐时功率、弃电和失负荷电量）、results/no_storage_summary.csv（全天电量与比例）、figures/no_storage_balance.png（电力平衡图）。输入CSV不被修改。具体公式、列名单位、适用边界及测试命令见docs/no_storage_model.md。

## 第2阶段直接运行

本机已在.venv中准备好运行环境。在VSCode中打开本项目目录，选择.venv对应的Python解释器，打开run_data_24h.py并点击“Run Python File”。也可在项目目录的终端运行：

```powershell
.\.venv\Scripts\python.exe run_data_24h.py
```

输出data/input_24h.csv及figures/input_24h_profiles.png，图片包含负荷、风电、光伏和风光总出力四条曲线。运行后直接打开PNG查看，不弹出图形窗口。CSV包含hour、load、wind、solar，小时为0至23，功率单位MW。重复运行会重新生成这两个文件。

参数集中在config/data_24h.json；构造方法、字段与适用边界见docs/data_description.md。此24小时入口独立于simulation.json，修改后者不会改变本阶段数据长度。

## 目录与每个文件的作用

```text
大创第一阶段/
├── 444.docx                     最终申请书，已有文件
├── README.md                    项目说明、文件用途与运行步骤
├── requirements.txt             Python第三方依赖
├── main.py                      统一运行入口，当前仅检查框架
├── run_data_24h.py               第2阶段入口，生成数据并绘图
├── run_no_storage.py             第3阶段入口，无储能平衡与结果输出
├── run_storage.py                第4阶段入口，储能规则调度与对比
├── run_capacity_sensitivity.py   第5阶段入口，批量仿真、汇总与四张图
├── run_economics.py              第6阶段入口，重新调度、成本评价与绘图
├── .gitignore                   排除虚拟环境、缓存等临时文件
├── .vscode/
│   └── launch.json              VSCode运行及调试入口
├── config/
│   ├── simulation.json          时间步数与时间步长
│   ├── data_24h.json             24小时曲线参数、装机与随机种子
│   ├── no_storage.json           火电最大出力
│   ├── storage.json              储能功率、容量、SOC与效率
│   ├── capacity_sensitivity.json  第5、6阶段容量列表与固定功率
│   └── economics.json            示例成本参数、单位与来源说明
├── data/
│   ├── input_24h.csv             第2阶段24小时基础输入数据
│   ├── raw/                     后续存放原始数据，保留来源
│   ├── processed/               后续存放清洗或构造后的模型输入
│   └── scenarios/               后续存放场景参数与配置表
├── src/
│   ├── __init__.py              将src标记为Python模块包
│   ├── paths.py                 统一定位项目与各数据目录
│   ├── data_loader.py           CSV读取及数据校验
│   ├── generate_data.py         构造并检查24小时数据
│   ├── balance_model.py         无储能逐时规则平衡
│   ├── metrics.py               电量汇总与新能源消纳比例
│   ├── validation.py            调度结果守恒与规则检查
│   ├── plot_results.py          输入曲线与无储能电力平衡图
│   ├── storage_model.py         储能参数与逐时调度规则
│   ├── storage_metrics.py       储能统计与无储能对比
│   ├── storage_validation.py    储能边界和能量守恒检查
│   ├── plot_storage.py          储能运行与对比图
│   ├── capacity_sensitivity.py  独立运行容量场景并计算边际变化
│   ├── plot_capacity_sensitivity.py  容量曲线与八项指标柱状图
│   ├── economic_model.py        参数校验、成本计算及费用核对
│   └── plot_economics.py        储能容量与综合成本曲线
├── results/
│   ├── no_storage_hourly.csv     无储能逐时计算结果
│   ├── no_storage_summary.csv    无储能全天汇总
│   ├── storage_hourly.csv        储能逐时结果
│   ├── storage_summary.csv       储能指标与参数汇总
│   ├── storage_baseline_hourly.csv  本次对比的无储能逐时结果
│   ├── storage_comparison.csv    无储能与储能指标对比
│   ├── capacity_sensitivity/
│   │   ├── summary.csv           五个容量场景的指标汇总
│   │   ├── E0_P0_hourly.csv      无储能逐时结果
│   │   ├── E20_P20_hourly.csv    20 MWh / 20 MW逐时结果
│   │   ├── E40_P20_hourly.csv    40 MWh / 20 MW逐时结果
│   │   ├── E60_P20_hourly.csv    60 MWh / 20 MW逐时结果
│   │   ├── E80_P20_hourly.csv    80 MWh / 20 MW逐时结果
│   │   ├── marginal_changes.csv 相邻容量的指标变化及单位容量增益
│   │   └── run_manifest.json    本次参数、输入校验值与依赖版本
│   └── economics/
│       ├── summary.csv           五组分项成本、总成本及消纳指标
│       ├── dispatch_summary.csv  本次重新计算的电量与储能指标
│       ├── E*_P*_hourly.csv      五份逐时结果，命名规则同第5阶段
│       └── run_manifest.json    成本参数、输入校验值与核对记录
├── figures/
│   ├── input_24h_profiles.png    四条风光荷输入曲线
│   ├── no_storage_balance.png   无储能电力平衡图
│   ├── storage_comparison.png   储能对比、充放电和SOC图
│   ├── capacity_sensitivity/
│   │   ├── fig1_renewable_utilization.png  容量与新能源消纳率
│   │   ├── fig2_curtailment_rate.png       容量与弃风弃光率
│   │   ├── fig3_thermal_generation.png     容量与火电发电量
│   │   └── fig4_comprehensive_bars.png     八项指标分面柱状图
│   └── economics/
│       └── capacity_vs_total_cost.png     容量与24小时综合成本
├── docs/
│   ├── metric_definitions.md    时序字段、指标含义与单位约定
│   ├── progress_checklist.md    分阶段工作清单及当前状态
│   ├── data_description.md      构造数据来源、方法与单位说明
│   ├── no_storage_model.md      无储能模型规则、单位与验证记录
│   ├── storage_model.md         储能规则、指标口径与初末电量说明
│   ├── capacity_sensitivity_analysis.md  第5阶段独立分析文档
│   └── economics_analysis.md    第6阶段参数、公式与独立分析文档
└── tests/
    ├── test_no_storage.py       无储能边界与手算测试
    ├── test_storage.py          储能边界、效率与调度手算测试
    ├── test_capacity_sensitivity.py  场景独立性与边际变化手算测试
    └── test_economics.py        成本手算、单位、折现与时长测试
```

空目录中的.gitkeep仅用于保留目录，不包含数据。第6阶段继续采用规则调度，没有引入优化求解器或新增第三方依赖。

## Python环境与依赖

建议使用Python 3.10或以上版本。在VSCode中通过“打开文件夹”打开本README所在的整个目录，并安装Microsoft Python扩展；调试时需Python Debugger扩展。

requirements.txt只包含三个基础库：

| 库 | 后续用途 |
|---|---|
| numpy | 数值数组、时序计算 |
| pandas | CSV读取、数据整理、结果表格 |
| matplotlib | 风光荷、储能SOC和场景对比图 |

当前框架入口仅使用Python标准库，即使尚未安装这三个库也可运行。清单暂不锁定版本；正式建模和实验时再记录验证过的版本，保证实验可复现。

在VSCode终端中运行以下命令。终端目录应为本README所在目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

不必激活虚拟环境，因此无需修改PowerShell执行策略。如果python命令不可用，需先安装Python并确保终端能够找到它；如已有Python Launcher，可用py -3替代第一条命令中的python。

随后在VSCode命令面板选择“Python: Select Interpreter”，选择本目录下.venv中的Python。打开main.py点击“Run Python File”，或选择“运行项目入口”并按F5。项目不写死本机Python安装路径。

main.py预期输出包括：24个时间步、每步1小时、仿真时长24小时，以及第2至6阶段入口提示。看到该信息只说明框架入口正常，不代表仿真成功。

## 后续扩展方式

config/simulation.json当前设置num_steps为24、time_step_hours为1.0。无储能计算模块不写死24步；后续扩展至168或8760步时，还须准备匹配长度的连续输入，并调整运行入口读取的数据路径。单改配置不会自动生成长时序数据。

统一使用MW表示功率、MWh表示电量、小时表示步长。SOC采用0至1的比例，与储能剩余电量分开记录。各研究指标的定义见docs/metric_definitions.md。

复杂求解器、网页界面与容量寻优算法在需要时再引入。第6阶段完成后停止，等待用户下一步指令。
