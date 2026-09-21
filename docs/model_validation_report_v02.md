# master 调度验证 v02

## 方法边界

原始U06连续LP允许同小时充放电。U06-master-v01虽然Optimal且守恒残差合格，但11个小时同时充放电，违反原判据。
完整失败结果和原始源码保留在results/optimization/U06-master-v01/，不改成成功。
U06R01按独立冻结规则增加二元互斥变量，模型是MILP，不再称连续LP。最低火电、爬坡和期末电量归位均显式建模。
互斥只禁止同一时段同时充放电，不禁止不同小时的循环。存在弃电惩罚和效率损耗时，跨时段循环可能是成本最优行为。

## 求解精度

CBC普通文本solution仅给有限小数位，直接读取可能不满足1e-6审计。
src/cbc_full_precision.py保留CBC原生二进制double精度，核对矩阵维度、文件长度、变量有限性和目标一致性。
Windows CBC串行threads=0，临时目录中相对路径输出；不通过放宽物理判据接受解。
零容量SOC为未定义NaN，不被当作零SOC。

## 验证证据

U06R01-v03的主例、约束对照、半小时、零储能和零风光共7次全部Optimal；最大残差7.37365724035044e-12。
U07R01-v01包含最低火电/爬坡/期末归位三因素的8种组合、反序8次、4小时手算例，共17次。
独立标准库审计脚本scripts/independent_dispatch_audit.py不引用优化模型；单独Python进程读回CSV并核对。
组合反序差0，Shapley归因加方法差与总差闭合，最大闭合误差1.4551915228366852e-11。
证据分别见results/optimization/U06R01-v03/run_manifest.json、results/validation/U07R01-v01/{combinations,shapley,closure}.csv。

归因仅解释当前模型和构造算例，不是电力系统实际因果效应。
规则法与MILP的约束不同，不能把全部成本差说成算法本身的改进。
历史U01—U05为历史基线，判据事后整理；本批新增实验先冻结后执行。未登记普适claims。
