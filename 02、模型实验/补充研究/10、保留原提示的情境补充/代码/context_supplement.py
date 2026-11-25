"""Retain original alerts while adding a separately identified contextual vote."""
from pathlib import Path
import json,hashlib,sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R

def main():
    OUT.mkdir(parents=True,exist_ok=True);protocol=Path(__file__).with_name('研究协议.json')
    R.dump(OUT/'执行输入.json',dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    source=ROOT/'02、模型实验/补充研究/09、日历情境历史/生成产物/逐课次预测.csv';f=pd.read_csv(source)
    original=pd.read_csv(ROOT/'02、模型实验/生成产物/unified/time_predictions.csv')
    if set(original.session_id)!=set(f.session_id) or not f.session_id.is_unique:raise ValueError('Changed cohort')
    f['context_alert']=f.alert;f['alert']=f.context_alert|f.old_alert;f['newly_reviewed']=f.alert&~f.old_alert
    f.to_csv(OUT/'逐课次预测.csv',index=False);f[f.newly_reviewed].to_csv(OUT/'新增复核课次.csv',index=False)
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.alert) for w,g in f.groupby('week')}
    before={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.old_alert) for w,g in f.groupby('week')}
    pooled=R.binary_metrics(f.occupancy_rate.lt(.1),f.alert);old=R.binary_metrics(f.occupancy_rate.lt(.1),f.old_alert)
    loss=lambda m:3*m['confusion_tn_fp_fn_tp'][2]+m['confusion_tn_fp_fn_tp'][1]
    checks=dict(original2=all(m['f1']>=.6 or m['precision']>=.65 for m in weekly.values()),
        every_week_f1_065=all(m['f1']>=.65 for m in weekly.values()),every_week_recall_065=all(m['recall']>=.65 for m in weekly.values()),
        pooled_precision=pooled['precision']>=.65,misses_per_week=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=before[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),
        misses_reduced=pooled['recall']>old['recall'],review_loss_reduced=loss(pooled)<loss(old))
    report=dict(weekly=weekly,before=before,pooled=pooled,old_pooled=old,checks=checks,eligible=all(checks.values()),formal_changed=False,
        new_review_count=int(f.newly_reviewed.sum()),new_true_low=int((f.newly_reviewed&f.occupancy_rate.lt(.1)).sum()),loss=loss(pooled),old_loss=loss(old))
    R.dump(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
