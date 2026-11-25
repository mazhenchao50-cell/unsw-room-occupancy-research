"""Pre-specified, nested candidates targeting missed alerts and input dependence."""
from pathlib import Path
import argparse, hashlib, json, sys, time
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parents[1]/'生成产物'
sys.path.insert(0,str(ROOT/'02、模型实验/代码/models'))
import revised as R
import stable_low as LOW
import calendar_context as C
import improvement_v8 as V8

PROTOCOL=Path(__file__).with_name('研究协议.json')
FAMILIES=('ensemble_1','logistic_2','lightgbm_2','forest_2','extra_2')
COLD=('ridge_10','ridge_100','svr_1','svr_10','forest_10','forest_30','extra_10','extra_30','lightgbm_80','lightgbm_200','count_ridge_100')
THRESHOLDS=(.25,.35,.45,.55,.65)

def save(name,data):R.dump(OUT/name,data)

def low_features(reference,query,mode):
    if mode=='without':reference=reference.assign(enrollments=np.nan);query=query.assign(enrollments=np.nan)
    elif mode!='with':raise ValueError(mode)
    x=LOW.features(reference,query)
    if mode=='without':
        x=x.drop(columns=['enrollments','enrollment_pressure','enrollment_missing_or_zero','attendance_factor_history'])
    return x

def classifier(name):
    args=dict(random_state=42,n_jobs=2)
    if name=='logistic_2':return LogisticRegression(C=1,class_weight={0:1,1:2},max_iter=3000,random_state=42)
    if name=='lightgbm_2':return lgb.LGBMClassifier(n_estimators=150,num_leaves=7,min_child_samples=30,learning_rate=.05,class_weight={0:1,1:2},verbosity=-1,**args)
    if name=='forest_2':return RandomForestClassifier(n_estimators=200,min_samples_leaf=10,class_weight={0:1,1:2},**args)
    if name=='extra_2':return ExtraTreesClassifier(n_estimators=200,min_samples_leaf=10,class_weight={0:1,1:2},**args)
    if name=='ensemble_1':return (LogisticRegression(C=1,max_iter=3000,random_state=42),lgb.LGBMClassifier(n_estimators=150,num_leaves=7,min_child_samples=30,learning_rate=.05,verbosity=-1,**args))
    raise ValueError(name)

def fit_classifier(reference,mode,name,matrix=None):
    x=low_features(reference,reference,mode) if matrix is None else matrix
    med=x.median().fillna(0);x=x.fillna(med);scaler=StandardScaler().fit(x)
    model=classifier(name);y=reference.occupancy_rate.lt(.1)
    if isinstance(model,tuple):model[0].fit(scaler.transform(x),y);model[1].fit(x,y)
    else:model.fit(scaler.transform(x) if name.startswith('logistic') else x,y)
    return dict(model=model,median=med,scaler=scaler,reference=reference.copy(),mode=mode,name=name,cutoff=reference.date.max(),fitted_ids=set(reference.session_id))

def predict_classifier(bundle,query,matrix=None):
    if query.date.min()<=bundle['cutoff'] or set(query.session_id)&bundle['fitted_ids']:raise ValueError('Forward-only prediction')
    x=(low_features(bundle['reference'],query,bundle['mode']) if matrix is None else matrix).fillna(bundle['median'])
    if list(x)!=list(bundle['median'].index) or not np.isfinite(x.to_numpy()).all():raise ValueError('Feature contract')
    model=bundle['model']
    if isinstance(model,tuple):return (model[0].predict_proba(bundle['scaler'].transform(x))[:,1]+model[1].predict_proba(x)[:,1])/2
    return model.predict_proba(bundle['scaler'].transform(x) if bundle['name'].startswith('logistic') else x)[:,1]

def f2(m):
    p,r=m['precision'],m['recall']
    return 5*p*r/(4*p+r) if 4*p+r else 0.

def choose_policy(earlier):
    trials=[]
    for mode in ('without','with'):
        for name in FAMILIES:
            frame=earlier[(earlier['mode']==mode)&(earlier['family']==name)]
            if not frame.session_id.is_unique or frame.week.nunique()!=3:raise ValueError('Three complete earlier weeks required')
            for threshold in THRESHOLDS:
                weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.score.ge(threshold)) for w,g in frame.groupby('week')}
                pooled=R.binary_metrics(frame.occupancy_rate.lt(.1),frame.score.ge(threshold))
                eligible=pooled['precision']>=.65 and min(m['precision'] for m in weekly.values())>=.5 and pooled['predicted_positive']>=20
                trials.append(dict(mode=mode,family=name,threshold=threshold,pooled=pooled,weekly=weekly,eligible=eligible,min_f2=min(f2(m) for m in weekly.values())))
    eligible=[t for t in trials if t['eligible']]
    if eligible:best=max(eligible,key=lambda t:(t['min_f2'],f2(t['pooled']),-('without','with').index(t['mode']),-FAMILIES.index(t['family']),t['threshold']))
    else:best=max(trials,key=lambda t:(-max(0,.65-t['pooled']['precision']),t['min_f2'],f2(t['pooled']),-trials.index(t)))
    return best,trials

def run_low(data):
    weeks=sorted(map(int,data.week.unique()));frames=[];models=OUT/'模型';models.mkdir(exist_ok=True)
    for week in weeks[2:]:
        train=data[data.week.lt(week)];query=data[data.week.eq(week)]
        for mode in ('without','with'):
            started=time.perf_counter();x=low_features(train,train,mode);z=low_features(train,query,mode)
            for name in FAMILIES:
                bundle=fit_classifier(train,mode,name,x);p=predict_classifier(bundle,query,z)
                f=query[['session_id','date','room','course_id','week','occupancy_rate']].copy()
                f['mode']=mode;f['family']=name;f['score']=p;frames.append(f)
                if week in (8,10,11,12):joblib.dump(bundle,models/f'low_{week}_{mode}_{name}.joblib')
            print('low fit',week,mode,round(time.perf_counter()-started,2),flush=True)
    all_predictions=pd.concat(frames,ignore_index=True);all_predictions.to_csv(OUT/'全部逐周前推分数.csv',index=False)
    selected=[];decisions={}
    for week in (8,10,11,12):
        prior=[w for w in weeks if w<week][-3:]
        earlier=all_predictions[all_predictions.week.isin(prior)]
        if earlier.date.max()>=data[data.week.eq(week)].date.min():raise ValueError('Selection leakage')
        best,trials=choose_policy(earlier);decisions[str(week)]=dict(prior_weeks=prior,selected=best,trials=trials)
        f=all_predictions[(all_predictions.week==week)&(all_predictions['mode']==best['mode'])&(all_predictions['family']==best['family'])].copy()
        bundle=joblib.load(models/f"low_{week}_{best['mode']}_{best['family']}.joblib")
        query=data.set_index('session_id',drop=False).loc[f.session_id]
        repeated=predict_classifier(bundle,query)
        np.testing.assert_allclose(repeated,f.score,atol=1e-12,rtol=0)
        np.testing.assert_array_equal(repeated>=best['threshold'],f.score.ge(best['threshold']))
        f['threshold']=best['threshold'];f['calendar_review']=C.review_flag(query);f['alert']=f.score.ge(best['threshold'])|f.calendar_review
        selected.append(f)
    chosen=pd.concat(selected,ignore_index=True);chosen.to_csv(OUT/'入选策略逐课次预测.csv',index=False)
    old=pd.read_csv(ROOT/'02、模型实验/生成产物/unified/time_predictions.csv').set_index('session_id').loc[chosen.session_id]
    old['low_alert']=old.model_alert|old.calendar_review  # Fixed v3 comparator, even after adopting a later formal system.
    weekly={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.alert) for w,g in chosen.groupby('week')}
    pooled=R.binary_metrics(chosen.occupancy_rate.lt(.1),chosen.alert)
    before={str(int(w)):R.binary_metrics(g.occupancy_rate.lt(.1),g.low_alert) for w,g in old.groupby('week')}
    gates=dict(original_criterion2_every_week=all(m['f1']>=.6 or m['precision']>=.65 for m in weekly.values()),pooled_precision=pooled['precision']>=.65,
        misses_not_increased_any_week=all(weekly[w]['confusion_tn_fp_fn_tp'][2]<=before[w]['confusion_tn_fp_fn_tp'][2] for w in weekly),
        pooled_misses_reduced=pooled['confusion_tn_fp_fn_tp'][2]<int((old.occupancy_rate.lt(.1)&~old.low_alert).sum()))
    report=dict(weekly=weekly,pooled=pooled,before=before,decisions=decisions,adoption_checks=gates,eligible=all(gates.values()),formal_changed=False)
    save('漏报与周波动结果.json',report);print('LOW SUMMARY',json.dumps({k:v for k,v in report.items() if k!='decisions'},ensure_ascii=False),flush=True)

def cold_features(frame):
    # Query truth and snapshot-dependent enrollment are never accessed.
    x=R.raw_features(frame.iloc[:0],frame.assign(enrollments=np.nan),use_history=False).drop(columns='enrollments')
    x['log_seats']=np.log(frame.seats);x['inverse_seats']=1/frame.seats
    x['term_week']=frame.week.astype(float)
    x['hour_sin']=np.sin(2*np.pi*x.course_start_h/24);x['hour_cos']=np.cos(2*np.pi*x.course_start_h/24)
    return x

def fit_cold(train,candidate):
    x=cold_features(train);med=x.median().fillna(0);x=x.fillna(med)
    weights=V8.room_weights(train);scale=StandardScaler().fit(x,sample_weight=weights);kind,param=candidate.rsplit('_',1);param=int(param)
    if kind in ('ridge','count_ridge'):model=Ridge(alpha=param)
    elif kind=='svr':model=SVR(C=param,epsilon=.05)
    elif kind=='forest':model=RandomForestRegressor(n_estimators=120,min_samples_leaf=param,n_jobs=2,random_state=42)
    elif kind=='extra':model=ExtraTreesRegressor(n_estimators=120,min_samples_leaf=param,n_jobs=2,random_state=42)
    elif kind=='lightgbm':model=lgb.LGBMRegressor(n_estimators=param,num_leaves=7,min_child_samples=30,learning_rate=.05,n_jobs=2,random_state=42,verbosity=-1)
    else:raise ValueError(candidate)
    standardized=kind in ('ridge','count_ridge','svr');target=train.occupancy_rate.to_numpy()
    if kind=='count_ridge':target=target*train.seats.to_numpy();weights=weights/(train.seats.to_numpy()**2);weights=weights/weights.mean()
    model.fit(scale.transform(x) if standardized else x,target,sample_weight=weights)
    return dict(model=model,median=med,scaler=scale,standardized=standardized,count=kind=='count_ridge',candidate=candidate,
                reference_rooms=sorted(train.room.unique()),fitted_ids=set(train.session_id),cutoff=train.date.max())

def predict_cold(bundle,query):
    if set(query.session_id)&bundle['fitted_ids']:raise ValueError('Fitted query')
    x=cold_features(query).fillna(bundle['median'])
    p=bundle['model'].predict(bundle['scaler'].transform(x) if bundle['standardized'] else x)
    if bundle['count']:p=p/query.seats.to_numpy()
    return np.maximum(0,p)

def select_cold(available):
    trials=[]
    for candidate in COLD:
        errors={}
        for room in sorted(available.room.unique()):
            train=available[available.room.ne(room)];query=available[available.room.eq(room)]
            p=predict_cold(fit_cold(train,candidate),query)
            errors[room]=float(np.sqrt(np.mean((query.occupancy_rate.to_numpy()-p)**2)))
        trials.append(dict(candidate=candidate,inner_macro_rmse=float(np.mean(list(errors.values()))),rooms=errors))
    best=min(trials,key=lambda t:(t['inner_macro_rmse'],COLD.index(t['candidate'])))
    return best['candidate'],trials

def run_cold(data):
    models=OUT/'模型';models.mkdir(exist_ok=True);reports={}
    for regime in ('spatial','forward'):
        frames=[];details={}
        for i,room in enumerate(sorted(data.room.unique())):
            available=data[data.room.ne(room)];query=data[data.room.eq(room)]
            if regime=='forward':available=available[available.week.le(10)];query=query[query.week.eq(12)]
            started=time.perf_counter();candidate,trials=select_cold(available);bundle=fit_cold(available,candidate)
            if regime=='forward' and bundle['cutoff']>=query.date.min():raise ValueError('Future labels')
            path=models/f'{regime}_{i}.joblib';joblib.dump(bundle,path);p=predict_cold(joblib.load(path),query)
            frame=R.prediction_frame(query,p);frames.append(frame)
            details[room]=dict(candidate=candidate,trials=trials,metrics=R.metrics(query.occupancy_rate,p),seconds=time.perf_counter()-started)
            print('cold',regime,room,candidate,details[room]['metrics']['rmse'],flush=True)
        joined=pd.concat(frames,ignore_index=True);joined.to_csv(OUT/f'{regime}_逐课次预测.csv',index=False)
        reports[regime]=dict(macro_rmse=float(np.mean([v['metrics']['rmse'] for v in details.values()])),rooms=details,conditional_interval=V8.conditional_interval(joined))
        save('无报名冷启动结果.json',reports)
    reports['eligible']=all(reports[k]['macro_rmse']<=.18 for k in ('spatial','forward'));reports['formal_changed']=False
    save('无报名冷启动结果.json',reports);print('COLD SUMMARY',reports['spatial']['macro_rmse'],reports['forward']['macro_rmse'],reports['eligible'],flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--task',choices=['low','cold','all'],default='all');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'));save('执行输入.json',dict(protocol=protocol,protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_sha256=hashlib.sha256((ROOT/'01、数据处理/清洗产物/sessions.csv').read_bytes()).hexdigest()))
    data=R.load()
    if args.task in ('low','all'):run_low(data)
    if args.task in ('cold','all'):run_cold(data)

if __name__=='__main__':main()
