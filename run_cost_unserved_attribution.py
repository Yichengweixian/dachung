"""U11R11 zero-solve accounting reconstructed from existing dispatch files."""
import argparse
from dataclasses import asdict
import json
from time import perf_counter

import numpy as np
import pandas as pd

from src.cost_unserved_attribution import (
    COSTS, METRICS, SCENARIOS, SEEDS, close, cost_check, decompose, hypothesis, top_contributors,
)
from src.economic_model import evaluate_system_costs, validate_cost_results
from src.fixed_weights_capacity_transfer import fixed_days, source_day
from src.optimization_validation import audit_dispatch, summarize_dispatch
from src.study_runtime import ROOT, StudyRun, configuration, dump, sha


def rebuild(path, source, storage, thermal, economics, info):
    q = pd.read_csv(path, float_precision="round_trip")
    checks = audit_dispatch(q, source, storage, thermal)
    if not checks["passed"] or info["solver_status"] != "Optimal" or info["storage"] != storage or info["thermal"] != thermal:
        raise ValueError("Invalid saved source case: "+str(path))
    if info["dt"] != 1. or not info["terminal"] or info["model_class"] != "MILP":
        raise ValueError("Saved model boundary mismatch")
    log = path.with_name(path.name.replace("_hourly.csv", "_cbc.log")).read_text(encoding="utf-8")
    if not any(x in log for x in ("Result - Optimal solution found", "Optimal objective")):
        raise ValueError("Missing original Optimal log")
    row = summarize_dispatch(q, asdict(economics)).iloc[0].to_dict()
    row.update(scenario=path.stem, energy_capacity_MWh=storage["energy_capacity_MWh"],
               power_capacity_MW=storage["power_capacity_MW"], num_steps=24, time_step_hours=1.,
               load_shedding_MWh=row["unserved_MWh"], storage_discharge_MWh=row["discharge_MWh"],
               initial_inventory_supply_MWh=max(0., float(q.energy_start_MWh.iloc[0]-q.energy_MWh.iloc[-1]))*storage["eta_discharge"])
    costs = evaluate_system_costs(pd.DataFrame([row]), economics)
    validate_cost_results(costs, economics)
    row.update(costs.iloc[0].to_dict())
    close(row["operating_cost_CNY"], info["objective_CNY"], "saved operating objective")
    if not np.isfinite([row[k] for k in METRICS]).all():
        raise ValueError("Nonfinite saved metric")
    return {k:float(row[k]) for k in METRICS}, checks["max_residual"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="U11R11-v01")
    args = parser.parse_args()
    run = StudyRun("U11R11-cost-unserved-attribution", "annual", args.run_id)
    started = perf_counter()
    try:
        cfg, base, thermal, economics = configuration()
        folders = {name:ROOT/"results/annual"/name for name in ("U11R02-v01", "U11R08B-v01", "U11R10-v01")}
        manifests = {name:json.loads((folder/"run_manifest.json").read_text(encoding="utf-8")) for name, folder in folders.items()}
        for manifest in manifests.values():
            if manifest["status"] != "complete":
                raise ValueError("Incomplete predecessor")
            for key in ("storage", "optimization", "no_storage", "economics"):
                if cfg[key] != manifest["freeze"]["config"][key+".json"]:
                    raise ValueError("Predecessor physical configuration mismatch")
        preflight = json.loads((ROOT/"results/annual/U11R11-predecessor-audit-v01.json").read_text(encoding="utf-8"))
        if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(folders["U11R10-v01"]/"run_manifest.json"):
            raise ValueError("Predecessor audit identity mismatch")
        data = pd.read_csv(folders["U11R02-v01"]/"input_8760h.csv", float_precision="round_trip")
        fixed = {}
        for seed in SEEDS:
            p = f"N48_seed{seed}"
            reps = pd.read_csv(folders["U11R08B-v01"]/(p+"_representatives.csv"), float_precision="round_trip")
            labels = pd.read_csv(folders["U11R08B-v01"]/(p+"_labels.csv"))
            days, weights, residual = fixed_days(data, reps, labels)
            fixed[seed] = reps, labels.cluster.to_numpy(), days, weights
        all_annual, all_clusters, gaps = [], [], []
        source_count = 0
        max_readback = max_physical = max_identity = max_gap_cost = 0.
        run.manifest["parameters"] = dict(scenarios=[list(x) for x in SCENARIOS], seeds=list(SEEDS),
                                          N=48, new_solver_calls=0, source_dispatches=1527,
                                          top_count=5, metrics=list(METRICS), costs=list(COSTS),
                                          hypothesis_seed=7, accounting_tolerance=1e-6)
        run.manifest["source_sha256"]["tests/test_cost_unserved_attribution.py"] = sha(ROOT/"tests/test_cost_unserved_attribution.py")
        for scenario, energy, power in SCENARIOS:
            storage = dict(base, energy_capacity_MWh=energy, power_capacity_MW=power)
            full_id = "U11R02-v01" if energy == 40 else "U11R10-v01"
            rep_id = "U11R08B-v01" if energy == 40 else "U11R10-v01"
            prefix = "" if energy == 40 else scenario+"_"
            saved = pd.read_csv(folders[full_id]/(prefix+"daily_summary.csv"), float_precision="round_trip")
            expected = [prefix+f"day_{d:03d}" for d in range(365)]
            if list(saved.scenario) != expected:
                raise ValueError("Saved full-day ordering mismatch")
            full_rows = []
            for d, name in enumerate(expected):
                row, residual = rebuild(folders[full_id]/(name+"_hourly.csv"), source_day(data, d), storage,
                                        thermal, economics, manifests[full_id]["cases"][name])
                max_physical = max(max_physical, residual)
                for metric in METRICS:
                    max_readback = max(max_readback, close(row[metric], saved.iloc[d][metric], name+" "+metric))
                full_rows.append(row)
                source_count += 1
            pd.DataFrame(full_rows).to_csv(run.out/(scenario+"_reconstructed_full.csv"), index=False, float_format="%.17g")
            original_full = pd.read_csv(folders[full_id]/"full_annual.csv", float_precision="round_trip")
            old_full = original_full.iloc[0] if energy == 40 else original_full[original_full.capacity_scenario == scenario].iloc[0]
            for metric in (k for k in METRICS if k in old_full.index):
                max_readback = max(max_readback, close(float(np.sum([r[metric] for r in full_rows])), old_full[metric], scenario+" full"))
            for seed in SEEDS:
                reps, labels, days, weights = fixed[seed]
                p = prefix+f"N48_seed{seed}"
                saved = pd.read_csv(folders[rep_id]/(p+"_summary.csv"), float_precision="round_trip")
                names = [p+f"_cluster{k}" for k in range(48)]
                if list(saved.scenario) != names:
                    raise ValueError("Representative sequence mismatch")
                rows = []
                for k, name in enumerate(names):
                    row, residual = rebuild(folders[rep_id]/(name+"_hourly.csv"), days[k], storage,
                                            thermal, economics, manifests[rep_id]["cases"][name])
                    max_physical = max(max_physical, residual)
                    for metric in METRICS:
                        max_readback = max(max_readback, close(row[metric], saved.iloc[k][metric], name+" "+metric))
                        gap = row[metric]-full_rows[int(reps.day.iloc[k])][metric]
                        gaps.append(dict(capacity_scenario=scenario, seed=seed, cluster=k, metric=metric, difference=gap))
                        if metric == "total_cost_CNY":
                            max_gap_cost = max(max_gap_cost, close(gap, 0., "same-day objective cost"))
                    rows.append(row)
                    source_count += 1
                pd.DataFrame(rows).to_csv(run.out/(p+"_reconstructed_representatives.csv"), index=False, float_format="%.17g")
                annual, clusters, difference = decompose(full_rows, rows, labels, reps.days, weights)
                max_identity = max(max_identity, difference, cost_check(annual, economics.load_shedding_penalty_CNY_per_MWh))
                annual["capacity_scenario"], annual["seed"] = scenario, seed
                clusters["capacity_scenario"], clusters["seed"] = scenario, seed
                for key in ("day", "date_UTC", "days", "effective_days"):
                    clusters[key] = clusters.cluster.map(reps.set_index("cluster")[key])
                comparison = pd.read_csv(folders[rep_id]/"comparison.csv", float_precision="round_trip")
                old_row = comparison[(comparison.N == 48) & (comparison.seed == seed)]
                if energy != 40:
                    old_row = old_row[old_row.capacity_scenario == scenario]
                if len(old_row) != 1:
                    raise ValueError("Original comparison identity mismatch")
                for metric in (k for k in METRICS if k in comparison.columns):
                    max_readback = max(max_readback, close(annual[annual.metric == metric].calibrated.iloc[0], old_row.iloc[0][metric], "original weighted "+metric))
                for metric, error_key in (("total_cost_CNY", "cost_error_CNY"), ("unserved_MWh", "unserved_error_MWh")):
                    max_readback = max(max_readback, close(annual[annual.metric == metric].total.iloc[0], old_row.iloc[0][error_key], "original error "+metric))
                all_annual.append(annual)
                all_clusters.append(clusters)
                print(scenario, seed, "accounting reconstructed", flush=True)
        annual = pd.concat(all_annual, ignore_index=True)
        clusters = pd.concat(all_clusters, ignore_index=True)
        costs = annual[annual.metric.isin(COSTS)].copy()
        verdict, decisions = hypothesis(costs)
        for filename, table in (("annual_decomposition.csv", annual), ("cluster_decomposition.csv", clusters),
                                ("cost_decomposition.csv", costs), ("same_source_gaps.csv", pd.DataFrame(gaps)),
                                ("top_contributors.csv", top_contributors(clusters))):
            table.to_csv(run.out/filename, index=False, float_format="%.17g")
        dump(run.out/"hypothesis.json", dict(hypothesis="seed7_shortage_fee_dominates_three_capacities",
                                              verdict=verdict, groups=decisions))
        if source_count != 1527 or run.manifest["cases"]:
            raise ValueError("Source/zero-solve budget mismatch")
        for path, expected in run.manifest["source_sha256"].items():
            if sha(ROOT/path) != expected:
                raise ValueError("Source drift during analysis: "+path)
        run.finish(verdict, dict(new_solver_calls=0, reconstructed_full_days=1095,
                   reconstructed_representative_days=432, groups=9, annual_rows=len(annual),
                   cluster_rows=len(clusters), max_physical_residual=max_physical,
                   max_readback_difference=max_readback, max_identity_difference=max_identity,
                   max_same_day_cost_difference=max_gap_cost, elapsed_seconds=perf_counter()-started))
    except Exception as exc:
        run.manifest.update(status="blocked", verdict="invalid", error=repr(exc), new_solver_calls=0)
        dump(run.out/"failure.json", dict(error=repr(exc), new_solver_calls=0))
        run.manifest["artifacts"] = {p.name:sha(p) for p in run.out.iterdir() if p.is_file() and p.name != "run_manifest.json"}
        dump(run.out/"run_manifest.json", run.manifest)
        raise


if __name__ == "__main__":
    main()
