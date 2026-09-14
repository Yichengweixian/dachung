---
unit: U00
status: complete
verdict: supported
rule_commit: null
code_commit: null
run_ids: [U00-baseline-20260913-01]
completed_at: 2026-09-13
---

# U00 结果与判定

依据用户批准的 current-environment-amendment.md 执行。原 Windows 计划保留，冻结文件哈希见 instructions/baseline_freeze.json。rule_commit/code_commit 不虚构自引用，收尾提交由 git log 定位。

## A. 有效性闸门

当前Python、git及环境清单获取成功；25项测试全部通过。冻结规则与受保护文件在运行前后哈希一致。原始提交及本轮开始前的11个重跑变化均保留。

## B. 主结果

supported：工程基线已建立，不是优化研究结果。完整清单在登记后生成，覆盖和两次重复生成检查由 scripts/make_baseline_manifest.py manifest 执行；检查失败不得提交本判定。

## C. 稳健性

清单排除自身，逐文件验证SHA-256及覆盖集合；当前Linux环境测试通过。Windows .venv、PowerShell/Git Bash未验证。

## D. 登记

原始提交：df5b172d2f11166614fa81bdba6f7dbba5fccf45。
产物：instructions/baseline_freeze.json、baseline_manifest.json、baseline_environment.txt、baseline_tests.txt、baseline_preexisting_changes.patch。
脚本：scripts/make_baseline_manifest.py。清单自哈希不写入被清单包含的文件，避免递归依赖。
本单元不登记科研claims，不修改原模型，不进入U06，未推送GitHub。

## E. 意外发现与规格修订建议

已有变化包括8张图片、2份运行记录和经济表末位浮点差异；原记录输入哈希与当前文件字节不一致，未篡改历史记录或将其解释为已验证。详见保留补丁及roadmap Backlog。
