"""Historical slot rule (experiment 19) inside the vacant-room candidate search."""
from datetime import time
from pathlib import Path
import json
import sys
import unittest
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'03、系统应用/代码'))
import free_slot_rule as F
from replay import candidates,load_slot_history,rule_reproduction,LISTED,conflict_detail
from query_support import EMPTY_PREDICTIONS,next_gap,brief
from i18n import LANGUAGES,t,room_display

STUDY=ROOT/'02、模型实验/补充研究/19、无课时段空教室识别/生成产物'


def history(rows):
    """rows: (room, day, hour, occupied)"""
    f=pd.DataFrame(rows,columns=['room','day','hour','occupied'])
    f['day']=pd.to_datetime(f.day);f['weekday']=f.day.dt.weekday;f['week']=1;f['peak']=f.occupied.map({True:9,False:0})
    return f[['room','day','week','weekday','hour','peak','occupied']]


class BuildTests(unittest.TestCase):
    def test_counting_rule_class_windows_week9_and_weekend(self):
        def row(ts,week,i,o,course=None,start=None,end=None):
            return dict(timestamp=ts,week=week,room_code='A',count_in=i,count_out=o,course_id=course,course_start=start,course_end=end)
        c=pd.DataFrame([row('2017-09-11 08:10:00',8,3,0),row('2017-09-11 08:20:00',8,4,0),row('2017-09-11 08:40:00',8,0,9),
            row('2017-09-11 08:50:00',8,1,0),row('2017-09-11 10:05:00',8,50,0,'C','10:00:00','11:00:00'),
            row('2017-09-11 11:10:00',8,0,0),row('2017-09-28 08:10:00',9,30,0),row('2017-09-16 08:10:00',8,30,0)])
        s=F.build_slot_history(c)
        self.assertEqual(sorted(s.day.dt.strftime('%Y-%m-%d').unique()),['2017-09-11'])
        # Hour 9 overlaps the 15-minute lead before 10:00 and hour 10 the class itself; hour 11 starts at its end.
        self.assertEqual(s.hour.tolist(),[8]+list(range(11,20)))
        first=s.iloc[0]
        self.assertEqual(int(first.peak),7)  # 3, 7, max(0,7-9)+0=0, 1
        self.assertTrue(first.occupied)
        self.assertFalse(s.iloc[1:].occupied.any())


class RuleTests(unittest.TestCase):
    h=history([('A','2017-09-04',9,True),('A','2017-08-28',9,False),('A','2017-08-21',9,False),
               ('B','2017-09-05',9,True),('A','2017-09-25',9,True),('A','2017-09-04',10,True),('A','2017-08-28',10,True)])

    def test_rate_reads_only_earlier_days_and_falls_back(self):
        self.assertEqual(F.slot_rate(self.h,'A','2017-09-11',9),(1/3,3))
        rate,n=F.slot_rate(self.h,'B','2017-09-11',9)  # B's only record is a Tuesday
        self.assertEqual(n,0)
        past=self.h[self.h.day.lt('2017-09-11')]
        self.assertAlmostEqual(rate,past.occupied.mean())
        self.assertIsNone(F.slot_rate(self.h,'A','2017-08-01',9))

    def test_scope_threshold_and_multi_hour_maximum(self):
        H=pd.Timedelta(hours=1)
        self.assertEqual(F.evaluate(self.h,'A','2017-09-16',9*H,10*H,[])['state'],'outside_scope')
        self.assertEqual(F.evaluate(self.h,'A','2017-09-11',7*H,8*H,[])['state'],'outside_scope')
        self.assertEqual(F.evaluate(self.h,'A','2017-09-11',19.5*H,20.5*H,[])['state'],'outside_scope')
        near=[(10*H,11*H)]
        self.assertEqual(F.evaluate(self.h,'A','2017-09-11',9*H,9*H+pd.Timedelta(minutes=50),near)['state'],'outside_scope')
        vacant=F.evaluate(self.h,'A','2017-09-11',9*H,10*H,[(11*H,12*H)])
        self.assertEqual((vacant['state'],vacant['hours'],vacant['history_n']),('vacant',[9],3))
        both=F.evaluate(self.h,'A','2017-09-11',9*H+pd.Timedelta(minutes=30),10*H+pd.Timedelta(minutes=30),[])
        self.assertEqual((both['state'],both['hours'],both['rate']),('used',[9,10],1.0))
        half=history([('A','2017-09-04',9,True),('A','2017-08-28',9,False)])
        self.assertEqual(F.evaluate(half,'A','2017-09-11',9*H,10*H,[])['state'],'used')


class CandidateTests(unittest.TestCase):
    def fixture(self):
        s=pd.DataFrame(dict(session_id=['x','y'],date=['2017-09-11','2017-09-11'],room=['A','B'],seats=[40,80],
            course_id=['c1','c2'],course_start=['13:00:00','09:00:00'],course_end=['14:00:00','10:00:00']))
        a=pd.DataFrame(dict(date=['2017-09-11'],room_code=['A'],start_time=['13:00:00'],end_time=['14:00:00']))
        # Room C is often used, so the all-room fallback (8/14) is at least one half: no fallback candidates.
        h=history([('A','2017-09-04',9,False),('A','2017-08-28',9,False),('B','2017-09-04',9,False),
                   ('A','2017-09-04',11,True),('A','2017-08-28',11,True),('A','2017-09-04',12,False),
                   ('A','2017-09-04',14,False),('A','2017-08-28',14,False)]
                  +[('C',day,15,True) for day in ('2017-09-04','2017-08-28','2017-08-21','2017-08-14','2017-08-07','2017-07-31')])
        return s,a,h

    def test_rule_lists_only_clear_low_use_slots_and_never_overrides_conflicts(self):
        s,a,h=self.fixture()
        rooms,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9),60,1)
        self.assertTrue(top.empty);self.assertEqual(set(rooms.status),{'schedule_unknown','scheduled_conflict'})
        rooms,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9),60,1,slot_history=h)
        self.assertEqual(rooms.set_index('room').status.to_dict(),{'A':'history_rule_candidate','B':'scheduled_conflict'})
        self.assertEqual(top.room.tolist(),['A']);self.assertFalse(top.verified_available.any())
        rooms,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(11),60,1,slot_history=h)
        self.assertEqual(rooms.set_index('room').status['A'],'history_rule_likely_used');self.assertNotIn('A',top.room.tolist())
        rooms,_,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(12),60,1,slot_history=h)
        self.assertEqual(rooms.set_index('room').status['A'],'schedule_unknown')  # 12:00-13:00 touches the 12:45 lead
        rooms,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9),60,41,slot_history=h)
        self.assertTrue(top.empty)

    def test_brief_and_later_search_use_the_rule(self):
        s,a,h=self.fixture()
        _,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9),60,10,slot_history=h)
        for locale in LANGUAGES:
            text=brief(top,'A',locale,'2017-09-11',time(9),60,10)
            self.assertIn(t(locale,'history_basis').format(rate='0%',n=2),text)
        self.assertEqual(top.status.iloc[0],'history_rule_candidate');self.assertIn(top.status.iloc[0],LISTED)
        later=next_gap(s,a,'2017-09-11',time(11),60,10,slot_history=h)
        self.assertEqual(later['start'],time(14))  # earlier starts touch hour 12 or 13, inside the 13:00 class window
        self.assertIsNone(next_gap(s,a,'2017-09-11',time(11),60,10))
        no_slot=history([('C','2017-09-04',15,False)])
        _,top,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9),60,10,slot_history=no_slot)
        self.assertEqual(int(top.history_n.iloc[0]),0)
        self.assertIn(t('zh','history_basis_prior').format(rate='0%',n=0),brief(top,'A','zh','2017-09-11',time(9),60,10))

    def test_conflict_times_and_end_of_class_block(self):
        H=lambda h,m=0:pd.Timedelta(hours=h,minutes=m)
        times,free=conflict_detail([(H(9),H(10)),(H(10),H(11,30)),(H(13),H(14)),(pd.NaT,H(15))],H(9,30),H(10,30))
        self.assertEqual((times,free),('09:00–10:00, 10:00–11:30','11:30'))   # back-to-back classes extend the block
        self.assertEqual(conflict_detail([(H(13),H(14))],H(9),H(10)),(None,None))
        s,a,h=self.fixture()
        rooms,_,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9,30),60,1,slot_history=h)
        b=rooms.set_index('room').loc['B']
        self.assertEqual((b.status,b.conflict_times,b.free_from),('scheduled_conflict','09:00–10:00','10:00'))
        for locale in LANGUAGES:
            shown=room_display(rooms,locale).set_index(t(locale,'room'))
            self.assertEqual(shown.loc['B',t(locale,'reason')],t(locale,'conflict_detail_reason').format(times='09:00–10:00',free='10:00'))
            self.assertNotIn('conflict_times',shown.columns)

    def test_display_translates_rule_statuses(self):
        s,a,h=self.fixture()
        rooms,_,_=candidates(s,a,EMPTY_PREDICTIONS,'2017-09-11',time(9),60,1,slot_history=h)
        for locale in LANGUAGES:
            f=room_display(rooms,locale).set_index(t(locale,'room'))
            self.assertEqual(f.loc['A',t(locale,'status')],t(locale,'history_vacant'))
            self.assertEqual(f.loc['A',t(locale,'history_rate')],'0%')
            self.assertEqual(f.loc['B',t(locale,'history_rate')],'—')


class EvidenceTests(unittest.TestCase):
    def test_constants_and_wording_match_frozen_experiments(self):
        pooled=json.loads((STUDY/'report.json').read_text(encoding='utf-8'))['pooled']
        upper=json.loads((STUDY/'carryover.json').read_text(encoding='utf-8'))['upper']['slot_history']
        self.assertEqual(F.EVIDENCE['recommend_precision'],round(pooled['slot_history']['recommend_precision'],3))
        self.assertEqual(F.EVIDENCE['vacant_coverage'],round(pooled['slot_history']['vacant_coverage'],3))
        self.assertEqual(F.EVIDENCE['no_class_precision'],round(pooled['timetable']['recommend_precision'],3))
        self.assertEqual(F.EVIDENCE['upper_bound_recommend_precision'],round(upper['recommend_precision'],3))
        self.assertEqual(F.EVIDENCE['upper_bound_vacant_coverage'],round(upper['vacant_coverage'],3))
        for locale in LANGUAGES:
            self.assertIn('84%',t(locale,'history_rule_scope'));self.assertIn('57%',t(locale,'history_rule_scope'))
            self.assertIn('84%',t(locale,'history_basis'))

    def test_real_data_reproduces_experiment_19(self):
        slots=load_slot_history(ROOT)
        self.assertEqual(len(slots),1268)
        result=rule_reproduction(slots)
        self.assertEqual(result['slots'],516)
        for key in ('recommend_precision','vacant_coverage','no_class_precision'):
            self.assertEqual(round(result[key],3),F.EVIDENCE[key],key)


if __name__=='__main__':unittest.main()
