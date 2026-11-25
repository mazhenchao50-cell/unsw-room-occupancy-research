import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'04、运行验证/代码'))
import verify_release as V


class ReleaseTests(unittest.TestCase):
    def test_full_validation_rejects_skipped_or_missing_test_execution(self):
        count=len(V.source_inventory(V.ROOT))
        self.assertEqual(V.unit_result(f'Ran {count} tests in 1.2s\n\nOK\n','extended'),dict(discovered=count,passed=count,skipped=0))
        self.assertEqual(V.unit_result(f'Ran {count} tests in 1.2s\n\nOK (skipped=7)\n','standard')['skipped'],7)
        for text in ['Ran 94 tests in 1.2s\nOK (skipped=7)\n','Ran 0 tests in 0s\nOK\n','Ran 94 tests in 1s\nFAILED (errors=1)\n','no test log']:
            with self.assertRaises(ValueError):V.unit_result(text,'extended')
        with self.assertRaises(ValueError):V.unit_result('Ran 1 test in 0.1s\nOK\n','extended')

    def archive(self,root,omit=None,extra=None,tamper=False):
        files={name:(b'class Fixture:\n    def test_fixture(self): pass\n' if Path(name).name.startswith('test_') else b'fixture') for name in V.REQUIRED if name!=omit}
        inputs=[{'file':name,'sha256':hashlib.sha256(b'data').hexdigest()} for name in sorted(V.RAW_NAMES)]
        manifest={name:hashlib.sha256(value).hexdigest() for name,value in files.items()}
        path=root/V.ARCHIVE;path.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(path,'w') as z:
            for name,value in files.items():z.writestr(name,b'changed' if tamper else value)
            z.writestr('README.md','guide')
            z.writestr('source_manifest.json',json.dumps(manifest))
            z.writestr('data_requirements.json',json.dumps(inputs))
            if extra:z.writestr(extra,b'outside')
        return path,manifest,inputs

    def test_release_requires_documents_read_by_rebuild_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['README.md','data_card.md','evaluation_protocol.md']:
                with self.subTest(document=name):
                    path,_,_=self.archive(root,omit='05、文档依赖/文档/'+name)
                    with self.assertRaisesRegex(ValueError,'Missing required'):V.inspect_archive(path)
            path,_,_=self.archive(root);V.inspect_archive(path)

    def test_unsafe_or_changed_archives_are_rejected_before_extracting(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['../outside.py','C:/outside.py','x./outside.py']:
                with self.subTest(path=name):
                    path,_,_=self.archive(root,extra=name)
                    with self.assertRaisesRegex(ValueError,'Unsafe'):V.inspect_archive(path)
            path,_,_=self.archive(root,extra='dir\\outside.py')
            with self.assertRaises(ValueError):V.inspect_archive(path)
            path,_,_=self.archive(root,tamper=True)
            with self.assertRaisesRegex(ValueError,'hash mismatch'):V.inspect_archive(path)

    def test_wrong_raw_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,_,inputs=self.archive(root)
            for item in inputs:(root/item['file']).write_bytes(b'data')
            V.validate_inputs(root,inputs)
            (root/inputs[0]['file']).write_bytes(b'another dataset')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):V.validate_inputs(root,inputs)

    def evidence(self,root):
        path,manifest,inputs=self.archive(root)
        for name in manifest:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            with ZipFile(path) as archive:p.write_bytes(archive.read(name))
        raw=root/'01、数据处理/原始数据/UNSW';raw.mkdir(parents=True)
        for item in inputs:(raw/item['file']).write_bytes(b'data')
        uci={}
        for name in ['occupancy_detection.zip','source.html']:
            p=root/'01、数据处理/原始数据/UCI'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'uci')
            uci[p.relative_to(root).as_posix()]=V.digest(p)
        record=dict(status='passed',archive_sha256=V.digest(path),source_sha256=manifest,uci_sha256=uci,validation_directory='D:/fixture',
            stages=[dict(command=cmd,returncode=0) for cmd in [['-m','pip','check'],['04、运行验证/代码/run_all.py','--profile','extended'],['04、运行验证/测试/test_app.py']]])
        ids=V.source_inventory(root)
        inventory=dict(expected_ids=ids,executed_ids=ids,failed_ids=[],error_ids=[],skipped_ids=[],
            test_source_sha256={n:h for n,h in manifest.items() if Path(n).name.startswith('test_')})
        record.update(test_contract=2,test_inventory=inventory,unit_tests=V.validate_inventory(inventory,'extended'))
        p=root/'04、运行验证/日志/release_validation_1/verification.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(record),encoding='utf-8')
        return path,p

    def test_source_and_archive_changes_invalidate_passed_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive,_=self.evidence(root)
            self.assertEqual(V.inspect_latest(root)['status'],'passed')
            added=root/'02、模型实验/代码/new_unpacked_model.py';added.parent.mkdir(parents=True,exist_ok=True);added.write_text('new source',encoding='utf-8')
            self.assertEqual(V.inspect_latest(root)['status'],'stale')
            added.unlink()
            self.assertEqual(V.inspect_latest(root)['status'],'passed')
            p=root/'05、文档依赖/文档/data_card.md';p.write_bytes(b'changed')
            self.assertEqual(V.inspect_latest(root)['status'],'stale')
            p.write_bytes(b'fixture');archive.write_bytes(archive.read_bytes()+b'changed')
            self.assertEqual(V.inspect_latest(root)['status'],'stale')

    def test_standard_profile_requires_matching_complete_stages(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,p=self.evidence(root)
            d=json.loads(p.read_text(encoding='utf-8'))
            d.update(profile='standard',uci_sha256={})
            d['stages'][1]['command'][-1]='standard'
            p.write_text(json.dumps(d),encoding='utf-8')
            self.assertEqual(V.inspect_latest(root)['status'],'passed')
            d['stages'][1]['command'][-1]='core'
            p.write_text(json.dumps(d),encoding='utf-8')
            self.assertEqual(V.inspect_latest(root)['status'],'not_passed')
    def test_latest_failure_is_not_hidden_by_older_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.evidence(root)
            p=root/'04、运行验证/日志/release_validation_2/verification.json';p.parent.mkdir();p.write_text('{"status":"failed"}')
            self.assertEqual(V.inspect_latest(root)['status'],'not_passed')
