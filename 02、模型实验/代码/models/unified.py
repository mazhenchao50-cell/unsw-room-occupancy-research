"""Executable routed research model with a frozen, label-independent policy.

Known room: revised LightGBM + v7 low-utilization classifier.
Unseen room: v8 nested-selected static model, low-use rule prediction < .1.
The historical spatial diagnostic is distinct from forward-time inference.
"""
from pathlib import Path
import sys
import hashlib
import json
import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
sys.path.insert(0,str(Path(__file__).resolve().parent))
import revised as R
import improvement_v7 as V7
import improvement_v8 as V8
import improvement_v9 as V9
import improvement_v10 as V10

OUT=R.ROOT/'02、模型实验/生成产物/unified'


def load_verified(root=R.ROOT):
    root=Path(root);out=root/'02、模型实验/生成产物/unified'
    report=json.loads((out/'report.json').read_text(encoding='utf-8'))
    for name,digest in report['sha256'].items():
        path=root/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Unified artifact or source has changed: '+name)
    return joblib.load(out/'model.joblib'),report


def route(known_rooms,query):
    if query.room.isna().any() or query.room.astype(str).str.strip().eq('').any():
        raise ValueError('Room identifier required')
    return np.where(query.room.isin(known_rooms),'known','unseen')


def fit_cold(reference):
    selected,trials=V8.select(reference)
    x=V8.features(reference);median=x.median().fillna(0);x=x.fillna(median)
    weights=V8.room_weights(reference);scaler=None
    if selected[0]=='Ridge':
        scaler=StandardScaler().fit(x,sample_weight=weights);x=scaler.transform(x)
        model=Ridge(alpha=selected[1])
    else:
        model=lgb.LGBMRegressor(n_estimators=int(selected[1]),learning_rate=.05,num_leaves=15,
            min_child_samples=20,random_state=42,n_jobs=2,verbosity=-1)
    model.fit(x,reference.occupancy_rate,sample_weight=weights)
    return dict(model=model,median=median,scaler=scaler,selected=list(selected),trials=trials,
        known_rooms=sorted(reference.room.unique()),cutoff=reference.date.max(),features=list(median.index))


def predict_cold(bundle,query):
    x=V8.features(query).fillna(bundle['median'])
    if bundle['scaler'] is not None:x=bundle['scaler'].transform(x)
    return np.maximum(0,bundle['model'].predict(x))


def probability(model,x):
    if len(model.classes_)==1:return np.full(len(x),float(model.classes_[0]))
    return model.predict_proba(x)[:,list(model.classes_).index(True)]


def fit_low(train,valid,final,cal):
    a,b=V7.matrix(train,valid);trials=[]
    def estimator(n):return lgb.LGBMClassifier(n_estimators=n,learning_rate=.05,num_leaves=15,
        min_child_samples=20,random_state=42,n_jobs=2,verbosity=-1)
    for n in [80,200,400]:
        m=estimator(n).fit(a,train.occupancy_rate.lt(.1));p=probability(m,b)
        trials.append((float(np.mean((valid.occupancy_rate.lt(.1).to_numpy()-p)**2)),n))
    _,n=min(trials)
    a=V7.features(final,final);median=a.median().fillna(0)
    m=estimator(n).fit(a.fillna(median),final.occupancy_rate.lt(.1))
    p=probability(m,V7.features(final,cal).fillna(median))
    threshold,scan=V7.select_threshold(cal.occupancy_rate.lt(.1),p)
    return dict(model=m,median=median,reference=final,threshold=threshold,trees=n,
        trials=trials,calibration_trials=scan)


def fit_low_prequential(data,test_week):
    """Select, calibrate and fit the alert branch using only weeks before test_week."""
    weeks=sorted(map(int,data.week.unique()));wi=weeks.index(int(test_week))
    if wi<3:raise ValueError('Insufficient history for prequential alert calibration')
    validation_week=weeks[wi-3];calibration_weeks=weeks[wi-2:wi]
    train=data[data.week<validation_week];valid=data[data.week.eq(validation_week)]
    selected,trials=V10.choose(train,valid)
    cal_frames=[];cal_probs=[]
    for cw in calibration_weeks:
        target=data[data.week.eq(cw)];fit=data[data.week<cw]
        cal_probs.append(V10.fit_predict(fit,target,selected));cal_frames.append(target)
    cal=pd.concat(cal_frames);y=cal.occupancy_rate.lt(.1).to_numpy(dtype=bool)
    threshold,scan,policy=V9.threshold_scan(y,np.concatenate(cal_probs))
    reference=data[data.week<int(test_week)]
    fitted=V10.fit_bundle(reference,selected)
    fitted.update(threshold=float(threshold['threshold']),calibration_weeks=calibration_weeks,
        validation_week=int(validation_week),calibration_trials=scan,calibration_policy=policy,
        model_selection_trials=trials)
    return fitted


def make_bundle(train,valid,final,cal,test_week,data=None):
    if not (train.date.max()<valid.date.min() and final.date.max()<cal.date.min()):
        raise ValueError('Training, validation and calibration must be chronological')
    if set(final.session_id)&set(cal.session_id):raise ValueError('Calibration overlap')
    _,warm,_=R.fit_selected('LightGBM',train,valid,final,cal.iloc[:1])
    data=R.load() if data is None else data
    low=fit_low_prequential(data,test_week)
    reference=data[data.week<int(test_week)]
    cutoff=max(pd.to_datetime(cal.date).max(),pd.to_datetime(reference.date).max())
    return dict(version='unified_v2',known_rooms=sorted(final.room.unique()),warm=warm,
        cold=fit_cold(final),low=low,cutoff=cutoff,
        fitted_ids=set(reference.session_id))


def predict_bundle(bundle,query):
    """Serving always rejects dates at/before all fitting and calibration data."""
    q=query.copy();q['date']=pd.to_datetime(q.date,errors='coerce')
    if q.empty:return pd.DataFrame(columns=['session_id','prediction','prediction_route','low_probability','low_alert'])
    if q.date.isna().any() or (q.date<=bundle['cutoff']).any():raise ValueError('Query must be after model and calibration cutoff')
    if not q.session_id.is_unique or set(q.session_id)&bundle['fitted_ids']:raise ValueError('Duplicate or fitted query session')
    routing=route(bundle['known_rooms'],q);p=np.empty(len(q));prob=np.full(len(q),np.nan);alerts=np.zeros(len(q),bool)
    warm=routing=='known';cold=~warm
    if warm.any():
        selected=q.iloc[np.flatnonzero(warm)];p[warm]=R.predict(bundle['warm'],selected)
        low=bundle['low'];prob[warm]=V10.predict_bundle(low,selected)
        alerts[warm]=prob[warm]>=low['threshold']
    if cold.any():
        p[cold]=predict_cold(bundle['cold'],q.iloc[np.flatnonzero(cold)]);alerts[cold]=p[cold]<.1
    return pd.DataFrame(dict(session_id=q.session_id.to_numpy(),prediction=p,prediction_route=routing,
        low_probability=prob,low_alert=alerts))


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=dict(version='unified_v2',status='Retrospective routed research system, not default',
        routing='Room in fitted reference -> revised LightGBM and validation-selected v10 classifier with prequential two-week threshold calibration; otherwise v8 static nested-selected model and prediction<.1 rule.',
        routing_inputs='Room identity only; never query occupancy, attendees, error or best test result.',
        time='Weeks 8,10,11,12; alert model family is selected on a prior validation week, threshold is calibrated on two strictly pre-test weeks, and inference is strictly after the full fitting cutoff.',
        spatial='All nine outer rooms excluded from fitting and inner selection; same router random comparator uses known branch.',
        forward_cold='Additional week12 held-room check: fit other rooms weeks<=10, never target-room labels or week11/12 labels.',
        limitations=['Previously inspected weeks and rooms','Original spatial diagnostic includes other-room later dates',
            'Week-specific high precision may still miss many low-use sessions; report recall and false negatives','Pooled four-week performance can differ from week12 point gate','Cold-room low-use score is a regression rule, no classifier probability','No automatic room release or access verification'],
        adoption='Original numeric criteria and stricter forward-cold result reported separately; no automatic default change.')
    R.dump(OUT/'protocol.json',protocol)
    d=R.load();weeks=sorted(d.week.unique());report=dict(protocol=protocol,rolling={},spatial={},forward_cold={})
    rolling=[]
    for tw in [8,10,11,12]:
        i=weeks.index(tw);vw,cw=weeks[i-2:i]
        train=d[d.week<vw];valid=d[d.week.eq(vw)];final=d[d.week<=vw];cal=d[d.week.eq(cw)];test=d[d.week.eq(tw)]
        bundle=make_bundle(train,valid,final,cal,tw,d);pred=predict_bundle(bundle,test)
        f=test[['session_id','date','room','course_id','week','occupancy_rate']].merge(pred,on='session_id',validate='one_to_one')
        rolling.append(f);met=R.metrics(f.occupancy_rate,f.prediction);low=R.binary_metrics(f.occupancy_rate.lt(.1),f.low_alert)
        base=R.baselines(final,test);gains={k:1-met['rmse']/R.metrics(test.occupancy_rate,base[k])['rmse'] for k in ['timetable_static','historical_mean']}
        report['rolling'][str(tw)]=dict(regression=met,low=low,baseline_gains=gains,threshold=bundle['low']['threshold'],
            routes=f.prediction_route.value_counts().to_dict(),cutoff=str(bundle['cutoff'].date()),cold_selection=bundle['cold']['selected'])
        if tw==12:
            joblib.dump(bundle,OUT/'model.joblib')
            loaded=predict_bundle(joblib.load(OUT/'model.joblib'),test)
            np.testing.assert_allclose(loaded.prediction,pred.prediction,rtol=0,atol=0)
            assert loaded.low_alert.equals(pred.low_alert)
        print('time',tw,round(met['rmse'],4),round(low['precision'],4),flush=True)
    f=pd.concat(rolling);f.to_csv(OUT/'time_predictions.csv',index=False)
    report['pooled_low']=R.binary_metrics(f.occupancy_rate.lt(.1),f.low_alert)
    report['robustness_summary']=dict(
        low_use_pooled_gate=bool(report['pooled_low']['f1']>=.6 or report['pooled_low']['precision']>=.65),
        low_use_week12_point_gate=bool(report['rolling']['12']['low']['f1']>=.6 or report['rolling']['12']['low']['precision']>=.65),
        weeks=list(map(int,[8,10,11,12])),
        interpretation='The original low-use gate passes on week 12 only; the pooled four-week result is reported separately and does not pass.')
    frames=[];forward=[]
    for room in sorted(d.room.unique()):
        reference=d[d.room.ne(room)];query=d[d.room.eq(room)]
        assert (route(reference.room.unique(),query)=='unseen').all()
        cold=fit_cold(reference);p=predict_cold(cold,query)
        frames.append(R.prediction_frame(query,p,prediction_route='unseen'))
        report['spatial'][room]=dict(metrics=R.metrics(query.occupancy_rate,p),selected=cold['selected'],
            reference_rooms=sorted(reference.room.unique()))
        past=reference[reference.week<=10];future=query[query.week.eq(12)]
        cold=fit_cold(past);assert cold['cutoff']<future.date.min()
        p=predict_cold(cold,future);forward.append(R.prediction_frame(future,p,prediction_route='unseen'))
        report['forward_cold'][room]=dict(metrics=R.metrics(future.occupancy_rate,p),selected=cold['selected'],cutoff=str(cold['cutoff'].date()),reference_rooms=cold['known_rooms'])
        print('room',room,'spatial',round(report['spatial'][room]['metrics']['rmse'],4),'forward',round(report['forward_cold'][room]['metrics']['rmse'],4),flush=True)
    spatial=pd.concat(frames);spatial.to_csv(OUT/'spatial_predictions.csv',index=False)
    pd.concat(forward).to_csv(OUT/'forward_cold_predictions.csv',index=False)
    # Use the actual router's known-room branch for its own random comparator.
    it,ie=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    itr,iv=train_test_split(it,test_size=.2,random_state=42)
    assert (route(d.iloc[it].room.unique(),d.iloc[ie])=='known').all()
    p,_,_=R.fit_selected('LightGBM',d.iloc[itr],d.iloc[iv],d.iloc[it],d.iloc[ie])
    R.prediction_frame(d.iloc[ie],p,prediction_route='known').to_csv(OUT/'random_predictions.csv',index=False)
    random=R.metrics(d.iloc[ie].occupancy_rate,p)
    macro=float(np.mean([m['metrics']['rmse'] for m in report['spatial'].values()]))
    future_macro=float(np.mean([m['metrics']['rmse'] for m in report['forward_cold'].values()]))
    report['spatial_summary']=dict(macro_rmse=macro,random_rmse=random['rmse'],gap_vs_random=macro/random['rmse']-1,
        conditional_course_bootstrap=V8.conditional_interval(spatial))
    report['forward_cold_summary']=dict(macro_rmse=future_macro,absolute_018_pass=bool(future_macro<=.18),
        note='Additional diagnostic, not substituted for original spatial gate.')
    last=report['rolling']['12'];low=last['low']
    report['original_numeric_gates']=dict(regression=all(x>=.1 for x in last['baseline_gains'].values()),
        low=bool(low['f1']>=.6 or low['precision']>=.65),spatial=bool(macro<=.18 or macro/random['rmse']-1<=.3))
    report['default_model_changed']=False
    report['sha256']={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(R.__file__),Path(V7.__file__),Path(V8.__file__),Path(V9.__file__),Path(V10.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'protocol.json',OUT/'model.joblib']}
    R.dump(OUT/'report.json',report)
    print('SUMMARY',report['original_numeric_gates'],report['spatial_summary'],report['forward_cold_summary'],flush=True)
    return report


if __name__=='__main__':run()
