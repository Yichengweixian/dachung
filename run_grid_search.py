"""Run frozen U09 main, deterministic-repeat, and high-capex grids."""

import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd
import pulp

from scripts.audit_u07 import check
from src.economic_model import EconomicParameters
from src.grid_search import generate_candidates, run_grid, select_best, with_robustness_costs
from src.optimization_validation import validate
from src.plot_grid_search import plot_best_dispatch, plot_heatmap


ROOT = Path(__file__).resolve().parent
UNIT = ROOT / "instructions/studies/U09-grid-search"
RUN_ID = "U09-20260913-01"
OUT = ROOT / "results/grid_search" / RUN_ID
FIG = ROOT / "figures/grid_search" / RUN_ID
COMPARE = ["total_cost_CNY", "renewable_utilization_pct", "curtailment_MWh",
           "thermal_generation_MWh", "load_shedding_MWh", "storage_discharge_MWh"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    frozen = json.loads((UNIT / "freeze.json").read_text(encoding="utf-8"))
    for relative, digest in frozen["sha256"].items():
        if sha(ROOT / relative) != digest:
            raise RuntimeError(f"Frozen input changed: {relative}")
    if OUT.exists() or FIG.exists():
        raise FileExistsError(f"Run {RUN_ID} already exists; frozen evidence may not be overwritten")
    OUT.mkdir(parents=True); FIG.mkdir(parents=True)
    completed = {"main": [], "repeat": [], "robustness": []}
    try:
        cfg = frozen["config"]
        data = pd.read_csv(ROOT / "data/input_24h.csv")
        base_storage = cfg["storage.json"]
        grid = cfg["grid_search.json"]
        dt = cfg["simulation.json"]["time_step_hours"]
        thermal = {"min": cfg["optimization.json"]["thermal_min_MW"],
                   "max": cfg["no_storage.json"]["thermal_max_MW"],
                   "ramp": cfg["optimization.json"]["thermal_ramp_MW_per_h"]}
        economics = EconomicParameters(**cfg["economics.json"]["parameters"])
        candidates = generate_candidates(grid)

        main_summary, dispatches, details = run_grid(
            data, base_storage, thermal, economics, dt, grid, independent_check=check, candidates=candidates
        )
        completed["main"] = main_summary.scenario.tolist()
        best, ties = select_best(main_summary)
        best_dispatch = dispatches[best.scenario].copy()
        best_dispatch.insert(0, "scenario", best.scenario)
        best_dispatch.to_csv(OUT / "best_dispatch.csv", index=False, float_format="%.17g")
        main_summary.to_csv(OUT / "summary.csv", index=False, float_format="%.12g")

        saved_summary = pd.read_csv(OUT / "summary.csv")
        saved_dispatch = pd.read_csv(OUT / "best_dispatch.csv")
        if len(saved_summary) != 101 or saved_summary.scenario.nunique() != 101:
            raise ValueError("Saved summary grid is incomplete")
        best_storage = dict(base_storage, energy_capacity_MWh=float(best.energy_capacity_MWh),
                            power_capacity_MW=float(best.power_capacity_MW))
        validate(saved_dispatch, data, best_storage, thermal, dt, True)
        check(saved_dispatch, best_storage, thermal, dt, True)

        repeat_summary, _, repeat_details = run_grid(
            data, base_storage, thermal, economics, dt, grid, independent_check=check,
            candidates=list(reversed(candidates))
        )
        completed["repeat"] = repeat_summary.scenario.tolist()
        a = main_summary.set_index("scenario")[COMPARE].sort_index()
        b = repeat_summary.set_index("scenario")[COMPARE].sort_index()
        repeat_differences = (a - b).abs()
        if float(repeat_differences.to_numpy().max()) >= 1e-6:
            raise ValueError("Full-grid deterministic repeat differs")

        robust_economics = with_robustness_costs(economics, grid["robustness_cost_overrides"])
        robust_summary, _, robust_details = run_grid(
            data, base_storage, thermal, robust_economics, dt, grid, independent_check=check,
            candidates=candidates
        )
        completed["robustness"] = robust_summary.scenario.tolist()
        robust_summary.to_csv(OUT / "robustness_summary.csv", index=False, float_format="%.12g")
        robust_best, robust_ties = select_best(robust_summary)
        direction_ok = (robust_best.energy_capacity_MWh <= best.energy_capacity_MWh and
                        robust_best.power_capacity_MW <= best.power_capacity_MW)
        if not direction_ok:
            raise ValueError("Higher-capex optimum moved toward larger capacity or power")

        neighbors = main_summary[
            ((main_summary.energy_capacity_MWh == best.energy_capacity_MWh) &
             (abs(main_summary.power_capacity_MW - best.power_capacity_MW) == 5)) |
            ((main_summary.power_capacity_MW == best.power_capacity_MW) &
             (abs(main_summary.energy_capacity_MWh - best.energy_capacity_MWh) == 10))
        ].copy()
        neighbors["cost_difference_from_best_CNY"] = neighbors.total_cost_CNY - best.total_cost_CNY
        neighbors.to_csv(OUT / "best_neighbors.csv", index=False, float_format="%.12g")

        plot_heatmap(saved_summary, "total_cost_CNY", FIG / "total_cost_heatmap.png")
        plot_heatmap(saved_summary, "renewable_utilization_pct", FIG / "renewable_utilization_heatmap.png")
        plot_best_dispatch(saved_dispatch, best, base_storage, FIG / "best_dispatch.png", dt)

        source_files = ["run_grid_search.py", "src/grid_search.py", "src/plot_grid_search.py"]
        internal = 0 < best.energy_capacity_MWh < 100 and 5 < best.power_capacity_MW < 50
        verdict = "supported" if internal else "inconclusive"
        manifest = {
            "run_id": RUN_ID,
            "frozen": frozen,
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {"pulp": pulp.__version__, "numpy": np.__version__, "pandas": pd.__version__},
            "execution_source_sha256": {p: sha(ROOT / p) for p in source_files},
            "evaluate_function": "src.economic_model.evaluate_system_costs",
            "candidate_count": len(candidates),
            "main_statuses": {name: item["solver_status"] for name, item in details.items()},
            "repeat_statuses": {name: item["solver_status"] for name, item in repeat_details.items()},
            "robustness_statuses": {name: item["solver_status"] for name, item in robust_details.items()},
            "repeat_max_absolute_difference": float(repeat_differences.to_numpy().max()),
            "best": {"scenario": best.scenario, "energy_capacity_MWh": float(best.energy_capacity_MWh),
                     "power_capacity_MW": float(best.power_capacity_MW), "total_cost_CNY": float(best.total_cost_CNY),
                     "tie_count": len(ties), "strictly_internal": bool(internal)},
            "robustness_best": {"scenario": robust_best.scenario,
                                "energy_capacity_MWh": float(robust_best.energy_capacity_MWh),
                                "power_capacity_MW": float(robust_best.power_capacity_MW),
                                "total_cost_CNY": float(robust_best.total_cost_CNY),
                                "tie_count": len(robust_ties), "direction_check": bool(direction_ok)},
            "verdict": verdict,
        }
        dump(OUT / "run_manifest.json", manifest)
        for relative, digest in frozen["sha256"].items():
            if sha(ROOT / relative) != digest:
                raise RuntimeError(f"Frozen input changed during run: {relative}")
        print(main_summary.nsmallest(10, "total_cost_CNY")[["scenario", "total_cost_CNY",
              "renewable_utilization_pct", "storage_utilization_pct"]].to_string(index=False))
        print("best", manifest["best"])
        print("robustness_best", manifest["robustness_best"])
        print("verdict", verdict)
    except Exception as exc:
        dump(OUT / "failure.json", {"error": repr(exc), "completed": completed, "verdict": "invalid"})
        raise


if __name__ == "__main__":
    main()

