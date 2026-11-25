"""Chronological bounded precision-constrained calibration; retrospective study."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R

GRID=[.30,.35,.40,.45,.50,.55,.60]


def choose(calibration, previous):
    if calibration.empty or not calibration.session_id.is_unique:
        raise ValueError('Unique earlier calibration predictions required')
    if not np.isfinite(calibration.probability).all():raise ValueError('Invalid probability')
    trials=[]
    for threshold in GRID:
        pooled=R.binary_metrics(calibration.occupancy_rate.lt(.1),calibration.probability.ge(threshold))
        weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.probability.ge(threshold)) for w,g in calibration.groupby('week')}
        trials.append(dict(threshold=threshold,pooled=pooled,weekly=weekly,
            eligible=pooled['precision']>=.70 and pooled['predicted_positive']>=20 and all(m['precision']>=.50 for m in weekly.values())))
    eligible=[r for r in trials if r['eligible']]
    selected=max(eligible,key=lambda r:(r['pooled']['recall'],r['pooled']['f1'],r['threshold']))['threshold'] if eligible else .50
    threshold=round(float(np.clip(selected,previous-.10,previous+.10)),2)
    return threshold,dict(selected_before_bound=selected,previous=previous,trials=trials,
                           fallback=not bool(eligible),final_threshold=threshold)


def evaluate(frame):
    frame=frame.copy();weeks=sorted(frame.week.unique());previous=.50;rows=[];decisions={}
    for week in weeks:
        earlier=[w for w in weeks if w<week][-3:]
        if len(earlier)<3:threshold=.50;detail=dict(initialization=True)
        else:
            cal=frame[frame.week.isin(earlier)]
            query=frame[frame.week.eq(week)]
            if pd.to_datetime(cal.date).max()>=pd.to_datetime(query.date).min():raise ValueError('Future calibration leakage')
            threshold,detail=choose(cal,previous)
        query=frame[frame.week.eq(week)].copy();query['threshold']=threshold
        query['alert']=query.probability.ge(threshold);rows.append(query);previous=threshold
        decisions[str(int(week))]=dict(calibration_weeks=[int(w) for w in earlier],**detail)
    return pd.concat(rows,ignore_index=True),decisions


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=Path(__file__).parent/'冻结协议.json'
    if not protocol.exists():raise ValueError('Write the protocol before evaluation')
    source=ROOT/'02、模型实验/补充研究/02、漏报与跨周稳定性/生成产物/recent_prequential.csv'
    frame=pd.read_csv(source);data=R.load();expected=data[data.week.ge(3)]
    assert frame.session_id.is_unique and set(frame.session_id)==set(expected.session_id)
    aligned=expected.set_index('session_id').loc[frame.session_id]
    np.testing.assert_allclose(aligned.occupancy_rate,frame.occupancy_rate,atol=0,rtol=0)
    results,decisions=evaluate(frame);test=results[results.week.isin([8,10,11,12])]
    assert len(test)==815 and test.session_id.is_unique
    pooled=R.binary_metrics(test.occupancy_rate.lt(.1),test.alert)
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.alert) for w,g in test.groupby('week')}
    checks=dict(week12_misses_at_most_25=weekly['12']['confusion_tn_fp_fn_tp'][2]<=25,
        pooled_precision_at_least_065=pooled['precision']>=.65,pooled_recall_at_least_060=pooled['recall']>=.60,
        every_week_original_gate=all(m['f1']>=.60 or m['precision']>=.65 for m in weekly.values()),
        every_week_recall_at_least_050=all(m['recall']>=.50 for m in weekly.values()))
    report=dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),pooled=pooled,weekly=weekly,decisions=decisions,
        checks=checks,passed=all(checks.values()),current_model_changed=False,
        evaluation_type='Replay of previously generated strictly chronological fixed-model probabilities; full fitting replay required before adoption.',
        sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source,protocol]})
    test.to_csv(OUT/'逐会话评估.csv',index=False);R.dump(OUT/'report.json',report)
    print(json.dumps(dict(pooled=pooled,weekly=weekly,checks=checks,thresholds={str(int(w)):float(g.threshold.iloc[0]) for w,g in test.groupby('week')}),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
