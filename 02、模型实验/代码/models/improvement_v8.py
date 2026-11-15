"""Nested spatial validation of history-free cold-start estimators.

All outer rooms were examined in earlier project work: retrospective diagnostic,
not a fresh blind test. No outer-room labels enter preprocessing or selection.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import lightgbm as lgb
import revised as R

OUT=R.ROOT/'02、模型实验/生成产物/improvement_v8'
GRID=[('LightGBM',n) for n in (80,200,400)]+[('Ridge',a) for a in (.1,1.,10.)]


def features(frame):
    """Only pre-class fields; neither course/room identity nor target history."""
    x=R.raw_features(frame.iloc[:0],frame,use_history=False)
    if not (np.isfinite(frame.seats)&frame.seats.gt(0)).all():
        raise ValueError('Positive finite capacity required')
    enrollment=frame.enrollments.where(frame.enrollments.ge(0))
    x['enrollment_pressure']=enrollment/frame.seats
    x['log_seats']=np.log(frame.seats)
    x['enrollment_missing']=enrollment.isna().astype(float)
    return x


def room_weights(frame):
    """Each training room contributes the same total squared-error weight."""
    count=frame.groupby('room').session_id.transform('count').to_numpy()
    return len(frame)/(frame.room.nunique()*count)


def fit_predict(train,query,candidate):
    if set(train.session_id)&set(query.session_id):
        raise ValueError('Training and query session IDs overlap')
    a,b=features(train),features(query)
    med=a.median().fillna(0);a=a.fillna(med);b=b.fillna(med)
    weights=room_weights(train);name,param=candidate
    if name=='LightGBM':
        model=lgb.LGBMRegressor(n_estimators=int(param),learning_rate=.05,num_leaves=15,
            min_child_samples=20,random_state=42,n_jobs=2,verbosity=-1)
    elif name=='Ridge':
        scaler=StandardScaler().fit(a,sample_weight=weights)
        a,b=scaler.transform(a),scaler.transform(b)
        model=Ridge(alpha=param)
    else:raise ValueError(name)
    model.fit(a,train.occupancy_rate,sample_weight=weights)
    return np.maximum(0,model.predict(b))


def select(available):
    """Inner room folds use only the outer training pool, including imputation."""
    rooms=sorted(available.room.unique())
    if len(rooms)<3:raise ValueError('At least three training rooms required')
    trials=[]
    for candidate in GRID:
        per_room={}
        for room in rooms:
            train=available[available.room.ne(room)];valid=available[available.room.eq(room)]
            p=fit_predict(train,valid,candidate)
            per_room[room]=R.metrics(valid.occupancy_rate,p)['rmse']
        trials.append(dict(candidate=list(candidate),inner_macro_rmse=float(np.mean(list(per_room.values()))),inner_rooms=per_room))
    best=min(range(len(trials)),key=lambda i:(trials[i]['inner_macro_rmse'],i))
    return GRID[best],trials


def predict_held_room(data,room):
    available=data[data.room.ne(room)];query=data[data.room.eq(room)]
    candidate,trials=select(available)
    p=fit_predict(available,query,candidate)
    return p,dict(selected=list(candidate),trials=trials,reference_rooms=sorted(available.room.unique()),
        unseen_course_fraction=float((~query.course_id.isin(available.course_id)).mean()))


def conditional_interval(frame):
    """Resample courses within each held room, keeping fitted predictions fixed."""
    rng=np.random.default_rng(42);room_samples=[]
    for _,g in frame.groupby('room'):
        groups=g.assign(sse=(g.prediction-g.occupancy_rate)**2).groupby('course_id').sse.agg(['sum','count'])
        indices=rng.integers(0,len(groups),size=(1000,len(groups)))
        sums=groups['sum'].to_numpy()[indices].sum(axis=1)
        counts=groups['count'].to_numpy()[indices].sum(axis=1)
        room_samples.append(np.sqrt(sums/counts))
    values=np.mean(room_samples,axis=0)
    return dict(macro_rmse_95=np.quantile(values,[.025,.975]).tolist(),replicates=1000,
        note='Conditional course-cluster bootstrap within the same nine rooms, fitted predictions fixed; ignores selection uncertainty and new-room sampling. Not a generalization guarantee.')


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=dict(experiment='v8',status='Retrospective nested spatial diagnostic',
        hypothesis='All courses belong to a single room: target-room holdout removes all course history. Temporal within-room selection may favor unavailable history.',
        candidates=[list(c) for c in GRID],features='Original pre-class features plus enrollment/seats, log seats, missing enrollment. No room ID, course ID or label history.',
        weighting='Equal total training weight per room',selection='Inner leave-one-room-out macro RMSE; exact ties use fixed grid order',
        preprocessing='Medians and standardization fitted separately inside each training fold',
        evaluation='Nine outer held rooms, all sessions retained; matched random holdout20% seed42 with same nested selector',
        acceptance='Original macro RMSE<=.18 OR gap versus own random comparator<=.30; no automatic deployment',
        uncertainty='1000 course-cluster resamples within each room after fitting; conditional, not selection or new-room uncertainty',
        limitations=['All nine rooms previously examined','Spatial training contains other-room later dates','No prospective time or unseen-campus claim','No correction based on outer test residuals'])
    R.dump(OUT/'protocol.json',protocol)
    d=R.load();frames=[];rooms={}
    for room in sorted(d.room.unique()):
        p,selection=predict_held_room(d,room);query=d[d.room.eq(room)]
        met=R.metrics(query.occupancy_rate,p)
        rooms[room]=dict(metrics=met,**selection)
        frames.append(R.prediction_frame(query,p))
        print('room',room,'RMSE',round(met['rmse'],4),'selected',selection['selected'],flush=True)
    f=pd.concat(frames).sort_values('session_id');f.to_csv(OUT/'loro_predictions.csv',index=False)
    it,ie=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    candidate,trials=select(d.iloc[it]);p=fit_predict(d.iloc[it],d.iloc[ie],candidate)
    random=R.metrics(d.iloc[ie].occupancy_rate,p)
    R.prediction_frame(d.iloc[ie],p).to_csv(OUT/'random_predictions.csv',index=False)
    macro=float(np.mean([v['metrics']['rmse'] for v in rooms.values()]));gap=macro/random['rmse']-1
    report=dict(protocol=protocol,rooms=rooms,macro_rmse=macro,micro=R.metrics(f.occupancy_rate,f.prediction),
        conditional_course_bootstrap=conditional_interval(f),
        random=dict(metrics=random,selected=list(candidate),trials=trials),gap_vs_random=gap,
        original_spatial_numeric_gate=bool(macro<=.18 or gap<=.3),default_model_changed=False,
        diagnostic=dict(courses=int(d.course_id.nunique()),courses_spanning_rooms=int((d.groupby('course_id').room.nunique()>1).sum()),
            target_room_unseen_course_fraction=1.0 if all(x['unseen_course_fraction']==1 for x in rooms.values()) else None))
    report['sha256']={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'protocol.json']}
    R.dump(OUT/'report.json',report)
    print('SUMMARY',macro,gap,report['original_spatial_numeric_gate'],flush=True)
    return report


if __name__=='__main__':run()
