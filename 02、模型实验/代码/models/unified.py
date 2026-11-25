"""Executable routed research model with a frozen, label-independent policy.

Known room: revised LightGBM + fixed ensemble and explicit calendar review.
Unseen room: cold_week nested-selected model (v8 features + teaching week), low-use rule prediction < .1.
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
import stable_low as LOW
import cold_week as COLD
import context_low as CONTEXT
import calendar_context as CALENDAR

OUT=R.ROOT/'02、模型实验/生成产物/unified'
PREDICTION_COLUMNS=['session_id','prediction','prediction_route','low_probability','context_probability','model_alert','context_alert','calendar_review','low_alert','regression_prediction','state_prediction','held_prediction']
ROOMS=('BUS 105','BUS 115','CLB 7','CLB 8','MathewsThA','MathewsThB','MathewsThC','MathewsThD','PhysicsTh')


def required_artifacts():
    """The verifier defines the contract; the report cannot omit required keys."""
    model_dir='02、模型实验/代码/models/'
    output='02、模型实验/生成产物/unified/'
    names={model_dir+n+'.py' for n in ('unified','revised','improvement_v7','improvement_v8','cold_week','stable_low','context_low','calendar_context')}
    names.update('01、数据处理/代码/'+n+'.py' for n in ('pipeline_clean','heal_base'))
    names.update('01、数据处理/清洗产物/'+n for n in ('sessions.csv','attendance_clean.csv','clean_computed.csv','input_manifest.json'))
    names.add('05、文档依赖/依赖/unsw_input_hashes.json')
    names.update(output+n for n in ('model.joblib','protocol.json'))
    names.update(output+'fold_models/rolling_'+str(w)+'.joblib' for w in (8,10,11,12))
    names.update(output+'fold_models/'+kind+'_'+str(i)+'.joblib' for kind in ('spatial','forward') for i in range(9))
    names.add(output+'fold_models/random.joblib')
    return names


def load_verified(root=R.ROOT):
    root=Path(root);out=root/'02、模型实验/生成产物/unified'
    report=json.loads((out/'report.json').read_text(encoding='utf-8'))
    if set(report.get('sha256',{})) != required_artifacts():
        raise ValueError('Incomplete or unexpected unified evidence manifest')
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
    """v5: the v8 static candidates remain inside the grid; selection is inner leave-one-room-out only."""
    return COLD.fit(reference)


def predict_cold(bundle,query):
    return COLD.predict(bundle,query)


def make_bundle(train,valid,final,cal,test_week,data=None):
    if not (train.date.max()<valid.date.min() and final.date.max()<cal.date.min()):
        raise ValueError('Training, validation and calibration must be chronological')
    if set(final.session_id)&set(cal.session_id):raise ValueError('Calibration overlap')
    _,warm,_=R.fit_selected('LightGBM',train,valid,final,cal.iloc[:1])
    # v6 two-part model (experiment 14): conditional regression on held-like sessions only.
    held=lambda x:x[x.occupancy_rate.ge(.1)]
    _,cond,_=R.fit_selected('LightGBM',held(train),held(valid),held(final),cal.iloc[:1])
    low_mean=float(final.loc[final.occupancy_rate.lt(.1),'occupancy_rate'].mean())
    data=R.load() if data is None else data
    reference=data[data.week<int(test_week)]
    low=LOW.fit_bundle(reference)
    cutoff=max(pd.to_datetime(cal.date).max(),pd.to_datetime(reference.date).max())
    return dict(version='unified_v6',known_rooms=sorted(final.room.unique()),warm=warm,cond=cond,low_mean=low_mean,
        cold=fit_cold(final),low=low,context=CONTEXT.fit(reference),cutoff=cutoff,
        fitted_ids=set(reference.session_id))


def predict_bundle(bundle,query):
    """Serving always rejects dates at/before all fitting and calibration data."""
    q=query.copy();q['date']=pd.to_datetime(q.date,errors='coerce')
    if q.empty:
        return pd.DataFrame({name:pd.Series(dtype=bool if name in ('model_alert','context_alert','calendar_review','low_alert') else float if name in ('prediction','low_probability','context_probability','regression_prediction','state_prediction','held_prediction') else object) for name in PREDICTION_COLUMNS})
    if q.date.isna().any() or (q.date<=bundle['cutoff']).any():raise ValueError('Query must be after model and calibration cutoff')
    CALENDAR.review_flag(q)  # Both serving routes share the same historical scope.
    if not q.session_id.is_unique or set(q.session_id)&bundle['fitted_ids']:raise ValueError('Duplicate or fitted query session')
    seats=pd.to_numeric(q.seats,errors='coerce')
    if not np.isfinite(seats).all() or not seats.between(35,497).all() or seats.mod(1).ne(0).any():
        raise ValueError('Capacity outside the observed historical serving domain (35..497 integer seats)')
    routing=route(bundle['known_rooms'],q);p=np.empty(len(q));reg=np.empty(len(q));state=np.empty(len(q));held=np.full(len(q),np.nan);prob=np.full(len(q),np.nan);alerts=np.zeros(len(q),bool)
    model_alert=np.zeros(len(q),bool);calendar_review=np.zeros(len(q),bool);context_alert=np.zeros(len(q),bool);context_prob=np.full(len(q),np.nan)
    warm=routing=='known';cold=~warm
    if warm.any():
        selected=q.iloc[np.flatnonzero(warm)];reg[warm]=R.predict(bundle['warm'],selected)
        low=LOW.predict_bundle(bundle['low'],selected);prob[warm]=low['probability']
        held_prediction=R.predict(bundle['cond'],selected);held[warm]=held_prediction
        p[warm]=prob[warm]*bundle['low_mean']+(1-prob[warm])*held_prediction
        context_prob[warm]=CONTEXT.predict(bundle['context'],selected);context_alert[warm]=context_prob[warm]>=CONTEXT.THRESHOLD
        model_alert[warm]=low['model_alert'];calendar_review[warm]=low['calendar_review'];alerts[warm]=low['alert']|context_alert[warm]
        state[warm]=np.where(alerts[warm],bundle['low_mean'],held_prediction)
    if cold.any():
        p[cold]=predict_cold(bundle['cold'],q.iloc[np.flatnonzero(cold)]);alerts[cold]=p[cold]<.1;model_alert[cold]=alerts[cold]
        reg[cold]=p[cold];state[cold]=p[cold]
    return pd.DataFrame(dict(session_id=q.session_id.to_numpy(),prediction=p,prediction_route=routing,
        low_probability=prob,context_probability=context_prob,model_alert=model_alert,context_alert=context_alert,calendar_review=calendar_review,low_alert=alerts,
        regression_prediction=reg,state_prediction=state,held_prediction=held))


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    folds=OUT/'fold_models';folds.mkdir(exist_ok=True)
    protocol=dict(version='unified_v6',status='Default historical research system for the original three numeric criteria',
        routing='Known room: two-part occupancy model (v6): prediction = p*m0 + (1-p)*m1 with p the original classifier probability, m0 the mean low-use occupancy of the regression training set and m1 a LightGBM regression fitted on sessions with occupancy>=.10; state_prediction = m0 when alerted else m1 (shown occupancy and <10% screening); regression_prediction keeps the single LightGBM for comparison. Alerts: original equal-weight logistic/tree score >=.50 OR complementary day-context logistic/tree/forest median >=.50 OR independently sourced public-holiday review. Unseen room: cold_week nested-selected model (v8 static features plus teaching week, pressure x week, pressure squared; Ridge/LightGBM/blend chosen by inner leave-one-room-out) and prediction<.1 rule.',
        routing_inputs='Room identity only; never query occupancy, attendees, error or best test result.',
        time='Weeks 8,10,11,12; fixed classifier parameters and threshold in every fold; features use only strictly earlier dates; inference is after all fitting observations.',
        baselines='Equal information (2026-11-24): both original criterion-1 baselines use every labelled week before the test week, the same cutoff as the low-use and context classifiers whose probability enters the two-part prediction. Gains with the former validation-week cutoff are kept as baseline_gains_validation_cutoff.',
        calendar=dict(window=[CALENDAR.WINDOW_START,CALENDAR.WINDOW_END],statewide_holidays=CALENDAR.STATEWIDE_PUBLIC_HOLIDAYS,sources=CALENDAR.SOURCES,source_sha256=CALENDAR.SOURCE_SHA256,meaning='Review context only; never a probability, relabel, deletion, or confirmed vacancy.'),
        spatial='All nine outer rooms excluded from fitting and inner selection; random comparator keeps the single LightGBM regression (v5 known branch), not the v6 two-part mean.',
        forward_cold='Additional week12 held-room check: fit other rooms weeks<=10, never target-room labels or week11/12 labels.',
        limitations=['Previously inspected weeks and rooms','Original spatial diagnostic includes other-room later dates',
            'Week-specific high precision may still miss many low-use sessions; report recall and false negatives','Pooled four-week performance can differ from week12 point gate','Cold-room low-use score is a regression rule, no classifier probability','No automatic room release or access verification'],
        context_history='All training and test observations retained. Ordinary-day historical features aggregate strictly earlier non-public-holiday references; holiday queries keep original history. Context vote is separate from original score and never described as a calibrated combined probability.',
        adoption='2026-11-18: retain original alerts and supplement with a fixed contextual majority following recorded experiments 05-10. All four weeks retain original criterion 2 with F1>=.65 and recall>=.65; per-week misses do not increase and pooled precision>=.65. Cost 3*FN+FP is a stated research assumption. Regression branches, labels and evaluation rows unchanged; retrospective, not a blind test. 2026-11-23 (v5): unseen-room branch replaced by cold_week after supplementary experiment 11 passed all four frozen checks (macro<=.175, forward not worse, rooms over .18 not more, interval upper not higher); known-room branch and alerts unchanged. 2026-11-23 (v6): known-room regression replaced by the two-part model after supplementary experiment 14 passed both frozen tiers (screening: every week F1>=.60, pooled F1 not below formal; regression: every week gains>=10%, week12 and pooled RMSE not worse). Alert rule unchanged.')
    R.dump(OUT/'protocol.json',protocol)
    d=R.load();weeks=sorted(d.week.unique());report=dict(protocol=protocol,rolling={},spatial={},forward_cold={})
    rolling=[]
    for tw in [8,10,11,12]:
        i=weeks.index(tw);vw,cw=weeks[i-2:i]
        train=d[d.week<vw];valid=d[d.week.eq(vw)];final=d[d.week<=vw];cal=d[d.week.eq(cw)];test=d[d.week.eq(tw)]
        bundle=make_bundle(train,valid,final,cal,tw,d);pred=predict_bundle(bundle,test)
        joblib.dump(bundle,folds/f'rolling_{tw}.joblib')
        f=test[['session_id','date','room','course_id','week','occupancy_rate']].merge(pred,on='session_id',validate='one_to_one')
        rolling.append(f);met=R.metrics(f.occupancy_rate,f.prediction);low=R.binary_metrics(f.occupancy_rate.lt(.1),f.low_alert)
        # Equal information (2026-11-24): p in the two-part prediction comes from classifiers fitted on every week
        # before the test week, so both original baselines get that same cutoff. The former validation-week cutoff
        # (less information for the baselines than for the model) is kept only for traceability.
        def gains_from(reference):
            base=R.baselines(reference,test)
            return {k:1-met['rmse']/R.metrics(test.occupancy_rate,base[k])['rmse'] for k in ['timetable_static','historical_mean']}
        gains=gains_from(d[d.week<tw]);gains_validation_cutoff=gains_from(final)
        report['rolling'][str(tw)]=dict(regression=met,low=low,baseline_gains=gains,baseline_gains_validation_cutoff=gains_validation_cutoff,threshold=bundle['low']['threshold'],
            classifier_only=R.binary_metrics(f.occupancy_rate.lt(.1),f.model_alert),context_only=R.binary_metrics(f.occupancy_rate.lt(.1),f.context_alert),
            context_added_alerts=int((f.context_alert&~(f.model_alert|f.calendar_review)).sum()),
            calendar_rows=int(f.calendar_review.sum()),calendar_added_alerts=int((f.calendar_review&~(f.model_alert|f.context_alert)).sum()),
            routes=f.prediction_route.value_counts().to_dict(),cutoff=str(bundle['cutoff'].date()),cold_selection=bundle['cold']['selected'])
        if tw==12:
            joblib.dump(bundle,OUT/'model.joblib')
            loaded=predict_bundle(joblib.load(OUT/'model.joblib'),test)
            np.testing.assert_allclose(loaded.prediction,pred.prediction,rtol=0,atol=0)
            assert loaded.low_alert.equals(pred.low_alert)
        print('time',tw,round(met['rmse'],4),round(low['precision'],4),flush=True)
    f=pd.concat(rolling);f.to_csv(OUT/'time_predictions.csv',index=False)
    report['pooled_low']=R.binary_metrics(f.occupancy_rate.lt(.1),f.low_alert)
    report['pooled_classifier_only']=R.binary_metrics(f.occupancy_rate.lt(.1),f.model_alert)
    report['robustness_summary']=dict(
        low_use_pooled_gate=bool(report['pooled_low']['f1']>=.6 or report['pooled_low']['precision']>=.65),
        low_use_week12_point_gate=bool(report['rolling']['12']['low']['f1']>=.6 or report['rolling']['12']['low']['precision']>=.65),
        weeks=list(map(int,[8,10,11,12])),
        every_week_original_low_gate=all(x['low']['f1']>=.6 or x['low']['precision']>=.65 for x in report['rolling'].values()),
        every_week_recall_at_least_050=all(x['low']['recall']>=.5 for x in report['rolling'].values()),
        pooled_precision_at_least_065=report['pooled_low']['precision']>=.65,
        pooled_recall_at_least_060=report['pooled_low']['recall']>=.6,
        week12_misses_at_most_25=report['rolling']['12']['low']['confusion_tn_fp_fn_tp'][2]<=25,
        interpretation='All four weeks and pooled metrics are reported with unchanged sample membership. These additional stability checks do not replace the original three criteria.')
    frames=[];forward=[]
    if tuple(sorted(d.room.unique())) != ROOMS:raise ValueError('Unexpected room cohort')
    for room_index,room in enumerate(ROOMS):
        reference=d[d.room.ne(room)];query=d[d.room.eq(room)]
        assert (route(reference.room.unique(),query)=='unseen').all()
        cold=fit_cold(reference);p=predict_cold(cold,query)
        joblib.dump(cold,folds/f'spatial_{room_index}.joblib')
        frames.append(R.prediction_frame(query,p,prediction_route='unseen'))
        report['spatial'][room]=dict(metrics=R.metrics(query.occupancy_rate,p),selected=cold['selected'],
            reference_rooms=sorted(reference.room.unique()))
        past=reference[reference.week<=10];future=query[query.week.eq(12)]
        cold=fit_cold(past);assert cold['cutoff']<future.date.min()
        joblib.dump(cold,folds/f'forward_{room_index}.joblib')
        p=predict_cold(cold,future);forward.append(R.prediction_frame(future,p,prediction_route='unseen'))
        report['forward_cold'][room]=dict(metrics=R.metrics(future.occupancy_rate,p),selected=cold['selected'],cutoff=str(cold['cutoff'].date()),reference_rooms=cold['known_rooms'])
        print('room',room,'spatial',round(report['spatial'][room]['metrics']['rmse'],4),'forward',round(report['forward_cold'][room]['metrics']['rmse'],4),flush=True)
    spatial=pd.concat(frames);spatial.to_csv(OUT/'spatial_predictions.csv',index=False)
    pd.concat(forward).to_csv(OUT/'forward_cold_predictions.csv',index=False)
    # Use the actual router's known-room branch for its own random comparator.
    it,ie=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    itr,iv=train_test_split(it,test_size=.2,random_state=42)
    assert (route(d.iloc[it].room.unique(),d.iloc[ie])=='known').all()
    p,random_bundle,_=R.fit_selected('LightGBM',d.iloc[itr],d.iloc[iv],d.iloc[it],d.iloc[ie])
    joblib.dump(random_bundle,folds/'random.joblib')
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
    report['default_model_changed']=True
    report['sha256']={name:hashlib.sha256((R.ROOT/name).read_bytes()).hexdigest() for name in sorted(required_artifacts())}
    R.dump(OUT/'report.json',report)
    print('SUMMARY',report['original_numeric_gates'],report['spatial_summary'],report['forward_cold_summary'],flush=True)
    return report


if __name__=='__main__':run()
