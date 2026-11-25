import os
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import cold_week as C
import revised as R


def small():
    d = R.load()
    rooms = ['CLB 7', 'MathewsThA', 'PhysicsTh', 'BUS 115']
    return d[d.room.isin(rooms)].groupby('room').head(60).copy()


class ColdWeekTests(unittest.TestCase):
    def test_held_room_labels_never_change_selection_or_prediction(self):
        d = small(); pool, query = d[d.room.ne('BUS 115')], d[d.room.eq('BUS 115')]
        a = C.fit(pool); p = C.predict(a, query)
        q2 = query.assign(occupancy_rate=99.0, attendees=999)
        np.testing.assert_array_equal(p, C.predict(a, q2))
        b = C.fit(pool.copy()); self.assertEqual(a['selected'], b['selected'])
        np.testing.assert_allclose(p, C.predict(b, query), rtol=0, atol=0)

    def test_features_exclude_identity_and_labels(self):
        cols = set(C.features(small(), 'week_features').columns)
        self.assertTrue({'week', 'pressure_x_week', 'pressure_sq', 'enrollment_pressure'} <= cols)
        self.assertFalse(cols & {'room', 'course_id', 'session_id', 'occupancy_rate', 'attendees'})

    def test_missing_week_rejected(self):
        with self.assertRaises(ValueError):
            C.features(small().drop(columns='week'), 'week_features')

    def test_grid_keeps_original_v8_candidates(self):
        self.assertEqual([c[1:] for c in C.GRID if c[0] == 'v8_control'],
                         [('Ridge', .1), ('Ridge', 1.), ('Ridge', 10.), ('LightGBM', 80), ('LightGBM', 200), ('LightGBM', 400)])

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE') == 'core', 'Unified research artifact is extended')
    def test_formal_spatial_predictions_equal_frozen_experiment_11(self):
        formal = pd.read_csv(ROOT / '02、模型实验/生成产物/unified/spatial_predictions.csv')
        study = pd.read_csv(ROOT / '02、模型实验/补充研究/11、空间冷启动余量/生成产物/逐课次留一教室预测.csv')
        m = formal.merge(study, on='session_id', suffixes=('_f', '_s'), validate='one_to_one')
        self.assertEqual(len(m), len(formal))
        np.testing.assert_allclose(m.prediction_f, m.prediction_s, rtol=0, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
