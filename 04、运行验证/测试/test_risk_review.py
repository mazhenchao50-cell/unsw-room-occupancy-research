import os
import sys
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import risk_review as V


class RiskReviewTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame(dict(session_id=['a','b','c','d'],date=['2020-01-01']*4,room=['r']*4,
            course_id=['one','one','two','two'],week=[8,10,11,12],occupancy_rate=[0.,.2,0.,.2],
            prediction=[0.,0.,.2,.2],low_alert=[True,True,False,False]))

    def test_alignment_is_order_invariant_and_rejects_missing_duplicate_or_changed_truth(self):
        f=self.fixture();pd.testing.assert_frame_equal(V.align(f.iloc[::-1],f),f)
        bad=[f.iloc[:-1],pd.concat([f.iloc[:3],f.iloc[:1]])]
        g=f.copy();g.loc[0,'occupancy_rate']=.5;bad.append(g)
        g=f.copy();g.loc[0,'room']='different';bad.append(g)
        for g in bad:
            with self.assertRaises(ValueError):V.align(g,f)

    def test_nonfinite_predictions_and_text_alerts_are_rejected(self):
        f=self.fixture()
        for value in [np.nan,np.inf,-1.]:
            g=f.copy();g.loc[0,'prediction']=value
            with self.assertRaises(ValueError):V.align(g,f)
        g=f.copy();g.low_alert=g.low_alert.astype(str)
        with self.assertRaises(ValueError):V.align(g,f)

    def test_confusion_cost_and_zero_difference_for_identical_predictions(self):
        f=self.fixture();s=V.summary(f)
        self.assertEqual(s['pooled']['low']['confusion_tn_fp_fn_tp'],[1,1,1,1])
        self.assertEqual(V.cost(s['pooled']['low'],5),6)
        ci=V.paired_course_interval(f,f,200)['candidate_minus_LightGBM_rmse_95']
        self.assertEqual(ci,[0.,0.])

    def test_paired_bootstrap_direction_and_alignment(self):
        f=self.fixture();g=f.copy();g.prediction=g.occupancy_rate
        self.assertLess(V.paired_course_interval(f,g,200)['candidate_minus_LightGBM_rmse_95'][1],0)
        with self.assertRaises(ValueError):V.paired_course_interval(f,g.iloc[::-1],20)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE') in ('core','standard'),'Review requires unified predictions')
    def test_artifact_coverage_and_metrics(self):
        r=json.loads((V.OUT/'report.json').read_text(encoding='utf-8'))
        f=pd.read_csv(V.OUT/'aligned_predictions.csv')
        truth=V.R.load();truth=truth[truth.week.isin(V.WEEKS)].reset_index(drop=True)
        self.assertEqual(set(f.model),set(V.MODELS))
        for name,g in f.groupby('model'):
            g=V.align(g,truth);s=V.summary(g)
            self.assertEqual(s['pooled']['low'],r['models'][name]['pooled']['low'])
            self.assertAlmostEqual(s['pooled']['rmse'],r['models'][name]['pooled']['rmse'])
        self.assertFalse(r['adoption']['default_changed'])
        self.assertFalse(r['adoption']['unified_changed'])
