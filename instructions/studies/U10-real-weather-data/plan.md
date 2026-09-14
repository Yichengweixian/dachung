# U10 执行计划（含可直接粘贴给 Codex 的提示词）

## 组0 前置与冻结（人工）

- [ ] 0.1 记录判据哈希；确认网络环境（若无法访问 NASA POWER，本单元改判 blocked 并只交付下载脚本）
- [ ] 0.2 确认 `src/data_loader.py` 校验口径（hour 连续、步长=1h、非负有限）
- [ ] 0.3 冻结转换模型参数（切入 3 / 额定 12 / 切出 25 m/s、辐照度基准 1000 W/m²、装机 100/150 MW）

## 组1 实现（Codex）

> 你是本项目编程助手。项目根 D:\ADMIN\Desktop\大创第一阶段。执行研究单元 U10：真实气象数据管线。先读 `instructions/studies/U10-real-weather-data/design.md` 和 `specs/data.md`，然后：
>
> 1. 新建 `scripts/download_nasa_power.py`：调用 NASA POWER 逐小时 API（坐标 30.59/114.30，辐照度与 50m 风速），把请求参数、原始返回原样保存到 `data/raw/`；脚本单独可运行。若当前网络失败：报告失败原因，脚本仍作为交付物，不伪造下载结果。
> 2. 新建 `src/convert_weather.py`：按 design.md 的三段式风机功率曲线与光伏辐照度模型转换标幺出力，乘装机得 MW；负荷用 24h 形状 × 7 天 × 日间系数（0.95/1.0/1.05 轮换）。
> 3. 新建 `run_real_data.py`：串起下载→转换→校验（复用 `src/data_loader.py` 的 validate_input_data，num_steps=168）→ 保存 `data/processed/input_168h.csv` → 绘图（原始气象 + 风光荷曲线）。
> 4. 写 `docs/real_weather_data_method.md`（来源、坐标、时间范围、单位、公式、局限、复现方法）。所有文件写读统一 `encoding="utf-8"`。
> 5. 完成后停止，等待下一步指令。

## 组2 自查（Codex，组1通过后发送）

> 请核对并逐项报告：1) data/raw/ 中原始返回文件与请求参数完整；2) 168h 输入通过全部校验（连续、非负、有限、光伏夜间为 0）；3) 转换脚本重跑结果逐值一致（可复现）；4) 文档明确标注负荷为构造形状。失败即停止。

## 组3 判定与登记

- [ ] 按 decision-rule 逐条判定写入 findings.md；追加 RUNLOG.md；更新 STATUS.md、specs/roadmap.md
- [ ] 完成后停止，等用户指令
