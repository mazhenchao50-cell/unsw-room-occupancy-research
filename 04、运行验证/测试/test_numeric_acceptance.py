import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'04、运行验证/代码'))
import numeric_acceptance as N
from serving_policy import initial_mode


class NumericAcceptanceTests(unittest.TestCase):
    def test_original_or_rules_without_changing_thresholds(self):
        gains = {'timetable_static': .10, 'historical_mean': .10}
        self.assertTrue(all(N.gates(gains, dict(f1=.59, precision=.65), .18, .10).values()))
        self.assertTrue(N.gates(gains, dict(f1=.60, precision=.64), .20, .16)['spatial'])
        self.assertFalse(N.gates(gains, dict(f1=.59, precision=.649), .181, .10)['low'])
        self.assertFalse(N.gates(gains, dict(f1=.59, precision=.649), .181, .10)['spatial'])
        gains['historical_mean'] = .0999
        self.assertFalse(N.gates(gains, dict(f1=.60, precision=.65), .18, .10)['regression'])

    def test_missing_baseline_or_invalid_metrics_are_rejected(self):
        for gains, random in [({'timetable_static': .5}, .2),
                              ({'timetable_static': .5, 'historical_mean': .2}, 0)]:
            with self.assertRaises(ValueError):
                N.gates(gains, dict(f1=.8, precision=.8), .17, random)

    def test_evaluation_rows_cannot_be_removed_duplicated_or_relabelled(self):
        source = pd.DataFrame(dict(session_id=['a','b'], room=['A','B'], week=[12,12], occupancy_rate=[.0,.3]))
        frame = source.assign(prediction=[.1,.2])
        N.align_predictions(frame, source)
        for bad in [frame.iloc[:1], pd.concat([frame, frame.iloc[:1]]),
                    frame.assign(prediction=[-.01,.2]),
                    frame.assign(room=['B','A']), frame.assign(occupancy_rate=[.3,.0])]:
            with self.assertRaises((ValueError, AssertionError)):
                N.align_predictions(bad, source)

    def test_random_comparator_cannot_select_its_own_easier_rows(self):
        data=pd.DataFrame(dict(session_id=range(100),room=['A']*100,week=[1]*100,occupancy_rate=[.1]*100))
        expected=N.random_reference(data)
        frame=expected.assign(prediction=.1)
        N.align_predictions(frame, expected)
        replacement=next(x for x in data.session_id if x not in set(expected.session_id))
        changed=frame.copy()
        changed.loc[changed.index[0],'session_id']=replacement
        for bad in [frame.iloc[:-1],changed]:
            with self.assertRaises(ValueError):
                N.align_predictions(bad, expected)

    def test_default_policy_is_explicit_and_baseline_is_still_selectable(self):
        self.assertEqual(initial_mode(), 'unified')
        self.assertEqual(initial_mode('current'), 'current')
        self.assertEqual(initial_mode('invalid'), 'unified')
        with patch.object(N, 'DEFAULT_MODE', 'current'):
            with self.assertRaisesRegex(ValueError, 'not the default'):
                N.assess(ROOT)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core', 'Baseline-only profile has no standard model')
    def test_actual_serving_model_and_full_evaluation_agree(self):
        result = N.assess(ROOT)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['n_week12'], 206)
        self.assertEqual(result['n_spatial'], 2360)
        self.assertEqual(len(result['spatial']['room_rmse']), 9)
        self.assertEqual(result['default_mode'], 'unified')
        self.assertEqual(result['cross_week']['n'],815)
        prediction=pd.read_csv(ROOT/'02、模型实验/生成产物/unified/time_predictions.csv')
        last=prediction[prediction.week.eq(12)];last_truth=last.occupancy_rate.lt(.1);last_alert=last.low_alert
        last_expected=[int((~last_truth&~last_alert).sum()),int((~last_truth&last_alert).sum()),int((last_truth&~last_alert).sum()),int((last_truth&last_alert).sum())]
        self.assertEqual(result['low']['confusion_tn_fp_fn_tp'],last_expected)
        truth=prediction.occupancy_rate.lt(.1);alert=prediction.low_alert
        expected=[int((~truth&~alert).sum()),int((~truth&alert).sum()),int((truth&~alert).sum()),int((truth&alert).sum())]
        self.assertEqual(result['cross_week']['pooled']['confusion_tn_fp_fn_tp'],expected)
        self.assertTrue(result['cross_week']['checks']['every_week_original_low_gate'])
        self.assertTrue(result['cross_week']['checks']['every_week_recall_at_least_050'])
        self.assertTrue(all(result['context_adoption']['checks'].values()))
