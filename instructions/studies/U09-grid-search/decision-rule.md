---
unit: U09
freeze_status: draft
freeze_commit: null
freeze_sha256: null
---

# U09 判定规则（执行前冻结，冻结后不得修改）

## A. 有效性闸门

- 运行前：U07 verdict = supported；网格定义、economics.json、输入与冻结记录一致；评价函数与 U05 为同一实现。
- 运行后：111 个组合全部 Optimal（个别组合异常须逐个报告，不得静默排除）；最优组合通过 U06/U07 全部检查。
- 任一组合非 Optimal 且未查明原因 → 判 `invalid`。

## B. 主判据（互斥，执行前已定）

- **supported**：全部组合 Optimal；最优组合 (E\*,P\*) 满足 0<E\*<100 且 5≤P\*≤50（**严格内部**）；且最优组合各项约束检查通过。
- **inconclusive**：全部 Optimal 但最优组合落在网格边界（E\*=0、E\*=100、P\*=50 之一）；如实记录边界方向，扩网格另开单元。
- **refuted**：求解大面积失败或约束违反且无法解释。
- 未执行：verdict 保持 `null`。

## C. 稳健性

- 用第二组成本参数（如 energy_capex 800→1200 元/kWh、power_capex 300→500 元/kW，其余不变）重跑全网格：(E\*,P\*) 应朝容量/功率更小的方向移动或保持；移动方向相反须解释。
- 全网格重跑一次结果逐行一致（确定性）。

## D. 论断映射

exploratory，不登记 claims。

## E. 禁止事后修改

冻结后不得修改：网格档位与组合规则、成本参数、目标函数构成、判据本身。需要改变 → 新建单元。
