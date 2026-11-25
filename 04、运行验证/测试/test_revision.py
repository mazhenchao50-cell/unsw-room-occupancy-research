import sys, unittest, json
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'03、系统应用/代码'))
sys.path.insert(0,str(ROOT/'02、模型实验/代码'))
from models.revised import history,matrices,load,raw_features,binary_metrics
from replay import candidates

class RevisionTests(unittest.TestCase):
    def test_history_cannot_see_own_same_day_or_future_labels(self):
        d=pd.DataFrame({'date':pd.to_datetime(['2017-01-01','2017-01-02','2017-01-02','2017-01-03']),
                        'course_id':['x']*4,'occupancy_rate':[.2,.4,.6,.8]})
        a=history(d,d)
        np.testing.assert_allclose(a.course_hist_mean,[.3,.2,.2,.4])
        d.loc[1:,'occupancy_rate']=999
        np.testing.assert_allclose(history(d,d).course_hist_mean[:3],a.course_hist_mean[:3])

    def test_fold_median_ignores_query_values(self):
        d=load(); tr=d[d.room.ne('BUS 105')]; te=d[d.room.eq('BUS 105')].copy()
        _,_,med=matrices(tr,te); te['enrollments']=999999
        _,_,changed=matrices(tr,te)
        pd.testing.assert_series_equal(med,changed)
        self.assertEqual(med.enrollments,tr.enrollments.median())

    def test_complete_time(self):
        d=load().head(1).copy(); d['course_start']='12:30:00';d['course_end']='14:00:00'
        x=raw_features(d,d,False)
        self.assertEqual(float(x.duration_h.iloc[0]),1.5)
        self.assertEqual(float(x.course_start_h.iloc[0]),12.5)

    def test_data_join_and_finite_values(self):
        d=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv'); a=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv')
        self.assertEqual(len(d),2362);self.assertTrue(d.session_id.is_unique)
        self.assertFalse(np.isinf(d.select_dtypes('number')).any().any())
        a=a[a.year.eq(2017)].rename(columns={'room_code':'room','start_time':'course_start','end_time':'course_end'})
        keys=['date','room','course_start','course_end']; a=a[~a.duplicated(keys,keep=False)]
        m=d[d.schedule_match.eq('matched')].merge(a,on=keys,validate='many_to_one')
        np.testing.assert_allclose(m.enroll_sched,m.enrollment,equal_nan=True)
        np.testing.assert_allclose(m.attend_sched,m.attendance,equal_nan=True)
        self.assertTrue(d.loc[d.enrollments.le(0),'attend_rate'].isna().all())

    def test_unknown_is_not_empty_and_end_boundary(self):
        s=pd.DataFrame([{'room':'A','seats':30,'date':'2017-01-01','course_start':'09:00:00','course_end':'10:00:00','session_id':'s'}])
        a=pd.DataFrame([{'room_code':'A','date':'2017-01-01','start_time':'09:00:00','end_time':'10:00:00'}])
        p=pd.DataFrame({'session_id':['s'],'prediction':[0.]})
        _,top,_=candidates(s,a,p,'2017-01-01','09:30:00'); self.assertEqual(len(top),0)
        _,top,_=candidates(s,a,p,'2017-01-01','10:00:00',coverage={('2017-01-01','A'):{'complete':True,'source':'synthetic complete schedule'}}); self.assertEqual(len(top),1)
        self.assertFalse(top.verified_available.any())
        _,top,_=candidates(s,a,p,'2017-01-02','10:00:00'); self.assertEqual(len(top),0)

    def test_low_utilization_is_not_no_show(self):
        y=np.array([0,1,30]); seats=np.array([100,100,497])
        self.assertEqual(int((y/seats<.1).sum()),3); self.assertEqual(int((y==0).sum()),1)
        self.assertIsNone(binary_metrics([False],[False])['precision_wilson_95'])

    def test_report_json_is_strict_and_predictions_complete(self):
        def reject(x):raise ValueError(x)
        for f in (ROOT/'02、模型实验/生成产物/revised').glob('*.json'):json.loads(f.read_text(encoding='utf-8'),parse_constant=reject)
        r=json.loads((ROOT/'02、模型实验/生成产物/revised/report.json').read_text(encoding='utf-8'))
        p=pd.read_csv(ROOT/'02、模型实验/生成产物/revised/loro_predictions.csv')
        self.assertEqual(len(p),2360);self.assertTrue(p.session_id.is_unique);self.assertFalse(p.week.eq(9).any())
        self.assertEqual(r['loro']['micro']['n'],len(p))
        p=pd.read_csv(ROOT/'02、模型实验/生成产物/revised/test_predictions.csv');self.assertTrue(p.p90.ge(p.p10).all())
        self.assertEqual(len(p),206)

if __name__=='__main__':unittest.main()
