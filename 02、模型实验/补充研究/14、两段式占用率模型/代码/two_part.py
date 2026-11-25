"""Experiment 14: two-part (hurdle) occupancy model built from each unified_v5 time fold's own earlier data.

Frozen protocol: 研究协议.json. p = formal stable_low probability (saved predictions), m0 = mean occupancy
of low sessions in the fold's regression training set, m1 = conditional regression fitted on held-like
sessions (occupancy >= 0.10) with the same LightGBM pipeline as the formal regression.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R

U = ROOT / '02、模型实验/生成产物/unified'
CURRENT_W12_RMSE = 0.1453332340425742


def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def fold(d, weeks, tw, saved):
    i = weeks.index(tw); vw, cw = weeks[i - 2:i]
    train, valid, final, test = d[d.week < vw], d[d.week.eq(vw)], d[d.week <= vw], d[d.week.eq(tw)]
    held = lambda x: x[x.occupancy_rate.ge(.1)]
    m0 = float(final.loc[final.occupancy_rate.lt(.1), 'occupancy_rate'].mean())
    m1, bundle, trials = R.fit_selected('LightGBM', held(train), held(valid), held(final), test)
    g = saved.set_index('session_id').loc[test.session_id].copy()
    if 'regression_prediction' in g: g['prediction'] = g.regression_prediction  # v6 stores the single regression separately
    p = g.low_probability.to_numpy()
    mean = p * m0 + (1 - p) * m1
    state = np.where(g.low_alert.to_numpy(), m0, m1)
    frame = pd.DataFrame(dict(session_id=test.session_id.to_numpy(), week=tw, occupancy_rate=test.occupancy_rate.to_numpy(),
        formal_prediction=g.prediction.to_numpy(), low_probability=p, low_alert=g.low_alert.to_numpy(),
        m0=m0, m1=m1, mean_prediction=mean, state_prediction=state))
    base = R.baselines(final, test); y = test.occupancy_rate.to_numpy()
    out = dict(m0=m0, m1_setting=bundle['setting'], held_train_rows=int(len(held(final))),
        rmse_formal=rmse(y, g.prediction), rmse_mean=rmse(y, mean), rmse_state=rmse(y, state),
        gains_mean={k: 1 - rmse(y, mean) / rmse(y, base[k]) for k in ('timetable_static', 'historical_mean')},
        gains_formal={k: 1 - rmse(y, g.prediction) / rmse(y, base[k]) for k in ('timetable_static', 'historical_mean')},
        screen_state=R.binary_metrics(y < .1, state < .1), screen_formal_regression=R.binary_metrics(y < .1, g.prediction.to_numpy() < .1),
        official_alert=R.binary_metrics(y < .1, g.low_alert.to_numpy()), m1_below_010=int((m1 < .1).sum()))
    return frame, out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = Path(__file__).with_name('研究协议.json')
    R.dump(OUT / '执行输入.json', dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    d = R.load(); weeks = sorted(d.week.unique()); saved = pd.read_csv(U / 'time_predictions.csv'); frames, report = [], dict(weekly={})
    for tw in (8, 10, 11, 12):
        f, o = fold(d, weeks, tw, saved); frames.append(f); report['weekly'][str(tw)] = o
        print(tw, 'RMSE formal %.4f mean %.4f' % (o['rmse_formal'], o['rmse_mean']), 'screen F1 %.3f' % o['screen_state']['f1'], 'm1<0.1:', o['m1_below_010'], flush=True)
    a = pd.concat(frames); a.to_csv(OUT / '逐课次两段式预测.csv', index=False); y = a.occupancy_rate.to_numpy()
    pooled_screen = R.binary_metrics(y < .1, a.state_prediction < .1); pooled_official = R.binary_metrics(y < .1, a.low_alert)
    w = report['weekly']
    checks_screen = dict(every_week_f1_060=all(v['screen_state']['f1'] >= .6 for v in w.values()),
                         pooled_f1_not_below_formal=pooled_screen['f1'] >= pooled_official['f1'] - 1e-12)
    checks_reg = dict(every_week_gains_010=all(min(v['gains_mean'].values()) >= .1 for v in w.values()),
                      week12_rmse_not_worse=w['12']['rmse_mean'] <= CURRENT_W12_RMSE,
                      pooled_rmse_not_worse=rmse(y, a.mean_prediction) <= rmse(y, a.formal_prediction))
    report.update(pooled=dict(rmse_formal=rmse(y, a.formal_prediction), rmse_mean=rmse(y, a.mean_prediction), rmse_state=rmse(y, a.state_prediction),
                              screen_state=pooled_screen, official_alert=pooled_official,
                              screen_formal_regression=R.binary_metrics(y < .1, a.formal_prediction < .1)),
                  checks_screening=checks_screen, adopt_screening=all(checks_screen.values()),
                  checks_regression=checks_reg, adopt_regression=all(checks_reg.values()),
                  sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ['02、模型实验/生成产物/unified/time_predictions.csv', '01、数据处理/清洗产物/sessions.csv']})
    R.dump(OUT / 'report.json', report)
    print(json.dumps(dict(pooled={k: (v if isinstance(v, float) else v['f1']) for k, v in report['pooled'].items()},
                          screening=checks_screen, regression=checks_reg), ensure_ascii=False))


if __name__ == '__main__':
    main()
