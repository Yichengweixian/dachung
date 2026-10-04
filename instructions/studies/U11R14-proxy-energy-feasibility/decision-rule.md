---
unit: U11R14
freeze_status: approved_for_freeze
user_approval: continuation_2026-10-04
---

# 冻结判据

范围/design与预算固定，先freeze后实现/求解，未运行verdict=null。主HiGHS3+交叉CBC3，全Optimal；依赖/配置/日期/成员/输入/版本一致，原计数点必须满足带t的LP。两求解器的可行性采用U11R08单次LP闸门：边界/总和残差<=1e-7、通道/t归一化残差<=1e-8；目标差<=1e-8。非唯一w不要求一致，不新增重复或选择更好权重。

证书采用原十进制Fraction，与通用旧certificate算法一致，原生权重到证明权重修复最大<=1e-7、精确上下界间距<=1e-8；近2%边界abs(t-.02)<=1e-8分类uncertain，否则精确上界<=.02且主t<=.02记reachable，精确下界>.02且主t>.02记unreachable，其余uncertain。全部三种子reachable则supported；至少一组严格unreachable则refuted；其余inconclusive。任何非有限、状态/身份/预算/哈希/证书/重建异常即invalid而非数学不可行结论，停止并保留，不覆盖。

独立审计从原CSV重算四通道代理/目标/模型、精确上下界/修复与分类，核对HiGHS进程设置、CBC原生变量/目标/MPS残差（总和/边界<=1e-6、其他<=1e-7，同时原十进制可行性须满足上段更严格闸门）。509个保存源日的物理/成本审计沿用<1e-6，全部诊断指标与CSV读回差<1e-6。审计不调用优化器。依赖在前后不漂移，正式LP数6、调度0。

E/D与成本/缺供只诊断，不参与本轮主判定或选择输出权重。supported仅说明固定新日集合能在本年度输入域达到四通道2%门槛，不说明非唯一minimax权重具有经济/可靠性精度、唯一机制、独立年份/真实电网、跨日SOC或整体项目完成。旧U11R12 refuted、U11R13回顾性supported等保持。
