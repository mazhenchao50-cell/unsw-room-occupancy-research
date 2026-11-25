"""Fixed low-utilization classifier plus separately identified calendar context."""
import warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import revised as R
import improvement_v7 as V7
import calendar_context as C

STRATEGY='fixed_ensemble_calendar_v1'
THRESHOLD=.50


def features(reference,query):
    reference=reference.copy();query=query.copy()
    reference['date']=pd.to_datetime(reference.date);query['date']=pd.to_datetime(query.date)
    x=V7.features(reference,query);records=[]
    for row in query.itertuples():
        past=reference[reference.date.lt(row.date)].sort_values(['date','session_id'])
        course=past[past.course_id.eq(row.course_id)];course_room=course[course.room.eq(row.room)]
        room=past[past.room.eq(row.room)]
        latest=past[past.date.ge(row.date-pd.Timedelta(days=21))]
        room_latest=room[room.date.ge(row.date-pd.Timedelta(days=21))]
        fallback=float(past.occupancy_rate.mean()) if len(past) else .3
        prior_low=float(past.occupancy_rate.lt(.1).mean()) if len(past) else .2
        def mean(part):return float(part.occupancy_rate.mean()) if len(part) else fallback
        def low(part):return float(part.occupancy_rate.lt(.1).mean()) if len(part) else prior_low
        last=mean(course.tail(1));before=mean(course.iloc[-2:-1]) if len(course)>1 else last
        records.append(dict(course_last_rate=last,course_recent_mean3=mean(course.tail(3)),
            course_recent_low3=low(course.tail(3)),course_recent_mean5=mean(course.tail(5)),
            course_recent_low5=low(course.tail(5)),course_trend3=mean(course.tail(3))-mean(course),
            course_last_delta=last-before,course_room_last=mean(course_room.tail(1)),
            course_room_mean3=mean(course_room.tail(3)),course_room_low3=low(course_room.tail(3)),
            room_recent_low=low(room_latest),global_recent_low=low(latest),
            course_history_log_n=np.log1p(len(course)),room_history_log_n=np.log1p(len(room)),
            days_since_course=float((row.date-course.date.max()).days) if len(course) else 90.,
            course_seen=float(bool(len(course))),course_room_seen=float(bool(len(course_room)))))
    return pd.concat([x,pd.DataFrame(records,index=query.index)],axis=1)


def fit_bundle(reference):
    if reference.empty or not reference.session_id.is_unique:raise ValueError('Unique nonempty reference required')
    x=features(reference,reference);median=x.median().fillna(0);x=x.fillna(median)
    if not np.isfinite(x.to_numpy()).all():raise ValueError('Non-finite fitting features')
    y=reference.occupancy_rate.lt(.1)
    if y.nunique()!=2:raise ValueError('Both classes required for the fixed classifier')
    scaler=StandardScaler().fit(x)
    logistic=LogisticRegression(C=1.0,class_weight=None,max_iter=2000,random_state=42)
    trees=lgb.LGBMClassifier(n_estimators=150,num_leaves=7,min_child_samples=30,
        learning_rate=.05,random_state=42,n_jobs=2,verbosity=-1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');logistic.fit(scaler.transform(x),y);trees.fit(x,y)
    if caught:raise ValueError('Fitting warning requires review: '+'; '.join(str(w.message) for w in caught))
    return dict(strategy=STRATEGY,threshold=THRESHOLD,logistic=logistic,trees=trees,scaler=scaler,
        median=median,features=list(x.columns),reference=reference.copy(),cutoff=reference.date.max(),
        fitted_ids=set(reference.session_id))


def predict_bundle(bundle,query):
    if bundle.get('strategy')!=STRATEGY or bundle['threshold']!=THRESHOLD:
        raise ValueError('Unknown fixed classifier policy')
    dates=pd.to_datetime(query.date,errors='coerce')
    if dates.isna().any() or dates.le(pd.Timestamp(bundle['cutoff'])).any():
        raise ValueError('Query must follow all fitting observations')
    if not query.session_id.is_unique or set(query.session_id)&bundle['fitted_ids']:
        raise ValueError('Duplicate or fitted query sessions')
    x=features(bundle['reference'],query).fillna(bundle['median'])
    if list(x.columns)!=bundle['features'] or not np.isfinite(x.to_numpy()).all():raise ValueError('Invalid classifier features')
    probability=(bundle['logistic'].predict_proba(bundle['scaler'].transform(x))[:,1]+bundle['trees'].predict_proba(x)[:,1])/2
    model_alert=probability>=THRESHOLD;calendar_review=C.review_flag(query)
    return dict(probability=probability,model_alert=model_alert,calendar_review=calendar_review,
                alert=model_alert|calendar_review)
