import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'03、系统应用/代码'))
from usability import summarize,sus_score,load_csv,load_protocol,ANSWERS,TASK_VERSION,CSV_COLUMNS

ALL_CORRECT=[{'task_id':tid,'outcome':'completed','duration_seconds':60,'assisted':False,'answer_code':code} for tid,code in ANSWERS.items()]


class UsabilityTests(unittest.TestCase):
    def record(self,pid='TEST_ONLY',tasks=None,sus=None):
        return {'schema_version':2,'confirmed_human_trial':True,'participant_id':pid,'observed_on':'2026-11-25','language':'ko',
                'app_version':TASK_VERSION,'tasks':[dict(t) for t in (tasks if tasks is not None else ALL_CORRECT[:1])],
                'sus':list(sus or [4,2,4,2,4,2,4,2,4,2])}

    def test_no_data_is_not_success(self):
        r=summarize([],load_protocol()[0])
        self.assertEqual(r['status'],'awaiting_human_trials')
        self.assertIsNone(r['overall']['completion_rate'])
        self.assertEqual(r['criteria']['status'],'insufficient_participants');self.assertIsNone(r['criteria']['met'])

    def test_help_and_missing_tasks_are_visible(self):
        t=dict(ALL_CORRECT[0],assisted=True)
        r=summarize([self.record(tasks=[t])])
        self.assertEqual(r['overall']['completion_rate'],1)
        self.assertEqual(r['overall']['independent_correct_completion_rate'],0)
        self.assertEqual(r['missing_tasks'],3)

    def test_reject_template_duplicate_invalid_time_language_and_version(self):
        r=self.record(); r['confirmed_human_trial']=False
        with self.assertRaises(ValueError): summarize([r])
        with self.assertRaises(ValueError): summarize([self.record(),self.record()])
        for value in [-1,float('nan'),float('inf'),True]:
            r=self.record();r['tasks'][0]['duration_seconds']=value
            with self.assertRaises(ValueError): summarize([r])
        for key,value in [('language','fr'),('app_version','unified_v6_20261123'),('observed_on',None),('schema_version',1)]:
            r=self.record();r[key]=value
            with self.assertRaises(ValueError): summarize([r])
        r=self.record();r['tasks'][0]['answer_code']='needs_verification'   # old task-set answer is not valid any more
        with self.assertRaises(ValueError): summarize([r])

    def test_wrong_understanding_is_not_success(self):
        r=self.record();r['tasks'][0].update(answer_code='incorrect')
        result=summarize([r])['overall']
        self.assertEqual(result['completion_rate'],1)
        self.assertEqual(result['understanding_rate'],0)
        self.assertEqual(result['independent_correct_completion_rate'],0)

    def test_sus_scoring_follows_brooke(self):
        self.assertEqual(sus_score([3]*10),50.0)
        self.assertEqual(sus_score([5,1]*5),100.0)
        self.assertEqual(sus_score([1,5]*5),0.0)
        for bad in [[3]*9,[0]+[3]*9,[6]+[3]*9,[3.0]*10,None]:
            with self.assertRaises(ValueError): sus_score(bad)
        r=self.record();r['sus']=[3]*9
        with self.assertRaises(ValueError): summarize([r])

    def test_frozen_criteria(self):
        protocol=load_protocol()[0]
        good=[self.record(f'P0{i}',ALL_CORRECT) for i in range(1,6)]
        self.assertEqual(summarize(good[:4],protocol)['criteria']['status'],'insufficient_participants')
        result=summarize(good,protocol)['criteria']
        self.assertTrue(result['met'])
        weak=[dict(r) for r in good];weak[0]['sus']=[3]*10;weak[1]['sus']=[3]*10;weak[2]['sus']=[3]*10
        self.assertFalse(summarize(weak,protocol)['criteria']['checks']['mean_sus'])
        missing=[self.record(f'P0{i}',ALL_CORRECT[:3]) for i in range(1,6)]   # T4 never observed counts against it
        checks=summarize(missing,protocol)['criteria']['checks']
        self.assertFalse(checks['every_task_independent_correct']);self.assertFalse(checks['overall_independent_correct'])
        helped=[self.record(f'P0{i}',[dict(t,assisted=(t['task_id']=='T3' and i<=3)) for t in ALL_CORRECT]) for i in range(1,6)]
        checks=summarize(helped,protocol)['criteria']['checks']
        self.assertFalse(checks['every_task_independent_correct'])   # T3 2/5 independent
        self.assertTrue(checks['overall_independent_correct'])        # 17/20

    def test_csv_sheet_round_trip_and_blank_sheet(self):
        # The live sheet holds real observations later and is not packaged; only its header contract is checked here.
        sheet=ROOT/'05、文档依赖/文档/usability/记录表.csv'
        if sheet.exists():self.assertEqual(sheet.read_text(encoding='utf-8-sig').splitlines()[0],','.join(CSV_COLUMNS))
        header=','.join(CSV_COLUMNS)
        with tempfile.TemporaryDirectory() as folder:
            blank=Path(folder)/'blank.csv';blank.write_text(header+'\n',encoding='utf-8-sig')
            self.assertEqual(load_csv(blank),[])
            blank.write_text('participant_id,observed_on\n',encoding='utf-8-sig')
            with self.assertRaises(ValueError):load_csv(blank)
        row=['P01','2026-11-25','zh','yes']+sum([['completed','75','no',code] for code in ANSWERS.values()],[])+['4','2','4','2','4','2','4','2','4','2','找候选时犹豫']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sheet.csv';path.write_text(header+'\n'+','.join(row)+'\n',encoding='utf-8-sig')
            records=load_csv(path)
            self.assertEqual(len(records),1);self.assertEqual(records[0]['tasks'],[dict(t,duration_seconds=75.0) for t in ALL_CORRECT])
            self.assertEqual(summarize(records)['sus']['mean'],75.0)
            path.write_text(header+'\n'+','.join(row[:3]+['no']+row[4:])+'\n',encoding='utf-8-sig')
            with self.assertRaises(ValueError): summarize(load_csv(path))
            path.write_text(header+'\n'+','.join(row[:21]+[''])+'\n',encoding='utf-8-sig')
            with self.assertRaises(ValueError): load_csv(path)

    def test_protocol_matches_code(self):
        protocol,digest=load_protocol()
        self.assertEqual(protocol['task_version'],TASK_VERSION);self.assertEqual(len(digest),64)
        template=json.loads((ROOT/'05、文档依赖/文档/usability/record_template.json').read_text(encoding='utf-8'))
        self.assertEqual(template['app_version'],TASK_VERSION);self.assertFalse(template['confirmed_human_trial'])
        self.assertEqual([t['task_id'] for t in template['tasks']],list(ANSWERS))


if __name__=='__main__': unittest.main()
