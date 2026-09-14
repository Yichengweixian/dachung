# U09前置条件与网格计数修订（冻结前）

U09草案原要求 U07 整体 supported，但事后复核的正确状态是：U06 supported；U07 独立数值验证 supported、旧归因设计 invalid；U07R supported。U09 只依赖调度模型的数值有效性和经济评价，不依赖 U07 旧归因公式。因此前置条件冻结为 U06 supported + U07 独立数值审计 supported + U07R supported，不改写 U07 历史。

草案设计中的组合总数有算术错误：E=0,P=0 为 1 个；10 个正容量与 10 个正功率组合为 100 个；总数是 101，不是 111。候选值、步长、组合规则和研究方向均未改变。

同时将“严格内部”统一为 0<E<100 且 5<P<50；P=5 与 P=50 均是功率网格边界。本文与 question/design/plan/decision-rule、网格配置、输入及参数一并在首次求解前冻结。
