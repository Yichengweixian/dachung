"""U10 离线测试：所有 NASA 响应均在测试中构造，绝不发起网络请求。"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.weather_pipeline import (
    PipelineError, build_input_168h, expected_timestamp_keys, parse_power_json,
    convert_saved_response, validate_power_payload, wind_power_mw, write_csv_atomic,
)


def fake_payload(drop_key=None):
    keys = expected_timestamp_keys()
    solar = {key: (0 if index % 3 == 0 else 500) for index, key in enumerate(keys)}
    wind = {key: (3 if index % 2 == 0 else 12) for index, key in enumerate(keys)}
    if drop_key:
        solar.pop(drop_key)
    return {
        "header": {"time_standard": "UTC", "fill_value": -999},
        "parameters": {"ALLSKY_SFC_SW_DWN": {"units": "Wh/m^2"}, "WS50M": {"units": "m/s"}},
        "properties": {"parameter": {"ALLSKY_SFC_SW_DWN": solar, "WS50M": wind}},
    }


class U10WeatherPipelineTests(unittest.TestCase):
    def test_valid_payload_converts_to_168_continuous_rows_reproducibly(self):
        weather, report = validate_power_payload(parse_power_json(json.dumps(fake_payload()).encode("utf-8")))
        template = pd.DataFrame({"hour": np.arange(24), "load": np.arange(24) + 10, "wind": 0.0, "solar": 0.0})
        first = build_input_168h(weather, template)
        second = build_input_168h(weather, template)
        self.assertTrue(report["passed"])
        self.assertEqual(first.hour.tolist(), list(range(168)))
        self.assertEqual(first.load.iloc[0], 9.5)
        self.assertEqual(first.load.iloc[24], 10.0)
        self.assertTrue((first.loc[weather.ALLSKY_SFC_SW_DWN == 0, "solar"] == 0).all())
        pd.testing.assert_frame_equal(first, second)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.csv"
            write_csv_atomic(first, path)
            self.assertEqual(path.read_bytes(), path.read_bytes())

    def test_missing_timestamp_is_rejected_without_interpolation(self):
        payload = parse_power_json(json.dumps(fake_payload(expected_timestamp_keys()[4])).encode("utf-8"))
        with self.assertRaisesRegex(PipelineError, "质量闸门"):
            validate_power_payload(payload)

    def test_duplicate_json_timestamp_is_rejected_before_silent_overwrite(self):
        key = expected_timestamp_keys()[0]
        body = json.dumps(fake_payload())
        needle = f'"{key}": 0'
        duplicate = f'"{key}": 0, "{key}": 1'
        payload = parse_power_json(body.replace(needle, duplicate, 1).encode("utf-8"))
        with self.assertRaisesRegex(PipelineError, "质量闸门"):
            validate_power_payload(payload)

    def test_power_curve_boundaries(self):
        self.assertEqual(wind_power_mw(2.99), 0.0)
        self.assertEqual(wind_power_mw(3), 0.0)
        self.assertEqual(wind_power_mw(12), 100.0)
        self.assertEqual(wind_power_mw(25), 100.0)
        self.assertEqual(wind_power_mw(25.01), 0.0)

    def test_offline_saved_response_writes_quality_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw_path = root / "raw.json"
            raw_path.write_text(json.dumps(fake_payload()), encoding="utf-8")
            template_path = root / "load.csv"
            pd.DataFrame({"hour": np.arange(24), "load": np.ones(24),
                          "wind": np.zeros(24), "solar": np.zeros(24)}).to_csv(template_path, index=False)
            artifacts = convert_saved_response(raw_path, "U10-TEST", template_path, root / "processed")
            manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
            self.assertTrue(json.loads(artifacts["quality_report"].read_text(encoding="utf-8"))["passed"])
            self.assertEqual(manifest["utc_window"]["count"], 168)
            self.assertEqual(pd.read_csv(artifacts["converted"]).shape, (168, 4))


if __name__ == "__main__":
    unittest.main()
