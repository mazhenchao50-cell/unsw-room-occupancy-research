"""X09: retrospective forward-time AND held-room benchmark.

The held room is absent from training, selection and alert calibration. Query
capacity is known before class; target labels and occupancy history are not.
This is a diagnostic research candidate, never an automatic deployment change.
"""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.metrics import average_precision_score, precision_recall_curve
import lightgbm as lgb

import revised as R
import improvement_v8 as V8

OUT=R.ROOT/'02、模型实验/生成产物/forward_cold_benchmark'
GRID={'Ridge':[1.,10.], 'RF':[2,12], 'SVR':[1.,10.],
      'LightGBM':[80,200], 'CapacityRidge':[1.,10.]}
BASELINES=['Ridge','RF','SVR','LightGBM']
TEST_WEEKS=[8,10,11,12]
THRESHOLDS=[.025,.05,.075,.1,.125,.15,.175,.2,.25,.3]


def protocol():
    return dict(version='X09_v1',status='Retrospective, all source rooms and weeks previously inspected',
        hypothesis='Capacity-similarity weighting may improve advance prediction for a room with zero occupancy history; superiority is not assumed.',
        label='Session sensor-derived peak attendees / seats; low utilization < .1; zero and overcapacity retained',
        outer='Four weeks 8,10,11,12 times nine held rooms. Same test sessions for every method.',
        time='For test week t, v is the second preceding available week and c the preceding week. Inner training strictly before v, validation at v; final source fit through v; source-only alert calibration at c.',
        information='Pre-class fields from v8; no room/course ID or target-room observation/label history. Target static capacity is allowed and must be constant per room.',
        selection='Two settings per family. Each inner validation room is excluded from its fit. Minimize macro RMSE over source validation rooms; fixed grid order breaks ties.',
        selected_baseline='Choose among the eight Ridge/RF/SVR/LightGBM candidates using inner scores only, independently in each outer fold.',
        candidates=GRID,weighting='Equal total source-room weight. CapacityRidge multiplies by exp(-abs(log(source seats / query-room seats))); fixed exponent 1, no outer-label tuning.',
        reference='StaticRidge1 is the fixed Ridge alpha=1 configuration used in existing v8 results, refit under X09 time cutoffs; not a reuse of v8 scores.',
        scaling='Training-only medians. Weighted training-only StandardScaler for Ridge/SVR. Predictions clipped only below zero.',
        alert_calibration='Leave each source calibration room out of training through v. Choose threshold with precision>=.80 AND recall>=.50 and >=5 alerts, maximize recall then precision; no feasible threshold -> no alerts, visibly marked.',
        thresholds=THRESHOLDS,
        review_budget='Predeclare ceil(20% of sessions) per held-room/week; rank smallest predicted occupancy, stable session-ID tie break. Ranking uses predictions, not query labels.',
        primary='Macro RMSE across nine held rooms pooled over four weeks; compare CapacityRidge to the inner-selected strong baseline. All family scores, weeks and rooms retained.',
        uncertainty='1000 paired fixed-prediction room/course resamples; preserves courses across weeks; not refitting/selection uncertainty or unseen-campus guarantee.',
        limits=['No new blind or independent dataset','Sensor labels are not field occupancy truth',
                'F1/precision screening is not room release permission','Capacity weighting has prior methodological precedents; no novelty claim',
                'Source-only calibration can shift in an unseen room','Original acceptance criteria and deployed models remain unchanged'])


def checked_data(data):
    d=data.copy()
    if d.empty or not d.session_id.is_unique:raise ValueError('Nonempty unique sessions required')
    d['date']=pd.to_datetime(d.date,errors='coerce')
    if d.date.isna().any() or not np.isfinite(d.occupancy_rate).all() or d.occupancy_rate.lt(0).any():raise ValueError('Invalid date or target')
    V8.features(d)
    if d.groupby('room').seats.nunique().ne(1).any():raise ValueError('Each room needs one static capacity')
    return d


def split_outer(data,room,test_week):
    """Filter the outer room BEFORE constructing any training/selection pool."""
    weeks=sorted(data.week.unique());index=weeks.index(test_week)
    if index<3:raise ValueError('Not enough preceding weeks')
    validation,calibration=weeks[index-2:index]
    source=data[data.room.ne(room)]
    train=source[source.week.lt(validation)]
    valid=source[source.week.eq(validation)]
    final=source[source.week.le(validation)]
    cal=source[source.week.eq(calibration)]
    query=data[data.room.eq(room)&data.week.eq(test_week)]
    pools=[train,valid,cal,query]
    if any(x.empty for x in pools):raise ValueError('Empty forward fold')
    if not train.date.max()<valid.date.min() or not final.date.max()<cal.date.min() or not cal.date.max()<query.date.min():
        raise ValueError('Dates must be strictly ordered')
    if room in set(final.room)|set(cal.room):raise ValueError('Held room leaked')
    return train,valid,final,cal,query,int(validation),int(calibration)


def fit_predict(train,query,candidate):
    if train.empty or query.empty:raise ValueError('Empty fitting/query pool')
    if set(train.session_id)&set(query.session_id):raise ValueError('Overlapping sessions')
    if train.date.max()>=query.date.min():raise ValueError('Future or same-day training information')
    if set(train.room)&set(query.room):raise ValueError('Query room must be unseen')
    if query.room.nunique()!=1 or query.seats.nunique()!=1:raise ValueError('One query room with constant capacity required')
    a,b=V8.features(train),V8.features(query)
    median=a.median().fillna(0);a=a.fillna(median);b=b.fillna(median)
    weights=V8.room_weights(train)
    name,setting=candidate
    if name=='CapacityRidge':
        capacity=float(query.seats.iloc[0])
        weights*=np.exp(-np.abs(np.log(train.seats.to_numpy()/capacity)))
        weights*=len(weights)/weights.sum()
    if name in ('Ridge','CapacityRidge','SVR'):
        scaler=StandardScaler().fit(a,sample_weight=weights)
        a,b=scaler.transform(a),scaler.transform(b)
    if name in ('Ridge','CapacityRidge'):model=Ridge(alpha=setting)
    elif name=='SVR':model=SVR(C=setting,epsilon=.05)
    elif name=='RF':model=RandomForestRegressor(n_estimators=120,min_samples_leaf=int(setting),random_state=42,n_jobs=1)
    elif name=='LightGBM':model=lgb.LGBMRegressor(n_estimators=int(setting),learning_rate=.05,num_leaves=15,
        min_child_samples=20,random_state=42,n_jobs=2,verbosity=-1)
    else:raise ValueError(name)
    model.fit(a,train.occupancy_rate,sample_weight=weights)
    prediction=np.maximum(0,model.predict(b))
    if not np.isfinite(prediction).all():raise ValueError('Nonfinite prediction')
    return prediction


def select(train,valid):
    if set(train.session_id)&set(valid.session_id) or train.date.max()>=valid.date.min():raise ValueError('Invalid inner chronology')
    rooms=sorted(valid.room.unique())
    if len(rooms)<3:raise ValueError('At least three source validation rooms')
    trials=[];chosen={}
    for name,settings in GRID.items():
        family=[]
        for setting in settings:
            errors={}
            for room in rooms:
                reference=train[train.room.ne(room)];query=valid[valid.room.eq(room)]
                prediction=fit_predict(reference,query,(name,setting))
                errors[room]=float(np.sqrt(np.mean((prediction-query.occupancy_rate.to_numpy())**2)))
            row=dict(candidate=[name,setting],inner_macro_rmse=float(np.mean(list(errors.values()))),inner_rooms=errors)
            trials.append(row);family.append(row)
        chosen[name]=min(family,key=lambda x:x['inner_macro_rmse'])['candidate']
    eligible=[x for x in trials if x['candidate'][0] in BASELINES]
    chosen['SelectedBaseline']=min(eligible,key=lambda x:x['inner_macro_rmse'])['candidate']
    chosen['StaticRidge1']=['Ridge',1.]
    return chosen,trials


def calibrated_policy(y,prediction):
    prediction=np.asarray(prediction,dtype=float)
    if len(y)!=len(prediction) or not len(prediction) or not np.isfinite(prediction).all():raise ValueError('Invalid calibration inputs')
    trials=[]
    for threshold in THRESHOLDS:
        met=R.binary_metrics(y,np.asarray(prediction)<threshold)
        trials.append(dict(threshold=threshold,**met))
    eligible=[x for x in trials if x['predicted_positive']>=5 and x['precision']>=.8 and x['recall']>=.5]
    best=max(eligible,key=lambda x:(x['recall'],x['precision'],-x['threshold'])) if eligible else None
    return dict(feasible=best is not None,threshold=best['threshold'] if best else None,trials=trials,
                note='Calibration eligibility is empirical, not a future precision guarantee; infeasible means no alerts.')


def budget_alerts(prediction,ids,fraction=.2):
    if not 0<fraction<=1:raise ValueError('Invalid review fraction')
    prediction=np.asarray(prediction,dtype=float)
    if len(prediction)!=len(ids) or not np.isfinite(prediction).all():raise ValueError('Invalid ranking input')
    flags=np.zeros(len(prediction),bool)
    if len(prediction):
        order=np.lexsort((np.asarray(ids,dtype=str),prediction))
        flags[order[:math.ceil(fraction*len(prediction))]]=True
    return flags


def evaluate_outer(data,room,test_week):
    train,valid,final,cal,query,vw,cw=split_outer(data,room,test_week)
    selected,trials=select(train,valid);cal_cache={};query_cache={};frames=[];policies={}
    for name,candidate in selected.items():
        key=tuple(candidate)
        if key not in query_cache:query_cache[key]=fit_predict(final,query,candidate)
        prediction=query_cache[key]
        if key not in cal_cache:
            rows=[]
            for calibration_room in sorted(cal.room.unique()):
                reference=final[final.room.ne(calibration_room)]
                target=cal[cal.room.eq(calibration_room)]
                p=fit_predict(reference,target,candidate)
                rows.append(pd.DataFrame(dict(session_id=target.session_id,truth=target.occupancy_rate,prediction=p)))
            calibration=pd.concat(rows)
            cal_cache[key]=calibrated_policy(calibration.truth.lt(.1),calibration.prediction)
        policy=cal_cache[key];policies[name]=policy
        frame=R.prediction_frame(query,prediction,model=name,validation_week=vw,calibration_week=cw,
            fitted_through=str(final.date.max().date()),calibrated_through=str(cal.date.max().date()),
            fixed_alert=prediction<.1,calibrated_alert=(prediction<policy['threshold'] if policy['feasible'] else np.zeros(len(query),bool)),
            calibration_feasible=policy['feasible'],budget_alert=budget_alerts(prediction,query.session_id))
        frames.append(frame)
    details=dict(held_room=room,test_week=int(test_week),validation_week=vw,calibration_week=cw,
        source_rooms=sorted(final.room.unique()),train_n=len(train),fit_n=len(final),calibration_n=len(cal),query_n=len(query),
        training_last_date=str(final.date.max().date()),calibration_last_date=str(cal.date.max().date()),
        query_first_date=str(query.date.min().date()),selected=selected,trials=trials,policies=policies)
    return pd.concat(frames,ignore_index=True),details


def score_frame(frame):
    per_room={room:R.metrics(g.occupancy_rate,g.prediction) for room,g in frame.groupby('room')}
    per_week={str(int(week)):dict(macro_rmse=float(np.mean([R.metrics(x.occupancy_rate,x.prediction)['rmse'] for _,x in g.groupby('room')])),
        metrics=R.metrics(g.occupancy_rate,g.prediction)) for week,g in frame.groupby('week')}
    screening={column:dict(**R.binary_metrics(frame.occupancy_rate.lt(.1),frame[column]),
        review_fraction=float(frame[column].mean())) for column in ['fixed_alert','calibrated_alert','budget_alert']}
    return dict(n=len(frame),pooled=R.metrics(frame.occupancy_rate,frame.prediction),per_room=per_room,per_week=per_week,
        macro_room_rmse=float(np.mean([x['rmse'] for x in per_room.values()])),screening=screening,
        feasible_calibration_folds=int(frame[['room','week','calibration_feasible']].drop_duplicates().calibration_feasible.sum()),
        average_precision=float(average_precision_score(frame.occupancy_rate.lt(.1),-frame.prediction)))


def paired_interval(candidate,baseline,replicates=1000):
    a=candidate[['session_id','room','course_id','occupancy_rate','prediction']]
    b=baseline[['session_id','occupancy_rate','prediction']]
    if not a.session_id.is_unique or not b.session_id.is_unique or set(a.session_id)!=set(b.session_id):raise ValueError('Unpaired predictions')
    merged=a.merge(b,on='session_id',validate='one_to_one',suffixes=('_a','_b'))
    if not np.array_equal(merged.occupancy_rate_a,merged.occupancy_rate_b):raise ValueError('Conflicting labels')
    merged['a']=(merged.prediction_a-merged.occupancy_rate_a)**2
    merged['b']=(merged.prediction_b-merged.occupancy_rate_b)**2
    rng=np.random.default_rng(42);curves=[]
    for _,g in merged.groupby('room'):
        grouped=g.groupby('course_id').agg(a=('a','sum'),b=('b','sum'),n=('a','size'))
        sample=rng.integers(0,len(grouped),size=(replicates,len(grouped)))
        counts=grouped.n.to_numpy()[sample].sum(axis=1)
        curves.append(np.sqrt(grouped.a.to_numpy()[sample].sum(axis=1)/counts)-np.sqrt(grouped.b.to_numpy()[sample].sum(axis=1)/counts))
    matrix=np.array(curves).T
    room_indices=rng.integers(0,matrix.shape[1],size=matrix.shape)
    delta=np.take_along_axis(matrix,room_indices,axis=1).mean(axis=1)
    return dict(candidate_minus_baseline_macro_rmse_95=np.quantile(delta,[.025,.975]).tolist(),replicates=replicates,
        note='Paired sensitivity resamples observed rooms and courses, predictions fixed; ignores shared-training dependence, refitting, selection and new-campus uncertainty.')


def run(out=OUT):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    frozen=protocol();R.dump(out/'protocol.json',frozen)
    data=checked_data(R.load());frames=[];folds=[]
    for week in TEST_WEEKS:
        for room in sorted(data.room.unique()):
            frame,details=evaluate_outer(data,room,week)
            frames.append(frame);folds.append(details)
            print('X09',week,room,'capacity',round(R.metrics(frame[frame.model.eq('CapacityRidge')].occupancy_rate,
                frame[frame.model.eq('CapacityRidge')].prediction)['rmse'],4),'baseline',details['selected']['SelectedBaseline'],flush=True)
    predictions=pd.concat(frames,ignore_index=True).sort_values(['model','session_id'])
    predictions.to_csv(out/'predictions.csv',index=False)
    models={name:score_frame(g) for name,g in predictions.groupby('model',sort=False)}
    curves={}
    for name,g in predictions.groupby('model',sort=False):
        precision,recall,threshold=precision_recall_curve(g.occupancy_rate.lt(.1),-g.prediction)
        curves[name]=dict(precision=precision.tolist(),recall=recall.tolist(),negative_prediction_threshold=threshold.tolist())
    R.dump(out/'pr_curves.json',curves)
    candidate=predictions[predictions.model.eq('CapacityRidge')];baseline=predictions[predictions.model.eq('SelectedBaseline')]
    reference=models['SelectedBaseline']['macro_room_rmse'];value=models['CapacityRidge']['macro_room_rmse']
    wins=sum(models['CapacityRidge']['per_room'][r]['rmse']<models['SelectedBaseline']['per_room'][r]['rmse'] for r in sorted(data.room.unique()))
    drop_week={str(w):{name:score_frame(g[g.week.ne(w)])['macro_room_rmse'] for name,g in predictions.groupby('model',sort=False)} for w in TEST_WEEKS}
    report=dict(protocol=frozen,folds=folds,models=models,common_sessions=int(candidate.session_id.nunique()),
        outer_folds=len(folds),primary_comparison=dict(candidate='CapacityRidge',baseline='SelectedBaseline',
            candidate_macro_rmse=value,baseline_macro_rmse=reference,relative_improvement=1-value/reference,room_wins=wins,
            conditional_paired_interval=paired_interval(candidate,baseline)),drop_one_week=drop_week,
        default_model_changed=False,original_acceptance_replaced=False,
        adoption='Diagnostic only. Do not adopt from one aggregate score. Compare paired uncertainty, every room/week, screening support and calibration failures. No novelty claim.')
    report['sha256']={p.relative_to(R.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),Path(R.__file__),Path(V8.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',out/'protocol.json',out/'predictions.csv',out/'pr_curves.json']}
    R.dump(out/'report.json',report)
    print('X09 SUMMARY',json.dumps(report['primary_comparison']),flush=True)
    return report


if __name__=='__main__':run()
