"""Functional evidence on real historical records; not a human usability study."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03、系统应用/代码'))
import hashlib
import itertools
import json
from datetime import datetime,timedelta,timezone
import pandas as pd
from replay import candidates,load_slot_history
from models.revised import ROOT,dump


def independent_rule_check(slots,sessions,attendance,day,room,start,end):
    """Recompute the experiment-19 decision for one listed room without the production helper."""
    query=pd.Timestamp(day)
    assert query.weekday()<5
    windows=[(pd.to_timedelta(a,errors='coerce'),pd.to_timedelta(b,errors='coerce')) for a,b in
             list(zip(attendance.loc[attendance.date.eq(day)&attendance.room_code.eq(room),'start_time'],attendance.loc[attendance.date.eq(day)&attendance.room_code.eq(room),'end_time']))
             +list(zip(sessions.loc[sessions.date.eq(day)&sessions.room.eq(room),'course_start'],sessions.loc[sessions.date.eq(day)&sessions.room.eq(room),'course_end']))]
    hours=range(int(start.total_seconds()//3600),int(-(-end.total_seconds()//3600)))
    rates=[]
    for h in hours:
        assert 8<=h<20,(day,room,h)
        a0,a1=pd.Timedelta(hours=h),pd.Timedelta(hours=h+1)
        assert not any(pd.notna(s) and pd.notna(e) and s-pd.Timedelta(minutes=15)<a1 and e>a0 for s,e in windows),(day,room,h)
        past=slots[slots.day.lt(query)]
        same=past[past.room.eq(room)&past.day.dt.weekday.eq(query.weekday())&past.hour.eq(h)]
        rates.append(same.occupied.mean() if len(same) else past.occupied.mean())
    assert max(rates)<.5,(day,room,rates)
    return float(max(rates))

def run():
    sessions=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv')
    attendance=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv')
    predictions=pd.read_csv(ROOT/'02、模型实验/生成产物/revised/test_predictions.csv')
    slots=load_slot_history(ROOT)
    dates=sorted(sessions.loc[sessions.week.eq(12),'date'].unique())
    capacities=sessions.groupby('room').seats.max().to_dict()
    rows=[]
    for day,hour,duration,minimum in itertools.product(dates,[8,9,12,18],[15,60,240],[1,35,246,497]):
        start=pd.Timedelta(hours=hour);end=start+pd.Timedelta(minutes=duration)
        rooms,top,active=candidates(sessions,attendance,predictions,day,f'{hour:02}:00:00',duration,minimum)
        expected_status={}
        for room,seats in capacities.items():
            if seats<minimum:continue
            timetable=attendance[attendance.date.eq(day)&attendance.room_code.eq(room)]
            observed=sessions[sessions.date.eq(day)&sessions.room.eq(room)]
            intervals=list(zip(timetable.start_time,timetable.end_time))+list(zip(observed.course_start,observed.course_end))
            conflict=False
            for a,b in intervals:
                a=pd.to_timedelta(a,errors='coerce');b=pd.to_timedelta(b,errors='coerce')
                if pd.notna(a) and pd.notna(b) and a<end and b>start:conflict=True
            expected_status[room]='scheduled_conflict' if conflict else 'schedule_unknown'
        assert rooms.set_index('room').status.to_dict()==expected_status,(day,hour,duration,minimum)
        assert top.empty,'Without the slot rule, no authoritative complete-day schedule coverage is present in this input'
        assert active.prediction.notna().all()
        # With the experiment-19 slot rule: conflicts stay blocked; every listed room is rechecked independently.
        ruled,top,_=candidates(sessions,attendance,predictions,day,f'{hour:02}:00:00',duration,minimum,slot_history=slots)
        statuses=ruled.set_index('room').status
        assert all(statuses[r]=='scheduled_conflict' for r,s in expected_status.items() if s=='scheduled_conflict')
        assert set(statuses)<= {'scheduled_conflict','schedule_unknown','history_rule_candidate','history_rule_likely_used'}
        assert top.status.eq('history_rule_candidate').all() and not top.verified_available.any() and top.seats.ge(minimum).all()
        for row in top.itertuples():
            rate=independent_rule_check(slots,sessions,attendance,day,row.room,start,end)
            assert abs(rate-row.history_rate)<1e-12,(day,row.room,rate,row.history_rate)
        rows.append({'date':day,'hour':hour,'duration_minutes':duration,'minimum_seats':minimum,
                     'candidate_rooms':top.room.tolist(),'likely_used_rooms':statuses[statuses.eq('history_rule_likely_used')].index.tolist(),
                     'scheduled_predictions':len(active),'passed':True})
    out=ROOT/'02、模型实验/生成产物/system';out.mkdir(parents=True,exist_ok=True)
    dump(out/'real_data_queries.json',rows)
    primary=json.loads((ROOT/'02、模型实验/生成产物/revised/report.json').read_text(encoding='utf-8'))
    dump(out/'functional_report.json',{
        'date':datetime.now(timezone(timedelta(hours=9))).date().isoformat(),'kind':'Automated functional checks using existing real UNSW historical records.',
        'queries':len(rows),'passed':len(rows),'candidate_rows':sum(len(r['candidate_rooms']) for r in rows),
        'zero_candidate_queries':sum(not r['candidate_rooms'] for r in rows),
        'checks':['capacity','independently recomputed known conflicts','missing full-day schedule coverage',
                  'no gap recommendation without coverage or slot rule','slot-rule candidates independently recomputed (weekday 08-20, no class window with 15-minute lead, strictly earlier same-slot share below 0.5)',
                  'unknown on-site availability retained','scheduled predictions present'],
        'candidate_source':'Experiment-19 historical slot rule, adopted 2026-11-24',
        'no_show':primary['no_show'],
        'human_trials':0,'onsite_availability_accuracy':None,
        'acceptance':'Functional evidence only. No-show utility, deployment and independent reproduction remain separate.',
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),
            ROOT/'03、系统应用/代码/replay.py',ROOT/'03、系统应用/代码/free_slot_rule.py',ROOT/'01、数据处理/清洗产物/clean_computed.csv',ROOT/'01、数据处理/清洗产物/sessions.csv',ROOT/'01、数据处理/清洗产物/attendance_clean.csv',
            ROOT/'02、模型实验/生成产物/revised/test_predictions.csv']}})
    print('PASS:',len(rows),'real-data query scenarios')

if __name__=='__main__':run()
