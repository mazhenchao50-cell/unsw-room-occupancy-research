"""Historical candidate search. A timetable gap is never occupancy ground truth."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码'))
import pandas as pd
import numpy as np
import joblib
from numbers import Real
from models.revised import raw_features, predict, ROOT

def candidates(sessions, attendance, predictions, date, start, duration=60, minimum_seats=1):
    if (isinstance(duration,bool) or not isinstance(duration,Real) or not np.isfinite(duration) or duration<=0
        or isinstance(minimum_seats,bool) or not isinstance(minimum_seats,Real) or not np.isfinite(minimum_seats)
        or minimum_seats<1 or not float(minimum_seats).is_integer()):
        raise ValueError('Invalid interval or capacity')
    day=pd.Timestamp(date).normalize(); begin=pd.to_timedelta(str(start),errors='coerce')
    if pd.isna(day) or pd.isna(begin) or begin<pd.Timedelta(0) or begin>=pd.Timedelta(days=1):
        raise ValueError('Invalid date or start time')
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
        day_covered=bool(len(a) or len(k))
        status='scheduled_conflict' if conflict else 'schedule_unknown' if incomplete or not day_covered else 'timetable_gap_occupancy_unknown'
        rows.append({'room':room,'seats':int(seats),'status':status,'verified_available':False,
                     'reason':'课表冲突，不推荐' if conflict else '课表信息不足' if status=='schedule_unknown' else '仅为课表空档候选，现场占用及开放权限待核实'})
    all_rows=pd.DataFrame(rows,columns=['room','seats','status','verified_available','reason'])
    top=all_rows[all_rows.status.eq('timetable_gap_occupancy_unknown')].sort_values(['seats','room']).head(5)
    ks=pd.to_timedelta(known.course_start,errors='coerce');ke=pd.to_timedelta(known.course_end,errors='coerce')
    active=known[valid_intervals(ks,ke)&(ks<end)&(ke>begin)]
    scored=active.merge(predictions,on='session_id',how='left',suffixes=('','_prediction'),validate='one_to_one')
    return all_rows,top,scored


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

def evaluate():
    import json
    s=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv'); a=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv')
    b=joblib.load(ROOT/'02、模型实验/生成产物/revised/model.joblib'); ns=joblib.load(ROOT/'02、模型实验/生成产物/revised/no_show.joblib')
    p=replay_predictions(s,b,ns); rows=[]; count=0
    for day in sorted(s.loc[s.week.eq(12),'date'].unique()):
        for hour in range(8,19):
            all_rows,top,active=candidates(s,a,p,day,f'{hour:02d}:00:00')
            assert top.status.eq('timetable_gap_occupancy_unknown').all()
            count+=1
            for row in top.to_dict('records'): rows.append({'date':day,'hour':hour,**row})
    pd.DataFrame(rows).to_csv(ROOT/'02、模型实验/生成产物/revised/replay_candidates.csv',index=False)
    from models.revised import dump
    dump(ROOT/'02、模型实验/生成产物/revised/replay_report.json',{'queries':count,'candidate_rows':len(rows),'top_k':5,'conflict_violations':0,
        'verified_availability_precision':None,'reason':'No occupancy/access ground truth for timetable gaps. Low-utilization scheduled sessions remain blocked.',
        'ranking':'Smallest sufficient capacity, room name tie-break. Occupancy prediction only for labelled scheduled-session domain.'})

if __name__=='__main__': evaluate()
