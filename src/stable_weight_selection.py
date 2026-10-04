"""U11R15: four-channel lexicographic weight rules — minimax -> L1/L-infinity -> date-order pinning.

Read-only reuse of the established evidence stack:
* `src.cbc_weight_evidence.EvidenceCBC` for native-precision CBC solves,
* `src.input_energy_feasibility.check_solution` for the single-LP feasibility gate,
* `scripts.audit_u11r08_feasibility.certificate/classify` for the exact rational minimax certificate.
Nothing in this module touches saved data or older units.
"""
import math
from pathlib import Path

import numpy as np
import pulp
from scipy import optimize

from .cbc_weight_evidence import EvidenceCBC
from .input_energy_feasibility import check_solution

BAND = 1e-6
RULES = ("l1", "linf")
CHANNELS = ("load", "wind", "solar", "excess_proxy")
E_GATE = 1.0
D_GATE = 0.02
MARGIN = 1e-6
WEIGHT_IDENTITY_TOL = 1e-4
BOUND_RESIDUAL = 1e-7
NORMALIZED_RESIDUAL = 1e-8
LIMIT_RESIDUAL = 1e-7


def build_model(energy, target, counts, rule, **meta):
    """Validate a four-channel instance and attach identity metadata."""
    a, b, c = (np.asarray(x, dtype=float) for x in (energy, target, counts))
    if rule not in RULES:
        raise ValueError("Unknown rule: " + str(rule))
    if c.ndim != 1 or not len(c) or a.shape != (4, len(c)) or b.shape != (4,):
        raise ValueError("Invalid four-channel dimensions")
    if (not all(np.isfinite(x).all() for x in (a, b, c)) or (a < 0).any() or (b < 0).any()
            or (c <= 0).any() or (c % 1 != 0).any() or math.fsum(c) != 365):
        raise ValueError("Invalid finite inputs/counts")
    if np.any(a[b == 0] != 0):
        raise ValueError("Nonzero representative for zero target")
    model = dict(energy=a.tolist(), target=b.tolist(), counts=c.tolist(), rule=rule,
                 channels=list(CHANNELS), band=BAND, unit="MWh")
    model.update(meta)
    return model


def stage_specs(model):
    """primary -> secondary -> one pinning stage per cluster, ordered by (date_UTC, index)."""
    order = sorted(range(len(model["counts"])), key=lambda i: (str(model["dates"][i]), i))
    specs = [dict(name="primary", objective="t", index=None),
             dict(name="secondary", objective="l1" if model["rule"] == "l1" else "linf", index=None)]
    specs += [dict(name="pin_%03d" % i, objective="w", index=i) for i in order]
    return specs


def _layout(model, with_secondary):
    n = len(model["counts"])
    if not with_secondary:
        return dict(n=n, t=n, nv=n + 1, secondary=None)
    return dict(n=n, t=n, secondary=n + 1, nv=n + 1 + (n if model["rule"] == "l1" else 1))


def _rows(model, layout, fixed):
    """Return (A_ub, b_ub) for a stage; fixed carries t_limit, s_limit and pins."""
    a = np.asarray(model["energy"], dtype=float)
    b = np.asarray(model["target"], dtype=float)
    c = np.asarray(model["counts"], dtype=float)
    n, nv, tcol, sec = layout["n"], layout["nv"], layout["t"], layout["secondary"]
    A_ub, b_ub = [], []

    def row():
        return np.zeros(nv)

    for k in range(4):
        if b[k] <= 0:
            continue
        r = row(); r[:n] = a[k] / b[k]; r[tcol] = -1.0
        A_ub.append(r); b_ub.append(1.0)
        r = row(); r[:n] = -a[k] / b[k]; r[tcol] = -1.0
        A_ub.append(r); b_ub.append(-1.0)
    if sec is not None:
        for i in range(n):
            r = row(); r[i] = 1.0 / c[i]; r[sec + (i if model["rule"] == "l1" else 0)] = -1.0
            A_ub.append(r); b_ub.append(1.0)
            r = row(); r[i] = -1.0 / c[i]; r[sec + (i if model["rule"] == "l1" else 0)] = -1.0
            A_ub.append(r); b_ub.append(-1.0)
        if fixed.get("s_limit") is not None:
            r = row()
            if model["rule"] == "l1":
                r[sec:sec + n] = 1.0
            else:
                r[sec] = 1.0
            A_ub.append(r); b_ub.append(float(fixed["s_limit"]))
    if fixed.get("t_limit") is not None:
        r = row(); r[tcol] = 1.0
        A_ub.append(r); b_ub.append(float(fixed["t_limit"]))
    for index, lower, upper in fixed.get("pins", []):
        r = row(); r[index] = 1.0
        A_ub.append(r); b_ub.append(float(upper))
        r = row(); r[index] = -1.0
        A_ub.append(r); b_ub.append(-float(lower))
    return [r.tolist() for r in A_ub], b_ub


def highs_problem(model, spec, fixed):
    """scipy.linprog problem dict for one stage (JSON serialisable)."""
    with_secondary = spec["objective"] != "t"
    layout = _layout(model, with_secondary)
    n, nv, tcol, sec = layout["n"], layout["nv"], layout["t"], layout["secondary"]
    A_ub, b_ub = _rows(model, layout, fixed)
    objective = np.zeros(nv)
    if spec["objective"] == "t":
        objective[tcol] = 1.0
    elif spec["objective"] == "l1":
        objective[sec:sec + n] = 1.0
    elif spec["objective"] == "linf":
        objective[sec] = 1.0
    elif spec["objective"] == "w":
        objective[spec["index"]] = 1.0
    else:
        raise ValueError("Unknown objective: " + str(spec["objective"]))
    c = np.asarray(model["counts"], dtype=float)
    bounds = [[float(.5 * v), float(2 * v)] for v in c] + [[0.0, None]] * (nv - n)
    return dict(stage=spec["name"], objective=spec["objective"], index=spec["index"],
                with_secondary=with_secondary, layout=layout, c=[float(x) for x in c],
                objective_vector=objective.tolist(), A_ub=A_ub, b_ub=b_ub,
                A_eq=[[1.0] * n + [0.0] * (nv - n)], b_eq=[365.0], bounds=bounds)


def solve_highs(problem):
    """Solve one stage with HiGHS; return the full solution record (no retries)."""
    result = optimize.linprog(problem["objective_vector"], A_ub=problem["A_ub"] or None,
                              b_ub=problem["b_ub"] or None, A_eq=problem["A_eq"], b_eq=problem["b_eq"],
                              bounds=problem["bounds"], method="highs-ds",
                              options={"presolve": True, "primal_feasibility_tolerance": 1e-9,
                                       "dual_feasibility_tolerance": 1e-9, "time_limit": 60., "disp": False})
    record = dict(stage=problem["stage"], objective=problem["objective"], index=problem["index"],
                  solver="highs", success=bool(result.success), status=int(result.status),
                  message=str(result.message), iterations=int(result.nit))
    if not (result.success and result.status == 0):
        raise RuntimeError("HiGHS stage not Optimal: " + repr(record))
    n = problem["layout"]["n"]
    record.update(x=[float(v) for v in result.x], objective=float(result.fun),
                  weights=[float(v) for v in result.x[:n]], t=float(result.x[problem["layout"]["t"]]),
                  inequality_marginals=[float(v) for v in result.ineqlin.marginals],
                  equality_marginals=[float(v) for v in result.eqlin.marginals])
    if problem["layout"]["secondary"] is not None:
        sec = problem["layout"]["secondary"]
        if problem["with_secondary"]:
            if problem["objective"] == "linf" or problem["objective"] == "w":
                record["secondary_value"] = float(result.x[sec])
            if problem["objective"] in ("l1", "w"):
                record["deviations"] = [float(v) for v in result.x[sec:sec + n]]
                record["secondary_value"] = float(np.sum(result.x[sec:sec + n]))
    else:
        record["secondary_value"] = None
    return record


def pulp_problem(model, spec, fixed):
    """pulp model for one stage, used for the native CBC cross path."""
    c = [float(v) for v in model["counts"]]
    a = [[float(v) for v in row] for row in model["energy"]]
    b = [float(v) for v in model["target"]]
    n = len(c)
    problem = pulp.LpProblem("U11R15_%s_%s" % (model["rule"], spec["name"]), pulp.LpMinimize)
    w = [pulp.LpVariable("w_%03d" % i, .5 * value, 2 * value) for i, value in enumerate(c)]
    t = pulp.LpVariable("worst_relative_error", 0)
    d = [pulp.LpVariable("d_%03d" % i, 0) for i in range(n)] if model["rule"] == "l1" else []
    u = pulp.LpVariable("worst_absolute_deviation", 0) if model["rule"] == "linf" else None
    for k in range(4):
        if b[k] <= 0:
            continue
        relative = pulp.lpSum(a[k][i] / b[k] * w[i] for i in range(n)) - 1
        problem += relative <= t, "channel_pos_%d" % k
        problem += -relative <= t, "channel_neg_%d" % k
    problem += pulp.lpSum(w) == 365, "total_days"
    if model["rule"] == "l1":
        for i in range(n):
            problem += d[i] >= (w[i] - c[i]) / c[i], "dev_pos_%d" % i
            problem += d[i] >= (c[i] - w[i]) / c[i], "dev_neg_%d" % i
    else:
        for i in range(n):
            problem += u >= (w[i] - c[i]) / c[i], "dev_pos_%d" % i
            problem += u >= (c[i] - w[i]) / c[i], "dev_neg_%d" % i
    if fixed.get("t_limit") is not None:
        problem += t <= float(fixed["t_limit"]), "primary_band"
    if fixed.get("s_limit") is not None:
        problem += (pulp.lpSum(d) if model["rule"] == "l1" else u) <= float(fixed["s_limit"]), "secondary_band"
    for index, lower, upper in fixed.get("pins", []):
        problem += w[index] >= float(lower), "pin_lower_%d" % index
        problem += w[index] <= float(upper), "pin_upper_%d" % index
    objective = {"t": t, "l1": pulp.lpSum(d), "linf": u}[spec["objective"]] if spec["objective"] != "w" \
        else w[spec["index"]]
    problem += objective
    return problem, dict(w=w, t=t, d=d, u=u)


def solve_cbc(model, spec, fixed, directory=None):
    """Solve one stage with native-precision CBC.

    `directory` is None for the (numerous) pinning stages, which then solve with temporary
    native artifacts; the decisive primary/secondary stages retain MPS and native solution files.
    """
    problem, variables = pulp_problem(model, spec, fixed)
    directory = None if directory is None else Path(directory)
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=False)
        problem.writeLP(str(directory / "model.lp"))
    solver = EvidenceCBC(msg=False, artifact_directory=None if directory is None else directory / "native")
    record = dict(stage=spec["name"], solver="cbc", objective_name=spec["objective"], status="attempted",
                  native_artifacts=bool(directory is not None))
    try:
        problem.solve(solver)
        record.update(status=pulp.LpStatus[problem.status], solution_status=problem.sol_status,
                      log=getattr(solver, "log", ""), precision=getattr(solver, "precision", {}))
        if problem.status != pulp.LpStatusOptimal or problem.sol_status != pulp.LpSolutionOptimal:
            raise RuntimeError("CBC stage not Optimal: " + str(record["status"]))
        weights = [float(v.value()) for v in variables["w"]]
        record.update(weights=weights, t=float(variables["t"].value()),
                      objective=float(pulp.value(problem.objective)))
        if model["rule"] == "l1":
            record["deviations"] = [float(v.value()) for v in variables["d"]]
            record["secondary_value"] = float(sum(record["deviations"]))
        else:
            record["secondary_value"] = float(variables["u"].value())
        if spec["objective"] == "t":
            record["secondary_value"] = None
        return record
    except Exception as exc:
        record.update(error=repr(exc), log=getattr(solver, "log", ""))
        raise
    finally:
        if directory is not None:
            from .study_runtime import dump
            dump(directory / "solution.json", {k: v for k, v in record.items() if k != "deviations"})


def stage_residuals(model, weights, t, secondary_value, fixed):
    """Frozen-gate residuals for one stage solution."""
    c = np.asarray(model["counts"], dtype=float)
    w = np.asarray(weights, dtype=float)
    a = np.asarray(model["energy"], dtype=float)
    b = np.asarray(model["target"], dtype=float)
    if w.shape != c.shape or not np.isfinite(np.r_[w, t]).all():
        raise ValueError("Nonfinite or incomplete stage solution")
    bounds = max(0.0, float(np.max(.5 * c - w)), float(np.max(w - 2 * c)), abs(float(math.fsum(w)) - 365))
    errors = [abs(float(math.fsum(a[k][i] * w[i] for i in range(len(c)))) / b[k] - 1) for k in range(4) if b[k] > 0]
    normalized = max([0.0, -float(t)] + [max(0.0, e - float(t)) for e in errors])
    limit = 0.0
    if fixed.get("t_limit") is not None:
        limit = max(limit, float(t) - float(fixed["t_limit"]))
    if fixed.get("s_limit") is not None:
        if secondary_value is None:
            raise ValueError("Missing secondary value for a banded stage")
        limit = max(limit, float(secondary_value) - float(fixed["s_limit"]))
    for index, lower, upper in fixed.get("pins", []):
        limit = max(limit, float(lower) - float(w[index]), float(w[index]) - float(upper))
    return dict(bounds=bounds, normalized=normalized, limit=max(0.0, limit), channel_errors=errors)


def require_stage(model, weights, t, secondary_value, fixed):
    residuals = stage_residuals(model, weights, t, secondary_value, fixed)
    if residuals["bounds"] > BOUND_RESIDUAL:
        raise ValueError("Stage bound/sum residual: %r" % residuals)
    if residuals["normalized"] > NORMALIZED_RESIDUAL:
        raise ValueError("Stage normalized residual: %r" % residuals)
    if residuals["limit"] > LIMIT_RESIDUAL:
        raise ValueError("Stage band/pin residual: %r" % residuals)
    return residuals


def run_highs_rule(model, directory=None, dump_stages=("primary", "secondary")):
    """Run the frozen HiGHS hierarchy for one instance/rule; returns the stage record set. No retries."""
    directory = Path(directory) if directory is not None else None
    stage_records, t_limit, s_limit, pins = [], None, None, []
    for spec in stage_specs(model):
        fixed = dict(t_limit=t_limit, s_limit=s_limit, pins=list(pins))
        problem = highs_problem(model, spec, fixed)
        if directory is not None and spec["name"] in dump_stages:
            from .study_runtime import dump
            dump(directory / ("highs_%s.json" % spec["name"]), problem)
        record = solve_highs(problem)
        residuals = require_stage(model, record["weights"], record["t"], record.get("secondary_value"), fixed)
        record["residuals"] = residuals
        record["fixed"] = dict(t_limit=t_limit, s_limit=s_limit, pins=[list(p) for p in pins])
        stage_records.append(record)
        if spec["objective"] == "t":
            t_limit = record["objective"] + BAND
            primary = record
        elif spec["objective"] in ("l1", "linf"):
            s_limit = record["objective"] + BAND
        else:
            index = spec["index"]
            value = record["weights"][index]
            pins.append((index, max(.5 * model["counts"][index], value - BAND),
                         min(2. * model["counts"][index], value + BAND)))
    return dict(rule=model["rule"], stages=stage_records, primary=stage_records[0],
                final=stage_records[-1], t_limit=t_limit, s_limit=s_limit, pins=[list(p) for p in pins])


def run_cbc_rule(model, rule, budget_full, directory, retain_stages=("primary", "secondary")):
    """Run the CBC cross path: all stages for `l1`, top level only for `linf`."""
    stages, t_limit, s_limit, pins = [], None, None, []
    for spec in stage_specs(model):
        if not budget_full and spec["objective"] == "w":
            break
        fixed = dict(t_limit=t_limit, s_limit=s_limit, pins=list(pins))
        target = None if directory is None or spec["name"] not in retain_stages else directory / ("%s_%s" % (rule, spec["name"]))
        record = solve_cbc(model, spec, fixed, target)
        residuals = require_stage(model, record["weights"], record["t"], record.get("secondary_value"), fixed)
        record["residuals"] = residuals
        record["fixed"] = dict(t_limit=t_limit, s_limit=s_limit, pins=[list(p) for p in pins])
        stages.append(record)
        if spec["objective"] == "t":
            t_limit = record["objective"] + BAND
        elif spec["objective"] in ("l1", "linf"):
            s_limit = record["objective"] + BAND
        else:
            index = spec["index"]
            value = record["weights"][index]
            pins.append((index, max(.5 * model["counts"][index], value - BAND),
                         min(2. * model["counts"][index], value + BAND)))
    return dict(rule=rule, stages=stages, primary=stages[0], final=stages[-1],
                t_limit=t_limit, s_limit=s_limit, pins=[list(p) for p in pins])


def h1_verdict(rows):
    """Frozen H1: reachable + four-channel D<=2% + E<=1.0 pp for all three seeds."""
    if len(rows) != 3 or {r["seed"] for r in rows} != {42, 7, 2026}:
        raise ValueError("Incomplete H1 matrix")
    for row in rows:
        if row["classification"] == "uncertain" or not row.get("cross_solver_ok", False):
            return "inconclusive"
        if row["classification"] == "unreachable":
            return "refuted"
        if abs(row["E"] - E_GATE) <= MARGIN:
            return "inconclusive"
        if row["E"] > E_GATE:
            return "refuted"
        if row["max_input_relative_error"] > D_GATE + MARGIN:
            return "refuted"
    return "supported"


def h2_verdict(rows):
    """Frozen H2: L1 |cost| and |unserved| errors no larger than the cluster-count baseline."""
    if len(rows) != 3 or {r["seed"] for r in rows} != {42, 7, 2026}:
        raise ValueError("Incomplete H2 matrix")
    for row in rows:
        for key, base in (("cost_error_CNY", "base_cost_error_CNY"),
                          ("unserved_error_MWh", "base_unserved_error_MWh")):
            margin = MARGIN * max(1.0, abs(float(row[base])))
            difference = abs(float(row[key])) - abs(float(row[base]))
            if abs(difference) <= margin:
                return "inconclusive"
            if difference > 0:
                return "refuted"
    return "supported"


def identity_difference(first, second):
    """Max absolute difference between two weight vectors (cross-solver identity check)."""
    if len(first) != len(second):
        raise ValueError("Weight length mismatch")
    return max(abs(float(a) - float(b)) for a, b in zip(first, second))
