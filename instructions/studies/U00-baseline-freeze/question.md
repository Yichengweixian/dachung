---
unit: U00
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：版本基线与产物清单冻结

## 要回答的可判定问题

项目当前是否具备可追溯的版本基线（本地 git 仓库）与完整产物清单（全部代码、配置、数据、结果、图、文档文件及其 SHA-256）？现有 25 项测试在当前环境下是否全部通过？

## 上游证据

- 项目现状：根目录现有 `src/`、`config/`、`data/`、`results/`、`figures/`、`docs/`、`tests/` 及 6 个运行入口
- 历史测试声明：docs 各阶段分析文档记载的测试数量与结果

## 范围

- 只建立版本基线与清单，不修改任何项目代码、数据或结果
- git 为**本地仓库**，不配置远程、不推送到任何平台
- 444.docx 加入仓库但只读（或用 .gitignore 排除大二进制，由用户决定）

## 预期结果与可能作废原因

- 预期：git init 成功；清单脚本可重复运行且哈希稳定；25 项测试全过
- 可能 invalid：环境异常（git 不可用、.venv 损坏）、清单遗漏文件、测试失败且非环境原因
