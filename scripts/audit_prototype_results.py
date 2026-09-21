"""U13R01 independent audit: artifact hashes, value agreement, browser-vs-CLI numbers.

Runs in a separate process and does not import the UI. The rule-mode baseline
re-computation is labelled separately because it necessarily uses the public src module.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "results/prototype/U13R01-v01"
BROWSER = ROOT / "results/prototype/browser_check_v02"
OUT = ROOT / "results/prototype/audit_v01"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric_max_diff(left, right, order=None):
    if len(left) != len(right):
        return None
    if order:
        left = left.sort_values(order).reset_index(drop=True)
        right = right.sort_values(order).reset_index(drop=True)
    common = [c for c in left.columns if c in right.columns
              and pd.api.types.is_numeric_dtype(left[c]) and pd.api.types.is_numeric_dtype(right[c])]
    if not common:
        return None
    return float(np.nanmax(np.abs(left[common].to_numpy() - right[common].to_numpy())))


report = {"unit": "U13R01-consistent-prototype", "run_audited": str(RUN.relative_to(ROOT)),
          "browser_evidence": str(BROWSER.relative_to(ROOT)),
          "method": "separate process; no src import for hash/value checks",
          "checks": {}, "failures": [], "notes": []}


def record(name, passed, detail):
    report["checks"][name] = {"passed": bool(passed), **detail}
    if not passed:
        report["failures"].append(name)


manifest = json.loads((RUN / "run_manifest.json").read_text(encoding="utf-8"))
record("manifest_status", manifest.get("status") == "complete" and manifest.get("verdict") == "inconclusive",
       {"status": manifest.get("status"), "verdict": manifest.get("verdict"),
        "recorded_checks": json.loads((RUN / "checks.json").read_text(encoding="utf-8"))})

mismatch = [n for n, d in manifest["artifacts"].items() if sha(RUN / n) != d]
record("artifact_sha256_matches_manifest", not mismatch,
       {"artifacts_checked": len(manifest["artifacts"]), "mismatch": mismatch})

changed = {p: {"recorded": d, "now": sha(ROOT / p)}
           for p, d in manifest["source_sha256"].items() if sha(ROOT / p) != d}
record("source_unchanged_since_run", not changed,
       {"sources_checked": len(manifest["source_sha256"]), "changed": changed})

extra = sorted(p.name for p in RUN.iterdir()
               if p.is_file() and p.name != "run_manifest.json" and p.name not in manifest["artifacts"])
if extra:
    report["notes"].append(f"Files in run directory not listed in manifest artifacts: {extra}")

pairs = [("ui_milp_24h_vs_U06R01_main", RUN / "ui_milp_24h.csv",
          ROOT / "results/optimization/U06R01-v03/main_hourly.csv", 1e-6, ["hour"]),
         ("ui_milp_168h_vs_run_cli_168h", RUN / "ui_milp_168h.csv",
          RUN / "cli_168h_hourly.csv", 1e-6, ["hour"])]
for name, left, right, tol, order in pairs:
    a, b = pd.read_csv(left), pd.read_csv(right)
    d = numeric_max_diff(a, b, order)
    record(name, d is not None and d < tol,
           {"max_abs_diff": d, "tolerance": tol, "rows": [len(a), len(b)]})

grid = pd.read_csv(RUN / "ui_grid.csv")
grid_cli = pd.read_csv(ROOT / "results/grid_search/U09R01-v01/summary.csv")
cols = ["energy_capacity_MWh", "power_capacity_MW", "total_cost_CNY",
        "renewable_utilization_pct", "curtailment_MWh"]
order = ["energy_capacity_MWh", "power_capacity_MW"]
d = numeric_max_diff(grid[cols], grid_cli[cols], order)
record("ui_grid_vs_U09R01_summary", d is not None and d < 1e-6,
       {"max_abs_diff": d, "tolerance": 1e-6, "candidates": [len(grid), len(grid_cli)],
        "ui_best": grid.loc[grid.total_cost_CNY.idxmin(), order].to_dict(),
        "frozen_best": grid_cli.loc[grid_cli.total_cost_CNY.idxmin(), order].to_dict()})

browser = json.loads((BROWSER / "browser_checks.json").read_text(encoding="utf-8"))
metrics = dict(m.split("==", 1) for m in browser["steps"]["02_milp_solve"]["metrics"])
main = pd.read_csv(ROOT / "results/optimization/U06R01-v03/summary.csv")
main = main[main.scenario == "main"].iloc[0]
expected = {"新能源消纳率": "renewable_utilization_pct", "弃电量": "curtailment_MWh",
            "缺供电量": "load_shedding_MWh", "总成本": "total_cost_CNY"}
displayed = {}
for label, column in expected.items():
    value = float(metrics[label].replace("%", "").replace(" MWh", "").replace(" 元", "").replace(",", ""))
    displayed[label] = {"browser_displayed": value, "cli_recorded": float(main[column]),
                        "abs_diff": abs(value - float(main[column]))}
record("browser_metrics_vs_cli_summary",
       all(v["abs_diff"] <= 5e-4 for v in displayed.values()),
       {"display_rounding_tolerance": 5e-4, "values": displayed})

best = grid_cli.loc[grid_cli.total_cost_CNY.idxmin()]
line = browser["steps"]["04_grid_101"]["best_line"]
numbers = [float(x.replace(",", "")) for x in re.findall(r"[\d,]+(?:\.\d+)?", line.split("网格 CSV")[0])]
record("browser_grid_best_vs_cli",
       len(numbers) >= 3 and numbers[0] == float(best.energy_capacity_MWh)
       and numbers[1] == float(best.power_capacity_MW) and numbers[2] == round(float(best.total_cost_CNY), 2),
       {"browser_displayed": numbers[:3],
        "cli_best": [float(best.energy_capacity_MWh), float(best.power_capacity_MW), float(best.total_cost_CNY)]})

record("browser_automation_steps", browser["verdict"] == "browser_automation_passed"
       and not browser["failed_steps"] and browser["console_error_count"] == 0,
       {"verdict": browser["verdict"], "failed_steps": browser["failed_steps"],
        "console_error_count": browser["console_error_count"],
        "human_confirmation": browser["human_confirmation"],
        "screenshots": browser["screenshots"]})
report["notes"].append("browser_checks.json reports human_confirmation=false; automation evidence "
                       "does not replace the manual acceptance required by the frozen rule.")

if "--with-src-reproduction" in sys.argv:
    sys.path.insert(0, str(ROOT))
    from src.prototype_service import dispatch as ui_dispatch, read_input
    from src.study_runtime import configuration
    cfg, s, t, e = configuration()
    data = read_input(ROOT / "data/input_24h.csv")
    q, row = ui_dispatch("规则", data, s, t, e)
    baseline = pd.read_csv(ROOT / "results/capacity_sensitivity/E40_P20_hourly.csv")
    d = numeric_max_diff(q, baseline, ["hour"])
    summary = pd.read_csv(ROOT / "results/capacity_sensitivity/summary.csv").set_index("scenario").loc["E40_P20"]
    columns = ["renewable_utilization_pct", "curtailment_rate_pct", "curtailment_MWh",
               "thermal_generation_MWh", "load_shedding_MWh", "storage_charge_MWh",
               "storage_discharge_MWh", "storage_utilization_pct"]
    summary_diff = max(abs(float(row[c]) - float(summary[c])) for c in columns)
    record("rule_baseline_reproduction_src_dependent",
           d is not None and d < 1e-6 and summary_diff < 1e-6,
           {"module": "src.prototype_service.dispatch(mode='规则') on the frozen config",
            "hourly_max_abs_diff_vs_E40_P20": d,
            "summary_max_abs_diff_vs_E40_P20": float(summary_diff),
            "recorded_rule_24h_max_diff": json.loads((RUN / "checks.json").read_text(encoding="utf-8"))["rule_24h_max_diff"],
            "frozen_storage_config": s, "frozen_thermal_config": t,
            "note": "uses the public src module; the file/value checks above do not"})

report["input_sha256"] = {
    "results/prototype/U13R01-v01/run_manifest.json": sha(RUN / "run_manifest.json"),
    "results/prototype/U13R01-v01/checks.json": sha(RUN / "checks.json"),
    "results/prototype/browser_check_v02/browser_checks.json": sha(BROWSER / "browser_checks.json"),
    "results/optimization/U06R01-v03/main_hourly.csv": sha(ROOT / "results/optimization/U06R01-v03/main_hourly.csv"),
    "results/grid_search/U09R01-v01/summary.csv": sha(ROOT / "results/grid_search/U09R01-v01/summary.csv"),
}
report["verdict"] = "audit_passed" if not report["failures"] else "audit_failed"
report["packages"] = {"pandas": pd.__version__, "numpy": np.__version__, "python": sys.version}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"verdict": report["verdict"], "failures": report["failures"],
                  "checks": {k: v["passed"] for k, v in report["checks"].items()},
                  "notes": report["notes"]}, ensure_ascii=False, indent=2))
sys.exit(0 if report["verdict"] == "audit_passed" else 1)
