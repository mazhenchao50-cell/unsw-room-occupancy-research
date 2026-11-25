"""Check temporal leakage, calendar semantics and actual serving boundaries."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import stable_low as S
import calendar_context as C


class StableLowTests(unittest.TestCase):
    def test_features_ignore_query_labels_and_same_day_or_future_reference_labels(self):
        d=S.R.load();q=d[d.week.eq(8)].head(3).copy();ref=d.copy()
        expected=S.features(ref,q)
        q['occupancy_rate']=99;q['attendees']=999
        future=ref.date.ge(q.date.min());ref.loc[future,'occupancy_rate']=500
        ref.loc[future,'attendees']=50000
        pd.testing.assert_frame_equal(expected,S.features(ref,q))

    def test_calendar_uses_dates_only_and_excludes_bank_only_holiday(self):
        q=pd.DataFrame(dict(date=['2017-08-07','2017-10-02','2017-10-03'],occupancy_rate=[0,.9,0]))
        self.assertEqual(C.review_flag(q).tolist(),[False,True,False])
        q['occupancy_rate']=-100
        self.assertEqual(C.review_flag(q).tolist(),[False,True,False])
        for date in ['bad','2018-10-01','2017-07-23','2017-10-21']:
            with self.assertRaises(ValueError):C.review_flag(pd.DataFrame(dict(date=[date])))

    def test_calendar_adds_review_without_fabricating_model_probability(self):
        d=S.R.load();ref=d[d.week.lt(10)];q=d[d.date.eq(pd.Timestamp('2017-10-02'))].head(2)
        # Fixed fake classifiers isolate the calendar rule from fitted labels.
        from types import SimpleNamespace
        clf=SimpleNamespace(predict_proba=lambda x:np.tile([.8,.2],(len(x),1)))
        bundle=dict(strategy=S.STRATEGY,threshold=.5,cutoff=ref.date.max(),fitted_ids=set(ref.session_id),
                    reference=ref,features=['x'],median=pd.Series({'x':0}),logistic=clf,trees=clf,
                    scaler=SimpleNamespace(transform=lambda x:x))
        with patch.object(S,'features',return_value=pd.DataFrame({'x':[0]*len(q)},index=q.index)):
            result=S.predict_bundle(bundle,q)
        np.testing.assert_allclose(result['probability'],.2)
        self.assertFalse(result['model_alert'].any());self.assertTrue(result['calendar_review'].all())
        self.assertTrue(result['alert'].all());self.assertEqual(len(q),2)

    def test_cutoff_duplicates_and_altered_policy_fail_before_feature_computation(self):
        bundle=dict(strategy=S.STRATEGY,threshold=.5,cutoff=pd.Timestamp('2017-10-06'),fitted_ids={'old'})
        for dates,ids in [(['2017-10-06'],['a']),(['bad'],['a']),(['2017-10-09']*2,['a','a']),(['2017-10-09'],['old'])]:
            with self.assertRaises(ValueError):S.predict_bundle(bundle,pd.DataFrame(dict(date=dates,session_id=ids)))
        bundle['threshold']=.3
        with self.assertRaises(ValueError):S.predict_bundle(bundle,pd.DataFrame())

    def test_registered_policy_and_calendar_sources_are_explicit(self):
        self.assertEqual(S.THRESHOLD,.5);self.assertEqual(C.STATEWIDE_PUBLIC_HOLIDAYS,('2017-10-02',))
        self.assertEqual(len(C.SOURCE_SHA256),2)
        self.assertTrue(all(len(value)==64 for value in C.SOURCE_SHA256.values()))


if __name__=='__main__':unittest.main()
