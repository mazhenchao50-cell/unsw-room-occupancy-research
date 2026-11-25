"""Paired retrospective risk review of fixed predictions; never tunes or adopts a model."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import revised as R

WEEKS=(8,10,11,12)
MODELS=('LightGBM','RF','SVR','MLR','Unified')
OUT=R.ROOT/'02、模型实验/生成产物/risk_review'


def align(frame,truth):
    """Reject incomplete or inconsistent evidence before calculating a comparison."""
    required=['session_id','date','room','course_id','week','occupancy_rate','prediction','low_alert']
    if not set(required)<=set(frame):raise ValueError('Missing prediction fields')
    if frame.session_id.isna().any() or not frame.session_id.is_unique:raise ValueError('Duplicate or missing session')
    if set(frame.session_id)!=set(truth.session_id):raise ValueError('Session coverage differs')
    f=frame.set_index('session_id').loc[truth.session_id].reset_index()
    if not np.isfinite(f[['occupancy_rate','prediction']].to_numpy(float)).all() or (f.prediction<0).any():
        raise ValueError('Nonfinite or negative prediction')
    for name in ['room','course_id','week']:
        if not np.array_equal(f[name].to_numpy(),truth[name].to_numpy()):raise ValueError('Metadata differs: '+name)
    if not np.array_equal(pd.to_datetime(f.date).to_numpy(),pd.to_datetime(truth.date).to_numpy()):raise ValueError('Dates differ')
    if not np.allclose(f.occupancy_rate,truth.occupancy_rate,rtol=0,atol=1e-12):raise ValueError('Targets differ')
    if not pd.api.types.is_bool_dtype(f.low_alert.dtype):raise ValueError('Alert must be an explicit boolean')
    return f


def cost(low,fp_weight):
    """Illustrative review burden, not measured operational loss."""
    _,fp,fn,_=low['confusion_tn_fp_fn_tp']
    return float(fp_weight*fp+fn)


def summary(f):
    def part(g):
        return dict(n=len(g),rmse=float(np.sqrt(np.mean((g.prediction-g.occupancy_rate)**2))),
                    low=R.binary_metrics(g.occupancy_rate<.1,g.low_alert))
    weekly={str(w):part(f[f.week.eq(w)]) for w in WEEKS}
    pooled=part(f)
    return dict(pooled=pooled,weekly=weekly,mean_week_rmse=float(np.mean([v['rmse'] for v in weekly.values()])),
                worst_week_rmse=max(v['rmse'] for v in weekly.values()),
                per_room={str(room):part(g) for room,g in f.groupby('room')},
                low_numeric_pass_weeks=sum(v['low']['f1']>=.6 or v['low']['precision']>=.65 for v in weekly.values()))


def paired_course_interval(base,candidate,replicates=2000):
    """Same course draw for both models, retaining its repeated weeks/sessions."""
    if not np.array_equal(base.session_id.to_numpy(),candidate.session_id.to_numpy()):raise ValueError('Unaligned pair')
    a=base.assign(base_error=(base.prediction-base.occupancy_rate)**2,
                  candidate_error=(candidate.prediction-candidate.occupancy_rate)**2)
    groups=a.groupby('course_id').agg(n=('session_id','size'),a=('base_error','sum'),b=('candidate_error','sum'))
    rng=np.random.default_rng(42);k=len(groups)
    draws=rng.multinomial(k,np.full(k,1/k),size=replicates)
    denominator=draws@groups.n.to_numpy()
    differences=np.sqrt((draws@groups.b.to_numpy())/denominator)-np.sqrt((draws@groups.a.to_numpy())/denominator)
    return dict(candidate_minus_LightGBM_rmse_95=np.quantile(differences,[.025,.975]).tolist(),
                course_clusters=k,replicates=replicates,
                note='Conditional fixed-prediction course bootstrap, not independent new-week evidence; shared calendar shocks and model-selection uncertainty are not covered.')


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    protocol=dict(version='risk_review_v1',weeks=list(WEEKS),models=list(MODELS),
        target='peak attendees / seats; low utilization <0.1',
        selection='Existing fixed predictions only. No new settings, threshold search, per-test-week winner switching or model adoption.',
        comparison='Same session IDs, dates, rooms, courses and labels required; missing rows are errors, never silently dropped.',
        uncertainty='Paired course-cluster bootstrap with 2000 draws; leave-one-week-out sensitivity separately.',
        illustrative_fp_costs=[1,2,5,10],
        scope='Known-room historical weeks only; cannot inherit spatial scores or establish new-campus performance.')
    R.dump(OUT/'protocol.json',protocol)
    truth=R.load();truth=truth[truth.week.isin(WEEKS)].reset_index(drop=True)
    frames={};sources=[Path(__file__),Path(R.__file__),R.ROOT/'01、数据处理/清洗产物/sessions.csv',OUT/'protocol.json']
    for model in MODELS:
        if model=='Unified':
            path=R.ROOT/'02、模型实验/生成产物/unified/time_predictions.csv';sources.append(path)
            f=pd.read_csv(path)
            if not f.prediction_route.eq('known').all():raise ValueError('Unexpected cold route in known-room review')
        else:
            paths=[R.ROOT/f'02、模型实验/生成产物/revised/week{w}_{model}.csv' for w in WEEKS]
            sources.extend(paths);f=pd.concat([pd.read_csv(p) for p in paths],ignore_index=True)
            f['low_alert']=f.prediction<.1
        frames[model]=align(f,truth)
    base=frames['LightGBM'];reports={name:summary(f) for name,f in frames.items()}
    for name,f in frames.items():
        item=reports[name]
        item['weeks_better_rmse_than_LightGBM']=sum(item['weekly'][str(w)]['rmse']<reports['LightGBM']['weekly'][str(w)]['rmse']-1e-12 for w in WEEKS)
        item['paired_uncertainty']=paired_course_interval(base,f)
        item['leave_one_week_out']={str(w):dict(
            rmse=float(np.sqrt(np.mean((f.loc[f.week.ne(w),'prediction']-f.loc[f.week.ne(w),'occupancy_rate'])**2))),
            candidate_minus_LightGBM_rmse=float(np.sqrt(np.mean((f.loc[f.week.ne(w),'prediction']-f.loc[f.week.ne(w),'occupancy_rate'])**2))-
                np.sqrt(np.mean((base.loc[base.week.ne(w),'prediction']-base.loc[base.week.ne(w),'occupancy_rate'])**2)))) for w in WEEKS}
    scenarios=[]
    for weight in protocol['illustrative_fp_costs']:
        costs={n:cost(s['pooled']['low'],weight) for n,s in reports.items()}
        scenarios.append(dict(false_positive_cost_over_false_negative=weight,costs=costs,
            minimum_cost_models=[n for n,c in costs.items() if c==min(costs.values())]))
    aligned=pd.concat([f.assign(model=name) for name,f in frames.items()],ignore_index=True)
    aligned.to_csv(OUT/'aligned_predictions.csv',index=False)
    sources.append(OUT/'aligned_predictions.csv')
    report=dict(protocol=protocol,n=len(truth),models=reports,cost_scenarios=scenarios,
        adoption=dict(default_changed=False,unified_changed=False,decision='Retain both modes; review RF as a candidate, not an adopted replacement.',
            reasons=['Only four previously inspected weeks; no algorithm wins every week.',
                     'Precision, recall and false-alert burden trade off; example costs are not measured user preferences.',
                     'Warm-model changes require their own routed random comparator, explanation and end-to-end validation.']),
        allowed_uses=['Historical method comparison','Manual review of low-utilization signals'],
        unsupported_uses=['Automatic room release or cancellation','Claim of actual vacancy or permission',
                          'Unseen-room low-alert precision inherited from known rooms','New-campus or future accuracy guarantee'],
        sha256={str(p.relative_to(R.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    R.dump(OUT/'report.json',report)
    for name,s in reports.items():print(name,round(s['pooled']['rmse'],5),s['pooled']['low']['confusion_tn_fp_fn_tp'],flush=True)
    return report


if __name__=='__main__':run()
