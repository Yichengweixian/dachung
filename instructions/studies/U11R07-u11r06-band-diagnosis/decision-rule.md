---
unit: U11R07
freeze_status: approved_for_freeze
user_approval: continuation_2026-09-26_read_only_diagnosis
---

# U11R07 判据

成功的诊断必须满足：U11R06 所有登记的来源/产物哈希一致、源码无漂移；重放的每个 LP 与保存文件逐字节同哈希，准确停在 `N24_seed42_main_lex_014`；零新增优化器或外部 CBC 进程；Decimal 对内存模型与 MPS 全部约束及变量界限读回完成，记录最大残差、具体行、固定区间、系数与 RHS 写出差。

诊断符合上述条件时，工程 complete；如果可证明简单权重区间矛盾、原模型明确的算术矛盾或确切序列化错误，则只报告被证实的局部原因。否则结论为 `inconclusive`（原因尚未证实），不得以容差量级、solver 日志或近似可行解宣称严格数学可行/不可行或 CBC 缺陷。哈希/重放/禁止求解闸门失败为 invalid。此单元不评价 E/D 研究门槛，也不升级 U11R06 判定。

冻结后不得补入新的求解器设置、放宽约束或重跑失败 LP；任何这样的数值实验须独立单元先定规则。
