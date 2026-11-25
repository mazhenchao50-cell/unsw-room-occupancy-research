"""Complementary day-context vote; ordinary-day history excludes holiday shocks."""
import warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import stable_low as L
import calendar_context as C

STRATEGY='calendar_context_majority_v1'
THRESHOLD=.5

def features(reference,query):
    original_index=query.index;query=query.reset_index(drop=True)
    holiday=C.review_flag(query);parts=[];regular=reference.loc[~C.review_flag(reference)]
    for flag in (False,True):
        part=query.iloc[np.flatnonzero(holiday==flag)]
        if not part.empty:parts.append(L.features(reference if flag else regular,part))
    if not parts:raise ValueError('Nonempty context query required')
    x=pd.concat(parts).loc[query.index];x['public_holiday']=holiday.astype(float);x.index=original_index
    return x

def fit(reference):
    if reference.empty or not reference.session_id.is_unique:raise ValueError('Unique training observations required')
    x=features(reference,reference);med=x.median().fillna(0);x=x.fillna(med);y=reference.occupancy_rate.lt(.1)
    if not np.isfinite(x.to_numpy()).all() or y.nunique()!=2:raise ValueError('Invalid context training data')
    scaler=StandardScaler().fit(x)
    logistic=LogisticRegression(C=1,max_iter=3000,random_state=42)
    trees=lgb.LGBMClassifier(n_estimators=150,num_leaves=7,min_child_samples=30,learning_rate=.05,random_state=42,n_jobs=2,verbosity=-1)
    forest=RandomForestClassifier(n_estimators=200,min_samples_leaf=10,class_weight={0:1,1:2},random_state=42,n_jobs=2)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');logistic.fit(scaler.transform(x),y);trees.fit(x,y);forest.fit(x,y)
    if caught:raise ValueError('Review training warnings: '+';'.join(str(w.message) for w in caught))
    return dict(strategy=STRATEGY,threshold=THRESHOLD,logistic=logistic,trees=trees,forest=forest,scaler=scaler,median=med,
        features=list(x.columns),reference=reference.copy(),fitted_ids=set(reference.session_id),cutoff=reference.date.max())

def predict_components(bundle,query):
    if bundle.get('strategy')!=STRATEGY or bundle['threshold']!=THRESHOLD:raise ValueError('Unknown context strategy')
    query=query.copy();query['date']=pd.to_datetime(query.date,errors='coerce')
    if query.empty or query.date.isna().any() or query.date.min()<=bundle['cutoff']:raise ValueError('Future-only context inference')
    if not query.session_id.is_unique or set(query.session_id)&bundle['fitted_ids']:raise ValueError('Duplicate or fitted context query')
    x=features(bundle['reference'],query).fillna(bundle['median'])
    if list(x)!=bundle['features'] or not np.isfinite(x.to_numpy()).all():raise ValueError('Context feature contract')
    return dict(logistic=bundle['logistic'].predict_proba(bundle['scaler'].transform(x))[:,1],
        trees=bundle['trees'].predict_proba(x)[:,1],forest=bundle['forest'].predict_proba(x)[:,1])

def predict(bundle,query):
    components=predict_components(bundle,query)
    return np.median(np.stack(list(components.values())),axis=0)
