"""Experiment 21 (in folder 19): unscheduled-slot labels with carry-over (upper bound) vs hourly reset (lower bound).

Frozen protocol: 研究协议_延续人数.json. Same slots, features, model and rules as free_slots.py.
"""
from pathlib import Path
import glob, hashlib, json, sys
import numpy as np
import pandas as pd
import lightgbm as lgb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import free_slots as F

OUT = HERE.parent / '生成产物'
PROTOCOL = HERE / '研究协议_延续人数.json'


def build():
    rows = []; drift = []
    for f in sorted(glob.glob(str(F.RAW / 'week*_computed_data.csv'))):
        w = pd.read_csv(f); w['ts'] = pd.to_datetime(w.Timestamp)
        for c in ('CountIn', 'CountOut'): w[c] = pd.to_numeric(w[c], errors='coerce').fillna(0).astype(int)
        week = int(w.Week.iloc[0])
        if week == 9: continue
        w = w[w.ts.dt.weekday < 5]; w['day'] = w.ts.dt.normalize()
        sched = w.dropna(subset=['CourseID']).drop_duplicates(['RoomName', 'day', 'CourseID', 'CourseStartTime'])
        sched = sched.assign(s=sched.day + pd.to_timedelta(sched.CourseStartTime), e=sched.day + pd.to_timedelta(sched.CourseEndTime))
        for (room, day), g in w.sort_values('ts').groupby(['RoomName', 'day']):
            ins, outs, ts = g.CountIn.to_numpy(), g.CountOut.to_numpy(), g.ts.to_numpy()
            run = np.empty(len(g)); a = 0
            for k, (i, o) in enumerate(zip(ins, outs)): a = max(0, a - o) + i; run[k] = a
            auth = g.NumAttendees.to_numpy(float); m = ~np.isnan(auth)
            if m.any(): drift.append(float(np.mean(run[m] - auth[m])))
            sc = sched[(sched.RoomName == room) & (sched.day == day)]
            for h in F.HOURS:
                a0, a1 = day + pd.Timedelta(hours=h), day + pd.Timedelta(hours=h + 1)
                if ((sc.s - F.LEAD < a1) & (sc.e > a0)).any(): continue
                win = (ts >= np.datetime64(a0)) & (ts < np.datetime64(a1))
                before = np.flatnonzero(ts < np.datetime64(a0)); start = run[before[-1]] if len(before) else 0
                peak_up = max([start] + list(run[win]))
                rows.append(dict(room=room, day=day, hour=h, peak_upper=float(peak_up)))
        print('week', week, len(rows), flush=True)
    return pd.DataFrame(rows), drift


def evaluate(s, label):
    s = s.copy(); s['peak'] = s[label]; s['occupied'] = s[label] >= F.K   # history features follow the evaluated label
    s = F.add_history(s.drop(columns=[c for c in ('slot_rate', 'slot_peak', 'slot_n', 'roomhour_rate') if c in s]))
    out = {}; frames = []
    for tw in F.WEEKS:
        tr, te = s[s.week < tw], s[s.week == tw].copy()
        m = lgb.LGBMClassifier(n_estimators=150, num_leaves=7, min_child_samples=30, learning_rate=.05, random_state=42, n_jobs=2, verbosity=-1)
        m.fit(tr[F.FEATURES], tr.occupied); te['pred'] = m.predict_proba(te[F.FEATURES])[:, 1] >= .5
        te['hist'] = te.slot_rate >= .5; te['tt'] = False; frames.append(te)
    f = pd.concat(frames)
    return dict(occupied_share_all=float(s.occupied.mean()), model=F.metrics(f.occupied, f.pred),
                slot_history=F.metrics(f.occupied, f['hist']), timetable=F.metrics(f.occupied, f['tt']))   # f.hist would be DataFrame.hist (plot method)


def main():
    base = F.add_history(F.build_slots()); base['room_code'] = base.room.astype('category').cat.codes
    up, drift = build()
    s = base.merge(up, on=['room', 'day', 'hour'], how='left', validate='one_to_one')
    s = s.rename(columns={'peak': 'peak_lower'})
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                  continuous_minus_author_mean_people=float(np.mean(drift)),
                  lower=evaluate(s, 'peak_lower'), upper=evaluate(s, 'peak_upper'))
    lo, hi = report['lower'], report['upper']
    better = lambda r: r['slot_history']['recommend_precision'] is not None and r['slot_history']['recommend_precision'] > r['timetable']['recommend_precision']
    report['robust'] = bool(better(lo) and better(hi))   # None = rule recommends no slot at all
    (OUT / 'carryover.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    brief = lambda r: dict(share=round(r['occupied_share_all'], 3), **{k: dict(f1=round(r[k]['f1'], 3), rec_prec=None if r[k]['recommend_precision'] is None else round(r[k]['recommend_precision'], 3), cover=None if r[k]['vacant_coverage'] is None else round(r[k]['vacant_coverage'], 3), n_rec=r[k]['recommended_vacant']) for k in ('model', 'slot_history', 'timetable')})
    print('SUMMARY', json.dumps(dict(drift=round(report['continuous_minus_author_mean_people'], 2), lower=brief(lo), upper=brief(hi), robust=report['robust']), ensure_ascii=False))


if __name__ == '__main__':
    main()
