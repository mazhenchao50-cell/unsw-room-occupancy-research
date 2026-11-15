import sys
import os
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import improvement_v7 as V


class NormalizedModelTests(unittest.TestCase):
    def test_scale_missing_zero_and_invalid_capacity(self):
        d=pd.DataFrame({'seats':[100]*4,'enrollments':[50,0,np.nan,200]})
        np.testing.assert_allclose(V.scale(d),[.5,1,1,2])
        d.loc[0,'seats']=0
        with self.assertRaises(ValueError): V.scale(d)

    def test_query_labels_and_future_labels_do_not_enter_features(self):
        d=V.R.load().head(20).copy()
        q=d.tail(2).copy(); a=V.features(d,q)
        q['occupancy_rate']=999.;q['attendees']=999.
        pd.testing.assert_frame_equal(a,V.features(d,q))
        ref=d.copy();ref.loc[ref.date>=q.date.min(),'occupancy_rate']=999.
        pd.testing.assert_frame_equal(a,V.features(ref,q))

    def test_abstention_and_invalid_calibration(self):
        t,scan=V.select_threshold([False,False],[0.,1.])
        self.assertGreater(t,1);self.assertEqual(scan,[])
        for y,p in [([],[]),([True],[np.nan]),([True],[.1,.2])]:
            with self.assertRaises(ValueError):V.select_threshold(y,p)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core','Independent extended experiment')
    def test_artifacts_recompute_and_spatial_exclusion(self):
        r=json.loads((V.OUT/'report.json').read_text(encoding='utf-8'))
        f=pd.read_csv(V.OUT/'rolling_predictions.csv')
        self.assertTrue(f.session_id.is_unique)
        self.assertEqual(sorted(f.week.unique()),[8,10,11,12])
        self.assertTrue((f.low_alert==(f.low_probability>=f.threshold)).all())
        met=V.R.binary_metrics(f.occupancy_rate<.1,f.low_alert)
        self.assertEqual(met['confusion_tn_fp_fn_tp'],r['pooled_low']['confusion_tn_fp_fn_tp'])
        f=pd.read_csv(V.OUT/'loro_predictions.csv');d=V.R.load()
        self.assertEqual(set(f.session_id),set(d.session_id));self.assertTrue(f.session_id.is_unique)
        rmses=[]
        for room,g in f.groupby('room'):
            self.assertNotIn(room,r['loro'][room]['reference_rooms'])
            rmse=V.R.metrics(g.occupancy_rate,g.prediction)['rmse'];rmses.append(rmse)
            self.assertAlmostEqual(rmse,r['loro'][room]['rmse'])
        self.assertAlmostEqual(np.mean(rmses),r['spatial_summary']['macro_rmse'])
