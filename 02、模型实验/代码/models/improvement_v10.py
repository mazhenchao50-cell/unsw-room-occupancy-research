"""V10: select low-utilization classifiers by validation ranking quality.

Explores class weighting and different model families while keeping all
calibration and test observations strictly chronological. Retrospective only.
"""
from pathlib import Path
import hashlib
import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

import revised as R
import improvement_v7 as V7
import improvement_v9 as V9

OUT=R.ROOT/'02、模型实验/生成产物/improvement_v10'
WEEKS=[8,10,11,12]


def candidates():
    out=[]
    for trees in [80,200,400]:
        for pos_weight in [1.,2.,3.]:
            out.append(('lgbm',trees,pos_weight))
    for leaf in [5,10]:
        for family in ['rf','extra']:
            out.append((family,leaf,'balanced_subsample' if family=='rf' else 'balanced'))
    for c in [.1,1.,10.]:
        for weighting in [None,'balanced']:
            out.append(('logit',c,weighting))
    return out


def fit_predict(train,query,candidate):
    if train.empty or query.empty or train.date.max()>=query.date.min():
        raise ValueError('Require nonempty, strictly chronological train/query sets')
    if set(train.session_id)&set(query.session_id):
        raise ValueError('Session leakage')
    a,b=V7.matrix(train,query)
    family,param,weight=candidate
    if family=='lgbm':
        model=lgb.LGBMClassifier(n_estimators=int(param),learning_rate=.05,num_leaves=15,
            min_child_samples=20,random_state=42,n_jobs=2,verbosity=-1,scale_pos_weight=weight)
        model.fit(a,train.occupancy_rate.lt(.1))
    elif family in ('rf','extra'):
        cls=RandomForestClassifier if family=='rf' else ExtraTreesClassifier
        kwargs=dict(n_estimators=400,min_samples_leaf=int(param),max_features=.8,
                    class_weight=weight,random_state=42,n_jobs=2)
        model=cls(**kwargs).fit(a,train.occupancy_rate.lt(.1))
    elif family=='logit':
        scaler=StandardScaler().fit(a);a=scaler.transform(a);b=scaler.transform(b)
        model=LogisticRegression(C=float(param),class_weight=weight,max_iter=2000,random_state=42)
        model.fit(a,train.occupancy_rate.lt(.1))
    else:
        raise ValueError(candidate)
    return V9.probabilities(model,b)


def fit_bundle(reference,candidate):
    """Fit the selected classifier on all pre-query labels for serving."""
    if reference.empty:
        raise ValueError('Nonempty reference required')
    a=V7.features(reference,reference);median=a.median().fillna(0);a=a.fillna(median)
    family,param,weight=candidate;scaler=None
    if family=='lgbm':
        model=lgb.LGBMClassifier(n_estimators=int(param),learning_rate=.05,num_leaves=15,
            min_child_samples=20,random_state=42,n_jobs=2,verbosity=-1,scale_pos_weight=weight)
        model.fit(a,reference.occupancy_rate.lt(.1))
    elif family in ('rf','extra'):
        cls=RandomForestClassifier if family=='rf' else ExtraTreesClassifier
        model=cls(n_estimators=400,min_samples_leaf=int(param),max_features=.8,
            class_weight=weight,random_state=42,n_jobs=2)
        model.fit(a,reference.occupancy_rate.lt(.1))
    elif family=='logit':
        scaler=StandardScaler().fit(a);a=scaler.transform(a)
        model=LogisticRegression(C=float(param),class_weight=weight,max_iter=2000,random_state=42)
        model.fit(a,reference.occupancy_rate.lt(.1))
    else:
        raise ValueError(candidate)
    return dict(model=model,median=median,scaler=scaler,reference=reference,
                selected=list(candidate),features=list(median.index))


def predict_bundle(bundle,query):
    x=V7.features(bundle['reference'],query).fillna(bundle['median'])
    if bundle['scaler'] is not None:x=bundle['scaler'].transform(x)
    return V9.probabilities(bundle['model'],x)


def choose(train,valid):
    y=valid.occupancy_rate.lt(.1).to_numpy(dtype=bool)
    trials=[]
    for index,candidate in enumerate(candidates()):
        p=fit_predict(train,valid,candidate)
        ap=float(average_precision_score(y,p))
        brier=float(np.mean((y-p)**2))
        trials.append(dict(candidate=list(candidate),average_precision=ap,brier=brier,grid_index=index))
    best=max(trials,key=lambda r:(r['average_precision'],-r['brier'],-r['grid_index']))
    return tuple(best['candidate']),trials


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    d=R.load();weeks=sorted(map(int,d.week.unique()))
    report=dict(protocol=dict(name='v10 validation-selected classifier family and class weighting',
        status='Exploratory retrospective evaluation; no independent holdout',
        model_selection='Choose among fixed LightGBM class weights, random/extra trees, and class-weighted logistic regression by validation average precision; Brier breaks ties.',
        threshold='Reuse V9 prequential two-week calibration; fixed precision>=0.65 and at least 20 pooled alerts; choose maximum calibration recall.',
        target='Observed peak occupancy_rate<0.10; not empty, cancellation, or availability.',
        test_weeks=WEEKS,limitations=['All weeks have been inspected','Single validation week per outer fold makes model selection noisy',
            'Calibration precision does not guarantee future precision','No campus transfer or operational truth']),rolling={})
    frames=[]
    for test_week in WEEKS:
        wi=weeks.index(test_week);validation_week=weeks[wi-3];calibration_weeks=weeks[wi-2:wi]
        train=d[d.week<validation_week];valid=d[d.week==validation_week]
        selected,trials=choose(train,valid)
        cal_parts=[];cal_probs=[]
        for cw in calibration_weeks:
            target=d[d.week==cw];fit=d[d.week<cw]
            cal_probs.extend(fit_predict(fit,target,selected).tolist());cal_parts.append(target)
        cal=pd.concat(cal_parts);cal_y=cal.occupancy_rate.lt(.1).to_numpy(dtype=bool)
        threshold,scan,policy=V9.threshold_scan(cal_y,np.asarray(cal_probs))
        test=d[d.week==test_week];final=d[d.week<test_week]
        test_prob=fit_predict(final,test,selected)
        met=R.binary_metrics(test.occupancy_rate.lt(.1),test_prob>=threshold['threshold'])
        frame=test[['session_id','date','room','course_id','week','occupancy_rate']].copy()
        frame['low_probability']=test_prob;frame['threshold']=threshold['threshold'];frame['low_alert']=test_prob>=threshold['threshold']
        frames.append(frame)
        report['rolling'][str(test_week)]=dict(validation_week=int(validation_week),calibration_weeks=list(map(int,calibration_weeks)),
            selected_candidate=list(selected),validation_trials=trials,calibration_sessions=len(cal),
            calibration_policy=policy,threshold=threshold['threshold'],calibration_metrics={k:threshold[k] for k in ['precision','recall','f1','predicted_positive','actual_positive']},
            test_metrics=met)
        print('week',test_week,'candidate',selected,'threshold',threshold['threshold'],
              'test P',round(met['precision'],4),'R',round(met['recall'],4),'F1',round(met['f1'],4),flush=True)
    pred=pd.concat(frames,ignore_index=True);pred.to_csv(OUT/'rolling_predictions.csv',index=False)
    pooled=R.binary_metrics(pred.occupancy_rate.lt(.1),pred.low_alert)
    v7=json.loads((OUT.parent/'improvement_v7/report.json').read_text(encoding='utf-8'))['pooled_low']
    report['pooled_test_metrics']=pooled
    report['comparison']={'v7_pooled':v7,'v9_pooled':json.loads((OUT.parent/'improvement_v9/report.json').read_text(encoding='utf-8'))['pooled_test_metrics'],
        'v10_pooled':pooled,'week12_pass':bool(report['rolling']['12']['test_metrics']['f1']>=.6 or report['rolling']['12']['test_metrics']['precision']>=.65),
        'pooled_pass':bool(pooled['f1']>=.6 or pooled['precision']>=.65)}
    report['sha256']={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),Path(V7.__file__),Path(V9.__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'rolling_predictions.csv']}
    R.dump(OUT/'protocol.json',report['protocol']);R.dump(OUT/'report.json',report)
    print('SUMMARY',report['comparison'],flush=True)
    return report


if __name__=='__main__':run()
