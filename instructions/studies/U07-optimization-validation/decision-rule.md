---
unit: U07
freeze_status: draft
freeze_commit: null
freeze_sha256: null
---

# U07 判定规则（执行前冻结，冻结后不得修改）

## A. 有效性闸门

- 运行前：U06 verdict 为 supported；U06 输出 SHA-256 与冻结记录一致；本文件哈希记录在案。
- 检查脚本 import 了模型校验函数 → 判 `invalid`（自查自证）。
- 对照时输入、参数、代码版本与 U06 一致（以 U06 run_manifest.json 为准）。

## B. 主判据（互斥，执行前已定）

- **supported**：6 项独立检查全部通过 + oracle 逐值通过 + 三因素归因的未解释残差 < 5% 的 U06−U05 总差异（按消纳率百分点计）。
- **refuted**：任一检查失败且不是检查脚本自身错误；或 oracle 不一致。
- **inconclusive**：检查通过但归因残差 ≥ 5% 且原因未查明。
- 未执行：verdict 保持 `null`。

## C. 稳健性

- 0.5h 步长与零储能、零新能源变体沿用 U06 稳健性结果，此处仅复算对照；
- 独立检查脚本换一台机器/新终端重跑结果一致（可复现）。

## D. 论断映射

exploratory，不登记 claims。

## E. 禁止事后修改

冻结后不得修改：检查阈值（1e-6、30、20 等）、归因公式、对照基线行（E40_P20）、判据本身。需要改变 → 新建单元。
