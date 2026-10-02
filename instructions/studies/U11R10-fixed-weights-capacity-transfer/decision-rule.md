---
unit: U11R10
freeze_status: approved_for_freeze
user_approval: continuation_2026-10-02
---

# 冻结判据

先冻结再实现/求解。固定 N=48、seed=[42,7,2026]、场景 E0_P0/E80_P20、已保存 effective_days，1020 次 MILP、0 次权重 LP，不据新结果重新选取代表日/权重/容量。

有效性：前置只读审计通过，所有冻结 SHA-256 匹配；原 configuration 物理/经济参数与 U11R08B 冻结配置一致。每组代表日48个、不重复、属于保存簇，标签覆盖365天，counts与days相等，weights有限且和365及0.5c至2c界限残差<=1e-6，主/重复权重保持原值。全部新求解 Optimal（MILP互斥），物理残差<1e-6；另进程重建保存的日成本/各年度指标差<1e-6；两次重复的全部有限汇总指标差<1e-6。预算和组数完整，源文件在正式运行中不漂移。

E=max(代表日与对应容量全年基准的消纳率绝对差、弃电率绝对差)，单位百分点；D=load/wind/solar年度输入电量最大绝对相对误差。输入分母为0时两端均0记0，否则invalid。研究门槛仍 E<=1.0、D<=0.02，不附加数值容差。

全部六个新配置/种子组通过，complete/supported，仅支持固定权重在这两个已注册同年度配置间迁移；完整有效而任一组不通过，complete/inconclusive。不补容量、种子或候选。非Optimal、物理/审计/数据/预算异常立即停止，blocked/invalid；环境缺失且未求解为blocked/null。未运行verdict=null。独立审计失败则不以runner的complete单独宣称成功。

成本与缺供误差只诊断；比例互补不是两个独立指标，D沿用样本内拟合结果，不变成样本外输入验证。不能推导跨年、独立真实电网、极端日、跨日储能、容量寻优成本精度或一般可靠性。U11R08B及其他历史判定保持原样；修订缘由登记本单元与roadmap，避免改动被后续冻结引用的历史findings。
