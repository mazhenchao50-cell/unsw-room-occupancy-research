"""Attendance-table-only cross-semester diagnostic, separate from sensor-session benchmark."""
import pandas as pd
from revised import ROOT,fit_selected,metrics,dump,prediction_frame

a=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv').rename(columns={'room_code':'room','start_time':'course_start','end_time':'course_end','enrollment':'enrollments','attendance':'attendees'})
a['date']=pd.to_datetime(a.date);a['occupancy_rate']=a.attendees/a.seats
a=a[a.occupancy_rate.notna() & a.seats.gt(0)].copy()
a['weekday']=a.date.dt.weekday;a['is_weekend']=a.weekday.ge(5).astype(int)
a['is_morning']=(pd.to_timedelta(a.course_start).dt.total_seconds()<43200).astype(int)
a['course_id']='unavailable';a['session_id']=['attendance-'+str(i) for i in a.index]
train=a[a.year.eq(2017)&a.week.lt(12)&a.week.ne(9)]; valid=a[a.year.eq(2017)&a.week.eq(12)]
final=a[a.year.eq(2017)&a.week.ne(9)]; test=a[a.year.eq(2018)]
r={'scope':'Separate attendance-table experiment: attendance/seats, no course history. Does not validate sensor-model transfer or match original-paper cleaning.',
   'n_2017':len(final),'n_2018':len(test),'scores':{}}
for name in ['LightGBM','RF','MLR','SVR']:
    p,b,trials=fit_selected(name,train,valid,final,test,False)
    r['scores'][name]=metrics(test.occupancy_rate,p)
    prediction_frame(test,p).to_csv(ROOT/f'02、模型实验/生成产物/revised/transfer2018_{name}.csv',index=False)
dump(ROOT/'02、模型实验/生成产物/revised/transfer2018_report.json',r)
