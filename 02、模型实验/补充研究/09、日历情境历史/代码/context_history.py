"""Keep all observations; condition strictly earlier history on known day context."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R
import calendar_context as C
from context_low import features,fit,predict

def main():
    OUT.mkdir(parents=True,exist_ok=True);data=R.load();frames=[]
    protocol=Path(__file__).with_name('研究协议.json')
    R.dump(OUT/'执行输入.json',dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    original=pd.read_csv(ROOT/'02、模型实验/生成产物/unified/time_predictions.csv').set_index('session_id')
    original['baseline_alert']=original.model_alert|original.calendar_review
    for week in (8,10,11,12):
        ref=data[data.week.lt(week)];query=data[data.week.eq(week)];bundle=fit(ref);path=OUT/f'model_{week}.joblib';joblib.dump(bundle,path)
        score=predict(joblib.load(path),query);frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['score']=score;frame['alert']=score>=.5;frame['alert']=frame.alert|C.review_flag(query)
        frame['old_alert']=original.loc[frame.session_id,'baseline_alert'].to_numpy();frames.append(frame);print('FIT',week,flush=True)
    f=pd.concat(frames,ignore_index=True);f.to_csv(OUT/'逐课次预测.csv',index=False)
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.alert) for w,g in f.groupby('week')}
    before={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.old_alert) for w,g in f.groupby('week')}
    pooled=R.binary_metrics(f.occupancy_rate.lt(.1),f.alert);old=R.binary_metrics(f.occupancy_rate.lt(.1),f.old_alert)
    loss=lambda m:3*m['confusion_tn_fp_fn_tp'][2]+m['confusion_tn_fp_fn_tp'][1]
    checks=dict(original2=all(m['f1']>=.6 or m['precision']>=.65 for m in weekly.values()),pooled_precision=pooled['precision']>=.65,
        misses_per_week=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=before[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),
        misses_reduced=pooled['recall']>old['recall'],review_loss_reduced=loss(pooled)<loss(old),worst_week_f1=min(m['f1'] for m in weekly.values())>=min(m['f1'] for m in before.values()))
    report=dict(weekly=weekly,before=before,pooled=pooled,old_pooled=old,checks=checks,eligible=all(checks.values()),formal_changed=False,loss=loss(pooled),old_loss=loss(old))
    R.dump(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
