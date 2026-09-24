---
unit: U11R05
mode: exploratory
status: not_started
verdict: null
---

# 单模型数值诊断草案（待确认）

U11R04在N48/seed42的lex_035阶段被CBC判Infeasible，已按规则停止。只读重放排除了简单边界交叉与重放不一致，但没有证明完整可行性或根因。

问题：保持这个失败模型的全部系数、固定带及求解容差不变，仅关闭CBC presolve，能否得到可复核、可重复的Optimal解？

这是数值诊断，不是代表日精度研究，不替代U11R04的完整9组矩阵，不改其invalid，不登记claims。
