"""Read-only source/data audit. Reports are evidence, not a proof of no bugs."""
import ast
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'04、运行验证/生成产物/百项整改/源文件审查'
SOURCE_DIRS=['01、数据处理/代码','02、模型实验/代码','03、系统应用/代码',
             '04、运行验证/代码','04、运行验证/测试','05、文档依赖/代码',
             '02、模型实验/补充研究']


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def source_inventory():
    paths=sorted({p for folder in SOURCE_DIRS for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts})
    modules={}
    for p in paths:modules.setdefault(p.stem,[]).append(p.relative_to(ROOT).as_posix())
    rows=[]
    for p in paths:
        text=p.read_text(encoding='utf-8-sig');tree=ast.parse(text,filename=str(p));compile(tree,str(p),'exec')
        imports=[];edges=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):
                imports.append(node.module or '')
                if node.module=='models':imports.extend(a.name for a in node.names)
        for name in sorted(set(imports)):
            edges.extend(modules.get(name.rsplit('.',1)[-1],[]))
        functions=[dict(name=n.name,line=n.lineno,end_line=n.end_lineno,kind=type(n).__name__,
                        purpose=ast.get_docstring(n) or '') for n in ast.walk(tree)
                   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
        refs=sorted({n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)
                     and len(n.value)<240 and any(ext in n.value for ext in ('.csv','.json','.joblib','.docx','.md','.zip'))})
        top_calls=[dict(line=n.lineno,expression=ast.get_source_segment(text,n)[:180]) for n in tree.body
                   if isinstance(n,(ast.Assign,ast.AnnAssign,ast.Expr)) and any(isinstance(x,ast.Call) for x in ast.walk(n))]
        rows.append(dict(file=p.relative_to(ROOT).as_posix(),sha256=sha(p),lines=len(text.splitlines()),
            purpose=ast.get_docstring(tree) or '',imports=sorted(set(imports)),local_dependencies=sorted(set(edges)),
            functions=functions,literal_file_references=refs,module_level_calls=top_calls,
            coverage='AST syntax and dependency inventory; functional execution coverage is reported separately'))
    save('代码逐文件核对.json',rows)
    return rows


def provenance(require_archive=True):
    archive=ROOT/'04、运行验证/日志/unsw_source_20261111/data.zip'
    raw=ROOT/'01、数据处理/原始数据/UNSW'
    names={f'{y}_sem2_attendance_data.csv' for y in (2017,2018)}|{f'week{w}_computed_data.csv' for w in range(1,13)}
    manifest=json.loads((ROOT/'01、数据处理/清洗产物/input_manifest.json').read_text(encoding='utf-8'))
    recorded={x['file']:x['sha256'] for x in manifest['files']}
    if len(recorded)!=14 or set(recorded)!=names or {p.name for p in raw.glob('*.csv')}!=names:
        raise ValueError('Raw CSV membership differs from the original fourteen')
    pinned=json.loads((ROOT/'05、文档依赖/依赖/unsw_input_hashes.json').read_text(encoding='utf-8'))
    expected={row['file']:row['sha256'] for row in pinned['files']}
    if expected!=recorded or any(sha(raw/name)!=expected[name] for name in names):
        raise ValueError('Raw identity differs from separately pinned official file hashes')
    if not require_archive:
        rows=[]
        for name in sorted(names):
            d=pd.read_csv(raw/name)
            rows.append(dict(file=name,bytes=(raw/name).stat().st_size,sha256=sha(raw/name),rows=len(d),columns=list(d),byte_identical=True))
        result=dict(checked_at=datetime.now(timezone.utc).isoformat(),files=rows,matched=14,source=pinned['url'],
            pinned_archive_sha256=pinned['archive_sha256'],archive_read_this_run=False,
            identity_scope='All current raw files rehashed against the separately pinned official identity; no archived ZIP read in this runtime mode.')
        save('原始数据重新核实.json',result);return result
    with ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Official archive CRC failed')
        members=[n for n in z.namelist() if n.endswith('.csv')]
        if len(members)!=14 or {Path(n).name for n in members}!=names:raise ValueError('Unexpected archive CSVs')
        rows=[]
        for member in members:
            name=Path(member).name;data=z.read(member);digest=hashlib.sha256(data).hexdigest()
            if not digest==sha(raw/name)==recorded[name]:raise ValueError('Dataset identity changed: '+name)
            d=pd.read_csv(raw/name)
            rows.append(dict(file=name,bytes=len(data),sha256=digest,rows=len(d),columns=list(d.columns),archive_member=member,byte_identical=True))
    result=dict(checked_at=datetime.now(timezone.utc).isoformat(),archive=str(archive.relative_to(ROOT)),
        archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,files=rows,matched=14,
        source='https://smartcampus.unsw.edu.au/roomoccupancy/data.zip',
        identity_scope='Rehashed archived official download against every current raw input and current cleaning manifest; no new download.',
        limit='Byte identity verifies provenance continuity, not sensor accuracy or data redistribution permission.')
    save('原始数据重新核实.json',result)
    return result


def labels():
    d=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv')
    c=pd.read_csv(ROOT/'01、数据处理/清洗产物/clean_computed.csv')
    peak=c[c.course_id.notna()].groupby(['date','room_code','course_id']).num_attendees.max()
    peak.index.names=['date','room','course_id']
    merged=d.merge(peak.rename('recomputed_peak'),on=['date','room','course_id'],validate='one_to_one')
    np.testing.assert_allclose(merged.attendees,merged.recomputed_peak,atol=0,rtol=0,equal_nan=True)
    np.testing.assert_allclose(d.occupancy_rate,d.attendees/d.seats,atol=1e-12,rtol=0,equal_nan=True)
    if len(merged)!=len(d) or not d.session_id.is_unique:raise ValueError('Session membership changed')
    result=dict(sessions=len(d),model_sessions=int((d.occupancy_rate.notna()&d.week.ne(9)).sum()),
        missing_label=int(d.occupancy_rate.isna().sum()),week9=int(d.week.eq(9).sum()),
        rooms=int(d.room.nunique()),label_rounding_changes=int(((d.attendees/d.seats<.1)!=(d.occupancy_rate<.1)).sum()),
        peaks_recomputed=True,labels_recomputed=True,
        clean_sha256={p.name:sha(p) for p in (ROOT/'01、数据处理/清洗产物').glob('*.csv')})
    save('标签与样本核对.json',result)
    return result


def workspace_inventory():
    """Every project file is indexed; caches and historical snapshots are labelled."""
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    for p in sorted(ROOT.parent.rglob('*')):
        if not p.is_file() or any(s in ('.git','.venv','.venv-repro') for s in p.parts):continue
        rel=p.relative_to(ROOT.parent).as_posix()
        if p.is_relative_to(OUT):continue  # Self-generating evidence has its own directory.
        if '__pycache__' in p.parts:kind='可重建缓存'
        elif '/日志/' in rel:kind='历史运行证据或冻结副本'
        elif '/原始数据/' in rel or rel.startswith('5、'):kind='数据原件或入口说明'
        elif '/生成产物/' in rel or '/清洗产物/' in rel:kind='可重建产物'
        elif p.suffix=='.py':kind='源代码'
        else:kind='文档依赖或历史提交材料'
        rows.append(dict(path=rel,bytes=p.stat().st_size,category=kind))
    with (OUT/'全项目文件目录.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['path','bytes','category']);writer.writeheader();writer.writerows(rows)
    return len(rows)


def run(runtime=False):
    source=source_inventory();origin=provenance(require_archive=not runtime);data=labels()
    count=None if runtime else workspace_inventory()
    result=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_files=len(source),
        source_lines=sum(x['lines'] for x in source),functions_and_classes=sum(len(x['functions']) for x in source),
        workspace_files=count,raw_files=origin['matched'],data=data,
        limitations=['Static inventory does not establish that each possible execution path is correct.',
                    'Historical snapshot copies are indexed, not re-executed as active code.',
                    'Legacy experiments cannot be promoted by selecting their outer-test score.',
                    'The original three point-estimate gates are not independent future validation.'])
    save('审计范围.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',action='store_true',help='Audit current sources, labels and pinned raw identity without requiring local historical ZIP/logs')
    run(parser.parse_args().runtime)
