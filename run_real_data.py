"""U10 未来运行入口：下载冻结响应，再离线转换为 168 小时输入。"""

from scripts.download_nasa_power import download
from src.weather_pipeline import convert_saved_response, make_run_id


def main() -> None:
    run_id = make_run_id()
    raw_files = download(run_id)
    artifacts = convert_saved_response(raw_files["raw"], run_id)
    print("U10 数据管线完成；负荷为构造负荷，非真实负荷。")
    for name, path in {**raw_files, **artifacts}.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
