"""Historical slot rule for unscheduled room-hours (supplementary experiment 19, adopted 2026-11-24).

Experiment 19 compared "no class means vacant" (75.0% of recommended hours actually vacant), this rule
(84.1%, covering 90.2% of vacant hours) and a fixed LightGBM (not better than the rule). The rule:
a room-hour is predicted spontaneously used when, in strictly earlier weeks, the same room, weekday and hour
was used (peak >= 5 people under the authors' counting rule) in at least half of its unscheduled occurrences.
With no same-slot history it falls back to the all-room earlier rate, exactly as evaluated.

Scope: weekdays, whole hours 08:00-20:00, hours not overlapping any class window [start-15min, end).
Outside that scope the rule has no evidence and the room is never recommended. A candidate remains an
unverified historical candidate: on-site occupancy, bookings and access are never confirmed.
"""
import numpy as np
import pandas as pd

HOURS = range(8, 20)
LEAD = pd.Timedelta(minutes=15)
PEOPLE = 5
THRESHOLD = .5
EXCLUDED_WEEK = 9
# Frozen results of experiment 19 (lower-bound label) and experiment 21 (carry-over upper bound).
EVIDENCE = dict(recommend_precision=.841, vacant_coverage=.902, no_class_precision=.750,
                upper_bound_recommend_precision=.568, upper_bound_vacant_coverage=.140,
                source='02、模型实验/补充研究/19、无课时段空教室识别')
COLUMNS = ['timestamp', 'week', 'room_code', 'count_in', 'count_out', 'course_id', 'course_start', 'course_end']


def build_slot_history(computed):
    """Label every unscheduled weekday room-hour with its counted peak, as in experiment 19."""
    c = computed.loc[:, COLUMNS].copy()
    c['timestamp'] = pd.to_datetime(c.timestamp, errors='coerce')
    c = c[c.timestamp.notna() & c.week.ne(EXCLUDED_WEEK) & c.timestamp.dt.weekday.lt(5)]
    for name in ('count_in', 'count_out'):
        c[name] = pd.to_numeric(c[name], errors='coerce').fillna(0).astype(int)
    c['day'] = c.timestamp.dt.normalize()
    sched = c.dropna(subset=['course_id']).drop_duplicates(['room_code', 'day', 'course_id', 'course_start'])
    sched = sched.assign(s=sched.day + pd.to_timedelta(sched.course_start, errors='coerce'),
                         e=sched.day + pd.to_timedelta(sched.course_end, errors='coerce'))
    windows = {key: g[['s', 'e']] for key, g in sched.groupby(['room_code', 'day'])}
    none = pd.DataFrame({'s': pd.Series(dtype='datetime64[ns]'), 'e': pd.Series(dtype='datetime64[ns]')})
    rows = []
    for (room, day), g in c.sort_values('timestamp', kind='stable').groupby(['room_code', 'day']):
        sc = windows.get((room, day), none)
        ins, outs, ts = g.count_in.to_numpy(), g.count_out.to_numpy(), g.timestamp.to_numpy()
        for h in HOURS:
            a0, a1 = day + pd.Timedelta(hours=h), day + pd.Timedelta(hours=h + 1)
            if ((sc.s - LEAD < a1) & (sc.e > a0)).any():
                continue
            m = (ts >= np.datetime64(a0)) & (ts < np.datetime64(a1)); count = 0; peak = 0
            for i, o in zip(ins[m], outs[m]):
                count = max(0, count - o) + i; peak = max(peak, count)
            rows.append(dict(room=room, day=day, week=int(g.week.iloc[0]), weekday=day.weekday(), hour=h, peak=peak))
    s = pd.DataFrame(rows, columns=['room', 'day', 'week', 'weekday', 'hour', 'peak'])
    s['occupied'] = s.peak.ge(PEOPLE)
    return s.sort_values(['day', 'room', 'hour']).reset_index(drop=True)


def slot_rate(history, room, day, hour):
    """Rule input from strictly earlier days only; returns (rate, same-slot count) or None without any past."""
    day = pd.Timestamp(day).normalize()
    past = history[history.day.lt(day)]
    if past.empty:
        return None
    slot = past[past.room.eq(room) & past.weekday.eq(day.weekday()) & past.hour.eq(hour)]
    return (float(slot.occupied.mean()) if len(slot) else float(past.occupied.mean())), int(len(slot))


def hours_for(begin, end):
    """Whole hours overlapped by [begin, end), both given as offsets from midnight."""
    first = int(begin // pd.Timedelta(hours=1))
    last = int(-(-end // pd.Timedelta(hours=1))) - 1
    return list(range(first, last + 1))


def evaluate(history, room, day, begin, end, windows):
    """Decide one room for one requested interval.

    windows: (start, end) class intervals of that room on that day from every known schedule source.
    Returns dict(state, hours, rate, history_n) with state 'vacant', 'used' or 'outside_scope'.
    """
    day = pd.Timestamp(day).normalize()
    hours = hours_for(begin, end)
    outside = dict(state='outside_scope', hours=hours, rate=None, history_n=None)
    if day.weekday() >= 5 or not hours or hours[0] < HOURS.start or hours[-1] >= HOURS.stop:
        return outside
    for h in hours:
        a0, a1 = pd.Timedelta(hours=h), pd.Timedelta(hours=h + 1)
        if any(pd.notna(s) and pd.notna(e) and s - LEAD < a1 and e > a0 for s, e in windows):
            return outside
    found = [slot_rate(history, room, day, h) for h in hours]
    if any(x is None for x in found):
        return outside
    rate = max(x[0] for x in found)
    return dict(state='used' if rate >= THRESHOLD else 'vacant', hours=hours, rate=rate,
                history_n=min(x[1] for x in found))
