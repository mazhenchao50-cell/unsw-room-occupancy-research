import sys
import os
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import improvement_v6 as V

class LowUtilCalibrationTests(unittest.TestCase):
    def test_no_positive_calibration_abstains(self):
        threshold,scan=V.choose_threshold([False,False],[0.,.05])
        self.assertEqual(threshold,0);self.assertEqual(scan,[])
        self.assertFalse((np.array([0.,.01])<threshold).any())

    def test_invalid_calibration_and_strict_boundary(self):
        for y,p in [([],[]),([True],[np.nan]),([True],[.1,.2])]:
            with self.assertRaises(ValueError):V.choose_threshold(y,p)
        t,scan=V.choose_threshold([True,False],[.10,.30])
        self.assertEqual(t,.12)
        self.assertEqual(next(r for r in scan if r['threshold']==.1)['predicted_positive'],0)

    def test_chronology_and_duplicate_identifiers_rejected(self):
        d=pd.DataFrame({'week':[1,2,3,4],'date':pd.date_range('2020-01-01',periods=4),'session_id':list('abcd')})
        self.assertEqual([len(x) for x in V.split_fold(d,4)],[1,1,1,1])
        d.loc[3,'date']=d.loc[1,'date']
        with self.assertRaises(ValueError):V.split_fold(d,4)
        d['date']=pd.date_range('2020-01-01',periods=4);d.loc[3,'session_id']='a'
        with self.assertRaises(ValueError):V.split_fold(d,4)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE') in ('core','standard'),'Independent extended experiment')
    def test_saved_results_cover_all_folds_and_recompute_scores(self):
        out=V.R.ROOT/'02、模型实验/生成产物/improvement_v6'
        d=pd.read_csv(out/'predictions.csv');r=json.loads((out/'report.json').read_text(encoding='utf-8'))
        self.assertTrue(d.session_id.is_unique);self.assertEqual(sorted(d.week.unique()),[8,10,11,12])
        self.assertTrue((d.calibrated_alert==(d.prediction<d.threshold)).all())
        for name,col in [('fixed','fixed_alert'),('calibrated','calibrated_alert')]:
            self.assertAlmostEqual(V.R.binary_metrics(d.occupancy_rate<.1,d[col])['f1'],r['pooled'][name]['f1'])
        self.assertFalse(r['default_model_changed'])
