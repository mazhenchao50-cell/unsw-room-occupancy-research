"""Regression tests for shared causes identified by the 2026-11-17 audit."""
from pathlib import Path
import sys,json,tempfile,unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
for folder in ('01、数据处理/代码','02、模型实验/代码','03、系统应用/代码','04、运行验证/代码'):
    sys.path.insert(0,str(ROOT/folder))
import heal_base as H
from replay import candidates
from models import unified as U
import numeric_acceptance as N
from run_tests import validate_inventory
from review_workflow import review_queue,export_review,explain_classifier,explain_context


class HundredAuditTests(unittest.TestCase):
    def fixture(self):
        s=pd.DataFrame(dict(session_id=['s'],date=['2017-09-11'],room=['A'],seats=[35],
            course_start=['09:00:00'],course_end=['10:00:00']))
        a=pd.DataFrame(dict(date=['2017-09-11'],room_code=['A'],start_time=['09:00:00'],end_time=['10:00:00']))
        p=pd.DataFrame(dict(session_id=['s'],prediction=[.15],prediction_route=['known'],low_probability=[.7],
            context_probability=[.6],model_alert=[True],context_alert=[True],calendar_review=[False],low_alert=[True],
            regression_prediction=[.15],state_prediction=[.04],held_prediction=[.3]))
        return s,a,p

    def test_missing_numeric_and_overflowing_dates_rejected(self):
        s,a,p=self.fixture()
        for day in (None,pd.NaT,'',0,20170911,True,'2017-09-31','2017-09-11T09:00:00'):
            with self.subTest(day=day),self.assertRaises(ValueError):candidates(s,a,p,day,'09:00:00')
        for start in ('09:99:00','09:00:99','9:30','1 day','09:00:00.5'):
            with self.subTest(start=start),self.assertRaises(ValueError):candidates(s,a,p,'2017-09-11',start)

    def test_one_observation_does_not_establish_daily_coverage(self):
        s,a,p=self.fixture()
        for start in ('02:00:00','11:00:00'):
            rooms,top,_=candidates(s,a,p,'2017-09-11',start)
            self.assertTrue(top.empty);self.assertEqual(rooms.status.iloc[0],'schedule_unknown')
        _,top,_=candidates(s,a,p,'2017-09-11','11:00:00',coverage={('2017-09-11','A'):{'complete':True,'source':'explicit synthetic coverage'}})
        self.assertEqual(len(top),1);self.assertFalse(top.verified_available.any())

    def test_counts_reject_negative_fractional_and_bad_separators(self):
        ledger=H.QualityLedger();values=pd.Series(['-1','1.5','1,2','1,234','0','NA','inf'])
        actual=H.count_field(values,ledger,'test')
        self.assertEqual(actual.notna().tolist(),[False,False,False,True,True,False,False])
        self.assertEqual(actual.iloc[3],1234)
        self.assertEqual(ledger.rows['invalid_count_test']['detected'],4)
        self.assertEqual(ledger.rows['invalid_count_test']['fixed'],0)
        self.assertTrue(H.count_field(pd.Series(['0']),ledger,'capacity',positive=True).isna().all())
        for value in ('0','00:00:00'):self.assertEqual(H._duration_to_min(value),(None,False))

    def test_empty_schema_and_cold_date_contract(self):
        empty=U.predict_bundle({},pd.DataFrame(columns=['date']))
        self.assertEqual(list(empty),U.PREDICTION_COLUMNS)
        self.assertEqual(empty.low_alert.dtype,bool)
        s,_,_=self.fixture();s['date']='2017-10-23'
        with self.assertRaises(ValueError):U.predict_bundle(dict(cutoff=pd.Timestamp('2017-10-15'),fitted_ids=set()),s)

    def test_manifest_cannot_omit_required_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'02、模型实验/生成产物/unified';out.mkdir(parents=True)
            for manifest in ({},{'../outside':'a'*64}):
                (out/'report.json').write_text(json.dumps({'sha256':manifest}),encoding='utf-8')
                with self.assertRaises(ValueError),patch.object(U.joblib,'load') as loader:
                    U.load_verified(root)
                loader.assert_not_called()

    def test_probability_tamper_is_rejected_even_when_alert_unchanged(self):
        _,_,served=self.fixture();saved=served.copy();saved['low_probability']=.999
        with self.assertRaises(AssertionError):N.compare_served(saved,served)
        saved=served.copy();saved['context_probability']=.999
        with self.assertRaises(AssertionError):N.compare_served(saved,served)
        for column in ('regression_prediction','state_prediction','held_prediction'):  # v6 two-part outputs
            saved=served.copy();saved[column]=saved[column]+.01
            with self.assertRaises(AssertionError):N.compare_served(saved,served)
        for column in ('model_alert','context_alert','calendar_review','low_alert'):
            saved=served.copy();saved[column]=~saved[column]
            with self.assertRaises(AssertionError):N.compare_served(saved,served)

    def test_full_test_inventory_rejects_partial_execution(self):
        record=dict(expected_ids=['a','b'],executed_ids=['a'],failed_ids=[],error_ids=[],skipped_ids=[])
        with self.assertRaises(ValueError):validate_inventory(record,'extended')
        record['executed_ids']=['a','a']
        with self.assertRaises(ValueError):validate_inventory(record,'extended')
        record['executed_ids']=['a','b'];record['skipped_ids']=['b']
        with self.assertRaises(ValueError):validate_inventory(record,'extended')

    def test_review_uses_model_without_claiming_release(self):
        s,_,p=self.fixture();q=review_queue(s,p,'2017-09-11')
        self.assertTrue(q.low_alert.iloc[0]);self.assertGreater(q.prediction.iloc[0],.1)
        result=json.loads(export_review(q.iloc[0],'hash','pending',''))
        self.assertFalse(result['automatic_release'])
        with self.assertRaises(ValueError):review_queue(s,p.iloc[:0],'2017-09-11')

    def test_actual_classifier_explanations_match_each_fold_and_reject_wrong_score(self):
        import joblib
        data=U.R.load()
        for week in (8,10,11,12):
            bundle=joblib.load(U.OUT/f'fold_models/rolling_{week}.joblib')
            query=data[data.week.eq(week)].iloc[:1]
            score=U.predict_bundle(bundle,query).low_probability.iloc[0]
            explanation=explain_classifier(bundle,query,score)
            self.assertAlmostEqual(explanation['ensemble_score'],score,places=10)
            self.assertEqual(set(explanation['table'].feature),set(bundle['low']['features']))
            with self.assertRaises(ValueError):explain_classifier(bundle,query,min(1,score+.01))
            with self.assertRaises(ValueError):explain_classifier(bundle,bundle['low']['reference'].iloc[:1],score)
            context_score=U.predict_bundle(bundle,query).context_probability.iloc[0]
            contextual=explain_context(bundle,query,context_score)
            self.assertAlmostEqual(contextual['context_score'],context_score,places=10)
            with self.assertRaises(ValueError):explain_context(bundle,query,min(1,context_score+.01))

    def test_new_representations_do_not_read_query_truth_or_enrollment_snapshot(self):
        import importlib.util
        path=ROOT/'02、模型实验/补充研究/05、成本敏感与无报名冷启动/代码/resolve_models.py'
        spec=importlib.util.spec_from_file_location('audit_resolution_models',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data=U.R.load();reference=data[data.week.lt(8)];query=data[data.week.eq(8)].iloc[:3]
        altered=query.assign(occupancy_rate=999.,attendees=999999,enrollments=999999,enroll_sched=999999)
        pd.testing.assert_frame_equal(module.cold_features(query),module.cold_features(altered))
        pd.testing.assert_frame_equal(module.low_features(reference,query,'without'),module.low_features(reference,altered,'without'))

    def test_regular_day_history_excludes_holiday_values_without_dropping_query_rows(self):
        import importlib.util
        path=ROOT/'02、模型实验/补充研究/09、日历情境历史/代码/context_history.py'
        spec=importlib.util.spec_from_file_location('context_candidate',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data=U.R.load();query=data[data.week.eq(11)].iloc[:3].copy();reference=data[data.week.lt(11)].copy()
        expected=module.features(reference,query)
        reference.loc[reference.date.eq(pd.Timestamp('2017-10-02')),'occupancy_rate']=999
        query['occupancy_rate']=777;query['attendees']=888
        pd.testing.assert_frame_equal(expected,module.features(reference,query))
        self.assertEqual(len(expected),len(query))
        self.assertFalse(expected.public_holiday.any())
