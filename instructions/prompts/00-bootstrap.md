# 初始化与开工核对

适用全局策略：[execution-policy.md](../specs/execution-policy.md)。代码一律由 Codex 编写（用户手动粘贴），Claude 只读审查；一次只推进一个单元。

以下为开工时使用的提示词；执行前先人工核对 Windows 环境（.venv 可用、路径相对项目根）。

> 你是本项目编程助手。项目为"高比例新能源电力电量平衡与储能容量-功率协同优化配置"研究，工程根目录为 D:\ADMIN\Desktop\大创第一阶段（下称项目根），说明包位于项目根下 instructions/。
>
> 第一步只读核对，不写代码：
> 1. 读 instructions/README.md、specs/roadmap.md、specs/execution-policy.md。
> 2. 核对 Windows 环境：在项目根运行 `\.venv\Scripts\python.exe --version` 与 `\.venv\Scripts\python.exe -m pip list`，确认 numpy/pandas/matplotlib 可用。
> 3. 运行 `\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v`，记录现有测试全过。
> 4. 只对"缺失且阻塞"的事项提出具体问题，同时推进不依赖的部分。
>
> 核对完成后先建立 U00 的冻结记录（输入与产物 SHA-256、参数快照、环境版本），再按 U00/plan.md 执行。完成后停止，等待用户指令。
