"""Additive accounting of fixed representative-day and weight errors."""
import math

import numpy as np
import pandas as pd

COSTS = ("thermal_cost_CNY", "curtailment_cost_CNY", "load_shedding_cost_CNY",
         "storage_variable_om_CNY", "storage_investment_allocated_CNY", "storage_fixed_om_CNY")
METRICS = ("renewable_available_MWh", "renewable_used_MWh", "curtailment_MWh",
           "total_load_MWh", "thermal_generation_MWh", "unserved_MWh", "discharge_MWh",
           "total_cost_CNY") + COSTS
SCENARIOS = (("E0_P0", 0., 0.), ("E40_P20", 40., 20.), ("E80_P20", 80., 20.))
SEEDS = (42, 7, 2026)


def close(actual, expected, label):
    difference = abs(float(actual)-float(expected))
    if not math.isfinite(difference) or difference >= 1e-6:
        raise ValueError(f"Accounting mismatch {label}: {difference}")
    return difference


def effect(replacement, total):
    difference = abs(total)-abs(replacement)
    return "reduced" if difference < -1e-6 else "increased" if difference > 1e-6 else "unchanged"


def decompose(full_rows, rep_rows, labels, counts, weights):
    full = pd.DataFrame(full_rows)[list(METRICS)].to_numpy(dtype=float)
    reps = pd.DataFrame(rep_rows)[list(METRICS)].to_numpy(dtype=float)
    labels = np.asarray(labels)
    counts, weights = np.asarray(counts, dtype=float), np.asarray(weights, dtype=float)
    if full.shape != (365, len(METRICS)) or reps.shape != (48, len(METRICS)) or labels.shape != (365,):
        raise ValueError("Incomplete fixed decomposition dimensions")
    if not all(np.isfinite(x).all() for x in (full, reps, labels, counts, weights)):
        raise ValueError("Nonfinite accounting input")
    if counts.shape != (48,) or weights.shape != (48,) or (labels % 1 != 0).any() or set(labels) != set(range(48)):
        raise ValueError("Invalid fixed cluster or weight dimensions")
    labels = labels.astype(int)
    if not np.array_equal(counts, np.bincount(labels, minlength=48)):
        raise ValueError("Cluster counts differ from actual memberships")
    if abs(float(weights.sum())-365.) > 1e-6 or (weights < .5*counts-1e-6).any() or (weights > 2*counts+1e-6).any():
        raise ValueError("Invalid frozen weight bounds/sum")
    annual, clusters = [], []
    maximum = 0.
    for j, metric in enumerate(METRICS):
        actual = math.fsum(full[:, j])
        control = float(np.dot(counts, reps[:, j]))
        calibrated = float(np.dot(weights, reps[:, j]))
        replacement, adjustment, total = control-actual, calibrated-control, calibrated-actual
        maximum = max(maximum, close(total, replacement+adjustment, metric+" annual identity"))
        signed = []
        for k in range(48):
            cluster_actual = math.fsum(full[labels == k, j])
            s = float(counts[k]*reps[k, j]-cluster_actual)
            a = float((weights[k]-counts[k])*reps[k, j])
            t = float(weights[k]*reps[k, j]-cluster_actual)
            maximum = max(maximum, close(t, s+a, metric+" cluster identity"))
            clusters.append(dict(metric=metric, cluster=k, cluster_full=cluster_actual,
                                 representative_value=float(reps[k, j]), replacement=s, adjustment=a, total=t))
            signed.append((s, a, t))
        for index, value in enumerate((replacement, adjustment, total)):
            maximum = max(maximum, close(math.fsum(x[index] for x in signed), value, metric+" cluster sum"))
        gross = math.fsum(abs(x[2]) for x in signed)
        net = math.fsum(x[2] for x in signed)
        cancellation = 1-abs(net)/gross if gross else 0.
        if not 0 <= cancellation <= 1:
            raise ValueError("Invalid signed cancellation ratio")
        annual.append(dict(metric=metric, full=actual, control=control, calibrated=calibrated,
                           replacement=replacement, adjustment=adjustment, total=total,
                           weight_effect=effect(replacement, total), gross_cluster_error=gross,
                           cancellation_fraction=cancellation))
    return pd.DataFrame(annual), pd.DataFrame(clusters), maximum


def cost_check(annual, penalty):
    table = annual.set_index("metric")
    differences = []
    for column in ("full", "control", "calibrated", "replacement", "adjustment", "total"):
        differences.append(close(math.fsum(table.loc[k, column] for k in COSTS),
                                 table.loc["total_cost_CNY", column], "six costs "+column))
        differences.append(close(table.loc["load_shedding_cost_CNY", column],
                                 penalty*table.loc["unserved_MWh", column], "shortage fee "+column))
    return max(differences)


def hypothesis(cost_rows):
    table = pd.DataFrame(cost_rows)
    if len(table) != 54 or set(zip(table.capacity_scenario, table.seed, table.metric)) != {
            (s, seed, metric) for s, _, _ in SCENARIOS for seed in SEEDS for metric in COSTS}:
        raise ValueError("Incomplete fee attribution matrix")
    if not np.isfinite(table.total).all():
        raise ValueError("Nonfinite fee attribution")
    decisions = []
    for scenario, _, _ in SCENARIOS:
        q = table[(table.capacity_scenario == scenario) & (table.seed == 7)]
        shortage = abs(float(q[q.metric == "load_shedding_cost_CNY"].total.iloc[0]))
        others = max(abs(float(x)) for x in q[q.metric != "load_shedding_cost_CNY"].total)
        margin = shortage-others
        state = "dominant" if margin > 1e-6 else "other_dominant" if margin < -1e-6 else "tie"
        decisions.append(dict(capacity_scenario=scenario, seed=7, shortage_abs_CNY=shortage,
                              next_abs_CNY=others, margin_CNY=margin, state=state))
    states = {row["state"] for row in decisions}
    verdict = "refuted" if "other_dominant" in states else "inconclusive" if "tie" in states else "supported"
    return verdict, decisions


def top_contributors(clusters):
    selected = clusters[clusters.metric.isin(("total_cost_CNY", "unserved_MWh"))].copy()
    selected["absolute_total"] = selected.total.abs()
    selected = selected.sort_values(["capacity_scenario", "seed", "metric", "absolute_total", "cluster"],
                                    ascending=[True, True, True, False, True])
    return selected.groupby(["capacity_scenario", "seed", "metric"], sort=False).head(5).reset_index(drop=True)
