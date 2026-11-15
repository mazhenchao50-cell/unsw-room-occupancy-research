"""Revision protocol v3. All published scores are retrospective, not a new blind test."""
from pathlib import Path
import json, hashlib, platform, importlib.metadata, argparse
import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, precision_recall_fscore_support, confusion_matrix

ROOT = Path(__file__).resolve().parents[3]
FEATURES = ['course_start_h','duration_h','doors','seats','enrollments','weekday','is_weekend','is_morning']
SEED = 42

def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def load(path=None):
    d = pd.read_csv(path or ROOT/'01、数据处理/清洗产物/sessions.csv')
    d['date'] = pd.to_datetime(d.date)
    d = d[d.occupancy_rate.notna() & d.week.ne(9)].copy()
    return d.sort_values(['date','room','course_id']).reset_index(drop=True)

def history(reference, query):
    """Only labelled reference sessions strictly BEFORE query calendar date.
    Same-day sessions and the row's own target can never enter these features.
    Cold-start prior is fixed at 0.3, not fitted using future training labels.
    """
    out = []
    for row in query.itertuples():
        past = reference[reference.date < row.date]
        course = past.loc[past.course_id.eq(row.course_id), 'occupancy_rate']
        prior = float(past.occupancy_rate.mean()) if len(past) else 0.3
        out.append((float(course.mean()) if len(course) else prior, len(course)))
    return pd.DataFrame(out, columns=['course_hist_mean','course_hist_n'], index=query.index)

def raw_features(reference, query, use_history=True):
    x = query[FEATURES[2:]].copy()
    start = pd.to_timedelta(query.course_start, errors='coerce').dt.total_seconds()/3600
    end = pd.to_timedelta(query.course_end, errors='coerce').dt.total_seconds()/3600
    x['course_start_h'] = start
    x['duration_h'] = (end-start).where(end>start)
    x = x[FEATURES].astype(float)
    if use_history:
        x = pd.concat([x, history(reference, query)], axis=1)
    return x

def matrices(train, query, use_history=True):
    a = raw_features(train, train, use_history)
    b = raw_features(train, query, use_history)
    med = a.median().fillna(0)
    return a.fillna(med), b.fillna(med), med

def binary_metrics(y, p):
    y = np.asarray(y, dtype=bool); p = np.asarray(p, dtype=bool)
    prec, rec, f1, _ = precision_recall_fscore_support(y, p, average='binary', zero_division=0)
    n = int(p.sum()); success = int((y&p).sum())
    if n:
        z=1.96; ph=success/n; den=1+z*z/n
        center=(ph+z*z/(2*n))/den; rad=z*np.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
        ci=[float(center-rad),float(center+rad)]
    else: ci=None
    return {'precision':float(prec),'recall':float(rec),'f1':float(f1),'actual_positive':int(y.sum()),'predicted_positive':n,
            'precision_wilson_95':ci,'confusion_tn_fp_fn_tp':confusion_matrix(y,p,labels=[False,True]).ravel().astype(int).tolist()}

def metrics(y, p):
    y=np.asarray(y); p=np.maximum(0,np.asarray(p))
    return {'n':len(y),'rmse':float(np.sqrt(mean_squared_error(y,p))),'mae':float(mean_absolute_error(y,p)),
            'r2':float(r2_score(y,p)) if len(y)>1 else None,'low_utilization':binary_metrics(y<.1,p<.1),
            'over_capacity':binary_metrics(y>1,p>1)}

def estimator(name, setting):
    if name=='LightGBM': return lgb.LGBMRegressor(n_estimators=setting,learning_rate=.05,num_leaves=15,min_child_samples=20,random_state=SEED,n_jobs=2,verbosity=-1)
    if name=='RF': return RandomForestRegressor(n_estimators=200,min_samples_leaf=setting,random_state=SEED,n_jobs=2)
    if name=='MLR': return make_pipeline(StandardScaler(),Ridge(alpha=setting))
    if name=='SVR': return make_pipeline(StandardScaler(),SVR(C=setting,epsilon=.05))
    raise ValueError(name)

GRID={'LightGBM':[80,200,400],'RF':[1,5,12],'MLR':[0.,1.,10.],'SVR':[.1,1.,10.]}

def fit_selected(name, train, valid, final, query, use_history=True):
    a,b,_=matrices(train,valid,use_history)
    trials=[]
    for setting in GRID[name]:
        m=estimator(name,setting).fit(a,train.occupancy_rate)
        trials.append((float(mean_squared_error(valid.occupancy_rate,np.maximum(0,m.predict(b)))),setting))
    _,chosen=min(trials)
    a,b,med=matrices(final,query,use_history)
    m=estimator(name,chosen).fit(a,final.occupancy_rate)
    return np.maximum(0,m.predict(b)), {'model':m,'median':med,'reference':final,'use_history':use_history,'features':list(a.columns),'setting':chosen}, trials

def predict(bundle, query):
    x=raw_features(bundle['reference'],query,bundle['use_history']).fillna(bundle['median'])
    return np.maximum(0,bundle['model'].predict(x))

def baselines(train, test):
    global_mean=float(train.occupancy_rate.mean())
    keys=['room','weekday','is_morning']
    out={}
    for stat in ['mean','median']:
        h=train.groupby(keys).occupancy_rate.agg(stat)
        vals=[h.get(tuple(row),global_mean) for row in test[keys].itertuples(index=False,name=None)]
        out['historical_'+stat]=np.asarray(vals)
    out['course_history_mean']=history(train,test).course_hist_mean.to_numpy()
    # Scheduled session baseline: scheduled enrolment / capacity, training-only imputation.
    enrollment=test.enrollments.fillna(train.enrollments.median())
    out['timetable_static']=(enrollment/test.seats).to_numpy()
    return {k:np.maximum(0,v) for k,v in out.items()}

def prediction_frame(test, p, **extra):
    f=test[['session_id','date','room','course_id','week','seats','attendees','occupancy_rate']].copy()
    f['prediction']=p
    for k,v in extra.items(): f[k]=v
    return f

def cluster_ci(frame):
    rng=np.random.default_rng(SEED); dates=frame.date.unique(); vals=[]
    for _ in range(500):
        s=pd.concat([frame[frame.date.eq(d)] for d in rng.choice(dates,len(dates),replace=True)])
        vals.append(np.sqrt(mean_squared_error(s.occupancy_rate,s.prediction)))
    return {'rmse_date_cluster_bootstrap_95':np.quantile(vals,[.025,.975]).tolist(),'clusters':len(dates),'replicates':500,
            'note':'Conditional retrospective uncertainty; does not establish new-campus validity.'}

def quantiles(train, valid, final, cal, test):
    models=[]; arrays=[]; choices=[]
    for alpha in [.1,.9]:
        a,b,_=matrices(train,valid)
        m=lgb.LGBMRegressor(objective='quantile',alpha=alpha,n_estimators=600,learning_rate=.05,num_leaves=15,n_jobs=2,verbosity=-1,random_state=SEED)
        m.fit(a,train.occupancy_rate,eval_set=[(b,valid.occupancy_rate)],callbacks=[lgb.early_stopping(40,verbose=False)])
        n=int(m.best_iteration_ or 600); choices.append(n)
        a,b,med=matrices(final,pd.concat([cal,test]))
        m=lgb.LGBMRegressor(objective='quantile',alpha=alpha,n_estimators=n,learning_rate=.05,num_leaves=15,n_jobs=2,verbosity=-1,random_state=SEED).fit(a,final.occupancy_rate)
        arrays.append(np.maximum(0,m.predict(b))); models.append(m)
    arr=np.array(arrays); crossings=int((arr[0]>arr[1]).sum()); arr.sort(axis=0)
    nc=len(cal); scores=np.maximum.reduce([arr[0,:nc]-cal.occupancy_rate.to_numpy(),cal.occupancy_rate.to_numpy()-arr[1,:nc],np.zeros(nc)])
    rank=min(nc,int(np.ceil((nc+1)*.8))); delta=float(np.sort(scores)[rank-1])
    low=np.maximum(0,arr[0,nc:]-delta); high=arr[1,nc:]+delta
    cover=(test.occupancy_rate.to_numpy()>=low)&(test.occupancy_rate.to_numpy()<=high)
    byroom={r:{'n':int(mask.sum()),'coverage':float(cover[mask].mean())} for r in sorted(test.room.unique()) for mask in [test.room.eq(r).to_numpy()]}
    return low,high,{'nominal_coverage':.8,'coverage':float(cover.mean()),'mean_width':float((high-low).mean()),'calibration_n':nc,'calibration_delta':delta,'trees_p10_p90':choices,'crossings_before_sort':crossings,'per_room':byroom,'note':'Time dependence violates exchangeability; no guaranteed future coverage.'}

def no_show(train,valid,final,test):
    # An independent zero-attendee classification task, never label <10% as no-show.
    a,b,_=matrices(train,valid)
    def cls(n): return lgb.LGBMClassifier(n_estimators=n,num_leaves=7,learning_rate=.05,n_jobs=2,verbosity=-1,random_state=SEED)
    candidates=[]
    for n in [40,100,200]:
        m=cls(n).fit(a,train.attendees.eq(0)); prob=m.predict_proba(b)[:,1]
        for threshold in [.1,.2,.3,.5]:
            met=binary_metrics(valid.attendees.eq(0),prob>=threshold)
            candidates.append((met['f1'],threshold,n))
    _,threshold,n=max(candidates)
    a,b,med=matrices(final,test); model=cls(n).fit(a,final.attendees.eq(0)); prob=model.predict_proba(b)[:,1]
    bundle={'model':model,'median':med,'reference':final,'use_history':True,'threshold':threshold}
    return prob, binary_metrics(test.attendees.eq(0),prob>=threshold),bundle

def run(out=None):
    out=Path(out or ROOT/'02、模型实验/生成产物/revised'); out.mkdir(parents=True,exist_ok=True)
    d=load(); report={'protocol':'v3','test_status':'Retrospective revision evaluation; week12 already inspected in previous research.',
                      'postprocessing':'All regressors lower-clipped at zero, no upper clipping. Labels retained above 1.',
                      'search_budget':'3 predefined settings per algorithm; common features; scaled SVR and linear model. MLR alpha=0 or ridge alpha=1/10 selected explicitly.',
                      'time':{},'rolling':{},'ablation':{},'loro':{}}
    weeks=sorted(d.week.unique())
    for tw in [8,10,11,12]:
        wi=weeks.index(tw); vw=weeks[wi-2]; cw=weeks[wi-1]
        tr=d[d.week<vw]; va=d[d.week.eq(vw)]; cal=d[d.week.eq(cw)]; te=d[d.week.eq(tw)]; final=pd.concat([tr,va]).sort_values('date')
        predictions=baselines(final,te); trials={}; bundles={}
        for name in GRID:
            p,b,t=fit_selected(name,tr,va,final,te); predictions[name]=p; bundles[name]=b; trials[name]=t
        scores={name:metrics(te.occupancy_rate,p) for name,p in predictions.items()}
        report['rolling'][str(tw)]={'train_weeks':sorted(int(w) for w in tr.week.unique()),'validation_week':int(vw),'calibration_week':int(cw),'scores':scores}
        for name,p in predictions.items():
            prediction_frame(te,p).to_csv(out/f'week{tw}_{name}.csv',index=False)
        print('time',tw,{k:round(v['rmse'],4) for k,v in scores.items()},flush=True)
        if tw==12:
            bundle=bundles['LightGBM']; joblib.dump(bundle,out/'model.joblib')
            report['time']=scores; report['selection_trials']=trials
            report['time']['LightGBM'].update(cluster_ci(prediction_frame(te,predictions['LightGBM'])))
            report['unseen_course_count_week12']=int((~te.course_id.isin(final.course_id)).sum())
            lo,hi,q=quantiles(tr,va,final,cal,te); report['quantiles']=q
            prob,nsm,nsbundle=no_show(tr,va,final,te); report['no_show']={'metrics':nsm,'threshold':nsbundle['threshold'],'label':'attendees == 0 at session peak'}
            joblib.dump(nsbundle,out/'no_show.joblib')
            prediction_frame(te,predictions['LightGBM'],p10=lo,p90=hi,no_show_probability=prob).to_csv(out/'test_predictions.csv',index=False)
            for name in GRID:
                p,_,_=fit_selected(name,tr,va,final,te,False)
                report['ablation'][name]={'without_course_history':metrics(te.occupancy_rate,p),'with_course_history':scores[name]}
    # Spatial folds and random comparator both use the same feature schema and tuning budget.
    frames=[]; perroom={}
    for room in sorted(d.room.unique()):
        te=d[d.room.eq(room)]; available=d[~d.room.eq(room)]
        tr=available[available.week.lt(11)]; va=available[available.week.eq(11)]
        p,b,_=fit_selected('LightGBM',tr,va,available,te)
        met=metrics(te.occupancy_rate,p); met['train_enrollment_median']=float(b['median']['enrollments']); met['unseen_course_fraction']=float((~te.course_id.isin(available.course_id)).mean())
        met['attendees_mae']=float(np.mean(np.abs((p-te.occupancy_rate.to_numpy())*te.seats.to_numpy())))
        perroom[room]=met; frames.append(prediction_frame(te,p)); print('LORO',room,round(met['rmse'],4),flush=True)
    f=pd.concat(frames); f.to_csv(out/'loro_predictions.csv',index=False)
    report['loro']={'micro':metrics(f.occupancy_rate,f.prediction),'macro_rmse':float(np.mean([v['rmse'] for v in perroom.values()])),
                    'per_room':perroom,'note':'Pure spatial model training includes later dates from other rooms. History features themselves only use earlier dates. Not a prospective-time experiment.'}
    ix=np.arange(len(d)); it,ie=train_test_split(ix,test_size=.2,random_state=SEED); itr,iv=train_test_split(it,test_size=.2,random_state=SEED)
    p,_,_=fit_selected('LightGBM',d.iloc[itr],d.iloc[iv],d.iloc[it],d.iloc[ie]); report['random_split']=metrics(d.iloc[ie].occupancy_rate,p)
    prediction_frame(d.iloc[ie],p).to_csv(out/'random_predictions.csv',index=False)
    base=report['random_split']['rmse']; report['loro']['macro_gap_vs_random']=(report['loro']['macro_rmse']-base)/base
    report['loro']['micro_gap_vs_time']=(report['loro']['micro']['rmse']-report['time']['LightGBM']['rmse'])/report['time']['LightGBM']['rmse']
    gs=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=SEED); it,ie=next(gs.split(d,groups=d.course_id))
    avail=d.iloc[it]; tr=avail[avail.week.lt(11)]; va=avail[avail.week.eq(11)]
    p,_,_=fit_selected('LightGBM',tr,va,avail,d.iloc[ie]); report['unseen_courses']=metrics(d.iloc[ie].occupancy_rate,p)
    report['unseen_courses']['held_course_count']=int(d.iloc[ie].course_id.nunique())
    prediction_frame(d.iloc[ie],p).to_csv(out/'unseen_course_predictions.csv',index=False)
    report['scope']={'cross_semester':'Not validated: attendance-only 2018 lacks aligned course identifiers and sensor event labels.',
                     'weather':'Not used; feature proposal withdrawn from implemented scope. Historical observed weather is not a pre-class forecast.',
                     'unscheduled_periods':'Unknown occupancy; never infer empty from absent session rows.'}
    ref=report['time']['LightGBM']; gains={k:(report['time'][k]['rmse']-ref['rmse'])/report['time'][k]['rmse'] for k in ['timetable_static','historical_mean','RF']}
    report['acceptance']={'baseline_relative_improvements':gains,'regression_10pct_both_simple_baselines':all(gains[k]>=.1 for k in ['timetable_static','historical_mean']),
                          'low_utilization_F1_060_or_precision_065':ref['low_utilization']['f1']>=.6 or (ref['low_utilization']['predicted_positive']>0 and ref['low_utilization']['precision']>=.65),
                          'loro_macro_018_or_gap_030':report['loro']['macro_rmse']<=.18 or report['loro']['macro_gap_vs_random']<=.3,
                          'note':'Original submitted numeric thresholds retained. Terminology/scope corrections require academic acceptance; software fixes do not guarantee threshold achievement.'}
    dump(out/'report.json',report)
    dump(out/'run_metadata.json',{'python':platform.python_version(),'seed':SEED,'versions':{k:importlib.metadata.version(k) for k in ['pandas','numpy','scikit-learn','lightgbm','shap','streamlit']},
                                 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sessions_sha256':hashlib.sha256((ROOT/'01、数据处理/清洗产物/sessions.csv').read_bytes()).hexdigest()})
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--out-dir',type=Path)
    run(parser.parse_args().out_dir)
