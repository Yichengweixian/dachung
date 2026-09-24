---
unit: U11R04
status: blocked
verdict: null
run_ids: []
---

# 当前记录（2026-09-24）

用户选择继续研究、不做PPT。已根据U11R03保存结果及src/representative_days.py准备受限电量校准权重的五份草案。

已确认的代码事实：现有权重取簇成员天数，不强制匹配全年三通道输入电量。旧结果9组最大输入电量误差均来自wind，且均超过2%，见results/annual/U11R03-v01/comparison.csv。尚未验证新方法可行效果，不能保证通过。

待用户确认新权重边界、层级LP方法及完整判据。无freeze.json，无新模型实现，无新数值实验，无run_manifest；设计预算不是实际求解次数。旧U11R03及U12R02判定不变。

外部换人材料抽查和U00正式基线未决项不因本草案完成而关闭。整体项目尚不能宣称研究全部完成。

## 2026-09-24 用户确认后的冻结前核验

用户明确同意原草案的方法、权重范围和判据，审批不再是阻塞。当前status=blocked、verdict=null：新实验尚未开始，不能把前置审计失败记作权重方法被反驳。

实际执行scripts/audit_representative_days.py U11R03-v01时，在源码漂移闸门退出，未进入该脚本的物理重审环节。错误仅指向scripts/check_materials_numbers.py；requested输出文件未生成。完整退出信息保存于results/annual/U11R04-preflight-v01/failure.json。

随后独立执行scripts/audit_study_artifacts.py，只读核对两份manifest：U11R02的893项哈希/425个已保存求解状态、U11R03的561项哈希/252个已保存求解状态通过。后者仍报告一项源码漂移。此检查不等于本轮完成逐时物理与成本重审。

根因证据：git show 41f1ea0 -- scripts/check_materials_numbers.py显示T4增加独立材料路径及防覆盖功能；rg检查调度、聚类与审计入口未发现该材料检查器调用。它被StudyRun全量scripts源码快照纳入旧manifest，因而触发严格零漂移条件；现有证据未显示计算模型或结果损坏。旧manifest与审计器均未改写，没有忽略漂移继续运行。

依plan组1“冻结前异常只报告，不进入新实验”，本轮停止于此。建议后续在隔离历史代码副本中重审旧基准，保留当前T4代码；若需要例外放行，应先明确审计范围，不能静默改闸门。原研究方法、1个百分点/2%门槛和0.5至2倍权重范围保持已确认，不需要重新确认同一方案。
