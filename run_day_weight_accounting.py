"""U11R13: reconstruct old hourly evidence, with zero new solver calls."""
import argparse
import json
from time import perf_counter

import numpy as np
import pandas as pd

from run_cost_unserved_attribution import rebuild
from src.annual_clustering import annual_metrics
from src.cost_unserved_attribution import COSTS, METRICS, SEEDS, close, cost_check, decompose
from src.day_weight_accounting import hypothesis, paths, path_cost_check
from src.fixed_weights_capacity_transfer import fixed_days, source_day
from src.representative_days import input_energy_errors
from src.study_runtime import ROOT, StudyRun, configuration, dump, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id",default="U11R13-v01")
    args = parser.parse_args()
    run = StudyRun("U11R13-day-weight-accounting","annual",args.run_id)
    started = perf_counter()
    try:
        cfg,storage,thermal,economics = configuration()
        if storage["energy_capacity_MWh"] != 40 or storage["power_capacity_MW"] != 20:
            raise ValueError("Frozen capacity mismatch")
        keys = ("U11R02-v01","U11R08B-v01","U11R12-v01")
        folders = {key:ROOT/"results/annual"/key for key in keys}
        manifests = {key:json.loads((folder/"run_manifest.json").read_text(encoding="utf-8")) for key,folder in folders.items()}
        for m in manifests.values():
            if m["status"] != "complete": raise ValueError("Incomplete predecessor")
            for key in ("storage","optimization","no_storage","economics"):
                if cfg[key] != m["freeze"]["config"][key+".json"]: raise ValueError("Physical configuration drift")
        preflight = json.loads((ROOT/"results/annual/U11R13-predecessor-audit-v01.json").read_text(encoding="utf-8"))
        if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(folders["U11R12-v01"]/"run_manifest.json"):
            raise ValueError("Predecessor audit identity mismatch")
        run.manifest["parameters"] = dict(N=48,seeds=list(SEEDS),energy_capacity_MWh=40,power_capacity_MW=20,
                                          new_solver_calls=0,source_dispatches=653,metrics=list(METRICS),
                                          counterfactuals=["old_count","new_count","Y00","Y10","Y01","Y11"],
                                          tolerance=1e-6,retrospective=True)
        run.manifest["source_sha256"]["tests/test_day_weight_accounting.py"] = sha(ROOT/"tests/test_day_weight_accounting.py")
        data = pd.read_csv(folders["U11R02-v01"]/"input_8760h.csv",float_precision="round_trip")
        full_saved = pd.read_csv(folders["U11R02-v01"]/"daily_summary.csv",float_precision="round_trip")
        if list(full_saved.scenario) != [f"day_{d:03d}" for d in range(365)]: raise ValueError("Full daily sequence mismatch")
        count = 0
        max_readback = max_physical = max_identity = max_source_cost = 0.
        full_rows = []
        for d in range(365):
            name = f"day_{d:03d}"
            row,residual = rebuild(folders["U11R02-v01"]/(name+"_hourly.csv"),source_day(data,d),storage,thermal,economics,manifests["U11R02-v01"]["cases"][name])
            for key in METRICS: max_readback = max(max_readback,close(row[key],full_saved.iloc[d][key],"full daily "+key))
            max_physical = max(max_physical,residual)
            full_rows.append(row)
            count += 1
        pd.DataFrame(full_rows).to_csv(run.out/"reconstructed_full.csv",index=False,float_format="%.17g")
        full = annual_metrics(full_rows,np.ones(365))
        prior_full = pd.read_csv(folders["U11R02-v01"]/"full_annual.csv",float_precision="round_trip").iloc[0]
        for key in full: max_readback = max(max_readback,close(full[key],prior_full[key],"full annual"))
        all_annual, all_clusters, all_paths, path_clusters, combinations, gaps = [],[],[],[],[],[]
        old_accounting = pd.read_csv(ROOT/"results/annual/U11R11-v01/annual_decomposition.csv",float_precision="round_trip")
        for seed in SEEDS:
            prefix = f"N48_seed{seed}"
            labels = pd.read_csv(folders["U11R08B-v01"]/(prefix+"_labels.csv"))
            collections = {}
            for day_set,folder_key in (("old","U11R08B-v01"),("new","U11R12-v01")):
                reps = pd.read_csv(folders[folder_key]/(prefix+"_representatives.csv"),float_precision="round_trip")
                days,weights,_ = fixed_days(data,reps,labels)
                summary = pd.read_csv(folders[folder_key]/(prefix+"_summary.csv"),float_precision="round_trip")
                names = [prefix+f"_cluster{k}" for k in range(48)]
                if list(summary.scenario) != names: raise ValueError("Saved representative sequence mismatch")
                rows = []
                for k,name in enumerate(names):
                    row,residual = rebuild(folders[folder_key]/(name+"_hourly.csv"),days[k],storage,thermal,economics,manifests[folder_key]["cases"][name])
                    max_physical = max(max_physical,residual)
                    for key in METRICS:
                        max_readback = max(max_readback,close(row[key],summary.iloc[k][key],"saved daily "+key))
                        gap = row[key]-full_rows[int(reps.day.iloc[k])][key]
                        gaps.append(dict(seed=seed,day_set=day_set,cluster=k,metric=key,difference=gap))
                        if key == "total_cost_CNY": max_source_cost = max(max_source_cost,close(gap,0.,"same-source cost"))
                    rows.append(row)
                    count += 1
                pd.DataFrame(rows).to_csv(run.out/(prefix+"_"+day_set+"_reconstructed.csv"),index=False,float_format="%.17g")
                annual,clusters,residual = decompose(full_rows,rows,labels.cluster,reps.days,weights)
                max_identity = max(max_identity,residual,cost_check(annual,economics.load_shedding_penalty_CNY_per_MWh))
                old_compare = pd.read_csv(folders[folder_key]/"comparison.csv",float_precision="round_trip")
                original = old_compare[(old_compare.N == 48) & (old_compare.seed == seed)]
                if len(original) != 1: raise ValueError("Prior comparison identity mismatch")
                original = original.iloc[0]
                for metric in METRICS:
                    saved_row = annual[annual.metric == metric].iloc[0]
                    if metric in old_compare.columns:
                        max_readback = max(max_readback,close(saved_row.calibrated,original[metric],"prior weighted total"))
                    if "control_"+metric in old_compare.columns:
                        max_readback = max(max_readback,close(saved_row.control,original["control_"+metric],"prior control total"))
                    if day_set == "old":
                        prior = old_accounting[(old_accounting.capacity_scenario == "E40_P20") & (old_accounting.seed == seed) & (old_accounting.metric == metric)]
                        if len(prior) != 1: raise ValueError("R11 accounting identity mismatch")
                        for key in ("full","control","calibrated","replacement","adjustment","total"):
                            max_readback = max(max_readback,close(saved_row[key],prior.iloc[0][key],"R11 accounting"))
                for metric,error_key in (("total_cost_CNY","cost_error_CNY"),("unserved_MWh","unserved_error_MWh")):
                    max_readback = max(max_readback,close(annual[annual.metric == metric].total.iloc[0],original[error_key],"prior signed error"))
                for table in (annual,clusters): table["seed"],table["day_set"] = seed,day_set
                for key in ("day","date_UTC","days","effective_days"):
                    clusters[key] = clusters.cluster.map(reps.set_index("cluster")[key])
                all_annual.append(annual)
                all_clusters.append(clusters)
                collections[day_set] = reps,days,weights,rows
            r0,d0,w0,v0 = collections["old"]
            r1,d1,w1,v1 = collections["new"]
            if not np.array_equal(r0.days,r1.days): raise ValueError("Old/new cluster counts differ")
            path,clpath,residual = paths(v0,v1,r0.days,w0,w1)
            max_identity = max(max_identity,residual,path_cost_check(path,economics.load_shedding_penalty_CNY_per_MWh))
            path["seed"],clpath["seed"] = seed,seed
            for key,values in (("old_day",r0.day),("new_day",r1.day),("old_weight",w0),("new_weight",w1)):
                clpath[key] = clpath.cluster.map(dict(enumerate(values)))
            all_paths.append(path)
            path_clusters.append(clpath)
            for combination,days,rows,w in (("old_count",d0,v0,r0.days),("new_count",d1,v1,r1.days),
                                            ("Y00",d0,v0,w0),("Y10",d1,v1,w0),("Y01",d0,v0,w1),("Y11",d1,v1,w1)):
                metrics = annual_metrics(rows,w)
                errors = input_energy_errors(data,days,w)
                E = max(abs(metrics[key]-full[key]) for key in ("renewable_utilization_pct","curtailment_rate_pct"))
                result = dict(seed=seed,combination=combination,**metrics,**errors,worst_error_pp=E,
                              passes_ED=E <= 1. and errors["max_input_relative_error"] <= .02,
                              cost_error_CNY=metrics["total_cost_CNY"]-full["total_cost_CNY"],
                              unserved_error_MWh=metrics["unserved_MWh"]-full["unserved_MWh"])
                if combination.startswith("Y"):
                    for key in METRICS:
                        value = float(np.dot([r[key] for r in rows],w))
                        max_identity = max(max_identity,close(value,path[path.metric == key][combination].iloc[0],"cross-path grid"))
                combinations.append(result)
            print(seed,"old/new and two accounting paths reconstructed",flush=True)
        annual = pd.concat(all_annual,ignore_index=True)
        clusters = pd.concat(all_clusters,ignore_index=True)
        cross = pd.concat(all_paths,ignore_index=True)
        clcross = pd.concat(path_clusters,ignore_index=True)
        verdict,decisions = hypothesis(annual)
        for filename,table in (("annual_decomposition.csv",annual),("cluster_decomposition.csv",clusters),
                               ("path_decomposition.csv",cross),("path_clusters.csv",clcross),
                               ("cost_decomposition.csv",annual[annual.metric.isin(COSTS)]),
                               ("counterfactuals.csv",pd.DataFrame(combinations)),("same_source_gaps.csv",pd.DataFrame(gaps))):
            table.to_csv(run.out/filename,index=False,float_format="%.17g")
        dump(run.out/"hypothesis.json",dict(retrospective=True,hypothesis="new_weights_increase_cost_and_unserved_absolute_errors",verdict=verdict,groups=decisions))
        if count != 653 or run.manifest["cases"] or (len(annual),len(clusters),len(cross),len(clcross),len(combinations),len(gaps)) != (84,4032,42,2016,18,4032):
            raise ValueError("Source/output/zero-solve budget mismatch")
        for path,digest in run.manifest["source_sha256"].items():
            if sha(ROOT/path) != digest: raise ValueError("Source drift: "+path)
        run.finish(verdict,dict(new_solver_calls=0,source_dispatches=count,groups=6,annual_rows=84,cluster_rows=4032,path_rows=42,path_cluster_rows=2016,
                               counterfactual_rows=18,max_physical_residual=max_physical,max_readback_difference=max_readback,
                               max_identity_difference=max_identity,max_same_source_cost_difference=max_source_cost,elapsed_seconds=perf_counter()-started))
    except Exception as exc:
        run.manifest.update(status="blocked",verdict="invalid",error=repr(exc),new_solver_calls=0)
        dump(run.out/"failure.json",dict(error=repr(exc),new_solver_calls=0))
        run.manifest["artifacts"] = {p.name:sha(p) for p in run.out.iterdir() if p.is_file() and p.name != "run_manifest.json"}
        dump(run.out/"run_manifest.json",run.manifest)
        raise


if __name__ == "__main__":
    main()
