"""Retrospective rolling calibration of low-utilization alerts, not zero occupancy."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import revised as R

PROTOCOL={
 'test_weeks':[8,10,11,12], 'model':'LightGBM only; existing revised.py grid',
 'target':'occupancy_rate < 0.10; not observed zero or actual room availability',
 'thresholds':[.05,.08,.10,.12,.15,.18,.20,.25,.30],
 'selection':'Model setting: preceding validation RMSE. Threshold: preceding calibration F1, then precision, then smaller threshold. No-positive calibration: no alerts.',
 'fit':'Fit on train plus validation; exclude calibration and test labels from training and history.',
 'comparison':'Same fold and same regression predictions, calibrated threshold versus fixed 0.10.',
 'diagnostic_gate':'Pooled F1 >= 0.60 and greater than fixed; F1 improves in at least 3 of 4 folds; pooled precision falls by no more than 0.05.',
 'scope':'All weeks were inspected in earlier research. Retrospective robustness diagnostic, not a new blind test or deployment approval.',
 'default_model_changed':False}

def split_fold(data,week):
    weeks=sorted(data.week.unique());index=weeks.index(week)
    if index<3:raise ValueError('Need training, validation, calibration and test periods')
    valid_week,cal_week=weeks[index-2:index]
    train=data[data.week<valid_week];valid=data[data.week.eq(valid_week)]
    cal=data[data.week.eq(cal_week)];test=data[data.week.eq(week)]
    parts=[train,valid,cal,test]
    if any(p.empty for p in parts) or any(a.date.max()>=b.date.min() for a,b in zip(parts,parts[1:])):
        raise ValueError('Chronology violation')
    if not pd.concat(parts).session_id.is_unique:raise ValueError('Overlapping session identifiers')
    return parts

def choose_threshold(labels,predictions):
    y=np.asarray(labels,dtype=bool);p=np.asarray(predictions,dtype=float)
    if y.ndim!=1 or p.shape!=y.shape or len(y)==0 or not np.isfinite(p).all():
        raise ValueError('Calibration labels and finite predictions must align')
    if not y.any():return 0.,[]
    scan=[{'threshold':t,**R.binary_metrics(y,p<t)} for t in PROTOCOL['thresholds']]
    best=max(scan,key=lambda r:(r['f1'],r['precision'],-r['threshold']))
    return best['threshold'],scan

def run():
    out=R.ROOT/'02、模型实验/生成产物/improvement_v6';out.mkdir(parents=True,exist_ok=True)
    R.dump(out/'protocol.json',PROTOCOL)
    data=R.load();folds={};frames=[]
    for week in PROTOCOL['test_weeks']:
        train,valid,cal,test=split_fold(data,week)
        final=pd.concat([train,valid]).sort_values('date')
        cp,bundle,trials=R.fit_selected('LightGBM',train,valid,final,cal)
        threshold,scan=choose_threshold(cal.occupancy_rate.to_numpy()<.1,cp)
        tp=R.predict(bundle,test)
        f=R.prediction_frame(test,tp);f['fixed_alert']=tp<.1;f['calibrated_alert']=tp<threshold;f['threshold']=threshold
        frames.append(f);y=test.occupancy_rate.to_numpy()<.1
        folds[str(week)]={'validation_week':int(valid.week.iloc[0]),'calibration_week':int(cal.week.iloc[0]),
            'counts':[len(p) for p in (train,valid,cal,test)],'threshold':threshold,'model_setting':bundle['setting'],
            'model_trials':trials,'calibration_scan':scan,'fixed':R.binary_metrics(y,tp<.1),'calibrated':R.binary_metrics(y,tp<threshold)}
        print('week',week,'threshold',threshold,'fixed F1',folds[str(week)]['fixed']['f1'],'calibrated F1',folds[str(week)]['calibrated']['f1'],flush=True)
    all_rows=pd.concat(frames);assert all_rows.session_id.is_unique
    all_rows.to_csv(out/'predictions.csv',index=False)
    y=all_rows.occupancy_rate.to_numpy()<.1
    fixed=R.binary_metrics(y,all_rows.fixed_alert);new=R.binary_metrics(y,all_rows.calibrated_alert)
    improved=sum(f['calibrated']['f1']>f['fixed']['f1'] for f in folds.values())
    gate=bool(new['f1']>=.6 and new['f1']>fixed['f1'] and improved>=3 and new['precision']>=fixed['precision']-.05)
    report={'protocol':PROTOCOL,'folds':folds,'pooled':{'fixed':fixed,'calibrated':new},'improved_folds':improved,
        'diagnostic_gate_passed':gate,'default_model_changed':False,
        'source_sha256':{str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',out/'protocol.json']}}
    R.dump(out/'report.json',report)
    print('POOLED',json.dumps(report['pooled']),'diagnostic gate',gate,flush=True)
    return report

if __name__=='__main__':run()
