# master 指令执行与核验 v01

日期：2026-09-15。项目：`E:\dachuang`。基线：`003a014ffa95a465cb2a0f0fb5874d2ccb75580f`。
按用户最后指令，仅在 master 上执行，不合并其他分支。改动尚未提交、推送。

## 结论与适用范围

U06 连续 LP 已实现并实际运行，主算例验收失败。原有25项测试与新增7项测试全部通过，
但单元测试通过不能代替正式研究判据。U09、U11、U13没有完成或通过的结论。

| 单元 | 已核对的实际状态 | 本次处理 |
|---|---|---|
| U06 | master 原本无优化实现；设计为连续LP | 新增实现并运行；11时段同时充放电，blocked / invalid |
| U09 | 无网格实现；缺少通过的U07；111/101组合数及P边界判据冲突 | 只检查前置，未运行，verdict=null |
| U11 | 无年度原始数据、8760h输入、年度仿真或聚类实现 | 只检查前置，未运行，verdict=null |
| U11R01 | 最新提交只有光伏封顶修订规格；data/raw只有.gitkeep | 未猜测原始单位/年份，未执行，verdict=null |
| U13 | 无web/app.py、使用说明及可验收网格模块；LP与规则基准不同 | 只检查前置，未运行，verdict=null |

## U06 如何实现

- 模型严格采用 master 的连续变量：火电、风光消纳/弃电、充放电、失负荷，以及25个电量边界。
- 火电最大出力只从 `config/no_storage.json` 读取；新 optimization.json 只增加最小出力、爬坡及目标分量说明。
- 固定40 MWh / 20 MW，SOC初始0.5、上下限0.1/0.9、效率0.95；成本系数从原 economics.json 读取。
- 所有原始数据和成本均为构造算例/测试假设，非真实电网或工程经济参数。
- `src/optimization_validation.py` 不导入优化器或建模函数；从输入和输出独立计算平衡、边界、SOC、互斥检查。
  原规则验证器含贪心调度策略检查，因此没有用于验收LP。
- 入口在求解前检查冻结输入、参数与规格的哈希，并运行测试；结果先按诊断文件保存、读回。
  任何检查失败返回非零，只保留诊断与失败记录，不生成通过验收的汇总或图表。

## 实际实验与根因

运行ID：`U06-master-v01`。CBC 2.10.3，PuLP 3.3.0；变量均连续，整数变量数0。

| 检查 | 实际结果 |
|---|---|
| CBC状态 | Optimal |
| 最大等式残差/边界违规量 | 5.789473735973161e-7，小于1e-6 |
| 功率平衡最大残差 | 约3.0e-7 MW |
| 期末电量与初始电量差 | 0 MWh |
| 同时充放电 | 11时段：0、1、2、3、4、9、10、11、12、13、14 |
| 内存结果与CSV读回验收 | 均失败，失败项仅simultaneous_charge_discharge |

例如hour=9：充电20 MW、放电18.05 MW。该现象远大于1e-6，与输出舍入或容差边缘无关。
连续LP仅约束充放电各自不超过20 MW，没有互斥约束。按当前成本系数，一小时在能量不变时
充20、放18.05会净吸收1.95 MWh，减少弃电惩罚390元，增加放电运维180.5元，
使目标减少209.5元。独立单时段手算测试用load=30、wind=100、thermal_min=30复现这一机制。

`design.md` 采用连续LP，而 `plan.md` 组2第5项要求二者不能同时超过1e-6。
程序严格实施前者并由校验器拒绝后者的失败结果。本次标为设计/执行验收invalid，
不代表CBC无解或LP数学模型不能求得最优。原decision-rule A/B对求解失败分类也有重叠，
此轮未触发Infeasible分支，不擅自重写这些条款。

依照plan组2，主算例失败后未进入三因素归因、正式半小时/零储能/零新能源稳健性组，
也未继续依赖它的U07/U09。半小时和零储能的单元测试只验证手算小例子，不替代正式稳健性研究。

## 验证命令与结果

```powershell
.\.venv\Scripts\python.exe scripts/prepare_master_baseline.py
.\.venv\Scripts\python.exe scripts/freeze_u06.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_optimization.py" -v
.\.venv\Scripts\python.exe run_optimization.py --run-id U06-master-v01
```

前两条已经执行并生成不可覆盖的v01记录，不要直接重复使用同一输出目录。
基线25项测试通过；U06新增7项测试通过；运行入口中的全量32项测试通过。
初次开发测试曾因不存在的PuLP统计方法报AttributeError，已按安装包接口修正为统计变量的isInteger()；
修正后7项测试及全量32项通过。正式主算例不是程序异常，而是校验器按要求拒绝11个同时充放电时段。

已建立 `.venv`，使用 `python -m venv --system-site-packages .venv` 复用本机数值库，
并执行 `.\.venv\Scripts\python.exe -m pip install pulp==3.3.0`。这不是完全隔离的依赖环境；
Python、NumPy、pandas、matplotlib和PuLP的实际版本保存在manifest，未对基线库做升级。

## 证据与文件清单

- `scripts/prepare_master_baseline.py`：原master文件哈希与25项测试记录。
- `scripts/freeze_u06.py`：在实现前保存输入、配置、计划和判据哈希；原判据正文保持原样。
- `config/optimization.json`、`src/optimization_model.py`：U06参数及连续LP。
- `src/optimization_validation.py`、`tests/test_optimization.py`：独立验收和7项边界/手算测试。
- `run_optimization.py`：前置核对、求解、诊断落盘、读回验收和失败即停。
- `results/master_revalidation_v01/`：baseline_manifest、baseline_tests和u06_freeze_record。
- `results/optimization/U06-master-v01/`：原始诊断CSV、checks、CBC日志、32项测试记录、failure和run_manifest。
- README、STATUS、U06 findings、RUNLOG、roadmap：更新本次状态及阻塞原因。

freeze中的原findings哈希是执行前快照；执行后允许更新结果台账，后续入口不把结果登记误判成方法改动。
原输入、444.docx、旧结果和提示词没有改动。没有发布新的经济结论、图表、论文结论或claims。

## 后续需要定稿的事项

1. U06另建修订单元明确互斥方法（如MILP），保留原LP失败记录。当前用户要求按原instructions执行，
   因此没有在冻结后自行改变模型类别、成本参数或验收门槛。
2. U09首次执行前解决101/111组合数、P边界判定及U07前置；不能静默凑出额外10个组合。
3. U11需要实际年度数据和来源元信息；聚类权重比例和为1、天数权重和为365须区分。
   U11R01需实际原始文件和旧失败证据，不能把提示词里的“2小时”当成实验结果。
4. U13应区分规则调度与优化调度的一致性基准；当前要求LP输出逐值等于规则结果存在模型口径冲突。

这些问题只登记在Backlog，本次不追溯修改被冻结的判据。
