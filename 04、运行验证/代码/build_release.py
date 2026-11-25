"""Build a source-only publication candidate, excluding data and environments."""
from pathlib import Path
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED
from verify_release import DOCS, inspect_archive,publication_sources

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'04、运行验证/生成产物/发布准备'
README=(ROOT/'05、文档依赖/文档/README.md').read_text(encoding='utf-8')


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    paths=publication_sources(ROOT)
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    inputs=json.loads((ROOT/'01、数据处理/清洗产物/input_manifest.json').read_text(encoding='utf-8'))
    data=[{'file':r['file'],'sha256':r['sha256']} for r in inputs['files']]
    target=OUT/'项目源码发布准备.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('README.md',README)
        z.writestr('source_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr('data_requirements.json',json.dumps(data,ensure_ascii=False,indent=2))
    with ZipFile(target) as z:
        assert z.testzip() is None
        assert not any('/原始数据/' in n or '.venv' in n or '/日志/' in n or n.endswith(('.csv','.joblib')) for n in z.namelist())
        for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        count=len(z.namelist())
    inspect_archive(target)
    report=dict(status='prepared_not_published',archive=target.name,entries=count,source_files=len(paths),data_included=False,
        dataset_identity='The 14 required UNSW CSVs were matched byte-for-byte with the official data.zip downloaded on 2026-11-11; per-file SHA256 requirements are included in the archive.',
        redistribution_license='unverified; raw data intentionally excluded from this source package',
        archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),checks=['CRC','every source hash','no data/models/env/logs'],
        outstanding=['Publication and verification of this updated source snapshot','UNSW acquisition/redistribution terms','Third-party rebuild with authorized data'])
    (OUT/'发布核对.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return report


if __name__=='__main__':build()
