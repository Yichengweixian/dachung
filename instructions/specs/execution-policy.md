# 执行策略：谁写码、谁审查、怎么推进

## 分工

| 角色 | 职责 |
|---|---|
| **Codex**（用户手动粘贴提示词） | 全部代码编写、依赖安装、运行与自查、结果登记。一次只执行一个单元的一个任务组 |
| **Claude**（本会话） | 只读审查：判据是否冻结、证据是否完整、结果是否可复现、差异归因是否成立；同时负责向用户讲解代码 |
| **用户（何柄初）** | 判据定稿、冻结确认、审阅结果、向导师汇报 |
| 团队成员 | 黄哲皓：数据与场景（U08/U10 输入）；杨骏盛伟：编程执行；龚正：文献与结果分析 |

## Windows 环境约定（所有提示词与文档统一遵守）

- 项目根 = `D:\ADMIN\Desktop\大创第一阶段`（含 src/、config/、data/、results/、figures/、docs/、tests/）；说明包根 = 其下 `instructions/`。提示词与代码一律使用**项目内相对路径**，不写死盘符。
- Python：`.\.venv\Scripts\python.exe`（PowerShell 语法，不激活虚拟环境，不修改执行策略）。
- 文件读写一律显式 `encoding="utf-8"`；Windows 控制台输出乱码不影响文件内容正确性，以文件为准。
- 哈希一律用 Python `hashlib.sha256`（脚本示例见 U00/design.md），不使用 shasum/md5 等 Unix 工具。
- 依赖变更：新增包必须记录版本并写入 `requirements.txt`；本包不引入任何定时任务、调度器或 macOS/Unix 专属机制——所有执行由人工按单元手动触发。
- Git 命令在 Git Bash 或 PowerShell 中均可用；U00 负责初始化本地仓库（无远程）。

## 推进流程（一次一单元）

1. 用户与 Claude 定稿单元五文件（question/design/plan/decision-rule/findings），**冻结 decision-rule**（记录输入哈希与参数快照）。
2. 用户把 plan.md 组1 提示词粘贴给 Codex 执行；组2 自查；Claude 按 prompts/03-audit.md 审计。
3. findings/RUNLOG/STATUS/roadmap/claims 收尾更新；**完成后停止**，等用户指令进入下一单元。

## 红线（Codex 违反即判定单元 invalid）

1. 为匹配申报书数字（84.63%、87.08%、308680 元等）修改数据、参数或口径；
2. 求解器非 Optimal 仍输出图表或结论；
3. 把构造数据描述为真实电网数据；
4. 批量删除文件；修改 444.docx 或提示词原文；
5. 跳过组0 冻结直接实现；冻结后修改判据、阈值、场景或候选；
6. 一个单元未收尾就自动开始下一单元。
