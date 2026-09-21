# 提示词（可直接粘贴给 Codex）：接续大创项目，从 U14 之后继续完成

> 生成时间：2026-09-16 23:15（本地）。本文件即完整提示词，无需再补充上下文。
> 使用方式：把下面 `---8<---` 之间的全部内容复制给 Codex。

---8<---

你是本项目（大学生创新训练计划第一阶段，以下简称"大创"）的编程助手，接续前一位助手已完成的工作。
**项目根目录：`E:\dachuang`（Windows）**。Git 分支 `master`，当前 HEAD 为 `003a014`（"更新：U11 光伏出力上限修订研究"）；
**本轮全部工作尚未提交、未推送**（工作区有约 88 个新增/修改条目）。

## 0. 你的任务总目标

把项目从"U06—U14 主体已完成、但仍有未决项与收尾项"推进到**可结题状态**：
补完基线冻结、处理两个 inconclusive 单元、同步成果材料与台账、并分单元提交。
**一切以文件与运行记录为准，不得凭记忆或推断填写任何数字。**

## 1. 先读这些文件（按顺序，读完再动手）

1. `instructions/AGENTS.md`（执行规则，最高优先级）
2. `instructions/sequence_status_v02.md`（单元台账：当前真实进度）
3. `instructions/STATUS.md`、`instructions/RUNLOG.md`（只增不改的追加记录）
4. `instructions/specs/roadmap.md`（总路线图 + Backlog + 口径红线）
5. `instructions/specs/claims.md`（论断登记表，目前为空，原因见 §3.3）
6. 各单元说明与结论：`instructions/studies/U06R01-mutual-exclusion/`、`U07R01-factorial-audit/`、
   `U08-penetration-matrix/`、`U09R01-grid-clarification/`、`U10-real-weather-data/`、
   `U11R02-annual-coherent/`、`U12R01-ga-baseline/`、`U13R01-consistent-prototype/`、`U14-materials/`
   （每个目录含 question/design/plan/decision-rule/findings[/freeze.json]）
7. `docs/number_sources.csv` 与 `docs/number_consistency_table.md`（U14 材料数字出处与核对表）
8. `docs/stage_report.md`（阶段报告，了解全貌）
9. `444.docx` 与 `instructions/prompts/*.md`：**只读，禁止修改**

## 2. 铁律（违反即视为无效工作）

1. **归属明确**：每次先说明在做哪个单元/任务，不得在台账之外临时改变策略。
2. **判据先行**：新建或修订单元必须先写 `decision-rule.md` 并生成 `freeze.json`，**冻结后才允许实现与求解**；
   冻结后不得改阈值、场景、候选、参数或方向。需要改 → 新建修订单元（如 U11R02 → U11R03）。
3. **证据三元组**：任何数值结论必须有「脚本 + 参数 + 代码/依赖版本」，并附 run_id、输入 SHA-256 与运行环境
   （由 `src/study_runtime.py` 的 `StudyRun` 自动写入 `results/<组>/<run_id>/run_manifest.json`）。
   文档结构通过 ≠ 模型通过。
4. **结果四分类**：`supported / refuted / inconclusive / invalid`；未执行一律 `verdict: null`。
   **否定与不确定结果完整保留，禁止删除失败记录，禁止为了好看调阈值。**
5. **禁止凑数**：不得为匹配申报书数字（如 84.63%、87.08%、308680 元）调整数据、参数或口径；
   这些历史数字不得作为本项目已复现结果引用。
6. **求解失败即停**：求解器状态非 Optimal 或数值异常，必须停止并报告，不得继续出图或下结论。
7. **文件保护**：`444.docx` 与提示词原文只读；禁止批量删除文件或目录，删除须逐文件给出路径并经用户确认。
8. **数据诚实**：构造数据必须标注"构造算例（非真实电网数据）"；真实数据必须记录来源、坐标、时间范围与转换方法。
   本项目真实部分**只有气象**（NASA POWER），负荷始终是构造形状。
9. **一次只推进一个研究单元**；每个单元完成后停止，等用户下一步指令。
10. **数字出处**：材料/汇报中的任何数字必须来自 `results/` CSV、运行 manifest 或单元 findings；
    U14 已建立的规则是——材料内数字用 `【ID】` 标签指回 `docs/number_sources.csv`，
    由 `scripts/check_materials_numbers.py` 自动回溯核对，**未登记数字即为失败**。

## 3. 现状快照（截至 2026-09-16 深夜）

### 3.1 已完成单元与判定

| 单元 | 判定 | 证据目录 | 关键事实 |
|---|---|---|---|
| U06（原 LP） | blocked / invalid（历史保留） | `results/optimization/U06-master-v01/` | CBC Optimal 但 11 时段同时充放电，违反验收 |
| U06R01（互斥 MILP 修订） | supported | `results/optimization/U06R01-v03/` | 7 场景全 Optimal，最大残差 7.3736572403504397e-12 |
| U07R01（全因子+独立审计） | supported | `results/validation/U07R01-v01/` | 17 场景，反序差 0，闭合残差 1.4551915228366852e-11 |
| U08（渗透率矩阵） | supported | `results/penetration/U08-master-v01/` | 12 场景，三项预设趋势成立 |
| U09R01（101 点网格） | supported | `results/grid_search/U09R01-v01/` | 303 次 Optimal；最优 70 MWh/25 MW = 486358.65 元/24h |
| U10（NASA 气象管线） | supported | `results/real_data/U10-master-v01/` | 168h 完整；四坐标微扰相对差 0；转换字节可复现 |
| U11R02（全年 365 独立日+典型日） | **inconclusive** | `results/annual/U11R02-v01/` | 425 次 Optimal；最优误差 6.4346 pp > 判据 1 pp |
| U12R01（三种子 GA） | **inconclusive** | `results/ga/U12R01-v01/` | 4440 次评估；成本误差 <0.5% 但每种子 1480 次 > 判据 101 次 |
| U13R01（原型） | **supported**（人工验收已确认） | `results/prototype/U13R01-v01/`、`browser_check_v02/`、`audit_v01/`、`human_acceptance_v01/` | 界面与基准逐值差 ≤5.82e-11；浏览器 5 步通过；44 项测试 OK |
| U14（成果材料） | complete（材料单元不设 verdict） | `docs/` 六份材料 + `results/materials/U14-v01/number_check.json` | 72 行数字出处全部回溯一致 |

### 3.2 全项目复核结论（最近一次）

`results/artifact_audit_v03.json`：8 个 run 全部 passed，5217 个场景均 Optimal 且残差 <1e-6，10609 项哈希一致，零错误。

### 3.3 未决与需要注意的点

- `U00` 仍为 partial：只有 baseline_manifest 与基线测试，未完成"版本基线与产物清单冻结"的全部正式验收。
- `U11R01`（年度光伏 150 MW 封顶修订）只是规格草案，未实施；U11R02 已用显式封顶跑完（该年触发 0 小时）。
- `claims.md` 为空是**合规**的：路线图把各单元标为 exploratory，按 claims 登记规则 exploratory 单元不登记论断；
  材料只引用 findings 与 CSV。若要把某结论升级为"一般性论断"，必须**先**在 claims.md 预写措辞并说明证据，再引用。
- 已知源漂移：`scripts/freeze_study.py` 在 U06R01/U07R01 运行之后被改过（该脚本只生成冻结记录、不参与模型计算），
  已在 RUNLOG 中如实登记，不影响任何数值结论。
- 已保留的失败证据（**不得删除**）：`results/optimization/U06-master-v01/`、
  `results/prototype/browser_check_v01/`（驱动脚本缺陷导致 2 步失败，修驱动后 v02 全过）、
  各单元 `failure.json`。
- 原型服务当前在本机运行（`http://127.0.0.1:8513`，仅本机可访问、已关闭使用统计）。

## 4. 环境与可复现命令

- 解释器：项目虚拟环境 `.\.venv\Scripts\python.exe`（Windows；**不要**用系统 Python）。
- 测试：`.\.venv\Scripts\python.exe -m unittest discover -s tests` → 期望 `Ran 44 tests ... OK`。
- 全项目产物复核：
  `.\.venv\Scripts\python.exe scripts\audit_study_artifacts.py <8个run_manifest.json> --output results/artifact_audit_v04.json`
  → 期望全部 `passed`。注意该脚本用文件独占模式写 output，**目标文件必须不存在**。
- U14 数字核对：`.\.venv\Scripts\python.exe scripts\check_materials_numbers.py` → 期望 `consistency_passed`。
- U13 独立审计：`.\.venv\Scripts\python.exe scripts\audit_prototype_results.py --with-src-reproduction`
  → 期望 `audit_passed`。
- 冻结新单元：`.\.venv\Scripts\python.exe scripts\freeze_study.py <单元目录名>`（会哈希该目录 `*.md`（不含 findings.md）、
  `config/*.json` 与 `data/input_24h.csv`，并写入 `freeze.json`；**必须在运行前执行**）。
- 求解入口示例：`run_u06_revision.py`、`run_grid_search.py`、`run_annual.py`、`run_ga.py`、`run_penetration.py`、
  `run_real_data.py`、`run_prototype_validation.py`。

**本机实测过的环境坑（照此处理，别浪费轮次）**：
1. CBC 用 `threads=1` 在 Windows 上会停滞，用**串行**（`threads=0`）；求解结果文件要用**临时目录内的相对路径**，
   不要传 Windows 绝对路径（否则出现 saveSolution 拼接错误）。
2. `pip` 与部分测试会往系统临时目录写文件；若被权限拒绝，把 `TEMP`/`TMP` 指到项目内目录再执行。
3. matplotlib 若报缓存目录不可写，设置 `MPLCONFIGDIR` 到项目内目录。
4. 生成的 run 目录是不可覆盖的（`StudyRun` 用独占创建）；重跑要换 run_id，**不要覆盖已有结果**。

## 5. 本轮要做的任务（按顺序，做完一项汇报一项）

### T1　U00 收尾（低风险，先做）

目标：把"版本基线与产物清单冻结"补成完整单元。
- 冻结 U00 判据；生成 `results/` 产物清单（路径 + SHA-256 + 所属单元 + 判定），记录环境（Python 与依赖版本）。
- **不要**改动任何已有 run 目录；清单是新增文件。
- 完成标准：清单可由脚本重新生成并逐项比对一致；把结果写入 `instructions/studies/U00-baseline-freeze/findings.md`
  与 RUNLOG/STATUS。

### T2　处理两个 inconclusive 单元（**必须先经用户确认方向与判据草案**）

先向用户提交两份 `decision-rule.md` 草案（**不要直接冻结、不要直接跑**），二选一或都做：
- **U11R03（典型日近似改进）**：当前判据是"最差误差 ≤1 个百分点"，实测最优 6.4346 pp。
  候选方向：提高典型日数 N、改用 k-medoids、加入幅值/持续时长特征、或改为"误差相对全年逐日基准的改进幅度"。
  草案必须写明：数据（`results/annual/U11R02-v01/input_8760h.csv`，365 天）、比较基准、判据数值与理由、失败判定方式。
- **U12R02（加速判据重设计）**：当前判据"目标函数评估次数 <101"未被 GA 满足（每种子 1480 次）。
  草案必须写明：加速的**可检验定义**（例如与 101 点网格相比，在同等或更好解质量下评估次数更少的比例）、
  随机种子集合、重复次数、以及"未达标即 inconclusive"的判定。
用户确认后：写 `freeze.json` → 实现 → 运行 → 登记（见 §6）。**不得改动 U11R02/U12R01 的历史判定与冻结文件。**

### T3　口径缺口（可选，需用户同意后再开）

如果用户希望补"逐日独立、无跨日耦合"这一最大缺口，新建单元研究跨日/周尺度储能（长时储能），
同样先冻结判据；不要偷偷把年度模型改成整年单体 MILP（当前 8760h 单体 MILP 未实现、也不在冻结范围内）。

### T4　材料与台账同步

- 若 T1/T2/T3 产生新结果：把新数字登记进 `docs/number_sources.csv`（沿用 `P/N` 编号规则与 `selector/column/tolerance` 字段），
  更新六份材料相关段落，然后重跑 `scripts/check_materials_numbers.py`，**必须仍为 `consistency_passed`**；
  核对表 `docs/number_consistency_table.md` 由脚本重新生成，不要手改。
- 同步 `instructions/sequence_status_v02.md`、`STATUS.md`、`RUNLOG.md`、`specs/roadmap.md`（含 Backlog）。

### T5　提交（分单元）

- 按单元分批 `git add` + commit（例如：`U06R01 互斥修订`、`U07R01 独立审计`、…、`U13R01 原型与人工验收`、
  `U14 成果材料`、`U00 基线冻结`、`U11R03 …`）。commit message 用中文，说明单元、判定与证据目录。
- **只提交，不推送**（`git push` 需用户明确指令）。
- 提交前确认工作区没有把 `results/**` 里的大批量运行产物误删或改写（只允许新增文件）。

## 6. 每完成一个单元的登记清单（缺一不可）

1. 该单元 `findings.md`：status / verdict / 主结果 / 稳健性 / 失败保留 / 意外发现；
2. `run_manifest.json`：run_id、输入与判据哈希、代码与依赖版本、各场景 solver_status 与残差；
3. `instructions/RUNLOG.md` 追加一条（只增不改）；
4. `instructions/sequence_status_v02.md` 更新该行状态与证据路径；
5. `instructions/STATUS.md` 更新当前状态段落；
6. 如涉及新发现或暂缓项，写入 `instructions/specs/roadmap.md` 的 Backlog。

## 7. 明确禁止

- 修改任何已冻结单元的 `decision-rule.md`/`freeze.json` 来"让结果通过"。
- 删除或改写历史失败记录（U06 原 LP、browser_check_v01、各 failure.json）。
- 把构造数据写成真实电网数据；把计划写成已完成；把 inconclusive 写成 supported。
- 引用 `results/` 中不存在的数字，或手工编造数值/图表。
- 批量删除文件；改动 `444.docx` 与 `instructions/prompts/*`。
- 未经用户确认就启动新的研究单元或改变研究判据。

## 8. 汇报格式（每轮结束回给我）

1. **做了什么**（单元编号 + 任务组）；
2. **实际运行的命令**及关键输出（含 run_id、平台、求解耗时）；
3. **判定**（supported / refuted / inconclusive / invalid / complete）与依据；
4. **产物路径**（新增/修改文件清单，含哈希或 manifest 路径）；
5. **失败或异常**（完整保留，不修饰）；
6. **下一步建议**与需要我确认的问题。

最后：如果你在任何一步发现"要改判据才能通过"，**停下来报告**，不要改。

---8<---
