"""Execute all registered unit suites and bind success to every concrete test ID."""
from pathlib import Path
import sys,os,json,hashlib,unittest,ast
ROOT=Path(__file__).resolve().parents[2]
SUPPLEMENT='02、模型实验/补充研究/02、漏报与跨周稳定性/代码'


def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from flatten(test)
        else:yield test


def source_inventory(root=ROOT):
    root=Path(root);ids=[]
    files=[*(root/'04、运行验证/测试').glob('test_*.py'),root/SUPPLEMENT/'test_stable_alerts.py']
    for path in files:
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        module='supplement_stable_tests' if path.name=='test_stable_alerts.py' else path.stem
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                ids.extend(module+'.'+cls.name+'.'+fn.name for fn in cls.body if isinstance(fn,ast.FunctionDef) and fn.name.startswith('test_'))
    return sorted(ids)


def discover(root=ROOT):
    root=Path(root)
    loader=unittest.TestLoader()
    main=loader.discover(str(root/'04、运行验证/测试'))
    sys.path.insert(0,str(root/SUPPLEMENT))
    import importlib.util
    path=root/SUPPLEMENT/'test_stable_alerts.py'
    spec=importlib.util.spec_from_file_location('supplement_stable_tests',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.TestSuite([main,loader.loadTestsFromModule(module)])
    if loader.errors:raise ValueError('Test discovery failed: '+str(loader.errors))
    return suite


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.executed=[]
    def startTest(self,test):
        self.executed.append(test.id());super().startTest(test)


def validate_inventory(record,profile):
    expected=record['expected_ids'];actual=record['executed_ids']
    if not expected or len(set(expected))!=len(expected) or sorted(expected)!=sorted(actual):
        raise ValueError('Missing, duplicate or substituted test execution')
    if record['failed_ids'] or record['error_ids'] or record.get('unexpected_success_ids'):
        raise ValueError('Test failures present')
    if profile=='extended' and record['skipped_ids']:raise ValueError('Full validation forbids skips')
    if record.get('expected_failure_ids'):raise ValueError('Expected failures still require resolution')
    return dict(discovered=len(expected),passed=len(actual)-len(record['skipped_ids']),skipped=len(record['skipped_ids']))


def main():
    suite=discover();ids=sorted(t.id() for t in flatten(suite))
    if ids!=source_inventory():raise ValueError('Discovery omitted or substituted source-defined test methods')
    files=sorted([*(ROOT/'04、运行验证/测试').glob('test_*.py'),ROOT/SUPPLEMENT/'test_stable_alerts.py'])
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordedResult).run(suite)
    record=dict(expected_ids=ids,executed_ids=result.executed,failed_ids=[t.id() for t,_ in result.failures],
        error_ids=[t.id() for t,_ in result.errors],skipped_ids=[t.id() for t,_ in result.skipped],
        expected_failure_ids=[t.id() for t,_ in result.expectedFailures],unexpected_success_ids=[t.id() for t in result.unexpectedSuccesses],
        test_source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    path=ROOT/'04、运行验证/生成产物/测试清单/完整测试执行.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    try:validate_inventory(record,os.getenv('PROJECT_TEST_PROFILE','extended'))
    except ValueError as exc:print(exc,file=sys.stderr);return 1
    return 0


if __name__=='__main__':sys.exit(main())
