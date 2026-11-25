import hashlib
import importlib.util
import subprocess
import sys
import unittest
import tempfile
import contextlib
import io
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class RebuildTests(unittest.TestCase):
    def test_missing_input_and_failed_stage_do_not_cascade(self):
        spec=importlib.util.spec_from_file_location('rebuild_failure',ROOT/'04、运行验证/代码/run_all.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            self.assertEqual(len(module.missing_inputs(temp,'core')),14)
            (temp/'week1_computed_data.csv').write_text('')
            self.assertEqual(len(module.missing_inputs(temp,'core')),14)
            (temp/'week1_computed_data.csv').write_text('header\nvalue')
            self.assertEqual(len(module.missing_inputs(temp,'core')),13)
            with patch.object(module,'ROOT',temp), patch.object(module.subprocess,'run',return_value=subprocess.CompletedProcess([],7)) as runner, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.execute_commands([['first.py'],['never.py']],'core'),7)
                self.assertEqual(runner.call_count,1)
            import json
            report=json.loads(next((temp/'04、运行验证/日志').glob('*/execution.json')).read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'failed')
            self.assertEqual(len(report['stages']),1)

    def test_profiles_generate_required_artifacts_before_testing(self):
        spec=importlib.util.spec_from_file_location('rebuild_plan',ROOT/'04、运行验证/代码/run_all.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        core=module.build_commands(Path('raw'),'core')
        self.assertNotIn(['02、模型实验/代码/models/improvement_v5.py'],core)
        with patch.dict(module.os.environ,{'UNSW_DOWNLOAD_DIR':'D:/fixture'}):
            extended=module.build_commands(Path('raw'),'extended',True)
        test_pos=extended.index(['04、运行验证/代码/run_tests.py'])
        for name in ('improvement_v3','improvement_v4'):
            self.assertLess(extended.index(['02、模型实验/代码/models/'+name+'.py']),test_pos)
        self.assertLess(extended.index(['02、模型实验/代码/models/improvement_v5.py']),test_pos)
        self.assertLess(extended.index(['02、模型实验/代码/models/external_uci.py','--download']),test_pos)
        self.assertLess(extended.index(['02、模型实验/代码/models/forward_cold_benchmark.py']),test_pos)
        self.assertNotIn(['02、模型实验/代码/models/forward_cold_benchmark.py'],core)
        standard=module.build_commands(Path('raw'),'standard')
        self.assertEqual(standard,module.build_commands(Path('raw')))
        self.assertIn(['02、模型实验/代码/models/unified.py'],standard)
        self.assertIn(['04、运行验证/代码/numeric_acceptance.py'],standard)
        self.assertLess(standard.index(['02、模型实验/代码/models/unified.py']),
                        standard.index(['04、运行验证/代码/numeric_acceptance.py']))
        self.assertNotIn(['02、模型实验/代码/models/external_uci.py'],standard)
        self.assertNotIn(['02、模型实验/代码/models/forward_cold_benchmark.py'],standard)

    def test_report_generation_preserves_curated_documents(self):
        paths=[ROOT/'05、文档依赖/文档/README.md',ROOT/'05、文档依赖/文档/evaluation_protocol.md',ROOT/'05、文档依赖/文档/data_card.md']
        before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable,str(ROOT/'04、运行验证/代码/build_reports.py')],cwd=ROOT,check=True,capture_output=True)
        after=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        self.assertEqual(before,after)
        self.assertTrue((ROOT/'05、文档依赖/文档/generated/README_baseline.md').exists())
