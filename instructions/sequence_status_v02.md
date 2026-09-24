# master 顺序执行 v02

用户授权U6往后依次完成。旧单元和失败记录保留，修订用独立单元与冻结。

| 单元 | 当前状态 | 证据 |
|---|---|---|
| U11R04 | blocked / null（方案已确认，冻结前源码漂移审计未通过） | results/annual/U11R04-preflight-v01/failure.json；无冻结、实现或新求解 |
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

- 2026-09-23 T4：六份修订材料和86行出处同步完成，最终check04为consistency_passed，56项测试通过；历史研究判定不变。机器抽样不等于decision-rule C外部换人审查，正式排版和新UI集成不在本轮范围。
