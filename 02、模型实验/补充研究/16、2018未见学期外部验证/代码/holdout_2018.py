"""Experiment 16: one-shot out-of-time validation of the frozen unified_v6 on 2018 semester-2 weeks 1-6.

Frozen protocol: 研究协议.json (hash recorded before results). The model is fitted once on 2017 with the
"next fold" recipe and never changed; only the history store grows week by week, as in serving.
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
import calendar_context as C
import unified as U

ROOM = {'Mathews Theatre A': 'MathewsThA', 'Mathews Theatre B': 'MathewsThB', 'Mathews Theatre C': 'MathewsThC',
        'Mathews Theatre D': 'MathewsThD', 'UNSW Business School 105': 'BUS 105', 'UNSW Business School 115': 'BUS 115',
        'Central Lecture Block 7': 'CLB 7', 'Central Lecture Block 8': 'CLB 8', 'Physics Theatre': 'PhysicsTh'}
KEY = ['room_name', 'day', 'start_time', 'end_time', 'school', 'class_type', 'faculty', 'degree', 'joint']
WINDOW_2018 = (pd.Timestamp('2018-07-23'), pd.Timestamp('2018-08-31'))
PAPER_DS3 = {'RF': 0.157, 'SVR': 0.193, 'MLR': 0.193, 'QRF': 0.217, 'Quantile LR': 0.240, 'Quantile SVM': 0.216}


def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2)))


def build_2018(d):
    a = pd.read_csv(ROOT / '01、数据处理/原始数据/UNSW/2018_sem2_attendance_data.csv')
    rooms = d.groupby('room')[['doors', 'seats']].first()
    a['room'] = a.room_name.map(ROOM)
    if a.room.isna().any(): raise ValueError('Unknown 2018 room')
    key = a[KEY].astype(str).agg('|'.join, axis=1)
    a['course_id'] = 'y2018-' + key.map(lambda k: hashlib.sha1(k.encode()).hexdigest()[:10])
    date = pd.to_datetime(a.date)
    b = pd.DataFrame(dict(room=a.room, date=date, course_id=a.course_id, week=a.week.astype(int),
        course_start=a.start_time.astype(str), course_end=a.end_time.astype(str),
        doors=a.room.map(rooms.doors).astype(float), seats=a.room.map(rooms.seats).astype(float),
        enrollments=a.enrollment.astype(float), attendees=a.attendance.astype(float),
        weekday=date.dt.weekday, is_weekend=(date.dt.weekday >= 5).astype(int)))
    hour = pd.to_timedelta(b.course_start).dt.total_seconds() / 3600
    b['is_morning'] = (hour < 12).astype(float)
    b['occupancy_rate'] = b.attendees / b.seats
    b['session_id'] = b.date.dt.strftime('%Y-%m-%d') + '|' + b.room + '|' + b.course_id + '|' + b.course_start
    if not b.session_id.is_unique: raise ValueError('Duplicate 2018 session ids')
    return b


def patched_review_flag(original):
    def review_flag(query):
        dates = pd.to_datetime(query.date, errors='coerce')
        in2018 = dates.between(*WINDOW_2018)
        out = np.zeros(len(query), bool)
        if (~in2018).any(): out[~in2018.to_numpy()] = original(query.loc[~in2018.to_numpy()])
        return out          # no NSW statewide public holiday 2018-07-23..08-31 (Aug 6 bank holiday is not statewide)
    return review_flag


def cluster_ci(frame, fn, reps=2000, seed=42):
    rng = np.random.default_rng(seed); groups = frame.groupby('course_id').indices; keys = list(groups); vals = []
    for _ in range(reps):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys), replace=True)]); vals.append(fn(frame.iloc[idx]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest())
    d = R.load()
    hour = pd.to_timedelta(d.course_start, errors='coerce').dt.total_seconds() / 3600
    report['is_morning_rule_agreement_2017'] = float(((hour < 12).astype(float) == d.is_morning).mean())
    b = build_2018(d)
    train, valid, final, cal = d[d.week < 11], d[d.week.eq(11)], d[d.week <= 11], d[d.week.eq(12)]
    bundle = U.make_bundle(train, valid, final, cal, 13, d)            # fitted once on 2017, then frozen
    C.review_flag = patched_review_flag(C.review_flag)
    frames = []
    for w in sorted(b.week.unique()):
        ref = pd.concat([d, b[b.week < w]], ignore_index=True)
        for part in ('warm', 'cond', 'low', 'context'): bundle[part]['reference'] = ref
        test = b[b.week.eq(w)]
        pred = U.predict_bundle(bundle, test)
        base = R.baselines(ref, test)
        last = []
        for r in test.itertuples():
            h = ref[(ref.course_id == r.course_id) & (ref.date < r.date)].sort_values('date')
            last.append(float(h.occupancy_rate.iloc[-1]) if len(h) else float(ref[ref.date < r.date].occupancy_rate.mean()))
        f = test[['session_id', 'week', 'course_id', 'room', 'seats', 'enrollments', 'attendees', 'occupancy_rate']].merge(pred, on='session_id', validate='one_to_one')
        f['timetable_static'] = base['timetable_static']; f['historical_mean'] = base['historical_mean']
        f['course_history_mean'] = base['course_history_mean']; f['last_session'] = last
        frames.append(f); print('week', w, len(f), round(rmse(f.occupancy_rate, f.prediction), 4), flush=True)
    f = pd.concat(frames, ignore_index=True); f.to_csv(OUT / '2018逐课次预测.csv', index=False, encoding='utf-8-sig')
    cols = ['prediction', 'regression_prediction', 'state_prediction', 'timetable_static', 'historical_mean', 'course_history_mean', 'last_session']
    report['n'] = int(len(f)); report['routes'] = f.prediction_route.value_counts().to_dict()
    report['weekly'] = {str(w): {c: rmse(g.occupancy_rate, g[c]) for c in cols} for w, g in f.groupby('week')}
    pooled = {c: rmse(f.occupancy_rate, f[c]) for c in cols}; report['pooled_rmse'] = pooled
    report['pooled_gains'] = {c: 1 - pooled['prediction'] / pooled[c] for c in cols[3:]}
    report['weekly_gains'] = {w: {c: 1 - v['prediction'] / v[c] for c in cols[3:]} for w, v in report['weekly'].items()}
    report['ci_rmse_baseline_minus_model'] = {c: cluster_ci(f, lambda g, c=c: rmse(g.occupancy_rate, g[c]) - rmse(g.occupancy_rate, g.prediction)) for c in cols[1:]}
    low = f.occupancy_rate < .1
    report['held_low_use'] = dict(positives=int(low.sum()), note='2018只含有人上课的课次；此处仅为“有人但<10%”的部分正例',
                                  metrics=R.binary_metrics(low, f.low_alert) if low.any() else None)
    na = f.attendees / f.enrollments
    keep = f.enrollments.gt(0) & na.le(1.5)
    y_na = na[keep].clip(upper=1); p_na = (f.prediction * f.seats / f.enrollments)[keep].clip(0, 1)
    report['original_paper_scale'] = dict(n=int(keep.sum()), rmse_unified_v6=rmse(y_na, p_na),
        rmse_single_regression=rmse(y_na, (f.regression_prediction * f.seats / f.enrollments)[keep].clip(0, 1)),
        rmse_timetable_static_equiv=rmse(y_na, np.ones(keep.sum())), paper_table_v_ds3=PAPER_DS3)
    g = report['pooled_gains']; ci = report['ci_rmse_baseline_minus_model']
    report['claims'] = dict(
        gate1_replicated=bool(g['timetable_static'] >= .1 and g['historical_mean'] >= .1 and ci['timetable_static'][0] > 0 and ci['historical_mean'][0] > 0),
        two_part_advantage_carried=bool(pooled['prediction'] <= pooled['regression_prediction']))
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print('SUMMARY', json.dumps(dict(n=report['n'], pooled_rmse={k: round(v, 4) for k, v in pooled.items()},
        gains={k: round(v, 3) for k, v in g.items()}, ci={k: [round(x, 3) for x in v] for k, v in ci.items()},
        paper=report['original_paper_scale'], held_low=report['held_low_use'], claims=report['claims'],
        morning_rule=report['is_morning_rule_agreement_2017']), ensure_ascii=False, default=float))


if __name__ == '__main__':
    main()
