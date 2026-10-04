# 固定设计

annual任务组，2023年8760h原输入，固定U11R12-v01的N48代表日与U11R08B原簇成员/计数，种子按42/7/2026。不重新选日、聚类或缩放曲线，不使用保存成本/缺供作为拟合目标。第四通道p_d=sum_h max(load-wind-solar-120MW,0)*1h，与R12选日代理一致；全年目标为365个实际日p之和，其并非真实缺供，忽略储能/爬坡/下限。

每种子一个minimax LP：min t>=0，0.5c_i<=w_i<=2c_i、sum w_i=365，对四通道目标T_k>0设置abs(sum a_ki*w_i/T_k-1)<=t。目标为0时要求代表输入全部0，误差为0。原w=c、t为其最大偏差是可行性预检点。无次级目标/字典序/固定带/新的调度MILP。本轮第四通道使用同样2%探索性保真门槛，不修改历史三通道2%或E1个百分点标准。

三个主LP使用现有scipy.optimize.linprog(method='highs-ds')，primal/dual feasibility tolerance 1e-9、presolve=True、time_limit=60、独立子进程完整日志及process信息。另三个CBC交叉LP使用现有EvidenceCBC原生双精度留证，presolve off、primal/integerTolerance1e-9、原gap/threads设置不变。总6 LP，0新调度，无失败后更换求解器补考。目标差<=1e-8；非唯一权重不要求两个求解器一致。

精确证书沿用U11R08的通道数无关certificate：从原CSV十进制Fraction重算4通道，依据HiGHS对偶构造严格弱对偶下界，原权重仅用于证明的有理数边界投影与总和修复得上界，修复<=1e-7，不替换主权重；保存有理数上下界/间距、证明权重和对偶。CBC原生变量/MPS和主LP模型系数另进程核对。

仅补充诊断：对两求解器权重分别用已保存的R12日输出加权，报告E、年度成本/缺供及其偏差，0新调度；指标不参与拟合/主判定。保留非唯一权重的两套不同结果，不挑选较好解。数据为NASA气象转换+构造负荷/示例成本，非真实电网数据。

固定环境numpy2.5.3、pandas3.0.5、scipy1.18.1、pulp3.3.0；沿用本地已有运行时和CBC，不安装/升级依赖。
