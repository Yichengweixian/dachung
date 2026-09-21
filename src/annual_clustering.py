"""Normalized features and physical mean typical days are kept distinct."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from threadpoolctl import threadpool_limits
from .data_loader import validate_input_data

def cluster_days(data,n,seed,n_init=10):
    validate_input_data(data,8760)
    curves=data[['load','wind','solar']].to_numpy().reshape(365,24,3)
    peaks=curves.max(axis=1,keepdims=True)
    features=(curves/np.where(peaks==0,1,peaks)).transpose(0,2,1).reshape(365,72)
    with threadpool_limits(limits=1):
        model=KMeans(n_clusters=n,init='k-means++',n_init=n_init,random_state=seed).fit(features)
        repeated=KMeans(n_clusters=n,init='k-means++',n_init=n_init,random_state=seed).fit(features)
    if not np.array_equal(model.labels_,repeated.labels_):raise ValueError('Clustering labels not repeatable')
    days=[];counts=[]
    for k in range(n):
        members=curves[model.labels_==k]
        if not len(members):raise ValueError('Empty cluster')
        day=pd.DataFrame(members.mean(axis=0),columns=['load','wind','solar']);day.insert(0,'hour',np.arange(24))
        validate_input_data(day,24);days.append(day);counts.append(len(members))
    if sum(counts)!=365:raise ValueError('Wrong weights')
    return days,np.asarray(counts),model.labels_,dict(inertia=float(model.inertia_),silhouette=float(silhouette_score(features,model.labels_)))

def annual_metrics(rows,weights):
    q=pd.DataFrame(rows);weights=np.asarray(weights,dtype=float)
    if len(q)!=len(weights) or (weights<0).any() or not np.isfinite(weights).all():raise ValueError('Bad weights')
    cols=['renewable_available_MWh','renewable_used_MWh','curtailment_MWh','total_load_MWh','thermal_generation_MWh','unserved_MWh','total_cost_CNY']
    totals={c:float(np.dot(q[c],weights)) for c in cols}
    if totals['renewable_available_MWh']<=0:raise ValueError('Zero annual renewable denominator')
    totals['renewable_utilization_pct']=100*totals['renewable_used_MWh']/totals['renewable_available_MWh']
    totals['curtailment_rate_pct']=100*totals['curtailment_MWh']/totals['renewable_available_MWh']
    return totals
