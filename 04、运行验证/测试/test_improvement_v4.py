import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '02、模型实验/代码/models'))
import improvement_v4 as V


class AdaptationTests(unittest.TestCase):
    def test_all_folds_disjoint_and_forward_time(self):
        d = V.R.load()
        for room in sorted(d.room.unique()):
            train, valid, final, adapt, test = V.split_fold(d, room)
            self.assertNotIn(room, set(final.room))
            self.assertEqual(set(adapt.week), {1, 2})
            self.assertEqual(set(test.week), {11, 12})
            self.assertLess(final.date.max(), test.date.min())
            self.assertLess(adapt.date.max(), test.date.min())
            self.assertTrue(set(adapt.session_id).isdisjoint(final.session_id))

    def test_test_labels_do_not_change_model_or_predictions(self):
        parts = V.split_fold(V.R.load(), 'BUS 105')
        predictions, evidence, _ = V.fold_predictions(*parts)
        mutated = parts[-1].copy()
        mutated['occupancy_rate'] = 999.
        mutated['attendees'] = 99999.
        changed, after, _ = V.fold_predictions(*parts[:-1], mutated)
        self.assertEqual(evidence, after)
        for name in predictions:
            np.testing.assert_allclose(predictions[name], changed[name], rtol=0, atol=0)

    def test_intermediate_target_weeks_are_not_used(self):
        d = V.R.load()
        before = V.split_fold(d, 'BUS 105')
        d.loc[d.room.eq('BUS 105') & d.week.between(3, 10), 'occupancy_rate'] = 999.
        after = V.split_fold(d, 'BUS 105')
        for a,b in zip(before, after):
            pd.testing.assert_frame_equal(a,b)


if __name__ == '__main__':
    unittest.main()
