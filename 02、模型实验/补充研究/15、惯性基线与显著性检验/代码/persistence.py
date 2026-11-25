"""Experiment 15: formal unified_v6 predictions vs persistence baselines, with McNemar and course-cluster bootstrap.

Frozen protocol: 研究协议.json (its SHA256 is written to the report before results). No model is fitted or tuned.
"""
from pathlib import Path
import hashlib, json, math, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议.json')
PRIOR = 0.3
WEEKS = [8, 10, 11, 12]


def metrics(y, p):
    y, p = np.asarray(y, bool), np.asarray(p, bool)
    tp, fp, fn = int((y & p).sum()), int((~y & p).sum()), int((y & ~p).sum())
    P = tp / (tp + fp) if tp + fp else 0.0; R = tp / (tp + fn) if tp + fn else 0.0
    return dict(precision=P, recall=R, f1=2 * P * R / (P + R) if P + R else 0.0, tp=tp, fp=fp, fn=fn, tn=int((~y & ~p).sum()), n=int(len(y)))


def mcnemar(y, a, b):
    """Exact two-sided McNemar on correctness of a vs b."""
    ca, cb = (np.asarray(a) == np.asarray(y)), (np.asarray(b) == np.asarray(y))
    n01, n10 = int((ca & ~cb).sum()), int((~ca & cb).sum()); n = n01 + n10
    if n == 0: return dict(a_only_correct=0, b_only_correct=0, p=1.0)
    k = min(n01, n10); p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return dict(a_only_correct=n01, b_only_correct=n10, p=p)


def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def history_features(sessions, rows):
    out = []
    for r in rows.itertuples():
        h = sessions[(sessions.course_id == r.course_id) & (sessions.date < r.date)].dropna(subset=['occupancy_rate']).sort_values('date')
        occ = h.occupancy_rate.to_numpy()
        out.append(dict(session_id=r.session_id, n_hist=len(occ),
            B1_last=bool(len(occ) and occ[-1] < .1),
            B2_last2_both=bool(len(occ) and (occ[-2:] < .1).all()),
            B3_hist_mean=bool(len(occ) and occ.mean() < .1),
            R1_last=float(occ[-1]) if len(occ) else PRIOR,
            R2_course_mean=float(occ.mean()) if len(occ) else PRIOR,
            prev_low=bool(occ[-1] < .1) if len(occ) else None))
    return pd.DataFrame(out)


def cluster_bootstrap(frame, stat, reps=2000, seed=42):
    rng = np.random.default_rng(seed); groups = frame.groupby('course_id').indices; keys = list(groups)
    vals = []
    for _ in range(reps):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys), replace=True)])
        vals.append(stat(frame.iloc[idx]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol_sha = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    sessions = pd.read_csv(ROOT / '01、数据处理/清洗产物/sessions.csv', parse_dates=['date'])
    sessions = sessions[sessions.week != 9]
    pred = pd.read_csv(ROOT / '02、模型实验/生成产物/unified/time_predictions.csv', parse_dates=['date'])
    pred = pred[pred.week.isin(WEEKS)].reset_index(drop=True)
    f = pred.merge(history_features(sessions, pred), on='session_id', how='left')
    f['y'] = f.occupancy_rate < .1
    f['transition'] = f.prev_low.isna() | (f.prev_low != f.y)
    f.to_csv(OUT / '逐课次对照.csv', index=False, encoding='utf-8-sig')
    cls = ['B1_last', 'B2_last2_both', 'B3_hist_mean']; reg = ['R1_last', 'R2_course_mean']
    report = dict(protocol_sha256=protocol_sha, n=int(len(f)), weekly={}, pooled={}, transition={}, bootstrap={})
    for w in WEEKS + ['pooled']:
        g = f if w == 'pooled' else f[f.week == w]
        y = g.y.to_numpy(); m = g.low_alert.to_numpy().astype(bool)
        block = dict(model=metrics(y, m), baselines={b: metrics(y, g[b]) for b in cls},
                     mcnemar={b: mcnemar(y, m, g[b].to_numpy()) for b in cls},
                     rmse=dict(model=rmse(g.occupancy_rate, g.prediction), single_regression=rmse(g.occupancy_rate, g.regression_prediction),
                               **{b: rmse(g.occupancy_rate, g[b]) for b in reg}))
        block['rmse_gain_vs'] = {b: 1 - block['rmse']['model'] / block['rmse'][b] for b in reg}
        (report['pooled'] if w == 'pooled' else report['weekly']).update({str(w): block} if w != 'pooled' else block)
    t = f[f.transition]
    report['transition'] = dict(n=int(len(t)), share=float(len(t) / len(f)), positives=int(t.y.sum()),
        model=metrics(t.y, t.low_alert.astype(bool)), B1_last=metrics(t.y, t.B1_last),
        stable=dict(n=int((~f.transition).sum()), model=metrics(f[~f.transition].y, f[~f.transition].low_alert.astype(bool)),
                    B1_last=metrics(f[~f.transition].y, f[~f.transition].B1_last)))
    f1 = lambda g, col: metrics(g.y, g[col].astype(bool))['f1']
    for b in cls:
        report['bootstrap'][f'f1_model_minus_{b}'] = cluster_bootstrap(f, lambda g: f1(g, 'low_alert') - f1(g, b))
    for b in reg:
        report['bootstrap'][f'rmse_{b}_minus_model'] = cluster_bootstrap(f, lambda g: rmse(g.occupancy_rate, g[b]) - rmse(g.occupancy_rate, g.prediction))
    p = report['pooled']; bs = report['bootstrap']
    report['claims'] = {b: bool(bs[f'f1_model_minus_{b}'][0] > 0 and p['mcnemar'][b]['p'] < .05) for b in cls}
    report['claims'].update({b: bool(bs[f'rmse_{b}_minus_model'][0] > 0) for b in reg})
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print(json.dumps(dict(pooled_f1={k: round(v['f1'], 3) for k, v in [('model', p['model'])] + list(p['baselines'].items())},
                          mcnemar_p={b: round(p['mcnemar'][b]['p'], 4) for b in cls}, bootstrap={k: [round(x, 3) for x in v] for k, v in bs.items()},
                          rmse={k: round(v, 4) for k, v in p['rmse'].items()}, transition_model=report['transition']['model'],
                          claims=report['claims']), ensure_ascii=False, default=float))


if __name__ == '__main__':
    main()
