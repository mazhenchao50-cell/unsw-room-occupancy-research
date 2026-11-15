"""User-facing query support; suggestions retain capacity, duration and safety filters."""
from datetime import time
import pandas as pd
from replay import candidates
from i18n import t

EMPTY_PREDICTIONS=pd.DataFrame(columns=['session_id'])


def interval_text(start,minutes):
    begin=pd.to_timedelta(str(start));end=begin+pd.Timedelta(minutes=minutes)
    if pd.isna(begin) or begin<pd.Timedelta(0) or end>pd.Timedelta(days=1) or minutes<=0:
        raise ValueError('Invalid same-day interval')
    def clock(delta):
        value=int(delta.total_seconds()//60)
        return f'{value//60:02d}:{value%60:02d}'
    return clock(begin),clock(end)


def next_gap(sessions,attendance,day,start,minutes,capacity):
    """First strictly later 15-minute start, at most four hours ahead, same date."""
    candidates(sessions,attendance,EMPTY_PREDICTIONS,day,start,minutes,capacity)
    begin=pd.to_timedelta(str(start)).total_seconds()/60
    first=(int(begin)//15+1)*15
    for minute in range(first,min(int(begin+240),int(1440-float(minutes)))+1,15):
        trial=time(minute//60,minute%60)
        _,top,_=candidates(sessions,attendance,EMPTY_PREDICTIONS,day,trial,minutes,capacity)
        if len(top):return dict(start=trial,candidates=len(top))
    return None


def query_summary(locale,day,start,minutes,capacity):
    begin,end=interval_text(start,minutes)
    return t(locale,'query_summary').format(date=str(pd.Timestamp(day).date()),start=begin,end=end,seats=int(capacity))


def brief(top,room,locale,day,start,minutes,capacity):
    selected=top[top.room.eq(room)]
    if len(selected)!=1:raise ValueError('Select a current candidate')
    row=selected.iloc[0]
    if row.status!='timetable_gap_occupancy_unknown' or bool(row.verified_available) or row.seats<capacity:
        raise ValueError('Not an unverified timetable-gap candidate')
    return '\n\n'.join([t(locale,'brief_title'),t(locale,'brief_scope'),
        query_summary(locale,day,start,minutes,capacity),
        t(locale,'selected_summary').format(room=room,seats=int(row.seats),spare=int(row.seats-capacity)),
        t(locale,'candidate_basis'),t(locale,'next_steps'),t(locale,'time_basis')])+'\n'
