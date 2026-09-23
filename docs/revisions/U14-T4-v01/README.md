# U14 / T4 材料修订 v01

日期：2026-09-23。此目录是包含 U11R03、U12R02 结果的最新材料入口。原 docs/ 六份材料及其数字表保留为历史版，不覆盖。

## 六份材料

- [阶段报告](stage_report.md)：增加代表日与固定预算 GA 的结果和限制。
- [汇报 PPT 大纲](汇报PPT大纲.md)：增加两页修订研究，区分历史结论。
- [汇报稿](汇报稿.md)：同步讲稿及问答，撤回缺乏证据的误差归因。
- [论文初稿](paper_draft.md)：同步摘要、结果、讨论与结论。
- [专利技术交底草稿](patent_disclosure_draft.md)：补充研究验证，不据此宣称新颖性或扩大权利要求。
- [软件著作权材料草稿](software_copyright_materials.md)：区分离线研究脚本与已人工验收的界面功能。

## 数字与验证

- [出处表](number_sources.csv)：保留原 72 行，新增 N54–N67，共 86 行。
- [最终核对表](number_consistency_table_check04.md)：consistency_passed。
- 首次核对表 number_consistency_table.md 是失败记录；check02、check03 是通过的中间版本，不能代替最终文件哈希。
- 最终机器报告：results/materials/U14-T4-v01-check04/number_check.json（路径相对仓库根目录）。
- 实际执行完整 unittest，56 项通过；新增三项覆盖自定义输出和既有报告保护。

复核时使用新的输出名，避免覆盖记录：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/check_materials_numbers.py --materials-dir docs/revisions/U14-T4-v01 --table docs/revisions/U14-T4-v01/number_sources.csv --out results/materials/U14-T4-v01-review01 --report-table docs/revisions/U14-T4-v01/number_consistency_table_review01.md
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p "test_*.py" -v
```

## 边界与待办

U11R03 仍为 inconclusive，U12R02 的 supported 仅限固定构造算例和预算/质量判据，不代表墙钟加速或连续全局最优。按 academic-humanizer 的证据约束调整结论措辞，旧数值与引用未改写。

本轮无新研究实验，无新 UI 功能。PPT 仍是 Markdown 大纲，论文、专利及软著仍是草稿，没有正式排版或申报。decision-rule C 要求的换人随机抽查 10 个数字仍待进行；机器生成抽样名单不等于外部人工审计。
