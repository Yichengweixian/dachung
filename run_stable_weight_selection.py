"""U11R15: three seeds x two lexicographic rules x two solvers, 459 LPs and zero dispatch.

Frozen hierarchy (see instructions/studies/U11R15-stable-weight-selection/decision-rule.md):
primary minimax t -> L1 (or L-infinity) deviation from cluster counts -> date-order pinning.
No retries, no tolerance changes, no weight selection by saved cost/unserved outcomes.
"""
import argparse
from fractions import Fraction as F
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np
import pandas as pd

from scripts.audit_u11r08_feasibility import certificate, classify, read_csv as read_text_csv
from src.annual_clustering import annual_metrics
from src.fixed_weights_capacity_transfer import fixed_days
from src.input_energy_feasibility import check_solution
from src.stable_weight_selection import (BAND, CHANNELS, WEIGHT_IDENTITY_TOL, build_model,
                                         h1_verdict, h2_verdict, highs_problem, identity_difference,
                                         run_cbc_rule, run_highs_rule, solve_highs, stage_specs)
from src.study_runtime import ROOT, StudyRun, dump, sha

SEEDS = (42, 7, 2026)
CEILING = 120.0
PRIMARY_LP_BUDGET = 6      # 3 HiGHS + 3 CBC primary stages
EXPECTED_LP_CALLS = 459


def read_frame(path):
    return pd.read_csv(path, float_precision="round_trip")


def channel_amounts(frame, ceiling):
    values = [math.fsum(frame[k]) for k in CHANNELS[:3]]
    values.append(math.fsum(max(float(row.load) - float(row.wind) - float(row.solar) - ceiling, 0.)
                            for row in frame.itertuples()))
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite four-channel amounts")
    return values


def exact_amounts(rows, ceiling):
    return ([sum(F(r[k]) for r in rows) for k in CHANNELS[:3]]
            + [sum(max(F(r["load"]) - F(r["wind"]) - F(r["solar"]) - ceiling, F(0)) for r in rows)])


def primary_problem(model):
    return highs_problem(model, stage_specs(model)[0], dict(t_limit=None, s_limit=None, pins=[]))


def run_worker(problem_path, solution_path):
    problem = json.loads(Path(problem_path).read_text(encoding="utf-8"))
    if Path(solution_path).exists():
        raise FileExistsError(solution_path)
    dump(solution_path, solve_highs(problem))


def diagnostics(rows, full, weights, model, label):
    metrics = annual_metrics(rows, weights)
    checks = check_solution(model, weights, max(abs(v) for v in
                                                [math.fsum(a * w for a, w in zip(row, weights)) / b - 1
                                                 for row, b in zip(model["energy"], model["target"])]))
    errors = checks["absolute_relative_errors"]
    record = dict(seed=model["seed"], rule=model["rule"], kind=label, **metrics,
                  worst_error_pp=max(abs(metrics["renewable_utilization_pct"] - full["renewable_utilization_pct"]),
                                     abs(metrics["curtailment_rate_pct"] - full["curtailment_rate_pct"])),
                  max_input_relative_error=max(errors[:3]), four_channel_relative_error=max(errors),
                  proxy_relative_error=errors[3],
                  cost_error_CNY=metrics["total_cost_CNY"] - full["total_cost_CNY"],
                  unserved_error_MWh=metrics["unserved_MWh"] - full["unserved_MWh"])
    record["passes_ED"] = bool(record["worst_error_pp"] <= 1. and record["four_channel_relative_error"] <= .02)
    return record


def structure(weights, counts):
    w = np.asarray(weights, dtype=float)
    c = np.asarray(counts, dtype=float)
    relative = np.abs(w - c) / c
    return dict(moved_days=int(np.sum(relative > 1e-9)),
                at_lower_bound=int(np.sum(np.abs(w - .5 * c) <= 1e-9)),
                at_upper_bound=int(np.sum(np.abs(w - 2. * c) <= 1e-9)),
                mean_abs_movement_days=float(np.sum(np.abs(w - c)) / 365.),
                l1_relative=float(np.sum(relative)), linf_relative=float(np.max(relative)),
                min_weight=float(np.min(w)), max_weight=float(np.max(w)))


def run(run_id):
    run = StudyRun("U11R15-stable-weight-selection", "annual", run_id)
    started = perf_counter()
    calls = 0
    try:
        cfg, storage, thermal, economics = None, None, None, None
        from src.study_runtime import configuration
        cfg, storage, thermal, economics = configuration()
        expected = dict(numpy="2.5.3", pandas="3.0.5", scipy="1.18.1", pulp="3.3.0")
        versions = {name: importlib.metadata.version(name) for name in expected}
        if versions != expected or thermal["thermal_max_MW"] != CEILING:
            raise ValueError("Frozen runtime/ceiling mismatch")
        run.manifest["packages"].update(versions)
        run.manifest["parameters"] = dict(N=48, seeds=list(SEEDS), channels=list(CHANNELS), band=BAND,
                                          thermal_max_MW=CEILING, e_gate=1., d_gate=.02,
                                          rules=["l1", "linf"], primary_lp_budget=PRIMARY_LP_BUDGET,
                                          dispatch_budget=0, expected_lp_calls=EXPECTED_LP_CALLS)
        for name in ("src/stable_weight_selection.py", "run_stable_weight_selection.py",
                     "tests/test_stable_weight_selection.py", "scripts/audit_stable_weight_selection.py"):
            if (ROOT / name).exists():
                run.manifest["source_sha256"][name] = sha(ROOT / name)
        predecessor = json.loads((ROOT / "results/annual/U11R14-v01-independent-audit-v02.json")
                                 .read_text(encoding="utf-8"))
        if not predecessor["passed"] or predecessor["run_manifest_sha256"] != \
                sha(ROOT / "results/annual/U11R14-v01/run_manifest.json"):
            raise ValueError("Predecessor identity mismatch")

        data = read_frame(ROOT / "results/annual/U11R02-v01/input_8760h.csv")
        if len(data) != 8760 or not np.array_equal(data.hour.to_numpy(), np.arange(8760)):
            raise ValueError("Annual hour axis mismatch")
        raw = read_text_csv(ROOT / "results/annual/U11R02-v01/input_8760h.csv")
        if len(raw) != 8760:
            raise ValueError("Raw annual row count mismatch")
        target_exact = exact_amounts(raw, F(int(CEILING)))
        target = channel_amounts(data, CEILING)
        full = read_frame(ROOT / "results/annual/U11R02-v01/full_annual.csv").iloc[0]

        comparison, diagnostics_rows, h1_rows, h2_rows, structure_rows = [], [], [], [], []
        for seed in SEEDS:
            prefix = "N48_seed%d" % seed
            reps = read_frame(ROOT / ("results/annual/U11R12-v01/%s_representatives.csv" % prefix))
            labels = read_frame(ROOT / ("results/annual/U11R08B-v01/%s_labels.csv" % prefix))
            days, effective, fixed_residual = fixed_days(data, reps, labels)
            counts = [int(v) for v in reps.days]
            if any(float(v) % 1 for v in reps.days) or sum(counts) != 365:
                raise ValueError("Representative cluster counts must be integers totalling 365")
            # `effective_days` in the saved representative file is the previously calibrated weight
            # vector (U11R08B), not the cluster count; the frozen counts are `days`.
            effective_gap = max(abs(float(a) - b) for a, b in zip(effective, counts))
            run.manifest.setdefault("effective_day_gap_days", {})["N48_seed%d" % seed] = effective_gap
            energy = np.asarray([channel_amounts(day, CEILING) for day in days]).T
            exact_energy = [exact_amounts(raw[int(d) * 24:(int(d) + 1) * 24], F(int(CEILING))) for d in reps.day]
            exact_energy = list(map(list, zip(*exact_energy)))
            group = run.out / prefix
            group.mkdir()
            summary = read_frame(ROOT / ("results/annual/U11R12-v01/%s_summary.csv" % prefix))
            if list(summary.scenario) != [prefix + "_cluster%d" % k for k in range(48)]:
                raise ValueError("Saved dispatch inventory mismatch: " + prefix)
            counts_metrics = diagnostics(summary.to_dict("records"), full, counts,
                                         build_model(energy, target, counts, "l1", seed=seed), "counts")
            base = dict(cost_error=counts_metrics["cost_error_CNY"],
                        unserved_error=counts_metrics["unserved_error_MWh"])
            models, highs, cbc, proofs = {}, {}, {}, {}
            for rule in ("l1", "linf"):
                model = build_model(energy, target, counts, rule, seed=seed, N=48,
                                    days=[int(v) for v in reps.day], dates=list(reps.date_UTC))
                models[rule] = model
                dump(group / ("model_%s.json" % rule), model)
                original_t = max(abs(math.fsum(a * c for a, c in zip(row, counts)) / b - 1) if b else 0.
                                 for row, b in zip(model["energy"], model["target"]))
                if rule == "l1":
                    dump(group / "count_feasible_point.json",
                         dict(weights=counts, t=original_t, checks=check_solution(model, counts, original_t)))
                calls += 1
                highs[rule] = run_highs_rule(model, directory=group)
                if rule == "l1":
                    retained = group / "highs_primary"
                    retained.mkdir()
                    dump(retained / "problem.json", primary_problem(model))
                calls += len(highs[rule]["stages"]) - 1
                primary = highs[rule]["primary"]
                proofs[rule] = certificate(exact_energy, target_exact, counts, primary["weights"],
                                           primary["inequality_marginals"][:8], primary["equality_marginals"])
                if F(proofs[rule]["gap"]) > F("1e-8"):
                    raise ValueError("Exact certificate gap exceeds frozen guard: " + rule)
                dump(group / ("certificate_%s.json" % rule), proofs[rule])
                dump(group / ("stages_%s.json" % rule),
                     [{k: v for k, v in stage.items() if k != "x"} for stage in highs[rule]["stages"]])
            calls += 1
            cbc["l1"] = run_cbc_rule(models["l1"], "l1", True, group / "cbc")
            calls += len(cbc["l1"]["stages"]) - 1
            calls += 1
            cbc["linf"] = run_cbc_rule(models["linf"], "linf", False, group / "cbc")
            calls += len(cbc["linf"]["stages"]) - 1

            cross = {}
            for rule in ("l1", "linf"):
                differences = [abs(float(a["objective"]) - float(b["objective"]))
                               for a, b in zip(highs[rule]["stages"], cbc[rule]["stages"])]
                cross[rule] = dict(stages_compared=len(differences), max_objective_difference=max(differences))
                if max(differences) > 1e-8:
                    raise ValueError("Cross-solver objective difference: %s" % rule)
            weight_difference = identity_difference(highs["l1"]["final"]["weights"], cbc["l1"]["final"]["weights"])
            cross["l1"]["max_weight_difference"] = weight_difference

            final = {}
            for rule in ("l1", "linf"):
                weights = highs[rule]["final"]["weights"]
                final[rule] = weights
                frame = pd.DataFrame(dict(cluster=np.arange(48), day=[int(v) for v in reps.day],
                                          date_UTC=list(reps.date_UTC), c=counts, w=weights))
                frame.to_csv(group / ("weights_%s.csv" % rule), index=False, float_format="%.17g",
                             lineterminator="\n")
                if read_frame(group / ("weights_%s.csv" % rule)).w.to_numpy().tolist() != weights:
                    raise ValueError("Weight CSV lost precision: " + rule)
            cbc_frame = pd.DataFrame(dict(cluster=np.arange(48), day=[int(v) for v in reps.day],
                                          date_UTC=list(reps.date_UTC), c=counts,
                                          w=cbc["l1"]["final"]["weights"]))
            cbc_frame.to_csv(group / "weights_cbc_l1.csv", index=False, float_format="%.17g", lineterminator="\n")

            problem_path, solution_path = group / "primary_problem.json", group / "primary_solution.json"
            dump(problem_path, primary_problem(models["l1"]))
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(problem_path),
                       "--solution", str(solution_path)]
            process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=180,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            (group / "primary_worker.log").write_text(process.stdout + process.stderr, encoding="utf-8")
            process.check_returncode()
            independent = json.loads(solution_path.read_text(encoding="utf-8"))
            reference = highs["l1"]["primary"]
            objective_difference = abs(float(independent["objective"]) - float(reference["objective"]))
            independent_difference = identity_difference(independent["weights"], reference["weights"])
            if objective_difference > 1e-10 or independent_difference > 1e-7:
                raise ValueError("Independent-process primary re-solve mismatch")
            calls += 1

            row = diagnostics(summary.to_dict("records"), full, final["l1"], models["l1"], "l1")
            linf_row = diagnostics(summary.to_dict("records"), full, final["linf"], models["linf"], "linf")
            diagnostics_rows += [counts_metrics, row, linf_row]
            structure_rows += [dict(seed=seed, rule=r, **structure(final[r], counts)) for r in ("l1", "linf")]
            classification = classify(float(highs["l1"]["primary"]["t"]), proofs["l1"])
            if classification != classify(float(highs["linf"]["primary"]["t"]), proofs["linf"]):
                raise ValueError("Rule-family classification mismatch")
            h1_rows.append(dict(seed=seed, classification=classification,
                                cross_solver_ok=bool(cross["l1"]["max_objective_difference"] <= 1e-8
                                                     and weight_difference <= WEIGHT_IDENTITY_TOL),
                                E=row["worst_error_pp"],
                                max_input_relative_error=row["four_channel_relative_error"]))
            h2_rows.append(dict(seed=seed, cost_error_CNY=row["cost_error_CNY"],
                                unserved_error_MWh=row["unserved_error_MWh"],
                                base_cost_error_CNY=base["cost_error"],
                                base_unserved_error_MWh=base["unserved_error"]))
            comparison.append(dict(seed=seed, N=48, classification=classification,
                                   highs_t=float(highs["l1"]["primary"]["t"]),
                                   cbc_t=float(cbc["l1"]["primary"]["t"]),
                                   highs_t_linf=float(highs["linf"]["primary"]["t"]),
                                   cbc_t_linf=float(cbc["linf"]["primary"]["t"]),
                                   exact_lower=proofs["l1"]["lower_float"],
                                   exact_upper=proofs["l1"]["upper_float"],
                                   l1_objective=float(highs["l1"]["stages"][1]["objective"]),
                                   linf_objective=float(highs["linf"]["stages"][1]["objective"]),
                                   max_objective_difference=cross["l1"]["max_objective_difference"],
                                   max_weight_difference=weight_difference,
                                   independent_objective_difference=objective_difference,
                                   independent_weight_difference=independent_difference))
            print(seed, classification, "E", row["worst_error_pp"], "D", row["four_channel_relative_error"],
                  "moved", structure(final["l1"], counts)["moved_days"], flush=True)

        if calls != EXPECTED_LP_CALLS:
            raise ValueError("Frozen solve budget mismatch: %d" % calls)
        if run.manifest["cases"]:
            raise ValueError("Dispatch budget must stay zero")
        pd.DataFrame(comparison).to_csv(run.out / "comparison.csv", index=False, float_format="%.17g",
                                        lineterminator="\n")
        pd.DataFrame(diagnostics_rows).to_csv(run.out / "diagnostics.csv", index=False, float_format="%.17g",
                                              lineterminator="\n")
        pd.DataFrame(structure_rows).to_csv(run.out / "structure.csv", index=False, float_format="%.17g",
                                            lineterminator="\n")
        pd.DataFrame(h1_rows).to_csv(run.out / "h1_matrix.csv", index=False, float_format="%.17g",
                                     lineterminator="\n")
        pd.DataFrame(h2_rows).to_csv(run.out / "h2_matrix.csv", index=False, float_format="%.17g",
                                     lineterminator="\n")
        h1 = h1_verdict(h1_rows)
        h2 = h2_verdict(h2_rows)
        for path, digest in run.manifest["source_sha256"].items():
            if sha(ROOT / path) != digest:
                raise ValueError("Source drift: " + path)
        run.manifest.update(lp_calls=calls, dispatch_calls=0, h1=h1, h2=h2)
        run.finish(h1, dict(primary_lp_calls=PRIMARY_LP_BUDGET, dispatch_calls=0, groups=3, rules=["l1", "linf"],
                            classification=[r["classification"] for r in comparison], h1=h1, h2=h2,
                            elapsed_seconds=perf_counter() - started))
    except Exception as exc:
        run.manifest.update(status="blocked", verdict="invalid", error=repr(exc), lp_calls=calls, dispatch_calls=0)
        dump(run.out / "failure.json", dict(error=repr(exc), lp_calls=calls, dispatch_calls=0))
        raise
    finally:
        run.manifest["artifacts"] = {p.relative_to(run.out).as_posix(): sha(p)
                                     for p in run.out.rglob("*") if p.is_file() and p.name != "run_manifest.json"}
        dump(run.out / "run_manifest.json", run.manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="U11R15-v01")
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--solution", type=Path)
    args = parser.parse_args()
    if args.worker:
        if args.solution is None:
            parser.error("--solution is required")
        run_worker(args.worker, args.solution)
    else:
        run(args.run_id)


if __name__ == "__main__":
    main()
