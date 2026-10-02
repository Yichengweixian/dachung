"""U11R10: frozen N48 weights at two uncalibrated storage configurations."""
import argparse
import importlib.metadata
import json
from time import perf_counter

import numpy as np
import pandas as pd

from run_budgeted_ga import saved_cost
from src.annual_clustering import annual_metrics
from src.data_loader import validate_input_data
from src.fixed_weights_capacity_transfer import (
    RATES, SCENARIOS, SEEDS, TOTALS, decision, fixed_days, repeat_difference, source_day,
)
from src.representative_days import input_energy_errors
from src.study_runtime import ROOT, StudyRun, configuration, dump, sha

UNIT = "U11R10-fixed-weights-capacity-transfer"
PREDECESSOR = ROOT/"results/annual/U11R08B-v01"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="U11R10-v01")
    args = parser.parse_args()
    run = StudyRun(UNIT, "annual", args.run_id)
    started = perf_counter()
    attempted = 0
    try:
        cfg, storage, thermal, economics = configuration()
        old = json.loads((PREDECESSOR/"run_manifest.json").read_text(encoding="utf-8"))
        preflight = json.loads((ROOT/"results/annual/U11R10-predecessor-audit-v01.json").read_text(encoding="utf-8"))
        if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(PREDECESSOR/"run_manifest.json"):
            raise ValueError("Predecessor audit mismatch")
        for key in ("storage", "optimization", "no_storage", "economics"):
            if cfg[key] != old["freeze"]["config"][key+".json"]:
                raise ValueError("Physical/economic configuration changed: "+key)
        data = pd.read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv", float_precision="round_trip")
        validate_input_data(data, 8760)
        fixed = {}
        for seed in SEEDS:
            prefix = f"N48_seed{seed}"
            reps = pd.read_csv(PREDECESSOR/(prefix+"_representatives.csv"), float_precision="round_trip")
            labels = pd.read_csv(PREDECESSOR/(prefix+"_labels.csv"))
            days, weights, residual = fixed_days(data, reps, labels)
            fixed[seed] = (days, weights, reps)
            # Copy original bytes rather than reserialize frozen weights.
            for suffix in ("representatives", "labels"):
                (run.out/(prefix+f"_{suffix}.csv")).write_bytes((PREDECESSOR/(prefix+f"_{suffix}.csv")).read_bytes())
            run.manifest.setdefault("fixed_weight_residuals", {})[str(seed)] = residual
        run.manifest["parameters"] = dict(N=48, seeds=list(SEEDS), scenarios=list(SCENARIOS),
                                          planned_milp_calls=1020, weight_lp_calls=0,
                                          daily_reset=True, dt=1., terminal=True,
                                          predecessor_publication="U11R08B", repeat="seed42_cluster0")
        run.manifest["packages"].update({p:importlib.metadata.version(p)
                                         for p in ("scikit-learn", "scipy", "threadpoolctl")})
        comparisons, full_rows = [], []
        cost_differences = []

        def case(name, day, st):
            nonlocal attempted
            attempted += 1
            _, row = run.case(name, day, st, thermal, economics)
            cost, residual = saved_cost(run.out/(name+"_hourly.csv"), day, st, thermal, economics)
            difference = abs(cost-row["total_cost_CNY"])
            if difference >= 1e-6:
                raise ValueError("Saved cost readback mismatch: "+name)
            cost_differences.append(difference)
            row["max_residual"] = residual
            return row

        for scenario, energy, power in SCENARIOS:
            st = dict(storage, energy_capacity_MWh=energy, power_capacity_MW=power)
            baseline_rows = []
            for d in range(365):
                baseline_rows.append(case(f"{scenario}_day_{d:03d}", source_day(data, d), st))
                if (d+1) % 50 == 0:
                    print(scenario, "full days", d+1, "calls", attempted, flush=True)
                    dump(run.out/"run_manifest.json", run.manifest)
            baseline_path = run.out/(scenario+"_daily_summary.csv")
            pd.DataFrame(baseline_rows).to_csv(baseline_path, index=False, float_format="%.17g")
            full = annual_metrics(pd.read_csv(baseline_path, float_precision="round_trip"), np.ones(365))
            full_rows.append(dict(capacity_scenario=scenario, **full))
            first_repeat = None
            for seed in SEEDS:
                days, weights, reps = fixed[seed]
                rows = []
                for k, day in enumerate(days):
                    row = case(f"{scenario}_N48_seed{seed}_cluster{k}", day, st)
                    rows.append(row)
                    if seed == 42 and k == 0:
                        first_repeat = row
                path = run.out/f"{scenario}_N48_seed{seed}_summary.csv"
                pd.DataFrame(rows).to_csv(path, index=False, float_format="%.17g")
                metrics = annual_metrics(pd.read_csv(path, float_precision="round_trip"), weights)
                errors = input_energy_errors(data, days, weights)
                row = dict(capacity_scenario=scenario, N=48, seed=seed, **metrics, **errors,
                           worst_error_pp=max(abs(metrics[k]-full[k]) for k in RATES),
                           cost_error_CNY=metrics["total_cost_CNY"]-full["total_cost_CNY"],
                           unserved_error_MWh=metrics["unserved_MWh"]-full["unserved_MWh"])
                for metric, field in (("total_cost_CNY", "cost_signed_relative_error"),
                                      ("unserved_MWh", "unserved_signed_relative_error")):
                    if full[metric] <= 0:
                        raise ValueError("Zero diagnostic denominator: "+metric)
                    row[field] = (metrics[metric]-full[metric])/full[metric]
                comparisons.append(row)
                print(scenario, seed, "E", row["worst_error_pp"], "D", row["max_input_relative_error"], flush=True)
            repeated = case(scenario+"_repeat_seed42_cluster0", fixed[42][0][0], st)
            difference = repeat_difference(first_repeat, repeated)
            pd.DataFrame([repeated]).to_csv(run.out/(scenario+"_repeat_summary.csv"), index=False, float_format="%.17g")
            run.manifest.setdefault("repeat_differences", {})[scenario] = difference
        table = pd.DataFrame(comparisons)
        verdict, passing = decision(table)
        table["passed"] = passing
        table.to_csv(run.out/"comparison.csv", index=False, float_format="%.17g")
        pd.DataFrame(full_rows).to_csv(run.out/"full_annual.csv", index=False, float_format="%.17g")
        if attempted != 1020 or len(run.manifest["cases"]) != 1020:
            raise ValueError("Incorrect formal solver call count")
        for path, expected in run.manifest["source_sha256"].items():
            if sha(ROOT/path) != expected:
                raise ValueError("Source changed during run: "+path)
        run.finish(verdict, dict(milp_calls=attempted, weight_lp_calls=0, groups=6,
                   passing_groups=int(passing.sum()), max_cost_difference=max(cost_differences),
                   max_residual=max(c["max_residual"] for c in run.manifest["cases"].values()),
                   elapsed_seconds=perf_counter()-started,
                   reference_E40_P20_comparison_sha256=sha(PREDECESSOR/"comparison.csv")))
    except Exception as exc:
        run.manifest.update(status="blocked", verdict="invalid", error=repr(exc),
                            attempted_milp_calls=attempted, elapsed_seconds=perf_counter()-started)
        if hasattr(exc, "log"):
            (run.out/"failed_cbc.log").write_text(exc.log, encoding="utf-8")
        dump(run.out/"failure.json", dict(error=repr(exc), attempted_milp_calls=attempted))
        run.manifest["artifacts"] = {p.name:sha(p) for p in run.out.iterdir()
                                     if p.is_file() and p.name != "run_manifest.json"}
        dump(run.out/"run_manifest.json", run.manifest)
        raise


if __name__ == "__main__":
    main()
