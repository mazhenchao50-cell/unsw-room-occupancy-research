"""Experiment 20: strict forward leave-one-room-out for criterion 3, with lagged campus features.

Frozen protocol: 研究协议.json. For target room r and week w, everything (fitting and model selection) uses
only the other rooms' sessions before week w. Campus-level lag features use only training rooms and earlier weeks.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议.json')
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import improvement_v8 as V8
import unified as U

PRIMARY = [8, 10, 11, 12]; SECONDARY = [5, 6, 7, 8, 10, 11, 12]
CANDIDATES = [(f, m, p) for f in ('static', 'week', 'lagged') for m, p in (('Ridge', 1.), ('Ridge', 10.), ('Ridge', 100.), ('LightGBM', 80), ('LightGBM', 200))]


def campus_table(ref):
    """Weekly campus means from the given (training-room) sessions."""
    att = (ref.attendees / ref.enrollments.where(ref.enrollments > 0)).clip(0, 1.5)
    t = pd.DataFrame(dict(week=ref.week, occ=ref.occupancy_rate, att=att)).groupby('week').mean()
    return t.sort_index()


def features(frame, family, table):
    x = V8.features(frame)
    if family == 'static': return x
    x['week'] = frame.week.astype(float).to_numpy()
    if family == 'week':
        x['pressure_x_week'] = x.enrollment_pressure * x.week; x['pressure_sq'] = x.enrollment_pressure ** 2
        return x
    lag = []
    weeks = table.index.to_numpy()
    for w in frame.week.to_numpy():
        prev = weeks[weeks < w]
        if len(prev) == 0: lag.append((np.nan,) * 4); continue
        last = table.loc[prev[-1]]; two = table.loc[prev[-2:]].mean()
        lag.append((last.occ, two.occ, last.att, two.att))
    lag = np.array(lag, float)
    x['campus_occ_last'], x['campus_occ_two'], x['campus_att_last'], x['campus_att_two'] = lag.T
    x['pressure_x_att_last'] = x.enrollment_pressure * x.campus_att_last
    return x


def fit(train, cand, table):
    family, name, param = cand
    a = features(train, family, table); med = a.median().fillna(0); a = a.fillna(med); w = V8.room_weights(train); scaler = None
    if name == 'Ridge':
        scaler = StandardScaler().fit(a, sample_weight=w); model = Ridge(alpha=param).fit(scaler.transform(a), train.occupancy_rate, sample_weight=w)
    else:
        model = lgb.LGBMRegressor(n_estimators=int(param), learning_rate=.05, num_leaves=15, min_child_samples=20, random_state=42,
                                  n_jobs=2, verbosity=-1).fit(a, train.occupancy_rate, sample_weight=w)
    return dict(cand=cand, model=model, med=med, scaler=scaler, table=table)


def predict(b, query):
    x = features(query, b['cand'][0], b['table']).fillna(b['med'])
    if b['scaler'] is not None: x = b['scaler'].transform(x)
    return np.clip(b['model'].predict(x), 0, None)


def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def select(train, mode):
    """Inner leave-one-training-room-out; 'forward' tests on the last available week only."""
    rooms = sorted(train.room.unique()); last = int(train.week.max()); scores = {}
    for cand in CANDIDATES:
        errs = []
        for r in rooms:
            if mode == 'forward':
                itr = train[(train.room != r) & (train.week < last)]; ite = train[(train.room == r) & (train.week == last)]
            else:
                itr = train[train.room != r]; ite = train[train.room == r]
            if ite.empty or itr.empty: continue
            errs.append(rmse(ite.occupancy_rate, predict(fit(itr, cand, campus_table(itr)), ite)))
        scores[cand] = float(np.mean(errs))
    best = min(scores, key=scores.get)
    return best, scores


_DATA = None


def _data():
    global _DATA
    if _DATA is None: _DATA = R.load()
    return _DATA


def room_task(kind, weeks, room):
    """One (method, room) unit; identical computation to the serial loop, run in a worker process."""
    d = _data()
    if kind == 'contemporaneous':
        train, query = d[d.room != room], d[d.room == room]
        cand, _ = select(train, 'contemporaneous')
        return kind, tuple(weeks), room, dict(rmse=rmse(query.occupancy_rate, predict(fit(train, cand, campus_table(train)), query)), chosen=['/'.join(map(str, cand))])
    y, p, chosen = [], [], []
    for w in weeks:
        train = d[(d.room != room) & (d.week < w)]; query = d[(d.room == room) & (d.week == w)]
        if query.empty: continue
        if kind == 'formal_cold_week':
            pred = U.predict_cold(U.fit_cold(train), query)
        else:
            cand, _ = select(train, 'forward'); chosen.append('/'.join(map(str, cand)))
            pred = predict(fit(train, cand, campus_table(train)), query)
        y.append(query.occupancy_rate.to_numpy()); p.append(pred)
    return kind, tuple(weeks), room, dict(rmse=rmse(np.concatenate(y), np.concatenate(p)), chosen=chosen)


def main():
    from concurrent.futures import ProcessPoolExecutor
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                  execution='per-room tasks in 8 worker processes; each fit keeps n_jobs=2 as frozen; results identical to serial order')
    tasks = [(k, w, r) for k, w in (('formal_cold_week', PRIMARY), ('new', PRIMARY), ('new', SECONDARY), ('contemporaneous', [])) for r in U.ROOMS]
    results = {}
    with ProcessPoolExecutor(max_workers=8) as pool:
        for kind, weeks, room, res in pool.map(room_task, *zip(*tasks)):
            results[(kind, weeks, room)] = res; print(kind, weeks[:1], room, round(res['rmse'], 4), flush=True)
    def block(kind, weeks):
        rooms = {r: results[(kind, tuple(weeks), r)] for r in U.ROOMS}
        chosen = pd.Series([c for v in rooms.values() for c in v['chosen']]).value_counts().to_dict() if kind != 'formal_cold_week' else None
        return dict(macro=float(np.mean([v['rmse'] for v in rooms.values()])), rooms={r: v['rmse'] for r, v in rooms.items()}, chosen=chosen)
    report['formal_cold_week_strict_primary'] = block('formal_cold_week', PRIMARY)
    report['new_strict_primary'] = block('new', PRIMARY)
    report['new_strict_secondary'] = block('new', SECONDARY)
    report['new_contemporaneous'] = block('contemporaneous', [])
    sp, cm = report['new_strict_primary']['macro'], report['new_contemporaneous']['macro']
    report['adopt'] = bool(sp <= .18 and cm <= .18)
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print('SUMMARY', json.dumps(dict(formal_strict=report['formal_cold_week_strict_primary']['macro'], new_strict=sp,
        new_strict_secondary=report['new_strict_secondary']['macro'], new_contemporaneous=cm, adopt=report['adopt'],
        chosen=report['new_strict_primary']['chosen']), ensure_ascii=False, default=float))


if __name__ == '__main__':
    main()
