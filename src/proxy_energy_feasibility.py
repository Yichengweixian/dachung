"""Four input-only channels and one minimax LP; no dispatch/selection changes."""
import math

import numpy as np
import pulp

from .cbc_weight_evidence import EvidenceCBC
from .data_loader import validate_input_data
from .input_energy_feasibility import check_solution

CHANNELS = ["load","wind","solar","excess_proxy"]
SEEDS = (42,7,2026)


def amounts(data, ceiling):
    validate_input_data(data)
    if not math.isfinite(ceiling) or ceiling <= 0: raise ValueError("Invalid thermal ceiling")
    values = [math.fsum(data[channel]) for channel in CHANNELS[:3]]
    values.append(math.fsum(max(float(row.load)-float(row.wind)-float(row.solar)-ceiling,0.) for row in data.itertuples()))
    if not all(math.isfinite(x) for x in values): raise ValueError("Nonfinite input amounts")
    return values


def build_model(energy, target, counts):
    a,b,c = (np.asarray(x,dtype=float) for x in (energy,target,counts))
    if c.ndim != 1 or not len(c) or a.shape != (4,len(c)) or b.shape != (4,): raise ValueError("Invalid four-channel dimensions")
    if not all(np.isfinite(x).all() for x in (a,b,c)) or (a < 0).any() or (b < 0).any() or (c <= 0).any() or (c % 1 != 0).any() or math.fsum(c) != 365:
        raise ValueError("Invalid finite inputs/counts")
    if np.any(a[b == 0] != 0): raise ValueError("Nonzero representative for zero target")
    rows, rhs = [], []
    for k in range(4):
        if b[k]:
            rows.extend([np.r_[a[k]/b[k],-1].tolist(),np.r_[-a[k]/b[k],-1].tolist()])
            rhs.extend([1.,-1.])
    return dict(energy=a.tolist(),target=b.tolist(),counts=c.tolist(),channels=CHANNELS,
                objective=[0.]*len(c)+[1.],A_ub=rows,b_ub=rhs,A_eq=[[1.]*len(c)+[0.]],b_eq=[365.],
                bounds=[[.5*x,2*x] for x in c]+[[0.,None]])


def cbc(model, directory):
    problem = pulp.LpProblem("U11R14_four_input_channels",pulp.LpMinimize)
    w = [pulp.LpVariable(f"w_{i:03d}",c/2.,2*c) for i,c in enumerate(model["counts"])]
    t = pulp.LpVariable("worst_relative_error",0.)
    problem += t
    problem += pulp.lpSum(w) == 365,"total_days"
    for k,(row,rhs) in enumerate(zip(model["A_ub"],model["b_ub"])):
        problem += pulp.lpSum(float(a)*x for a,x in zip(row[:-1],w))-t <= rhs,f"channel_{k}"
    directory.mkdir()
    problem.writeLP(str(directory/"model.lp"))
    solver = EvidenceCBC(msg=False,artifact_directory=directory/"native")
    record = dict(status="attempted")
    try:
        problem.solve(solver)
        record.update(status=pulp.LpStatus[problem.status],solution_status=problem.sol_status,log=getattr(solver,"log",""))
        if problem.status != pulp.LpStatusOptimal or problem.sol_status != pulp.LpSolutionOptimal: raise RuntimeError("CBC did not prove Optimal: "+record["status"])
        record.update(weights=[float(v.value()) for v in w],t=float(t.value()),objective=float(pulp.value(problem.objective)),precision=solver.precision)
        record["checks"] = check_solution(model,record["weights"],record["t"])
        return record
    except Exception as exc:
        record.update(error=repr(exc),log=getattr(solver,"log",""))
        raise
    finally:
        from .study_runtime import dump
        dump(directory/"solution.json",record)


def decision(rows):
    if len(rows) != 3 or {r["seed"] for r in rows} != set(SEEDS): raise ValueError("Incomplete/duplicate matrix")
    states = {r["classification"] for r in rows}
    if not states <= {"reachable","unreachable","uncertain"}: raise ValueError("Unknown classification")
    return "refuted" if "unreachable" in states else "inconclusive" if "uncertain" in states else "supported"
