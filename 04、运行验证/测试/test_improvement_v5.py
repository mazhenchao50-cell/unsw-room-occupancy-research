from pathlib import Path
import sys
import os
import unittest
import pandas as pd
import numpy as np
import joblib
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import improvement_v5 as V

class NoShowTests(unittest.TestCase):
    def test_history_excludes_same_date_and_future(self):
        d=pd.DataFrame({'date':pd.to_datetime(['2017-01-01','2017-01-02','2017-01-02','2017-01-03']),
                        'attendees':[0,5,0,5],'course_id':['a']*4,'room':['r']*4})
        before=V.event_history(d,d)
        d.loc[1:,'attendees']=100
        after=V.event_history(d,d)
        pd.testing.assert_frame_equal(before.iloc[:3],after.iloc[:3])
        self.assertEqual(before.iloc[0].course_no_show_rate,.05)
        self.assertEqual(before.iloc[1].course_no_show_rate,1.)

    def test_no_positive_calibration_does_not_claim_precision(self):
        threshold,scan=V.choose_threshold([False,False],np.array([.8,.9]))
        self.assertEqual(threshold,1.01)
        self.assertEqual(scan,[])
        self.assertIsNone(V.score([False,True],[False,False])['precision_wilson_95'])

    def test_precision_weighted_score(self):
        metric=V.score([True,False,False,False],[True,True,True,True])
        self.assertLess(metric['f0_5'],metric['f1'])

    @unittest.skipIf(os.environ.get('PROJECT_TEST_PROFILE') in ('core','standard'),'Saved v5 artifact check belongs to extended profile')
    def test_saved_model_reproduces_and_ignores_test_targets(self):
        bundle=joblib.load(V.R.ROOT/'02、模型实验/生成产物/improvement_v5/no_show.joblib')
        data=V.R.load();test=data[data.week.eq(12)].copy()
        expected=pd.read_csv(V.R.ROOT/'02、模型实验/生成产物/improvement_v5/predictions.csv')
        expected=expected[expected.week.eq(12)]
        self.assertLess(bundle['reference'].date.max(),test.date.min())
        p=V.predict(bundle,test)
        np.testing.assert_allclose(p,expected.new_probability,rtol=1e-12,atol=1e-12)
        test['attendees']=99999;test['occupancy_rate']=999
        np.testing.assert_array_equal(p,V.predict(bundle,test))
