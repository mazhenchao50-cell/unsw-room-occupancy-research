"""Separate real-data occupancy detection benchmark, never main-model transfer."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import urllib.request
import zipfile
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import revised as R

RAW=R.ROOT/'01、数据处理/原始数据/UCI'
OUT=R.ROOT/'02、模型实验/生成产物/external_uci'
URL='https://archive.ics.uci.edu/static/public/357/occupancy%2Bdetection.zip'
PAGE='https://archive.ics.uci.edu/dataset/357/occupancy%2Bdetection'
FEATURES=['Temperature','Humidity','Light','CO2','HumidityRatio']
PROTOCOL={'task':'Current office occupancy detection using contemporaneous sensors, not forecasting.',
          'train':'datatraining.txt', 'test':'datatest2.txt',
          'excluded':'datatest.txt predates training and is not used for fitting, tuning or scores.',
          'features':FEATURES,'model':'StandardScaler + LogisticRegression(C=1, max_iter=2000, random_state=42)',
          'threshold':0.5, 'selection':'Fixed parameters, no test-driven search.',
          'positive_label':'Empty room = Occupancy == 0',
          'scope':'Separate office model. No UNSW, new-campus, timetable/access or human-usability validation.'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch():
    RAW.mkdir(parents=True,exist_ok=True)
    for url,name in [(URL,'occupancy_detection.zip'),(PAGE,'source.html')]:
        request=urllib.request.Request(url,headers={'User-Agent':'CampusResearch/1.0'})
        with urllib.request.urlopen(request,timeout=45) as response:
            data=response.read(5_000_001)
        if len(data)>5_000_000:
            raise ValueError('Unexpectedly large source response')
        (RAW/name).write_bytes(data)

def load_parts():
    parts={}
    with zipfile.ZipFile(RAW/'occupancy_detection.zip') as archive:
        for name in ['datatraining.txt','datatest.txt','datatest2.txt']:
            payload=archive.read(name)
            d=pd.read_csv(io.BytesIO(payload)).reset_index(drop=True)
            d['date']=pd.to_datetime(d.date)
            if d[FEATURES+['Occupancy','date']].isna().any().any():
                raise ValueError('Unexpected missing input values')
            if not np.isfinite(d[FEATURES].to_numpy()).all() or not set(d.Occupancy.unique())<={0,1}:
                raise ValueError('Invalid features or labels')
            if not d.date.is_unique:
                raise ValueError('Duplicate timestamps in source segment')
            parts[name]=(d,hashlib.sha256(payload).hexdigest())
    return parts

def fit_predict(train,test):
    if train.date.max()>=test.date.min():
        raise ValueError('Test must be strictly later than training')
    model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,random_state=42))
    model.fit(train[FEATURES],train.Occupancy)
    probability=model.predict_proba(test[FEATURES])[:,1]
    majority=np.full(len(test),int(train.Occupancy.mode().iloc[0]))
    return model,probability,majority

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    R.dump(OUT/'protocol.json',PROTOCOL)
    parts=load_parts()
    train=parts[PROTOCOL['train']][0];test=parts[PROTOCOL['test']][0]
    _,probability,majority=fit_predict(train,test)
    scores={}
    for name,pred in [('logistic_regression',(probability>=.5).astype(int)),('training_majority',majority)]:
        scores[name]={'accuracy':float(accuracy_score(test.Occupancy,pred)),
                      'empty_detection':R.binary_metrics(test.Occupancy.eq(0),pred==0),
                      'occupied_detection':R.binary_metrics(test.Occupancy.eq(1),pred==1),
                      'per_date':{str(day):R.binary_metrics(group.Occupancy.eq(0),pred[group.index]==0)
                                  for day,group in test.groupby(test.date.dt.date)}}
    frame=test[['date','Occupancy']].copy()
    frame['occupied_probability']=probability
    frame['predicted_occupancy']=(probability>=.5).astype(int)
    frame['majority_occupancy']=majority
    frame.to_csv(OUT/'test_predictions.csv',index=False)
    manifest={'dataset':'Occupancy Detection','creator':'Luis Candanedo','year':2016,
              'doi':'10.24432/C5X01N','source_url':PAGE,'download_url':URL,
              'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
              'license_evidence':'Saved official source.html; does not apply to the UNSW dataset.',
              'local_archive_mtime_utc':datetime.fromtimestamp((RAW/'occupancy_detection.zip').stat().st_mtime,timezone.utc).isoformat(),
              'timestamp_basis':'Local downloaded archive modification time, not the original publisher creation time.',
              'audited_at_utc':datetime.now(timezone.utc).isoformat(),
              'changes':'Original ZIP retained; parse timestamps, standardize training features, fit separate classifier.',
              'files':{name:{'rows':len(d),'sha256':digest,'start':str(d.date.min()),'end':str(d.date.max())}
                       for name,(d,digest) in parts.items()},
              'zip_sha256':sha(RAW/'occupancy_detection.zip'),'source_html_sha256':sha(RAW/'source.html')}
    # Verify that the saved official page actually contains the cited license link.
    if 'creativecommons.org/licenses/by/4.0' not in (RAW/'source.html').read_text(encoding='utf-8'):
        raise ValueError('License evidence missing from saved source page')
    R.dump(RAW/'manifest.json',manifest)
    report={'protocol':PROTOCOL,'train_n':len(train),'test_n':len(test),
            'total_source_n':sum(len(d) for d,_ in parts.values()),'models':scores,
            'data_manifest':'01、数据处理/原始数据/UCI/manifest.json',
            'limitations':['One office, temporally correlated minute observations.',
                          'Sensors are observed at prediction time; not a future prediction.',
                          'Empty-room precision here does not validate scheduled no-show or access permission.',
                          'No human trial records or local-campus measurements are generated.'],
            'python':platform.python_version(),
            'versions':{k:importlib.metadata.version(k) for k in ['pandas','numpy','scikit-learn']},
            'sha256':{str(p.relative_to(R.ROOT)):sha(p) for p in [Path(__file__),Path(R.__file__),
                       OUT/'protocol.json',RAW/'occupancy_detection.zip',RAW/'source.html',OUT/'test_predictions.csv']}}
    R.dump(OUT/'report.json',report)
    print(json.dumps({'train_n':len(train),'test_n':len(test),'models':scores},ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true')
    if parser.parse_args().download: fetch()
    run()
