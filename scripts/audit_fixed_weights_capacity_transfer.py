"""U11R10 saved-result audit; stdlib arithmetic, no optimizer/src imports."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.independent_dispatch_audit import audit_file

TOTALS = ("renewable_available_MWh", "renewable_used_MWh", "curtailment_MWh",
          "total_load_MWh", "thermal_generation_MWh", "unserved_MWh", "total_cost_CNY")
RATES = ("renewable_utilization_pct", "curtailment_rate_pct")
SCENARIOS = (("E0_P0", 0., 0.), ("E80_P20", 80., 20.))
SEEDS = (42, 7, 2026)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def annual(rows, weights):
    if len(rows) != len(weights) or not rows or not all(math.isfinite(w) and w >= 0 for w in weights):
        raise ValueError("Invalid annual rows/weights")
    totals = {key: math.fsum(float(row[key])*w for row, w in zip(rows, weights)) for key in TOTALS}
    if not all(math.isfinite(x) for x in totals.values()) or totals["renewable_available_MWh"] <= 0:
        raise ValueError("Invalid annual denominator/totals")
    totals["renewable_utilization_pct"] = 100*totals["renewable_used_MWh"]/totals["renewable_available_MWh"]
    totals["curtailment_rate_pct"] = 100*totals["curtailment_MWh"]/totals["renewable_available_MWh"]
    return totals


def saved_metrics(path, source, storage, thermal, economics):
    residual = audit_file(path, storage, thermal)
    q = [{k: float(v) if v else math.nan for k, v in r.items()} for r in read_csv(path)]
    if len(q) != 24 or len(source) != 24:
        raise ValueError("Wrong daily source/output length")
    for i, (row, original) in enumerate(zip(q, source)):
        for output, key in (("load", "load"), ("wind_available", "wind"), ("solar_available", "solar")):
            error = abs(row[output]-float(original[key]))
            if not math.isfinite(error) or error >= 1e-6:
                raise ValueError("Hourly source mismatch")
        if row["hour"] != i:
            raise ValueError("Source day hour reset mismatch")
    pairs = dict(renewable_available_MWh=("wind_available", "solar_available"),
                 renewable_used_MWh=("wind_used", "solar_used"), curtailment_MWh=("wind_curt", "solar_curt"),
                 total_load_MWh=("load",), thermal_generation_MWh=("thermal",), unserved_MWh=("unserved",))
    totals = {key: sum(math.fsum(r[field] for r in q) for field in fields) for key, fields in pairs.items()}
    discharge = math.fsum(r["discharge"] for r in q)
    p = economics
    rate = p["discount_rate"]
    crf = rate/-math.expm1(-p["storage_lifetime_years"]*math.log1p(rate)) if rate else 1/p["storage_lifetime_years"]
    capex = 1000*(storage["energy_capacity_MWh"]*p["storage_energy_capex_CNY_per_kWh"]
                  + storage["power_capacity_MW"]*p["storage_power_capex_CNY_per_kW"])
    operating = (totals["thermal_generation_MWh"]*p["thermal_cost_CNY_per_MWh"]
                 + totals["curtailment_MWh"]*p["curtailment_penalty_CNY_per_MWh"]
                 + totals["unserved_MWh"]*p["load_shedding_penalty_CNY_per_MWh"]
                 + discharge*p["storage_variable_om_CNY_per_MWh_discharged"])
    totals["total_cost_CNY"] = operating+capex*(crf+p["storage_fixed_om_fraction_per_year"])*24/p["hours_per_year"]
    totals["renewable_utilization_pct"] = 100*totals["renewable_used_MWh"]/totals["renewable_available_MWh"]
    totals["curtailment_rate_pct"] = 100*totals["curtailment_MWh"]/totals["renewable_available_MWh"]
    return totals, residual, operating


def check_close(actual, expected, label):
    difference = abs(float(actual)-float(expected))
    if not math.isfinite(difference) or difference >= 1e-6:
        raise ValueError(f"Readback mismatch {label}: {difference}")
    return difference


def audit(folder):
    record = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    if record["status"] != "complete" or record["unit"] != "U11R10-fixed-weights-capacity-transfer":
        raise ValueError("Run not complete or incorrect unit")
    frozen = ROOT/"instructions/studies/U11R10-fixed-weights-capacity-transfer/freeze.json"
    if sha(frozen) != record["freeze_sha256"] or json.loads(frozen.read_text(encoding="utf-8")) != record["freeze"]:
        raise ValueError("Freeze identity mismatch")
    checked = 1
    for rel, expected in record["freeze"]["sha256"].items():
        if sha(ROOT/rel) != expected:
            raise ValueError("Frozen hash mismatch: "+rel)
        checked += 1
    for rel, expected in record["source_sha256"].items():
        if sha(ROOT/rel) != expected:
            raise ValueError("Source hash mismatch: "+rel)
        checked += 1
    actual_files = {p.name for p in folder.iterdir() if p.is_file() and p.name != "run_manifest.json"}
    if actual_files != set(record["artifacts"]):
        raise ValueError("Artifact inventory mismatch")
    for name, expected in record["artifacts"].items():
        if sha(folder/name) != expected:
            raise ValueError("Artifact hash mismatch: "+name)
        checked += 1
    cfg = record["freeze"]["config"]
    base = cfg["storage.json"]
    thermal = {k:cfg["optimization.json"][k] for k in ("thermal_min_MW", "thermal_ramp_MW_per_h")}
    thermal["thermal_max_MW"] = cfg["no_storage.json"]["thermal_max_MW"]
    economics = cfg["economics.json"]["parameters"]
    predecessor = ROOT/"results/annual/U11R08B-v01"
    old = json.loads((predecessor/"run_manifest.json").read_text(encoding="utf-8"))
    for key in ("storage", "optimization", "no_storage", "economics"):
        if cfg[key+".json"] != old["freeze"]["config"][key+".json"]:
            raise ValueError("Predecessor configuration drift")
    preflight = json.loads((ROOT/"results/annual/U11R10-predecessor-audit-v01.json").read_text(encoding="utf-8"))
    if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(predecessor/"run_manifest.json"):
        raise ValueError("Predecessor audit mismatch")
    expected_cases = set()
    for name, _, _ in SCENARIOS:
        expected_cases.update(f"{name}_day_{d:03d}" for d in range(365))
        expected_cases.update(f"{name}_N48_seed{s}_cluster{k}" for s in SEEDS for k in range(48))
        expected_cases.add(name+"_repeat_seed42_cluster0")
    if set(record["cases"]) != expected_cases or len(expected_cases) != 1020:
        raise ValueError("Formal call inventory mismatch")
    if record["parameters"] != dict(N=48, seeds=list(SEEDS), scenarios=[list(x) for x in SCENARIOS],
                                     planned_milp_calls=1020, weight_lp_calls=0, daily_reset=True,
                                     dt=1., terminal=True, predecessor_publication="U11R08B", repeat="seed42_cluster0"):
        raise ValueError("Parameter snapshot mismatch")
    source = read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")
    if len(source) != 8760:
        raise ValueError("Wrong annual input dimensions")
    fixed = {}
    max_weight_residual = 0.
    for seed in SEEDS:
        prefix = f"N48_seed{seed}"
        for suffix in ("representatives", "labels"):
            filename = prefix+f"_{suffix}.csv"
            if sha(folder/filename) != sha(predecessor/filename):
                raise ValueError("Fixed input copy changed")
        reps = read_csv(folder/(prefix+"_representatives.csv"))
        labels = read_csv(folder/(prefix+"_labels.csv"))
        if len(reps) != 48 or len(labels) != 365 or [int(r["day"]) for r in labels] != list(range(365)):
            raise ValueError("Fixed cluster dimensions/order")
        labs = [int(r["cluster"]) for r in labels]
        indices, weights = [], []
        for k, rep in enumerate(reps):
            day = int(rep["day"])
            count = labs.count(k)
            w = float(rep["effective_days"])
            if int(rep["cluster"]) != k or not 0 <= day < 365 or labs[day] != k or float(rep["days"]) != count:
                raise ValueError("Fixed cluster membership/count mismatch")
            if not math.isfinite(w) or w != float(rep["repeat_days"]):
                raise ValueError("Fixed weight mismatch")
            residual = max(0., .5*count-w, w-2*count)
            max_weight_residual = max(max_weight_residual, residual)
            indices.append(day)
            weights.append(w)
        max_weight_residual = max(max_weight_residual, abs(math.fsum(weights)-365))
        if len(set(indices)) != 48 or max_weight_residual > 1e-6:
            raise ValueError("Invalid fixed weights/source days")
        fixed[seed] = indices, weights
    comparison = read_csv(folder/"comparison.csv")
    full_annual = read_csv(folder/"full_annual.csv")
    if len(comparison) != 6 or {(r["capacity_scenario"], int(r["seed"])) for r in comparison} != {(n, s) for n, _, _ in SCENARIOS for s in SEEDS}:
        raise ValueError("Comparison matrix mismatch")
    if len(full_annual) != 2 or {r["capacity_scenario"] for r in full_annual} != {x[0] for x in SCENARIOS}:
        raise ValueError("Annual scenario matrix mismatch")
    max_residual = max_difference = max_objective_difference = repeat_max = 0.
    passing, rebuilt = [], []

    def read_case(name, day, storage, saved):
        nonlocal max_residual, max_difference, max_objective_difference
        info = record["cases"][name]
        if info["storage"] != storage or info["thermal"] != thermal or info["dt"] != 1. or info["terminal"] is not True:
            raise ValueError("Case physical configuration mismatch")
        if info["solver_status"] != "Optimal" or info["model_class"] != "MILP" or info["max_residual"] >= 1e-6:
            raise ValueError("Case solver state/physics mismatch")
        log = (folder/(name+"_cbc.log")).read_text(encoding="utf-8")
        if not any(marker in log for marker in ("Result - Optimal solution found", "Optimal objective")):
            raise ValueError("Missing CBC Optimal evidence: "+name)
        row, residual, objective = saved_metrics(folder/(name+"_hourly.csv"), source[day*24:(day+1)*24], storage, thermal, economics)
        max_residual = max(max_residual, residual)
        max_objective_difference = max(max_objective_difference, check_close(objective, info["objective_CNY"], name+" objective"),
                                       check_close(objective, info["precision"]["native_objective"], name+" native objective"))
        for key in TOTALS+RATES:
            max_difference = max(max_difference, check_close(row[key], saved[key], name+" "+key))
        return row

    for scenario, energy, power in SCENARIOS:
        storage = dict(base, energy_capacity_MWh=energy, power_capacity_MW=power)
        summaries = read_csv(folder/(scenario+"_daily_summary.csv"))
        names = [f"{scenario}_day_{d:03d}" for d in range(365)]
        if [r["scenario"] for r in summaries] != names:
            raise ValueError("Daily baseline sequence mismatch")
        rows = [read_case(name, d, storage, saved) for d, (name, saved) in enumerate(zip(names, summaries))]
        full = annual(rows, [1.]*365)
        saved_full = next(r for r in full_annual if r["capacity_scenario"] == scenario)
        for key in TOTALS+RATES:
            max_difference = max(max_difference, check_close(full[key], saved_full[key], scenario+" full "+key))
        main_first = None
        for seed in SEEDS:
            indices, weights = fixed[seed]
            summaries = read_csv(folder/f"{scenario}_N48_seed{seed}_summary.csv")
            names = [f"{scenario}_N48_seed{seed}_cluster{k}" for k in range(48)]
            if [r["scenario"] for r in summaries] != names:
                raise ValueError("Representative sequence mismatch")
            rows = [read_case(name, d, storage, saved) for name, d, saved in zip(names, indices, summaries)]
            if seed == 42:
                main_first = summaries[0]
            totals = annual(rows, weights)
            error = max(abs(totals[k]-full[k]) for k in RATES)
            errors = []
            for key in ("load", "wind", "solar"):
                actual = math.fsum(float(r[key]) for r in source)
                weighted = math.fsum(math.fsum(float(r[key]) for r in source[d*24:(d+1)*24])*w for d, w in zip(indices, weights))
                if actual == 0 and weighted != 0:
                    raise ValueError("Zero annual input denominator")
                totals[key+"_input_MWh"] = weighted
                totals[key+"_relative_error"] = abs(weighted-actual)/actual if actual else 0.
                errors.append(totals[key+"_relative_error"])
            totals.update(worst_error_pp=error, max_input_relative_error=max(errors),
                          cost_error_CNY=totals["total_cost_CNY"]-full["total_cost_CNY"],
                          unserved_error_MWh=totals["unserved_MWh"]-full["unserved_MWh"],
                          cost_signed_relative_error=(totals["total_cost_CNY"]-full["total_cost_CNY"])/full["total_cost_CNY"],
                          unserved_signed_relative_error=(totals["unserved_MWh"]-full["unserved_MWh"])/full["unserved_MWh"])
            saved = next(r for r in comparison if r["capacity_scenario"] == scenario and int(r["seed"]) == seed)
            if int(saved["N"]) != 48:
                raise ValueError("Fixed N mismatch")
            for key, value in totals.items():
                max_difference = max(max_difference, check_close(value, saved[key], scenario+" comparison "+key))
            passed = error <= 1. and max(errors) <= .02
            if saved["passed"] != str(passed):
                raise ValueError("Group decision mismatch")
            passing.append(passed)
            rebuilt.append(dict(capacity_scenario=scenario, seed=seed, **totals, passed=passed))
        name = scenario+"_repeat_seed42_cluster0"
        repeated = read_csv(folder/(scenario+"_repeat_summary.csv"))
        if len(repeated) != 1 or repeated[0]["scenario"] != name:
            raise ValueError("Repeat summary mismatch")
        read_case(name, fixed[42][0][0], storage, repeated[0])
        differences = []
        if set(main_first) != set(repeated[0]):
            raise ValueError("Repeat summary keys mismatch")
        for key in main_first:
            if key == "scenario":
                continue
            try:
                left, right = float(main_first[key]), float(repeated[0][key])
            except ValueError:
                if main_first[key] != repeated[0][key]:
                    raise ValueError("Repeat nonnumeric field mismatch")
                continue
            if key == "storage_utilization_pct" and energy == 0 and math.isnan(left) and math.isnan(right):
                continue
            differences.append(check_close(left, right, "repeat "+key))
        repeat_max = max(repeat_max, max(differences))
        check_close(max(differences), record["repeat_differences"][scenario], "repeat manifest")
    verdict = "supported" if all(passing) else "inconclusive"
    if record["verdict"] != verdict or record["details"]["milp_calls"] != 1020 or record["details"]["weight_lp_calls"] != 0 or record["details"]["passing_groups"] != sum(passing):
        raise ValueError("Final verdict/budget mismatch")
    if record["details"]["reference_E40_P20_comparison_sha256"] != sha(predecessor/"comparison.csv"):
        raise ValueError("Original E40 reference identity mismatch")
    return dict(passed=True, run_id=record["run_id"], checked_hashes=checked, milp_calls=1020,
                weight_lp_calls=0, new_solver_calls=0, audited_full_days=730, audited_representative_days=288,
                audited_repeat_days=2, max_residual=max_residual, max_readback_difference=max_difference,
                max_objective_difference=max_objective_difference, max_weight_residual=max_weight_residual,
                repeat_max_difference=repeat_max, passing_groups=sum(passing), verdict=verdict,
                comparison=rebuilt, audit_source_sha256=sha(__file__), run_manifest_sha256=sha(folder/"run_manifest.json"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        report = audit(ROOT/"results/annual"/args.run_id)
    except Exception as exc:
        report = dict(passed=False, error=repr(exc), new_solver_calls=0, audit_source_sha256=sha(__file__))
    with (ROOT/args.output).open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({k:v for k,v in report.items() if k != "comparison"}, ensure_ascii=False), flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
