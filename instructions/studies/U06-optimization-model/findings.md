---
unit: U06
status: complete
verdict: supported
rule_commit: null
code_commit: null
run_ids: [U06-20260913-01, U06-20260913-02]
completed_at: 2026-09-13
---

# U06 结果与判定

## 02重跑与最终判定（下方01失败过程保留）

用户指示继续定位和修复。冻结判据、输入和参数未改，仅将CBC文本解读取改为同次求解的原始双精度二进制解读取。根因为文本舍入；无截断或投影、未放宽容差。
02全部7场景Optimal、全部约束及CSV读回验证通过，最大残差7.37099270509134e-12 MW/MWh。28项测试通过（25项原测试+3项手算/精度回归及破坏检测/不可行拒绝）。
最终supported仅表示本探索单元通过。01仍为invalid，保留原目录和failure.json；U07尚未执行，不登记科研claims。
主场景成本484525.190859元，消纳率81.8231006%，失负荷0。顺序归因见02/attribution.csv，成本口径与限制见docs/optimization_model.md。
证据：results/optimization/U06-20260913-02/run_manifest.json记录环境、源码哈希、冻结配置、CBC文本解/日志及每项残差；tests/test_optimization.py为回归测试。

已按用户批准的 milp-amendment.md 实现并运行；未通过全部验收。冻结内容见freeze.json。保留原设计文本，不更改容差。

## A. 有效性闸门

运行前25项测试通过，冻结输入和配置校验通过。40MWh主场景、顺序归因变体、半小时和零储能均通过存盘前后检查。零新能源场景返回Optimal，但独立校验测得功率平衡残差5.000000001587068e-6 MW，违反严格小于1e-6要求，已立即停止。U06整体判invalid，不登记成功论断。

## B. 主结果

主场景与归因逐时CSV为部分执行证据，不能代表U06整体验收成功。没有生成正式summary.csv及成功run_manifest.json。失败详情见results/optimization/U06-20260913-01/failure.json。

## C. 稳健性

dt=0.5和E=P=0已通过；零新能源未通过。尚未进入U07，没有宣称完成优化模型独立测试套件。

## D. 登记

脚本：run_optimization.py、src/optimization_model.py、src/optimization_validation.py；参数与原判据哈希：freeze.json；依赖PuLP 3.3.0。失败记录与部分结果已保留，未推送。

## E. 与规则调度的差异归因

预定顺序：规则→同物理边界MILP→最小出力→爬坡→期末归位。逐步增量见attribution.csv，数值加和已核对；结果为顺序相关，不是独立因果贡献。整体验证未通过，暂不作为正式项目结论。

## F. 意外发现与规格修订建议

下一步应调查CBC文本解精度和原始约束残差；目前未证实误差根因。不得提高容差、截断输出或覆盖失败结果来宣称通过。未开始U07。
