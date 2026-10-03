"""Frozen U11R12 selection comparison; no change to historical solvers."""
import argparse
import importlib.metadata
import json
from time import perf_counter

import numpy as np
import pandas as pd

from run_budgeted_ga import saved_cost
from run_energy_calibrated_days_resolved import baseline_guard, CHANNELS
from src.annual_clustering import annual_metrics
from src.energy_calibrated_weights_resolved import BAND, calibrate
from src.fixed_weights_capacity_transfer import SEEDS, repeat_difference, source_day
from src.input_shortage_proxy import decision, select_days
from src.representative_days import input_energy_errors
from src.study_runtime import ROOT, StudyRun, dump, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", default="U11R12-v01")
    args = p.parse_args()
    run = StudyRun("U11R12-input-shortage-proxy", "annual", args.run_id)
    started = perf_counter()
    lp_calls = dispatch_calls = 0
    try:
        cfg, st, th, economics = baseline_guard()
        if BAND != 1e-6 or st["energy_capacity_MWh"] != 40 or st["power_capacity_MW"] != 20:
            raise ValueError("Frozen numerical/configuration mismatch")
        expected = dict(numpy="2.5.3", pandas="3.0.5", pulp="3.3.0", **{"scikit-learn":"1.9.1", "scipy":"1.18.1", "threadpoolctl":"3.7.0"})
        versions = {name:importlib.metadata.version(name) for name in expected}
        if versions != expected:
            raise ValueError("Environment version mismatch")
        run.manifest["packages"].update(versions)
        run.manifest["source_sha256"]["tests/test_input_shortage_proxy.py"] = sha(ROOT/"tests/test_input_shortage_proxy.py")
        preflight = json.loads((ROOT/"results/annual/U11R12-predecessor-audit-v01.json").read_text(encoding="utf-8"))
        if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(ROOT/"results/annual/U11R11-v01/run_manifest.json"):
            raise ValueError("Predecessor evidence mismatch")
        data = pd.read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv", float_precision="round_trip")
        full = pd.read_csv(ROOT/"results/annual/U11R02-v01/full_annual.csv", float_precision="round_trip").iloc[0]
        old = pd.read_csv(ROOT/"results/annual/U11R08B-v01/comparison.csv", float_precision="round_trip")
        original_full = json.loads((ROOT/"results/annual/U11R02-v01/run_manifest.json").read_text(encoding="utf-8"))
        original_daily = pd.read_csv(ROOT/"results/annual/U11R02-v01/daily_summary.csv", float_precision="round_trip")
        run.manifest["parameters"] = dict(N=48, seeds=list(SEEDS), thermal_max_MW=th["thermal_max_MW"],
                                          selection="nearest_cluster_mean_daily_excess_then_shape_then_earliest",
                                          tie_tolerance=1e-12, fixed_band=BAND, lp_budget=300, dispatch_budget=147,
                                          energy_capacity_MWh=40, power_capacity_MW=20)
        comparisons, same_source = [], []
        max_cost = max_physical = max_repeat = max_source_cost = 0.
        for seed in SEEDS:
            prefix = f"N48_seed{seed}"
            original = pd.read_csv(ROOT/"results/annual/U11R08B-v01"/(prefix+"_representatives.csv"), float_precision="round_trip")
            labels = pd.read_csv(ROOT/"results/annual/U11R08B-v01"/(prefix+"_labels.csv"))
            days, reps, proxies = select_days(data, labels, original, th["thermal_max_MW"])
            proxies.to_csv(run.out/(prefix+"_proxies.csv"), index=False, float_format="%.17g")
            pd.concat([day.assign(cluster=k) for k,day in enumerate(days)]).to_csv(run.out/(prefix+"_inputs.csv"), index=False, float_format="%.17g")
            a = np.array([[day[c].sum() for day in days] for c in CHANNELS])
            b = data[CHANNELS].sum().to_numpy()
            weights = []
            for label in ("main", "repeat"):
                directory = run.out/(prefix+"_"+label+"_models")
                directory.mkdir()
                def record_stage(record):
                    nonlocal lp_calls
                    lp_calls += 1
                    dump(run.out/(prefix+"_"+label+"_"+record["stage"]+".json"), record)
                    run.manifest["lp_calls"] = lp_calls
                    dump(run.out/"run_manifest.json", run.manifest)
                w, _ = calibrate(a, b, reps.days.to_numpy(), reps.date_UTC.tolist(), record_stage, directory)
                weights.append(w)
            difference = float(np.max(np.abs(weights[0]-weights[1])))
            if difference > 1e-6:
                raise ValueError("Nonrepeatable weight calibration")
            reps = reps.assign(effective_days=weights[0], repeat_days=weights[1], effective_probability=weights[0]/365.)
            reps.to_csv(run.out/(prefix+"_representatives.csv"), index=False, float_format="%.17g")
            rows = []
            for k, day in enumerate(days):
                name = prefix+f"_cluster{k}"
                dispatch_calls += 1
                _, row = run.case(name, day, st, th, economics)
                cost, residual = saved_cost(run.out/(name+"_hourly.csv"), day, st, th, economics)
                delta = abs(cost-row["total_cost_CNY"])
                if delta >= 1e-6:
                    raise ValueError("Saved daily cost differs")
                max_cost, max_physical = max(max_cost, delta), max(max_physical, residual)
                old_name = f"day_{int(reps.day.iloc[k]):03d}"
                old_info = original_full["cases"][old_name]
                if old_info["solver_status"] != "Optimal" or old_info["storage"] != st or old_info["thermal"] != th:
                    raise ValueError("Same-source configuration/status mismatch")
                old_cost, _ = saved_cost(ROOT/"results/annual/U11R02-v01"/(old_name+"_hourly.csv"), source_day(data, reps.day.iloc[k]), st, th, economics)
                source_delta = abs(old_cost-cost)
                if source_delta >= 1e-6:
                    raise ValueError("Same-source cost differs")
                max_source_cost = max(max_source_cost, source_delta)
                source_comparison = dict(seed=seed, cluster=k, day=int(reps.day.iloc[k]), cost_difference_CNY=cost-old_cost)
                for key in ("renewable_available_MWh", "renewable_used_MWh", "curtailment_MWh", "total_load_MWh", "thermal_generation_MWh", "unserved_MWh"):
                    source_comparison[key+"_difference"] = row[key]-original_daily.iloc[int(reps.day.iloc[k])][key]
                same_source.append(source_comparison)
                rows.append(row)
            name = prefix+"_repeat_cluster0"
            dispatch_calls += 1
            _, repeated = run.case(name, days[0], st, th, economics)
            repeat_cost, residual = saved_cost(run.out/(name+"_hourly.csv"), days[0], st, th, economics)
            if abs(repeat_cost-repeated["total_cost_CNY"]) >= 1e-6:
                raise ValueError("Repeat saved cost differs")
            maximum = repeat_difference(rows[0], repeated)
            max_repeat, max_physical = max(max_repeat, maximum), max(max_physical, residual)
            pd.DataFrame([repeated]).to_csv(run.out/(prefix+"_repeat_summary.csv"), index=False, float_format="%.17g")
            summary = run.out/(prefix+"_summary.csv")
            pd.DataFrame(rows).to_csv(summary, index=False, float_format="%.17g")
            rows = pd.read_csv(summary, float_precision="round_trip").to_dict("records")
            metrics = annual_metrics(rows, weights[0])
            control = annual_metrics(rows, reps.days)
            errors = input_energy_errors(data, days, weights[0])
            prior = old[(old.N == 48) & (old.seed == seed)]
            if len(prior) != 1:
                raise ValueError("Historical comparison identity mismatch")
            prior = prior.iloc[0]
            cost_error = metrics["total_cost_CNY"]-full["total_cost_CNY"]
            shortage_error = metrics["unserved_MWh"]-full["unserved_MWh"]
            result = dict(N=48, seed=seed, **metrics, **errors,
                          worst_error_pp=max(abs(metrics[k]-full[k]) for k in ("renewable_utilization_pct", "curtailment_rate_pct")),
                          cost_error_CNY=cost_error, unserved_error_MWh=shortage_error,
                          old_cost_error_CNY=prior.cost_error_CNY, old_unserved_error_MWh=prior.unserved_error_MWh,
                          cost_absolute_improvement_CNY=abs(prior.cost_error_CNY)-abs(cost_error),
                          unserved_absolute_improvement_MWh=abs(prior.unserved_error_MWh)-abs(shortage_error),
                          changed_days=int(reps.changed.sum()), repeat_weight_difference=difference,
                          repeat_dispatch_difference=maximum)
            result.update({"control_"+k:v for k,v in control.items()})
            comparisons.append(result)
            print(seed, "complete", {k:result[k] for k in ("changed_days", "worst_error_pp", "cost_absolute_improvement_CNY", "unserved_absolute_improvement_MWh")}, flush=True)
        table = pd.DataFrame(comparisons)
        verdict, passed = decision(table)
        table["passes_ED"] = passed
        table.to_csv(run.out/"comparison.csv", index=False, float_format="%.17g")
        pd.DataFrame(same_source).to_csv(run.out/"same_source_costs.csv", index=False, float_format="%.17g")
        if (lp_calls, dispatch_calls, len(run.manifest["cases"])) != (300, 147, 147):
            raise ValueError("Frozen solver budget mismatch")
        for path, digest in run.manifest["source_sha256"].items():
            if sha(ROOT/path) != digest:
                raise ValueError("Source drift during run: "+path)
        run.manifest.update(lp_calls=lp_calls, dispatch_calls=dispatch_calls)
        run.finish(verdict, dict(groups=3, passes_ED=passed, max_cost_readback=max_cost,
                   max_physical_residual=max_physical, max_repeat_difference=max_repeat,
                   max_same_source_cost_difference=max_source_cost, elapsed_seconds=perf_counter()-started))
    except Exception as exc:
        run.manifest.update(status="blocked", verdict="invalid", error=repr(exc), lp_calls=lp_calls, dispatch_calls=dispatch_calls)
        if hasattr(exc, "log"):
            (run.out/"failed_dispatch_cbc.log").write_text(exc.log, encoding="utf-8")
        dump(run.out/"failure.json", dict(error=repr(exc), lp_calls=lp_calls, dispatch_calls=dispatch_calls))
        raise
    finally:
        run.manifest["artifacts"] = {p.relative_to(run.out).as_posix():sha(p) for p in run.out.rglob("*") if p.is_file() and p.name != "run_manifest.json"}
        dump(run.out/"run_manifest.json", run.manifest)


if __name__ == "__main__":
    main()
