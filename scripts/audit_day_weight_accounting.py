"""Independent standard-library replay of U11R13; no src/optimizer imports."""
import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_cost_unserved_attribution import COSTS, METRICS, detailed_metrics
from scripts.audit_fixed_weights_capacity_transfer import read_csv, check_close, annual, sha

SEEDS = (42,7,2026)
PATH_COLUMNS = ("Y00","Y10","Y01","Y11","delta","day_first","weight_after_day",
                "weight_first","day_after_weight","interaction","day_average","weight_average")
ACCOUNT_COLUMNS = ("full","control","calibrated","replacement","adjustment","total","gross_cluster_error","cancellation_fraction")


def unique(rows,fields):
    result = {tuple(row[key] for key in fields):row for row in rows}
    if len(result) != len(rows): raise ValueError("Duplicate output identity")
    return result


def audit(folder):
    m = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    frozen = ROOT/"instructions/studies/U11R13-day-weight-accounting/freeze.json"
    if m["status"] != "complete" or m["unit"] != "U11R13-day-weight-accounting" or m["cases"] or m["details"]["new_solver_calls"] != 0:
        raise ValueError("Incomplete/nonzero-solve analysis")
    if sha(frozen) != m["freeze_sha256"] or json.loads(frozen.read_text(encoding="utf-8")) != m["freeze"]:
        raise ValueError("Freeze identity mismatch")
    checked = 1
    for entries,base in ((m["freeze"]["sha256"],ROOT),(m["source_sha256"],ROOT),(m["artifacts"],folder)):
        for path,digest in entries.items():
            if sha(base/path) != digest: raise ValueError("Hash mismatch: "+path)
            checked += 1
    if {p.name for p in folder.iterdir() if p.is_file() and p.name != "run_manifest.json"} != set(m["artifacts"]):
        raise ValueError("Artifact inventory mismatch")
    expected_params = dict(N=48,seeds=list(SEEDS),energy_capacity_MWh=40,power_capacity_MW=20,new_solver_calls=0,source_dispatches=653,
                           metrics=list(METRICS),counterfactuals=["old_count","new_count","Y00","Y10","Y01","Y11"],tolerance=1e-6,retrospective=True)
    if m["parameters"] != expected_params: raise ValueError("Parameter mismatch")
    cfg = m["freeze"]["config"]
    storage = cfg["storage.json"]
    thermal = {key:cfg["optimization.json"][key] for key in ("thermal_min_MW","thermal_ramp_MW_per_h")}
    thermal["thermal_max_MW"] = cfg["no_storage.json"]["thermal_max_MW"]
    economics = cfg["economics.json"]["parameters"]
    source = read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")
    if len(source) != 8760 or storage["energy_capacity_MWh"] != 40 or storage["power_capacity_MW"] != 20:
        raise ValueError("Input/capacity mismatch")
    folders = {key:ROOT/"results/annual"/key for key in ("U11R02-v01","U11R08B-v01","U11R12-v01")}
    manifests = {key:json.loads((p/"run_manifest.json").read_text(encoding="utf-8")) for key,p in folders.items()}
    for old in manifests.values():
        if old["status"] != "complete": raise ValueError("Incomplete predecessor")
        for key in ("storage","optimization","no_storage","economics"):
            if old["freeze"]["config"][key+".json"] != cfg[key+".json"]: raise ValueError("Predecessor configuration mismatch")
    preflight = json.loads((ROOT/"results/annual/U11R13-predecessor-audit-v01.json").read_text(encoding="utf-8"))
    if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(folders["U11R12-v01"]/"run_manifest.json"):
        raise ValueError("Predecessor audit mismatch")
    tables = {name:read_csv(folder/(name+".csv")) for name in ("annual_decomposition","cluster_decomposition","path_decomposition","path_clusters","counterfactuals","cost_decomposition","same_source_gaps")}
    if [len(tables[k]) for k in tables] != [84,4032,42,2016,18,36,4032]: raise ValueError("Output dimensions mismatch")
    ai = unique(tables["annual_decomposition"],("seed","day_set","metric"))
    ci = unique(tables["cluster_decomposition"],("seed","day_set","metric","cluster"))
    pi = unique(tables["path_decomposition"],("seed","metric"))
    pci = unique(tables["path_clusters"],("seed","metric","cluster"))
    combos = unique(tables["counterfactuals"],("seed","combination"))
    fees = unique(tables["cost_decomposition"],("seed","day_set","metric"))
    gaps = unique(tables["same_source_gaps"],("seed","day_set","metric","cluster"))
    maximum = physical = identity = same_cost = 0.
    count = 0

    def check(a,b,label):
        nonlocal maximum
        maximum = max(maximum,check_close(a,b,label))

    full_rows = []
    saved = read_csv(folder/"reconstructed_full.csv")
    original_daily = read_csv(folders["U11R02-v01"]/"daily_summary.csv")
    if len(saved) != 365 or [r["scenario"] for r in original_daily] != [f"day_{d:03d}" for d in range(365)]: raise ValueError("Full source inventory mismatch")
    for d in range(365):
        name = f"day_{d:03d}"
        row,residual = detailed_metrics(folders["U11R02-v01"]/(name+"_hourly.csv"),source[d*24:(d+1)*24],storage,thermal,economics,manifests["U11R02-v01"]["cases"][name])
        for key in METRICS:
            check(row[key],saved[d][key],"full rebuild")
            check(row[key],original_daily[d][key],"full original")
        full_rows.append(row)
        physical = max(physical,residual)
        count += 1
    full = annual(full_rows,[1.]*365)
    old_full = read_csv(folders["U11R02-v01"]/"full_annual.csv")[0]
    for key,value in full.items(): check(value,old_full[key],"full annual")
    old_account = unique(read_csv(ROOT/"results/annual/U11R11-v01/annual_decomposition.csv"),("capacity_scenario","seed","metric"))
    rebuilt = {}
    combo_details = []
    for seed in SEEDS:
        prefix = f"N48_seed{seed}"
        labels = read_csv(folders["U11R08B-v01"]/(prefix+"_labels.csv"))
        if len(labels) != 365 or [int(r["day"]) for r in labels] != list(range(365)): raise ValueError("Cluster day ordering mismatch")
        labs = [int(r["cluster"]) for r in labels]
        if set(labs) != set(range(48)): raise ValueError("Incomplete cluster set")
        sets = {}
        for side,key in (("old","U11R08B-v01"),("new","U11R12-v01")):
            reps = read_csv(folders[key]/(prefix+"_representatives.csv"))
            summary = read_csv(folders[key]/(prefix+"_summary.csv"))
            saved = read_csv(folder/(prefix+"_"+side+"_reconstructed.csv"))
            if len(reps) != 48 or len(saved) != 48 or [r["scenario"] for r in summary] != [prefix+f"_cluster{k}" for k in range(48)]: raise ValueError("Representative inventory mismatch")
            chosen = [int(r["day"]) for r in reps]
            weights = [float(r["effective_days"]) for r in reps]
            counts = [labs.count(k) for k in range(48)]
            if len(set(chosen)) != 48 or abs(math.fsum(weights)-365.) > 1e-6: raise ValueError("Representative/weight identity mismatch")
            rows = []
            for k,rep in enumerate(reps):
                d = chosen[k]
                if int(rep["cluster"]) != k or not 0 <= d < 365 or labs[d] != k or int(rep["days"]) != counts[k] or not .5*counts[k]-1e-6 <= weights[k] <= 2*counts[k]+1e-6 or float(rep["repeat_days"]) != weights[k] or rep["date_UTC"] != (date(2023,1,1)+timedelta(days=d)).isoformat():
                    raise ValueError("Frozen representative metadata mismatch")
                check(rep["effective_probability"],weights[k]/365.,"weight probability")
                name = prefix+f"_cluster{k}"
                row,residual = detailed_metrics(folders[key]/(name+"_hourly.csv"),source[d*24:(d+1)*24],storage,thermal,economics,manifests[key]["cases"][name])
                for metric in METRICS:
                    check(row[metric],saved[k][metric],"representative reconstruction")
                    check(row[metric],summary[k][metric],"representative original")
                    gap = row[metric]-full_rows[d][metric]
                    check(gap,gaps[(str(seed),side,metric,str(k))]["difference"],"same-source gap")
                    if metric == "total_cost_CNY": same_cost = max(same_cost,check_close(gap,0.,"same-source cost"))
                rows.append(row)
                physical = max(physical,residual)
                count += 1
            original_comparison = [r for r in read_csv(folders[key]/"comparison.csv") if int(r["N"]) == 48 and int(r["seed"]) == seed]
            if len(original_comparison) != 1: raise ValueError("Original comparison mismatch")
            old_compare = original_comparison[0]
            for metric in METRICS:
                F = math.fsum(r[metric] for r in full_rows)
                C = math.fsum(c*r[metric] for c,r in zip(counts,rows))
                W = math.fsum(w*r[metric] for w,r in zip(weights,rows))
                S,A,T = C-F,W-C,W-F
                cluster_terms = []
                for k,rep in enumerate(reps):
                    actual = math.fsum(full_rows[d][metric] for d in range(365) if labs[d] == k)
                    s,a,t = counts[k]*rows[k][metric]-actual,(weights[k]-counts[k])*rows[k][metric],weights[k]*rows[k][metric]-actual
                    values = dict(cluster_full=actual,representative_value=rows[k][metric],replacement=s,adjustment=a,total=t)
                    original = ci[(str(seed),side,metric,str(k))]
                    for column,value in values.items(): check(value,original[column],"cluster "+column)
                    for column in ("day","days","effective_days"): check(rep[column],original[column],"cluster metadata")
                    if rep["date_UTC"] != original["date_UTC"]: raise ValueError("Cluster date mismatch")
                    identity = max(identity,check_close(t,s+a,"cluster identity"))
                    cluster_terms.append((s,a,t))
                for index,value in enumerate((S,A,T)): identity = max(identity,check_close(value,math.fsum(r[index] for r in cluster_terms),"annual cluster sum"))
                identity = max(identity,check_close(T,S+A,"annual accounting identity"))
                gross = math.fsum(abs(r[2]) for r in cluster_terms)
                values = dict(full=F,control=C,calibrated=W,replacement=S,adjustment=A,total=T,gross_cluster_error=gross,
                              cancellation_fraction=1-abs(math.fsum(r[2] for r in cluster_terms))/gross if gross else 0.)
                saved_row = ai[(str(seed),side,metric)]
                state = "increased" if abs(T)-abs(S) > 1e-6 else "reduced" if abs(T)-abs(S) < -1e-6 else "unchanged"
                if saved_row["weight_effect"] != state: raise ValueError("Weight-effect classification mismatch")
                for column,value in values.items(): check(value,saved_row[column],"annual "+column)
                if metric in COSTS:
                    if fees[(str(seed),side,metric)] != saved_row: raise ValueError("Fee subset mismatch")
                if metric in old_compare: check(W,old_compare[metric],"original annual weighted")
                if "control_"+metric in old_compare: check(C,old_compare["control_"+metric],"original count control")
                if side == "old":
                    previous = old_account[("E40_P20",str(seed),metric)]
                    for column in ACCOUNT_COLUMNS[:6]: check(values[column],previous[column],"R11 accounting")
                if metric in ("total_cost_CNY","unserved_MWh"):
                    check(T,old_compare["cost_error_CNY" if metric == "total_cost_CNY" else "unserved_error_MWh"],"prior signed error")
                rebuilt[(seed,side,metric)] = values
            for column in ACCOUNT_COLUMNS[:6]:
                identity = max(identity,check_close(math.fsum(rebuilt[(seed,side,k)][column] for k in COSTS),rebuilt[(seed,side,"total_cost_CNY")][column],"six-fee accounting"),
                               check_close(economics["load_shedding_penalty_CNY_per_MWh"]*rebuilt[(seed,side,"unserved_MWh")][column],rebuilt[(seed,side,"load_shedding_cost_CNY")][column],"shortage accounting"))
            sets[side] = reps,chosen,weights,rows,counts
        r0,d0,w0,v0,c = sets["old"]
        r1,d1,w1,v1,c1 = sets["new"]
        if c != c1: raise ValueError("Counts changed between day sets")
        cross_metrics = {}
        for metric in METRICS:
            cells = []
            for k in range(48):
                x,y = v0[k][metric],v1[k][metric]
                p = w0[k]*(y-x)
                q = (w1[k]-w0[k])*x
                I = (w1[k]-w0[k])*(y-x)
                values = dict(Y00=w0[k]*x,Y10=w0[k]*y,Y01=w1[k]*x,Y11=w1[k]*y,delta=w1[k]*y-w0[k]*x,
                              day_first=p,weight_after_day=(w1[k]-w0[k])*y,weight_first=q,day_after_weight=w1[k]*(y-x),
                              interaction=I,day_average=(w0[k]+w1[k])*(y-x)/2.,weight_average=(w1[k]-w0[k])*(x+y)/2.)
                saved_row = pci[(str(seed),metric,str(k))]
                for column,value in values.items(): check(value,saved_row[column],"cluster path "+column)
                for column,value in dict(old_day=d0[k],new_day=d1[k],old_weight=w0[k],new_weight=w1[k]).items(): check(value,saved_row[column],"path metadata")
                for a,b in ((values["delta"],values["day_first"]+values["weight_after_day"]),(values["delta"],values["weight_first"]+values["day_after_weight"]),
                            (I,values["day_after_weight"]-values["day_first"]),(I,values["weight_after_day"]-values["weight_first"]),
                            (values["delta"],values["day_average"]+values["weight_average"])):
                    identity = max(identity,check_close(a,b,"cluster path identity"))
                cells.append(values)
            values = {column:math.fsum(r[column] for r in cells) for column in PATH_COLUMNS}
            for column,value in values.items(): check(value,pi[(str(seed),metric)][column],"annual path "+column)
            for a,b in ((values["delta"],values["Y11"]-values["Y00"]),(values["delta"],values["day_first"]+values["weight_after_day"]),
                        (values["delta"],values["weight_first"]+values["day_after_weight"]),(values["delta"],values["day_average"]+values["weight_average"]),
                        (values["interaction"],values["day_after_weight"]-values["day_first"]),(values["interaction"],values["weight_after_day"]-values["weight_first"])):
                identity = max(identity,check_close(a,b,"annual path identity"))
            cross_metrics[metric] = values
        for column in PATH_COLUMNS:
            identity = max(identity,check_close(math.fsum(cross_metrics[k][column] for k in COSTS),cross_metrics["total_cost_CNY"][column],"path six fees"),
                           check_close(economics["load_shedding_penalty_CNY_per_MWh"]*cross_metrics["unserved_MWh"][column],cross_metrics["load_shedding_cost_CNY"][column],"path shortage fees"))
        for name,days,rows,w in (("old_count",d0,v0,c),("new_count",d1,v1,c),("Y00",d0,v0,w0),("Y10",d1,v1,w0),("Y01",d0,v0,w1),("Y11",d1,v1,w1)):
            metrics = annual(rows,w)
            saved_row = combos[(str(seed),name)]
            for column,value in metrics.items(): check(value,saved_row[column],"counterfactual annual")
            errors = []
            for channel in ("load","wind","solar"):
                actual = math.fsum(float(r[channel]) for r in source)
                estimated = math.fsum(weight*math.fsum(float(r[channel]) for r in source[day*24:(day+1)*24]) for day,weight in zip(days,w))
                error = abs(estimated-actual)/actual if actual else (0. if estimated == 0 else math.inf)
                check(estimated,saved_row[channel+"_input_MWh"],"counterfactual input")
                check(error,saved_row[channel+"_relative_error"],"counterfactual channel error")
                errors.append(error)
            D = max(errors)
            E = max(abs(metrics[k]-full[k]) for k in ("renewable_utilization_pct","curtailment_rate_pct"))
            for column,value in dict(max_input_relative_error=D,worst_error_pp=E,cost_error_CNY=metrics["total_cost_CNY"]-full["total_cost_CNY"],unserved_error_MWh=metrics["unserved_MWh"]-full["unserved_MWh"]).items(): check(value,saved_row[column],"counterfactual error")
            if (saved_row["passes_ED"] == "True") != (E <= 1 and D <= .02): raise ValueError("Counterfactual pass classification mismatch")
            combo_details.append(dict(seed=seed,combination=name,E=E,D=D,passes_ED=E <= 1 and D <= .02))
    if count != 653: raise ValueError("Source readback budget mismatch")
    decisions = []
    for seed in SEEDS:
        for metric in ("total_cost_CNY","unserved_MWh"):
            row = rebuilt[(seed,"new",metric)]
            increase = abs(row["total"])-abs(row["replacement"])
            state = "increased" if increase > 1e-6 else "reduced" if increase < -1e-6 else "unchanged"
            decisions.append(dict(seed=seed,metric=metric,count_error=row["replacement"],calibrated_error=row["total"],absolute_error_increase=increase,state=state))
    states = {r["state"] for r in decisions}
    verdict = "refuted" if "reduced" in states else "inconclusive" if "unchanged" in states else "supported"
    h = json.loads((folder/"hypothesis.json").read_text(encoding="utf-8"))
    if m["verdict"] != verdict or h["verdict"] != verdict or h["retrospective"] is not True or h["hypothesis"] != "new_weights_increase_cost_and_unserved_absolute_errors" or len(h["groups"]) != 6:
        raise ValueError("Retrospective verdict mismatch")
    for saved,expected in zip(h["groups"],decisions):
        for column,value in expected.items():
            if isinstance(value,float): check(value,saved[column],"hypothesis readback")
            elif value != saved[column]: raise ValueError("Hypothesis identity/state mismatch")
    for column,value in dict(new_solver_calls=0,source_dispatches=653,groups=6,annual_rows=84,cluster_rows=4032,path_rows=42,path_cluster_rows=2016,counterfactual_rows=18).items():
        if m["details"][column] != value: raise ValueError("Manifest count mismatch")
    return dict(passed=True,new_solver_calls=0,checked_hashes=checked,source_dispatches=count,max_physical_residual=physical,
                max_readback_difference=maximum,max_identity_difference=identity,max_same_source_cost_difference=same_cost,
                verdict=verdict,retrospective=True,hypothesis=decisions,counterfactuals=combo_details,
                run_manifest_sha256=sha(folder/"run_manifest.json"),audit_source_sha256=sha(__file__))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_id")
    p.add_argument("--output",required=True)
    args = p.parse_args()
    try: report = audit(ROOT/"results/annual"/args.run_id)
    except Exception as exc: report = dict(passed=False,error=repr(exc),new_solver_calls=0,audit_source_sha256=sha(__file__))
    with (ROOT/args.output).open("x",encoding="utf-8") as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write("\n")
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if not report["passed"]: raise SystemExit(1)


if __name__ == "__main__":
    main()
