"""Experiment 23: calibrate the first-stage probability p of the formal two-part occupancy model.

Frozen protocol: 研究协议.json (hash in report). Out-of-sample scores come from the formal stable_low recipe
refitted on strictly earlier weeks only; the test-week calibrator never sees the test week. Alerts are unchanged.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议.json')
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import stable_low as LOW

U = ROOT / '02、模型实验/生成产物/unified'
TEST_WEEKS = [8, 10, 11, 12]
FIRST_CAL_WEEK = 4
EPS = 1e-6
METHODS = ('original', 'platt', 'isotonic')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2)))
def logit(p): p = np.clip(np.asarray(p, float), EPS, 1 - EPS); return np.log(p / (1 - p))


def prob_metrics(y, p):
    y = np.asarray(y, float); p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).sum() for b in np.unique(bins)) / len(y)
    return dict(n=int(len(y)), brier=float(np.mean((p - y) ** 2)), log_loss=float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
                ece=float(ece), mean_p=float(p.mean()), prevalence=float(y.mean()), mean_p_minus_prevalence=float(p.mean() - y.mean()))


def out_of_sample_scores(d):
    """For each week w >= 4 (week 9 already excluded), fit the formal classifier on weeks < w and score week w."""
    rows, skipped = [], {}
    for w in sorted(d.week.unique()):
        if w < FIRST_CAL_WEEK or w >= max(TEST_WEEKS):
            continue
        query = d[d.week.eq(w)]
        try:
            bundle = LOW.fit_bundle(d[d.week.lt(w)])
            p = LOW.predict_bundle(bundle, query)['probability']
        except ValueError as exc:
            skipped[int(w)] = str(exc); continue
        rows.append(pd.DataFrame(dict(session_id=query.session_id.to_numpy(), week=int(w), p=p, y=query.occupancy_rate.lt(.1).to_numpy())))
        print('scored week', int(w), len(query), flush=True)
    return pd.concat(rows, ignore_index=True), skipped


def fit_platt(cal):
    model = LogisticRegression(C=1e6, max_iter=1000).fit(logit(cal.p).reshape(-1, 1), cal.y)
    return (lambda p: model.predict_proba(logit(p).reshape(-1, 1))[:, 1]), dict(coef=float(model.coef_[0, 0]), intercept=float(model.intercept_[0]))


def fit_isotonic(cal):
    model = IsotonicRegression(out_of_bounds='clip', y_min=0., y_max=1.).fit(cal.p, cal.y.astype(float))
    return model.predict


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = R.load(); saved = pd.read_csv(U / 'time_predictions.csv').set_index('session_id')
    oos, skipped = out_of_sample_scores(d)
    oos.to_csv(OUT / '样本外分数.csv', index=False, encoding='utf-8-sig')
    weekly, frames = {}, []
    for t in TEST_WEEKS:
        bundle = joblib.load(U / f'fold_models/rolling_{t}.joblib'); m0 = float(bundle['low_mean'])
        test = d[d.week.eq(t)]; g = saved.loc[test.session_id]
        y = test.occupancy_rate.to_numpy(); low = y < .1
        p = g.low_probability.to_numpy(); m1 = g.held_prediction.to_numpy()
        e0 = p * m0 + (1 - p) * m1
        if np.max(np.abs(e0 - g.prediction.to_numpy())) > 1e-12:
            raise ValueError('Recomputed two-part mean differs from the formal prediction')
        cal = oos[oos.week.lt(t)]
        platt, platt_info = fit_platt(cal); iso = fit_isotonic(cal)
        probs = dict(original=p, platt=platt(p), isotonic=iso(p))
        means = {k: v * m0 + (1 - v) * m1 for k, v in probs.items()}
        base = R.baselines(d[d.week.lt(t)], test)  # equal-information baselines, as in the formal report
        weekly[str(t)] = dict(calibration_weeks=sorted(int(w) for w in cal.week.unique()), calibration_n=int(len(cal)),
            calibration_prevalence=float(cal.y.mean()), platt=platt_info, m0=m0,
            probability={k: prob_metrics(low, v) for k, v in probs.items()},
            rmse={k: rmse(y, v) for k, v in means.items()},
            gains={k: {b: 1 - rmse(y, v) / rmse(y, base[b]) for b in ('timetable_static', 'historical_mean')} for k, v in means.items()},
            alerts_unchanged=True)
        frames.append(pd.DataFrame(dict(session_id=test.session_id.to_numpy(), week=t, course_id=test.course_id.to_numpy(),
            occupancy_rate=y, low_use=low, m0=m0, m1=m1, **{f'p_{k}': v for k, v in probs.items()}, **{f'mean_{k}': v for k, v in means.items()})))
        print('week', t, {k: round(v, 4) for k, v in weekly[str(t)]['rmse'].items()},
              {k: round(weekly[str(t)]['probability'][k]['brier'], 4) for k in METHODS}, flush=True)
    f = pd.concat(frames, ignore_index=True); f.to_csv(OUT / '逐课次校准预测.csv', index=False, encoding='utf-8-sig')
    pooled = dict(probability={k: prob_metrics(f.low_use, f[f'p_{k}']) for k in METHODS},
                  rmse={k: rmse(f.occupancy_rate, f[f'mean_{k}']) for k in METHODS})
    rng = np.random.default_rng(42); groups = f.groupby('course_id').indices; keys = np.array(list(groups)); diffs = []
    for _ in range(2000):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys), replace=True)]); s = f.iloc[idx]
        diffs.append(rmse(s.occupancy_rate, s.mean_platt) - rmse(s.occupancy_rate, s.mean_original))
    ci = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
    checks = dict(
        a_pooled_brier_lower=bool(pooled['probability']['platt']['brier'] < pooled['probability']['original']['brier']),
        b_pooled_rmse_not_higher=bool(pooled['rmse']['platt'] <= pooled['rmse']['original']),
        c_no_week_worse_than_0002=bool(all(w['rmse']['platt'] - w['rmse']['original'] <= .002 for w in weekly.values())),
        d_gate1_every_week=bool(all(min(w['gains']['platt'].values()) >= .1 for w in weekly.values())))
    report = dict(protocol_sha256=sha(PROTOCOL), skipped_calibration_weeks=skipped, weekly=weekly, pooled=pooled,
        ci_pooled_rmse_platt_minus_original=ci, significant=bool(ci[1] < 0 or ci[0] > 0), checks=checks, adopt=bool(all(checks.values())),
        sources={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), U / 'time_predictions.csv', ROOT / '01、数据处理/清洗产物/sessions.csv',
                 ROOT / '02、模型实验/代码/models/stable_low.py']})
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('POOLED', json.dumps({k: {'rmse': round(pooled['rmse'][k], 5), 'brier': round(pooled['probability'][k]['brier'], 5),
          'ece': round(pooled['probability'][k]['ece'], 4), 'mean_p': round(pooled['probability'][k]['mean_p'], 4)} for k in METHODS}),
          'prevalence', round(pooled['probability']['original']['prevalence'], 4), 'CI', [round(x, 5) for x in ci], 'checks', checks, 'adopt', report['adopt'], flush=True)


if __name__ == '__main__':
    main()
