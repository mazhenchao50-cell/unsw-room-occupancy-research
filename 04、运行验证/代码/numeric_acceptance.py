"""Recompute the three original gates for the model actually selected by default.

No threshold search, new model selection or pooled-week substitution occurs here.
This is a retrospective numeric check, not external approval or a novelty claim.
"""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import joblib

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'02、模型实验/代码'))
sys.path.insert(0, str(ROOT/'03、系统应用/代码'))
from models import unified as U
from serving_policy import DEFAULT_MODE, POLICY_VERSION
from verify_release import validate_inputs, RAW_NAMES


def gates(gains, low, macro, random_rmse):
    values = [*gains.values(), low['f1'], low['precision'], macro, random_rmse]
    if not np.isfinite(values).all() or random_rmse <= 0:
        raise ValueError('Non-finite metric or invalid random comparator')
    if set(gains) != {'timetable_static', 'historical_mean'}:
        raise ValueError('Both original baselines are required')
    return dict(regression=all(v >= .10 for v in gains.values()),
                low=low['f1'] >= .60 or low['precision'] >= .65,
                spatial=macro <= .18 or macro/random_rmse-1 <= .30)


def align_predictions(frame, expected):
    if not frame.session_id.is_unique or set(frame.session_id) != set(expected.session_id):
        raise ValueError('Missing, duplicate or substituted evaluation sessions')
    merged = expected[['session_id', 'room', 'week', 'occupancy_rate']].merge(
        frame, on='session_id', suffixes=('_source', ''), validate='one_to_one')
    for key in ['room', 'week']:
        if not merged[key].equals(merged[key+'_source']):
            raise ValueError('Evaluation metadata changed: '+key)
    np.testing.assert_allclose(merged.occupancy_rate, merged.occupancy_rate_source, rtol=0, atol=1e-12)
    if not np.isfinite(merged.prediction).all() or (merged.prediction < 0).any():
        raise ValueError('Non-finite or negative predictions')
    return merged


def random_reference(data):
    """Recreate the registered split; never let the saved CSV choose its own rows."""
    _, indices = train_test_split(np.arange(len(data)), test_size=.2, random_state=42)
    return data.iloc[indices]


def compare_served(saved, served):
    actual=served.set_index('session_id').loc[saved.session_id]
    for column in ('prediction','low_probability','context_probability','regression_prediction','state_prediction','held_prediction'):
        np.testing.assert_allclose(saved[column],actual[column],rtol=0,atol=1e-12,equal_nan=True,
                                   err_msg='Saved predictions differ from model inference: '+column)
    for column in ('prediction_route','model_alert','context_alert','calendar_review','low_alert'):
        np.testing.assert_array_equal(saved[column],actual[column],err_msg='Saved flag differs: '+column)


def verify_clean_chain(root):
    """Rebuild labels from the verified raw inputs; do not trust clean-table hashes alone."""
    parent=root/'04、运行验证/生成产物/百项整改';parent.mkdir(parents=True,exist_ok=True)
    outputs=('sessions.csv','attendance_clean.csv','clean_computed.csv')
    with tempfile.TemporaryDirectory(prefix='raw_chain_',dir=parent) as folder:
        result=subprocess.run([sys.executable,str(root/'01、数据处理/代码/pipeline_clean.py'),
            '--data-dir',str(root/'01、数据处理/原始数据/UNSW'),'--out-dir',folder],
            cwd=root,capture_output=True,text=True,encoding='utf-8')
        if result.returncode:raise ValueError('Raw-to-clean reconstruction failed: '+result.stderr[-2000:])
        for name in outputs:
            if hashlib.sha256((Path(folder)/name).read_bytes()).digest()!=hashlib.sha256((root/'01、数据处理/清洗产物'/name).read_bytes()).digest():
                raise ValueError('Raw-to-clean lineage mismatch: '+name)
    return dict(status='passed',outputs=list(outputs),method='fresh subprocess from all 14 hash-verified raw CSVs')


def stability_checks(weekly,pooled):
    return dict(low_use_pooled_gate=bool(pooled['f1']>=.6 or pooled['precision']>=.65),
        low_use_week12_point_gate=bool(weekly['12']['f1']>=.6 or weekly['12']['precision']>=.65),
        weeks=[8,10,11,12],
        every_week_original_low_gate=all(x['f1']>=.6 or x['precision']>=.65 for x in weekly.values()),
        every_week_recall_at_least_050=all(x['recall']>=.5 for x in weekly.values()),
        pooled_precision_at_least_065=pooled['precision']>=.65,pooled_recall_at_least_060=pooled['recall']>=.6,
        week12_misses_at_most_25=weekly['12']['confusion_tn_fp_fn_tp'][2]<=25)


def assess(root=ROOT):
    root = Path(root)
    if DEFAULT_MODE != 'unified':
        raise ValueError('The evaluated model is not the default serving policy')
    out = root/'02、模型实验/生成产物/unified'
    bundle, report = U.load_verified(root)
    data = U.R.load(root/'01、数据处理/清洗产物/sessions.csv')
    manifest_path = root/'01、数据处理/清洗产物/input_manifest.json'
    inputs = json.loads(manifest_path.read_text(encoding='utf-8'))['files']
    pinned=json.loads((root/'05、文档依赖/依赖/unsw_input_hashes.json').read_text(encoding='utf-8'))['files']
    if {x['file']:x['sha256'] for x in inputs}!={x['file']:x['sha256'] for x in pinned}:
        raise ValueError('Inputs do not match the independently pinned official archive')
    if len(inputs) != 14 or {x['file'] for x in inputs} != RAW_NAMES:
        raise ValueError('The fourteen original UNSW inputs are required')
    validate_inputs(root/'01、数据处理/原始数据/UNSW', inputs)
    clean_chain=verify_clean_chain(root)
    query = data[data.week.eq(12)]
    time = pd.read_csv(out/'time_predictions.csv')
    rolling = align_predictions(time, data[data.week.isin([8,10,11,12])])
    source_dates=data.set_index('session_id').loc[rolling.session_id,'date']
    np.testing.assert_array_equal(pd.to_datetime(rolling.date).to_numpy(),source_dates.to_numpy())
    if any(not np.isfinite(rolling[name]).all() or not rolling[name].between(0,1).all() for name in ('low_probability','context_probability')):
        raise ValueError('Invalid low-use probability')
    for name in ['model_alert','context_alert','calendar_review','low_alert']:
        if rolling[name].dtype!=bool:raise ValueError('Boolean alert required: '+name)
    np.testing.assert_array_equal(rolling.model_alert,rolling.low_probability.ge(U.LOW.THRESHOLD))
    np.testing.assert_array_equal(rolling.context_alert,rolling.context_probability.ge(U.CONTEXT.THRESHOLD))
    np.testing.assert_array_equal(rolling.calendar_review,U.CALENDAR.review_flag(rolling))
    np.testing.assert_array_equal(rolling.low_alert,rolling.model_alert|rolling.context_alert|rolling.calendar_review)
    weekly={str(int(w)):U.R.binary_metrics(g.occupancy_rate.lt(.1),g.low_alert) for w,g in rolling.groupby('week')}
    for week,metrics in weekly.items():
        if metrics!=report['rolling'][week]['low']:raise ValueError('Weekly low-use report mismatch')
    pooled=U.R.binary_metrics(rolling.occupancy_rate.lt(.1),rolling.low_alert)
    if pooled!=report['pooled_low']:raise ValueError('Pooled low-use report mismatch')
    checks=stability_checks(weekly,pooled)
    old_flags=rolling.model_alert|rolling.calendar_review
    before=U.R.binary_metrics(rolling.occupancy_rate.lt(.1),old_flags)
    base_weekly={str(int(w)):U.R.binary_metrics(g.occupancy_rate.lt(.1),g.model_alert|g.calendar_review) for w,g in rolling.groupby('week')}
    cost=lambda m:3*m['confusion_tn_fp_fn_tp'][2]+m['confusion_tn_fp_fn_tp'][1]
    context_checks=dict(every_week_f1_065=all(m['f1']>=.65 for m in weekly.values()),
        every_week_recall_065=all(m['recall']>=.65 for m in weekly.values()),pooled_precision_065=pooled['precision']>=.65,
        no_week_miss_increase=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=base_weekly[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),
        total_misses_reduced=pooled['confusion_tn_fp_fn_tp'][2]<before['confusion_tn_fp_fn_tp'][2],
        stated_cost_reduced=cost(pooled)<cost(before))
    added=rolling.low_alert&~old_flags
    context_adoption=dict(checks=context_checks,baseline=before,current=pooled,
        added_reviews=int(added.sum()),added_true_low=int((added&rolling.occupancy_rate.lt(.1)).sum()),
        added_false_alert=int((added&rolling.occupancy_rate.ge(.1)).sum()),
        old_cost=cost(before),new_cost=cost(pooled),cost_assumption='3*FN+FP; stated research assumption, not measured campus cost')
    if not all(context_checks.values()):raise ValueError('Formal model does not meet its separately declared context adoption checks')
    if any(report['robustness_summary'].get(k)!=v for k,v in checks.items()):
        raise ValueError('Cross-week stability checks do not match recomputed metrics')
    for week,rows in rolling.groupby('week'):
        fold=joblib.load(out/f'fold_models/rolling_{int(week)}.joblib')
        expected=data[data.week.eq(week)]
        if set(fold['low']['reference'].session_id)!=set(data[data.week.lt(week)].session_id):
            raise ValueError('Unexpected rolling fitting cohort')
        if set(fold['context']['reference'].session_id)!=set(data[data.week.lt(week)].session_id):
            raise ValueError('Unexpected context fitting cohort')
        compare_served(rows,U.predict_bundle(fold,expected))
    aligned = align_predictions(time[time.week.eq(12)], query)
    served = U.predict_bundle(bundle, query).set_index('session_id').loc[aligned.session_id]
    compare_served(aligned,served.reset_index())
    if set(aligned.prediction_route) != {'known'}:
        raise ValueError('Week 12 must use the fitted known-room branch')
    # Equal information: the baselines see the same weeks as the classifiers inside the two-part prediction.
    base = U.R.baselines(bundle['low']['reference'], query)
    rmse = U.R.metrics(aligned.occupancy_rate, aligned.prediction)['rmse']
    base_rmse = {k: U.R.metrics(query.occupancy_rate, base[k])['rmse']
                 for k in ['timetable_static', 'historical_mean']}
    gains = {k: 1-rmse/value for k, value in base_rmse.items()}
    low = U.R.binary_metrics(aligned.occupancy_rate.lt(.1), aligned.low_alert)
    spatial = align_predictions(pd.read_csv(out/'spatial_predictions.csv'), data)
    if set(spatial.prediction_route) != {'unseen'} or spatial.room.nunique() != 9:
        raise ValueError('Spatial evaluation must contain all nine unseen-room folds')
    rooms = {}
    for room, rows in spatial.groupby('room'):
        cold=joblib.load(out/f'fold_models/spatial_{U.ROOMS.index(room)}.joblib')
        expected=data[data.room.eq(room)]
        if cold['fitted_ids']!=set(data[data.room.ne(room)].session_id):raise ValueError('Spatial fitting membership changed')
        prediction=pd.Series(U.predict_cold(cold,expected),index=expected.session_id).loc[rows.session_id]
        np.testing.assert_allclose(rows.prediction,prediction,rtol=0,atol=1e-12)
        fold = report['spatial'][room]
        if set(fold['reference_rooms']) != set(data.room)-{room}:
            raise ValueError('Held room was not excluded from the fitting reference')
        rooms[room] = U.R.metrics(rows.occupancy_rate, rows.prediction)['rmse']
        np.testing.assert_allclose(rooms[room], fold['metrics']['rmse'], rtol=0, atol=1e-12)
    macro = float(np.mean(list(rooms.values())))
    random = pd.read_csv(out/'random_predictions.csv')
    align_predictions(random, random_reference(data))
    random_bundle=joblib.load(out/'fold_models/random.joblib')
    random_query=random_reference(data)
    if set(random_bundle['reference'].session_id)!=set(data.session_id)-set(random_query.session_id):
        raise ValueError('Random fitting membership changed')
    actual=pd.Series(U.R.predict(random_bundle,random_query),index=random_query.session_id).loc[random.session_id]
    np.testing.assert_allclose(random.prediction,actual,rtol=0,atol=1e-12)
    forward=align_predictions(pd.read_csv(out/'forward_cold_predictions.csv'),query)
    for room,rows in forward.groupby('room'):
        cold=joblib.load(out/f'fold_models/forward_{U.ROOMS.index(room)}.joblib')
        expected=query[query.room.eq(room)]
        if cold['fitted_ids']!=set(data[data.room.ne(room)&data.week.le(10)].session_id) or cold['cutoff']>=expected.date.min():
            raise ValueError('Forward cold fitting cohort or chronology changed')
        actual=pd.Series(U.predict_cold(cold,expected),index=expected.session_id).loc[rows.session_id]
        np.testing.assert_allclose(rows.prediction,actual,rtol=0,atol=1e-12)
    if set(random.prediction_route) != {'known'}:
        raise ValueError('Random comparator must use the same router')
    random_rmse = U.R.metrics(random.occupancy_rate, random.prediction)['rmse']
    np.testing.assert_allclose(random_rmse, report['spatial_summary']['random_rmse'], rtol=0, atol=1e-12)
    decisions = gates(gains, low, macro, random_rmse)
    if decisions != report['original_numeric_gates']:
        raise ValueError('Recomputed gates disagree with the model report')
    tn, fp, fn, tp = low['confusion_tn_fp_fn_tp']
    items = [
        dict(criterion='① 相比两个简单基线RMSE改善≥10%', passed=decisions['regression'],
             evidence=f"正式分场景方案第12周RMSE {rmse:.6f}；相对静态课表改善{gains['timetable_static']:.2%}，相对历史均值改善{gains['historical_mean']:.2%}。"),
        dict(criterion='② 低利用率F1≥0.60或Precision≥0.65', passed=decisions['low'],
             evidence=f"同一正式方案第12周Precision {low['precision']:.2%}，F1 {low['f1']:.6f}；F1分支{'通过' if low['f1']>=.6 else '未通过'}，精确率分支{'通过' if low['precision']>=.65 else '未通过'}；命中{tp}、误报{fp}、漏报{fn}，召回率{low['recall']:.2%}。"),
        dict(criterion='③ 留一教室宏RMSE≤0.18或与随机切分差距≤30%', passed=decisions['spatial'],
             evidence=f"同一分场景规则的九教室宏RMSE {macro:.6f}；与自身随机切分差距{macro/random_rmse-1:.2%}。宏RMSE≤0.18分支{'通过' if macro<=.18 else '未通过'}，差距≤30%分支{'通过' if macro/random_rmse-1<=.3 else '未通过'}；两分支分别如实计算。")]
    for item in items:
        item['status'] = '达原定数值门槛' if item['passed'] else '未达原定数值门槛'
    paths = [Path(__file__), root/'03、系统应用/代码/serving_policy.py',
             root/'03、系统应用/代码/app.py', manifest_path,
             *[out/name for name in ['report.json','model.joblib','time_predictions.csv','spatial_predictions.csv','random_predictions.csv']]]
    return dict(policy=POLICY_VERSION, default_mode=DEFAULT_MODE, status='passed' if all(decisions.values()) else 'failed',
                items=items, gates=decisions, n_week12=len(query), n_spatial=len(spatial),
                rmse=rmse, baseline_rmse=base_rmse, baseline_gains=gains, low=low,
                spatial=dict(macro_rmse=macro, room_rmse=rooms, random_rmse=random_rmse, gap_vs_random=macro/random_rmse-1),
                scope='UNSW historical data; original week-12 and nine-room criteria; retrospective point estimates, not a new blind test.',
                adoption=report['protocol']['adoption'],
                clean_chain=clean_chain,verification_level='all four rolling, nine spatial, nine forward-cold and random folds re-inferred',
                cross_week=dict(n=len(rolling),weekly=weekly,pooled=pooled,checks=checks),
                context_adoption=context_adoption,
                limits=dict(pooled_low=pooled, spatial_interval=report['spatial_summary']['conditional_course_bootstrap'],
                            criterion_four='Deferred; not included in this numeric pass.', independent_campus=False),
                sha256={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


def build(root=ROOT):
    root = Path(root)
    try:
        result = assess(root)
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        result = dict(status='unverified', default_mode=DEFAULT_MODE, gates={}, items=[], reason=str(exc))
    U.R.dump(root/'02、模型实验/生成产物/acceptance/numeric_status.json', result)
    return result


if __name__ == '__main__':
    result = build()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['status'] == 'passed' else 1)
