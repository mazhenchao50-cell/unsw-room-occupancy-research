import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('evidence',ROOT/'04、运行验证/代码/reproduction_evidence.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)

class EvidenceTests(unittest.TestCase):
    def fixture(self,root):
        p=root/'04、运行验证/代码/sample.py';p.parent.mkdir(parents=True);p.write_text('x=1')
        report=root/'04、运行验证/日志/reproduction_20261106/verification.json';report.parent.mkdir(parents=True)
        inputs=[]
        raw=root/'01、数据处理/原始数据/UNSW';raw.mkdir(parents=True)
        for n in [f'{y}_sem2_attendance_data.csv' for y in (2017,2018)]+[f'week{w}_computed_data.csv' for w in range(1,13)]:
            q=raw/n;q.write_text('data');inputs.append({'file':n,'sha256':E.digest(q)})
        m=report.parent/'project/01、数据处理/清洗产物/input_manifest.json';m.parent.mkdir(parents=True);m.write_text(json.dumps({'files':inputs}))
        data={'status':'passed','profile':'core','source_sha256':{p.relative_to(root).as_posix():E.digest(p)},'stages':[{'command':c,'returncode':0} for c in [['-m','pip','check'],['04、运行验证/代码/run_all.py'],['04、运行验证/测试/test_app.py']]]}
        report.write_text(json.dumps(data),encoding='utf-8')
        return p,report,m

    def test_valid_then_source_and_raw_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);p,report,m=self.fixture(r)
            self.assertEqual(E.inspect_latest(r)['status'],'passed')
            p.write_text('x=2');self.assertEqual(E.inspect_latest(r)['status'],'stale')
            p.write_text('x=1');(r/'01、数据处理/原始数据/UNSW/week1_computed_data.csv').write_text('changed')
            self.assertEqual(E.inspect_latest(r)['status'],'stale')

    def test_latest_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);self.fixture(r)
            p=r/'04、运行验证/日志/reproduction_20261107/verification.json';p.parent.mkdir();p.write_text('{"status":"failed"}')
            self.assertEqual(E.inspect_latest(r)['status'],'not_passed')

    def test_missing_input_manifest_and_incomplete_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);_,p,m=self.fixture(r);m.unlink()
            self.assertEqual(E.inspect_latest(r)['status'],'unverified')
            d=json.loads(p.read_text());d['stages']=d['stages'][:2];p.write_text(json.dumps(d))
            self.assertEqual(E.inspect_latest(r)['status'],'not_passed')
