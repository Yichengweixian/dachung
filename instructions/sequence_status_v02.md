# master 顺序执行 v02

用户授权U6往后依次完成。旧单元和失败记录保留，修订用独立单元与冻结。

| 单元 | 当前状态 | 证据 |
|---|---|---|
| U11R15 | complete / refuted（L1主规则未共同通过E门槛；规则本身给出唯一可复现权重） | results/annual/U11R15-v03/、U11R15-v03-independent-audit-v02.json；459 LP全Optimal、0新调度；v01/v02失败与审计v01失败保留 |
| U11R14 | complete / supported（仅固定新日集合四通道输入可行性） | results/annual/U11R14-v01/、U11R14-v01-independent-audit.json；6 LP全Optimal、0新调度，6434项哈希/509源日审计；非唯一最优权重下seed7/2026的E仍超标，非方法成功 |
| U11R13 | complete / supported（仅回顾性会计：新日校准增大六项误差） | results/annual/U11R13-v01/、U11R13-v01-independent-audit.json；653源日零求解、6358项哈希通过，两替换顺序存在交互；非新算法成功 |
| U11R12 | complete / refuted（选日+原校准流程未共同改善成本/缺供） | results/annual/U11R12-v01/、U11R12-v01-independent-audit.json；300LP+147MILP全Optimal，E/D全部通过，但seed42/2026经济与缺供误差增大 |
| U11R11 | complete / supported（仅成本/缺供会计归因，非精度改善） | results/annual/U11R11-v01/、U11R11-v01-independent-audit.json；九组1527日重建、零正式求解；权重改善未消除替代偏差 |
| U11R10 | complete / supported（固定N48权重的两配置迁移双门槛） | results/annual/U11R10-v01/、U11R10-v01-independent-audit.json；1020次全Optimal，六组均通过，成本/缺供只诊断 |
| U11R08B | complete / supported（仅当前年度固定日集合双门槛，BAND=1e-6） | results/annual/U11R08B-v01/、独立审计；540 LP+252 MILP全Optimal，共同通过N=48 |
| U11R09 | complete / inconclusive（R08固定权重重新调度；无共同N通过双门槛） | results/annual/U11R09-v01/、U11R09-v01-independent-audit.json；252次主MILP+9次重复，零权重LP |
| U11R08 | complete / supported（固定日集合的输入电量可行性；U11比例门槛仍未共同通过） | results/annual/U11R08-v02/、independent_audit/report.json；9次主LP与9次独立LP均Optimal，零新增调度 |
| U11R07 | complete / inconclusive（只读诊断，数值根因未证实） | results/annual/U11R07-v01/、U11R07-v01-independent-audit.json；16份LP逐字节一致、零求解调用 |
| U11R06 | blocked / invalid（presolve off 全矩阵在第44次权重LP停） | results/annual/U11R06-v01/、U11R06-v01-partial-audit.json；43次LP与12次调度Optimal，矩阵未完成 |
| U11R05 | complete / supported（只限单模型presolve off诊断） | results/annual/U11R05-v01/、U11R05-v01-independent-audit.json；2次Optimal且重复差0 |
| U11R04 | blocked / invalid（隔离核验后已运行，权重LP非Optimal即停） | results/annual/U11R04-v01/、U11R04-v01-partial-audit.json；101次LP与36次调度，未完成矩阵 |
| U00 | partial / null（T1补证时未提交；后续发布不追溯改判） | results/baseline/U00-T1-v02/；最终登记后快照U00-T1-v03/ |
| U06R01 | complete / supported | results/optimization/U06R01-v03/ |
| U07R01 | complete / supported | results/validation/U07R01-v01/ |
| U08 | complete / supported | results/penetration/U08-master-v01/ |
| U09R01 | complete / supported | results/grid_search/U09R01-v01/ |
| U10 | complete / supported | results/real_data/U10-master-v01/ |
| U11R02 | complete / inconclusive | results/annual/U11R02-v01/ |
| U12R01 | complete / inconclusive | results/ga/U12R01-v01/ |
| U11R03 | complete / inconclusive（比例改善，输入电量未达2%门槛） | results/annual/U11R03-v01/、results/annual/U11R03-v01-independent-audit.json |
| U12R02 | complete / supported（10/10种子，89次/种子，复现差0） | results/ga/U12R02-v02/、results/ga/U12R02-v02-independent-audit.json；v01失败保留 |
| U13R01 | complete / supported（人工操作验收已由用户确认） | results/prototype/U13R01-v01/、results/prototype/browser_check_v02/、results/prototype/audit_v01/audit_report.json、results/prototype/human_acceptance_v01/ |
| U14 | complete / 材料单元不设verdict（T4同步完成，换人抽查待办） | docs/revisions/U14-T4-v01/README.md；results/materials/U14-T4-v01-check04/number_check.json；旧版全部保留 |

- 2026-10-05 U11R15：四通道 minimax 加确定性次级规则（L1 相对原簇计数偏离最小 → 按 date_UTC 打钉），
  L∞ 为预声明对照。三 seed 首级均 reachable（精确上界 ≤2.2815796798661977e-15），
  两求解器 50 级目标差 ≤3.9834269216498797e-10、最终权重差 ≤2.594632064756297e-09 天、另进程重解差 0
  → 问题1（唯一可复现权重）成立；但 seed42 的 E=1.0087256325909344 个百分点超 1.0 门槛，H1=refuted；
  H2=refuted。对照 L∞ 三 seed E=0.557103/0.622921/0.356998 全部通过，但按冻结判据不据此换主规则。
  下一步若要采用 L∞ 或带逐日上限的 L1，须另立单元先冻结；容量迁移需新调度预算。
- 2026-09-23 T4：六份修订材料和86行出处同步完成，最终check04为consistency_passed，56项测试通过；历史研究判定不变。机器抽样不等于decision-rule C外部换人审查，正式排版和新UI集成不在本轮范围。
- 2026-09-27 U11R08：三个N均在三seed下满足2%输入电量门槛；附加比例重建没有共同N满足1个百分点。下一步只研究代表日选取，不改权重流程和验收标准。
- 2026-09-28 U11R09：使用R08正式权重重新完成全部调度；D九组均通过，E在N12/seed7、N24/seed7、N48/seed42超标，无共同N，complete/inconclusive。独立只读审计通过；下一步只研究代表日选取。
