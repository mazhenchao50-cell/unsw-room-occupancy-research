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
from replay import candidates
from models.revised import ROOT,dump

def run():
    sessions=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv')
    attendance=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv')
    predictions=pd.read_csv(ROOT/'02、模型实验/生成产物/revised/test_predictions.csv')
    dates=sorted(sessions.loc[sessions.week.eq(12),'date'].unique())
    capacities=sessions.groupby('room').seats.max().to_dict()
    rows=[]
    for day,hour,duration,minimum in itertools.product(dates,[8,9,12,18],[15,60,240],[1,35,246,497]):
        start=pd.Timedelta(hours=hour);end=start+pd.Timedelta(minutes=duration)
        rooms,top,active=candidates(sessions,attendance,predictions,day,f'{hour:02}:00:00',duration,minimum)
        eligible=[]
        for room,seats in capacities.items():
            if seats<minimum:continue
            timetable=attendance[attendance.date.eq(day)&attendance.room_code.eq(room)]
            observed=sessions[sessions.date.eq(day)&sessions.room.eq(room)]
            intervals=list(zip(timetable.start_time,timetable.end_time))+list(zip(observed.course_start,observed.course_end))
            if not intervals:continue
            valid=True
            for a,b in intervals:
                a=pd.to_timedelta(a,errors='coerce');b=pd.to_timedelta(b,errors='coerce')
                if pd.isna(a) or pd.isna(b) or a<pd.Timedelta(0) or b>pd.Timedelta(days=1) or b<=a or (a<end and b>start):
                    valid=False;break
            if valid:eligible.append((seats,room))
        expected=[room for seats,room in sorted(eligible)[:5]]
        assert top.room.tolist()==expected,(day,hour,duration,minimum)
        assert not top.verified_available.any()
        assert top.seats.ge(minimum).all()
        assert active.prediction.notna().all()
        rows.append({'date':day,'hour':hour,'duration_minutes':duration,'minimum_seats':minimum,
                     'candidate_rooms':top.room.tolist(),'scheduled_predictions':len(active),'passed':True})
    out=ROOT/'02、模型实验/生成产物/system';out.mkdir(parents=True,exist_ok=True)
    dump(out/'real_data_queries.json',rows)
    primary=json.loads((ROOT/'02、模型实验/生成产物/revised/report.json').read_text(encoding='utf-8'))
    dump(out/'functional_report.json',{
        'date':datetime.now(timezone(timedelta(hours=9))).date().isoformat(),'kind':'Automated functional checks using existing real UNSW historical records.',
        'queries':len(rows),'passed':len(rows),'candidate_rows':sum(len(r['candidate_rooms']) for r in rows),
        'zero_candidate_queries':sum(not r['candidate_rooms'] for r in rows),
        'checks':['capacity','schedule conflict','incomplete schedule exclusion','smallest sufficient capacity ranking',
                  'top5','unknown on-site availability retained','scheduled predictions present'],
        'no_show':primary['no_show'],
        'human_trials':0,'onsite_availability_accuracy':None,
        'acceptance':'Functional evidence only. No-show utility, deployment and independent reproduction remain separate.',
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),
            ROOT/'03、系统应用/代码/replay.py',ROOT/'01、数据处理/清洗产物/sessions.csv',ROOT/'01、数据处理/清洗产物/attendance_clean.csv',
            ROOT/'02、模型实验/生成产物/revised/test_predictions.csv']}})
    print('PASS:',len(rows),'real-data query scenarios')

if __name__=='__main__':run()
