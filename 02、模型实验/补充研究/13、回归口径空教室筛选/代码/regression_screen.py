"""Experiment 13: regression-based empty-room screening with a threshold chosen on the earlier calibration week.

Frozen protocol: 研究协议.json. Uses the saved unified_v5 rolling fold models (no retraining).
For test week tw, the calibration week cw is the week immediately before tw in the cohort; the fold's
warm model was fitted on weeks <= vw < cw, so its cw predictions are out-of-sample.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R

U = ROOT / '02、模型实验/生成产物/unified'
GRID = [round(x, 2) for x in np.arange(.08, .2501, .01)]


def choose(y, p):
    scores = [(R.binary_metrics(y, p < t)['f1'], -t, t) for t in GRID]
    return max(scores)[2], {str(t): R.binary_metrics(y, p < t)['f1'] for t in GRID}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = Path(__file__).with_name('研究协议.json')
    R.dump(OUT / '执行输入.json', dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    d = R.load(); weeks = sorted(d.week.unique()); f = pd.read_csv(U / 'time_predictions.csv'); rows = []; report = dict(weekly={})
    for tw in (8, 10, 11, 12):
        i = weeks.index(tw); vw, cw = weeks[i - 2:i]
        bundle = joblib.load(U / f'fold_models/rolling_{tw}.joblib'); warm = bundle['warm']
        assert pd.to_datetime(warm['reference'].date).max() < pd.to_datetime(d[d.week.eq(cw)].date).min()
        cal = d[d.week.eq(cw)]; pc = R.predict(warm, cal); tau, curve = choose(cal.occupancy_rate.lt(.1), pc)
        test = f[f.week.eq(tw)].copy(); y = test.occupancy_rate.lt(.1)
        if 'regression_prediction' in test: test['prediction'] = test.regression_prediction  # v6: single regression kept here
        test['screen_literal'] = test.prediction.lt(.1); test['screen_calibrated'] = test.prediction.lt(tau); test['tau'] = tau
        rows.append(test[['session_id', 'week', 'room', 'occupancy_rate', 'prediction', 'tau', 'screen_literal', 'screen_calibrated']])
        report['weekly'][str(tw)] = dict(calibration_week=int(cw), tau=tau, calibration_f1_curve=curve,
            literal=R.binary_metrics(y, test.screen_literal), calibrated=R.binary_metrics(y, test.screen_calibrated))
        m = report['weekly'][str(tw)]['calibrated']
        print(tw, 'cw', cw, 'tau', tau, 'P %.3f R %.3f F1 %.3f' % (m['precision'], m['recall'], m['f1']), flush=True)
    allp = pd.concat(rows); allp.to_csv(OUT / '逐课次筛选.csv', index=False); y = allp.occupancy_rate.lt(.1)
    pooled = R.binary_metrics(y, allp.screen_calibrated)
    checks = dict(every_week_f1_060=all(v['calibrated']['f1'] >= .6 for v in report['weekly'].values()),
                  pooled_f1_065=pooled['f1'] >= .65, pooled_precision_065=pooled['precision'] >= .65, thresholds_from_earlier_weeks=True)
    report.update(pooled_literal=R.binary_metrics(y, allp.screen_literal), pooled_calibrated=pooled, checks=checks,
                  eligible=all(checks.values()), formal_alert_rule_changed=False,
                  sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                          ['02、模型实验/生成产物/unified/time_predictions.csv'] + [f'02、模型实验/生成产物/unified/fold_models/rolling_{w}.joblib' for w in (8, 10, 11, 12)]})
    R.dump(OUT / 'report.json', report)
    print(json.dumps(dict(pooled=dict(P=pooled['precision'], R=pooled['recall'], F1=pooled['f1']), checks=checks), ensure_ascii=False))


if __name__ == '__main__':
    main()
