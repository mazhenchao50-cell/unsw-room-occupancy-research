import unittest
import numpy as np
import pandas as pd
import stable_alerts as S


class StableAlertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=S.R.load()

    def test_recent_features_never_see_same_day_or_future_labels(self):
        query=self.data[self.data.week.eq(8)].head(3).copy()
        reference=self.data.copy()
        before=S.features(reference,query)
        reference.loc[reference.date.ge(query.date.min()),'occupancy_rate']=999.
        after=S.features(reference,query)
        pd.testing.assert_frame_equal(before,after)

    def test_query_labels_do_not_affect_features(self):
        reference=self.data[self.data.week.lt(8)]
        query=self.data[self.data.week.eq(8)].head(4).copy()
        before=S.features(reference,query)
        query['occupancy_rate']=999.;query['attendees']=999.
        pd.testing.assert_frame_equal(before,S.features(reference,query))

    def test_same_period_overlap_and_duplicate_queries_are_rejected(self):
        train=self.data[self.data.week.lt(4)]
        query=self.data[self.data.week.eq(4)].head(3).copy()
        S.validate_forward(train,query)
        with self.assertRaises(ValueError):S.validate_forward(pd.concat([train,query]),query)
        with self.assertRaises(ValueError):S.validate_forward(train,pd.concat([query,query.iloc[:1]]))

    def test_empty_history_fallback_is_finite(self):
        query=self.data[self.data.week.eq(1)].head(2).copy()
        frame=S.features(self.data.iloc[:0],query)
        self.assertTrue(np.isfinite(frame.fillna(0).to_numpy()).all())
        self.assertTrue(frame.course_seen.eq(0).all())
        self.assertTrue(frame.course_history_log_n.eq(0).all())

    def test_adoption_rejects_trading_all_misses_for_false_alerts(self):
        weekly={str(w):dict(precision=.4,recall=1.,f1=.57,confusion_tn_fp_fn_tp=[0,100,0,50]) for w in [8,10,11,12]}
        checks=S.adoption(dict(precision=.4,recall=1.),weekly)
        self.assertTrue(checks['week12_misses_at_most_25'])
        self.assertFalse(checks['pooled_precision_at_least_065'])
        self.assertFalse(all(checks.values()))


if __name__=='__main__':unittest.main()
