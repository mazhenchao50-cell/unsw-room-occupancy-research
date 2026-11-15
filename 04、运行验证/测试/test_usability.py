import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03、系统应用/代码'))
from usability import summarize


class UsabilityTests(unittest.TestCase):
    def record(self):
        return {'schema_version':1,'confirmed_human_trial':True,'participant_id':'TEST_ONLY',
                'observed_on':'2026-10-31','app_version':'TEST_ONLY',
                'tasks':[{'task_id':'T1','outcome':'completed','duration_seconds':20,
                          'assisted':True,'answer_code':'needs_verification'}]}

    def test_no_data_is_not_success(self):
        r=summarize([])
        self.assertEqual(r['status'],'awaiting_human_trials')
        self.assertIsNone(r['overall']['completion_rate'])

    def test_help_and_missing_tasks_are_visible(self):
        r=summarize([self.record()])
        self.assertEqual(r['overall']['completion_rate'],1)
        self.assertEqual(r['overall']['independent_correct_completion_rate'],0)
        self.assertEqual(r['missing_tasks'],3)

    def test_reject_template_duplicate_and_invalid_time(self):
        r=self.record(); r['confirmed_human_trial']=False
        with self.assertRaises(ValueError): summarize([r])
        with self.assertRaises(ValueError): summarize([self.record(),self.record()])
        for value in [-1,float('nan'),float('inf'),True]:
            r=self.record();r['tasks'][0]['duration_seconds']=value
            with self.assertRaises(ValueError): summarize([r])

    def test_wrong_understanding_is_not_success(self):
        r=self.record();r['tasks'][0].update(assisted=False,answer_code='incorrect')
        result=summarize([r])['overall']
        self.assertEqual(result['completion_rate'],1)
        self.assertEqual(result['understanding_rate'],0)
        self.assertEqual(result['independent_correct_completion_rate'],0)

    def test_versions_and_dates_cannot_be_mixed_or_missing(self):
        a=self.record();b=self.record();b.update(participant_id='TEST_2',app_version='OTHER')
        with self.assertRaises(ValueError): summarize([a,b])
        a['observed_on']=None
        with self.assertRaises(ValueError): summarize([a])


if __name__=='__main__': unittest.main()
