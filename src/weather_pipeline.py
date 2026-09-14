"""U10 NASA POWER 原始响应的离线校验、转换和审计留档。"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data_loader import validate_input_data
from src.paths import PROJECT_ROOT, PROCESSED_DATA_DIR, RAW_DATA_DIR

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/hourly/point"
FROZEN_PARAMETERS = {
    "parameters": "ALLSKY_SFC_SW_DWN,WS50M", "community": "RE",
    "longitude": "114.3000", "latitude": "30.5900", "start": "20200101",
    "end": "20200107", "format": "JSON", "time-standard": "UTC",
}
START_UTC = datetime(2020, 1, 1, tzinfo=timezone.utc)
END_UTC = datetime(2020, 1, 7, 23, tzinfo=timezone.utc)
EXPECTED_TIMESTAMPS = tuple(START_UTC + timedelta(hours=i) for i in range(168))
SOURCE_FIELDS = ("ALLSKY_SFC_SW_DWN", "WS50M")
FILL_VALUES = {-999.0}
WIND_CAPACITY_MW, SOLAR_CAPACITY_MW = 100.0, 150.0


class PipelineError(ValueError):
    """冻结输入契约或质量闸门未通过。"""


class DuplicateTrackingDict(dict):
    """保留 JSON 对象中的重复键，防止 json 默认的静默覆盖。"""

    def __init__(self, pairs):
        super().__init__()
        self.duplicate_keys = []
        for key, value in pairs:
            if key in self:
                self.duplicate_keys.append(key)
            self[key] = value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_timestamp_keys() -> list[str]:
    return [item.strftime("%Y%m%d%H") for item in EXPECTED_TIMESTAMPS]


def make_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return "U10-" + now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def frozen_filename(suffix: str) -> str:
    return "nasa_power_hourly_wuhan_20200101_20200107_utc" + suffix


def parse_power_json(raw_bytes: bytes) -> dict[str, Any]:
    try:
        return json.loads(raw_bytes.decode("utf-8"), object_pairs_hook=DuplicateTrackingDict)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(f"NASA POWER 响应不是 UTF-8 JSON：{exc}") from exc


def _unit(value: str) -> str:
    return value.replace("²", "^2").replace(" ", "").lower()


def _metadata_units(payload: dict[str, Any]) -> dict[str, str]:
    metadata = payload.get("parameters")
    if not isinstance(metadata, dict):
        raise PipelineError("响应缺少 parameters 单位元数据。")
    units = {}
    for field in SOURCE_FIELDS:
        item = metadata.get(field)
        if not isinstance(item, dict) or not isinstance(item.get("units"), str):
            raise PipelineError(f"响应缺少 {field} 的单位元数据。")
        units[field] = item["units"]
    # POWER 的逐小时辐照量有时写作 Wh/m^2；一个小时的区间量与 Wh/m^2/h 数值等价。
    irradiance = _unit(units["ALLSKY_SFC_SW_DWN"])
    if irradiance not in {"wh/m^2", "wh/m^2/h"} or _unit(units["WS50M"]) != "m/s":
        raise PipelineError(f"NASA POWER 单位不符合冻结规则：{units}")
    return units


def _series(payload: dict[str, Any], field: str) -> DuplicateTrackingDict:
    try:
        series = payload["properties"]["parameter"][field]
    except (KeyError, TypeError) as exc:
        raise PipelineError(f"响应缺少必需变量 {field}。") from exc
    if not isinstance(series, DuplicateTrackingDict):
        raise PipelineError(f"变量 {field} 不是 JSON 时间键对象。")
    return series


def _quality_template(units: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "expected_count": 168, "time_standard": "UTC", "expected_start": START_UTC.isoformat(),
        "expected_end": END_UTC.isoformat(), "source_units": units or {},
        "missing_timestamps": 0, "duplicate_timestamps": 0, "unparseable_timestamps": 0,
        "nonfinite_values": 0, "fill_values": 0, "range_violations": 0,
        "issues": [], "passed": False,
    }


def validate_power_payload(payload: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """校验冻结 UTC 窗口，返回原始气象表和可写入 JSON 的质量报告。"""
    units = _metadata_units(payload)
    report = _quality_template(units)
    expected = expected_timestamp_keys()
    expected_set = set(expected)
    sources = {field: _series(payload, field) for field in SOURCE_FIELDS}
    keys = set()
    for field, series in sources.items():
        duplicates = list(series.duplicate_keys)
        report["duplicate_timestamps"] += len(duplicates)
        if duplicates:
            report["issues"].append(f"{field} 存在重复时间键：{duplicates}")
        for key in series:
            try:
                datetime.strptime(key, "%Y%m%d%H").replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                report["unparseable_timestamps"] += 1
                report["issues"].append(f"{field} 含无法解析的时间键：{key!r}")
            keys.add(key)
        missing = expected_set - set(series)
        extra = set(series) - expected_set
        report["missing_timestamps"] += len(missing)
        if missing or extra:
            report["issues"].append(f"{field} 缺失 {len(missing)}、窗口外 {len(extra)} 个时间键")
    if keys != expected_set:
        report["issues"].append("源时间键集合与冻结的 168 小时 UTC 窗口不完全相同。")

    rows = []
    for hour, key in enumerate(expected):
        values = {}
        for field, series in sources.items():
            value = series.get(key)
            try:
                number = float(value)
            except (TypeError, ValueError):
                report["nonfinite_values"] += 1
                report["issues"].append(f"{field}/{key} 非数值：{value!r}")
                number = math.nan
            if number in FILL_VALUES:
                report["fill_values"] += 1
                report["issues"].append(f"{field}/{key} 是填充值。")
            if not math.isfinite(number):
                report["nonfinite_values"] += 1
                report["issues"].append(f"{field}/{key} 非有限。")
            if field == "WS50M" and math.isfinite(number) and not 0 <= number <= 75:
                report["range_violations"] += 1
                report["issues"].append(f"WS50M/{key} 超出 [0, 75] m/s。")
            if field == "ALLSKY_SFC_SW_DWN" and math.isfinite(number) and not 0 <= number <= 1500:
                report["range_violations"] += 1
                report["issues"].append(f"ALLSKY_SFC_SW_DWN/{key} 超出 [0, 1500] Wh/m²/h。")
            values[field] = number
        rows.append({"timestamp_utc": EXPECTED_TIMESTAMPS[hour].isoformat(), **values})
    if any(report[key] for key in ("missing_timestamps", "duplicate_timestamps", "unparseable_timestamps", "nonfinite_values", "fill_values", "range_violations")) or keys != expected_set:
        raise PipelineError("NASA POWER 原始数据未通过时间或数值质量闸门：" + "; ".join(report["issues"]))
    report["passed"] = True
    return pd.DataFrame(rows), report


def wind_power_mw(speed_m_per_s: float) -> float:
    if speed_m_per_s < 3 or speed_m_per_s > 25:
        return 0.0
    if speed_m_per_s >= 12:
        return WIND_CAPACITY_MW
    return WIND_CAPACITY_MW * (speed_m_per_s ** 3 - 3 ** 3) / (12 ** 3 - 3 ** 3)


def build_input_168h(weather: pd.DataFrame, load_template: pd.DataFrame) -> pd.DataFrame:
    """按冻结公式生成模型输入；不插补任何气象或负荷值。"""
    if len(weather) != 168 or list(weather.columns) != ["timestamp_utc", *SOURCE_FIELDS]:
        raise PipelineError("已校验气象表必须包含 168 行及冻结字段。")
    validate_input_data(load_template, num_steps=24, time_step_hours=1.0)
    daily = np.asarray(load_template["load"], dtype=float)
    factors = np.asarray([0.95, 1.00, 1.05, 0.95, 1.00, 1.05, 0.95])
    load = np.concatenate([daily * factor for factor in factors])
    wind = np.asarray([wind_power_mw(float(value)) for value in weather["WS50M"]])
    irradiance = np.asarray(weather["ALLSKY_SFC_SW_DWN"], dtype=float)
    solar = SOLAR_CAPACITY_MW * np.maximum(irradiance, 0.0) / 1000.0
    output = pd.DataFrame({"hour": np.arange(168), "load": load, "wind": wind, "solar": solar})
    if not ((output.wind >= 0).all() and (output.wind <= WIND_CAPACITY_MW).all() and
            (output.solar >= 0).all() and (output.solar <= SOLAR_CAPACITY_MW).all() and
            (output.loc[irradiance == 0, "solar"] == 0).all()):
        raise PipelineError("转换结果违反冻结物理边界。")
    validate_input_data(output, num_steps=168, time_step_hours=1.0)
    return output


def write_csv_atomic(data: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    data.to_csv(temporary, index=False, float_format="%.6f", encoding="utf-8", lineterminator="\n")
    os.replace(temporary, path)


def write_json_atomic(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def create_run_manifest(run_id: str, raw_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    return {
        "unit": "U10", "run_id": run_id, "frozen_request": {"endpoint": ENDPOINT, "parameters": FROZEN_PARAMETERS},
        "local_timezone": "Asia/Shanghai", "utc_window": {"start": START_UTC.isoformat(), "end": END_UTC.isoformat(), "count": 168},
        "source_fields": {"ALLSKY_SFC_SW_DWN": "Wh/m²/h", "WS50M": "m/s"},
        "output_fields": {"hour": "h index", "load": "MW (synthetic)", "wind": "MW", "solar": "MW"},
        "artifacts": {"raw": str(raw_path), "raw_sha256": sha256_file(raw_path), "converted": str(output_path),
                      "converted_sha256": sha256_file(output_path), "quality_report": str(report_path)},
        "code": {"weather_pipeline": "src/weather_pipeline.py", "python": sys.version, "platform": platform.platform()},
    }


def default_load_template() -> Path:
    return PROJECT_ROOT / "data" / "input_24h.csv"


def convert_saved_response(raw_path: Path, run_id: str, load_path: Path | None = None,
                           processed_root: Path = PROCESSED_DATA_DIR) -> dict[str, Path]:
    """离线转换已经保存的原始响应；不发起网络请求。"""
    payload = parse_power_json(raw_path.read_bytes())
    report_path = processed_root / f"{run_id}_quality_report.json"
    try:
        weather, report = validate_power_payload(payload)
        input_data = build_input_168h(weather, pd.read_csv(load_path or default_load_template()))
    except PipelineError as exc:
        report = locals().get("report", _quality_template())
        report["passed"] = False
        report["failure"] = str(exc)
        write_json_atomic(report, report_path)
        raise
    output_copy = processed_root / f"{run_id}_input_168h_wuhan_20200101T0000Z_20200107T2300Z.csv"
    canonical = processed_root / "input_168h.csv"
    write_csv_atomic(input_data, output_copy)
    write_csv_atomic(input_data, canonical)
    write_json_atomic(report, report_path)
    manifest_path = processed_root / f"{run_id}_run_manifest.json"
    write_json_atomic(create_run_manifest(run_id, raw_path, output_copy, report_path), manifest_path)
    return {"converted": output_copy, "canonical": canonical, "quality_report": report_path, "manifest": manifest_path}
