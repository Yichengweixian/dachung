# U10 设计：NASA POWER 至 168h 输入

## 获取、留档与命名

唯一允许的请求是 `question.md` 冻结的 HTTPS GET 端点和参数。下载程序不得把系统当前日期写入查询，也不得将浏览器页面、重定向错误页或失败响应当作数据。每次未来执行以运行 ID `U10-YYYYMMDDTHHMMSSZ` 建立目录 `data/raw/U10-YYYYMMDDTHHMMSSZ/`，并写入：

- `nasa_power_hourly_wuhan_20200101_20200107_utc.json`：字节不改的成功 JSON 响应；
- `nasa_power_hourly_wuhan_20200101_20200107_utc.request.json`：完整 URL、全部查询参数、请求和响应 UTC 时间、HTTP 状态、响应头、SHA-256；
- `nasa_power_hourly_wuhan_20200101_20200107_utc.sha256`：原始响应的 SHA-256。

转换后唯一模型输入为 `data/processed/input_168h.csv`；同一运行的不可覆盖副本为 `data/processed/U10-YYYYMMDDTHHMMSSZ_input_168h_wuhan_20200101T0000Z_20200107T2300Z.csv`。同时生成 `data/processed/U10-YYYYMMDDTHHMMSSZ_quality_report.json` 与 `data/processed/U10-YYYYMMDDTHHMMSSZ_run_manifest.json`。manifest 必须指向原始文件、两个 SHA-256、脚本路径/版本、参数和环境；质量报告必须列出每项检查的计数与处置。

## 字段、单位与转换

| 来源字段 | NASA POWER 单位 | 目标字段 | 目标单位 | 冻结转换 |
|---|---:|---|---:|---|
| 时间键 `YYYYMMDDHH` | UTC 小时起点 | `hour` | h（索引） | 将键解析为有时区的 UTC；按时间升序，以 `2020-01-01T00:00Z` 为 0，逐行加 1 |
| `WS50M` | m/s | `wind` | MW | 100 MW × `p_wind(v)`；`v<3` 为 0，`3≤v<12` 为 `(v³-3³)/(12³-3³)`，`12≤v≤25` 为 1，`v>25` 为 0 |
| `ALLSKY_SFC_SW_DWN` | Wh/m²/h | `solar` | MW | 150 MW × `max(G,0)/1000`；结果限制在 `[0,150]` MW；`G=0` 时严格为 0 |
| 24h 构造负荷 | MW | `load` | MW | 按问题文件规定循环并乘七天系数；不从 NASA 推导 |

POWER 返回的参数单位必须与表格一致；任何单位差异、未声明单位或无法解析的元数据均停止转换。写入 CSV 前，`wind` 和 `solar` 保留至少 6 位小数（不得为“两位小数”而改变可复现性）；只有展示图可另行四舍五入。输出 UTF-8、LF 换行、表头精确为 `hour,load,wind,solar`。

## 时间、缺失和重复规则

先把所有源键解析为 UTC，再以固定 UTC 窗口重建期望键集合 `2020010100…2020010723`。不得根据本地日期截取，也不得受 DST 影响；本地时区仅记录为审计字段。

- 缺失时间键、重复时间键、非整点键、无法解析键：计入质量报告并停止；不删除重复行来“修复”。
- `-999`、`-999.0`、空值、NaN、Inf 以及 API 元数据声明的填充值均视为缺失；必需气象变量不插补、不前/后填、不线性插值，任一出现即停止。
- 负荷模板缺值、气象值非数值或非有限值同样停止。原始辐照度 `<0`、风速 `<0`、风速 `>75 m/s`、辐照度 `>1500 Wh/m²/h` 为物理范围失败，不裁剪掩盖问题。

## 可执行验收条件和失败处置

| 步骤 | 验收条件 | 失败后的处理 |
|---|---|---|
| 请求 | HTTP 200、JSON 可解析、回显坐标/日期/参数与冻结值完全相同 | 保存失败元数据和错误正文摘要；不创建转换 CSV；网络/API 故障记 `inconclusive` |
| 原始留档 | 三个 raw 文件存在，哈希可复算且匹配 | 判 `invalid`，停止 |
| 时间规范化 | 两变量各有同一组恰好 168 个预期 UTC 键，严格一小时递增、无重复 | 判 `invalid`，停止 |
| 数值质量 | 缺失/重复/非有限/范围违规计数均为 0 | 原始数据问题记 `refuted`；解析或处置违反本设计记 `invalid` |
| 转换 | 四列精确存在，所有值有限非负，`0≤wind≤100`、`0≤solar≤150`，且 `G=0 ⇒ solar=0` | 判 `refuted`；若由实现偏离冻结公式导致，判 `invalid` |
| 输入契约 | `validate_input_data(csv, num_steps=168, time_step_hours=1.0)` 通过；两次相同原始文件和参数转换的 CSV 字节 SHA-256 相同 | 首次不通过按原因判定并停止；复现不一致判 `invalid` |

本设计不创建上述产物；它只规定未来执行必须产生的产物与验收标准。
