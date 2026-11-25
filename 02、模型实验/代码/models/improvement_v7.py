"""Fixed retrospective v7: enrollment normalization and direct low-use classifier.

No outer test labels enter fitting or threshold selection. All outer folds were
previously inspected in this project, so this is not independent validation.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
import revised as R

OUT = R.ROOT / '02、模型实验/生成产物/improvement_v7'
THRESHOLDS = [.1, .2, .3, .4, .5, .6, .7, .8, .9]


def scale(frame):
    """Known enrollment pressure, with capacity fallback for absent enrollment."""
    seats = frame.seats.to_numpy(float)
    if not np.all(np.isfinite(seats) & (seats > 0)):
        raise ValueError('Positive finite capacity required')
    e = frame.enrollments.to_numpy(float)
    return np.where(np.isfinite(e) & (e > 0), e / seats, 1.)


def features(reference, query):
    x = R.raw_features(reference, query)
    x['enrollment_pressure'] = scale(query)
    x['enrollment_missing_or_zero'] = (~(query.enrollments.fillna(0) > 0)).astype(float)
    x['log_seats'] = np.log(query.seats)
    # Unlike a query's own label, strictly earlier reference labels are available.
    factors = reference.occupancy_rate.to_numpy() / scale(reference)
    reference = reference.assign(attendance_factor=factors)
    rows = []
    for row in query.itertuples():
        past = reference[reference.date < row.date]
        course = past[past.course_id.eq(row.course_id)]
        source = course if len(course) else past
        rows.append((float(source.attendance_factor.mean()) if len(source) else .5,
                     float(source.occupancy_rate.lt(.1).mean()) if len(source) else .2))
    x[['attendance_factor_history', 'low_use_history']] = rows
    return x


def matrix(reference, query):
    a, b = features(reference, reference), features(reference, query)
    med = a.median().fillna(0)
    return a.fillna(med), b.fillna(med)


def fit_predict(train, valid, final, query, task, cached=None):
    """Select only tree count on validation; normalization is fixed in advance."""
    a, b = cached[0] if cached else matrix(train, valid)
    trials = []
    def model(n):
        args = dict(n_estimators=n, learning_rate=.05, num_leaves=15,
                    min_child_samples=20, random_state=42, n_jobs=2, verbosity=-1)
        return lgb.LGBMClassifier(**args) if task == 'classify' else lgb.LGBMRegressor(**args)
    def fit(m, x, data):
        if task == 'classify':
            return m.fit(x, data.occupancy_rate.lt(.1))
        s = scale(data)
        return m.fit(x, data.occupancy_rate / s, sample_weight=s*s)
    def predict(m, x, data):
        if task == 'classify':
            if len(m.classes_) == 1:
                return np.full(len(data), float(m.classes_[0]))
            return m.predict_proba(x)[:, list(m.classes_).index(True)]
        return np.maximum(0, m.predict(x)) * scale(data)
    for n in [80, 200, 400]:
        p = predict(fit(model(n), a, train), b, valid)
        # Brier score for probabilities; original occupancy MSE for regression.
        y = valid.occupancy_rate.lt(.1) if task == 'classify' else valid.occupancy_rate
        trials.append((float(np.mean((np.asarray(y)-p)**2)), n))
    _, n = min(trials)
    a, b = cached[1] if cached else matrix(final, query)
    return predict(fit(model(n), a, final), b, query), dict(trees=n, validation_trials=trials)


def select_threshold(y, p):
    y, p = np.asarray(y, bool), np.asarray(p, float)
    if len(y) != len(p) or not len(y) or not np.isfinite(p).all():
        raise ValueError('Calibration arrays must be nonempty, aligned, finite')
    if not y.any():
        return 1.01, []
    rows = [dict(threshold=t, **R.binary_metrics(y, p >= t)) for t in THRESHOLDS]
    # A precision target cannot be met by just one lucky calibration alert.
    eligible = [m for m in rows if m['precision'] >= .65 and m['predicted_positive'] >= 10]
    best = max(eligible or rows, key=lambda m: (m['f1'], m['precision'], m['threshold']))
    return best['threshold'], rows


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = dict(experiment='v7', status='Retrospective, no independent holdout',
        representation='Occupancy/enrollment_pressure target; pressure squared sample weights; invert pressure at prediction',
        fallback='Missing or nonpositive enrollment uses pressure 1 and explicit indicator',
        model='LightGBM fixed 80/200/400 trees; original MSE or classification Brier validation',
        low_label='occupancy_rate < 0.1, never absence or availability',
        thresholds=THRESHOLDS, calibration='F1 among precision>=.65 and >=10 alerts; else max F1; zero positives abstain',
        weeks=[8,10,11,12], spatial='All nine rooms held out entirely; same random comparator',
        adoption_gate='No automatic adoption. Require original numeric gates, pooled low-use gate, no pooled precision or recall loss vs current regression rule; independent review of explanations.',
        limitations=['All weeks and rooms previously inspected','Spatial training includes later dates from other rooms','No independent truth for cancellation or room availability'])
    R.dump(OUT/'protocol.json', protocol)
    d = R.load(); weeks = sorted(d.week.unique()); report = dict(protocol=protocol, rolling={}, loro={})
    frames = []
    for tw in protocol['weeks']:
        i=weeks.index(tw); vw,cw=weeks[i-2:i]
        tr=d[d.week<vw]; va=d[d.week.eq(vw)]; cal=d[d.week.eq(cw)]; te=d[d.week.eq(tw)]
        final=pd.concat([tr,va]).sort_values('date'); q=pd.concat([cal,te])
        assert final.date.max() < cal.date.min() <= cal.date.max() < te.date.min()
        cached=(matrix(tr,va),matrix(final,q))
        all_p, rm = fit_predict(tr,va,final,q,'regress',cached)
        p=all_p[len(cal):]
        probs, cm = fit_predict(tr,va,final,q,'classify',cached)
        threshold, trials = select_threshold(cal.occupancy_rate.lt(.1),probs[:len(cal)])
        prob=probs[len(cal):]; alerts=prob>=threshold
        met=R.metrics(te.occupancy_rate,p); low=R.binary_metrics(te.occupancy_rate.lt(.1),alerts)
        f=R.prediction_frame(te,p,low_probability=prob,low_alert=alerts,threshold=threshold)
        frames.append(f)
        baselines=R.baselines(final,te)
        gains={name:1-met['rmse']/R.metrics(te.occupancy_rate,baselines[name])['rmse'] for name in ['timetable_static','historical_mean']}
        report['rolling'][str(tw)]=dict(regression=met,classification=low,regression_selection=rm,classification_selection=cm,
            threshold=threshold,calibration_trials=trials,baseline_gains=gains,train_weeks=sorted(map(int,tr.week.unique())),validation_week=int(vw),calibration_week=int(cw))
        print('week',tw,'RMSE',round(met['rmse'],4),'F1',round(low['f1'],4),'P',round(low['precision'],4),flush=True)
    f=pd.concat(frames);f.to_csv(OUT/'rolling_predictions.csv',index=False)
    report['pooled_low']=R.binary_metrics(f.occupancy_rate.lt(.1),f.low_alert)
    frames=[]
    for room in sorted(d.room.unique()):
        te=d[d.room.eq(room)]; avail=d[d.room.ne(room)]
        assert not set(avail.session_id)&set(te.session_id)
        p, selection=fit_predict(avail[avail.week<11],avail[avail.week.eq(11)],avail,te,'regress')
        met=R.metrics(te.occupancy_rate,p)
        report['loro'][room]=dict(**met,selection=selection,reference_rooms=sorted(avail.room.unique()))
        frames.append(R.prediction_frame(te,p));print('room',room,round(met['rmse'],4),flush=True)
    f=pd.concat(frames);f.to_csv(OUT/'loro_predictions.csv',index=False)
    macro=float(np.mean([v['rmse'] for v in report['loro'].values()]))
    it,ie=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    itr,iv=train_test_split(it,test_size=.2,random_state=42)
    p,_=fit_predict(d.iloc[itr],d.iloc[iv],d.iloc[it],d.iloc[ie],'regress')
    R.prediction_frame(d.iloc[ie],p).to_csv(OUT/'random_predictions.csv',index=False)
    random=R.metrics(d.iloc[ie].occupancy_rate,p)
    report['spatial_summary']=dict(macro_rmse=macro,random=random,gap_vs_random=macro/random['rmse']-1)
    last=report['rolling']['12']; low=last['classification']
    report['numeric_candidate_gates']=dict(regression=all(x>=.1 for x in last['baseline_gains'].values()),
        low=low['f1']>=.6 or low['precision']>=.65,spatial=macro<=.18 or macro/random['rmse']-1<=.3)
    original=pd.concat([pd.read_csv(R.ROOT/f'02、模型实验/生成产物/revised/week{w}_LightGBM.csv') for w in protocol['weeks']])
    original_low=R.binary_metrics(original.occupancy_rate.lt(.1),original.prediction.lt(.1))
    report['original_pooled_low']=original_low
    pooled=report['pooled_low']
    report['retrospective_integration_gate_passed']=bool(all(report['numeric_candidate_gates'].values()) and
        (pooled['f1']>=.6 or pooled['precision']>=.65) and pooled['precision']>=original_low['precision'] and pooled['recall']>=original_low['recall'])
    report['default_model_changed']=False
    report['sha256']={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'protocol.json']}
    R.dump(OUT/'report.json',report)
    print('SUMMARY',report['numeric_candidate_gates'],report['pooled_low'],report['spatial_summary'],flush=True)
    return report


if __name__=='__main__':
    run()
