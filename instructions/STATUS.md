# 当前状态

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
