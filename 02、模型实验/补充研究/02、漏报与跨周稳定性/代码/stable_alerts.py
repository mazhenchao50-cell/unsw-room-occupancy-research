"""Fixed retrospective candidate for missed low-use sessions and weekly drift."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import warnings

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'02、模型实验/代码/models'))
import revised as R
import improvement_v7 as V7

OUT = Path(__file__).resolve().parents[1]/'生成产物'
TEST_WEEKS = [8, 10, 11, 12]
THRESHOLDS = [round(x/100, 2) for x in range(10, 91, 5)]


def features(reference, query, recent=True):
    """Only reference labels strictly before each query date are available."""
    reference=reference.copy();query=query.copy()
    reference['date']=pd.to_datetime(reference.date)
    query['date']=pd.to_datetime(query.date)
    x=V7.features(reference, query)
    if not recent:
        return x
    records=[]
    for row in query.itertuples():
        past=reference[reference.date.lt(row.date)].sort_values(['date','session_id'])
        course=past[past.course_id.eq(row.course_id)]
        course_room=course[course.room.eq(row.room)]
        room=past[past.room.eq(row.room)]
        latest=past[past.date.ge(row.date-pd.Timedelta(days=21))]
        room_latest=room[room.date.ge(row.date-pd.Timedelta(days=21))]
        fallback=float(past.occupancy_rate.mean()) if len(past) else .3
        prior_low=float(past.occupancy_rate.lt(.1).mean()) if len(past) else .2
        def mean(part):return float(part.occupancy_rate.mean()) if len(part) else fallback
        def low(part):return float(part.occupancy_rate.lt(.1).mean()) if len(part) else prior_low
        last=mean(course.tail(1));before=mean(course.iloc[-2:-1]) if len(course)>1 else last
        records.append(dict(
            course_last_rate=last,course_recent_mean3=mean(course.tail(3)),
            course_recent_low3=low(course.tail(3)),course_recent_mean5=mean(course.tail(5)),
            course_recent_low5=low(course.tail(5)),course_trend3=mean(course.tail(3))-mean(course),
            course_last_delta=last-before,course_room_last=mean(course_room.tail(1)),
            course_room_mean3=mean(course_room.tail(3)),course_room_low3=low(course_room.tail(3)),
            room_recent_low=low(room_latest),global_recent_low=low(latest),
            course_history_log_n=np.log1p(len(course)),room_history_log_n=np.log1p(len(room)),
            days_since_course=float((row.date-course.date.max()).days) if len(course) else 90.,
            course_seen=float(bool(len(course))),course_room_seen=float(bool(len(course_room)))))
    return pd.concat([x,pd.DataFrame(records,index=query.index)],axis=1)


def validate_forward(reference, query):
    if reference.empty or query.empty or reference.date.max()>=query.date.min():
        raise ValueError('Training must end before the whole forecast period')
    if not query.session_id.is_unique or set(reference.session_id)&set(query.session_id):
        raise ValueError('Duplicate or fitted evaluation sessions')


def fit_bundle(reference, recent=True, matrix=None):
    if reference.empty:
        raise ValueError('Nonempty fitting reference required')
    x=features(reference,reference,recent) if matrix is None else matrix.copy()
    median=x.median().fillna(0);x=x.fillna(median)
    if not np.isfinite(x.to_numpy()).all():raise ValueError('Non-finite fitting features')
    y=reference.occupancy_rate.lt(.1)
    if y.nunique()<2:raise ValueError('Both classes are required')
    scaler=StandardScaler().fit(x)
    logistic=LogisticRegression(C=1.0,class_weight=None,max_iter=2000,random_state=42)
    trees=lgb.LGBMClassifier(n_estimators=150,num_leaves=7,min_child_samples=30,
                            learning_rate=.05,random_state=42,n_jobs=2,verbosity=-1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        logistic.fit(scaler.transform(x),y);trees.fit(x,y)
    return dict(logistic=logistic,trees=trees,scaler=scaler,median=median,
                reference=reference.copy(),recent=recent,features=list(x.columns),
                cutoff=reference.date.max(),fitted_ids=set(reference.session_id),
                warnings=[str(w.message) for w in caught])


def predict_components(bundle, query, matrix=None):
    validate_forward(bundle['reference'],query)
    x=features(bundle['reference'],query,bundle['recent']) if matrix is None else matrix.copy()
    x=x.fillna(bundle['median'])
    if list(x.columns)!=bundle['features'] or not np.isfinite(x.to_numpy()).all():
        raise ValueError('Invalid serving features')
    a=bundle['logistic'].predict_proba(bundle['scaler'].transform(x))[:,1]
    b=bundle['trees'].predict_proba(x)[:,1]
    return dict(logistic=a,trees=b,ensemble=(a+b)/2)


def choose_threshold(calibration, worst_week=True):
    if calibration.empty or not calibration.session_id.is_unique:
        raise ValueError('Nonempty unique calibration sessions required')
    if not np.isfinite(calibration.probability).all():raise ValueError('Invalid calibration probability')
    rows=[]
    for threshold in THRESHOLDS:
        weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.probability.ge(threshold))
                for w,g in calibration.groupby('week')}
        pooled=R.binary_metrics(calibration.occupancy_rate.lt(.1),calibration.probability.ge(threshold))
        rows.append(dict(threshold=threshold,weekly=weekly,pooled=pooled,
                         min_f1=min(m['f1'] for m in weekly.values()),
                         mean_f1=float(np.mean([m['f1'] for m in weekly.values()]))))
    if worst_week:
        best=max(rows,key=lambda r:(r['min_f1'],r['mean_f1'],r['pooled']['precision'],r['threshold']))
    else:
        best=max(rows,key=lambda r:(r['pooled']['f1'],r['pooled']['precision'],r['threshold']))
    return best,rows


def adoption(metrics, weekly):
    return dict(week12_misses_at_most_25=weekly['12']['confusion_tn_fp_fn_tp'][2]<=25,
                pooled_precision_at_least_065=metrics['precision']>=.65,
                pooled_recall_at_least_060=metrics['recall']>=.60,
                every_week_original_gate=all(m['f1']>=.60 or m['precision']>=.65 for m in weekly.values()),
                every_week_recall_at_least_050=all(m['recall']>=.50 for m in weekly.values()))


def summarize(frame, alert):
    return dict(pooled=R.binary_metrics(frame.occupancy_rate.lt(.1),frame[alert]),
                weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g[alert]) for w,g in frame.groupby('week')})


def paired_interval(frame, replicates=1000):
    rng=np.random.default_rng(42);groups=[g for _,g in frame.groupby('course_id')]
    deltas=[]
    for _ in range(replicates):
        sample=pd.concat([groups[i] for i in rng.integers(0,len(groups),len(groups))],ignore_index=True)
        y=sample.occupancy_rate.lt(.1)
        a=R.binary_metrics(y,sample.primary_alert);b=R.binary_metrics(y,sample.old_alert)
        deltas.append([a['recall']-b['recall'],a['precision']-b['precision'],a['f1']-b['f1']])
    return dict(recall_delta_95=np.quantile(deltas,[.025,.975],axis=0)[:,0].tolist(),
                precision_delta_95=np.quantile(deltas,[.025,.975],axis=0)[:,1].tolist(),
                f1_delta_95=np.quantile(deltas,[.025,.975],axis=0)[:,2].tolist(),replicates=replicates,
                scope='Conditional course-cluster resampling, fitted predictions fixed; not independent future evidence or selection-adjusted inference.')


def run(cache_root):
    cache_root=Path(cache_root).resolve()
    cache_root.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((Path(__file__).parent/'固定研究协议.json').read_text(encoding='utf-8-sig'))
    R.dump(OUT/'固定研究协议.json',protocol)
    data=R.load();weeks=sorted(map(int,data.week.unique()))
    old=pd.read_csv(ROOT/'02、模型实验/生成产物/improvement_v10/rolling_predictions.csv')
    predictions={};bundles={};fit_warnings={}
    for recent,label in [(True,'recent'),(False,'no_recent')]:
        frames=[]
        for week in weeks[2:]:
            train=data[data.week.lt(week)];query=data[data.week.eq(week)]
            validate_forward(train,query)
            a=features(train,train,recent);b=features(train,query,recent)
            bundle=fit_bundle(train,recent,a);components=predict_components(bundle,query,b)
            frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
            for name,probability in components.items():frame[name]=probability
            frame['probability']=components['ensemble'];frames.append(frame)
            fit_warnings[f'{label}_{week}']=bundle['warnings']
            if week==12:
                joblib.dump(bundle,cache_root/f'{label}_week12.joblib');bundles[label]=bundle
            print('FIT',label,'week',week,'n',len(query),flush=True)
        predictions[label]=pd.concat(frames,ignore_index=True)
        predictions[label].to_csv(OUT/f'{label}_prequential.csv',index=False)
    outcomes=[];calibrations={}
    for week in TEST_WEEKS:
        preceding=[w for w in weeks if w<week][-3:]
        cal=predictions['recent'][predictions['recent'].week.isin(preceding)]
        assert set(cal.week)==set(preceding) and cal.week.max()<week
        best,scan=choose_threshold(cal);pooled,_=choose_threshold(cal,False)
        no_cal=predictions['no_recent'][predictions['no_recent'].week.isin(preceding)]
        no_best,_=choose_threshold(no_cal)
        test=predictions['recent'][predictions['recent'].week.eq(week)].copy()
        test['threshold']=best['threshold'];test['primary_alert']=test.probability.ge(best['threshold'])
        test['fixed_alert']=test.probability.ge(.5);test['pooled_threshold_alert']=test.probability.ge(pooled['threshold'])
        no_test=predictions['no_recent'].set_index('session_id').loc[test.session_id]
        test['no_recent_alert']=no_test.probability.to_numpy()>=no_best['threshold']
        matched=old.set_index('session_id').loc[test.session_id]
        np.testing.assert_allclose(matched.occupancy_rate,test.occupancy_rate,rtol=0,atol=1e-12)
        test['old_alert']=matched.low_alert.to_numpy();test['old_probability']=matched.low_probability.to_numpy()
        outcomes.append(test)
        calibrations[str(week)]=dict(weeks=preceding,selected=best,scan=scan,pooled_threshold=pooled['threshold'],no_recent_threshold=no_best['threshold'])
        m=R.binary_metrics(test.occupancy_rate.lt(.1),test.primary_alert)
        print('TEST',week,'threshold',best['threshold'],'P',round(m['precision'],4),'R',round(m['recall'],4),'F1',round(m['f1'],4),m['confusion_tn_fp_fn_tp'],flush=True)
        if week==12:
            bundles['recent']['threshold']=best['threshold'];bundles['recent']['calibration_weeks']=preceding
            joblib.dump(bundles['recent'],cache_root/'candidate.joblib')
    frame=pd.concat(outcomes,ignore_index=True);assert frame.session_id.is_unique and len(frame)==815
    frame.to_csv(OUT/'逐会话对比.csv',index=False)
    comparisons={key:summarize(frame,alert) for key,alert in [('primary','primary_alert'),('old','old_alert'),
                  ('fixed_05','fixed_alert'),('pooled_f1','pooled_threshold_alert'),('no_recent','no_recent_alert')]}
    checks=adoption(comparisons['primary']['pooled'],comparisons['primary']['weekly'])
    misses=frame[frame.week.eq(12)&frame.occupancy_rate.lt(.1)&frame.old_alert.eq(False)].copy()
    misses['recovered']=misses.primary_alert
    misses.to_csv(OUT/'参照方案漏报逐条复核.csv',index=False)
    grouped=[]
    for week,g in frame.groupby('week'):
        for room,part in g.groupby('room'):
            for name,alert in [('old','old_alert'),('primary','primary_alert')]:
                grouped.append(dict(week=int(week),room=room,method=name,n=len(part),**R.binary_metrics(part.occupancy_rate.lt(.1),part[alert])))
    R.dump(OUT/'逐周逐教室错误.json',grouped)
    result=dict(protocol=protocol,comparisons=comparisons,adoption_checks=checks,adoption_passed=all(checks.values()),
                calibrations=calibrations,fit_warnings=fit_warnings,paired_interval=paired_interval(frame),
                recovered_old_misses=int(misses.recovered.sum()),still_missed_old_cases=int((~misses.recovered).sum()),
                current_model_changed=False,candidate_bundle=str(cache_root/'candidate.joblib'),
                sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    [Path(__file__),Path(R.__file__),Path(V7.__file__),ROOT/'01、数据处理/清洗产物/sessions.csv',
                     OUT/'固定研究协议.json',OUT/'逐会话对比.csv']})
    R.dump(OUT/'report.json',result)
    print(json.dumps({'adoption_checks':checks,'comparisons':comparisons,'recovered_old_misses':result['recovered_old_misses']},ensure_ascii=False,indent=2),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache-root',type=Path,required=True)
    run(parser.parse_args().cache_root)
