# U00 当前环境修订与冻结

用户于本轮明确同意：适配当前 Linux 环境、保留原始提交和重跑差异、仅本地完成 U00、不推送 GitHub。本文优先于原 Windows 操作示例；提示词原文不修改。

## 冻结判据

- 使用当前 Python 解释器，不声称验证了用户 Windows .venv。记录 Python、平台、pip 全量包、git 版本。
- 保留既有初始提交 df5b172d2f11166614fa81bdba6f7dbba5fccf45，不重新 git init，不变更远程，不推送。
- 444.docx 已在初始提交中，继续保留且只读。
- U00 开始时已有重跑变化：保存原提交到当前文件的二进制补丁及逐文件 SHA-256；这些变化不计为 U00 新增修改。
- 保护 U00 开始时的所有既有文件内容，除本单元计划、判据及状态登记文档外，不修改代码、配置、数据、结果、图片和申请书。
- 清单覆盖全部文件；排除目录 .git、.venv、.cache、__pycache__、.claude；仅额外排除清单自身 instructions/baseline_manifest.json。清单不含动态时间戳。
- 环境、测试和状态记录全部写完后连续生成清单两次，字节哈希必须一致，并独立核对覆盖集合及每个文件哈希。
- 测试命令固定为当前解释器运行 `-m unittest discover -s tests -p test_*.py -v`，必须正好25项全部通过。
- supported：既有初始提交存在、环境记录成功、25项测试通过、保护文件未变、清单完整且稳定；测试/保护检查失败为 invalid；无法解释清单差异为 inconclusive。
- 不执行 PowerShell/Git Bash 交叉验证，记为未验证的平台兼容性，而非成功。
- 本次仅工程基线判定，不登记科研 claims。完成后停止，不进入 U06。

冻结证据：本文与原 decision-rule.md、plan.md、design.md 的 SHA-256 保存到 baseline_freeze.json。生成冻结记录后不得修改本文。
