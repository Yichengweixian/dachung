# 执行记录（追加式）

每完成一个研究单元（或一次独立审计/重规划）追加一条，只增不改。字段：

`日期 | 单元 | 动作 | 判定/结果 | 关键文件`

---

（尚无记录。U00 执行后写入第一条。）

2026-09-15 | U06/master | 基线检查、外部冻结、连续LP实现、主算例验收 |
blocked / invalid：32项测试通过，CBC Optimal，但11时段同时充放电；按plan组2停止后续实验 |
results/master_revalidation_v01/、results/optimization/U06-master-v01/、docs/master_instruction_validation_v01.md。
代码尚未提交，代码/参数/输入哈希和环境以manifest为准。U09/U11/U13未执行，verdict保持null。

2026-09-15 | U06R01 | 用户授权顺序执行后新增互斥修订 | supported，7场景全部Optimal，残差最大7.37365724035044e-12 | results/optimization/U06R01-v03/。v01线程停滞、v02原生文件路径失败完整保留。

2026-09-16 | U07R01 | 全因子归因与独立进程审计 | supported，17场景，反序差0，闭合残差1.4552e-11 | results/validation/U07R01-v01/。

2026-09-16 | U08 | 12场景矩阵及反序复现 | supported，三项趋势通过，反序差0 | results/penetration/U08-master-v01/；三幅图已实际打开检查。

2026-09-16 | U09R01 | 101点网格、反序、高投资成本 | supported，303次Optimal，70MWh/25MW为唯一离散最优 | results/grid_search/U09R01-v01/；三幅图已实际打开检查。

2026-09-16 | U10 | 固定历史7天、原始NASA响应、四坐标微扰、另进程转换 | supported，168h完整，CSV字节复现，微扰指标差0 | results/real_data/U10-master-v01/、data/raw/U10-master-v01/；两幅图已实际打开检查。

2026-09-16 | U11R02 | 全年365独立日+六组典型日比较 | inconclusive，425次Optimal，但最好误差6.434640个百分点超阈值 | results/annual/U11R02-v01/；两幅图已实际打开检查。

2026-09-16 | U12R01 | 三种子完整GA | inconclusive，4440次Optimal，成本误差均<0.5%但每种子1480次不满足<101加速判据 | results/ga/U12R01-v01/；收敛图已实际打开检查。

2026-09-16 | U13R01 | 原型七模块自动化验收+真实浏览器(Chrome CDP)操作+另进程独立审计 | inconclusive（工程待人工验收）：界面与U06R01/U09R01/E40_P20逐值差均<1e-6，浏览器五步通过、控制台错误0，独立审计audit_passed；browser_checks记录human_confirmation=false，不冒充人工 | results/prototype/U13R01-v01/、results/prototype/browser_check_v02/、results/prototype/browser_check_v01/（失败保留）、results/prototype/audit_v01/audit_report.json；截图已逐张打开检查。

2026-09-16 | U14 | 六份成果材料整理+数字一致性核对+口径红线自查 | 完成（材料单元不设verdict）：consistency_passed，72行出处全部回溯一致、未登记数字0、未引用行0、标签错位0，红线自查通过 | docs/stage_report.md、docs/汇报PPT大纲.md、docs/汇报稿.md、docs/paper_draft.md、docs/patent_disclosure_draft.md、docs/software_copyright_materials.md；docs/number_sources.csv、docs/number_consistency_table.md、results/materials/U14-v01/number_check.json。前两轮核对失败记录保留在findings。

2026-09-16 | U13R01 | 人工操作验收确认登记（用户文字确认“通过”），并同步U14材料中“待人工验收”的过时表述 | U13R01 verdict inconclusive→supported（按冻结判据闭环）；U14材料红线自查同步改为“人工验收已确认”并新增禁止过时表述检查，重新核对仍consistency_passed | results/prototype/human_acceptance_v01/human_acceptance.json；instructions/studies/U13R01-consistent-prototype/findings.md。当次机器记录run_manifest.json的verdict未改写。

2026-09-16 | 全项目 | 8个已完成的运行manifest只读复核（脚本scripts/audit_study_artifacts.py） | 全部passed：8个run、5217个场景（均Optimal且残差<1e-6）、10609项哈希一致、无误 | results/artifact_audit_v03.json。发现scripts/freeze_study.py在U06R01/U07R01运行后有过改动（LastWriteTime 20:38，晚于两个run），该脚本只用于生成冻结记录、不参与模型计算；U08及以后各run记录的哈希与其一致，故不影响任何数值结论，如实登记。

2026-09-17 | U00 / T1 | 非提交补证，原规则原样冻结，新增工作区快照与results归属索引 | U00-T1-v02辅助检查通过：10838个文件双遍及独立再次核对一致，47项测试OK，PowerShell/Git Bash均正常；U00正式验收仍partial/null | results/baseline/U00-T1-v02/。v01首遍后中止记录完整保留；最终台账及归属补齐后的快照另存U00-T1-v03，实际检查结果见其manifest。不提交、不推送，不改历史run或U14材料，不启动后续修订研究。

2026-09-17 | T2 / U11R03、U12R02草案 | 用户“继续”后准备方法与判据供确认 | 两单元not_started/null，未冻结、未实现、未运行；原1个百分点及0.5%质量量级保留，提议输入电量保真检查与显式小预算 | instructions/studies/U11R03-amplitude-representative-days/、U12R02-budgeted-ga/。只新增说明及台账，无提交、推送或材料数字变更；待用户确认后才执行单一研究单元。

2026-09-21 | Git发布 | 用户授权检查当前工作副本并上传GitHub master | 发布前origin/master与本地基线无分叉，47项unittest通过，无超过10 MB项目文件，未发现明显凭据；提交与推送只发布既有成果，不确认U11R03/U12R02草案，不改变历史verdict | 当前完整工作副本及本日志。

2026-09-22 | U11R03 | 用户确认继续并要求每阶段上传；冻结后完成幅值保留与真实代表日完整矩阵 | 252次Optimal，51项测试通过，另进程561项哈希及逐时复核通过；全部9组输入电量偏差超过2%，verdict=inconclusive | results/annual/U11R03-v01/、results/annual/U11R03-v01-independent-audit.json。旧基准365日只读复核通过。每阶段完成即提交推送的授权持续有效。

2026-09-23 | U12R02 | 固定89次预算GA及10种子主试验、种子42独立复现 | supported：10/10质量达标，979次Optimal，重复成本/轨迹差0，53项测试通过；逐时读回与另进程审计 | results/ga/U12R02-v02/、results/ga/U12R02-v02-independent-audit.json。v01基准路径缺main_前缀在求解前失败并保留，v02修正入口；无门槛、算子、数据调整。

2026-09-23 | U14 / T4 | 六份材料及数字出处版本化同步 | complete（材料单元，verdict null）：86行出处、最终check04 consistency_passed，56项unittest通过；新增独立输出与防覆盖测试。check01格式识别失败和check02/03中间通过记录均保留 | docs/revisions/U14-T4-v01/、results/materials/U14-T4-v01/run_manifest.json。旧研究判定、原材料、冻结规则及既有结果均不改；无新研究实验；外部换人10项数字抽查与正式排版仍待办。按用户持续授权提交并推送master。

2026-09-24 | U11R04草案 | 用户选择继续研究、不做PPT；基于U11R03结果与现有代码提出受限权重校准 | not_started/null，五份草案待方法与数值确认，无freeze、实现或新求解 | instructions/studies/U11R04-energy-calibrated-weights/。原1个百分点与2%不放宽，新权重边界为提案；旧研究判定不变，按持续授权发布草案不等于批准实验。

2026-09-24 | U11R04前置核验 | 用户明确“同意”，登记方法审批后只读核验 | blocked/null：U11R03审计因T4材料检查器源码漂移退出；两旧运行产物哈希检查893+561项通过，但本轮物理重审未完成 | results/annual/U11R04-preflight-v01/failure.json、U11R04-preflight-hash-audit-v01.json。无freeze、无实现、无新求解；依plan冻结前异常只报告，保留旧manifest及所有判据。

2026-09-24 | U11R04执行 | 用户要求继续；隔离历史源码复核通过后按原批准方案冻结、实现、测试、运行 | blocked/invalid：专项6项与全量62项测试通过；正式101次LP（1次Infeasible）+36次Optimal调度后立即停止，耗时28.920328秒；另进程313项哈希与部分物理/成本审计通过但研究无效 | results/annual/U11R04-isolated-preflight-v01/（审计入口遗漏失败）、v02/（通过）、U11R04-v01/、U11R04-v01-partial-audit.json。首次隔离入口遗漏修复仅影响审计准备；正式求解失败后没有重试或改容差。全部失败保留，无PPT，按持续授权提交推送。

2026-09-24 | U11R04只读诊断与U11R05草案 | 重放21阶段、Decimal核对内存与MPS模型，不调用优化器 | LP全部逐字节一致，简单边界无冲突，上一解非严格可行，根因未确定；诊断3项测试通过，U11R04 invalid不变 | results/annual/U11R04-diagnosis-v01/（RHS解析器错误保留）、v02/（完成）；scripts/diagnose_u11r04_serialization.py。U11R05五份草案待确认，拟仅关闭presolve单实例最多2次诊断，未冻结未运行。
