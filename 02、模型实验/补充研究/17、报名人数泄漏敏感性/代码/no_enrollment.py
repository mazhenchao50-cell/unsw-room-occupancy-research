"""Experiment 17: rerun unified_v6 with enrollment information removed (enrollments := seats).

Frozen protocol: 研究协议.json. Same code, folds, selection and thresholds as the formal model; only the
input column changes. Baselines are computed from the original data so the comparators are unchanged.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议.json')
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import unified as U


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), rolling={}, spatial={})
    d = R.load(); weeks = sorted(d.week.unique())
    a = d.copy(); a['enrollments'] = a['seats'].astype(float)   # no enrollment information
    frames = []
    for tw in [8, 10, 11, 12]:
        i = weeks.index(tw); vw, cw = weeks[i - 2:i]
        split = lambda x: (x[x.week < vw], x[x.week.eq(vw)], x[x.week <= vw], x[x.week.eq(cw)], x[x.week.eq(tw)])
        train, valid, final, cal, test = split(a)
        bundle = U.make_bundle(train, valid, final, cal, tw, a); pred = U.predict_bundle(bundle, test)
        f = test[['session_id', 'week', 'occupancy_rate']].merge(pred, on='session_id', validate='one_to_one'); frames.append(f)
        o_final, o_test = split(d)[2], split(d)[4]
        base = R.baselines(o_final, o_test)
        met = R.metrics(f.occupancy_rate, f.prediction)
        report['rolling'][str(tw)] = dict(regression=met, low=R.binary_metrics(f.occupancy_rate.lt(.1), f.low_alert),
            baseline_gains={k: 1 - met['rmse'] / R.metrics(o_test.occupancy_rate, base[k])['rmse'] for k in ('timetable_static', 'historical_mean')})
        print('time', tw, round(met['rmse'], 4), round(report['rolling'][str(tw)]['low']['f1'], 4), flush=True)
    f = pd.concat(frames); f.to_csv(OUT / '逐课次预测_无报名人数.csv', index=False, encoding='utf-8-sig')
    report['pooled'] = dict(regression=R.metrics(f.occupancy_rate, f.prediction), low=R.binary_metrics(f.occupancy_rate.lt(.1), f.low_alert))
    for room in U.ROOMS:
        reference, query = a[a.room.ne(room)], a[a.room.eq(room)]
        cold = U.fit_cold(reference); p = U.predict_cold(cold, query)
        report['spatial'][room] = dict(rmse=R.metrics(query.occupancy_rate, p)['rmse'], selected=cold['selected'])
        print('room', room, round(report['spatial'][room]['rmse'], 4), flush=True)
    macro = float(np.mean([v['rmse'] for v in report['spatial'].values()]))
    formal = json.loads((ROOT / '02、模型实验/生成产物/unified/report.json').read_text(encoding='utf-8'))
    w12 = report['rolling']['12']
    report['gates_without_enrollment'] = dict(regression=all(g >= .1 for g in w12['baseline_gains'].values()),
        low=bool(w12['low']['f1'] >= .6 or w12['low']['precision'] >= .65), spatial=bool(macro <= .18), macro_rmse=macro)
    report['formal'] = dict(w12_rmse=formal['rolling']['12']['regression']['rmse'], w12_f1=formal['rolling']['12']['low']['f1'],
        macro_rmse=formal['spatial_summary']['macro_rmse'], w12_gains=formal['rolling']['12']['baseline_gains'])
    report['claim'] = 'robust' if all(report['gates_without_enrollment'][k] for k in ('regression', 'low', 'spatial')) else 'depends_on_enrollment'
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print('SUMMARY', json.dumps(dict(gates=report['gates_without_enrollment'], formal=report['formal'],
        w12=dict(rmse=w12['regression']['rmse'], f1=w12['low']['f1'], gains=w12['baseline_gains']),
        pooled=dict(rmse=report['pooled']['regression']['rmse'], f1=report['pooled']['low']['f1']), claim=report['claim']), default=float))


if __name__ == '__main__':
    main()
