"""V11: model-family search with worst-calibration-week precision control.

Before a test week, the chosen alert threshold must meet precision>=0.65 and
minimum support in each of the two earlier calibration weeks. If no threshold
is supported in both, the policy abstains and requires manual review.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

import revised as R
import improvement_v9 as V9
import improvement_v10 as V10

OUT=R.ROOT/'02、模型实验/生成产物/improvement_v11'
WEEKS=[8,10,11,12]
MIN_ALERTS_PER_WEEK=10


def choose_robust_threshold(cal_frames,cal_probs):
    thresholds=V9.THRESHOLDS
    rows=[]
    for threshold in thresholds:
        weekly=[]
        for frame,prob in zip(cal_frames,cal_probs):
            y=frame.occupancy_rate.lt(.1).to_numpy(dtype=bool);pred=np.asarray(prob)>=threshold
            tp=int(np.sum(y&pred));fp=int(np.sum(~y&pred));fn=int(np.sum(y&~pred));n=tp+fp
            weekly.append(dict(precision=tp/n if n else 0.,recall=tp/(tp+fn) if tp+fn else 0.,
                               alerts=n,tp=tp,fp=fp,fn=fn,actual=int(y.sum())))
        eligible=all(w['precision']>=.65 and w['alerts']>=MIN_ALERTS_PER_WEEK for w in weekly)
        rows.append(dict(threshold=threshold,eligible=eligible,weekly=weekly,
                         min_precision=min(w['precision'] for w in weekly),
                         mean_recall=float(np.mean([w['recall'] for w in weekly])),
                         total_alerts=sum(w['alerts'] for w in weekly)))
    eligible=[r for r in rows if r['eligible']]
    if not eligible:
        return None,rows,'abstain: no threshold has >=0.65 precision and >=10 alerts in both calibration weeks'
    selected=max(eligible,key=lambda r:(r['mean_recall'],r['min_precision'],r['total_alerts'],-r['threshold']))
    return selected,rows,'maximize mean recall subject to per-week calibration precision>=0.65 and >=10 alerts'


def metrics(y,alerts):
    return R.binary_metrics(np.asarray(y,dtype=bool),np.asarray(alerts,dtype=bool))


def run():
    OUT.mkdir(parents=True,exist_ok=True);d=R.load();weeks=sorted(map(int,d.week.unique()))
    report=dict(protocol=dict(name='v11 worst-week calibration precision and abstention',
        status='Retrospective diagnostic; all weeks previously inspected',
        model_selection='Same fixed model-family grid as V10, selected by validation average precision.',
        threshold='Threshold must meet precision>=0.65 and at least 10 alerts separately in both preceding calibration weeks. If none qualifies, emit no model alerts and direct to manual review.',
        target='Observed peak occupancy_rate<0.10, not empty, cancellation, or availability.',test_weeks=WEEKS,
        limitations=['Two past weeks cannot guarantee future precision','Abstention increases missed cases and manual workload',
                     'All evaluation weeks were previously inspected','No future-term or campus validation']),rolling={})
    frames=[]
    for test_week in WEEKS:
        wi=weeks.index(test_week);validation_week=weeks[wi-3];calibration_weeks=weeks[wi-2:wi]
        train=d[d.week<validation_week];valid=d[d.week==validation_week]
        selected,model_trials=V10.choose(train,valid)
        cal_frames=[];cal_probs=[]
        for cw in calibration_weeks:
            target=d[d.week==cw];fit=d[d.week<cw]
            cal_probs.append(V10.fit_predict(fit,target,selected));cal_frames.append(target)
        threshold_row,scan,policy=choose_robust_threshold(cal_frames,cal_probs)
        test=d[d.week==test_week];final=d[d.week<test_week]
        p=V10.fit_predict(final,test,selected)
        threshold=threshold_row['threshold'] if threshold_row else None
        alerts=(p>=threshold) if threshold is not None else np.zeros(len(test),dtype=bool)
        met=metrics(test.occupancy_rate.lt(.1),alerts)
        frame=test[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['low_probability']=p;frame['threshold']=threshold;frame['low_alert']=alerts
        frame['abstained']=threshold is None;frames.append(frame)
        report['rolling'][str(test_week)]=dict(validation_week=int(validation_week),calibration_weeks=list(map(int,calibration_weeks)),
            selected_candidate=list(selected),model_trials=model_trials,
            calibration_policy=policy,selected_threshold=threshold,calibration_threshold_scan=scan,
            test_sessions=len(test),abstained=threshold is None,test_metrics=met)
        print('week',test_week,'candidate',selected,'threshold',threshold,'abstained',threshold is None,
              'P',round(met['precision'],4),'R',round(met['recall'],4),'F1',round(met['f1'],4),flush=True)
    pred=pd.concat(frames,ignore_index=True);pred.to_csv(OUT/'rolling_predictions.csv',index=False)
    pooled=R.binary_metrics(pred.occupancy_rate.lt(.1),pred.low_alert);report['pooled_test_metrics']=pooled
    report['comparison']={'v7':json.loads((OUT.parent/'improvement_v7/report.json').read_text(encoding='utf-8'))['pooled_low'],
        'v10':json.loads((OUT.parent/'improvement_v10/report.json').read_text(encoding='utf-8'))['pooled_test_metrics'],
        'v11':pooled,'week12_gate':bool(report['rolling']['12']['test_metrics']['f1']>=.6 or report['rolling']['12']['test_metrics']['precision']>=.65),
        'pooled_gate':bool(pooled['f1']>=.6 or pooled['precision']>=.65),
        'abstained_weeks':[w for w,r in report['rolling'].items() if r['abstained']]}
    report['sha256']={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),Path(V10.__file__),Path(V9.__file__),Path(V9.V7.__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'rolling_predictions.csv']}
    R.dump(OUT/'protocol.json',report['protocol']);R.dump(OUT/'report.json',report)
    print('SUMMARY',report['comparison'],flush=True);return report


if __name__=='__main__':run()
