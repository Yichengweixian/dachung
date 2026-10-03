"""U11R12 input-only member selection; original cluster labels stay fixed."""
import numpy as np
import pandas as pd

from .data_loader import validate_input_data
from .fixed_weights_capacity_transfer import SEEDS, source_day

TIE = 1e-12


def member_index(proxies, features, members):
    values = proxies[members]
    target = float(values.mean())
    distances = np.abs(values-target)
    eligible = members[distances <= distances.min()+TIE]
    shape = np.linalg.norm(features[eligible]-features[members].mean(axis=0), axis=1)
    tied = eligible[shape <= shape.min()+TIE]
    chosen = int(tied.min())
    return chosen, target, float(abs(proxies[chosen]-target)), len(eligible), len(tied)


def select_days(data, labels, original, thermal_max):
    validate_input_data(data, 8760)
    if not np.isfinite(thermal_max) or thermal_max <= 0:
        raise ValueError("Invalid thermal ceiling")
    if len(labels) != 365 or list(labels.day) != list(range(365)) or len(original) != 48 or list(original.cluster) != list(range(48)):
        raise ValueError("Invalid cluster/day dimensions/order")
    raw = labels.cluster.to_numpy(dtype=float)
    if not np.isfinite(raw).all() or (raw % 1 != 0).any() or set(raw) != set(range(48)):
        raise ValueError("Invalid/incomplete cluster membership")
    lab = raw.astype(int)
    counts = np.bincount(lab, minlength=48)
    if not np.array_equal(counts, original.days.to_numpy()):
        raise ValueError("Original cluster counts mismatch")
    curves = data[["load", "wind", "solar"]].to_numpy().reshape(365, 24, 3)
    proxy = np.maximum(curves[:, :, 0]-curves[:, :, 1]-curves[:, :, 2]-thermal_max, 0.).sum(axis=1)
    features = curves.transpose(0, 2, 1).reshape(365, 72)/100.
    if not np.isfinite(proxy).all() or not np.isfinite(features).all():
        raise ValueError("Nonfinite selection feature")
    rows, days = [], []
    for k in range(48):
        members = np.flatnonzero(lab == k)
        chosen, target, difference, ties, final_ties = member_index(proxy, features, members)
        day = source_day(data, chosen)
        validate_input_data(day, 24)
        days.append(day)
        rows.append(dict(cluster=k, day=chosen,
                         date_UTC=(pd.Timestamp("2023-01-01")+pd.Timedelta(days=chosen)).strftime("%Y-%m-%d"),
                         days=int(counts[k]), weight=counts[k]/365., proxy_MWh=proxy[chosen],
                         cluster_proxy_mean_MWh=target, proxy_distance_MWh=difference,
                         proxy_tie_count=ties, final_tie_count=final_ties,
                         original_day=int(original.day.iloc[k]), changed=chosen != int(original.day.iloc[k])))
    return days, pd.DataFrame(rows), pd.DataFrame(dict(day=np.arange(365), cluster=lab, proxy_MWh=proxy))


def decision(table):
    if len(table) != 3 or set(table.seed) != set(SEEDS) or not (table.N == 48).all():
        raise ValueError("Incomplete/duplicate three-seed N48 matrix")
    keys = ["worst_error_pp", "max_input_relative_error", "cost_absolute_improvement_CNY", "unserved_absolute_improvement_MWh"]
    values = table[keys].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, :2] < 0).any():
        raise ValueError("Invalid hypothesis metrics")
    passed = (values[:, 0] <= 1.) & (values[:, 1] <= .02)
    improvements = values[:, 2:]
    verdict = "refuted" if (improvements < -1e-6).any() else "supported" if passed.all() and (improvements > 1e-6).all() else "inconclusive"
    return verdict, passed.tolist()
