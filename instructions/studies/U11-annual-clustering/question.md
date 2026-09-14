---
unit: U11
mode: exploratory
branch: null
opened: null
closed: null
status: not_started
verdict: null
---

# 单元问题：8760 小时全年仿真与 k-means 典型日聚类

## 要回答的可判定问题

用 k-means 把 8760 小时风光荷数据聚为 N 个典型日（含权重）后，加权年度仿真得到的年度消纳率、弃电率，与"逐日独立 LP 全年合计"（365 个 24h 日，日间 SOC 不跨天）的误差是否在 ±1 个百分点以内？

## 上游证据

U10（真实气象数据管线与转换模型）、U06（LP 模型）、specs/methods.md

## 范围

- 只做聚类与年度仿真对照，不做 (E,P) 寻优（那是 U09 在年度尺度的后续扩展，进 Backlog）
- 全年口径统一为"逐日独立 LP 串联"（日初 SOC=0.5、日末归位），聚类与全仿真使用同一口径，误差只反映聚类近似本身
- 不登记 claims（exploratory）

## 预期结果与可能作废原因

- 预期：N=10 左右误差 <1 个百分点；聚类能保留"晴/阴/大风"等典型形态
- 可能 invalid：全年数据不完整；聚类与全仿真口径不一致；种子未固定导致不可复现
