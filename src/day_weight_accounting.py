"""Additive two-order accounting, not a causal estimator or optimizer."""
import math

import numpy as np
import pandas as pd

from .cost_unserved_attribution import COSTS, METRICS, SEEDS, close

PATH_COLUMNS = ("Y00", "Y10", "Y01", "Y11", "delta", "day_first", "weight_after_day",
                "weight_first", "day_after_weight", "interaction", "day_average", "weight_average")


def path_check(row):
    return max(close(row["delta"], row["day_first"]+row["weight_after_day"], "day-first path"),
               close(row["delta"], row["weight_first"]+row["day_after_weight"], "weight-first path"),
               close(row["delta"], row["day_average"]+row["weight_average"], "average path"),
               close(row["interaction"], row["day_after_weight"]-row["day_first"], "day interaction"),
               close(row["interaction"], row["weight_after_day"]-row["weight_first"], "weight interaction"),
               close(row["delta"], row["Y11"]-row["Y00"], "cross-grid delta"))


def paths(old_rows, new_rows, counts, old_weights, new_weights):
    old = pd.DataFrame(old_rows)[list(METRICS)].to_numpy(dtype=float)
    new = pd.DataFrame(new_rows)[list(METRICS)].to_numpy(dtype=float)
    c, w0, w1 = [np.asarray(x,dtype=float) for x in (counts,old_weights,new_weights)]
    if old.shape != (48,len(METRICS)) or new.shape != old.shape or any(x.shape != (48,) for x in (c,w0,w1)):
        raise ValueError("Incomplete day/weight matrix")
    if not all(np.isfinite(x).all() for x in (old,new,c,w0,w1)) or (c <= 0).any() or (c % 1 != 0).any() or c.sum() != 365:
        raise ValueError("Invalid/nonfinite accounting inputs")
    for w in (w0,w1):
        if abs(float(w.sum())-365) > 1e-6 or (w < .5*c-1e-6).any() or (w > 2*c+1e-6).any():
            raise ValueError("Invalid frozen weight bounds/sum")
    annual, clusters, maximum = [], [], 0.
    for j,metric in enumerate(METRICS):
        cells = []
        for k in range(48):
            r0, r1 = old[k,j], new[k,j]
            d0, q0 = w0[k]*(r1-r0), (w1[k]-w0[k])*r0
            interaction = (w1[k]-w0[k])*(r1-r0)
            row = dict(Y00=w0[k]*r0, Y10=w0[k]*r1, Y01=w1[k]*r0, Y11=w1[k]*r1,
                       delta=w1[k]*r1-w0[k]*r0, day_first=d0, weight_after_day=(w1[k]-w0[k])*r1,
                       weight_first=q0, day_after_weight=w1[k]*(r1-r0), interaction=interaction,
                       day_average=d0+interaction/2., weight_average=q0+interaction/2.)
            maximum = max(maximum,path_check(row))
            cells.append(row)
            clusters.append(dict(metric=metric,cluster=k,**row))
        row = {key:math.fsum(cell[key] for cell in cells) for key in PATH_COLUMNS}
        maximum = max(maximum,path_check(row))
        annual.append(dict(metric=metric,**row))
    return pd.DataFrame(annual), pd.DataFrame(clusters), maximum


def path_cost_check(table, penalty):
    q = table.set_index("metric")
    maximum = 0.
    for key in PATH_COLUMNS:
        maximum = max(maximum,close(math.fsum(q.loc[k,key] for k in COSTS),q.loc["total_cost_CNY",key],"six-fee path "+key),
                      close(penalty*q.loc["unserved_MWh",key],q.loc["load_shedding_cost_CNY",key],"shortage path "+key))
    return maximum


def hypothesis(annual):
    q = annual[(annual.day_set == "new") & annual.metric.isin(("total_cost_CNY","unserved_MWh"))]
    expected = {(seed,k) for seed in SEEDS for k in ("total_cost_CNY","unserved_MWh")}
    if len(q) != 6 or set(zip(q.seed,q.metric)) != expected or not np.isfinite(q[["replacement","total"]].to_numpy()).all():
        raise ValueError("Incomplete/nonfinite retrospective hypothesis matrix")
    rows = []
    for seed in SEEDS:
        for metric in ("total_cost_CNY","unserved_MWh"):
            row = q[(q.seed == seed) & (q.metric == metric)].iloc[0]
            increase = abs(float(row.total))-abs(float(row.replacement))
            state = "increased" if increase > 1e-6 else "reduced" if increase < -1e-6 else "unchanged"
            rows.append(dict(seed=seed,metric=metric,count_error=float(row.replacement),
                             calibrated_error=float(row.total),absolute_error_increase=increase,state=state))
    states = {row["state"] for row in rows}
    verdict = "refuted" if "reduced" in states else "inconclusive" if "unchanged" in states else "supported"
    return verdict,rows
