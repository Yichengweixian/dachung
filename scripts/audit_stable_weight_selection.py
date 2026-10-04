"""U11R15 independent audit — standard library only, zero optimisation calls.

Rebuilds the four input channels from the original CSV with exact decimal arithmetic, re-derives every
saved hierarchy stage (objective, bands, pins), re-proves the primary minimax certificate by rational weak
duality, recomputes E/D/cost/unserved from the saved dispatches, rebuilds the 509 saved source days and
their cost decomposition, and re-derives the frozen H1/H2 verdicts. It never imports the unit's model,
runner or decision code, and it forbids subprocess/pulp/scipy.optimize through runtime guards.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (42, 7, 2026)
CHANNELS = ("load", "wind", "solar", "excess_proxy")
CEILING = 120
BAND = F(1, 1000000)
E_GATE = F(1)
D_GATE = F(2, 100)
MARGIN = F(1, 1000000)
SUMMARY_COLUMNS = ("renewable_available_MWh", "renewable_used_MWh", "curtailment_MWh", "total_load_MWh",
                   "thermal_generation_MWh", "unserved_MWh", "total_cost_CNY")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def floats(rows, column):
    return [float(row[column]) for row in rows]


def channel_vector(rows, exact):
    if exact:
        values = [sum(F(row[key]) for row in rows) for key in CHANNELS[:3]]
        values.append(sum(max(F(row["load"]) - F(row["wind"]) - F(row["solar"]) - CEILING, F(0))
                          for row in rows))
    else:
        values = [math.fsum(float(row[key]) for row in rows) for key in CHANNELS[:3]]
        values.append(math.fsum(max(float(row["load"]) - float(row["wind"]) - float(row["solar"]) - CEILING, 0.)
                                for row in rows))
    return values


def require(condition, message):
    if not condition:
        raise ValueError(message)


def channel_rows(energy, target):
    """Exact normalised channel rows/rhs for the four-channel minimax (2 rows per nonzero target)."""
    rows, rhs = [], []
    for amount, total in zip(energy, target):
        require(total >= 0 and all(value >= 0 for value in amount), "negative input")
        if total == 0:
            require(all(value == 0 for value in amount), "nonzero representative in a zero channel")
            continue
        row = [value / total for value in amount]
        rows.extend([row, [-value for value in row]])
        rhs.extend([F(1), F(-1)])
    return rows, rhs


def weak_duality(energy, target, counts, weights, inequality, equality):
    """Independent rational certificate: lower bound from the dual, upper bound from a feasible point."""
    rows, rhs = channel_rows(energy, target)
    require(len(inequality) == len(rows) and len(equality) == 1, "dual dimensions")
    lower = [F(c) / 2 for c in counts]
    upper = [F(c) * 2 for c in counts]
    native = [F.from_float(float(w)) for w in weights]
    proof = [min(hi, max(lo, w)) for w, lo, hi in zip(native, lower, upper)]
    require(max(abs(w - p) for w, p in zip(native, proof)) <= F("1e-7"), "large bound repair")
    delta = F(365) - sum(proof)
    require(abs(delta) <= F("1e-7"), "large sum repair")
    for i in range(len(proof)):
        change = min(delta, upper[i] - proof[i]) if delta > 0 else max(delta, lower[i] - proof[i])
        proof[i] += change
        delta -= change
    require(delta == 0, "cannot repair the sum")
    y = [min(F(0), F.from_float(float(v))) for v in inequality]
    scale = max(F(1), -sum(y))
    y = [value / scale for value in y]
    z = F.from_float(float(equality[0]))
    r = [-sum(row[i] * value for row, value in zip(rows, y)) - z for i in range(len(counts))]
    lb = max(F(0), sum(b * v for b, v in zip(rhs, y)) + 365 * z
             + sum(min(v * lo, v * hi) for v, lo, hi in zip(r, lower, upper)))
    ub = max([F(0)] + [sum(x * w for x, w in zip(row, proof)) - b for row, b in zip(rows, rhs)])
    require(lb <= ub, "invalid exact bounds")
    return dict(lower=str(lb), upper=str(ub), gap=str(ub - lb), max_repair=str(max(abs(w - p)
                for w, p in zip(native, proof))), lower_float=float(lb), upper_float=float(ub))


def state(t, lower, upper):
    if upper - lower > F("1e-8") or abs(F.from_float(float(t)) - F(2, 100)) <= F("1e-8"):
        return "uncertain"
    if upper <= F(2, 100) and float(t) <= 0.02:
        return "reachable"
    if lower > F(2, 100) and float(t) > 0.02:
        return "unreachable"
    return "uncertain"


def stage_check(model, record, limits, pins, previous_pins):
    """Re-derive one saved HiGHS/CBC stage from the frozen rule definition."""
    counts = [F(c) for c in model["counts"]]
    energy = [[F.from_float(float(v)) for v in row] for row in model["energy"]]
    target = [F.from_float(float(v)) for v in model["target"]]
    weights = [F.from_float(float(v)) for v in record["weights"]]
    t = F.from_float(float(record["t"]))
    require(len(weights) == len(counts), "weight dimension")
    bounds = max([F(0)] + [max(counts[i] / 2 - w, w - 2 * counts[i]) for i, w in enumerate(weights)])
    total = abs(sum(weights) - 365)
    errors = [abs(sum(energy[k][i] * weights[i] for i in range(len(weights))) / target[k] - 1)
              for k in range(4) if target[k] > 0]
    require(bounds <= F(1, 10 ** 7), "stage bound/sum residual: %s" % float(bounds))
    require(total <= F(1, 10 ** 7), "stage sum residual: %s" % float(total))
    require(max(errors) <= t + F(1, 10 ** 8), "stage channel residual")
    deviations = [abs(weights[i] - counts[i]) / counts[i] for i in range(len(weights))]
    l1, linf = sum(deviations), max(deviations)
    objective = F.from_float(float(record["objective"]))
    if record["stage"] == "primary":
        require(abs(t - max(errors)) <= F(1, 10 ** 9), "primary objective is not the worst channel error")
        require(abs(objective - t) <= F(1, 10 ** 9), "primary objective mismatch")
    elif record["objective"] == "l1" or (record["objective"] == "w" and model["rule"] == "l1"):
        require(abs(objective - l1) <= F(1, 10 ** 7), "L1 objective mismatch")
    elif record["objective"] == "linf" or (record["objective"] == "w" and model["rule"] == "linf"):
        require(abs(objective - linf) <= F(1, 10 ** 7), "L-infinity objective mismatch")
    if record["objective"] == "w":
        require(abs(objective - weights[record["index"]]) <= F(1, 10 ** 7), "pin objective mismatch")
    errors_out = []
    if limits["t_limit"] is not None:
        errors_out.append(float(max(F(0), t - limits["t_limit"])))
    if limits["s_limit"] is not None:
        require(record.get("secondary_value") is not None, "missing secondary value")
        value = F.from_float(float(record["secondary_value"]))
        errors_out.append(float(max(F(0), value - limits["s_limit"])))
    for index, lower, upper in pins:
        errors_out.append(float(max(F(0), F.from_float(float(lower)) - weights[index],
                                    weights[index] - F.from_float(float(upper)))))
    require(max(errors_out, default=0.) <= 1e-7, "stage band/pin residual: %s" % max(errors_out, default=0.))
    return dict(bounds=float(bounds), sum=float(total), l1=float(l1), linf=float(linf),
                pin_order=[index for index, _, _ in pins])


def annual(rows, weights):
    totals = {key: math.fsum(float(row[key]) * float(w) for row, w in zip(rows, weights))
              for key in SUMMARY_COLUMNS}
    require(totals["renewable_available_MWh"] > 0, "zero renewable denominator")
    totals["renewable_utilization_pct"] = 100. * totals["renewable_used_MWh"] / totals["renewable_available_MWh"]
    totals["curtailment_rate_pct"] = 100. * totals["curtailment_MWh"] / totals["renewable_available_MWh"]
    return totals


def day_check(path, storage, thermal, economics, expected_summary=None):
    """Rebuild one saved dispatch day: balance, bounds, SOC recursion, cost decomposition."""
    rows = read_rows(path)
    require(len(rows) == 24, "day length: %s" % path)
    require([int(row["hour"]) for row in rows] == list(range(24)), "hour axis: %s" % path)
    eta_c, eta_d = float(storage["eta_charge"]), float(storage["eta_discharge"])
    energy_cap = float(storage["energy_capacity_MWh"])
    power = float(storage["power_capacity_MW"])
    soc_min, soc_max, soc0 = float(storage["soc_min"]), float(storage["soc_max"]), float(storage["soc_initial"])
    residual = 0.
    previous = energy_cap * soc0
    totals = dict(renewable_available_MWh=0., renewable_used_MWh=0., curtailment_MWh=0., total_load_MWh=0.,
                  thermal_generation_MWh=0., unserved_MWh=0., storage_discharge_MWh=0.)
    for row in rows:
        values = {key: float(row[key]) for key in ("load", "wind_available", "solar_available", "wind_used",
                                                   "solar_used", "wind_curt", "solar_curt", "thermal", "charge",
                                                   "discharge", "unserved", "energy_start_MWh", "energy_MWh")}
        balance = (values["wind_used"] + values["solar_used"] + values["thermal"] + values["discharge"]
                   + values["unserved"] - values["load"] - values["charge"])
        residual = max(residual, abs(balance))
        require(values["wind_used"] + values["wind_curt"] - values["wind_available"] <= 1e-6, "wind identity")
        require(values["solar_used"] + values["solar_curt"] - values["solar_available"] <= 1e-6, "solar identity")
        for key in ("wind_used", "solar_used", "wind_curt", "solar_curt", "thermal", "charge", "discharge",
                    "unserved"):
            require(values[key] >= -1e-9, "negative dispatch: " + key)
        require(values["charge"] <= power + 1e-6 and values["discharge"] <= power + 1e-6, "power bound")
        require(min(values["charge"], values["discharge"]) <= 1e-6, "simultaneous charge/discharge")
        require(values["unserved"] <= values["load"] + 1e-6, "unserved above load")
        require(abs(values["energy_start_MWh"] - previous) <= 1e-6, "SOC recursion start")
        expected = previous + eta_c * values["charge"] - values["discharge"] / eta_d
        require(abs(values["energy_MWh"] - expected) <= 1e-6, "SOC recursion")
        require(soc_min * energy_cap - 1e-6 <= values["energy_MWh"] <= soc_max * energy_cap + 1e-6, "SOC bound")
        previous = values["energy_MWh"]
        totals["renewable_available_MWh"] += values["wind_available"] + values["solar_available"]
        totals["renewable_used_MWh"] += values["wind_used"] + values["solar_used"]
        totals["curtailment_MWh"] += values["wind_curt"] + values["solar_curt"]
        totals["total_load_MWh"] += values["load"]
        totals["thermal_generation_MWh"] += values["thermal"]
        totals["unserved_MWh"] += values["unserved"]
        totals["storage_discharge_MWh"] += values["discharge"]
    require(abs(previous - energy_cap * soc0) <= 1e-6, "terminal SOC: %s" % path)
    thermal_cost = float(economics["thermal_cost_CNY_per_MWh"]) * totals["thermal_generation_MWh"]
    curtail_cost = float(economics["curtailment_penalty_CNY_per_MWh"]) * totals["curtailment_MWh"]
    shed_cost = float(economics["load_shedding_penalty_CNY_per_MWh"]) * totals["unserved_MWh"]
    variable_om = float(economics["storage_variable_om_CNY_per_MWh_discharged"]) * totals["storage_discharge_MWh"]
    hours = float(economics["hours_per_year"])
    rate = float(economics["discount_rate"])
    life = float(economics["storage_lifetime_years"])
    crf = rate * (1 + rate) ** life / ((1 + rate) ** life - 1)
    year_fraction = 24. / hours
    capex = energy_cap * 1000 * float(economics["storage_energy_capex_CNY_per_kWh"]) \
        + power * 1000 * float(economics["storage_power_capex_CNY_per_kW"])
    fixed_om = (float(economics["storage_fixed_om_fraction_per_year"]) * capex + capex * crf) * year_fraction
    cost = thermal_cost + curtail_cost + shed_cost + variable_om + fixed_om
    totals.update(thermal_cost_CNY=thermal_cost, curtailment_cost_CNY=curtail_cost,
                  load_shedding_cost_CNY=shed_cost, storage_variable_om_CNY=variable_om,
                  storage_fixed_and_capital_CNY=fixed_om, total_cost_CNY=cost)
    if expected_summary is not None:
        for key, value in totals.items():
            saved = expected_summary.get(key)
            if saved in (None, ""):
                continue
            require(abs(float(saved) - value) <= 1e-6 * max(1., abs(value)), "saved summary mismatch: " + key)
    return residual, totals


def audit(folder):
    manifest = json.loads((folder / "run_manifest.json").read_text(encoding="utf-8"))
    frozen_path = ROOT / "instructions/studies/U11R15-stable-weight-selection/freeze.json"
    require(manifest["status"] == "complete" and manifest["unit"] == "U11R15-stable-weight-selection",
            "formal status/unit mismatch")
    require(not manifest["cases"] and manifest["dispatch_calls"] == 0, "dispatch budget mismatch")
    require(manifest["lp_calls"] == 459, "LP budget mismatch: %r" % manifest["lp_calls"])
    require(sha(frozen_path) == manifest["freeze_sha256"], "freeze identity mismatch")
    require(json.loads(frozen_path.read_text(encoding="utf-8")) == manifest["freeze"], "freeze content mismatch")
    expected_packages = dict(numpy="2.5.3", pandas="3.0.5", scipy="1.18.1", pulp="3.3.0")
    require(all(manifest["packages"][key] == value for key, value in expected_packages.items()),
            "package version mismatch")
    parameters = manifest["parameters"]
    require(parameters["N"] == 48 and parameters["seeds"] == list(SEEDS) and parameters["thermal_max_MW"] == 120
            and parameters["band"] == 1e-6 and parameters["expected_lp_calls"] == 459,
            "frozen parameter mismatch")

    hashes = 0
    for entries, base in ((manifest["freeze"]["sha256"], ROOT), (manifest["source_sha256"], ROOT),
                          (manifest["artifacts"], folder)):
        for path, digest in entries.items():
            require(sha(base / path) == digest, "hash mismatch: " + str(path))
            hashes += 1
    inventory = {p.relative_to(folder).as_posix() for p in folder.rglob("*")
                 if p.is_file() and p.name != "run_manifest.json"}
    require(inventory == set(manifest["artifacts"]), "artifact inventory mismatch")

    config = manifest["freeze"]["config"]
    storage, economics = config["storage.json"], config["economics.json"]["parameters"]
    thermal = {key: config["optimization.json"][key] for key in ("thermal_min_MW", "thermal_ramp_MW_per_h")}
    thermal["thermal_max_MW"] = config["no_storage.json"]["thermal_max_MW"]
    require(storage["energy_capacity_MWh"] == 40 and storage["power_capacity_MW"] == 20
            and thermal["thermal_max_MW"] == 120, "frozen configuration mismatch")

    annual_rows = read_rows(ROOT / "results/annual/U11R02-v01/input_8760h.csv")
    require(len(annual_rows) == 8760 and [int(row["hour"]) for row in annual_rows] == list(range(8760)),
            "annual hour axis mismatch")
    target_exact = channel_vector(annual_rows, True)
    target_float = channel_vector(annual_rows, False)
    full = read_rows(ROOT / "results/annual/U11R02-v01/full_annual.csv")[0]

    diagnostics = read_rows(folder / "diagnostics.csv")
    comparison = read_rows(folder / "comparison.csv")
    structure = read_rows(folder / "structure.csv")
    h1_saved = read_rows(folder / "h1_matrix.csv")
    h2_saved = read_rows(folder / "h2_matrix.csv")
    require([int(row["seed"]) for row in comparison] == list(SEEDS), "comparison seed order")
    require([(int(row["seed"]), row["kind"]) for row in diagnostics]
            == [(seed, kind) for seed in SEEDS for kind in ("counts", "l1", "linf")], "diagnostic matrix order")

    residue = dict(bounds=0., sum=0., saved_stage_max=None, physical=0., readback=0., mps=0.)
    day_count = 0
    verdict_rows, h2_rows, classifications = [], [], []
    for seed in SEEDS:
        prefix = "N48_seed%d" % seed
        group = folder / prefix
        reps = read_rows(ROOT / ("results/annual/U11R12-v01/%s_representatives.csv" % prefix))
        labels = read_rows(ROOT / ("results/annual/U11R08B-v01/%s_labels.csv" % prefix))
        require(len(reps) == 48 and len(labels) == 365, "saved day inventory mismatch")
        require([int(row["cluster"]) for row in reps] == list(range(48)), "representative cluster order")
        require([int(row["day"]) for row in labels] == list(range(365)), "label day order")
        counts = [0] * 48
        for row in labels:
            counts[int(row["cluster"])] += 1
        require(counts == [int(row["days"]) for row in reps], "cluster counts differ from saved days")
        require(sum(counts) == 365, "cluster counts do not total 365")
        for row in reps:
            expected_date = D(2023) * 0 + _date(int(row["day"]))
            require(row["date_UTC"] == expected_date, "representative date mismatch")
        energy_exact, energy_float = [], []
        for row in reps:
            day = int(row["day"])
            block = annual_rows[day * 24:(day + 1) * 24]
            energy_exact.append(channel_vector(block, True))
            energy_float.append(channel_vector(block, False))
        energy_exact = list(map(list, zip(*energy_exact)))
        energy_float = list(map(list, zip(*energy_float)))
        rules = {}
        for rule in ("l1", "linf"):
            model = json.loads((group / ("model_%s.json" % rule)).read_text(encoding="utf-8"))
            require(model["counts"] == counts and model["rule"] == rule, "model identity mismatch: " + rule)
            require([int(v) for v in model["days"]] == [int(row["day"]) for row in reps], "model day order")
            saved = [[float(v) for v in row] for row in model["energy"]]
            for k in range(4):
                for i in range(48):
                    residue["readback"] = max(residue["readback"], abs(saved[k][i] - energy_float[k][i]))
                require(abs(float(model["target"][k]) - target_float[k]) <= 1e-9 * max(1., abs(target_float[k])),
                        "model target mismatch")
            require(residue["readback"] <= 1e-9, "four-channel rebuild mismatch")
            stages = json.loads((group / ("stages_%s.json" % rule)).read_text(encoding="utf-8"))
            require(len(stages) == (50 if rule == "l1" else 50), "stage count mismatch: " + rule)
            limits = dict(t_limit=None, s_limit=None)
            pins = []
            order = sorted(range(48), key=lambda i: (str(model["dates"][i]), i))
            require([stage["stage"] for stage in stages]
                    == ["primary", "secondary"] + ["pin_%03d" % i for i in order], "stage order mismatch")
            for index, record in enumerate(stages):
                limits = dict(t_limit=limits["t_limit"], s_limit=limits["s_limit"])
                check = stage_check(model, record, limits, pins, None)
                if record["stage"] == "primary":
                    require(abs(record["t"] - record["objective"]) <= 1e-12, "primary t/objective mismatch")
                    limits["t_limit"] = F.from_float(float(record["objective"])) + BAND
                elif record["stage"] == "secondary":
                    limits["s_limit"] = F.from_float(float(record["objective"])) + BAND
                else:
                    value = F.from_float(float(record["weights"][record["index"]]))
                    pins.append((record["index"], max(F(counts[record["index"]]) / 2, value - BAND),
                                 min(F(counts[record["index"]]) * 2, value + BAND)))
                residue["bounds"] = max(residue["bounds"], check["bounds"])
                residue["sum"] = max(residue["sum"], check["sum"])
            rules[rule] = dict(stages=stages, pins=pins, limits=limits, model=model)
        # exact certificate for the shared primary stage
        primary = rules["l1"]["stages"][0]
        other = rules["linf"]["stages"][0]
        require(max(abs(float(a) - float(b)) for a, b in zip(primary["weights"], other["weights"])) <= 1e-9
                and abs(float(primary["t"]) - float(other["t"])) <= 1e-12,
                "primary stage differs between the two rule families")
        proof = weak_duality(energy_exact, target_exact, counts, primary["weights"],
                             primary["inequality_marginals"][:8], primary["equality_marginals"])
        saved_proof = json.loads((group / "certificate_l1.json").read_text(encoding="utf-8"))
        require(proof["lower"] == saved_proof["lower"] and proof["upper"] == saved_proof["upper"]
                and proof["gap"] == saved_proof["gap"], "certificate mismatch")
        require(F(proof["gap"]) <= F("1e-8"), "certificate gap")
        classification = state(primary["t"], F(proof["lower"]), F(proof["upper"]))
        classifications.append(classification)
        # two-path consistency
        row = next(item for item in comparison if int(item["seed"]) == seed)
        require(float(row["max_objective_difference"]) <= 1e-8, "cross-solver objective difference")
        require(float(row["max_weight_difference"]) <= 1e-4, "cross-solver weight difference")
        require(float(row["independent_objective_difference"]) <= 1e-10, "independent objective difference")
        require(float(row["independent_weight_difference"]) <= 1e-7, "independent weight difference")
        require(abs(float(row["exact_lower"]) - proof["lower_float"]) <= 1e-15
                and abs(float(row["exact_upper"]) - proof["upper_float"]) <= 1e-15, "comparison certificate mismatch")
        # dispatches and diagnostics
        summary = read_rows(ROOT / ("results/annual/U11R12-v01/%s_summary.csv" % prefix))
        require([r["scenario"] for r in summary] == [prefix + "_cluster%d" % k for k in range(48)],
                "saved dispatch inventory mismatch")
        for kind, weights in (("counts", counts), ("l1", rules["l1"]["stages"][-1]["weights"]),
                              ("linf", rules["linf"]["stages"][-1]["weights"])):
            metrics = annual(summary, weights)
            saved = next(item for item in diagnostics if int(item["seed"]) == seed and item["kind"] == kind)
            for key in SUMMARY_COLUMNS + ("renewable_utilization_pct", "curtailment_rate_pct"):
                require(abs(float(saved[key]) - metrics[key]) <= 1e-6 * max(1., abs(metrics[key])),
                        "diagnostic mismatch %s/%s/%s" % (seed, kind, key))
            E = max(abs(metrics["renewable_utilization_pct"] - float(full["renewable_utilization_pct"])),
                    abs(metrics["curtailment_rate_pct"] - float(full["curtailment_rate_pct"])))
            require(abs(float(saved["worst_error_pp"]) - E) <= 1e-6, "E mismatch")
            cost_error = metrics["total_cost_CNY"] - float(full["total_cost_CNY"])
            unserved_error = metrics["unserved_MWh"] - float(full["unserved_MWh"])
            require(abs(float(saved["cost_error_CNY"]) - cost_error) <= 1e-6 * max(1., abs(cost_error)),
                    "cost error mismatch")
            require(abs(float(saved["unserved_error_MWh"]) - unserved_error) <= 1e-6 * max(1., abs(unserved_error)),
                    "unserved error mismatch")
            errors = [abs(math.fsum(energy_float[k][i] * float(weights[i]) for i in range(48)) / target_float[k] - 1)
                      for k in range(4)]
            require(abs(float(saved["four_channel_relative_error"]) - max(errors)) <= 1e-9, "D mismatch")
            if kind == "counts":
                base = dict(cost=cost_error, unserved=unserved_error)
            if kind == "l1":
                passed = max(errors) <= float(D_GATE) and E <= 1.
                require(bool(saved["passes_ED"]) == passed, "passes_ED mismatch")
                verdict_rows.append(dict(seed=seed, classification=classification, E=E, D=max(errors),
                                         cost_error=cost_error, unserved_error=unserved_error))
        h2_rows.append(dict(seed=seed, cost_error=verdict_rows[-1]["cost_error"],
                            unserved_error=verdict_rows[-1]["unserved_error"],
                            base_cost=base["cost"], base_unserved=base["unserved"]))
        # 509 saved source days: 365 annual + 144 representative-day dispatches
        annual_folder = ROOT / "results/annual/U11R02-v01"
        for day in range(365):
            daily = read_rows(annual_folder / ("day_%03d_summary.csv" % day)) if \
                (annual_folder / ("day_%03d_summary.csv" % day)).exists() else None
            residual, _ = day_check(annual_folder / ("day_%03d_hourly.csv" % day), storage, thermal, economics,
                                    daily[0] if daily else None)
            residue["physical"] = max(residue["physical"], residual)
            day_count += 1
        for cluster in range(48):
            saved = next(item for item in summary if item["scenario"] == prefix + "_cluster%d" % cluster)
            residual, _ = day_check(ROOT / ("results/annual/U11R12-v01/%s_cluster%d_hourly.csv" % (prefix, cluster)),
                                    storage, thermal, economics, saved)
            residue["physical"] = max(residue["physical"], residual)
            day_count += 1
    h1 = "supported"
    for row in verdict_rows:
        if row["classification"] == "unreachable":
            h1 = "refuted"
            break
        if row["classification"] == "uncertain" or abs(row["E"] - 1.) <= 1e-6:
            h1 = "inconclusive"
            break
        if row["E"] > 1.:
            h1 = "refuted"
            break
        if row["D"] > 2. / 100 + 1e-6:
            h1 = "refuted"
            break
    h2 = "supported"
    for row in h2_rows:
        stop = False
        for key, base_key in (("cost_error", "base_cost"), ("unserved_error", "base_unserved")):
            margin = 1e-6 * max(1., abs(row[base_key]))
            difference = abs(row[key]) - abs(row[base_key])
            if abs(difference) <= margin:
                h2, stop = "inconclusive", True
            elif difference > 0:
                h2, stop = "refuted", True
            if stop:
                break
        if stop:
            break
    require(manifest["verdict"] == h1 and manifest["h1"] == h1 and manifest["h2"] == h2,
            "verdict re-derivation mismatch: %r/%r/%r" % (manifest["verdict"], h1, h2))
    require([row["classification"] for row in h1_saved] == classifications, "classification matrix")
    require([int(row["seed"]) for row in h2_saved] == list(SEEDS), "h2 matrix order")
    require(day_count == 509, "source day count: %d" % day_count)
    require(residue["bounds"] <= 1e-7 and residue["sum"] <= 1e-7 and residue["readback"] <= 1e-9,
            "residual summary")
    require(residue["physical"] <= 1e-6, "physical residual: %r" % residue["physical"])
    return dict(passed=True, new_solver_calls=0, formal_lp_calls=459, dispatch_calls=0,
                source_days=day_count, checked_hashes=hashes, verdict=h1, h2=h2,
                classifications=classifications, max_stage_bound_residual=residue["bounds"],
                max_four_channel_rebuild_difference=residue["readback"],
                max_physical_residual=residue["physical"],
                diagnostics=[dict(row) for row in verdict_rows], h2_matrix=h2_rows,
                run_manifest_sha256=sha(folder / "run_manifest.json"), audit_source_sha256=sha(__file__))


def _date(day):
    import datetime
    return (datetime.date(2023, 1, 1) + datetime.timedelta(days=day)).strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        with patch("subprocess.run", side_effect=AssertionError("No subprocess in audit")), \
                patch("pulp.LpProblem.solve", side_effect=AssertionError("No optimisation in audit")), \
                patch("scipy.optimize.linprog", side_effect=AssertionError("No LP in audit")):
            report = audit(ROOT / "results/annual" / args.run_id)
    except Exception as exc:
        report = dict(passed=False, error=repr(exc), new_solver_calls=0, audit_source_sha256=sha(__file__))
    with (ROOT / args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key != "diagnostics"},
                     ensure_ascii=False), flush=True)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
