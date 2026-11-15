"""Create an evidence-based acceptance snapshot from existing reports."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from reproduction_evidence import inspect_latest
from verify_release import inspect_latest as inspect_release

ROOT=Path(__file__).resolve().parents[2]
INPUTS={
    'model':'02、模型实验/生成产物/revised/report.json',
    'shap':'02、模型实验/生成产物/revised/shap_report.json',
    'functional':'02、模型实验/生成产物/system/functional_report.json',
    'label':'02、模型实验/生成产物/label_audit/report.json',
    'usability':'02、模型实验/生成产物/usability/summary.json',
}

def alert_review(metrics):
    tn, fp, fn, tp = metrics['confusion_tn_fp_fn_tp']
    total = tn + fp + fn + tp
    return {
        'sessions': total,
        'alerts': tp + fp,
        'correct_alerts': tp,
        'false_alerts': fp,
        'missed_low_use': fn,
        'actual_low_use': tp + fn,
        'prevalence': (tp + fn) / total,
        'precision': metrics['precision'],
        'recall': metrics['recall'],
    }


def build():
    sources={key:ROOT/path for key,path in INPUTS.items()}
    evidence={key:json.loads(path.read_text(encoding='utf-8')) for key,path in sources.items() if path.is_file()}
    model=evidence['model'];functional=evidence['functional']
    low=model['time']['LightGBM']['low_utilization']
    acceptance=model['acceptance']
    reproduction=inspect_latest(ROOT)
    release_validation=inspect_release(ROOT)
    items=[
        {'criterion':'① 相比两个简单基线RMSE改善≥10%','status':'达数值门槛' if acceptance['regression_10pct_both_simple_baselines'] else '未达数值门槛',
         'evidence':f"第12周LightGBM RMSE {model['time']['LightGBM']['rmse']:.4f}；相对静态课表和历史均值改善 {acceptance['baseline_relative_improvements']['timetable_static']:.1%}、{acceptance['baseline_relative_improvements']['historical_mean']:.1%}。同周RF RMSE {model['time']['RF']['rmse']:.4f}更低。"},
        {'criterion':'② 低利用率F1≥0.60或Precision≥0.65','status':'达数值门槛' if acceptance['low_utilization_F1_060_or_precision_065'] else '未达数值门槛',
         'evidence':f"当前主模型第12周F1 {low['f1']:.4f}，Precision {low['precision']:.4f}；离线候选不能计入默认模型。"},
        {'criterion':'③ 留一教室宏RMSE≤0.18或与随机切分差距≤30%','status':'达数值门槛' if acceptance['loro_macro_018_or_gap_030'] else '未达数值门槛',
         'evidence':f"主模型9间教室宏RMSE {model['loro']['macro_rmse']:.4f}；此为未见教室诊断，不能用有目标教室历史的实验替代。"},
        {'criterion':'④ 系统流程、解释、信号意义与复现','status':'部分完成，不能整体通过',
         'evidence':f"自动查询{functional['passed']}/{functional['queries']}；SHAP报告{'存在' if 'shap' in evidence else '缺失'}；当前代码与输入复现{reproduction.get('status','未核验')}。原文No-show指低于10%的利用率，实际含义已纠正；GitHub端复现尚未核验。额外零峰值实验不是原定必过门槛。"},
    ]
    if 'shap' not in evidence or functional['passed']!=functional['queries'] or reproduction.get('status')!='passed':
        items[3]['status']='证据不齐，不能通过'
    reviewed=alert_review(low)
    alert_check={
        'requirement':'No-show检测意义',
        'status':'历史人工复核用途有量化证据',
        'evidence':f"第12周低利用率（峰值占用率低于10%）有{reviewed['actual_low_use']}/{reviewed['sessions']}条，基率{reviewed['prevalence']:.1%}。默认回归阈值提示{reviewed['alerts']}条，命中{reviewed['correct_alerts']}条，误报{reviewed['false_alerts']}条，漏报{reviewed['missed_low_use']}条。可用于安排课后容量复核顺序，现场可用性须另查。",
    }
    shap_rows={row['feature']:row for row in evidence.get('shap',{}).get('ranking',[])}
    shap_detail='当前缺少可核对的SHAP特征排行。'
    if all(key in shap_rows for key in ['course_hist_mean','course_hist_n','doors']):
        history=shap_rows['course_hist_mean']
        history_count=shap_rows['course_hist_n']
        shap_detail=(f"第12周{evidence['shap']['n']}条回归解释中，课程历史均值占平均绝对SHAP总量{history['share']:.1%}，方向与持续利用需求相符。"
                     f"历史样本数虽占{history_count['share']:.1%}，Spearman仅{history_count['spearman']:.3f}。门数可能代理教室身份，需审阅。解释范围为已知教室占用率回归。")
    items[3]['subchecks']=[
        {'requirement':'Streamlit输入输出流程','status':'已自动验证' if functional['passed']==functional['queries'] and reproduction.get('status')=='passed' else '待验证',
         'evidence':f"{functional['passed']}/{functional['queries']}查询；四语交互见完整复现第三阶段。"},
        {'requirement':'SHAP符合领域常识','status':'有计算证据，解释需审阅' if shap_rows else '缺少证据',
         'evidence':shap_detail},
        alert_check,
        {'requirement':'GitHub代码按README复现','status':'本机复现通过，GitHub端未验证' if reproduction.get('status')=='passed' else '当前复现待验证',
         'evidence':'本机安装与隔离重建有记录；尚无已核验的GitHub发布及第三方复现证据。'},
    ]
    out={'generated_at_seoul':datetime.now(timezone(timedelta(hours=9))).isoformat(),'basis':'Original submitted numeric criteria; retrospective evidence only.',
         'reproduction':reproduction,'report_scope':'指标来自当前保存的历史实验报告；复现状态单独核对当前代码和输入，不等于现场验证或新环境安装。','items':items,'human_trials':evidence.get('usability',{}).get('participants',0),
         'limitations':['Sensor-derived zero peak does not establish cancellation or student no-show.',
                        'Repeatedly examined test weeks cannot be presented as a new blind test.',
                        'Timetable gaps do not establish actual availability or access permission.'],
         'source_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources.values() if path.is_file()}}
    out['low_use_review']={'week':12,'label':'peak occupancy ratio < 0.1','default':reviewed,
        'intended_use':'Prioritize historical capacity reviews by staff; verify with course and facilities records.'}
    out['release_validation']=release_validation
    if release_validation['status']=='passed':
        items[3]['subchecks'][-1].update(status='本机源码与实际发布包重建通过，GitHub端未验证',
            evidence='实际源码ZIP已在D盘全新目录由原始数据重建，并通过四语界面检查；沿用已有Python环境，未完成GitHub发布、新机器安装或第三方复现。')
    if release_validation.get('report'):
        path=ROOT/release_validation['report']
        out['source_sha256'][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    candidate=ROOT/'02、模型实验/生成产物/improvement_v8/report.json'
    if candidate.is_file():
        cold=json.loads(candidate.read_text(encoding='utf-8'))
        current=all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in cold['sha256'].items())
        out['candidate_evidence']=[dict(criterion='③',method='v8 history-free nested spatial selection',
            evidence_current=current,macro_rmse=cold['macro_rmse'],gap_vs_random=cold['gap_vs_random'],
            numeric_gate=bool(current and cold['original_spatial_numeric_gate']),default_model_changed=False,
            scope='候选在历史九间教室达到数值门槛，不覆盖现用模型；独立新教室和前瞻时间未验证。',
            conditional_course_bootstrap=cold.get('conditional_course_bootstrap'))]
        out['source_sha256'][str(candidate.relative_to(ROOT))]=hashlib.sha256(candidate.read_bytes()).hexdigest()
    unified=ROOT/'02、模型实验/生成产物/unified/report.json'
    if unified.is_file():
        routed=json.loads(unified.read_text(encoding='utf-8'))
        current=all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in routed['sha256'].items())
        out['integrated_research_evidence']=dict(evidence_current=current,original_numeric_gates=routed['original_numeric_gates'],
            week12=routed['rolling']['12'],spatial=routed['spatial_summary'],forward_cold=routed['forward_cold_summary'],
            robustness_summary=routed.get('robustness_summary'),pooled_low=routed.get('pooled_low'),
            all_three_numeric=bool(current and all(routed['original_numeric_gates'].values())),default_model_changed=False,
            scope='界面显式选择的分场景研究方案；三项数值门槛仅按第12周及九间历史教室的点估计计算。四周合并的低利用率精确率另列且未过门槛；不代表④全部完成或独立新校园验证。')
        out['source_sha256'][str(unified.relative_to(ROOT))]=hashlib.sha256(unified.read_bytes()).hexdigest()
        if current:
            routed_review=alert_review(routed['rolling']['12']['low'])
            out['low_use_review']['unified']=routed_review
            alert_check['evidence']+=(
                f"统一研究模式提示{routed_review['alerts']}条，命中{routed_review['correct_alerts']}条，"
                f"误报{routed_review['false_alerts']}条，漏报{routed_review['missed_low_use']}条。"
                f"适合优先核对少量提示，仍须抽查未提示的课程。")
    risk=ROOT/'02、模型实验/生成产物/risk_review/report.json'
    if risk.is_file():
        review=json.loads(risk.read_text(encoding='utf-8'))
        current=all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in review['sha256'].items())
        out['risk_review']=dict(evidence_current=current,n=review['n'],adoption=review['adoption'],
            report=str(risk.relative_to(ROOT)),scope=review['protocol']['scope'],unsupported_uses=review['unsupported_uses'])
        out['source_sha256'][str(risk.relative_to(ROOT))]=hashlib.sha256(risk.read_bytes()).hexdigest()
    target=ROOT/'02、模型实验/生成产物/acceptance';target.mkdir(parents=True,exist_ok=True)
    benchmark=ROOT/'02、模型实验/生成产物/forward_cold_benchmark/report.json'
    if benchmark.is_file():
        diagnostic=json.loads(benchmark.read_text(encoding='utf-8'))
        current=bool(diagnostic.get('sha256')) and all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in diagnostic['sha256'].items())
        out['forward_cold_benchmark']=dict(evidence_current=current,report=str(benchmark.relative_to(ROOT)),
            n=diagnostic['common_sessions'],outer_folds=diagnostic['outer_folds'],primary_comparison=diagnostic['primary_comparison'],
            adoption=diagnostic['adoption'],scope='四周前推与留教室同时限制的回顾研究；不替换原验收、默认模型或统一研究模式，不代表已证明创新。')
        out['source_sha256'][str(benchmark.relative_to(ROOT))]=hashlib.sha256(benchmark.read_bytes()).hexdigest()
    lines=['# 项目验收证据快照','','按已提交数值门槛与当前默认系统生成；不是导师或校方验收结论。','']
    for item in items:
        lines.extend([f"## {item['criterion']} — {item['status']}",'',item['evidence'],''])
        for check in item.get('subchecks',[]):
            lines.extend([f"- {check['requirement']}：{check['status']}。{check['evidence']}"])
        if item.get('subchecks'):lines.append('')
    for candidate in out.get('candidate_evidence',[]):
        lines.extend(['## 第③项独立候选进展','',f"v8宏RMSE {candidate['macro_rmse']:.4f}，同方法随机切分差距 {candidate['gap_vs_random']:.1%}；来源一致：{candidate['evidence_current']}；原数值门槛：{candidate['numeric_gate']}。{candidate['scope']}",''])
    if 'integrated_research_evidence' in out:
        r=out['integrated_research_evidence']
        lines.extend(['## 分场景研究方案统一验证','',f"前三项历史数值门槛：{r['all_three_numeric']}；来源一致：{r['evidence_current']}。{r['scope']}",''])
    if 'risk_review' in out:
        r=out['risk_review']
        lines.extend(['## 固定方案风险复核','',f"{r['n']}条共同会话，来源一致：{r['evidence_current']}。未自动替换默认或统一研究模式；详见 {r['report']}。仅评价历史已见教室，不能继承新教室表现。",''])
    if 'forward_cold_benchmark' in out:
        diagnostic=out['forward_cold_benchmark'];primary=diagnostic['primary_comparison']
        lines.extend(['## 严格前推与新教室对照','',
            f"{diagnostic['n']}条共同会话、{diagnostic['outer_folds']}折，来源一致：{diagnostic['evidence_current']}。容量加权宏RMSE {primary['candidate_macro_rmse']:.4f}，内层选定强基线 {primary['baseline_macro_rmse']:.4f}，相对改善 {primary['relative_improvement']:.1%}。{diagnostic['scope']}",''])
    journey=ROOT/'02、模型实验/生成产物/system/multilingual_checks.json'
    if journey.is_file():
        checks=json.loads(journey.read_text(encoding='utf-8'))
        current=bool(checks.get('sha256')) and all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in checks['sha256'].items())
        ready=all(checks.get(k)=='passed' for k in ['missing_setup_four_languages','data_only_query_four_languages','later_time_action_four_languages'])
        out['user_journey']=dict(evidence_current=current,automated_scenarios_passed=bool(current and ready),
            report=str(journey.relative_to(ROOT)),human_trials=out['human_trials'],
            scope='四语需求输入、候选选择与核查单、缺少模型的基础查询、保持条件的稍晚时段建议；自动检查不等于真人易用性验证。')
        out['source_sha256'][str(journey.relative_to(ROOT))]=hashlib.sha256(journey.read_bytes()).hexdigest()
        lines.extend(['## 用户操作流程','',f"四语场景检查通过：{out['user_journey']['automated_scenarios_passed']}；来源一致：{current}；真人参与数：{out['human_trials']}。{out['user_journey']['scope']}",''])
    lines.extend(['## 实际发布包重建','',f"状态：{release_validation['status']}。{release_validation['reason']}",''])
    lines.extend(['## 仍需外部证据','',*[f'- {x}' for x in out['limitations']],'',
                  '来源及哈希见 `02、模型实验/生成产物/acceptance/status.json`。'])
    (target/'status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return out

if __name__=='__main__':
    print([(item['criterion'][0],item['status']) for item in build()['items']])
