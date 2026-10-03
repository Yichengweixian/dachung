"""U11R12 independent selection/annual replay and saved CBC evidence audit."""
import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_fixed_weights_capacity_transfer import annual, read_csv, check_close, sha, TOTALS
from scripts.audit_cost_unserved_attribution import detailed_metrics
from scripts.audit_energy_calibrated_days_resolved_v02 import audit_solver_evidence
from src.energy_calibrated_weights_resolved import check_stage

SEEDS = (42, 7, 2026)


def audit(folder):
    m = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    frozen = ROOT/"instructions/studies/U11R12-input-shortage-proxy/freeze.json"
    if m["status"] != "complete" or m["unit"] != "U11R12-input-shortage-proxy" or sha(frozen) != m["freeze_sha256"] or json.loads(frozen.read_text(encoding="utf-8")) != m["freeze"]:
        raise ValueError("Run/freeze identity mismatch")
    hashes = 1
    for entries,base in ((m["freeze"]["sha256"], ROOT), (m["source_sha256"], ROOT), (m["artifacts"], folder)):
        for path,digest in entries.items():
            if sha(base/path) != digest: raise ValueError("Hash mismatch: "+path)
            hashes += 1
    if {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.name != "run_manifest.json"} != set(m["artifacts"]):
        raise ValueError("Artifact inventory mismatch")
    expected_params = dict(N=48,seeds=list(SEEDS),thermal_max_MW=120,
                           selection="nearest_cluster_mean_daily_excess_then_shape_then_earliest",
                           tie_tolerance=1e-12,fixed_band=1e-6,lp_budget=300,dispatch_budget=147,
                           energy_capacity_MWh=40,power_capacity_MW=20)
    if m["parameters"] != expected_params:
        raise ValueError("Frozen parameter mismatch")
    cfg = m["freeze"]["config"]
    storage = cfg["storage.json"]
    thermal = {k:cfg["optimization.json"][k] for k in ("thermal_min_MW", "thermal_ramp_MW_per_h")}
    thermal["thermal_max_MW"] = cfg["no_storage.json"]["thermal_max_MW"]
    economics = cfg["economics.json"]["parameters"]
    if storage["energy_capacity_MWh"] != 40 or storage["power_capacity_MW"] != 20 or thermal["thermal_max_MW"] != 120:
        raise ValueError("Configuration mismatch")
    source = read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")
    if len(source) != 8760:
        raise ValueError("Source input incomplete")
    daily = [source[d*24:(d+1)*24] for d in range(365)]
    proxies = [sum(max(float(r["load"])-float(r["wind"])-float(r["solar"])-120.,0.) for r in day) for day in daily]
    features = [[float(r[channel])/100. for channel in ("load","wind","solar") for r in day] for day in daily]
    old_folder = ROOT/"results/annual/U11R02-v01"
    old_manifest = json.loads((old_folder/"run_manifest.json").read_text(encoding="utf-8"))
    old_rows, max_physical = [], 0.
    maximum = max_mps = max_bound = max_normalized = max_source_cost = max_repeat = 0.

    def close(a,b,label):
        nonlocal maximum
        maximum = max(maximum,check_close(a,b,label))

    old_summary = read_csv(old_folder/"daily_summary.csv")
    if [r["scenario"] for r in old_summary] != [f"day_{d:03d}" for d in range(365)]:
        raise ValueError("Full baseline daily inventory mismatch")
    for d in range(365):
        name = f"day_{d:03d}"
        row,residual = detailed_metrics(old_folder/(name+"_hourly.csv"),daily[d],storage,thermal,economics,old_manifest["cases"][name])
        for key in row: close(row[key],old_summary[d][key],"old daily "+key)
        old_rows.append(row)
        max_physical = max(max_physical,residual)
    full = annual(old_rows,[1.]*365)
    recorded_full = read_csv(old_folder/"full_annual.csv")[0]
    for key,value in full.items(): close(value,recorded_full[key],"annual baseline")
    prior = [r for r in read_csv(ROOT/"results/annual/U11R08B-v01/comparison.csv") if int(r["N"]) == 48]
    comparison = read_csv(folder/"comparison.csv")
    if len(comparison) != 3 or [int(r["seed"]) for r in comparison] != list(SEEDS) or any(int(r["N"]) != 48 for r in comparison):
        raise ValueError("Incomplete comparison matrix")
    gaps = read_csv(folder/"same_source_costs.csv")
    if len(gaps) != 144:
        raise ValueError("Same-source comparison inventory mismatch")
    lp_count = count = 0
    reconstructed, passes, changes = [], [], []
    expected_cases = set()
    for seed,result in zip(SEEDS,comparison):
        prefix = f"N48_seed{seed}"
        labels = read_csv(ROOT/"results/annual/U11R08B-v01"/(prefix+"_labels.csv"))
        original = read_csv(ROOT/"results/annual/U11R08B-v01"/(prefix+"_representatives.csv"))
        reps = read_csv(folder/(prefix+"_representatives.csv"))
        proxy_rows = read_csv(folder/(prefix+"_proxies.csv"))
        exported = read_csv(folder/(prefix+"_inputs.csv"))
        if len(labels) != 365 or len(reps) != 48 or len(original) != 48 or len(proxy_rows) != 365 or len(exported) != 1152:
            raise ValueError("Selection inventory mismatch")
        if [int(r["day"]) for r in labels] != list(range(365)) or [int(r["cluster"]) for r in reps] != list(range(48)):
            raise ValueError("Selection ordering mismatch")
        labs = [int(r["cluster"]) for r in labels]
        if set(labs) != set(range(48)):
            raise ValueError("Missing cluster")
        for d,saved in enumerate(proxy_rows):
            if int(saved["day"]) != d or int(saved["cluster"]) != labs[d]: raise ValueError("Proxy identity mismatch")
            close(saved["proxy_MWh"],proxies[d],"daily proxy")
        chosen = []
        for k,rep in enumerate(reps):
            members = [d for d in range(365) if labs[d] == k]
            target = sum(proxies[d] for d in members)/len(members)
            distances = {d:abs(proxies[d]-target) for d in members}
            minimum = min(distances.values())
            eligible = [d for d in members if distances[d] <= minimum+1e-12]
            center = [sum(features[d][i] for d in members)/len(members) for i in range(72)]
            shape = {d:math.sqrt(sum((features[d][i]-center[i])**2 for i in range(72))) for d in eligible}
            best = min(shape.values())
            tied = [d for d in eligible if shape[d] <= best+1e-12]
            selected = min(tied)
            if int(rep["day"]) != selected or int(rep["days"]) != len(members) or int(original[k]["days"]) != len(members) or int(rep["original_day"]) != int(original[k]["day"]):
                raise ValueError("Independent selection/count mismatch")
            if rep["date_UTC"] != (date(2023,1,1)+timedelta(days=selected)).isoformat() or int(rep["proxy_tie_count"]) != len(eligible) or int(rep["final_tie_count"]) != len(tied) or (rep["changed"] == "True") != (selected != int(original[k]["day"])):
                raise ValueError("Selection metadata mismatch")
            for key,value in dict(proxy_MWh=proxies[selected],cluster_proxy_mean_MWh=target,proxy_distance_MWh=distances[selected],weight=len(members)/365.).items(): close(rep[key],value,"selected "+key)
            chosen.append(selected)
            for hour,row in enumerate(exported[k*24:(k+1)*24]):
                if int(row["cluster"]) != k or int(row["hour"]) != hour: raise ValueError("Exported input ordering mismatch")
                for channel in ("load","wind","solar"): close(row[channel],daily[selected][hour][channel],"selected actual input")
        if len(set(chosen)) != 48:
            raise ValueError("Duplicate representative day")
        c = np.asarray([int(r["days"]) for r in reps])
        a = np.asarray([[sum(float(row[channel]) for row in daily[d]) for d in chosen] for channel in ("load","wind","solar")])
        b = np.asarray([sum(float(row[channel]) for row in source) for channel in ("load","wind","solar")])
        stages = ["primary","secondary"]+[f"lex_{k:03d}" for k in sorted(range(48),key=lambda k:reps[k]["date_UTC"])]
        endings = []
        for label in ("main","repeat"):
            pins, t_limit, l_limit = [], None, None
            for index,stage in enumerate(stages):
                q = json.loads((folder/(prefix+"_"+label+"_"+stage+".json")).read_text(encoding="utf-8"))
                if q["status"] != "Optimal" or q.get("error") or q["solution_status"] != 1 or q["band"] != 1e-6 or q["stage"] != stage or q["pins"] != pins or q["t_limit"] != t_limit or q["l_limit"] != l_limit:
                    raise ValueError("Stage status/order/band mismatch")
                checked = check_stage(a,b,c,q)
                max_bound = max(max_bound,checked["bounds_residual"])
                max_normalized = max(max_normalized,checked["normalized_residual"])
                max_mps = max(max_mps,audit_solver_evidence(folder/(prefix+"_"+label+"_models")/(stage+"_cbc"),q))
                objective = q["t"] if index == 0 else sum(q["deviations"]) if index == 1 else q["weights"][int(stage[4:])]
                if abs(q["objective"]-objective) > 1e-7: raise ValueError("LP objective reconstruction mismatch")
                if index == 0: t_limit = q["objective"]+1e-6
                elif index == 1: l_limit = q["objective"]+1e-6
                else:
                    k = int(stage[4:])
                    pins.append(dict(index=k,lower=max(.5*c[k],objective-1e-6),upper=min(2*c[k],objective+1e-6)))
                lp_count += 1
            endings.append(q["weights"])
        weight_difference = max(abs(x-y) for x,y in zip(*endings))
        if weight_difference > 1e-6: raise ValueError("Nonrepeatable LP")
        close(result["repeat_weight_difference"],weight_difference,"weight repeat difference")
        weights = [float(r["effective_days"]) for r in reps]
        if weights != endings[0] or [float(r["repeat_days"]) for r in reps] != endings[1]: raise ValueError("Exported weights mismatch")
        for rep,w in zip(reps,weights): close(rep["effective_probability"],w/365.,"effective probability")
        summary = read_csv(folder/(prefix+"_summary.csv"))
        if [r["scenario"] for r in summary] != [prefix+f"_cluster{k}" for k in range(48)]: raise ValueError("Dispatch inventory mismatch")
        rows = []
        for k,day in enumerate(chosen):
            name = prefix+f"_cluster{k}"
            expected_cases.add(name)
            row,residual = detailed_metrics(folder/(name+"_hourly.csv"),daily[day],storage,thermal,economics,m["cases"][name])
            max_physical = max(max_physical,residual)
            for key in row: close(row[key],summary[k][key],"new daily "+key)
            gap = next(r for r in gaps if int(r["seed"]) == seed and int(r["cluster"]) == k)
            if int(gap["day"]) != day: raise ValueError("Same-source day identity mismatch")
            source_difference = row["total_cost_CNY"]-old_rows[day]["total_cost_CNY"]
            max_source_cost = max(max_source_cost,check_close(source_difference,0.,"same-source cost"))
            close(gap["cost_difference_CNY"],source_difference,"saved same-source cost")
            for key in TOTALS[:-1]: close(gap[key+"_difference"],row[key]-old_rows[day][key],"same-source metric gap")
            rows.append(row)
            count += 1
        name = prefix+"_repeat_cluster0"
        expected_cases.add(name)
        repeated,residual = detailed_metrics(folder/(name+"_hourly.csv"),daily[chosen[0]],storage,thermal,economics,m["cases"][name])
        max_physical = max(max_physical,residual)
        saved_repeat = read_csv(folder/(prefix+"_repeat_summary.csv"))
        if len(saved_repeat) != 1 or saved_repeat[0]["scenario"] != name: raise ValueError("Repeat inventory mismatch")
        for key in repeated:
            close(repeated[key],saved_repeat[0][key],"repeat rebuild")
            close(repeated[key],rows[0][key],"repeat metric")
        repeat_difference = 0.
        for key,value in summary[0].items():
            if key in ("scenario","solver_status"): continue
            repeat_difference = max(repeat_difference,check_close(value,saved_repeat[0][key],"repeat full summary"))
        close(result["repeat_dispatch_difference"],repeat_difference,"repeat summary difference")
        max_repeat = max(max_repeat,repeat_difference)
        count += 1
        metrics, control = annual(rows,weights), annual(rows,c)
        for key,value in metrics.items(): close(value,result[key],"weighted annual")
        for key,value in control.items(): close(value,result["control_"+key],"count control")
        input_errors = []
        for j,channel in enumerate(("load","wind","solar")):
            actual = float(b[j])
            weighted = math.fsum(float(a[j,k])*weights[k] for k in range(48))
            error = abs(weighted-actual)/actual if actual else 0.
            input_errors.append(error)
            close(result[channel+"_relative_error"],error,"channel relative error")
            close(result[channel+"_input_MWh"],weighted,"channel annual input")
        D = max(input_errors)
        E = max(abs(metrics[key]-full[key]) for key in ("renewable_utilization_pct","curtailment_rate_pct"))
        cost_error = metrics["total_cost_CNY"]-full["total_cost_CNY"]
        unserved_error = metrics["unserved_MWh"]-full["unserved_MWh"]
        old_result = next(r for r in prior if int(r["seed"]) == seed)
        improvements = [abs(float(old_result["cost_error_CNY"]))-abs(cost_error),abs(float(old_result["unserved_error_MWh"]))-abs(unserved_error)]
        expected = dict(worst_error_pp=E,max_input_relative_error=D,cost_error_CNY=cost_error,unserved_error_MWh=unserved_error,
                        old_cost_error_CNY=float(old_result["cost_error_CNY"]),old_unserved_error_MWh=float(old_result["unserved_error_MWh"]),
                        cost_absolute_improvement_CNY=improvements[0],unserved_absolute_improvement_MWh=improvements[1],
                        changed_days=sum(day != int(r["day"]) for day,r in zip(chosen,original)))
        for key,value in expected.items(): close(value,result[key],"comparison "+key)
        passed = E <= 1 and D <= .02
        if (result["passes_ED"] == "True") != passed: raise ValueError("ED classification mismatch")
        passes.append(passed)
        reconstructed.append(dict(seed=seed,**expected))
        changes.extend(improvements)
    verdict = "refuted" if any(v < -1e-6 for v in changes) else "supported" if all(passes) and all(v > 1e-6 for v in changes) else "inconclusive"
    if (lp_count,count,len(m["cases"]),m["lp_calls"],m["dispatch_calls"]) != (300,147,147,300,147) or set(m["cases"]) != expected_cases:
        raise ValueError("Solver budget/case identity mismatch")
    if m["verdict"] != verdict or m["details"]["passes_ED"] != passes:
        raise ValueError("Hypothesis verdict mismatch")
    return dict(passed=True,new_solver_calls=0,checked_hashes=hashes,weight_lp_calls=lp_count,dispatch_calls=count,
                baseline_days_reconstructed=365,max_readback_difference=maximum,max_physical_residual=max_physical,
                max_mps_residual=max_mps,max_weight_bound_residual=max_bound,max_normalized_residual=max_normalized,
                max_same_source_cost_difference=max_source_cost,max_repeat_difference=max_repeat,
                verdict=verdict,passes_ED=passes,groups=reconstructed,
                audit_source_sha256=sha(__file__),run_manifest_sha256=sha(folder/"run_manifest.json"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_id")
    p.add_argument("--output",required=True)
    args = p.parse_args()
    try:
        report = audit(ROOT/"results/annual"/args.run_id)
    except Exception as exc:
        report = dict(passed=False,error=repr(exc),new_solver_calls=0,audit_source_sha256=sha(__file__))
    with (ROOT/args.output).open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write("\n")
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if not report["passed"]: raise SystemExit(1)


if __name__ == "__main__":
    main()
