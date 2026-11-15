import sys
import os
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import improvement_v8 as V


class NestedSpatialTests(unittest.TestCase):
    def sample(self):
        d=V.R.load()
        return pd.concat([g.head(20) for _,g in list(d.groupby('room'))[:4]]).copy()

    def test_query_labels_ids_and_history_do_not_enter_features(self):
        d=self.sample();a=V.features(d)
        d['occupancy_rate']=999.;d['attendees']=999.;d['course_id']='new';d['room']='new'
        pd.testing.assert_frame_equal(a,V.features(d))
        self.assertFalse(any('hist' in c or 'course_id'==c or 'room'==c for c in a.columns))

    def test_each_room_has_equal_weight(self):
        d=self.sample();d=d.drop(d.index[:7]);w=V.room_weights(d)
        totals=pd.Series(w).groupby(d.room.to_numpy()).sum()
        np.testing.assert_allclose(totals,totals.iloc[0])

    def test_outer_labels_do_not_change_selection_or_predictions(self):
        d=self.sample();room=sorted(d.room.unique())[0]
        p,selection=V.predict_held_room(d,room)
        d.loc[d.room.eq(room),'occupancy_rate']=999.
        p2,selection2=V.predict_held_room(d,room)
        np.testing.assert_allclose(p,p2,rtol=0,atol=0)
        self.assertEqual(selection,selection2)
        self.assertNotIn(room,selection['reference_rooms'])
        for trial in selection['trials']:self.assertNotIn(room,trial['inner_rooms'])

    def test_overlap_and_bad_capacity_rejected(self):
        d=self.sample()
        with self.assertRaises(ValueError):V.fit_predict(d,d,('Ridge',1.))
        d.loc[d.index[0],'seats']=0
        with self.assertRaises(ValueError):V.features(d)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core','Independent extended spatial experiment')
    def test_complete_outer_coverage_and_recomputed_metrics(self):
        r=json.loads((V.OUT/'report.json').read_text(encoding='utf-8'))
        f=pd.read_csv(V.OUT/'loro_predictions.csv');d=V.R.load();scores=[]
        self.assertEqual(set(f.session_id),set(d.session_id));self.assertTrue(f.session_id.is_unique)
        self.assertEqual(len(r['rooms']),9)
        for room,g in f.groupby('room'):
            met=V.R.metrics(g.occupancy_rate,g.prediction);scores.append(met['rmse'])
            self.assertAlmostEqual(met['rmse'],r['rooms'][room]['metrics']['rmse'])
            self.assertNotIn(room,r['rooms'][room]['reference_rooms'])
            for trial in r['rooms'][room]['trials']:
                self.assertNotIn(room,trial['inner_rooms'])
        self.assertAlmostEqual(np.mean(scores),r['macro_rmse'])
        q=pd.read_csv(V.OUT/'random_predictions.csv')
        rmse=V.R.metrics(q.occupancy_rate,q.prediction)['rmse']
        self.assertAlmostEqual(np.mean(scores)/rmse-1,r['gap_vs_random'])
        self.assertFalse(r['default_model_changed'])
