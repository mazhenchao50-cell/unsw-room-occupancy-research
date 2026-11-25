"""Experiment 19: are unscheduled room-hours really vacant, and can spontaneous use be predicted in advance?

Frozen protocol: 研究协议.json. Labels use the authors' attendee-counting rule (subtract exits, floor at 0,
add entries) applied to each unscheduled hour; features are known in advance from the timetable and earlier weeks.
"""
from pathlib import Path
import glob, hashlib, json
import numpy as np
import pandas as pd
import lightgbm as lgb

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议.json')
RAW = ROOT / '01、数据处理/原始数据/UNSW'
HOURS = range(8, 20); LEAD = pd.Timedelta(minutes=15); K = 5; WEEKS = [8, 10, 11, 12]


def metrics(y, p):
    y, p = np.asarray(y, bool), np.asarray(p, bool)
    tp, fp, fn, tn = int((y & p).sum()), int((~y & p).sum()), int((y & ~p).sum()), int((~y & ~p).sum())
    P = tp / (tp + fp) if tp + fp else 0.0; R = tp / (tp + fn) if tp + fn else 0.0
    rec_vac = ~p; vac = ~y
    return dict(precision=P, recall=R, f1=2 * P * R / (P + R) if P + R else 0.0, tp=tp, fp=fp, fn=fn, tn=tn,
                recommended_vacant=int(rec_vac.sum()), recommend_precision=float((vac & rec_vac).sum() / rec_vac.sum()) if rec_vac.any() else None,
                vacant_coverage=float((vac & rec_vac).sum() / vac.sum()) if vac.any() else None)


def build_slots():
    rows = []
    for f in sorted(glob.glob(str(RAW / 'week*_computed_data.csv'))):
        w = pd.read_csv(f); w['ts'] = pd.to_datetime(w.Timestamp)
        for c in ('CountIn', 'CountOut'):   # week8 has one corrupted CountOut cell (a file path); treated as 0
            w[c] = pd.to_numeric(w[c], errors='coerce').fillna(0).astype(int)
        week = int(w.Week.iloc[0])
        if week == 9: continue
        w = w[w.ts.dt.weekday < 5]
        w['day'] = w.ts.dt.normalize()
        sched = w.dropna(subset=['CourseID']).drop_duplicates(['RoomName', 'day', 'CourseID', 'CourseStartTime'])
        sched = sched.assign(s=sched.day + pd.to_timedelta(sched.CourseStartTime), e=sched.day + pd.to_timedelta(sched.CourseEndTime))
        meta = w.groupby('RoomName')[['NumSeats', 'NumDoorways']].first()
        for (room, day), g in w.sort_values('ts').groupby(['RoomName', 'day']):
            sc = sched[(sched.RoomName == room) & (sched.day == day)]
            ins, outs, ts = g.CountIn.to_numpy(), g.CountOut.to_numpy(), g.ts.to_numpy()
            for h in HOURS:
                a0, a1 = day + pd.Timedelta(hours=h), day + pd.Timedelta(hours=h + 1)
                if ((sc.s - LEAD < a1) & (sc.e > a0)).any(): continue                 # overlaps a scheduled class window
                m = (ts >= np.datetime64(a0)) & (ts < np.datetime64(a1)); a = 0; peak = 0
                for i, o in zip(ins[m], outs[m]): a = max(0, a - o) + i; peak = max(peak, a)
                nxt = sc[sc.s >= a1]; prv = sc[sc.e <= a0]
                rows.append(dict(room=room, day=day, week=week, weekday=day.weekday(), hour=h, peak=peak, entries=int(ins[m].sum()),
                    seats=float(meta.loc[room, 'NumSeats']), doors=float(meta.loc[room, 'NumDoorways']),
                    min_to_next=float(min(600, (nxt.s.min() - a1).total_seconds() / 60)) if len(nxt) else 600.,
                    min_since_prev=float(min(600, (a0 - prv.e.max()).total_seconds() / 60)) if len(prv) else 600.,
                    next_enroll=float(nxt.sort_values('s').NumEnrollments.iloc[0]) if len(nxt) and pd.notna(nxt.sort_values('s').NumEnrollments.iloc[0]) else 0.,
                    prev_enroll=float(prv.sort_values('e').NumEnrollments.iloc[-1]) if len(prv) and pd.notna(prv.sort_values('e').NumEnrollments.iloc[-1]) else 0.))
        print('week', week, len(rows), flush=True)
    s = pd.DataFrame(rows); s['occupied'] = s.peak >= K
    return s


def add_history(s):
    s = s.sort_values('day').reset_index(drop=True); prior = float(s.occupied.mean())
    feats = []
    for r in s.itertuples():
        past = s[s.day < r.day]
        slot = past[(past.room == r.room) & (past.weekday == r.weekday) & (past.hour == r.hour)]
        rh = past[(past.room == r.room) & (past.hour == r.hour)]
        g = float(past.occupied.mean()) if len(past) else prior
        feats.append(dict(slot_rate=float(slot.occupied.mean()) if len(slot) else g, slot_peak=float(slot.peak.mean()) if len(slot) else 0.,
                          slot_n=len(slot), roomhour_rate=float(rh.occupied.mean()) if len(rh) else g))
    return pd.concat([s, pd.DataFrame(feats, index=s.index)], axis=1)


FEATURES = ['seats', 'doors', 'weekday', 'hour', 'week', 'min_to_next', 'min_since_prev', 'next_enroll', 'prev_enroll',
            'slot_rate', 'slot_peak', 'slot_n', 'roomhour_rate', 'room_code']


def cluster_ci(frame, fn, reps=2000, seed=42):
    rng = np.random.default_rng(seed); groups = frame.groupby('room').indices; keys = list(groups); vals = []
    for _ in range(reps):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys), replace=True)]); vals.append(fn(frame.iloc[idx]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), threshold_people=K)
    s = add_history(build_slots()); s['room_code'] = s.room.astype('category').cat.codes
    report['slots'] = dict(n=int(len(s)), occupied_share=float(s.occupied.mean()), by_k={k: float((s.peak >= k).mean()) for k in (3, 5, 10)},
                           peak_median_when_occupied=float(s.loc[s.occupied, 'peak'].median()))
    frames = []
    for tw in WEEKS:
        tr, te = s[s.week < tw], s[s.week == tw].copy()
        model = lgb.LGBMClassifier(n_estimators=150, num_leaves=7, min_child_samples=30, learning_rate=.05, random_state=42, n_jobs=2, verbosity=-1)
        model.fit(tr[FEATURES], tr.occupied)
        te['prob'] = model.predict_proba(te[FEATURES])[:, 1]; te['pred'] = te.prob >= .5
        te['base_hist'] = te.slot_rate >= .5; te['base_timetable'] = False
        frames.append(te)
        report.setdefault('weekly', {})[str(tw)] = dict(model=metrics(te.occupied, te.pred), slot_history=metrics(te.occupied, te.base_hist),
                                                        timetable=metrics(te.occupied, te.base_timetable), n=int(len(te)), occupied=int(te.occupied.sum()))
        print('week', tw, report['weekly'][str(tw)]['model']['f1'], flush=True)
    f = pd.concat(frames); f.drop(columns=['day']).assign(day=f.day.dt.date).to_csv(OUT / '无课时段逐条预测.csv', index=False, encoding='utf-8-sig')
    report['pooled'] = dict(model=metrics(f.occupied, f.pred), slot_history=metrics(f.occupied, f.base_hist), timetable=metrics(f.occupied, f.base_timetable))
    f1 = lambda g, c: metrics(g.occupied, g[c])['f1']
    report['ci_f1_model_minus_history'] = cluster_ci(f, lambda g: f1(g, 'pred') - f1(g, 'base_hist'))
    report['sensitivity_k'] = {}
    for k in (3, 10):
        y = f.peak >= k
        report['sensitivity_k'][str(k)] = dict(occupied_share=float(y.mean()), note='模型仍按K=5训练，仅改评估标签', model=metrics(y, f.pred), slot_history=metrics(y, f.base_hist))
    p = report['pooled']
    report['claim'] = bool(p['model']['f1'] > p['slot_history']['f1'] and report['ci_f1_model_minus_history'][0] > 0
                           and p['model']['recommend_precision'] > p['timetable']['recommend_precision'])
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print('SUMMARY', json.dumps(dict(slots=report['slots'], pooled={k: {m: (round(v, 3) if isinstance(v, float) else v) for m, v in d.items()} for k, d in p.items()},
                                     ci=report['ci_f1_model_minus_history'], claim=report['claim']), ensure_ascii=False, default=float))


if __name__ == '__main__':
    main()
