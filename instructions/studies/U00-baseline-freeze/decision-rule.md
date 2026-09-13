---
unit: U00
freeze_status: draft
freeze_commit: null
freeze_sha256: null
---

# U00 判定规则（执行前冻结，冻结后不得修改）

## A. 有效性闸门

- 运行前：git 与 .venv 可用；本文件与 plan.md 哈希记录在案；444.docx 入库决定已由用户确认。
- 运行后：初始提交存在；清单两次运行哈希一致；未发现既有文件被修改。
- git 不可用或环境损坏 → 单元判 `blocked`（工程状态），verdict `invalid` 并写明原因，不伪造提交。

## B. 主判据

- **supported**：git 初始提交存在 + 清单覆盖项目根全部未排除文件 + 25 项测试全部通过 + 环境记录完整 + 清单可重复。
- **refuted**：测试失败（排除环境原因后）或清单遗漏文件且无法解释。
- **inconclusive**：清单两次运行不一致但原因未查明。
- 未执行：verdict 保持 `null`。

## C. 稳健性

- 清单脚本连续运行两次哈希一致；
- 换 PowerShell 与 Git Bash 分别运行 git 命令均正常。

## D. 论断映射

exploratory，不登记 claims。

## E. 禁止事后修改

冻结后不得修改：排除目录集合、清单输出位置、测试命令；444.docx 入库决定冻结后不反转。
