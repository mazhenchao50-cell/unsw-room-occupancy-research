"""Test independently sourced calendar context without changing labels or regression."""
from pathlib import Path
import hashlib
import json
import sys
import argparse
import os
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--calendar-dir',type=Path,
        default=Path(os.environ.get('UNSW_CALENDAR_DIR',str(ROOT.parent/'11、运行环境与验证存档（原D盘）/2、外部来源证据/学期日历原件_20261117'))))
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((Path(__file__).parent/'冻结协议.json').read_text(encoding='utf-8'))
    protocol['calendar']['local_originals']=str(args.calendar_dir.resolve())
    R.dump(OUT/'冻结协议.json',protocol)
    for name,expected in protocol['calendar']['sha256'].items():
        p=args.calendar_dir/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
    source=ROOT/'02、模型实验/补充研究/02、漏报与跨周稳定性/生成产物/recent_prequential.csv'
    frame=pd.read_csv(source);frame=frame[frame.week.isin([8,10,11,12])].copy()
    data=R.load();truth=data[data.week.isin([8,10,11,12])]
    assert frame.session_id.is_unique and set(frame.session_id)==set(truth.session_id) and len(frame)==815
    np.testing.assert_allclose(frame.occupancy_rate,truth.set_index('session_id').loc[frame.session_id].occupancy_rate,rtol=0,atol=0)
    frame['calendar_review']=frame.date.isin(protocol['calendar']['statewide_public_holidays'])
    frame['model_alert']=frame.ensemble.ge(.50)
    frame['alert']=frame.model_alert|frame.calendar_review
    summaries={}
    for name,col in [('classifier_only','model_alert'),('combined','alert')]:
        pooled=R.binary_metrics(frame.occupancy_rate.lt(.1),frame[col])
        weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g[col]) for w,g in frame.groupby('week')}
        summaries[name]=dict(pooled=pooled,weekly=weekly)
    pooled=summaries['combined']['pooled'];weekly=summaries['combined']['weekly']
    checks=dict(week12_misses_at_most_25=weekly['12']['confusion_tn_fp_fn_tp'][2]<=25,
        pooled_precision_at_least_065=pooled['precision']>=.65,pooled_recall_at_least_060=pooled['recall']>=.60,
        every_week_original_gate=all(m['f1']>=.60 or m['precision']>=.65 for m in weekly.values()),
        every_week_recall_at_least_050=all(m['recall']>=.50 for m in weekly.values()))
    report=dict(protocol=protocol,summaries=summaries,checks=checks,passed=all(checks.values()),
        calendar_rows=int(frame.calendar_review.sum()),calendar_added_alerts=int((frame.calendar_review&~frame.model_alert).sum()),
        current_model_changed=False,requires_fresh_training=True,
        sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,Path(__file__),OUT/'冻结协议.json']})
    frame.to_csv(OUT/'逐会话评估.csv',index=False);R.dump(OUT/'report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
