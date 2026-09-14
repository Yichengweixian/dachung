# U10 NASA POWER 168 小时数据管线运行说明

本实现对应 `instructions/studies/U10-nasa-power/` 已冻结的五份文档。它只生成风光可用出力；`load` 使用现有 24 小时构造负荷形状的七天循环，因而始终是“构造负荷，非真实负荷”。不运行调度、优化或绘图。

## 入口与产物

`scripts/download_nasa_power.py` 是参数化下载入口，固定保护端点、变量、地点和日期，不能以参数改写冻结规格。它接受 `--run-id`、`--raw-root` 和 `--timeout-seconds`；`--dry-run` 只打印完整 URL，绝不联网或写文件。成功下载时，原始字节、请求元数据和 SHA-256 写入 `data/raw/U10-<UTC运行ID>/`。

`run_real_data.py` 是未来获准联网时的完整入口：下载成功后调用 `src/weather_pipeline.py`，将已保存的原始响应转换为 `data/processed/input_168h.csv`，并保留带运行 ID 的 CSV、副本质量报告和 run-manifest。它不是本次执行的一部分。

若已经有经过审计的原始 JSON，可在 Python 中只离线调用：

```python
from pathlib import Path
from src.weather_pipeline import convert_saved_response

convert_saved_response(Path("data/raw/U10-.../nasa_power_hourly_wuhan_20200101_20200107_utc.json"), "U10-...")
```

## 固定规则

- 请求使用 NASA POWER `temporal/hourly/point`，`ALLSKY_SFC_SW_DWN,WS50M`，武汉 `(30.5900, 114.3000)`，UTC `2020-01-01T00:00Z` 至 `2020-01-07T23:00Z`（168 条）。
- JSON 时间键先按 UTC `YYYYMMDDHH` 解析，再映射至 `hour=0…167`；`Asia/Shanghai` 只作审计显示，绝不参与截取。
- `WS50M`（m/s）按冻结的 3/12/25 m/s 曲线转换为 0–100 MW；`ALLSKY_SFC_SW_DWN`（逐小时间隔 Wh/m²）按 1000 Wh/m²/h 基准转换为 0–150 MW。
- 必需变量不接受 `-999`、空值、NaN、Inf、缺时、重复时、非整点、负值、风速大于 75 m/s 或辐照度大于 1500 Wh/m²/h。程序不插补、删重、裁剪或换日期。
- 只有通过 `validate_input_data(..., num_steps=168, time_step_hours=1.0)` 的 CSV 才会成为规范输入；同一原始文件重跑必须得到相同 CSV SHA-256。

## 离线最小测试

测试使用构造的内存 JSON，因此不下载数据、不产生项目数据产物：

```powershell
python -m unittest tests.test_u10_nasa_power -v
```

它验证 168 个连续 UTC 时点、构造负荷七天系数、风机边界、零辐照度光伏、缺失时间键和 JSON 重复键拒绝。网络/API 失败时下载脚本只保存失败请求元数据并停止；真实运行的 verdict 必须仍按 `decision-rule.md` 填写，不由本说明推断。
