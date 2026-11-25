"""Experiment 11: teaching-week features for the unseen-room (cold) branch, nested-selected.

Frozen protocol: 研究协议.json (hash recorded before any fitting). Outer rooms never enter
preprocessing, selection or post-processing. Retrospective: all nine rooms were inspected earlier.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import improvement_v8 as V8

CURRENT = dict(macro=0.1797152963826738, forward=0.17163237812858084, rooms_over=5, upper=0.1895671877230475)
GRID = ([('v8_control', 'Ridge', a) for a in (.1, 1., 10.)] + [('v8_control', 'LightGBM', n) for n in (80, 200, 400)]
        + [('week_features', 'Ridge', a) for a in (.1, 1., 10., 100.)] + [('week_features', 'LightGBM', n) for n in (80, 200, 400)]
        + [('week_blend', 'Blend', None)])


def features(frame, family):
    x = V8.features(frame)
    if family != 'v8_control':
        x['week'] = frame.week.astype(float).to_numpy()
        x['pressure_x_week'] = x.enrollment_pressure * x.week
        x['pressure_sq'] = x.enrollment_pressure ** 2
    return x


def fit_one(train, query, family, name, param):
    a, b = features(train, family), features(query, family)
    med = a.median().fillna(0); a, b = a.fillna(med), b.fillna(med)
    w = V8.room_weights(train)
    if name == 'Ridge':
        s = StandardScaler().fit(a, sample_weight=w); a, b = s.transform(a), s.transform(b)
        model = Ridge(alpha=param)
    else:
        model = lgb.LGBMRegressor(n_estimators=int(param), learning_rate=.05, num_leaves=15,
                                  min_child_samples=20, random_state=42, n_jobs=2, verbosity=-1)
    model.fit(a, train.occupancy_rate, sample_weight=w)
    return np.maximum(0, model.predict(b))


def inner_scores(pool):
    """Inner leave-one-room-out over the outer training pool only."""
    rooms = sorted(pool.room.unique()); preds = {}
    for cand in GRID[:-1]:
        preds[cand] = {r: fit_one(pool[pool.room.ne(r)], pool[pool.room.eq(r)], *cand) for r in rooms}
    truth = {r: pool[pool.room.eq(r)].occupancy_rate.to_numpy() for r in rooms}
    score = lambda p: float(np.mean([np.sqrt(np.mean((p[r] - truth[r]) ** 2)) for r in rooms]))
    scores = {c: score(p) for c, p in preds.items()}
    best = lambda name: min((c for c in scores if c[0] == 'week_features' and c[1] == name), key=lambda c: (scores[c], GRID.index(c)))
    br, bl = best('Ridge'), best('LightGBM')
    scores[GRID[-1]] = score({r: (preds[br][r] + preds[bl][r]) / 2 for r in rooms})
    return scores, (br, bl)


def fit_predict(pool, query, cand, parts):
    if cand[0] == 'week_blend':
        return (fit_one(pool, query, *parts[0]) + fit_one(pool, query, *parts[1])) / 2
    return fit_one(pool, query, *cand)


def nested(pool, query):
    scores, parts = inner_scores(pool)
    chosen = min(scores, key=lambda c: (scores[c], GRID.index(c)))
    return fit_predict(pool, query, chosen, parts), chosen, scores, parts


def label(c): return '/'.join(str(x) for x in c if x is not None)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = Path(__file__).with_name('研究协议.json')
    R.dump(OUT / '执行输入.json', dict(protocol=json.loads(protocol.read_text(encoding='utf-8')),
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sessions_sha256=hashlib.sha256((ROOT / '01、数据处理/清洗产物/sessions.csv').read_bytes()).hexdigest()))
    d = R.load(); rooms = sorted(d.room.unique()); frames, fwd, report = [], [], dict(rooms={}, fixed_family={})
    fixed = {c: [] for c in GRID}
    for room in rooms:
        pool, query = d[d.room.ne(room)], d[d.room.eq(room)]
        p, chosen, scores, parts = nested(pool, query)
        frames.append(R.prediction_frame(query, p, prediction_route='unseen'))
        rmse = R.metrics(query.occupancy_rate, p)['rmse']
        for c in GRID:  # disclosure only; never used for selection
            fixed[c].append(R.metrics(query.occupancy_rate, fit_predict(pool, query, c, parts))['rmse'])
        past, future = pool[pool.week.le(10)], query[query.week.eq(12)]
        pf, chosen_f, _, _ = nested(past, future)
        fwd.append(R.prediction_frame(future, pf, prediction_route='unseen'))
        report['rooms'][room] = dict(rmse=rmse, selected=label(chosen), inner_scores={label(c): v for c, v in scores.items()},
            forward_rmse=R.metrics(future.occupancy_rate, pf)['rmse'], forward_selected=label(chosen_f))
        print(room, round(rmse, 4), label(chosen), 'forward', round(report['rooms'][room]['forward_rmse'], 4), flush=True)
    spatial = pd.concat(frames); spatial.to_csv(OUT / '逐课次留一教室预测.csv', index=False)
    pd.concat(fwd).to_csv(OUT / '逐课次前推冷启动预测.csv', index=False)
    macro = float(np.mean([v['rmse'] for v in report['rooms'].values()]))
    forward = float(np.mean([v['forward_rmse'] for v in report['rooms'].values()]))
    over = sum(v['rmse'] > .18 for v in report['rooms'].values())
    interval = V8.conditional_interval(spatial)
    checks = dict(macro_at_most_0175=macro <= .175, forward_not_worse=forward <= CURRENT['forward'],
                  rooms_over_018_not_more=over <= CURRENT['rooms_over'], interval_upper_not_higher=interval['macro_rmse_95'][1] <= CURRENT['upper'])
    report.update(macro_rmse=macro, forward_macro_rmse=forward, rooms_over_018=over, conditional_course_bootstrap=interval,
                  current=CURRENT, checks=checks, eligible=all(checks.values()), formal_changed=False,
                  fixed_family={label(c): float(np.mean(v)) for c, v in fixed.items()})
    R.dump(OUT / 'report.json', report)
    print(json.dumps(dict(macro=macro, forward=forward, over=over, interval=interval['macro_rmse_95'], checks=checks), ensure_ascii=False))


if __name__ == '__main__':
    main()
