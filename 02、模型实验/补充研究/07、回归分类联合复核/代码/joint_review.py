"""One fixed cross-task confirmation rule; all outer predictions retained."""
from pathlib import Path
import sys,json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R

def main():
    OUT.mkdir(parents=True,exist_ok=True);protocol=Path(__file__).with_name('研究协议.json')
    R.dump(OUT/'执行输入.json',dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    source=ROOT/'02、模型实验/生成产物/unified/time_predictions.csv';f=pd.read_csv(source)
    expected=R.load();expected=expected[expected.week.isin([8,10,11,12])]
    if not f.session_id.is_unique or set(f.session_id)!=set(expected.session_id):raise ValueError('Changed cohort')
    f['old_alert']=f.model_alert|f.calendar_review
    # v6 keeps the single regression in regression_prediction; this experiment is defined on it.
    single=f.regression_prediction if 'regression_prediction' in f else f.prediction
    f['regression_review']=single.lt(.1)&f.low_probability.ge(.25)
    f['joint_alert']=f.old_alert|f.regression_review
    f['newly_reviewed']=f.joint_alert&~f.old_alert
    f.to_csv(OUT/'联合复核逐课次.csv',index=False);f[f.newly_reviewed].to_csv(OUT/'新增复核课次.csv',index=False)
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.joint_alert) for w,g in f.groupby('week')}
    before={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.old_alert) for w,g in f.groupby('week')}
    pooled=R.binary_metrics(f.occupancy_rate.lt(.1),f.joint_alert);old=R.binary_metrics(f.occupancy_rate.lt(.1),f.old_alert)
    checks=dict(original2=all(m['f1']>=.6 or m['precision']>=.65 for m in weekly.values()),pooled_precision=pooled['precision']>=.65,
        misses_per_week=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=before[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),misses_reduced=pooled['recall']>old['recall'])
    report=dict(weekly=weekly,before=before,pooled=pooled,old_pooled=old,checks=checks,eligible=all(checks.values()),formal_changed=False,
        new_review_count=int(f.newly_reviewed.sum()),new_true_low=int((f.newly_reviewed&f.occupancy_rate.lt(.1)).sum()),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    cost=lambda m:3*m['confusion_tn_fp_fn_tp'][2]+m['confusion_tn_fp_fn_tp'][1]
    report.update(cost_assumption='3*FN+FP',candidate_cost=cost(pooled),old_cost=cost(old),
        deployment_review='Registered numeric checks pass, but added false alerts exceed benefit under the stated 3:1 cost. Not adopted.' if all(checks.values()) and cost(pooled)>=cost(old) else 'Inspect all registered checks and costs; no automatic deployment.')
    R.dump(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
