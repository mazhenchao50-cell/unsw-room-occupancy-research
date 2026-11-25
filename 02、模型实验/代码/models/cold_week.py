"""Unseen-room (cold) branch for unified_v5: teaching-week features with nested room selection.

Adopted 2026-11-23 from supplementary experiment 11 after all four frozen adoption checks passed.
Candidates: original v8 features (Ridge 0.1/1/10, LightGBM 80/200/400); v8 features + teaching week,
enrollment pressure x week and pressure squared (Ridge 0.1/1/10/100, LightGBM 80/200/400); and the
equal-weight blend of the inner-best Ridge and LightGBM on the week features. Selection is inner
leave-one-room-out macro RMSE on the fitting pool only; no room/course identity or label history.
"""
import numpy as np
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import improvement_v8 as V8

GRID = ([('v8_control', 'Ridge', a) for a in (.1, 1., 10.)] + [('v8_control', 'LightGBM', n) for n in (80, 200, 400)]
        + [('week_features', 'Ridge', a) for a in (.1, 1., 10., 100.)] + [('week_features', 'LightGBM', n) for n in (80, 200, 400)]
        + [('week_blend', 'Blend', None)])


def features(frame, family):
    x = V8.features(frame)
    if family != 'v8_control':
        if 'week' not in frame or frame.week.isna().any():
            raise ValueError('Teaching week required for the unseen-room branch')
        x['week'] = frame.week.astype(float).to_numpy()
        x['pressure_x_week'] = x.enrollment_pressure * x.week
        x['pressure_sq'] = x.enrollment_pressure ** 2
    return x


def _fit(train, family, name, param):
    a = features(train, family); med = a.median().fillna(0); a = a.fillna(med)
    w = V8.room_weights(train); scaler = None
    if name == 'Ridge':
        scaler = StandardScaler().fit(a, sample_weight=w); a = scaler.transform(a); model = Ridge(alpha=param)
    else:
        model = lgb.LGBMRegressor(n_estimators=int(param), learning_rate=.05, num_leaves=15,
                                  min_child_samples=20, random_state=42, n_jobs=2, verbosity=-1)
    model.fit(a, train.occupancy_rate, sample_weight=w)
    return dict(family=family, name=name, param=param, model=model, median=med, scaler=scaler)


def _predict(part, query):
    x = features(query, part['family']).fillna(part['median'])
    if part['scaler'] is not None: x = part['scaler'].transform(x)
    return np.maximum(0, part['model'].predict(x))


def select(pool):
    rooms = sorted(pool.room.unique())
    if len(rooms) < 3: raise ValueError('At least three training rooms required')
    preds = {c: {r: _predict(_fit(pool[pool.room.ne(r)], *c), pool[pool.room.eq(r)]) for r in rooms} for c in GRID[:-1]}
    truth = {r: pool[pool.room.eq(r)].occupancy_rate.to_numpy() for r in rooms}
    score = lambda p: float(np.mean([np.sqrt(np.mean((p[r] - truth[r]) ** 2)) for r in rooms]))
    scores = {c: score(p) for c, p in preds.items()}
    best = lambda n: min((c for c in scores if c[0] == 'week_features' and c[1] == n), key=lambda c: (scores[c], GRID.index(c)))
    parts = (best('Ridge'), best('LightGBM'))
    scores[GRID[-1]] = score({r: (preds[parts[0]][r] + preds[parts[1]][r]) / 2 for r in rooms})
    chosen = min(scores, key=lambda c: (scores[c], GRID.index(c)))
    return chosen, parts, scores


def fit(reference):
    chosen, parts, scores = select(reference)
    members = [_fit(reference, *p) for p in parts] if chosen[0] == 'week_blend' else [_fit(reference, *chosen)]
    return dict(version='cold_week_v1', members=members, selected=[str(x) for x in chosen if x is not None],
                trials=[dict(candidate=[str(x) for x in c if x is not None], inner_macro_rmse=v) for c, v in scores.items()],
                known_rooms=sorted(reference.room.unique()), cutoff=reference.date.max(), fitted_ids=set(reference.session_id))


def predict(bundle, query):
    return np.mean([_predict(m, query) for m in bundle['members']], axis=0)
