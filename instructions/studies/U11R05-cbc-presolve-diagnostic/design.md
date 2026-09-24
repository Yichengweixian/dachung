# U11R05 方法草案（未冻结、未执行）

## 固定输入

唯一模型：results/annual/U11R04-diagnosis-v02/reconstructed.mps。对应N48/seed42主权重计算的lex_035阶段。使用同目录diagnosis.json的原变量名映射与source/输出哈希，冻结原失败JSON、LP、U11R04 manifest与freeze。

该MPS来自原实现和保存解的只读重放，21个LP与原记录逐字节一致，但原求解时的临时MPS未保存，因此仍称“重建模型”。原CBC失败日志为历史对照，不重新运行已失败的默认配置。

## 唯一求解配置变化

使用与U11R04相同的CBC二进制，冻结路径、SHA-256与版本。仍用primalTolerance=1e-9、integerTolerance=1e-9、ratioGap=0、allowableGap=0、threads=0；仅增加presolve=off。该选项已通过本机CBC -presolve?? -quit确认存在，默认on。其他设置及目标均不变，不修改primary/secondary/lex固定带，不改权重上下界，不换优化算法，不升级依赖。

每次独立进程启动，调用模式：cbc reconstructed.mps -primalTolerance 1e-9 -integerTolerance 1e-9 -ratioGap 0 -allowableGap 0 -threads 0 -presolve off -branch -printingOptions all -solution solution.txt -saveSolution solution.bin -quit。每次最长60秒，与现有封装相同；实际可执行路径在冻结时从已安装PuLP解析。

首轮通过全部有效性检查后才独立重复一次；最多2次优化调用，失败立即停，不探测其他参数组合。保存MPS、完整命令、stdout/stderr、退出码、文本及原生二进制解、计时与所有产物哈希；输出新目录，禁止覆盖。

## 结果读取与限制

按现有CBC原生双精度布局读变量，并按MPS变量映射做独立Decimal残差检查。不能将CBC文本解的低精度数字当作正式验收值。记录文本/二进制目标及变量差异，验证变量数/约束数匹配。没有调度MILP调用，没有新年度指标，没有扩大N或换种子。

presolve off成功最多支持该重建实例在此配置下可求解；不证明一般性CBC缺陷、全部原约束严格精确可行、跨平台鲁棒性或整个代表日研究达标。若通过，完整矩阵恢复仍须另定修订执行方案，不能直接补跑U11R04。
