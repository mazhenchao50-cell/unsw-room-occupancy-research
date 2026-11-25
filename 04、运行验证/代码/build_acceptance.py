"""One current-model acceptance summary; history belongs in the whitepapers."""
from datetime import datetime,timezone
import json
from pathlib import Path
from numeric_acceptance import build as build_numeric
from verify_release import inspect_latest
ROOT=Path(__file__).resolve().parents[2]


def alert_review(metrics):
    tn,fp,fn,tp=metrics['confusion_tn_fp_fn_tp']
    return dict(sessions=tn+fp+fn+tp,alerts=tp+fp,correct_alerts=tp,false_alerts=fp,
                missed_low_use=fn,actual_low_use=tp+fn,precision=metrics['precision'],recall=metrics['recall'],f1=metrics['f1'])


def build():
    numeric=build_numeric(ROOT);release=inspect_latest(ROOT)
    field_evidence=json.loads((ROOT/'05、文档依赖/依赖/unsw_field_evidence.json').read_text(encoding='utf-8'))
    items=[dict(item) for item in numeric.get('items',[])]
    if not items:
        items=[dict(criterion=str(i),status='待验证',evidence=numeric.get('reason','缺少正式结果')) for i in range(1,4)]
    items.append(dict(criterion='④ 系统流程、解释、信号意义与GitHub复现',status='后续处理',evidence='本轮验收范围为原定前三项与完整代码检查。'))
    out=dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),default_mode=numeric['default_mode'],
             items=items,numeric_acceptance=numeric,release_validation=release,
             low_use_review=dict(week=12,label='peak occupancy ratio < 0.1',
                                 default=alert_review(numeric['low']) if numeric['status']=='passed' else None),
             cross_week=numeric.get('cross_week'),data_interpretation=field_evidence,
             scope='UNSW 2017历史数据；第12周与九教室原定验收，四周稳定性单列。')
    lines=['# 当前正式方案验收','','此文件由当前模型及逐样本预测重算生成。历史实验及弃用原因见两本正式白皮书。','']
    for item in items:lines.extend([f"## {item['criterion']}：{item['status']}",'',item['evidence'],''])
    if numeric['status']=='passed':
        lines.extend(['## 跨周检查','','|周次|精确率|召回率|F1|误报|漏报|','|---|---:|---:|---:|---:|---:|'])
        rows=list(numeric['cross_week']['weekly'].items())+[('合计',numeric['cross_week']['pooled'])]
        for week,m in rows:
            _,fp,fn,_=m['confusion_tn_fp_fn_tp']
            lines.append(f"|{week}|{m['precision']:.2%}|{m['recall']:.2%}|{m['f1']:.4f}|{fp}|{fn}|")
        lines.extend(['','分类器固定阈值0.50；公共假日另作复核提示，模型概率保持原值。全部815条评估记录保留。',''])
    lines.extend(['## 数据字段依据','',field_evidence['summary'],'',
                  '依据及原文哈希：05、文档依赖/依赖/unsw_field_evidence.json；字段来源解释不改变前三项数值门槛。','',
                  '## 完整运行检查','',f"{release['status']}：{release['reason']}",'',
                  '逐样本、阈值和来源核对见numeric_status.json；完整运行状态绑定实际源码ZIP。'])
    target=ROOT/'02、模型实验/生成产物/acceptance';target.mkdir(parents=True,exist_ok=True)
    (target/'status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return out


if __name__=='__main__':print([(x['criterion'][0],x['status']) for x in build()['items']])
