"""User-facing query support; suggestions retain capacity, duration and safety filters."""
from datetime import time
import pandas as pd
from replay import candidates,LISTED
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


def next_gap(sessions,attendance,day,start,minutes,capacity,coverage=None,slot_history=None):
    """First strictly later 15-minute start, at most four hours ahead, same date.

    Returns None both when the search finds nothing and when no evidence source exists;
    callers must only claim a completed search when coverage or slot_history was supplied.
    """
    candidates(sessions,attendance,EMPTY_PREDICTIONS,day,start,minutes,capacity,coverage=coverage,slot_history=slot_history)
    if not coverage and slot_history is None:return None
    begin=pd.to_timedelta(str(start)).total_seconds()/60
    first=(int(begin)//15+1)*15
    for minute in range(first,min(int(begin+240),int(1440-float(minutes)))+1,15):
        trial=time(minute//60,minute%60)
        _,top,_=candidates(sessions,attendance,EMPTY_PREDICTIONS,day,trial,minutes,capacity,coverage=coverage,slot_history=slot_history)
        if len(top):return dict(start=trial,candidates=len(top))
    return None


def query_summary(locale,day,start,minutes,capacity):
    begin,end=interval_text(start,minutes)
    return t(locale,'query_summary').format(date=str(pd.Timestamp(day).date()),start=begin,end=end,seats=int(capacity))


def brief(top,room,locale,day,start,minutes,capacity):
    selected=top[top.room.eq(room)]
    if len(selected)!=1:raise ValueError('Select a current candidate')
    row=selected.iloc[0]
    if row.status not in LISTED or bool(row.verified_available) or row.seats<capacity:
        raise ValueError('Not an unverified timetable-gap candidate')
    return '\n\n'.join([t(locale,'brief_title'),t(locale,'brief_scope'),
        query_summary(locale,day,start,minutes,capacity),
        t(locale,'selected_summary').format(room=room,seats=int(row.seats),spare=int(row.seats-capacity)),
        basis(locale,row),t(locale,'next_steps'),t(locale,'time_basis')])+'\n'


def basis(locale,row):
    """Why one listed room appears; the slot-rule wording carries its measured historical reliability."""
    if row.status!='history_rule_candidate':return t(locale,'candidate_basis')
    key='history_basis' if int(row.history_n) else 'history_basis_prior'
    return t(locale,key).format(rate=f'{float(row.history_rate):.0%}',n=int(row.history_n))
