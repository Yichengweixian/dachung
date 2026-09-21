---
unit: U10
status: complete
verdict: supported
rule_commit: null
code_commit: null
run_ids: []
completed_at: null
---

# U10 结果与判定

U10-master-v01：168h完整、通过输入校验，无插补；独立Python进程重复转换CSV字节相同。
原始响应和请求：data/raw/U10-master-v01/；SHA-256见results/real_data/U10-master-v01/run_manifest.json。
辐照度Wh/m²为逐小时量，除1h后用于光伏换算；风速m/s；时区UTC。
四点微扰的风光峰值/均值差均为0，符合冻结阈值，但可能同属源数据网格，不能据此主张空间高精度。
负荷为构造形状，非真实负荷；未使用u10-complete分支。

## A. 有效性闸门

通过，原始响应、单位、168连续时间戳、夜间零出力与重复转换已核对。

## B. 主结果

supported（管线有效性，不是电网模型实证有效性）。

## C. 稳健性

四坐标微扰通过；独立进程复现通过。

## D. 登记

证据见run_manifest.json和robustness.csv；方法见docs/real_weather_data_method_v02.md。无claims。

## E. 意外发现与规格修订建议

执行后填写。
