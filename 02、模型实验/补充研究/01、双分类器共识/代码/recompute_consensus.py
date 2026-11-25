"""Recompute fixed agreement policies from complete chronological predictions.

Supplementary retrospective analysis, separate from the deployed UI and the
extended rebuild. No thresholds or per-test-week winners are selected here.
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p/'01、数据处理').is_dir())
sys.path.insert(0, str(ROOT/'02、模型实验/代码/models'))
import revised as R

OUT = HERE.parents[1]/'生成产物'
WEEKS = (8, 10, 11, 12)

def combine(a, b):
    """Label-independent fixed policy; disagreement is review, not a low alert."""
    if a.dtype != bool or b.dtype != bool:
        raise ValueError('Require explicit boolean base alerts')
    return a & b, np.where(a & b, 'priority_review',
                         np.where(a | b, 'disagreement_review', 'no_alert'))

def run():
    product=ROOT/'02、模型实验/生成产物'
    files=[product/f'improvement_v{v}/rolling_predictions.csv' for v in (7,10)]
    inputs=[pd.read_csv(p) for p in files]
    truth=R.load();truth=truth[truth.week.isin(WEEKS)].set_index('session_id').sort_index()
    for f in inputs:
        if not f.session_id.is_unique or set(f.session_id)!=set(truth.index):
            raise ValueError('Incomplete or duplicate session coverage')
        f.set_index('session_id',inplace=True);f.sort_index(inplace=True)
        for name in ('room','course_id','week'):
            if not f[name].equals(truth[name]):raise ValueError('Metadata mismatch: '+name)
        if not np.array_equal(pd.to_datetime(f.date),pd.to_datetime(truth.date)):
            raise ValueError('Date mismatch')
        np.testing.assert_allclose(f.occupancy_rate,truth.occupancy_rate,rtol=0,atol=1e-12)
        if f.low_alert.dtype != bool:raise ValueError('Ambiguous alert type')
        if not np.array_equal(f.low_alert, f.low_probability >= f.threshold):
            raise ValueError('Stored alert differs from stored prior-week threshold')
    a,b=inputs
    consensus,tier=combine(a.low_alert.to_numpy(),b.low_alert.to_numpy())
    # These checks exercise the policy independently of labels and row order.
    np.testing.assert_array_equal(combine(np.array([False,False,True,True]),
        np.array([False,True,False,True]))[0],[False,False,False,True])
    np.testing.assert_array_equal(combine(a.low_alert.to_numpy()[::-1],
        b.low_alert.to_numpy()[::-1])[0][::-1],consensus)
    f=truth[['date','room','course_id','week','occupancy_rate']].copy()
    f['v7_alert']=a.low_alert;f['v10_alert']=b.low_alert
    f['consensus_alert']=consensus;f['review_tier']=tier
    reports={}
    for name,pred in [('v7',a.low_alert),('v10',b.low_alert),
                      ('consensus',pd.Series(consensus,index=f.index)),
                      ('either',a.low_alert|b.low_alert)]:
        weekly={str(w):R.binary_metrics(f.loc[f.week.eq(w),'occupancy_rate']<.1,
                                      pred.loc[f.week.eq(w)]) for w in WEEKS}
        pooled=R.binary_metrics(f.occupancy_rate<.1,pred)
        passes=lambda m: bool(m['precision']>=.65 or m['f1']>=.60)
        reports[name]=dict(pooled=pooled,weekly=weekly,pooled_gate=passes(pooled),
            weekly_gates={w:passes(m) for w,m in weekly.items()})
    report=dict(protocol='Fixed V7 AND V10 alerts; OR retained as comparison; no test-week switching.',
        status='Exploratory historical candidate; not adopted in the app',
        n=len(f),comparisons=reports,
        tier_counts=f.review_tier.value_counts().to_dict(),
        adoption=dict(default_changed=False,app_changed=False,
            reason='Consensus reduces false positives but loses true positives; retain separate review tiers and expose misses.'),
        limitations=['All four weeks previously inspected; method choice is retrospective',
            'Wilson intervals ignore repeated-course dependence and selection; not a future guarantee',
            'No alert does not establish normal use; disagreement does not establish low use',
            'No inherited regression or spatial superiority; these base branches are unchanged'],
        checks=['815 aligned unique sessions','metadata and truth match','thresholds reproduce alerts',
                'boolean truth table','row permutation invariance'])
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/'逐会话核查分层.csv';f.reset_index().to_csv(target,index=False,encoding='utf-8-sig')
    sources=[HERE,Path(R.__file__),ROOT/'01、数据处理/清洗产物/sessions.csv',*files,target]
    report['sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    R.dump(OUT/'report.json',report)
    print(json.dumps(reports['consensus'],ensure_ascii=False))

if __name__=='__main__':run()
