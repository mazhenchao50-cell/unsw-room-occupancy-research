import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import forward_cold_benchmark as B


class ForwardColdTests(unittest.TestCase):
    @staticmethod
    def sample():
        d=B.R.load()
        rooms=sorted(d.room.unique())[:4]
        return d[d.room.isin(rooms)].groupby(['room','week'],group_keys=False).head(2).copy()

    def test_held_room_and_future_answers_do_not_change_predictions_or_selection(self):
        data=self.sample();room=sorted(data.room.unique())[0]
        first,info=B.evaluate_outer(data,room,12)
        data.loc[data.room.eq(room)|data.week.ge(12),'occupancy_rate']=999.
        data.loc[data.room.eq(room)|data.week.ge(12),'attendees']=999.
        second,changed=B.evaluate_outer(data,room,12)
        self.assertEqual(info,changed)
        np.testing.assert_array_equal(first.prediction,second.prediction)
        for column in ['fixed_alert','calibrated_alert','budget_alert']:
            np.testing.assert_array_equal(first[column],second[column])
        self.assertNotIn(room,info['source_rooms'])
        self.assertLess(info['training_last_date'],info['calibration_last_date'])
        self.assertLess(info['calibration_last_date'],info['query_first_date'])

    def test_fit_rejects_seen_room_future_and_identity_overlap(self):
        data=self.sample();room=sorted(data.room.unique())[0]
        train,valid,final,cal,query,_,_=B.split_outer(data,room,12)
        with self.assertRaises(ValueError):B.fit_predict(final,final.iloc[:1],('Ridge',1.))
        same_room=cal[cal.room.eq(final.room.iloc[0])]
        with self.assertRaises(ValueError):B.fit_predict(final,same_room,('Ridge',1.))
        late=final.copy();late['date']=query.date.max()
        with self.assertRaises(ValueError):B.fit_predict(late,query,('Ridge',1.))
        mixed=pd.concat([cal.groupby('room').head(1)])
        with self.assertRaises(ValueError):B.fit_predict(train,mixed,('CapacityRidge',1.))

    def test_calibration_infeasibility_and_predeclared_tie_rule(self):
        no=B.calibrated_policy([False]*8+[True]*2,np.ones(10))
        self.assertFalse(no['feasible']);self.assertIsNone(no['threshold'])
        yes=B.calibrated_policy([True]*5+[False]*5,[.01]*5+[.7]*5)
        self.assertTrue(yes['feasible']);self.assertEqual(yes['threshold'],.025)
        with self.assertRaises(ValueError):B.calibrated_policy([True],[np.nan])

    def test_fixed_budget_is_explicit_and_ties_are_stable(self):
        flags=B.budget_alerts([.1,.1,.5,.8,.9],['b','a','c','d','e'])
        self.assertEqual(flags.tolist(),[False,True,False,False,False])
        self.assertEqual(int(B.budget_alerts(np.arange(6),list('abcdef')).sum()),2)
        with self.assertRaises(ValueError):B.budget_alerts([np.inf],['a'])

    def test_paired_uncertainty_refuses_missing_and_conflicting_sessions(self):
        d=self.sample()[['session_id','room','course_id','occupancy_rate']].copy()
        d['prediction']=d.occupancy_rate+.1
        result=B.paired_interval(d,d,100)
        np.testing.assert_allclose(result['candidate_minus_baseline_macro_rmse_95'],[0,0])
        with self.assertRaises(ValueError):B.paired_interval(d,d.iloc[:-1],10)
        changed=d.copy();changed.loc[changed.index[0],'occupancy_rate']+=.1
        with self.assertRaises(ValueError):B.paired_interval(d,changed,10)

    def test_capacity_and_session_identity_checks_preserve_overcapacity(self):
        d=self.sample()
        changed=d.copy();changed.loc[changed.index[0],'occupancy_rate']=1.5
        self.assertEqual(B.checked_data(changed).occupancy_rate.iloc[0],1.5)
        with self.assertRaises(ValueError):B.checked_data(pd.concat([d,d.iloc[:1]]))
        changed=d.copy();changed.loc[changed.index[0],'seats']=0
        with self.assertRaises(ValueError):B.checked_data(changed)
        changed=d.copy();changed.loc[changed.index[0],'seats']+=1
        with self.assertRaises(ValueError):B.checked_data(changed)

    @unittest.skipIf(os.getenv('PROJECT_TEST_PROFILE')=='core','Separate extended forward-cold experiment')
    def test_complete_shared_coverage_metrics_and_selection_are_recomputed(self):
        report=json.loads((B.OUT/'report.json').read_text(encoding='utf-8'))
        predictions=pd.read_csv(B.OUT/'predictions.csv')
        expected=B.R.load();expected=expected[expected.week.isin(B.TEST_WEEKS)]
        self.assertEqual(report['outer_folds'],36)
        self.assertEqual(report['common_sessions'],len(expected))
        self.assertEqual(set(predictions.model),set(B.GRID)|{'SelectedBaseline','StaticRidge1'})
        for name,g in predictions.groupby('model'):
            self.assertTrue(g.session_id.is_unique)
            self.assertEqual(set(g.session_id),set(expected.session_id))
            actual=B.score_frame(g)
            self.assertAlmostEqual(actual['macro_room_rmse'],report['models'][name]['macro_room_rmse'])
            self.assertEqual(actual['screening']['calibrated_alert']['confusion_tn_fp_fn_tp'],
                             report['models'][name]['screening']['calibrated_alert']['confusion_tn_fp_fn_tp'])
            for _,fold in g.groupby(['room','week']):
                self.assertEqual(int(fold.budget_alert.sum()),int(np.ceil(.2*len(fold))))
                self.assertLess(fold.fitted_through.iloc[0],fold.calibrated_through.iloc[0])
                self.assertLess(fold.calibrated_through.iloc[0],fold.date.min())
        for fold in report['folds']:
            self.assertNotIn(fold['held_room'],fold['source_rooms'])
            for trial in fold['trials']:self.assertNotIn(fold['held_room'],trial['inner_rooms'])
            eligible=[x for x in fold['trials'] if x['candidate'][0] in B.BASELINES]
            self.assertEqual(fold['selected']['SelectedBaseline'],min(eligible,key=lambda x:x['inner_macro_rmse'])['candidate'])
        self.assertFalse(report['default_model_changed'])
        self.assertFalse(report['original_acceptance_replaced'])


if __name__=='__main__':unittest.main()
