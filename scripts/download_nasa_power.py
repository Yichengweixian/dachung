"""U10 参数化下载入口；仅在直接运行且未使用 --dry-run 时联网。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.paths import RAW_DATA_DIR
from src.weather_pipeline import ENDPOINT, FROZEN_PARAMETERS, frozen_filename, make_run_id, sha256_file, write_json_atomic


def build_url(parameters: dict[str, str] = FROZEN_PARAMETERS) -> str:
    return ENDPOINT + "?" + urlencode(parameters)


def assert_frozen(parameters: dict[str, str]) -> None:
    if parameters != FROZEN_PARAMETERS:
        raise ValueError("U10 已冻结端点和查询参数；不得通过下载脚本改变地点、日期或变量。")


def download(run_id: str, raw_root: Path = RAW_DATA_DIR, timeout_seconds: float = 30.0,
             parameters: dict[str, str] = FROZEN_PARAMETERS) -> dict[str, Path]:
    """下载一次冻结请求，保留原始字节和请求审计记录。"""
    assert_frozen(parameters)
    run_dir = raw_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    request_path = run_dir / frozen_filename(".request.json")
    raw_path = run_dir / frozen_filename(".json")
    sha_path = run_dir / frozen_filename(".sha256")
    url = build_url(parameters)
    metadata = {"run_id": run_id, "url": url, "parameters": parameters,
                "requested_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "U10-NASA-POWER-pipeline"})
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            metadata.update({"response_at_utc": datetime.now(timezone.utc).isoformat(), "http_status": response.status,
                             "response_headers": dict(response.headers.items())})
            if response.status != 200:
                raise RuntimeError(f"NASA POWER 返回 HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        metadata.update({"failed": True, "error_type": type(exc).__name__, "error": str(exc)})
        write_json_atomic(metadata, request_path)
        raise RuntimeError(f"NASA POWER 请求失败；已保存失败元数据：{request_path}") from exc
    raw_path.write_bytes(body)
    metadata["raw_sha256"] = sha256_file(raw_path)
    write_json_atomic(metadata, request_path)
    sha_path.write_text(metadata["raw_sha256"] + "  " + raw_path.name + "\n", encoding="utf-8")
    return {"raw": raw_path, "request": request_path, "sha256": sha_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="下载冻结的 U10 NASA POWER 原始响应。")
    parser.add_argument("--run-id", default=None, help="默认生成 U10-YYYYMMDDTHHMMSSZ。")
    parser.add_argument("--raw-root", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true", help="仅输出冻结 URL，不联网也不写文件。")
    args = parser.parse_args()
    if args.dry_run:
        print(build_url())
        return
    files = download(args.run_id or make_run_id(), args.raw_root, args.timeout_seconds)
    print(json.dumps({name: str(path) for name, path in files.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
