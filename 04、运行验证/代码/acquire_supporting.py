"""Download optional research inputs into an explicitly chosen directory.

No default system-drive cache. Calendar originals are hash pinned; UCI source
terms are saved alongside the archive. Raw data are never put in the source ZIP.
"""
from pathlib import Path
import argparse,hashlib,json,sys,urllib.request,shutil
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import calendar_context as C
import external_uci as E


def acquire(directory):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True);records=[]
    sources=[(E.URL,'occupancy_detection.zip',None),(E.PAGE,'source.html',None)]
    sources.extend((url,name,C.SOURCE_SHA256[name]) for url,name in zip(C.SOURCES,C.SOURCE_SHA256))
    for url,name,expected in sources:
        path=directory/name
        if not path.exists():
            request=urllib.request.Request(url,headers={'User-Agent':'UNSW-Historical-Research/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response:payload=response.read(30_000_001)
            if len(payload)>30_000_000:raise ValueError('Unexpected download size: '+name)
            if expected and hashlib.sha256(payload).hexdigest()!=expected:raise ValueError('Published evidence has changed: '+name)
            path.write_bytes(payload)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected and digest!=expected:raise ValueError('Calendar hash mismatch: '+name)
        records.append(dict(file=name,url=url,sha256=digest,bytes=path.stat().st_size))
    if 'creativecommons.org/licenses/by/4.0' not in (directory/'source.html').read_text(encoding='utf-8'):
        raise ValueError('UCI licence evidence missing; inspect the saved source page')
    raw=ROOT/'01、数据处理/原始数据/UCI';raw.mkdir(parents=True,exist_ok=True)
    for name in ('occupancy_detection.zip','source.html'):
        if (directory/name).resolve()!=(raw/name).resolve():shutil.copy2(directory/name,raw/name)
    (directory/'acquisition.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Set UNSW_CALENDAR_DIR to',directory)
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--download-dir',type=Path,required=True)
    acquire(parser.parse_args().download_dir)
