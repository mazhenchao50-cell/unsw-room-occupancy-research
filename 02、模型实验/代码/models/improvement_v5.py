"""L026: rare no-show detection, past-only event history and precision-focused calibration."""
from pathlib import Path
import sys
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import lightgbm as lgb
sys.path.insert(0,str(Path(__file__).resolve().parent))
import revised as R

PROTOCOL={'test_weeks':[8,10,11,12], 'label':'attendees == 0; not low utilization',
 'selection':'Validation average precision, ties resolved by candidate order; no test labels.',
 'candidates':['original_features_lgb','event_history_lgb','event_history_logistic'],
 'thresholds':[.02,.05,.1,.15,.2,.3,.4,.5,.6,.7,.8,.9],
 'threshold_selection':'Calibration F0.5, then precision, then higher threshold. No-positive calibration => threshold 1.01.',
 'history':'Strictly earlier reference dates; course and room event rates smoothed with 10 prior observations; fixed no-history prior .05.',
 'scope':'Retrospective rolling-time evaluation on previously inspected data; no new blind test.',
 'integration_gate':'Pooled precision and F0.5 exceed old baseline; pooled recall >= .2; FP falls in at least 3/4 folds.'}

def event_history(reference,query):
    rows=[]
    for row in query.itertuples():
        past=reference[reference.date<row.date]
        prior=float(past.attendees.eq(0).mean()) if len(past) else .05
        values=[]
        for key in ['course_id','room']:
            group=past[past[key].eq(getattr(row,key))]
            values.extend([(float(group.attendees.eq(0).sum())+10*prior)/(len(group)+10),len(group)])
        rows.append(values)
    return pd.DataFrame(rows,index=query.index,columns=['course_no_show_rate','course_no_show_n','room_no_show_rate','room_no_show_n'])

def features(reference,query,enhanced):
    x=R.raw_features(reference,query)
    return pd.concat([x,event_history(reference,query)],axis=1) if enhanced else x

def fit(name,train):
    enhanced=name!='original_features_lgb'
    x=features(train,train,enhanced);median=x.median().fillna(0)
    if name=='event_history_logistic':
        model=make_pipeline(StandardScaler(),LogisticRegression(C=1,class_weight='balanced',max_iter=2000,random_state=42))
    else:
        model=lgb.LGBMClassifier(n_estimators=100,num_leaves=7,learning_rate=.05,n_jobs=2,verbosity=-1,random_state=42)
    model.fit(x.fillna(median),train.attendees.eq(0))
    return {'model':model,'median':median,'reference':train,'enhanced':enhanced,'name':name,'schema':'noshow_v5'}

def predict(bundle,query):
    return bundle['model'].predict_proba(features(bundle['reference'],query,bundle['enhanced']).fillna(bundle['median']))[:,1]

def score(y,alert):
    m=R.binary_metrics(y,alert);p=m['precision'];r=m['recall']
    m['f0_5']=1.25*p*r/(.25*p+r) if p+r else 0.
    return m

def choose_threshold(y,prob):
    if not np.asarray(y).any():return 1.01,[]
    rows=[{'threshold':t,**score(y,prob>=t)} for t in PROTOCOL['thresholds']]
    best=max(rows,key=lambda m:(m['f0_5'],m['precision'],m['threshold']))
    return best['threshold'],rows

def train_selected(train,valid,final,cal):
    trials=[]
    for name in PROTOCOL['candidates']:
        bundle=fit(name,train);p=predict(bundle,valid)
        ap=float(average_precision_score(valid.attendees.eq(0),p)) if valid.attendees.eq(0).any() else 0.
        trials.append({'candidate':name,'validation_average_precision':ap})
    chosen=max(trials,key=lambda row:row['validation_average_precision'])['candidate']
    bundle=fit(chosen,final)
    bundle['threshold'],scan=choose_threshold(cal.attendees.eq(0),predict(bundle,cal))
    return bundle,trials,scan

def run():
    out=R.ROOT/'02、模型实验/生成产物/improvement_v5';out.mkdir(parents=True,exist_ok=True)
    R.dump(out/'protocol.json',PROTOCOL)
    d=R.load();weeks=sorted(d.week.unique());folds={};frames=[]
    for tw in PROTOCOL['test_weeks']:
        pos=weeks.index(tw);vw,cw=weeks[pos-2:pos]
        train=d[d.week<vw];valid=d[d.week.eq(vw)];cal=d[d.week.eq(cw)];test=d[d.week.eq(tw)]
        final=pd.concat([train,valid]).sort_values('date')
        assert final.date.max()<cal.date.min() and cal.date.max()<test.date.min()
        bundle,trials,scan=train_selected(train,valid,final,cal)
        p=predict(bundle,test)
        old_prob,_,old_bundle=R.no_show(train,valid,final,test)
        new=score(test.attendees.eq(0),p>=bundle['threshold'])
        old=score(test.attendees.eq(0),old_prob>=old_bundle['threshold'])
        folds[str(tw)]={'validation_week':int(vw),'calibration_week':int(cw),
            'train_n':len(train),'validation_n':len(valid),'calibration_n':len(cal),'test_n':len(test),
            'chosen_model':bundle['name'],'threshold':bundle['threshold'],'selection_trials':trials,
            'calibration_scan':scan,'new':new,'old':old}
        f=test[['session_id','date','week','room','course_id','attendees']].copy()
        f['new_probability']=p;f['new_alert']=p>=bundle['threshold']
        f['old_probability']=old_prob;f['old_alert']=old_prob>=old_bundle['threshold']
        frames.append(f)
        if tw==12:joblib.dump(bundle,out/'no_show.joblib')
        print(tw,bundle['name'],'threshold',bundle['threshold'],'old',old['precision'],old['recall'],'new',new['precision'],new['recall'],flush=True)
    f=pd.concat(frames);assert f.session_id.is_unique
    f.to_csv(out/'predictions.csv',index=False)
    new=score(f.attendees.eq(0),f.new_alert);old=score(f.attendees.eq(0),f.old_alert)
    improved=sum(v['new']['confusion_tn_fp_fn_tp'][1]<v['old']['confusion_tn_fp_fn_tp'][1] for v in folds.values())
    gate=bool(new['precision']>old['precision'] and new['f0_5']>old['f0_5'] and new['recall']>=.2 and improved>=3)
    report={'protocol':PROTOCOL,'folds':folds,'pooled':{'new':new,'old':old},'fp_reduced_folds':improved,
            'retrospective_integration_gate_passed':gate,
            'sha256':{str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',out/'protocol.json']}}
    R.dump(out/'report.json',report)
    print('POOLED',json.dumps(report['pooled']), 'gate',gate,flush=True)
    return report

if __name__=='__main__':run()
