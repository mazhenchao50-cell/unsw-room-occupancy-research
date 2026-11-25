"""V9: prequential two-week calibration for low-utilization alerts.

All prior weeks remain in chronological order. Calibration probabilities for
each week are produced by a model fitted strictly before that week. The
threshold is selected from two such weeks and scored only on a later week.
This is retrospective exploration: all UNSW weeks were previously inspected.
"""
from pathlib import Path
import hashlib
import json

import lightgbm as lgb
import numpy as np
import pandas as pd

import revised as R
import improvement_v7 as V7

OUT = R.ROOT / '02、模型实验/生成产物/improvement_v9'
WEEKS = [8, 10, 11, 12]
TREE_GRID = [80, 200, 400]
THRESHOLDS = [round(x, 2) for x in np.arange(.10, 1.00, .05)]
MIN_CALIBRATION_ALERTS = 20


def estimator(n):
    return lgb.LGBMClassifier(
        n_estimators=n, learning_rate=.05, num_leaves=15,
        min_child_samples=20, random_state=42, n_jobs=2, verbosity=-1)


def probabilities(model, x):
    if len(model.classes_) == 1:
        return np.full(len(x), float(model.classes_[0]))
    return model.predict_proba(x)[:, list(model.classes_).index(True)]


def fit_probability(train, query, trees):
    if train.empty or query.empty:
        raise ValueError('Training and query data must be nonempty')
    if train.date.max() >= query.date.min():
        raise ValueError('Calibration/test prediction must be strictly forward in time')
    if set(train.session_id) & set(query.session_id):
        raise ValueError('Session leakage')
    a, b = V7.matrix(train, query)
    model = estimator(trees).fit(a, train.occupancy_rate.lt(.1))
    return probabilities(model, b)


def choose_trees(train, valid):
    if train.date.max() >= valid.date.min():
        raise ValueError('Validation must follow training')
    a, b = V7.matrix(train, valid)
    y = valid.occupancy_rate.lt(.1).to_numpy(dtype=bool)
    trials = []
    for trees in TREE_GRID:
        p = probabilities(estimator(trees).fit(a, train.occupancy_rate.lt(.1)), b)
        trials.append(dict(trees=trees, brier=float(np.mean((y-p)**2))))
    best = min(trials, key=lambda x: (x['brier'], TREE_GRID.index(x['trees'])))
    return best['trees'], trials


def threshold_scan(y, p):
    y = np.asarray(y, dtype=bool)
    p = np.asarray(p, dtype=float)
    rows = []
    for threshold in THRESHOLDS:
        predicted = p >= threshold
        tp = int(np.sum(predicted & y)); fp = int(np.sum(predicted & ~y))
        fn = int(np.sum(~predicted & y)); positives = tp + fp
        precision = tp / positives if positives else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
        rows.append(dict(threshold=threshold, precision=precision, recall=recall,
                         f1=f1, actual_positive=tp+fn, predicted_positive=positives,
                         tp=tp, fp=fp, fn=fn))
    eligible = [r for r in rows if r['precision'] >= .65 and
                r['predicted_positive'] >= MIN_CALIBRATION_ALERTS]
    if eligible:
        selected = max(eligible, key=lambda r: (r['recall'], r['f1'], -r['threshold']))
        policy = 'maximum calibration recall subject to precision>=.65 and at least 20 alerts'
    else:
        selected = max(rows, key=lambda r: (r['f1'], r['precision'], r['threshold']))
        policy = 'no eligible threshold; maximum calibration F1 fallback'
    return selected, rows, policy


def metrics(y, p, threshold):
    return R.binary_metrics(np.asarray(y, dtype=bool), np.asarray(p) >= threshold)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    data = R.load().copy()
    data['date'] = pd.to_datetime(data.date)
    weeks = sorted(map(int, data.week.unique()))
    report = dict(protocol=dict(
        name='v9 prequential pooled two-week threshold calibration',
        status='Retrospective; weeks and rooms previously inspected',
        target='Low utilization means observed peak occupancy_rate < 0.10; not absence or availability.',
        calibration='For each test week, use the two preceding weeks. Each week’s calibration probability comes from a classifier fitted only on earlier weeks. Select maximum calibration recall among fixed thresholds with precision>=0.65 and at least 20 pooled alerts; otherwise fall back to maximum F1.',
        model_selection='Select 80/200/400 LightGBM trees by Brier score on a validation week three weeks before the test week. The chosen tree count is fixed across calibration folds and final refit.',
        test_weeks=WEEKS, thresholds=THRESHOLDS, minimum_calibration_alerts=MIN_CALIBRATION_ALERTS,
        limitations=['All test weeks were previously inspected','Two calibration weeks may still not represent future term shifts',
                     'Precision is not a guarantee; do not automate room release','No external-campus validation']),
        rolling={}, predictions=[])
    frames=[]
    for test_week in WEEKS:
        wi=weeks.index(test_week)
        if wi < 5:
            raise ValueError(f'Insufficient history for test week {test_week}')
        validation_week=weeks[wi-3]
        calibration_weeks=weeks[wi-2:wi]
        train=data[data.week < validation_week]
        valid=data[data.week == validation_week]
        trees,tree_trials=choose_trees(train,valid)

        cal_frames=[];cal_p=[]
        for calibration_week in calibration_weeks:
            fit=data[data.week < calibration_week]
            target=data[data.week == calibration_week]
            p=fit_probability(fit,target,trees)
            cal_frames.append(target)
            cal_p.extend(p.tolist())
        cal=pd.concat(cal_frames,ignore_index=False)
        cal_y=cal.occupancy_rate.lt(.1).to_numpy(dtype=bool)
        selected,scan,policy=threshold_scan(cal_y,np.asarray(cal_p))

        final=data[data.week < test_week]
        test=data[data.week == test_week]
        test_p=fit_probability(final,test,trees)
        test_y=test.occupancy_rate.lt(.1).to_numpy(dtype=bool)
        outcome=metrics(test_y,test_p,selected['threshold'])
        frame=test[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['low_probability']=test_p
        frame['threshold']=selected['threshold']
        frame['low_alert']=test_p >= selected['threshold']
        frames.append(frame)
        report['rolling'][str(test_week)]=dict(
            train_weeks=sorted(map(int,train.week.unique())),
            validation_week=int(validation_week),
            calibration_weeks=list(map(int,calibration_weeks)),
            calibration_sessions=len(cal),
            calibration_actual_low=int(cal_y.sum()),
            calibration_policy=policy,
            selected_threshold=selected['threshold'],
            selected_calibration_metrics={k:selected[k] for k in ['precision','recall','f1','actual_positive','predicted_positive','tp','fp','fn']},
            threshold_scan=scan,tree_trials=tree_trials,selected_trees=trees,
            test_sessions=len(test),test_low_metrics=outcome)
        print('week',test_week,'threshold',selected['threshold'],'test P',round(outcome['precision'],4),
              'R',round(outcome['recall'],4),'F1',round(outcome['f1'],4),flush=True)
    pred=pd.concat(frames,ignore_index=True)
    pred.to_csv(OUT/'rolling_predictions.csv',index=False)
    report['pooled_test_metrics']=R.binary_metrics(pred.occupancy_rate.lt(.1),pred.low_alert)
    report['comparison_to_v7_policy']={
        'v7_report':'02、模型实验/生成产物/improvement_v7/report.json',
        'v7_pooled_metrics':json.loads((OUT.parent/'improvement_v7/report.json').read_text(encoding='utf-8'))['pooled_low'],
        'v9_pooled_metrics':report['pooled_test_metrics'],
        'v9_week12':report['rolling']['12']['test_low_metrics'],
        'criterion_2_week12_pass':bool(report['rolling']['12']['test_low_metrics']['f1']>=.6 or report['rolling']['12']['test_low_metrics']['precision']>=.65),
        'criterion_2_pooled_pass':bool(report['pooled_test_metrics']['f1']>=.6 or report['pooled_test_metrics']['precision']>=.65),
        'scope':'Historical prequential comparison only; not independent or prospective validation.'}
    report['sha256']={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__),Path(V7.__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'rolling_predictions.csv']}
    R.dump(OUT/'protocol.json',report['protocol'])
    R.dump(OUT/'report.json',report)
    print('SUMMARY',report['pooled_test_metrics'],report['comparison_to_v7_policy'],flush=True)
    return report


if __name__ == '__main__':
    run()
