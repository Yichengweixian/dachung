"""项目统一入口：第1阶段仅检查目录与时间配置，不执行仿真。"""

import json

from src.paths import CONFIG_DIR, PROJECT_ROOT


def main():
    config_path = CONFIG_DIR / "simulation.json"
    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)

    steps = config["num_steps"]
    step_hours = config["time_step_hours"]
    if type(steps) is not int or steps <= 0:
        raise ValueError("num_steps 必须为正整数。")
    if type(step_hours) not in (int, float) or step_hours <= 0:
        raise ValueError("time_step_hours 必须为正数。")

    print("高比例新能源电力电量平衡项目")
    print(f"项目目录：{PROJECT_ROOT}")
    print(f"时间配置：{steps} 个时间步，每步 {step_hours} 小时")
    print(f"仿真时长：{steps * step_hours:g} 小时")
    print("框架检查通过。数据生成运行run_data_24h.py；无储能运行run_no_storage.py；储能对比运行run_storage.py。")
    print("第5阶段容量敏感性分析运行run_capacity_sensitivity.py。")
    print("第6阶段系统经济性评价运行run_economics.py。")


if __name__ == "__main__":
    main()
