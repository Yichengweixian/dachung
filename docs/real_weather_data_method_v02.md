# NASA POWER 气象转换方法 v02

来源：[NASA POWER逐小时官方接口](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)。
固定武汉30.59°N/114.30°E，2023-01-01—01-07 UTC，ALLSKY_SFC_SW_DWN与WS50M。
参数来自config/study_sequence_v02.json；请求、原始字节及服务端元数据在data/raw/U10-master-v01/，不得手工更改。

辐照度元数据Wh/m²表示每小时辐照能量；除1h取得该小时平均W/m²。光伏P=150G/1000 MW，此单元没有封顶。
风电装机100MW；v<3为0，3≤v≤12为100(v³−3³)/(12³−3³)，12<v≤25为100，v>25为0（v单位m/s）。
负荷为构造形状，非真实负荷：data/input_24h.csv的负荷按UTC日重复，日系数0.95/1/1.05循环；未对齐当地实际负荷时钟。
模型简化了风机群尾流、空气密度、组件温度、倾角与逆变器效率，气象估计出力不等于实测电站出力。

严格拒绝重复JSON键、缺失小时、非有限值、负值、缺失标记、未知单位和非UTC时间标准；不做插补。
输出两位小数，数据及元数据均保留。data/processed/U10-master-v01/input_168h.csv为版本化正式输入。
零辐照严格映射零光伏；全部168行通过校验。另一个Python进程重复转换CSV字节一致。

四坐标微扰（纬度或经度±0.1°）风光峰值、均值相对差0，通过预设10%界限。
这可能是源产品空间网格相同，不是空间精细分辨能力的证据。
所有数值证据：results/real_data/U10-master-v01/run_manifest.json、robustness.csv。

独立下载（输出必须是新目录）：
```powershell
.\.venv\Scripts\python.exe scripts/download_nasa_power.py --start 20230101 --end 20230107 --output data/raw/my-new-week
```
转换：
```powershell
.\.venv\Scripts\python.exe -m src.convert_weather --raw data/raw/my-new-week/response.json --start 20230101 --end 20230107 --output data/processed/my-new-week.csv
```
整单元复现：`python run_real_data.py --run-id U10-recheck-v02`（重新联网下载五个坐标）。
