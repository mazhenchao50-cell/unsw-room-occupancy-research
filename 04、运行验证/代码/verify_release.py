"""Validate and rebuild the actual source ZIP in a fresh D-drive directory.

Uses the invoking environment and existing authorized raw inputs. No download,
dependency installation, publication, or third-party verification is performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from zipfile import ZipFile, BadZipFile

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE='04、运行验证/生成产物/发布准备/项目源码发布准备.zip'
DOCS=['README.md','evaluation_protocol.md','data_card.md','reproduction.md','sources.md','项目实施目录说明.md']
REQUIRED={f'05、文档依赖/文档/{n}' for n in DOCS}|{
    '04、运行验证/代码/run_all.py','04、运行验证/测试/test_app.py',
    '03、系统应用/代码/app.py','05、文档依赖/依赖/requirements-windows-py313.lock'}
RAW_NAMES={f'{y}_sem2_attendance_data.csv' for y in (2017,2018)}|{f'week{w}_computed_data.csv' for w in range(1,13)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_archive(path):
    with ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len({n.casefold() for n in names}):
            raise ValueError('Duplicate or Windows-aliased archive member')
        if sum(i.file_size for i in z.infolist())>50_000_000:
            raise ValueError('Unexpected source archive size')
        for info in z.infolist():
            n=info.filename;p=PurePosixPath(n)
            if (not n or '\\' in n or ':' in n or p.is_absolute() or
                any(part in ('.','..') or part.endswith((' ','.')) for part in n.split('/')) or
                stat.S_ISLNK(info.external_attr>>16)):
                raise ValueError('Unsafe archive path: '+n)
            if '/原始数据/' in n or '/生成产物/' in n or '/日志/' in n or n.endswith(('.joblib','.csv')):
                raise ValueError('Unexpected data or generated artifact in source archive: '+n)
        if z.testzip() is not None:raise ValueError('Archive CRC failure')
        manifest=json.loads(z.read('source_manifest.json'))
        if not isinstance(manifest,dict) or not REQUIRED<=set(manifest):
            raise ValueError('Missing required source/document: '+str(sorted(REQUIRED-set(manifest))))
        if set(names)!=set(manifest)|{'README.md','source_manifest.json','data_requirements.json'}:
            raise ValueError('Archive members do not match source manifest')
        for name,expected in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=expected:
                raise ValueError('Source hash mismatch: '+name)
        inputs=json.loads(z.read('data_requirements.json'))
        if len(inputs)!=14 or {item['file'] for item in inputs}!=RAW_NAMES:
            raise ValueError('Expected exactly fourteen UNSW inputs')
        return manifest,inputs


def validate_inputs(folder,requirements):
    for item in requirements:
        path=Path(folder)/item['file']
        if not path.is_file() or digest(path)!=item['sha256']:
            raise ValueError('Raw input missing or hash mismatch: '+item['file'])


def inspect_latest(root):
    root=Path(root);reports=sorted((root/'04、运行验证/日志').glob('release_validation_*/verification.json'))
    if not reports:return dict(status='missing',reason='尚无实际发布包重建记录')
    path=reports[-1];result=dict(report=str(path.relative_to(root)))
    try:
        d=json.loads(path.read_text(encoding='utf-8'))
        expected=[['-m','pip','check'],['04、运行验证/代码/run_all.py','--profile','extended'],['04、运行验证/测试/test_app.py']]
        stages=d.get('stages',[])
        if d.get('status')!='passed' or len(stages)!=3 or any(s.get('returncode')!=0 or s.get('command')!=cmd for s,cmd in zip(stages,expected)):
            return dict(result,status='not_passed',reason='最新发布包验证未完整通过')
        if digest(root/ARCHIVE)!=d['archive_sha256']:
            return dict(result,status='stale',reason='当前发布包与已验证ZIP不同')
        manifest,inputs=inspect_archive(root/ARCHIVE)
        if manifest!=d['source_sha256'] or any(digest(root/name)!=value for name,value in manifest.items()):
            return dict(result,status='stale',reason='当前源码或配套说明已变化')
        validate_inputs(root/'01、数据处理/原始数据/UNSW',inputs)
        if any(digest(root/name)!=value for name,value in d['uci_sha256'].items()):
            return dict(result,status='stale',reason='外部诊断输入已变化')
        return dict(result,status='passed',archive_sha256=d['archive_sha256'],
                    validation_directory=d['validation_directory'],
                    reason='实际ZIP在D盘新目录重建和四语测试通过；使用已有环境，不是GitHub或第三方复现')
    except (OSError,ValueError,KeyError,TypeError,BadZipFile) as exc:
        return dict(result,status='unverified',reason='无法核验发布包证据：'+str(exc))


def run(output_root):
    output_root=Path(output_root).resolve()
    if output_root.drive.upper()!='D:':raise ValueError('Release validation output must be on D:')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=ROOT/'04、运行验证/日志'/('release_validation_'+stamp)
    evidence.mkdir(parents=True)
    directory=output_root/stamp
    d=dict(status='running',scope='Actual source ZIP; same existing Python environment; no downloads or third-party claims',
           validation_directory=str(directory),python=sys.executable,python_version=sys.version,stages=[])
    def save():
        text=json.dumps(d,ensure_ascii=False,indent=2)
        (evidence/'verification.json').write_text(text,encoding='utf-8')
        if directory.is_dir():(directory/'verification.json').write_text(text,encoding='utf-8')
    save()
    try:
        archive=ROOT/ARCHIVE;manifest,inputs=inspect_archive(archive)
        raw=ROOT/'01、数据处理/原始数据/UNSW';validate_inputs(raw,inputs)
        uci=[ROOT/'01、数据处理/原始数据/UCI'/name for name in ['occupancy_detection.zip','source.html']]
        if not all(p.is_file() for p in uci):raise ValueError('UCI source files required for extended rebuild')
        directory.mkdir(parents=True,exist_ok=False)
        project=directory/'project';project.mkdir()
        for name in ['logs','tmp','cache']:(directory/name).mkdir()
        frozen=directory/'source.zip';shutil.copy2(archive,frozen)
        d.update(archive_sha256=digest(frozen),source_sha256=manifest,raw_inputs=inputs,
                 uci_sha256={p.relative_to(ROOT).as_posix():digest(p) for p in uci})
        if d['archive_sha256']!=digest(archive):raise ValueError('Archive changed while copying')
        with ZipFile(frozen) as z:z.extractall(project)
        for item in inputs:
            target=project/'01、数据处理/原始数据/UNSW'/item['file'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(raw/item['file'],target)
        validate_inputs(project/'01、数据处理/原始数据/UNSW',inputs)
        for source in uci:
            target=project/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            if digest(target)!=d['uci_sha256'][source.relative_to(ROOT).as_posix()]:raise ValueError('UCI copy mismatch')
        d['initial_generated_outputs_absent']=not (project/'02、模型实验/生成产物').exists() and not (project/'01、数据处理/清洗产物').exists()
        if not d['initial_generated_outputs_absent']:raise ValueError('Generated outputs present before rebuild')
        save()
        env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
            TMP=str(directory/'tmp'),TEMP=str(directory/'tmp'),TMPDIR=str(directory/'tmp'),PIP_CACHE_DIR=str(directory/'cache'))
        commands=[['-m','pip','check'],['04、运行验证/代码/run_all.py','--profile','extended'],['04、运行验证/测试/test_app.py']]
        for index,command in enumerate(commands,1):
            log=directory/'logs'/f'{index:02d}.log'
            print('RUN',command,'LOG',log,flush=True)
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run([sys.executable,'-u',*command],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT)
            d['stages'].append(dict(command=command,returncode=result.returncode,log=str(log)))
            if result.returncode:raise RuntimeError(f'Stage {index} failed; see {log}')
            save()
        d['status']='passed';save()
        print('PASS: actual source ZIP rebuilt;',evidence,flush=True)
        return 0
    except Exception as exc:
        d.update(status='failed',error=str(exc));save()
        print('FAILED:',exc,'Evidence:',evidence,file=sys.stderr,flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,default=Path('D:/ProjectTools/UNSW_ReleaseValidation'))
    sys.exit(run(parser.parse_args().output_root))
