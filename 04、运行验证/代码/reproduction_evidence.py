"""Bind the latest completed reproduction to the current code and raw inputs."""
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_latest(root):
    root=Path(root)
    reports=sorted((root/'04、运行验证/日志').glob('reproduction_*/verification.json'))
    if not reports:
        return {'status':'missing','reason':'没有复现记录'}
    path=reports[-1]
    result={'report':str(path.relative_to(root)),'status':'unverified'}
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        stages=data.get('stages',[])
        if data.get('status')!='passed' or len(stages)!=3 or any(s.get('returncode')!=0 for s in stages):
            return dict(result,status='not_passed',reason='最新运行未完整通过，不回退引用旧成功')
        expected=[['-m','pip','check'],['04、运行验证/代码/run_all.py'],['04、运行验证/测试/test_app.py']]
        if any(s.get('command',[])[:len(e)]!=e for s,e in zip(stages,expected)):
            return dict(result,status='unverified',reason='验证阶段与当前协议不符')
        manifest={k.replace('\\','/'):v for k,v in data.get('source_sha256',{}).items()}
        folders=['01、数据处理/代码','02、模型实验/代码','03、系统应用/代码','04、运行验证/代码','04、运行验证/测试','05、文档依赖/依赖']
        files=[p for folder in folders for p in (root/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.txt','.lock')]
        mismatches=[str(p.relative_to(root)) for p in files if manifest.get(p.relative_to(root).as_posix())!=digest(p)]
        current={p.relative_to(root).as_posix() for p in files}
        mismatches += [k for k in manifest if any(k.startswith(f+'/') for f in folders) and Path(k).suffix in ('.py','.txt','.lock') and k not in current]
        if mismatches:
            return dict(result,status='stale',reason='源码或依赖已变化',mismatches=mismatches)
        raw_manifest=path.parent/'project/01、数据处理/清洗产物/input_manifest.json'
        inputs=json.loads(raw_manifest.read_text(encoding='utf-8'))['files']
        names={f'{y}_sem2_attendance_data.csv' for y in (2017,2018)}|{f'week{w}_computed_data.csv' for w in range(1,13)}
        if len(inputs)!=14 or {x['file'] for x in inputs}!=names:
            raise ValueError('原始输入清单不完整')
        for item in inputs:
            p=root/'01、数据处理/原始数据/UNSW'/item['file']
            if digest(p)!=item['sha256']:
                return dict(result,status='stale',reason='原始输入已变化')
        if data.get('profile')=='extended':
            for name in ('occupancy_detection.zip','source.html'):
                rel='01、数据处理/原始数据/UCI/'+name
                if digest(root/rel)!=digest(path.parent/'project'/rel):
                    return dict(result,status='stale',reason='UCI来源文件已变化')
        return dict(result,status='passed',profile=data.get('profile'),reason='最新完整复现与当前源码 依赖 原始输入一致；不代表重新安装环境')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return dict(result,status='unverified',reason='证据无法核验: '+str(exc))
