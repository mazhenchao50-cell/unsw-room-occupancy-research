"""Experiment 22 (in folder 16): 2018 evaluation using 2017 information only, for an equal-information
comparison with the original paper. Frozen protocol: 研究协议_同等信息.json."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import holdout_2018 as H

OUT = HERE.parent / '生成产物'
PROTOCOL = HERE / '研究协议_同等信息.json'


def main():
    d = H.R.load(); b = H.build_2018(d)
    train, valid, final, cal = d[d.week < 11], d[d.week.eq(11)], d[d.week <= 11], d[d.week.eq(12)]
    bundle = H.U.make_bundle(train, valid, final, cal, 13, d)
    H.C.review_flag = H.patched_review_flag(H.C.review_flag)
    for part in ('warm', 'cond', 'low', 'context'): bundle[part]['reference'] = d     # 2017 information only
    pred = H.U.predict_bundle(bundle, b)
    base = H.R.baselines(d, b)
    f = b[['session_id', 'week', 'course_id', 'seats', 'enrollments', 'attendees', 'occupancy_rate']].merge(pred, on='session_id', validate='one_to_one')
    f['timetable_static'] = base['timetable_static']; f['historical_mean'] = base['historical_mean']
    na = f.attendees / f.enrollments; keep = f.enrollments.gt(0) & na.le(1.5); y = na[keep].clip(upper=1)
    scale = lambda c: (f[c] * f.seats / f.enrollments)[keep].clip(0, 1)
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), n=int(len(f)), n_paper_scale=int(keep.sum()),
        occupancy_rmse={c: H.rmse(f.occupancy_rate, f[c]) for c in ('prediction', 'regression_prediction', 'timetable_static', 'historical_mean')},
        paper_scale_rmse=dict(unified_v6=H.rmse(y, scale('prediction')), single_regression=H.rmse(y, scale('regression_prediction'))),
        paper_table_v_ds3=H.PAPER_DS3)
    report['occupancy_gains'] = {c: 1 - report['occupancy_rmse']['prediction'] / report['occupancy_rmse'][c] for c in ('timetable_static', 'historical_mean')}
    best = min(report['paper_scale_rmse'].values())
    report['claim_not_worse_than_paper_rf'] = bool(best <= H.PAPER_DS3['RF'])
    (OUT / 'equal_info.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print('SUMMARY', json.dumps(report, ensure_ascii=False, default=float))


if __name__ == '__main__':
    main()
