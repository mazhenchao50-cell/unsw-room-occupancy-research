"""Fixed retrospective diagnostics requested by the hundred-item audit.

Reports every registered comparison. Does not select a new winner or modify
formal targets, cohorts, thresholds or alerts from these inspected results.
"""
from pathlib import Path
import sys,json,hashlib,time,argparse
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
ROOT=Path(__file__).resolve().parents[2]
for folder in ('02、模型实验/代码/models','01、数据处理/代码','02、模型实验/补充研究/02、漏报与跨周稳定性/代码'):
    sys.path.insert(0,str(ROOT/folder))
import revised as R
import unified as U
import stable_alerts as S
import heal_base as H
OUT=ROOT/'04、运行验证/生成产物/百项整改/诊断实验'


def save(name,data):R.dump(OUT/name,data)


def cluster_interval(frame,key,repeats=1000):
    groups=[g for _,g in frame.groupby(key)];rng=np.random.default_rng(20261118);values=[]
    for _ in range(repeats):
        draw=pd.concat([groups[i] for i in rng.integers(0,len(groups),len(groups))])
        y=draw.occupancy_rate.lt(.1).to_numpy();p=draw.low_alert.to_numpy(bool)
        tp=int((y&p).sum());fp=int((~y&p).sum());fn=int((y&~p).sum())
        values.append([tp/(tp+fp) if tp+fp else 0,tp/(tp+fn) if tp+fn else 0,2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0])
    return dict(cluster=key,clusters=len(groups),replicates=repeats,
        precision_recall_f1_95=np.quantile(values,[.025,.975],axis=0).T.tolist(),
        interpretation='Conditional on these fixed predictions and observed clusters; not selection-aware, not an external validation.')


def calibration(frame):
    y=frame.occupancy_rate.lt(.1).to_numpy(float);p=frame.low_probability.to_numpy();bins=[]
    for low in np.arange(0,1,.1):
        mask=(p>=low)&(p<low+.1 if low<.9 else p<=1)
        if mask.any():bins.append(dict(lower=float(low),n=int(mask.sum()),mean_score=float(p[mask].mean()),observed_fraction=float(y[mask].mean())))
    return dict(brier=float(np.mean((p-y)**2)),ece_10_bins=float(sum(x['n']*abs(x['mean_score']-x['observed_fraction']) for x in bins)/len(frame)),bins=bins,
        note='Descriptive calibration check only; no recalibration on test outcomes.')


def data_diagnostics():
    s=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv');a=pd.read_csv(ROOT/'01、数据处理/清洗产物/attendance_clean.csv')
    c=pd.read_csv(ROOT/'01、数据处理/清洗产物/clean_computed.csv')
    dual=s[s.enrollments.notna()&s.enroll_sched.notna()]
    differences=dual[dual.enrollments.ne(dual.enroll_sched)]
    differences.to_csv(OUT/'选课人数双来源差异.csv',index=False)
    attendance=s[s.attendees.notna()&s.attend_sched.notna()]
    attendance[attendance.attendees.ne(attendance.attend_sched)].to_csv(OUT/'峰值与考勤差异.csv',index=False)
    invalid_cells=[]
    for path in sorted((ROOT/'01、数据处理/原始数据/UNSW').glob('*.csv')):
        raw=pd.read_csv(path,dtype=str,keep_default_na=False)
        fields=('NumSeats','NumDoorways','CountIn','CountOut','NumEnrollments','NumAttendees') if path.name.startswith('week') else ('enrollment','attendance')
        for field in fields:
            values=raw[field];parsed=pd.to_numeric(values.map(H._to_num),errors='coerce')
            minimum=1 if field in ('NumSeats','NumDoorways') else 0
            invalid=~values.map(H._is_na)&(parsed.isna()|parsed.lt(minimum)|parsed.mod(1).ne(0))
            for index,value in values[invalid].items():invalid_cells.append(dict(file=path.name,source_line=int(index)+2,field=field,original_value=value,handling='cell isolated as missing; no guessed repair'))
    pd.DataFrame(invalid_cells,columns=['file','source_line','field','original_value','handling']).to_csv(OUT/'非法原始单元格隔离清单.csv',index=False)
    reasons=[]
    for row in s[s.schedule_match.ne('matched')].itertuples():
        pool=a[a.year.eq(2017)&a.date.eq(row.date)&a.room_code.eq(row.room)]
        reason='ambiguous_exact_slot' if row.schedule_match=='ambiguous' else 'no_same_date_room' if pool.empty else 'start_end_do_not_match'
        reasons.append(dict(session_id=row.session_id,reason=reason,candidate_records=len(pool),
            start_matches=int(pool.start_time.eq(row.course_start).sum()),end_matches=int(pool.end_time.eq(row.course_end).sum())))
    pd.DataFrame(reasons).to_csv(OUT/'未匹配课次分解.csv',index=False)
    current=s.copy();current['unrounded']=current.attendees/current.seats
    flips=current.occupancy_rate.round(4).lt(.1).ne(current.unrounded.lt(.1))&current.unrounded.notna()
    static=c[c.course_id.notna()].groupby(['date','room_code','course_id'])[['seats','doors','num_enrollments']].nunique()
    ledger=H.QualityLedger();october=H.load_computed(str(ROOT/'01、数据处理/原始数据/UNSW'),ledger,range(9,11),True)
    october=october[october.date.astype(str).eq('2017-10-02')]
    columns=[col for col in october if col!='src_week']
    discarded=october[october.src_week.eq(9)][columns].merge(october[october.src_week.eq(10)][columns].drop_duplicates(),on=columns,how='left',indicator=True)
    nonexact=discarded[discarded['_merge'].eq('left_only')].drop(columns='_merge')
    nonexact.to_csv(OUT/'来源策略舍弃的非重复事件.csv',index=False)
    def peaks(part):return part[part.course_id.notna()].groupby(['date','room_code','course_id']).num_attendees.max()
    before=peaks(october);after=peaks(october[october.src_week.eq(10)])
    peak_compare=pd.concat([before.rename('all_sources_peak'),after.rename('retained_peak')],axis=1)
    peak_compare.to_csv(OUT/'重复来源保留策略峰值敏感性.csv')
    save('数据字段诊断.json',dict(total_sessions=len(s),valid_labels=int(s.occupancy_rate.notna().sum()),
        enrollment_dual_nonmissing=len(dual),enrollment_disagreements=len(differences),enrollment_disagreement_fraction=len(differences)/len(dual),
        invalid_raw_numeric_cells=len(invalid_cells),
        attendance_dual_nonmissing=len(attendance),attendance_disagreements=int(attendance.attendees.ne(attendance.attend_sched).sum()),
        schedule_reason_counts=pd.DataFrame(reasons).reason.value_counts().to_dict(),
        unknown_course_events=int(c.course_id.isna().sum()),total_events=len(c),
        unknown_course_nonmissing_occupancy=int((c.course_id.isna()&c.num_attendees.notna()).sum()),
        static_variation_sessions={key:int(static[key].gt(1).sum()) for key in static},
        rounding_label_flips=int(flips.sum()),nonexact_discarded_rows=len(nonexact),
        peak_changed_by_source_policy=int(peak_compare.all_sources_peak.ne(peak_compare.retained_peak).sum()),
        excluded_week9_sessions=json.loads(s[s.week.eq(9)].to_json(orient='records')),
        unresolved=['The two enrollment snapshots have no documented acquisition timestamp; no source is asserted authoritative.',
            'Nonmatching attendance may reflect slot/statistic differences; no guessed crosswalk is applied.',
            'Unknown-course events cannot independently identify vacant versus spontaneous occupation without validated accumulation/coverage.']))


def prediction_diagnostics():
    f=pd.read_csv(U.OUT/'time_predictions.csv');s=R.load();metadata=s.set_index('session_id').loc[f.session_id]
    for name in ('enrollments','seats','attendees','course_start'):f[name]=metadata[name].to_numpy()
    groups={}
    for name,mask in [('enrollment_missing',f.enrollments.isna()),('enrollment_zero',f.enrollments.eq(0)),
                      ('enrollment_positive',f.enrollments.gt(0)),('over_capacity',f.occupancy_rate.gt(1)),('not_over_capacity',f.occupancy_rate.le(1))]:
        part=f[mask]
        groups[name]=dict(n=len(part),regression=R.metrics(part.occupancy_rate,part.prediction),low=R.binary_metrics(part.occupancy_rate.lt(.1),part.low_alert)) if len(part) else dict(n=0)
    components={};budgets={};strong={};misses=[]
    for week,part in f.groupby('week'):
        bundle=joblib.load(U.OUT/f'fold_models/rolling_{int(week)}.joblib');query=s[s.week.eq(week)]
        base=R.baselines(bundle['low']['reference'],query)  # equal information with the formal two-part prediction
        strong[str(week)]={name:R.metrics(query.occupancy_rate,p) for name,p in base.items()}
        strong[str(week)]['formal']=R.metrics(part.occupancy_rate,part.prediction)
        components[str(week)]=dict(combined=R.binary_metrics(part.occupancy_rate.lt(.1),part.low_alert),
            classifier_only=R.binary_metrics(part.occupancy_rate.lt(.1),part.model_alert),
            calendar_only=R.binary_metrics(part.occupancy_rate.lt(.1),part.calendar_review),
            regression_classifier_disagreements=int(part.prediction.lt(.1).ne(part.low_alert).sum()),calibration=calibration(part))
        ranked=part.assign(review_rank_score=part[['low_probability','context_probability']].max(axis=1)).sort_values(['low_alert','review_rank_score','course_start','room'],ascending=[False,False,True,True])
        budgets[str(week)]=[]
        for k in (10,25,50):
            chosen=ranked.head(k);tp=int(chosen.occupancy_rate.lt(.1).sum())
            budgets[str(week)].append(dict(review_budget=k,model_true_low=tp,model_false_alert=k-tp,
                random_expected_true_low=float(k*part.occupancy_rate.lt(.1).mean()),
                note='Offline weekly review budget using the UI alert/score ranking; not measured staff time or usable-space benefit.'))
        lost=part[part.occupancy_rate.lt(.1)&~part.low_alert].copy();lost['review_reason']='both original and context scores below fixed thresholds; no public-holiday flag'
        misses.append(lost)
    pd.concat(misses).to_csv(OUT/'全部跨周漏报逐条清单.csv',index=False)
    spatial=pd.read_csv(U.OUT/'spatial_predictions.csv');forward=pd.read_csv(U.OUT/'forward_cold_predictions.csv')
    cold={name:dict(low_rule_metrics=R.binary_metrics(part.occupancy_rate.lt(.1),part.prediction.lt(.1)),n=len(part),
        calibrated_classifier_probability=False) for name,part in [('spatial',spatial),('forward_cold',forward)]}
    quantile=pd.read_csv(ROOT/'02、模型实验/生成产物/revised/test_predictions.csv')
    interval_coverage={str(room):dict(n=len(g),coverage=float((g.occupancy_rate.ge(g.p10)&g.occupancy_rate.le(g.p90)).mean())) for room,g in quantile.groupby('room')}
    zero=pd.read_csv(ROOT/'02、模型实验/生成产物/label_audit/observed_zero_sessions.csv')
    zero=f.merge(zero[['session_id','max_internal_gap_minutes','observed_span_fraction']],on='session_id',validate='one_to_one')
    zero_groups={}
    for name,mask in [('internal_gap_over_10_minutes',zero.max_internal_gap_minutes.gt(10)),('no_large_internal_gap',zero.max_internal_gap_minutes.le(10))]:
        g=zero[mask];zero_groups[name]=dict(n=len(g),alerts=int(g.low_alert.sum()),misses=int((~g.low_alert).sum()))
    save('预测与复核收益诊断.json',dict(subgroups=groups,weekly=components,strong_baselines=strong,
        zero_peak_coverage_strata=zero_groups,interval_coverage_by_room=interval_coverage,
        review_budget=budgets,cluster_intervals={key:cluster_interval(f,key) for key in ('course_id','date')},
        calibration=calibration(f),cold_low_rule=cold,
        regression_weekly={str(w):R.metrics(g.occupancy_rate,g.prediction) for w,g in f.groupby('week')},
        note='Formal thresholds and samples unchanged; all weeks shown. Conditional uncertainty cannot undo earlier test inspection.'))


def ablations():
    data=R.load();weeks=sorted(data.week.unique());outcomes=[];cost=[];regression=[]
    for week in (8,10,11,12):
        query=data[data.week.eq(week)];reference=data[data.week.lt(week)]
        for recent,label in ((True,'recent'),(False,'no_recent')):
            started=time.perf_counter();bundle=S.fit_bundle(reference,recent);pred=S.predict_components(bundle,query)
            cost.append(dict(week=week,variant=label,seconds=time.perf_counter()-started,warnings=bundle['warnings']))
            for component,prob in pred.items():
                frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
                frame['variant']=label;frame['component']=component;frame['score']=prob;frame['alert']=prob>=.5
                outcomes.append(frame)
        # Remove all enrollment inputs before fitting and querying, including historical normalization.
        no_enrollment=reference.assign(enrollments=np.nan);query_no=query.assign(enrollments=np.nan)
        started=time.perf_counter();bundle=S.fit_bundle(no_enrollment,True);pred=S.predict_components(bundle,query_no)
        cost.append(dict(week=week,variant='no_enrollment',seconds=time.perf_counter()-started,warnings=bundle['warnings']))
        frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['variant']='no_enrollment';frame['component']='ensemble';frame['score']=pred['ensemble'];frame['alert']=frame.score.ge(.5);outcomes.append(frame)
        def separated(part,x):
            x=x.drop(columns='enrollment_missing_or_zero').copy()
            x['enrollment_missing']=part.enrollments.isna().astype(float)
            x['enrollment_zero']=part.enrollments.eq(0).astype(float)
            x['enrollment_pressure']=part.enrollments/part.seats
            return x
        started=time.perf_counter()
        x=separated(reference,S.features(reference,reference));z=separated(query,S.features(reference,query))
        bundle=S.fit_bundle(reference,True,x);pred=S.predict_components(bundle,query,z)
        cost.append(dict(week=week,variant='separate_enrollment_states',seconds=time.perf_counter()-started,warnings=bundle['warnings']))
        frame=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['variant']='separate_enrollment_states';frame['component']='ensemble';frame['score']=pred['ensemble'];frame['alert']=frame.score.ge(.5);outcomes.append(frame)
        i=weeks.index(week);vw,cw=weeks[i-2:i]
        train=data[data.week.lt(vw)];valid=data[data.week.eq(vw)];final=data[data.week.le(vw)]
        for name,method in [('no_enrollment','LightGBM'),('RF','RF'),('LightGBM','LightGBM')]:
            blocks=[train,valid,final,query]
            if name=='no_enrollment':blocks=[part.assign(enrollments=np.nan) for part in blocks]
            started=time.perf_counter();p,_,trials=R.fit_selected(method,*blocks)
            regression.append(dict(week=week,variant=name,seconds=time.perf_counter()-started,metrics=R.metrics(query.occupancy_rate,p),validation_trials=trials))
        print('ABLATION week',week,'complete',flush=True)
    frame=pd.concat(outcomes,ignore_index=True);frame.to_csv(OUT/'固定阈值析因消融预测.csv',index=False)
    scores=[]
    for (variant,component,week),part in frame.groupby(['variant','component','week']):
        scores.append(dict(variant=variant,component=component,week=int(week),metrics=R.binary_metrics(part.occupancy_rate.lt(.1),part.alert)))
    save('消融与无选课人数敏感性.json',dict(protocol='fixed threshold .50; no calendar in classifier factorial; all registered cells and weeks shown; no test-set winner adoption',
        classifier=scores,cost=cost,regression=regression,changes_formal_model=False))


def random_seeds():
    data=R.load();rows=[]
    for seed in (0,1,7,42,2026):
        it,ie=train_test_split(np.arange(len(data)),test_size=.2,random_state=seed)
        itr,iv=train_test_split(it,test_size=.2,random_state=seed)
        p,_,_=R.fit_selected('LightGBM',data.iloc[itr],data.iloc[iv],data.iloc[it],data.iloc[ie])
        cold=U.fit_cold(data.iloc[it]);cp=U.predict_cold(cold,data.iloc[ie])
        rows.append(dict(seed=seed,router_known=R.metrics(data.iloc[ie].occupancy_rate,p),static_same_algorithm=R.metrics(data.iloc[ie].occupancy_rate,cp)))
        print('RANDOM seed',seed,'complete',flush=True)
    save('随机划分与静态对照.json',dict(registered_seeds=[0,1,7,42,2026],results=rows,
        original_gate_seed=42,note='Distribution only; never select best seed or substitute the static comparison for the original router comparator.'))


def unresolved_input_sensitivity():
    data=R.load();no=data.assign(enrollments=np.nan);cold=[]
    for room in sorted(data.room.unique()):
        train=no[no.room.ne(room)];query=no[no.room.eq(room)]
        bundle=U.fit_cold(train);p=U.predict_cold(bundle,query)
        cold.append(dict(room=room,metrics=R.metrics(query.occupancy_rate,p),selected=bundle['selected']))
        print('NO ENROLLMENT cold',room,flush=True)
    full=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv');full['date']=pd.to_datetime(full.date)
    full=full[full.occupancy_rate.notna()].sort_values(['date','room','course_id']).reset_index(drop=True)
    query=full[full.week.eq(12)];bundle=joblib.load(U.OUT/'fold_models/rolling_12.joblib')
    reference=full[full.week.le(10)];x,_,median=R.matrices(reference,query)
    model=R.estimator('LightGBM',bundle['warm']['setting']).fit(x,reference.occupancy_rate)
    altered=dict(model=model,median=median,reference=reference,use_history=True)
    p=R.predict(altered,query)
    low=U.LOW.fit_bundle(full[full.week.lt(12)]);lp=U.LOW.predict_bundle(low,query)
    save('输入假设补充敏感性.json',dict(no_enrollment_cold=cold,
        no_enrollment_cold_macro_rmse=float(np.mean([x['metrics']['rmse'] for x in cold])),
        include_week9=dict(additional_training_rows=int(full.week.eq(9).sum()),
            no_retuning=True,regression=R.metrics(query.occupancy_rate,p),low=R.binary_metrics(query.occupancy_rate.lt(.1),lp['alert'])),
        interpretation='Sensitivity only. Original cohort is unchanged. Enrollment timing remains a source-documentation question regardless of scores.'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--models',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    save('预设诊断协议.json',dict(date='2026-11-18',classifier_threshold=.5,weeks=[8,10,11,12],
        seeds=[0,1,7,42,2026],regressors=['LightGBM','RF'],enrollment_ablation='remove feature from both reference and query',
        additional_sensitivity=['separate missing/zero enrollment indicators with observed pressure','all nine cold-room folds without enrollment','include the single week9 observation in week12 fitting without retuning'],
        purpose='Resolve hundred-audit evidence gaps, not select on outer-test performance',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    data_diagnostics();prediction_diagnostics()
    if args.models:ablations();random_seeds();unresolved_input_sensitivity()
    print('Diagnostics complete',flush=True)


if __name__=='__main__':main()
