# 大创项目 · 研究规格驱动执行说明包（Research-SDD）

本包把大创项目"高比例新能源电力电量平衡与储能容量-功率协同优化配置"从口头阶段计划升级为**规格驱动的执行包**：每个阶段对应一个研究单元，判据先冻结再实现，提示词可直接粘贴给 Codex 执行，结果由 Claude（本会话）审查并教学。

建立日期：2026-09-12。当前项目已由 Codex 完成第 1—6 阶段（构造数据、无储能平衡、固定储能调度、容量敏感性、经济性评价），本包将已完成部分登记为基线证据（U01—U05），重点细化剩余阶段（U06—U14）。

## 从哪里开始

1. 读 [执行策略](specs/execution-policy.md)（谁写码、谁审查、一次推进多少）。
2. 读 [研究问题](specs/question.md) 与 [总路线](specs/roadmap.md)，确认单元编号与依赖。
3. 从 **U00（基线冻结）** 开始：为项目建立版本基线与产物清单，再进入 U06。
4. 每执行一个单元：先按 `prompts/01-study-spec.md` 从 `studies/_TEMPLATE/` 建齐五文件并**冻结 decision-rule**，再按 `prompts/02-implement.md` 把 `plan.md` 的提示词粘贴给 Codex。
5. 单元完成后按 `prompts/03-audit.md`（Claude 审查）与 `prompts/04-replan.md`（收尾）更新 `findings.md`、`RUNLOG.md`、`STATUS.md`、`specs/roadmap.md` 及符合条件的 `specs/claims.md`。

## 目录

```text
instructions/
  README.md                  阅读与执行入口
  AGENTS.md                  Codex 与人工共同遵守的十条执行纪律
  STATUS.md / RUNLOG.md      当前状态表与追加式执行记录
  specs/
    question.md              研究问题、系统组成、边界
    data.md                  数据字典摘要；细节指向项目 docs/
    methods.md               方法路线与指标口径；细节指向项目 docs/
    claims.md                论断登记规则与登记表
    roadmap.md               单元总路线、依赖、最小汇报路径、Backlog
    execution-policy.md      Codex 写码 / Claude 审查 / 人工成员的分工与流程
  studies/                   U00—U14 研究单元（五文件制）
    _TEMPLATE/               question / design / plan / decision-rule / findings 模板
  prompts/                   初始化、单元规格、实现、审计、重规划五个提示词
```

项目代码与数据仍位于本目录上级（`src/`、`config/`、`data/`、`results/`、`figures/`、`docs/`、`tests/`），本包不移动任何已有文件。

## 单元总览与最小路线

| 单元 | 内容 | 状态 |
|---|---|---|
| U00 | 版本基线与产物清单冻结 | not_started |
| U01—U05 | 第 1—6 阶段已完成工作（构造数据/无储能/储能/容量敏感性/经济性） | 基线登记 |
| U06 | 时序优化模型（LP）：火电最小出力、爬坡、期末 SOC 归位 | not_started |
| U07 | 优化模型独立验证与规则调度对照 | not_started |
| U08 | 新能源渗透率场景矩阵（4 系数 × 3 储能） | not_started |
| U09 | 储能容量-功率网格搜索（E×P） | not_started |
| U10 | 真实气象数据管线（NASA POWER → 168h 输入） | not_started |
| U11 | 8760 小时全年仿真与 k-means 典型日聚类 | not_started |
| U12 | 遗传算法/粒子群增强（可选） | not_started |
| U13 | 决策软件原型（Streamlit） | not_started |
| U14 | 成果凝练（报告/PPT/论文初稿/专利交底书） | not_started |

**汇报最小路线**：U00 → U06 → U07 → U08（拿到"优化模型 + 渗透率矩阵"即可支撑一次像样的阶段汇报）。
**完整路线**：继续 U09（核心创新点）→ U10/U11（真实数据与全年尺度）→ U12 → U13 → U14。

## 使用边界

- 本包只定义未来工作。未执行单元一律 `verdict: null`；不得把规划路径、示范提示词、勾选项当作已完成事实。
- U01—U05 的判据为事后整理，仅作**基线证据**，不进入 claims；claims 只登记"判据冻结后 confirmatory supported"的结果。
- `444.docx` 为最终申请书，只读；构造数据必须标注"构造算例"，不得描述为真实电网数据。
- 不得为匹配申报书中的任何数字（如 84.63%、87.08%）修改数据、参数或口径。
