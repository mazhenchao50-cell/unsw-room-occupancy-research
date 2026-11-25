"""Audit observed-zero labels without relabelling, dropping samples or retuning."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码'))
import hashlib
from datetime import datetime, timezone, timedelta
import pandas as pd
from models.revised import ROOT,dump

def run():
    paths=[ROOT/'01、数据处理/清洗产物'/name for name in ['sessions.csv','clean_computed.csv','attendance_clean.csv']]
    sessions,computed,attendance=[pd.read_csv(p) for p in paths]
    grouped=computed[computed.course_id.notna()].groupby(['date','room_code','course_id']).agg(
        event_rows=('timestamp','size'),valid_label_rows=('num_attendees','count'),
        first_event=('timestamp','min'),last_event=('timestamp','max'))
    grouped.index.names=['date','room','course_id']
    valid=computed[computed.course_id.notna() & computed.num_attendees.notna()].copy()
    valid['timestamp']=pd.to_datetime(valid.timestamp)
    valid=valid.sort_values(['date','room_code','course_id','timestamp'])
    valid['gap_minutes']=valid.groupby(['date','room_code','course_id']).timestamp.diff().dt.total_seconds()/60
    gaps=valid.groupby(['date','room_code','course_id']).gap_minutes.max().rename('max_internal_gap_minutes')
    gaps.index.names=['date','room','course_id']
    evidence=sessions.merge(grouped,on=['date','room','course_id'],how='left',validate='one_to_one')
    evidence=evidence.merge(gaps,on=['date','room','course_id'],how='left',validate='one_to_one')
    zeros=evidence[evidence.attendees.eq(0)]
    zeros=zeros.copy()
    start=pd.to_datetime(zeros.date+' '+zeros.course_start)
    end=pd.to_datetime(zeros.date+' '+zeros.course_end)
    first=pd.to_datetime(zeros.first_event)
    last=pd.to_datetime(zeros.last_event)
    zeros['first_observation_delay_minutes']=(first-start).dt.total_seconds()/60
    zeros['last_observation_early_minutes']=(end-last).dt.total_seconds()/60
    zeros['observed_span_fraction']=(last-first).dt.total_seconds()/(end-start).dt.total_seconds()
    bydate=zeros.groupby('date').size().sort_values(ascending=False)
    out=ROOT/'02、模型实验/生成产物/label_audit';out.mkdir(parents=True,exist_ok=True)
    zeros.to_csv(out/'observed_zero_sessions.csv',index=False)
    summary={'audit_date':datetime.now(timezone(timedelta(hours=9))).date().isoformat(),'total_sessions':len(sessions),
        'valid_label_sessions':int(sessions.attendees.notna().sum()),'observed_zero_sessions':len(zeros),
        'zero_schedule_matches':{str(k):int(v) for k,v in zeros.schedule_match.value_counts().items()},
        'zero_missing_enrollment':int(zeros.enrollments.isna().sum()),
        'zero_nonpositive_enrollment':int(zeros.enrollments.le(0).sum()),
        'zero_observation_count_min':int(zeros.valid_label_rows.min()),
        'zero_observation_count_median':float(zeros.valid_label_rows.median()),
        'zero_boundary_within_10_minutes':int((zeros.first_observation_delay_minutes.le(10)&zeros.last_observation_early_minutes.le(10)).sum()),
        'zero_first_delay_over_10_minutes':int(zeros.first_observation_delay_minutes.gt(10).sum()),
        'zero_last_early_over_10_minutes':int(zeros.last_observation_early_minutes.gt(10).sum()),
        'zero_max_internal_gap_minutes':float(zeros.max_internal_gap_minutes.max()),
        'zero_internal_gap_over_10_minutes':int(zeros.max_internal_gap_minutes.gt(10).sum()),
        'zero_observed_span_fraction_median':float(zeros.observed_span_fraction.median()),
        'zero_by_date':{str(k):int(v) for k,v in bydate.items()},
        'attendance_2017_zero_rows':int((attendance.year.eq(2017)&attendance.attendance.eq(0)).sum()),
        'interpretation':['Observed sensor-derived peak zero is a proxy, not independently confirmed absence.',
            'No exact attendance match is not proof of an erroneous label; attendance also contains no zero rows.',
            'Concentration on one date is a diagnostic signal, not proof of outage, cancellation or holiday.',
            'Boundary and gap checks assess temporal sampling only, not sensor accuracy, cancellation cause or uninterrupted occupancy.',
            'Labels are retained unchanged; no post-test exclusion used to improve metrics.'],
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]}}
    dump(out/'report.json',summary)
    print('Observed zeros:',len(zeros),'schedule matching:',summary['zero_schedule_matches'],'largest date count:',int(bydate.iloc[0]))
    return summary

if __name__=='__main__':run()
