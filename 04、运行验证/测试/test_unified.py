import sys
import os
import json
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import unified as U


class RoutedSystemTests(unittest.TestCase):
    def test_selected_logistic_serving_matches_offline_pipeline(self):
        d=U.R.load();reference=d[d.week.lt(8)];query=d[d.week.eq(8)].head(12)
        candidate=('logit',1.0,'balanced')
        low=U.V10.fit_bundle(reference,candidate);low['threshold']=.65
        expected=U.V10.fit_predict(reference,query,candidate)
        b=dict(cutoff=reference.date.max(),fitted_ids=set(reference.session_id),
               known_rooms=sorted(reference.room.unique()),warm=None,low=low)
        with patch.object(U.R,'predict',return_value=np.zeros(len(query))):
            result=U.predict_bundle(b,query)
        np.testing.assert_allclose(result.low_probability,expected,rtol=1e-12,atol=1e-12)
        np.testing.assert_array_equal(result.low_alert,expected>=.65)

    def test_routing_uses_only_fitted_room_membership(self):
        q=pd.DataFrame(dict(room=['new','old','new'],occupancy_rate=[0,1,99]))
        self.assertEqual(U.route(['old'],q).tolist(),['unseen','known','unseen'])
        q['occupancy_rate']=-500
        self.assertEqual(U.route(['old'],q).tolist(),['unseen','known','unseen'])
        q.loc[0,'room']=''
        with self.assertRaises(ValueError):U.route(['old'],q)

    def test_cutoff_duplicate_and_fitted_ids_rejected_before_scoring(self):
        b=dict(cutoff=pd.Timestamp('2020-01-01'),fitted_ids={'fitted'})
        for date,ids in [('2020-01-01',['a']),('bad',['a']),('2020-01-02',['a','a']),('2020-01-02',['fitted'])]:
            q=pd.DataFrame(dict(date=[date]*len(ids),session_id=ids))
            with self.assertRaises(ValueError):U.predict_bundle(b,q)

    def test_stale_bundle_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);out=r/'02、模型实验/生成产物/unified';out.mkdir(parents=True)
            (r/'input.txt').write_text('changed')
            (out/'report.json').write_text(json.dumps({'sha256':{'input.txt':hashlib.sha256(b'original').hexdigest()}}))
            with self.assertRaises(ValueError):U.load_verified(r)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core','Unified research artifact is extended')
    def test_serialized_predictions_and_mixed_routing_ignore_query_labels(self):
        b,r=U.load_verified();d=U.R.load();q=d[d.week.eq(12)].head(2).copy()
        q.loc[q.index[-1],'room']='unseen-room';q.loc[q.index[-1],'session_id']='unseen-session'
        p=U.predict_bundle(b,q)
        self.assertEqual(p.prediction_route.tolist(),['known','unseen'])
        self.assertTrue(pd.isna(p.low_probability.iloc[1]))
        self.assertEqual(p.low_alert.iloc[1],p.prediction.iloc[1]<.1)
        np.testing.assert_allclose(p.prediction.iloc[1:],U.predict_cold(b['cold'],q.iloc[1:]))
        q['occupancy_rate']=999;q['attendees']=999
        pd.testing.assert_frame_equal(p,U.predict_bundle(b,q))
        full=U.predict_bundle(b,d[d.week.eq(12)])
        saved=pd.read_csv(U.OUT/'time_predictions.csv').query('week==12')
        m=full.merge(saved,on='session_id',suffixes=('_now','_saved'),validate='one_to_one')
        np.testing.assert_allclose(m.prediction_now,m.prediction_saved,atol=1e-12)
        self.assertTrue((m.low_alert_now==m.low_alert_saved).all())

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core','Unified research artifact is extended')
    def test_numeric_gates_recompute_with_same_router_random_comparator(self):
        r=json.loads((U.OUT/'report.json').read_text(encoding='utf-8'))
        s=pd.read_csv(U.OUT/'spatial_predictions.csv');rand=pd.read_csv(U.OUT/'random_predictions.csv')
        self.assertTrue(s.session_id.is_unique);self.assertEqual(set(s.session_id),set(U.R.load().session_id))
        self.assertEqual(set(s.prediction_route),{'unseen'});self.assertEqual(set(rand.prediction_route),{'known'})
        macro=float(np.mean([U.R.metrics(g.occupancy_rate,g.prediction)['rmse'] for _,g in s.groupby('room')]))
        random=U.R.metrics(rand.occupancy_rate,rand.prediction)['rmse']
        self.assertAlmostEqual(r['spatial_summary']['macro_rmse'],macro)
        self.assertAlmostEqual(r['spatial_summary']['gap_vs_random'],macro/random-1)
        self.assertEqual(r['original_numeric_gates']['spatial'],macro<=.18 or macro/random-1<=.3)
        f=pd.read_csv(U.OUT/'time_predictions.csv').query('week==12')
        low=U.R.binary_metrics(f.occupancy_rate<.1,f.low_alert)
        self.assertEqual(r['rolling']['12']['low']['confusion_tn_fp_fn_tp'],low['confusion_tn_fp_fn_tp'])

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core','Unified research artifact is extended')
    def test_forward_cold_excludes_target_room_and_future_labels(self):
        r=json.loads((U.OUT/'report.json').read_text(encoding='utf-8'))
        f=pd.read_csv(U.OUT/'forward_cold_predictions.csv');d=U.R.load()
        self.assertEqual(set(f.session_id),set(d[d.week.eq(12)].session_id));self.assertTrue(f.session_id.is_unique)
        for room,g in f.groupby('room'):
            self.assertNotIn(room,r['forward_cold'][room]['reference_rooms'])
            self.assertLess(pd.Timestamp(r['forward_cold'][room]['cutoff']),pd.to_datetime(g.date).min())
