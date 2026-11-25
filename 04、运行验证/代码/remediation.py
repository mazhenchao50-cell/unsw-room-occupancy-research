"""Hundred-item remediation ledger: original finding -> root cause -> change -> evidence.

This ledger never equates a passing test with closing every research limitation.
Human confirmations are attributed to the person providing them.
"""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'04、运行验证/生成产物/百项整改'
SOURCE=ROOT.parent/'7、项目检查报告/全面审查20261117/100项问题证据.json'
GROUPS=[(1,20,'需求与使用闭环'),(21,40,'数据来源与字段语义'),(41,60,'研究协议与推断边界'),
        (61,74,'输入契约与失败处理'),(75,80,'验收证据完整性'),(81,89,'复现与执行范围'),(90,93,'界面默认与容错'),(94,100,'文档与交付一致性')]


def read():
    path=OUT/'整改台账.json'
    return json.loads(path.read_text(encoding='utf-8'))


def save(data):
    OUT.mkdir(parents=True,exist_ok=True)
    data['updated_utc']=datetime.now(timezone.utc).isoformat()
    data['counts']={state:sum(x['state']==state for x in data['issues']) for state in sorted({x['state'] for x in data['issues']})}
    (OUT/'整改台账.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def initialize():
    if (OUT/'整改台账.json').exists():return read()
    findings=json.loads(SOURCE.read_text(encoding='utf-8'))
    assert len(findings)==100 and len({x['id'] for x in findings})==100
    issues=[]
    for finding in findings:
        n=int(finding['id'][1:])
        issues.append(dict(id=finding['id'],title=finding['title'],original_type=finding['status'],priority=finding['priority'],
            group=next(name for lo,hi,name in GROUPS if lo<=n<=hi),original_fact=finding['fact'],
            state='待处理',root_cause='',change='',verification=[],remaining='',history=[]))
    data=dict(schema=1,source=str(SOURCE.relative_to(ROOT.parent)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        rules=['前三项原始门槛不变','不以测试总数代替逐项证据','修复、边界、人工确认分别记录','旧实验属于历史，不能改为新盲测'],
        user_confirmations=[dict(date='2026-11-18',source='用户本次明确回复',
            scope='用户确认导师已明确认可限定UNSW历史数据研究；未独立取得导师书面意见',
            contribution='用户陈述当前全部任务由本人完成；计划书分工属于计划，后续细分不倒填实际贡献；使用开发工具辅助',
            review='用户陈述由团队自行复核；不是独立第三方验收')],issues=issues)
    save(data);return data


def record(ids,state,cause,change,evidence=(),remaining=''):
    data=read();wanted=set(ids)
    if wanted-{x['id'] for x in data['issues']}:raise ValueError('Unknown issue ID')
    for item in data['issues']:
        if item['id'] in wanted:
            item['history'].append({k:item[k] for k in ('state','root_cause','change','verification','remaining')})
            item.update(state=state,root_cause=cause,change=change,verification=list(evidence),remaining=remaining)
    save(data)


if __name__=='__main__':
    initialize()
    print(json.dumps(read()['counts'],ensure_ascii=False))
