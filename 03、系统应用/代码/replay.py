"""Historical candidate search. A timetable gap is never occupancy ground truth.

Two evidence sources can list a room: caller-supplied authoritative full-day coverage
('timetable_gap_occupancy_unknown'), or the experiment-19 historical slot rule
('history_rule_candidate'). Neither verifies on-site occupancy or access.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd
import numpy as np
import joblib
from numbers import Real
from datetime import date as Date, datetime, time as Time
import re
from models.revised import raw_features, predict, ROOT
import free_slot_rule as SLOT

LISTED=('timetable_gap_occupancy_unknown','history_rule_candidate')

def candidates(sessions, attendance, predictions, date, start, duration=60, minimum_seats=1, coverage=None, slot_history=None):
    if (isinstance(duration,bool) or not isinstance(duration,Real) or not np.isfinite(duration) or duration<=0
        or isinstance(minimum_seats,bool) or not isinstance(minimum_seats,Real) or not np.isfinite(minimum_seats)
        or minimum_seats<1 or not float(minimum_seats).is_integer()):
        raise ValueError('Invalid interval or capacity')
    if not isinstance(date,(str,Date,datetime,pd.Timestamp)) or pd.isna(date):
        raise ValueError('Invalid date or start time')
    if isinstance(date,str) and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):
        raise ValueError('Date must be ISO YYYY-MM-DD')
    try:
        day=pd.Timestamp(date)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid date') from exc
    if pd.isna(day) or day.tzinfo is not None or day != day.normalize():
        raise ValueError('Date must be a timezone-free calendar day')
    value=str(start)
    match=re.fullmatch(r'(\d{2}):(\d{2})(?::(\d{2}))?',value)
    if match is None or any(int(v or 0)>limit for v,limit in zip(match.groups(),(23,59,59))):
        raise ValueError('Invalid date or start time')
    begin=pd.Timedelta(hours=int(match[1]),minutes=int(match[2]),seconds=int(match[3] or 0))
    end=begin+pd.Timedelta(minutes=duration)
    if end>pd.Timedelta(days=1):raise ValueError('Invalid interval or capacity')
    schedules=attendance[pd.to_datetime(attendance.date).eq(day)].copy()
    known=sessions[pd.to_datetime(sessions.date).eq(day)].copy()
    rooms=sessions.groupby('room').seats.max()
    rows=[]
    for room,seats in rooms.items():
        if not np.isfinite(seats) or seats<minimum_seats: continue
        a=schedules[schedules.room_code.eq(room)]
        k=known[known.room.eq(room)]
        starts=pd.to_timedelta(a.start_time,errors='coerce'); ends=pd.to_timedelta(a.end_time,errors='coerce')
        ks=pd.to_timedelta(k.course_start,errors='coerce'); ke=pd.to_timedelta(k.course_end,errors='coerce')
        conflict=bool(((starts<end)&(ends>begin)).any() or ((ks<end)&(ke>begin)).any())
        valid_schedule=valid_intervals(starts,ends)
        valid_known=valid_intervals(ks,ke)
        incomplete=bool((~valid_schedule).any() or (~valid_known).any())
        # Observing one class never establishes a complete timetable for the day.
        # Only caller-supplied authoritative coverage metadata can establish it.
        evidence=(coverage or {}).get((str(day.date()),room),{})
        day_covered=bool(evidence.get('complete') is True and evidence.get('source'))
        status='scheduled_conflict' if conflict else 'schedule_unknown' if incomplete or not day_covered else 'timetable_gap_occupancy_unknown'
        rule=dict(rate=None,history_n=None)
        if status=='schedule_unknown' and not incomplete and slot_history is not None:
            # Experiment-19 rule: every overlapped whole hour must be an in-scope unscheduled hour whose
            # strictly earlier same-slot spontaneous-use share is below one half.
            rule=SLOT.evaluate(slot_history,room,day,begin,end,list(zip(starts,ends))+list(zip(ks,ke)))
            status={'vacant':'history_rule_candidate','used':'history_rule_likely_used'}.get(rule['state'],status)
        reasons={'scheduled_conflict':'课表冲突，不推荐','schedule_unknown':'课表信息不足或超出历史规则范围',
                 'timetable_gap_occupancy_unknown':'仅为课表空档候选，现场占用及开放权限待核实',
                 'history_rule_candidate':'历史时段规则候选，现场占用及开放权限待核实',
                 'history_rule_likely_used':'此前同时段常被自发占用，不推荐'}
        times,free=conflict_detail(list(zip(starts,ends))+list(zip(ks,ke)),begin,end) if status=='scheduled_conflict' else (None,None)
        rows.append({'room':room,'seats':int(seats),'status':status,'verified_available':False,'reason':reasons[status],
                     'history_rate':rule['rate'],'history_n':rule['history_n'],'conflict_times':times,'free_from':free})
    all_rows=pd.DataFrame(rows,columns=['room','seats','status','verified_available','reason','history_rate','history_n','conflict_times','free_from'])
    top=all_rows[all_rows.status.isin(LISTED)].sort_values(['seats','room']).head(5)
    ks=pd.to_timedelta(known.course_start,errors='coerce');ke=pd.to_timedelta(known.course_end,errors='coerce')
    active=known[valid_intervals(ks,ke)&(ks<end)&(ke>begin)]
    scored=active.merge(predictions,on='session_id',how='left',suffixes=('','_prediction'),validate='one_to_one')
    return all_rows,top,scored


def conflict_detail(intervals,begin,end):
    """Known classes overlapping [begin,end) and the end of the back-to-back class block (heuristic review F8).

    Returns ('HH:MM–HH:MM, …', 'HH:MM'); only an end of known classes, never a confirmed vacancy.
    """
    def clock(delta):
        minutes=int(delta.total_seconds()//60);return f'{minutes//60:02d}:{minutes%60:02d}'
    known=sorted({(s,e) for s,e in intervals if pd.notna(s) and pd.notna(e) and e>s})
    hits=[(s,e) for s,e in known if s<end and e>begin]
    if not hits:return None,None
    free=max(e for _,e in hits);changed=True
    while changed:
        changed=False
        for s,e in known:
            if s<=free<e:free=e;changed=True
    return ', '.join(f'{clock(s)}–{clock(e)}' for s,e in hits),clock(free)


def valid_intervals(starts,ends):
    """Only same-day, positive-length known schedule intervals are interpretable."""
    return starts.notna() & ends.notna() & starts.ge(pd.Timedelta(0)) & ends.le(pd.Timedelta(days=1)) & ends.gt(starts)

def replay_predictions(sessions, model, no_show_model):
    sessions=sessions.copy(); sessions['date']=pd.to_datetime(sessions.date)
    # Only after training cutoff. Earlier dates cannot be predicted by a later fitted model.
    sessions=sessions[sessions.date>model['reference'].date.max()]
    sessions=sessions[sessions.week.eq(12)]
    p=predict(model,sessions)
    x=raw_features(no_show_model['reference'],sessions).fillna(no_show_model['median'])
    prob=no_show_model['model'].predict_proba(x)[:,1]
    return pd.DataFrame({'session_id':sessions.session_id,'prediction':p,'no_show_probability':prob,'no_show_alert':prob>=no_show_model['threshold']})

def load_slot_history(root=ROOT):
    """Unscheduled weekday room-hours labelled with the experiment-19 counting rule."""
    return SLOT.build_slot_history(pd.read_csv(Path(root)/'01、数据处理/清洗产物/clean_computed.csv',usecols=SLOT.COLUMNS))


def rule_reproduction(history,weeks=(8,10,11,12)):
    """Re-apply the rule to every evaluated unscheduled hour and recompute the experiment-19 figures."""
    rows=history[history.week.isin(weeks)]
    pred=np.array([SLOT.slot_rate(history,r.room,r.day,r.hour)[0]>=SLOT.THRESHOLD for r in rows.itertuples()])
    vacant=~rows.occupied.to_numpy();recommended=~pred
    return dict(weeks=list(weeks),slots=int(len(rows)),recommended=int(recommended.sum()),
        recommend_precision=float((vacant&recommended).sum()/recommended.sum()),
        vacant_coverage=float((vacant&recommended).sum()/vacant.sum()),no_class_precision=float(vacant.mean()))


def evaluate():
    s=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv'); a=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv')
    b=joblib.load(ROOT/'02、模型实验/生成产物/revised/model.joblib'); ns=joblib.load(ROOT/'02、模型实验/生成产物/revised/no_show.joblib')
    history=load_slot_history()
    labels=history.assign(day=history.day.dt.strftime('%Y-%m-%d')).set_index(['room','day','hour']).occupied
    p=replay_predictions(s,b,ns); rows=[]; count=0; zero=0; hours_checked=[]
    for day in sorted(s.loc[s.week.eq(12),'date'].unique()):
        for hour in range(8,19):
            all_rows,top,active=candidates(s,a,p,day,f'{hour:02d}:00:00',slot_history=history)
            assert top.status.isin(LISTED).all() and top.history_rate.lt(SLOT.THRESHOLD).all()
            count+=1; zero+=top.empty
            for row in top.to_dict('records'):
                # The query day's own sensor label is used only here, after the fact, to score the replay.
                key=(row['room'],day,hour)
                hours_checked.append(None if key not in labels.index else not bool(labels[key]))
                rows.append({'date':day,'hour':hour,**row})
    pd.DataFrame(rows,columns=['date','hour','room','seats','status','verified_available','reason','history_rate','history_n']).to_csv(ROOT/'02、模型实验/生成产物/revised/replay_candidates.csv',index=False)
    scored=[x for x in hours_checked if x is not None]
    reproduction=rule_reproduction(history)
    for key in ('recommend_precision','vacant_coverage','no_class_precision'):
        if round(reproduction[key],3)!=SLOT.EVIDENCE[key]:raise ValueError('Slot rule no longer reproduces experiment 19: '+key)
    from models.revised import dump
    dump(ROOT/'02、模型实验/生成产物/revised/replay_report.json',{'queries':count,'candidate_rows':len(rows),'zero_candidate_queries':int(zero),'top_k':5,'conflict_violations':0,
        'candidate_source':'Experiment-19 historical slot rule (adopted 2026-11-24): no known class window [start-15min,end) in any overlapped weekday hour 08-20, and strictly earlier same room/weekday/hour spontaneous-use share (peak>=5) below 0.5.',
        'rule_reproduction':reproduction,'evidence':SLOT.EVIDENCE,
        'week12_replay_candidates_vacant':dict(scored=len(scored),vacant=int(sum(scored)),share=float(np.mean(scored)) if scored else None,
            note='Same-day sensor labels are used only after the fact to score week-12 candidates at whole-hour 60-minute queries; label resets each hour (lower bound of spontaneous use).'),
        'verified_availability_precision':None,'reason':'No on-site occupancy/access ground truth. Low-utilization scheduled sessions remain blocked.',
        'ranking':'Smallest sufficient capacity, room name tie-break. Occupancy prediction only for labelled scheduled-session domain.'})

if __name__=='__main__': evaluate()
