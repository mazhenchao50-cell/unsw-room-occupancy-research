"""Single early calibration, frozen across subsequent weeks; no outer-score selection."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R
import stable_low as L
import calendar_context as C

def f2(m):
    p,r=m['precision'],m['recall']
    return 5*p*r/(4*p+r) if 4*p+r else 0.

def choose(frame):
    if set(frame.week)!={5,6,7} or not frame.session_id.is_unique:raise ValueError('Only complete early calibration folds')
    trials=[]
    for threshold in (.25,.35,.45,.55,.65):
        weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.score.ge(threshold)) for w,g in frame.groupby('week')}
        pooled=R.binary_metrics(frame.occupancy_rate.lt(.1),frame.score.ge(threshold))
        trials.append(dict(threshold=threshold,weekly=weekly,pooled=pooled,min_f2=min(f2(m) for m in weekly.values()),
            eligible=pooled['precision']>=.65 and min(m['precision'] for m in weekly.values())>=.5 and pooled['predicted_positive']>=20))
    eligible=[x for x in trials if x['eligible']]
    best=max(eligible,key=lambda x:(x['min_f2'],f2(x['pooled']),x['threshold'])) if eligible else dict(threshold=.5)
    return best,trials

def main():
    OUT.mkdir(parents=True,exist_ok=True);data=R.load();cal=[]
    protocol=Path(__file__).with_name('研究协议.json')
    R.dump(OUT/'执行输入.json',dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    for week in (5,6,7):
        reference=data[data.week.lt(week)];query=data[data.week.eq(week)]
        bundle=L.fit_bundle(reference);p=L.predict_bundle(bundle,query)['probability']
        frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy();frame['score']=p;cal.append(frame)
    calibration=pd.concat(cal,ignore_index=True);calibration.to_csv(OUT/'早期校准逐课次.csv',index=False);best,trials=choose(calibration)
    chosen=[]
    for week in (8,10,11,12):
        bundle=joblib.load(ROOT/f'02、模型实验/生成产物/unified/fold_models/rolling_{week}.joblib')
        query=data[data.week.eq(week)]
        if calibration.date.max()>=query.date.min():raise ValueError('Future calibration')
        frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy();pred=L.predict_bundle(bundle['low'],query)
        frame['score']=pred['probability'];frame['old_alert']=pred['alert'];frame['threshold']=best['threshold'];frame['calendar_review']=C.review_flag(query)
        frame['alert']=frame.score.ge(best['threshold'])|frame.calendar_review;chosen.append(frame)
    result=pd.concat(chosen,ignore_index=True);result.to_csv(OUT/'固定阈值逐课次.csv',index=False)
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.alert) for w,g in result.groupby('week')}
    before={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.old_alert) for w,g in result.groupby('week')}
    pooled=R.binary_metrics(result.occupancy_rate.lt(.1),result.alert);old=R.binary_metrics(result.occupancy_rate.lt(.1),result.old_alert)
    checks=dict(original2=all(m['f1']>=.6 or m['precision']>=.65 for m in weekly.values()),pooled_precision=pooled['precision']>=.65,
        misses_per_week=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=before[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),
        misses_reduced=pooled['confusion_tn_fp_fn_tp'][2]<old['confusion_tn_fp_fn_tp'][2])
    report=dict(threshold=best['threshold'],early_calibration=best,trials=trials,weekly=weekly,before=before,pooled=pooled,old_pooled=old,
        checks=checks,eligible=all(checks.values()),formal_changed=False)
    R.dump(OUT/'report.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('trials','early_calibration')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
