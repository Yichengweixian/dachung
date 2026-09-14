"""第2阶段入口：生成data/input_24h.csv，并绘制四条基础曲线。"""

import json

import pandas as pd

from src.generate_data import generate_24h_data, validate_24h_data
from src.paths import PROJECT_ROOT, CONFIG_DIR, FIGURES_DIR
from src.plot_results import plot_input_profiles


def main():
    with (CONFIG_DIR / "data_24h.json").open(encoding="utf-8") as file:
        config = json.load(file)
    data = generate_24h_data(config)
    validate_24h_data(data, config)

    csv_path = PROJECT_ROOT / "data" / "input_24h.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(csv_path, index=False, float_format="%.2f", encoding="utf-8")
    saved = pd.read_csv(csv_path)
    validate_24h_data(saved, config)
    image_path = FIGURES_DIR / "input_24h_profiles.png"
    plot_input_profiles(saved, image_path)

    total = saved.wind + saved.solar
    gap = total - saved.load
    print("24小时构造数据生成与检查完成（不是实际电网运行数据）。")
    print(f"CSV：{csv_path}")
    print(f"曲线图：{image_path}")
    for name in ("load", "wind", "solar"):
        print(f"{name}：{saved[name].min():.2f}—{saved[name].max():.2f} MW")
    print(f"风光富余小时：{saved.loc[gap > 0, 'hour'].tolist()}")
    print(f"风光不足小时：{saved.loc[gap < 0, 'hour'].tolist()}")
    print(f"风光可发电量/负荷电量：{total.sum() / saved.load.sum():.2%}")
    print("富余或不足仅比较风光与负荷，不代表实际弃电或失负荷；尚未计算火电和储能。")


if __name__ == "__main__":
    main()
