# 执行计划模板（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工 + 只读核对）

- [ ] 0.1 记录输入文件 SHA-256（用 `hashlib`，示例见 U00/design.md）、参数快照、本计划与判据文件哈希
- [ ] 0.2 核对 `.venv` 可用：`.\.venv\Scripts\python.exe --version`
- [ ] 0.3 核对上游证据文件存在且与本设计一致
- [ ] 0.4 确认 decision-rule.md 已冻结（freeze_status: frozen + 哈希）

## 组1 实现（Codex）

> （填写可直接粘贴的完整提示词：角色背景、先读文件清单、任务步骤、参数与输出路径、禁止事项、完成后停止）

## 组2 自查（Codex，组1通过后发送）

> （填写逐项数值检查清单，每项附阈值；任何一项失败即停止并报告）

## 组3 判定与登记（Codex 汇总，Claude 审查）

- [ ] 按 decision-rule 逐条判定，写入 findings.md
- [ ] 追加 RUNLOG.md，更新 STATUS.md、specs/roadmap.md，适用时登记 claims
- [ ] 完成后停止，等用户指令；不得自动进入下一单元
