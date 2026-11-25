"""Fixed three-model vote with strictly earlier training; no week-specific search."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R
import stable_low as L
import calendar_context as C

def main():
    OUT.mkdir(parents=True,exist_ok=True);data=R.load();frames=[]
    protocol=Path(__file__).with_name('研究协议.json')
    R.dump(OUT/'执行输入.json',dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    for week in (8,10,11,12):
        low=joblib.load(ROOT/f'02、模型实验/生成产物/unified/fold_models/rolling_{week}.joblib')['low']
        reference=low['reference'];query=data[data.week.eq(week)]
        if reference.date.max()>=query.date.min():raise ValueError('Future fitting')
        x=L.features(reference,reference).fillna(low['median']);z=L.features(reference,query).fillna(low['median'])
        forest=RandomForestClassifier(n_estimators=200,min_samples_leaf=10,class_weight={0:1,1:2},random_state=42,n_jobs=2)
        forest.fit(x,reference.occupancy_rate.lt(.1));path=OUT/f'forest_{week}.joblib';joblib.dump(forest,path)
        a=low['logistic'].predict_proba(low['scaler'].transform(z))[:,1];b=low['trees'].predict_proba(z)[:,1];c=joblib.load(path).predict_proba(z)[:,1]
        frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['logistic_score']=a;frame['tree_score']=b;frame['forest_score']=c;frame['score']=np.median(np.stack([a,b,c]),axis=0)
        calendar=C.review_flag(query);frame['old_alert']=(a+b)/2>=.5;frame['old_alert']=frame.old_alert|calendar;frame['alert']=frame.score.ge(.5)|calendar;frames.append(frame)
        print('FIT',week,flush=True)
    f=pd.concat(frames,ignore_index=True);f.to_csv(OUT/'逐课次预测.csv',index=False)
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.alert) for w,g in f.groupby('week')}
    before={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.old_alert) for w,g in f.groupby('week')}
    pooled=R.binary_metrics(f.occupancy_rate.lt(.1),f.alert);old=R.binary_metrics(f.occupancy_rate.lt(.1),f.old_alert)
    loss=lambda m:3*m['confusion_tn_fp_fn_tp'][2]+m['confusion_tn_fp_fn_tp'][1]
    checks=dict(original2=all(m['f1']>=.6 or m['precision']>=.65 for m in weekly.values()),pooled_precision=pooled['precision']>=.65,
        misses_per_week=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=before[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),
        misses_reduced=pooled['recall']>old['recall'],review_loss_reduced=loss(pooled)<loss(old))
    report=dict(weekly=weekly,before=before,pooled=pooled,old_pooled=old,checks=checks,eligible=all(checks.values()),formal_changed=False,
        review_cost_assumption='3*FN+FP; research assumption, not measured school cost',loss=loss(pooled),old_loss=loss(old))
    R.dump(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
