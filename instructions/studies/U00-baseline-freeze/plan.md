# U00 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录本计划与判据文件 SHA-256；确认 `.gitignore` 覆盖 .venv/、__pycache__/、.cache/、.claude/
- [ ] 0.2 确认 git 可用：`git --version`（Git Bash 或 PowerShell 均可）
- [ ] 0.3 确认 .venv 可用：`.\.venv\Scripts\python.exe --version`
- [ ] 0.4 与用户确认 444.docx 是否入库

## 组1 实现（Codex）

> 你是本项目编程助手。项目根目录为 D:\ADMIN\Desktop\大创第一阶段。现在执行研究单元 U00：建立版本基线与产物清单。先读 `instructions/specs/execution-policy.md` 和 `instructions/studies/U00-baseline-freeze/design.md`，然后：
>
> 1. 在项目根执行 `git init`（本地仓库，不配置远程，不推送）。
> 2. 新建 `scripts/make_baseline_manifest.py`，按 design.md 的清单脚本示例实现：遍历项目根全部文件（排除 .venv/.cache/__pycache__/.claude/.git），计算每个文件 SHA-256，输出 `instructions/baseline_manifest.json`（路径统一正斜杠，JSON 带 ensure_ascii=False）。
> 3. 记录环境：Python 版本、pip 全部包与版本、git 版本，写入 `instructions/baseline_environment.txt`。
> 4. 运行全量测试：`.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`，输出重定向保存为 `instructions/baseline_tests.txt`；有失败必须报告并停止。
> 5. 再运行一次清单脚本，确认两次哈希一致。
> 6. 执行 git add（按 .gitignore 规则）并创建初始提交，提交信息 `U00: baseline freeze`。
> 7. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) git log 有一条初始提交；2) baseline_manifest.json 中文件数与项目根实际文件数一致（排除项内文件除外）；3) baseline_tests.txt 中全部测试 OK；4) 清单两次运行哈希一致；5) 未修改任何既有代码、数据与结果文件（对照组0 冻结哈希）。任何一项失败即停止并报告。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
