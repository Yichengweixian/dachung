"""Fixed, previously calibrated representative days; no fitting or clustering."""
import numbers

import numpy as np
import pandas as pd

SEEDS = (42, 7, 2026)
SCENARIOS = (("E0_P0", 0., 0.), ("E80_P20", 80., 20.))
TOTALS = ("renewable_available_MWh", "renewable_used_MWh", "curtailment_MWh",
          "total_load_MWh", "thermal_generation_MWh", "unserved_MWh", "total_cost_CNY")
RATES = ("renewable_utilization_pct", "curtailment_rate_pct")


def source_day(data, day):
    if not 0 <= day < 365 or day != int(day):
        raise ValueError("Invalid source day")
    q = data.iloc[int(day)*24:(int(day)+1)*24].copy().reset_index(drop=True)
    if len(q) != 24:
        raise ValueError("Incomplete source day")
    q.hour = np.arange(24)
    return q


def fixed_days(data, representatives, labels):
    r = representatives
    if len(data) != 8760 or len(r) != 48 or len(labels) != 365:
        raise ValueError("Wrong fixed input dimensions")
    if list(r.cluster) != list(range(48)) or list(labels.day) != list(range(365)):
        raise ValueError("Wrong fixed cluster/day ordering")
    if r.day.duplicated().any() or not np.isfinite(r.day).all() or (r.day % 1 != 0).any():
        raise ValueError("Invalid representative source indices")
    if not np.isfinite(labels.cluster).all() or (labels.cluster % 1 != 0).any():
        raise ValueError("Invalid labels")
    lab = labels.cluster.to_numpy(dtype=int)
    if set(lab) != set(range(48)):
        raise ValueError("Incomplete fixed cluster set")
    counts = np.bincount(lab, minlength=48)
    if not np.array_equal(counts, r.days.to_numpy()):
        raise ValueError("Fixed cluster counts mismatch")
    days = [source_day(data, d) for d in r.day]
    if not np.array_equal(lab[r.day.to_numpy(dtype=int)], np.arange(48)):
        raise ValueError("Representative outside its original cluster")
    dates = (pd.Timestamp("2023-01-01") + pd.to_timedelta(r.day, unit="D")).dt.strftime("%Y-%m-%d")
    if list(r.date_UTC) != list(dates):
        raise ValueError("Fixed date mismatch")
    weights = r.effective_days.to_numpy(dtype=float)
    if not np.isfinite(weights).all() or not np.array_equal(weights, r.repeat_days.to_numpy()):
        raise ValueError("Fixed or repeated weights mismatch")
    residual = max(abs(float(weights.sum())-365.), float(np.max(.5*counts-weights)),
                   float(np.max(weights-2*counts)), 0.)
    if residual > 1e-6:
        raise ValueError("Fixed weight bound/sum residual")
    probabilities = r.effective_probability.to_numpy(dtype=float)
    if not np.isfinite(probabilities).all() or np.max(np.abs(probabilities-weights/365.)) > 1e-6:
        raise ValueError("Fixed probability mismatch")
    return days, weights, residual


def repeat_difference(first, repeated):
    errors = []
    if set(first) != set(repeated):
        raise ValueError("Repeat summary keys differ")
    for key, value in first.items():
        other = repeated[key]
        if isinstance(value, numbers.Real):
            if key == "storage_utilization_pct" and np.isnan(value) and np.isnan(other):
                continue
            if not np.isfinite([value, other]).all():
                raise ValueError("Nonfinite repeat summary: "+key)
            errors.append(abs(float(value)-float(other)))
    difference = max(errors, default=0.)
    if difference >= 1e-6:
        raise ValueError("Independent repeat mismatch")
    return difference


def decision(table):
    expected = {(name, seed) for name, _, _ in SCENARIOS for seed in SEEDS}
    if len(table) != 6 or set(zip(table.capacity_scenario, table.seed)) != expected:
        raise ValueError("Incomplete or duplicate transfer matrix")
    values = table[["worst_error_pp", "max_input_relative_error"]].to_numpy()
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid transfer errors")
    passing = (table.worst_error_pp <= 1.) & (table.max_input_relative_error <= .02)
    return "supported" if passing.all() else "inconclusive", passing
