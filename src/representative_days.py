"""Amplitude-preserving clustering and actual-day representatives for U11R03."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_limits
from .data_loader import validate_input_data


def nearest_member(features, members, center):
    distances = np.linalg.norm(features[members] - center, axis=1)
    tied = members[distances <= distances.min() + 1e-12]
    selected = int(tied.min())
    return selected, float(np.linalg.norm(features[selected] - center))


def cluster_real_days(data, n, seed):
    validate_input_data(data, 8760)
    curves = data[['load', 'wind', 'solar']].to_numpy().reshape(365, 24, 3)
    features = curves.transpose(0, 2, 1).reshape(365, 72) / 100.
    with threadpool_limits(limits=1):
        model = KMeans(n_clusters=n, init='k-means++', n_init=10, random_state=seed).fit(features)
        repeat = KMeans(n_clusters=n, init='k-means++', n_init=10, random_state=seed).fit(features)
    if not np.array_equal(model.labels_, repeat.labels_):
        raise ValueError('Nonrepeatable labels')
    days, records = [], []
    for k in range(n):
        members = np.flatnonzero(model.labels_ == k)
        if not len(members):
            raise ValueError('Empty cluster')
        selected, distance = nearest_member(features, members, model.cluster_centers_[k])
        day = pd.DataFrame(curves[selected], columns=['load', 'wind', 'solar'])
        day.insert(0, 'hour', np.arange(24))
        days.append(day)
        records.append(dict(cluster=k, day=selected,
                            date_UTC=str((pd.Timestamp('2023-01-01') + pd.Timedelta(days=selected)).date()),
                            days=len(members), weight=len(members)/365, distance=distance))
    representatives = pd.DataFrame(records)
    if representatives.days.sum() != 365 or abs(representatives.weight.sum()-1) > 1e-12:
        raise ValueError('Invalid weights')
    return days, representatives, model.labels_


def input_energy_errors(data, days, weights):
    weights = np.asarray(weights, dtype=float)
    if len(days) != len(weights) or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError('Invalid weights')
    errors = {}
    for col in ['load', 'wind', 'solar']:
        actual = float(data[col].sum())
        estimated = float(np.dot([day[col].sum() for day in days], weights))
        errors[col+'_input_MWh'] = estimated
        errors[col+'_relative_error'] = abs(estimated-actual)/actual if actual else (0. if estimated == 0 else float('inf'))
    errors['max_input_relative_error'] = max(errors[c+'_relative_error'] for c in ['load', 'wind', 'solar'])
    return errors


def passing_sizes(comparison):
    passed = []
    for n in [12, 24, 48]:
        group = comparison[comparison.N == n]
        if len(group) != 3 or set(group.seed) != {42, 7, 2026}:
            raise ValueError('Incomplete experiment matrix')
        if ((group.worst_error_pp <= 1.) & (group.max_input_relative_error <= .02)).all():
            passed.append(n)
    return passed
