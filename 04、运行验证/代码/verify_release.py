"""Validate and rebuild the actual source ZIP in a fresh D-drive directory.

Uses the invoking environment and existing authorized raw inputs. No download,
dependency installation, publication, or third-party verification is performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from run_tests import validate_inventory,source_inventory
from zipfile import ZipFile, BadZipFile

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE='04、运行验证/生成产物/发布准备/项目源码发布准备.zip'
# 项目外的环境与验证存档（2026-11-23起由D:/ProjectTools迁入毕业设计文件夹第11号目录）
ENV_ARCHIVE=ROOT.parent/'11、运行环境与验证存档（原D盘）'
CALENDAR_DEFAULT=ENV_ARCHIVE/'2、外部来源证据/学期日历原件_20261117'
DOCS=['README.md','evaluation_protocol.md','data_card.md','reproduction.md','sources.md','项目实施目录说明.md']
REQUIRED={f'05、文档依赖/文档/{n}' for n in DOCS}|{
    '04、运行验证/代码/run_all.py','04、运行验证/测试/test_app.py',
    '02、模型实验/补充研究/02、漏报与跨周稳定性/代码/test_stable_alerts.py',
    '03、系统应用/代码/app.py','05、文档依赖/依赖/requirements-windows-py313.lock','05、文档依赖/依赖/unsw_input_hashes.json',
    '05、文档依赖/依赖/unsw_field_evidence.json'}
RAW_NAMES={f'{y}_sem2_attendance_data.csv' for y in (2017,2018)}|{f'week{w}_computed_data.csv' for w in range(1,13)}


def publication_sources(root=ROOT):
    """One source-selection contract for packaging and freshness verification."""
    root=Path(root);paths=[]
    for folder in ['01、数据处理/代码','02、模型实验/代码','03、系统应用/代码','04、运行验证/代码','04、运行验证/测试','05、文档依赖/依赖']:
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.txt','.lock','.json') and '__pycache__' not in p.parts)
    paths.extend(p for name in DOCS if (p:=root/'05、文档依赖/文档'/name).is_file())
    # Human-trial protocol, template and printed materials (2026-11-24). The filled sheet 记录表.csv and records/
    # hold participant observations and are never packaged.
    paths.extend(p for p in (root/'05、文档依赖/文档/usability').glob('*') if p.is_file() and p.suffix in ('.md','.json'))
    paths.extend(p for p in (root/'02、模型实验/补充研究').rglob('*') if p.is_file() and p.suffix in ('.py','.json') and '代码' in p.parts and '__pycache__' not in p.parts)
    return sorted(set(paths))


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


def unit_result(text,profile,expected_ids=None):
    matches=re.findall(r'^Ran (\d+) tests? in ',text,re.M)
    if len(matches)!=1 or not re.search(r'^OK(?: \(skipped=\d+\))?\s*$',text,re.M):
        raise ValueError('Missing or failed unittest summary')
    count=int(matches[0]);skip=re.search(r'^OK \(skipped=(\d+)\)',text,re.M)
    skipped=int(skip[1]) if skip else 0
    expected_ids=source_inventory(ROOT) if expected_ids is None else expected_ids
    if count!=len(expected_ids) or len(set(expected_ids))!=len(expected_ids):
        raise ValueError('Test count does not match the complete source-defined inventory')
    if count<=0 or skipped>count or (profile=='extended' and skipped):
        raise ValueError('Full validation requires actual tests and zero skips')
    return dict(discovered=count,passed=count-skipped,skipped=skipped)


def inspect_latest(root):
    root=Path(root);reports=sorted((root/'04、运行验证/日志').glob('release_validation_*/verification.json'))
    if not reports:return dict(status='missing',reason='尚无实际发布包重建记录')
    path=reports[-1];result=dict(report=str(path.relative_to(root)))
    try:
        d=json.loads(path.read_text(encoding='utf-8'))
        profile=d.get('profile','extended')  # Earlier evidence used extended only.
        if profile not in ('standard','extended'):
            return dict(result,status='not_passed',reason='不支持的重建范围')
        expected=[['-m','pip','check'],['04、运行验证/代码/run_all.py','--profile',profile],['04、运行验证/测试/test_app.py']]
        stages=d.get('stages',[])
        if d.get('status')!='passed' or len(stages)!=3 or any(s.get('returncode')!=0 or s.get('command')!=cmd for s,cmd in zip(stages,expected)):
            return dict(result,status='not_passed',reason='最新发布包验证未完整通过')
        if digest(root/ARCHIVE)!=d['archive_sha256']:
            return dict(result,status='stale',reason='当前发布包与已验证ZIP不同')
        manifest,inputs=inspect_archive(root/ARCHIVE)
        if set(manifest)!={p.relative_to(root).as_posix() for p in publication_sources(root)}:
            return dict(result,status='stale',reason='当前可发布文件集合已增加或删除，旧ZIP不能覆盖当前源码')
        if manifest!=d['source_sha256'] or any(digest(root/name)!=value for name,value in manifest.items()):
            return dict(result,status='stale',reason='当前源码或配套说明已变化')
        validate_inputs(root/'01、数据处理/原始数据/UNSW',inputs)
        if any(digest(root/name)!=value for name,value in d['uci_sha256'].items()):
            return dict(result,status='stale',reason='外部诊断输入已变化')
        if d.get('test_contract')!=2:
            return dict(result,status='not_passed',reason='旧测试证据未绑定完整测试ID清单，需要重验')
        counts=validate_inventory(d['test_inventory'],profile)
        if sorted(d['test_inventory']['expected_ids'])!=source_inventory(root):
            return dict(result,status='not_passed',reason='测试ID不等于当前全部测试源码定义')
        if counts!=d['unit_tests'] or any(manifest.get(name)!=value for name,value in d['test_inventory']['test_source_sha256'].items()):
            return dict(result,status='not_passed',reason='完整测试清单或测试源码不匹配')
        expected_files={name for name in manifest if name.startswith('04、运行验证/测试/test_') and name.endswith('.py')}
        expected_files.add('02、模型实验/补充研究/02、漏报与跨周稳定性/代码/test_stable_alerts.py')
        if set(d['test_inventory']['test_source_sha256'])!=expected_files:
            return dict(result,status='not_passed',reason='测试文件清单遗漏')
        return dict(result,status='passed',profile=profile,unit_tests=d.get('unit_tests'),archive_sha256=d['archive_sha256'],
                    validation_directory=d['validation_directory'],
                    reason='实际ZIP在项目外独立目录重建和四语测试通过；使用已有环境，不是GitHub或第三方复现')
    except (OSError,ValueError,KeyError,TypeError,BadZipFile) as exc:
        return dict(result,status='unverified',reason='无法核验发布包证据：'+str(exc))


def run(output_root, profile='extended'):
    if profile not in ('standard','extended'):
        raise ValueError('Expected standard or extended rebuild')
    output_root=Path(output_root).resolve()
    if output_root==ROOT or ROOT.is_relative_to(output_root) or output_root.is_relative_to(ROOT):
        raise ValueError('Release validation requires a separate output directory outside the source tree')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=ROOT/'04、运行验证/日志'/('release_validation_'+stamp)
    evidence.mkdir(parents=True)
    directory=output_root/stamp
    d=dict(status='running',profile=profile,scope='Actual source ZIP; same existing Python environment; no downloads or third-party claims',
           validation_directory=str(directory),python=sys.executable,python_version=sys.version,stages=[])
    def save():
        text=json.dumps(d,ensure_ascii=False,indent=2)
        (evidence/'verification.json').write_text(text,encoding='utf-8')
        if directory.is_dir():(directory/'verification.json').write_text(text,encoding='utf-8')
    save()
    try:
        archive=ROOT/ARCHIVE;manifest,inputs=inspect_archive(archive)
        raw=ROOT/'01、数据处理/原始数据/UNSW';validate_inputs(raw,inputs)
        uci=[ROOT/'01、数据处理/原始数据/UCI'/name for name in ['occupancy_detection.zip','source.html']] if profile=='extended' else []
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
        env.setdefault('UNSW_CALENDAR_DIR',str(CALENDAR_DEFAULT))  # 重建副本不在原目录树中，显式传入日历原件位置
        commands=[['-m','pip','check'],['04、运行验证/代码/run_all.py','--profile',profile],['04、运行验证/测试/test_app.py']]
        for index,command in enumerate(commands,1):
            log=directory/'logs'/f'{index:02d}.log'
            print('RUN',command,'LOG',log,flush=True)
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run([sys.executable,'-u',*command],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT)
            d['stages'].append(dict(command=command,returncode=result.returncode,log=str(log)))
            if result.returncode:raise RuntimeError(f'Stage {index} failed; see {log}')
            if index==2:
                execution=sorted((project/'04、运行验证/日志').glob('rebuild_*/execution.json'))[-1]
                inner=json.loads(execution.read_text(encoding='utf-8'))
                if inner['status']!='passed':raise ValueError('Inner rebuild incomplete')
                unit=next(s for s in inner['stages'] if s['command']==['04、运行验证/代码/run_tests.py'])
                inventory=json.loads((project/'04、运行验证/生成产物/测试清单/完整测试执行.json').read_text(encoding='utf-8'))
                counts=validate_inventory(inventory,profile)
                if counts!=unit_result((project/unit['log']).read_text(encoding='utf-8'),profile,source_inventory(project)):raise ValueError('Test log and inventory disagree')
                d.update(test_contract=2,test_inventory=inventory,unit_tests=counts,
                         rebuild_stages=len(inner['stages']))
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
    parser.add_argument('--output-root',type=Path,default=ENV_ARCHIVE/'3、发布包重建与验证存档/发布包验证')
    parser.add_argument('--profile',choices=['standard','extended'],default='extended')
    args=parser.parse_args()
    sys.exit(run(args.output_root,args.profile))
