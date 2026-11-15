"""Rebuild in an output-free source snapshot with the invoking Python environment.

This does not install dependencies or download UNSW data. Use a newly installed
environment to test installation plus rebuilding. Original results are preserved.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=['core','extended'],default='extended')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'01、数据处理/原始数据/UNSW')
    args=parser.parse_args()
    from run_all import missing_inputs
    missing=missing_inputs(args.data_dir.resolve(),args.profile)
    if missing:
        parser.error('Missing inputs:\n'+'\n'.join(missing))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'04、运行验证/日志'/f'reproduction_{stamp}'
    snapshot=out/'project'
    snapshot.mkdir(parents=True)
    # The managed desktop may point Windows TEMP at a protected app-container
    # directory. Keep tempfile-based tests inside this writable evidence folder.
    temp_dir=out/'tmp'
    temp_dir.mkdir()
    for name in ('01、数据处理/代码','02、模型实验/代码','03、系统应用/代码',
                 '04、运行验证/代码','04、运行验证/测试','05、文档依赖/文档','05、文档依赖/依赖'):
        shutil.copytree(ROOT/name,snapshot/name,ignore=shutil.ignore_patterns('__pycache__','generated'))
    if args.profile=='extended':
        shutil.copytree(ROOT/'01、数据处理/原始数据/UCI',snapshot/'01、数据处理/原始数据/UCI')
    assert not (snapshot/'02、模型实验/生成产物').exists() and not (snapshot/'01、数据处理/清洗产物').exists()
    files=[p for p in snapshot.rglob('*') if p.is_file()]
    report={'status':'running','profile':args.profile,'python':sys.executable,'version':sys.version,
            'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'fresh_outputs':True,'dependency_installation':'See separate pip installation report; not performed by this script.',
            'source_sha256':{str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'stages':[]}
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',
                                      TMP=str(temp_dir),TEMP=str(temp_dir),TMPDIR=str(temp_dir))
    commands=[['-m','pip','check'],['04、运行验证/代码/run_all.py','--profile',args.profile,'--data-dir',str(args.data_dir.resolve())],
              ['04、运行验证/测试/test_app.py']]
    def save():
        (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    for i,command in enumerate(commands,1):
        log=out/f'{i:02d}.log'
        print('RUN',command,'LOG',log,flush=True)
        with log.open('w',encoding='utf-8') as stream:
            result=subprocess.run([sys.executable,'-u',*command],cwd=snapshot,env=env,stdout=stream,stderr=subprocess.STDOUT)
        report['stages'].append({'command':command,'returncode':result.returncode,'log':log.name})
        if result.returncode:
            report['status']='failed';save()
            print('FAILED; retained evidence:',out,flush=True)
            return result.returncode
        save()
    report['status']='passed';save()
    from build_acceptance import build
    build()
    print('PASS: snapshot rebuild and UI. Evidence:',out,flush=True)
    return 0

if __name__=='__main__':
    sys.exit(main())
