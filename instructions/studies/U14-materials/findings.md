---
unit: U14
status: complete
verdict: null（材料单元不设 verdict）
rule_commit: null
code_commit: null
run_ids: [U14-v01]
completed_at: null
---

# U14 结果与判定

本单元为材料单元，不设 verdict；按 decision-rule B 的完成标准判定：六份材料齐备、数字一致性核对全部通过、口径红线无违反 → **完成**。

## A. 有效性闸门

前序单元 findings 已收尾（U06R01—U13R01，U14 之前最后一项为 U13R01）；材料清单、数字出处规则与口径红线已冻结，
冻结记录见同目录 freeze.json（git_head 003a014，含本目录四份说明文件与全部 config 的 SHA-256）。

## B. 完成标准

| 材料 | 文件 |
|---|---|
| 阶段报告 | docs/stage_report.md |
| 汇报 PPT 大纲（10 页，待排版为 pptx） | docs/汇报PPT大纲.md |
| 5 分钟汇报稿 + 导师提问清单 | docs/汇报稿.md |
| 论文初稿（框架 + 结果段落） | docs/paper_draft.md |
| 专利交底书初稿 | docs/patent_disclosure_draft.md |
| 软著材料清单与说明 | docs/software_copyright_materials.md |

数字出处与核对：

- 出处表：docs/number_sources.csv，共 72 行（P01—P19 冻结参数；N01—N53 运行结果）。
- 核对脚本：scripts/check_materials_numbers.py（另进程；CSV 按"选择器 + 列"取值比较，JSON 按路径取值，
  findings/日志按原文串匹配）。
- 核对报告：results/materials/U14-v01/number_check.json；人读核对表：docs/number_consistency_table.md。
- 判定：consistency_passed——源值比对全部一致；材料中未登记数字 0 个；未引用行 0 个；标签与数值错位 0 处；
  六份材料的 SHA-256 已登记在报告的 materials 字段。
- 材料内数字采用【ID】标签指回出处表；每个标签所在行必须出现该行数值，否则判错位。

前两轮核对失败记录（保留）：首轮 N41/N42 的 findings 命中串写错、PPT 大纲字号数字未登记；
第二轮 5 处"标签与数值不在同一行"（成本只写在另一句）。均按核对结果修正材料或出处表，未放宽判据。

## C. 稳健性

核对报告按固定随机种子生成 10 行外部抽查清单（编号、数值、出处、选择器、列），供他人换人复核。
**本单元不冒充他人抽查结论**：该 10 项的独立复核尚未由第二人执行，状态为待办。

## D. 登记

材料文件哈希登记在 results/materials/U14-v01/number_check.json 的 materials 字段；
材料本身不进入任何单元的冻结哈希。

## E. 意外发现与规格修订建议

- 口径红线自查已脚本化（构造数据标注、figures 路径存在性、禁用申报书历史数字、inconclusive 表述、
  人工验收待办表述）。建议后续材料单元沿用该检查。
- PPT 仅交付 md 大纲，pptx 排版由用户完成；如需成稿，应另立单元并重新登记图表来源。
- claims.md 目前无登记论断，所有 supported 单元的结论尚未登记为 claims；如需在论文/汇报中作为
  一般性结论引用，应先在 claims.md 登记措辞。
