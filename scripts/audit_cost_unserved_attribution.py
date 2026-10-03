"""Independent stdlib replay of U11R11's old hourly evidence and accounting."""
import argparse
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_fixed_weights_capacity_transfer import read_csv, saved_metrics, check_close

COSTS = ("thermal_cost_CNY", "curtailment_cost_CNY", "load_shedding_cost_CNY",
         "storage_variable_om_CNY", "storage_investment_allocated_CNY", "storage_fixed_om_CNY")
METRICS = ("renewable_available_MWh", "renewable_used_MWh", "curtailment_MWh",
           "total_load_MWh", "thermal_generation_MWh", "unserved_MWh", "discharge_MWh",
           "total_cost_CNY") + COSTS
SCENARIOS = (("E0_P0", 0., 0.), ("E40_P20", 40., 20.), ("E80_P20", 80., 20.))
SEEDS = (42, 7, 2026)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def detailed_metrics(path, source, storage, thermal, p, info):
    row, residual, operating = saved_metrics(path, source, storage, thermal, p)
    check_close(operating, info["objective_CNY"], "original operating objective")
    if info["solver_status"] != "Optimal" or info["model_class"] != "MILP" or info["storage"] != storage or info["thermal"] != thermal or info["dt"] != 1. or not info["terminal"]:
        raise ValueError("Saved source identity/state mismatch")
    log = path.with_name(path.name.replace("_hourly.csv", "_cbc.log")).read_text(encoding="utf-8")
    if not any(x in log for x in ("Result - Optimal solution found", "Optimal objective")):
        raise ValueError("Missing original Optimal log")
    q = read_csv(path)
    discharge = math.fsum(float(r["discharge"]) for r in q)
    rate = p["discount_rate"]
    crf = rate/-math.expm1(-p["storage_lifetime_years"]*math.log1p(rate)) if rate else 1/p["storage_lifetime_years"]
    capex = 1000*(storage["energy_capacity_MWh"]*p["storage_energy_capex_CNY_per_kWh"]+storage["power_capacity_MW"]*p["storage_power_capex_CNY_per_kW"])
    row.update(discharge_MWh=discharge,
               thermal_cost_CNY=row["thermal_generation_MWh"]*p["thermal_cost_CNY_per_MWh"],
               curtailment_cost_CNY=row["curtailment_MWh"]*p["curtailment_penalty_CNY_per_MWh"],
               load_shedding_cost_CNY=row["unserved_MWh"]*p["load_shedding_penalty_CNY_per_MWh"],
               storage_variable_om_CNY=discharge*p["storage_variable_om_CNY_per_MWh_discharged"],
               storage_investment_allocated_CNY=capex*crf*24/p["hours_per_year"],
               storage_fixed_om_CNY=capex*p["storage_fixed_om_fraction_per_year"]*24/p["hours_per_year"])
    check_close(math.fsum(row[k] for k in COSTS), row["total_cost_CNY"], "daily six fees")
    return {k:row[k] for k in METRICS}, residual


def audit(folder):
    m = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    frozen = ROOT/"instructions/studies/U11R11-cost-unserved-attribution/freeze.json"
    if m["status"] != "complete" or m["unit"] != "U11R11-cost-unserved-attribution" or m["cases"] or m["details"]["new_solver_calls"] != 0:
        raise ValueError("Incomplete/nonzero-solve analysis")
    if sha(frozen) != m["freeze_sha256"] or json.loads(frozen.read_text(encoding="utf-8")) != m["freeze"]:
        raise ValueError("Freeze identity mismatch")
    checked = 1
    for paths, base in ((m["freeze"]["sha256"], ROOT), (m["source_sha256"], ROOT), (m["artifacts"], folder)):
        for path, digest in paths.items():
            if sha(base/path) != digest:
                raise ValueError("Hash mismatch: "+path)
            checked += 1
    if {p.name for p in folder.iterdir() if p.is_file() and p.name != "run_manifest.json"} != set(m["artifacts"]):
        raise ValueError("Artifact inventory mismatch")
    expected_params = dict(scenarios=[list(x) for x in SCENARIOS], seeds=list(SEEDS), N=48,
                           new_solver_calls=0, source_dispatches=1527, top_count=5,
                           metrics=list(METRICS), costs=list(COSTS), hypothesis_seed=7, accounting_tolerance=1e-6)
    if m["parameters"] != expected_params:
        raise ValueError("Frozen analysis parameter mismatch")
    cfg = m["freeze"]["config"]
    base = cfg["storage.json"]
    thermal = {k:cfg["optimization.json"][k] for k in ("thermal_min_MW", "thermal_ramp_MW_per_h")}
    thermal["thermal_max_MW"] = cfg["no_storage.json"]["thermal_max_MW"]
    economics = cfg["economics.json"]["parameters"]
    source = read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")
    folders = {key:ROOT/"results/annual"/key for key in ("U11R02-v01", "U11R08B-v01", "U11R10-v01")}
    original = {key:json.loads((p/"run_manifest.json").read_text(encoding="utf-8")) for key,p in folders.items()}
    for old in original.values():
        if old["status"] != "complete":
            raise ValueError("Incomplete predecessor")
        for key in ("storage", "optimization", "no_storage", "economics"):
            if old["freeze"]["config"][key+".json"] != cfg[key+".json"]:
                raise ValueError("Predecessor configuration mismatch")
    preflight = json.loads((ROOT/"results/annual/U11R11-predecessor-audit-v01.json").read_text(encoding="utf-8"))
    if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(folders["U11R10-v01"]/"run_manifest.json"):
        raise ValueError("Predecessor audit mismatch")
    annual_saved = read_csv(folder/"annual_decomposition.csv")
    clusters_saved = read_csv(folder/"cluster_decomposition.csv")
    gap_saved = read_csv(folder/"same_source_gaps.csv")
    fee_saved = read_csv(folder/"cost_decomposition.csv")
    top_saved = read_csv(folder/"top_contributors.csv")
    if (len(annual_saved), len(clusters_saved), len(gap_saved), len(fee_saved), len(top_saved)) != (126, 6048, 6048, 54, 90):
        raise ValueError("Incomplete output dimensions")

    def index(rows, fields):
        result = {tuple(row[k] for k in fields):row for row in rows}
        if len(result) != len(rows):
            raise ValueError("Duplicate output identity")
        return result

    annual_index = index(annual_saved, ("capacity_scenario", "seed", "metric"))
    cluster_index = index(clusters_saved, ("capacity_scenario", "seed", "metric", "cluster"))
    gap_index = index(gap_saved, ("capacity_scenario", "seed", "metric", "cluster"))
    fee_index = index(fee_saved, ("capacity_scenario", "seed", "metric"))
    maximum = residual_max = same_day_cost_max = 0.
    count = 0
    rebuilt = {}

    def check(a, b, label):
        nonlocal maximum
        maximum = max(maximum, check_close(a, b, label))

    for scenario, energy, power in SCENARIOS:
        st = dict(base, energy_capacity_MWh=energy, power_capacity_MW=power)
        full_key, rep_key, prefix = ("U11R02-v01", "U11R08B-v01", "") if energy == 40 else ("U11R10-v01", "U11R10-v01", scenario+"_")
        full = []
        recorded_full = read_csv(folder/(scenario+"_reconstructed_full.csv"))
        old_summary = read_csv(folders[full_key]/(prefix+"daily_summary.csv"))
        if len(recorded_full) != 365 or [r["scenario"] for r in old_summary] != [prefix+f"day_{d:03d}" for d in range(365)]:
            raise ValueError("Full-day inventory/order mismatch")
        for day in range(365):
            name = prefix+f"day_{day:03d}"
            row, residual = detailed_metrics(folders[full_key]/(name+"_hourly.csv"), source[day*24:(day+1)*24], st, thermal, economics, original[full_key]["cases"][name])
            for metric in METRICS:
                check(row[metric], recorded_full[day][metric], "rebuilt full")
                check(row[metric], old_summary[day][metric], "original full")
            residual_max = max(residual_max, residual)
            full.append(row)
            count += 1
        original_full = read_csv(folders[full_key]/"full_annual.csv")
        saved_full = original_full[0] if energy == 40 else next(r for r in original_full if r["capacity_scenario"] == scenario)
        for metric in METRICS:
            if metric in saved_full:
                check(math.fsum(r[metric] for r in full), saved_full[metric], "original annual baseline")
        for seed in SEEDS:
            reps = read_csv(folders["U11R08B-v01"]/f"N48_seed{seed}_representatives.csv")
            labels = read_csv(folders["U11R08B-v01"]/f"N48_seed{seed}_labels.csv")
            if len(reps) != 48 or len(labels) != 365 or [int(r["day"]) for r in labels] != list(range(365)):
                raise ValueError("Original fixed-day dimensions/order")
            labs = [int(r["cluster"]) for r in labels]
            weights = [float(r["effective_days"]) for r in reps]
            if len({int(r["day"]) for r in reps}) != 48 or set(labs) != set(range(48)):
                raise ValueError("Invalid fixed-day uniqueness/membership")
            for k, r in enumerate(reps):
                if int(r["cluster"]) != k or labs[int(r["day"])] != k or labs.count(k) != float(r["days"]) or float(r["repeat_days"]) != weights[k] or not .5*float(r["days"])-1e-6 <= weights[k] <= 2*float(r["days"])+1e-6:
                    raise ValueError("Fixed cluster/weight mismatch")
                if r["date_UTC"] != (date(2023,1,1)+timedelta(days=int(r["day"]))).isoformat():
                    raise ValueError("Original UTC date mismatch")
            check(math.fsum(weights), 365., "fixed weight sum")
            p = prefix+f"N48_seed{seed}"
            recorded_reps = read_csv(folder/(p+"_reconstructed_representatives.csv"))
            old_summary = read_csv(folders[rep_key]/(p+"_summary.csv"))
            if len(recorded_reps) != 48 or [r["scenario"] for r in old_summary] != [p+f"_cluster{k}" for k in range(48)]:
                raise ValueError("Original representative inventory/order")
            rows = []
            for k, r in enumerate(reps):
                day = int(r["day"])
                name = p+f"_cluster{k}"
                row, residual = detailed_metrics(folders[rep_key]/(name+"_hourly.csv"), source[day*24:(day+1)*24], st, thermal, economics, original[rep_key]["cases"][name])
                for metric in METRICS:
                    check(row[metric], recorded_reps[k][metric], "rebuilt representative")
                    check(row[metric], old_summary[k][metric], "original representative")
                    gap = row[metric]-full[day][metric]
                    check(gap, gap_index[(scenario, str(seed), metric, str(k))]["difference"], "same-source gap")
                    if metric == "total_cost_CNY":
                        same_day_cost_max = max(same_day_cost_max, check_close(gap, 0., "same-source cost"))
                residual_max = max(residual_max, residual)
                rows.append(row)
                count += 1
            for metric in METRICS:
                actual = math.fsum(r[metric] for r in full)
                control = math.fsum(float(rep["days"])*r[metric] for rep,r in zip(reps,rows))
                calibrated = math.fsum(w*r[metric] for w,r in zip(weights,rows))
                s, a, t = control-actual, calibrated-control, calibrated-actual
                terms = []
                for k, rep in enumerate(reps):
                    key = (scenario, str(seed), metric, str(k))
                    saved = cluster_index[key]
                    cluster_actual = math.fsum(r[metric] for d,r in enumerate(full) if labs[d] == k)
                    sk = float(rep["days"])*rows[k][metric]-cluster_actual
                    ak = (weights[k]-float(rep["days"]))*rows[k][metric]
                    tk = weights[k]*rows[k][metric]-cluster_actual
                    for column,value in dict(cluster_full=cluster_actual, representative_value=rows[k][metric], replacement=sk, adjustment=ak, total=tk).items():
                        check(value, saved[column], "cluster "+column)
                    check(tk, sk+ak, "cluster identity")
                    for column in ("day", "date_UTC", "days", "effective_days"):
                        if column == "date_UTC":
                            if rep[column] != saved[column]: raise ValueError("Cluster source date mismatch")
                        else:
                            check(rep[column], saved[column], "cluster metadata")
                    terms.append((sk,ak,tk))
                for j,value in enumerate((s,a,t)):
                    check(math.fsum(r[j] for r in terms), value, "cluster annual identity")
                gross = math.fsum(abs(r[2]) for r in terms)
                cancellation = 1-abs(math.fsum(r[2] for r in terms))/gross if gross else 0.
                weight_effect = "reduced" if abs(t)-abs(s) < -1e-6 else "increased" if abs(t)-abs(s) > 1e-6 else "unchanged"
                key = (scenario,str(seed),metric)
                expected = dict(full=actual, control=control, calibrated=calibrated, replacement=s,
                                adjustment=a, total=t, gross_cluster_error=gross, cancellation_fraction=cancellation)
                for column,value in expected.items():
                    check(value, annual_index[key][column], "annual "+column)
                    if metric in COSTS: check(value, fee_index[key][column], "fee "+column)
                if annual_index[key]["weight_effect"] != weight_effect or metric in COSTS and fee_index[key]["weight_effect"] != weight_effect:
                    raise ValueError("Weight-effect classification mismatch")
                check(t,s+a,"annual identity")
                rebuilt[key] = expected
            original_comparison = [r for r in read_csv(folders[rep_key]/"comparison.csv")
                                   if int(r["N"]) == 48 and int(r["seed"]) == seed
                                   and (energy == 40 or r["capacity_scenario"] == scenario)]
            if len(original_comparison) != 1:
                raise ValueError("Original comparison matrix mismatch")
            saved_comparison = original_comparison[0]
            for metric in METRICS:
                if metric in saved_comparison:
                    check(rebuilt[(scenario,str(seed),metric)]["calibrated"], saved_comparison[metric], "original weighted total")
            for metric,column in (("total_cost_CNY","cost_error_CNY"),("unserved_MWh","unserved_error_MWh")):
                check(rebuilt[(scenario,str(seed),metric)]["total"], saved_comparison[column], "original recorded error")
            for column in ("full","control","calibrated","replacement","adjustment","total"):
                check(math.fsum(rebuilt[(scenario,str(seed),k)][column] for k in COSTS), rebuilt[(scenario,str(seed),"total_cost_CNY")][column], "six-cost identity")
                check(economics["load_shedding_penalty_CNY_per_MWh"]*rebuilt[(scenario,str(seed),"unserved_MWh")][column], rebuilt[(scenario,str(seed),"load_shedding_cost_CNY")][column], "shortage-cost identity")
    if count != 1527:
        raise ValueError("Readback budget mismatch")
    expected_top = []
    for scenario in sorted(x[0] for x in SCENARIOS):
        for seed in sorted(SEEDS):
            for metric in sorted(("total_cost_CNY","unserved_MWh")):
                candidates = [r for r in clusters_saved if r["capacity_scenario"] == scenario and int(r["seed"]) == seed and r["metric"] == metric]
                expected_top.extend(sorted(candidates,key=lambda r:(-abs(float(r["total"])),int(r["cluster"])))[:5])
    if [(r["capacity_scenario"],r["seed"],r["metric"],r["cluster"]) for r in top_saved] != [(r["capacity_scenario"],r["seed"],r["metric"],r["cluster"]) for r in expected_top]:
        raise ValueError("Top-five ordering mismatch")
    for saved,expected in zip(top_saved,expected_top):
        for column in expected:
            if saved[column] != expected[column]: raise ValueError("Top-five content mismatch")
        check(saved["absolute_total"],abs(float(expected["total"])),"top magnitude")
    states, decisions = [], []
    for scenario,_,_ in SCENARIOS:
        shortage = abs(rebuilt[(scenario,"7","load_shedding_cost_CNY")]["total"])
        other = max(abs(rebuilt[(scenario,"7",k)]["total"]) for k in COSTS if k != "load_shedding_cost_CNY")
        margin = shortage-other
        state = "dominant" if margin > 1e-6 else "other_dominant" if margin < -1e-6 else "tie"
        states.append(state)
        decisions.append(dict(capacity_scenario=scenario,seed=7,shortage_abs_CNY=shortage,next_abs_CNY=other,margin_CNY=margin,state=state))
    verdict = "refuted" if "other_dominant" in states else "inconclusive" if "tie" in states else "supported"
    decision = json.loads((folder/"hypothesis.json").read_text(encoding="utf-8"))
    if m["verdict"] != verdict or decision["verdict"] != verdict or decision["hypothesis"] != "seed7_shortage_fee_dominates_three_capacities" or len(decision["groups"]) != 3:
        raise ValueError("Hypothesis verdict mismatch")
    for saved,expected in zip(decision["groups"],decisions):
        for key,value in expected.items():
            if isinstance(value,float): check(saved[key],value,"hypothesis "+key)
            elif saved[key] != value: raise ValueError("Hypothesis group mismatch")
    for field,value in dict(reconstructed_full_days=1095,reconstructed_representative_days=432,groups=9,annual_rows=126,cluster_rows=6048).items():
        if m["details"][field] != value: raise ValueError("Manifest count mismatch")
    return dict(passed=True,checked_hashes=checked,new_solver_calls=0,reconstructed_full_days=1095,
                reconstructed_representative_days=432,annual_rows=126,cluster_rows=6048,
                max_physical_residual=residual_max,max_readback_difference=maximum,
                max_same_day_cost_difference=same_day_cost_max,verdict=verdict,
                hypothesis=decisions,audit_source_sha256=sha(__file__),run_manifest_sha256=sha(folder/"run_manifest.json"))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        report=audit(ROOT/"results/annual"/args.run_id)
    except Exception as exc:
        report=dict(passed=False,error=repr(exc),new_solver_calls=0,audit_source_sha256=sha(__file__))
    with (ROOT/args.output).open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write("\n")
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if not report["passed"]: raise SystemExit(1)


if __name__=="__main__":
    main()
