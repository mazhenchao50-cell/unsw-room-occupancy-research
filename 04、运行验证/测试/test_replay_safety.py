import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03、系统应用/代码'))
from replay import candidates

class ReplaySafetyTests(unittest.TestCase):
    def setUp(self):
        self.s=pd.DataFrame([{'room':'A','seats':30,'date':'2017-01-01','course_start':'09:00:00','course_end':'10:00:00','session_id':'s'}])
        self.a=pd.DataFrame([{'room_code':'A','date':'2017-01-01','start_time':'09:00:00','end_time':'10:00:00'}])
        self.p=pd.DataFrame({'session_id':['s'],'prediction':[0.]})

    def test_malformed_or_reversed_schedule_is_never_candidate(self):
        for start,end in [('09:00:00','09:00:00'),('12:00:00','09:00:00'),('-01:00:00','01:00:00'),('23:00:00','25:00:00'),('bad',None)]:
            with self.subTest(start=start,end=end):
                a=self.a.copy();a['start_time']=start;a['end_time']=end
                rooms,top,_=candidates(self.s,a,self.p,'2017-01-01','15:00:00')
                self.assertTrue(top.empty)
                self.assertEqual(rooms.status.iloc[0],'schedule_unknown')
                s=self.s.copy();s['course_start']=start;s['course_end']=end
                _,top,_=candidates(s,self.a,self.p,'2017-01-01','15:00:00')
                self.assertTrue(top.empty)

    def test_invalid_query_and_capacity_are_rejected(self):
        for start,duration,capacity in [('bad',60,1),('-01:00:00',60,1),('24:00:00',60,1),('23:30:00',60,1),
            ('12:00:00',float('nan'),1),('12:00:00',float('inf'),1),('12:00:00',-1,1),
            ('12:00:00',60,float('nan')),('12:00:00',60,2.5),('12:00:00',60,True)]:
            with self.subTest(start=start,duration=duration,capacity=capacity):
                with self.assertRaises(ValueError):candidates(self.s,self.a,self.p,'2017-01-01',start,duration,capacity)

    def test_missing_capacity_and_midnight_boundary(self):
        _,top,_=candidates(self.s,self.a,self.p,'2017-01-01','23:00:00',60,30,
            coverage={('2017-01-01','A'):{'complete':True,'source':'synthetic complete schedule'}})
        self.assertEqual(len(top),1)
        self.s['seats']=float('nan')
        _,top,_=candidates(self.s,self.a,self.p,'2017-01-01','15:00:00')
        self.assertTrue(top.empty)
