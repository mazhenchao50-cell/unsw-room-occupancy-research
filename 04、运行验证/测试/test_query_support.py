from datetime import time
from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03、系统应用/代码'))
from query_support import next_gap,brief,interval_text,EMPTY_PREDICTIONS
from replay import candidates
from i18n import LANGUAGES,t


class QuerySupportTests(unittest.TestCase):
    coverage={('2020-01-01','A'):{'complete':True,'source':'synthetic complete schedule for this boundary test'}}
    def fixture(self):
        s=pd.DataFrame(dict(session_id=['one'],date=['2020-01-01'],room=['A'],seats=[30],
            course_id=['course'],course_start=['09:00:00'],course_end=['10:00:00']))
        a=pd.DataFrame(dict(date=['2020-01-01'],room_code=['A'],start_time=['09:00:00'],end_time=['10:00:00']))
        return s,a

    def test_later_suggestion_keeps_duration_capacity_and_conflicts(self):
        s,a=self.fixture()
        later=next_gap(s,a,'2020-01-01',time(9),60,20,coverage=self.coverage)
        self.assertEqual(later['start'],time(10))
        _,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2020-01-01',later['start'],60,20,coverage=self.coverage)
        self.assertEqual(top.room.tolist(),['A'])
        self.assertIsNone(next_gap(s,a,'2020-01-01',time(9),60,31))

    def test_unknown_day_and_malformed_schedule_never_become_suggestions(self):
        s,a=self.fixture()
        self.assertIsNone(next_gap(s,a,'2020-01-02',time(9),60,20))
        a.loc[0,'end_time']='bad'
        self.assertIsNone(next_gap(s,a,'2020-01-01',time(9),60,20))

    def test_midnight_and_search_window_are_not_extended(self):
        s,a=self.fixture()
        self.assertIsNone(next_gap(s,a,'2020-01-01',time(23),60,20))
        s.loc[0,'course_end']='14:00:00';a.loc[0,'end_time']='14:00:00'
        self.assertIsNone(next_gap(s,a,'2020-01-01',time(9),60,20))
        with self.assertRaises(ValueError):next_gap(s,a,'2020-01-01',time(23,30),60,20)

    def test_brief_requires_a_current_unverified_candidate(self):
        s,a=self.fixture();_,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2020-01-01',time(10),60,20,coverage=self.coverage)
        for locale in LANGUAGES:
            value=brief(top,'A',locale,'2020-01-01',time(10),60,20)
            self.assertIn(t(locale,'brief_scope'),value)
            self.assertIn(t(locale,'next_steps'),value)
            self.assertIn('10:00',value);self.assertIn('11:00',value)
        with self.assertRaises(ValueError):brief(top,'old-room','zh','2020-01-01',time(10),60,20)
        top.loc[:,'verified_available']=True
        with self.assertRaises(ValueError):brief(top,'A','zh','2020-01-01',time(10),60,20)

    def test_interval_end_of_day_and_invalid_duration(self):
        self.assertEqual(interval_text(time(23),60),('23:00','24:00'))
        with self.assertRaises(ValueError):interval_text(time(23),61)
        with self.assertRaises(ValueError):interval_text(time(9),0)
