---
unit: U00
status: in_progress
verdict: null
rule_commit: null
code_commit: null
run_ids: [U00-T1-v01, U00-T1-v02, U00-T1-v03]
completed_at: null
---

# U00 结果与判定

2026-09-17执行T1非提交补证。原判据及计划未改，哈希冻结于freeze.json。
U00仍为partial（正式验收未全部完成），verdict=null；不将辅助检查等同于原U00 supported。

## A. 有效性闸门

Git和项目虚拟环境可用，既有HEAD为003a014ffa95a465cb2a0f0fb5874d2ccb75580f。
444.docx已在原仓库被跟踪，本轮未改变文件及跟踪状态；原流程的用户入库确认不由机器检查代替。

## B. 主结果

U00-T1-v02：10838个既有工作区文件、10568个results文件，连续两遍SHA-256一致；47项测试通过。
环境、源码与冻结哈希、两种终端的Git输出均存于results/baseline/U00-T1-v02/。
最终台账登记及产物归属补齐后另取U00-T1-v03快照；其实际计数、测试与通过状态以该run_manifest.json为准，不回写旧快照。

## C. 稳健性

v02采集后另一次 --verify 核对：added/missing/changed均为空；Git HEAD与索引/工作区状态未被采集程序改变（仅新增本轮输出）。
后续台账登记会造成v02快照的预期差异，最终复核请使用v03快照；不能把登记后的旧快照差异误报为研究产物损坏。

## D. 登记

新增scripts/make_baseline_manifest.py、tests/test_baseline_manifest.py、execution-note-20260917.md、freeze.json及版本化results/baseline/证据。
artifacts.csv/json分别列出历史run判定与当前findings判定，不覆盖人工验收之前的机器记录。跨单元审计、基础占位文件单独分类。无claims。

## E. 意外发现与规格修订建议

v01串行小文件采集耗时过长，在首遍完成后中止；已有快照和环境文件以及failure.json保留。v02改为有界并发读取，并使Git状态前后比较均扣除本轮新增输出目录，检查标准未放宽。
正式待办：当前工作区的基线提交未授权；444.docx入库确认需补充；原清单自包含/输出路径口径需明确。当前快照采用采集时点语义，本轮输出的哈希另记于run_manifest，不伪造包含自身最终哈希的清单。
