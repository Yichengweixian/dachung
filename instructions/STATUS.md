# 当前状态

## 2026-09-23 T4材料同步完成

六份材料的新增修订版位于docs/revisions/U14-T4-v01/，原版保留。86行出处及最终check04核对通过，56项unittest通过；检查器增加独立版本路径及防覆盖测试。U11R03仍inconclusive，U12R02仅在固定构造算例内supported；无新研究求解，无新界面集成。
首次检查因中文与数字无空格导致标签识别失败，保留check01；修正格式后check02/03通过，进一步明确历史措辞后的check04为最终记录。decision-rule C换人抽查10个数字仍待外部完成，PPT仅Markdown大纲。阶段发布按用户持续授权提交并推送；下一研究方向需要另立单元与确认判据。

## 2026-09-23 U12R02完成

U12R02-v02完成10个固定种子各89次目标调用，10/10质量达标，种子42独立重复轨迹差0；979次求解全部Optimal，判定supported。每次评估数较101减少11.881188%，总研究开销890+89=979次；不宣称墙钟加速、连续全局最优或跨数据普适性。53项测试通过，另进程审计见results/ga/U12R02-v02-independent-audit.json。
v01基准路径错误在求解前停止，失败记录保留；v02仅修正main_文件名前缀。U11R03与旧U12R01判定不变。下一阶段为T4材料和数字出处同步。

## 2026-09-22 U11R03完成

U11R03-v01全部252次求解Optimal，独立复核561项哈希及全部物理解通过，51项测试通过。结论inconclusive：48个代表日下三种子比例误差均<1个百分点，但风电年度输入电量偏差分别为7.123600%、10.303090%、3.225039%，仍超过2%。完整9组结果见本单元findings及comparison.csv。
用户已要求此后每个阶段完成即提交并上传GitHub。该授权持续适用于本项目阶段发布；U00保持partial/null；U12R02是下一单元，本阶段没有执行。
下方各日期段落为历史状态，当前以本节和顺序台账为准。

## 2026-09-21 Git 发布

用户已明确授权将当前完整工作副本提交并推送到GitHub的master。发布前复核：远端与本地基线无分叉，47项unittest通过，无超过10 MB的项目文件，未发现明显凭据文件或凭据赋值。
此次授权只改变版本发布状态，不构成对U11R03/U12R02草案判据的确认，也不追溯改变任何研究verdict。U00仍保持partial/null；此前各段“不提交、不推送”均为对应执行当轮的历史边界。

## 2026-09-17 T2 判据草案（尚未进入实验）

已提出U11R03幅值保留/真实代表日与U12R02固定小预算GA两套草案，每套五份说明。
用户尚未确认方向及数值判据；两单元均not_started、verdict=null，没有freeze.json，没有新实现或新求解。
U11R03拟保留1个百分点精度并增加2%输入电量保真要求；U12R02拟每次89次目标调用、10种子至少9个质量达标。
所有上述新数字均为计划，不是结果。U11R02/U12R01历史inconclusive不变；U00仍partial。本段所述当轮没有提交或推送。
本次仅新增草案与状态登记。此前U00-T1-v03快照保持原样，新增说明和台账造成的当前工作区差异是预期差异。

## 2026-09-17 U00 / T1 补证（优先于下方历史记录）

仅执行用户确认的T1，不提交、不推送，不启动U11R03/U12R02。
U00-T1-v02清单连续两遍一致并通过独立再次核对；47项测试通过，Python/pip/Git环境与Git Bash检查已保存。
本轮补齐归属索引及台账后，最终快照为results/baseline/U00-T1-v03/，实际检查状态以其run_manifest.json为准。
U00保持partial，正式verdict=null：工作区基线提交未做，444.docx入库确认及原清单自引用/输出口径尚待明确。
历史研究run、U14材料及提示词原文不修改；v01中止证据保留。

## 2026-09-16 顺序执行 v02（优先于下方历史记录）

当前进度以[顺序台账](sequence_status_v02.md)及各运行manifest为准。
U06R01互斥MILP、U07R01独立审计、U08场景矩阵、U09R01网格、U10气象管线已完成并supported。
U11R02全年典型日与U12R01 GA对比均为inconclusive（未达冻结判据，阈值未改）。U13R01原型七模块自动化、真实浏览器操作与另进程独立审计均通过，
冻结判据要求的人工操作验收已由用户确认通过，verdict由inconclusive更新为supported（机器记录run_manifest.json未改写，人工确认另档登记）。
U14材料单元已完成：六份材料 + 72行数字出处全部回溯一致（docs/number_consistency_table.md），口径红线自查通过；该单元不设verdict。
U06—U14序列至此全部执行完毕。claims表保持为空：路线图将各单元标为exploratory，按claims登记规则exploratory单元不登记论断，材料只引用各单元findings与CSV。
历史U06失败仍保留，不追溯改判；不合并u10-complete。
44项测试实际通过；当时工作位于E:\dachuang的本地master，尚未提交或推送。
U00仅有baseline_manifest及基线测试，不冒充全部正式验收。

## 2026-09-15 master 本地执行记录（历史）

- 工作基线：`003a014ffa95a465cb2a0f0fb5874d2ccb75580f`；当前本地分支 master。
- U06：blocked / invalid（连续 LP 与验收中的充放电互斥要求冲突）。
  `U06-master-v01` 返回 Optimal，但 11 时段同时充放电；最大等式残差/边界违规量
  `5.789473735973161e-7`，低于原始 `1e-6` 门槛。失败并非模型无解或数值残差超标。
- 基线测试 25/25；实现后 32/32。单元测试通过不等于 U06 主算例验收通过。
- U09：not_started，verdict=null；缺少通过的 U06/U07，另有 111/101 组合数和 P 边界判据冲突待定稿。
- U11：not_started，verdict=null；本分支无年度原始数据、8760h 输入、年度仿真或聚类实现。
- U11R01：仍为规格草案；没有另一工作副本中的原始年度数据、转换代码及失败证据，未实施封顶修订。
- U13：not_started，verdict=null；缺少已验收的优化/网格实现及 web 原型，LP 与规则基准的一致性要求需澄清。
- 环境：项目 `.venv` 使用 Python 3.13 的 system-site-packages，新增 PuLP 3.3.0；实际库版本见运行 manifest。
- 记录：`results/master_revalidation_v01/`、`results/optimization/U06-master-v01/`、
  `docs/master_instruction_validation_v01.md`。U00 的全部正式验收未执行，不能据此将其标为 supported。
- 本次改动尚未提交或推送；下方“尚未是 Git 仓库”等描述仅代表旧状态。

更新时间：2026-09-12。范围：本执行包建立时的项目真实状态核对（只读，未改代码）。

| 项目 | 状态 | 已有证据 / 下一步 |
|---|---|---|
| 第 1—6 阶段代码与结果 | complete（历史基线） | 入口 run_data_24h.py / run_no_storage.py / run_storage.py / run_capacity_sensitivity.py / run_economics.py；结果与测试见 U01—U05 findings |
| 现有测试 | complete / passed（历史） | 25 项 unittest 通过（5+5+8+7 按阶段分布）；U00 将全量重跑记录 |
| 版本控制 | not_started | 项目尚未是 git 仓库；U00 负责建立版本基线 |
| 执行说明包 | complete | 本包（specs/studies/prompts 齐备），仅为说明包验收 |
| U00 基线冻结 | not_started | verdict=null，decision-rule 未冻结 |
| U01—U05 基线登记 | complete（事后整理） | 判据为事后整理，不进入 claims |
| U06—U14 未来单元 | not_started | 每单元 verdict=null，decision-rule 未冻结 |
| 优化求解器依赖 | not_started | scipy / PuLP 均未安装；U06 安装并锁定版本 |
| 真实数据（NASA POWER） | not_started | U10 建立下载与转换管线 |

状态字段与科研判定分开：工程可用 `not_started / in_progress / blocked / complete`；`complete` 只代表工作做完，不自动表示研究结论 supported。
