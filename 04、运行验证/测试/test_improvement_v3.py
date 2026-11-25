import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '02、模型实验/代码/models'))
import improvement_v3 as V


class CapacityPriorTests(unittest.TestCase):
    def setUp(self):
        self.ref = pd.DataFrame({'date': pd.to_datetime(['2017-01-01'] * 2 + ['2017-01-02', '2017-01-03']),
                                 'course_id': ['a', 'b', 'c', 'd'], 'seats': [50, 200, 50, 50],
                                 'occupancy_rate': [.2, .8, 10., 20.]})
        self.query = pd.DataFrame({'date': pd.to_datetime(['2017-01-02'] * 2),
                                   'course_id': ['new', 'new'], 'seats': [50, 200]}, index=[7, 9])

    def test_query_capacity_and_past_only(self):
        result = V.capacity_history(self.ref, self.query)
        np.testing.assert_allclose(result.course_hist_mean, [.32, .68])
        self.ref.loc[2:, 'occupancy_rate'] = 9999
        pd.testing.assert_frame_equal(result, V.capacity_history(self.ref, self.query))
        self.assertEqual(list(result.index), [7, 9])

    def test_known_course_and_empty_history(self):
        self.query['course_id'] = 'a'
        np.testing.assert_allclose(V.capacity_history(self.ref, self.query).course_hist_mean, [.2, .2])
        self.query['date'] = pd.Timestamp('2016-01-01')
        np.testing.assert_allclose(V.capacity_history(self.ref, self.query).course_hist_mean, [.3, .3])

    def test_restore_on_failure(self):
        original = V.R.history
        with self.assertRaises(RuntimeError):
            with V.using_history(V.capacity_history):
                raise RuntimeError('test')
        self.assertIs(V.R.history, original)


if __name__ == '__main__':
    unittest.main()
