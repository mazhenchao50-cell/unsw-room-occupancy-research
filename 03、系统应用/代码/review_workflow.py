"""Model-supported historical review queue; never a room-release decision."""
import json
import numpy as np
import pandas as pd


def review_queue(sessions,predictions,day):
    required={'session_id','prediction','prediction_route','low_probability','context_probability','model_alert','context_alert','calendar_review','low_alert'}
    if not required<=set(predictions):raise ValueError('Incomplete formal predictions')
    if not predictions.session_id.is_unique:raise ValueError('Duplicate predictions')
    query=sessions[pd.to_datetime(sessions.date).eq(pd.Timestamp(day))]
    frame=query.merge(predictions,on='session_id',validate='one_to_one',how='left',indicator=True)
    if not frame['_merge'].eq('both').all():raise ValueError('Missing prediction for a selected session')
    if frame.low_alert.isna().any():raise ValueError('Missing review decision')
    frame['review_rank_score']=frame[['low_probability','context_probability']].max(axis=1)
    return frame.drop(columns='_merge').sort_values(['low_alert','review_rank_score','course_start','room'],
        ascending=[False,False,True,True],na_position='last').reset_index(drop=True)


def classifier_evidence(bundle,query):
    from models import stable_low as L
    low=bundle['low'];x=L.features(low['reference'],query).fillna(low['median'])
    logistic=low['logistic'].predict_proba(low['scaler'].transform(x))[:,1]
    trees=low['trees'].predict_proba(x)[:,1]
    return pd.DataFrame(dict(session_id=query.session_id.to_numpy(),logistic_score=logistic,tree_score=trees,
        ensemble_score=(logistic+trees)/2,course_recent_mean3=x.course_recent_mean3.to_numpy(),
        course_recent_low3=x.course_recent_low3.to_numpy(),course_seen=x.course_seen.astype(bool).to_numpy()))


def explain_classifier(bundle,query,expected_score):
    """Reconstruct both binary logits, then the actual mean probability score."""
    from models import stable_low as L
    if len(query)!=1:raise ValueError('Exactly one class is required')
    low=bundle['low'];query=query.copy();query['date']=pd.to_datetime(query.date,errors='coerce')
    actual=L.predict_bundle(low,query)['probability'][0]
    x=L.features(low['reference'],query).fillna(low['median'])
    z=low['scaler'].transform(x)
    logistic_contributions=z[0]*low['logistic'].coef_[0]
    logistic_base=float(low['logistic'].intercept_[0])
    tree_contributions=np.asarray(low['trees'].predict(x,pred_contrib=True),dtype=float)
    if tree_contributions.shape!=(1,len(x.columns)+1):raise ValueError('Classifier contribution shape')
    raw_logistic=float(low['logistic'].decision_function(z)[0])
    raw_tree=float(np.asarray(low['trees'].predict(x,raw_score=True))[0])
    reconstructed=np.array([logistic_base+logistic_contributions.sum(),tree_contributions.sum()])
    np.testing.assert_allclose(reconstructed,[raw_logistic,raw_tree],atol=1e-7,rtol=0)
    # Stable sigmoid; logit contributions are never added as probability points.
    scores=np.exp(-np.logaddexp(0,-reconstructed));ensemble=float(scores.mean())
    if not np.isfinite(expected_score) or not np.isclose(ensemble,expected_score,atol=1e-7,rtol=0) or not np.isclose(ensemble,actual,atol=1e-7,rtol=0):
        raise ValueError('Classifier explanation differs from displayed score')
    table=pd.DataFrame(dict(feature=x.columns,value=x.iloc[0].to_numpy(),logistic_log_odds=logistic_contributions,tree_log_odds=tree_contributions[0,:-1]))
    rank=np.abs(table.logistic_log_odds)+np.abs(table.tree_log_odds)
    table=table.iloc[np.argsort(-rank.to_numpy(),kind='stable')].reset_index(drop=True)
    return dict(session_id=str(query.session_id.iloc[0]),logistic_base=logistic_base,tree_base=float(tree_contributions[0,-1]),
        logistic_score=float(scores[0]),tree_score=float(scores[1]),ensemble_score=ensemble,threshold=float(low['threshold']),
        calendar_review=bool(L.C.review_flag(query)[0]),units='Component log-odds, not percentage points; sigmoid each reconstructed component then average',table=table)


# Features a reviewer can read directly (2026-11-24, heuristic review F2). Log transforms, indicators and
# weekday codes stay in the technical table only.
PLAIN_FEATURES={'percent':('course_hist_mean','course_last_rate','course_recent_mean3','course_recent_low3','course_recent_mean5',
    'course_recent_low5','course_room_last','course_room_mean3','course_room_low3','room_recent_low','global_recent_low',
    'low_use_history','enrollment_pressure','attendance_factor_history'),
    'points':('course_trend3','course_last_delta'),'count':('course_hist_n','seats','enrollments','doors'),
    'days':('days_since_course',),'clock':('course_start_h',),'hours':('duration_h',)}
PLAIN_KIND={name:kind for kind,names in PLAIN_FEATURES.items() for name in names}


def plain_reasons(table,flagged,limit=3):
    """Top readable features pushing the classifier towards its own decision (log-odds of both components summed)."""
    t=pd.DataFrame(table);combined=t.logistic_log_odds+t.tree_log_odds
    t=t.assign(combined=combined,kind=t.feature.map(PLAIN_KIND))
    t=t[t.kind.notna()&(t.combined.gt(0) if flagged else t.combined.lt(0))]
    t=t.iloc[np.argsort(-t.combined.abs().to_numpy(),kind='stable')].head(limit)
    return [dict(feature=r.feature,value=float(r.value),kind=r.kind) for r in t.itertuples()]


def forest_path_contributions(model,values):
    """Mean class-probability changes along actual decision paths, not SHAP."""
    x=np.asarray(values,dtype=np.float32).reshape(-1);result=np.zeros(len(x));base=0.
    positive=int(np.flatnonzero(model.classes_==True)[0])
    for estimator in model.estimators_:
        tree=estimator.tree_;node=0
        def prob(index):
            counts=tree.value[index,0];return float(counts[positive]/counts.sum())
        previous=prob(0);base+=previous
        while tree.feature[node]>=0:
            feature=tree.feature[node];child=tree.children_left[node] if x[feature]<=tree.threshold[node] else tree.children_right[node]
            current=prob(child);result[feature]+=current-previous;node=child;previous=current
    return base/len(model.estimators_),result/len(model.estimators_)


def explain_context(bundle,query,expected_score):
    from models import context_low as C
    if len(query)!=1:raise ValueError('Exactly one class is required')
    context=bundle['context'];actual=C.predict_components(context,query)
    x=C.features(context['reference'],query).fillna(context['median']);z=context['scaler'].transform(x)
    logistic_base=float(context['logistic'].intercept_[0]);logistic=z[0]*context['logistic'].coef_[0]
    trees=np.asarray(context['trees'].predict(x,pred_contrib=True))[0]
    forest_base,forest=forest_path_contributions(context['forest'],x.iloc[0].to_numpy())
    scores=np.array([float(np.exp(-np.logaddexp(0,-(logistic_base+logistic.sum())))),
        float(np.exp(-np.logaddexp(0,-trees.sum()))),forest_base+forest.sum()])
    np.testing.assert_allclose(scores,[actual[name][0] for name in ('logistic','trees','forest')],atol=1e-7,rtol=0)
    score=float(np.median(scores))
    if not np.isfinite(expected_score) or not np.isclose(score,expected_score,atol=1e-7,rtol=0):raise ValueError('Context explanation differs from displayed score')
    table=pd.DataFrame(dict(feature=x.columns,value=x.iloc[0].to_numpy(),logistic_log_odds=logistic,tree_log_odds=trees[:-1],forest_probability_points=100*forest))
    return dict(session_id=str(query.session_id.iloc[0]),logistic_base=logistic_base,tree_base=float(trees[-1]),forest_base=float(forest_base),
        logistic_score=float(scores[0]),tree_score=float(scores[1]),forest_score=float(scores[2]),context_score=score,threshold=.5,
        units='Logistic/tree: log-odds; forest: probability points along decision paths, not SHAP; median of reconstructed component scores',table=table)


def export_review(row,model_fingerprint,disposition,note,explanation=None,context_explanation=None):
    """A user-authored historical annotation, explicitly not occupancy/access evidence."""
    if disposition not in ('pending','historical_label_checked','suspected_false_alert'):raise ValueError('Unknown review action')
    return json.dumps(dict(schema=2,scope='UNSW historical desk review; no real-time access or cancellation authority',
        session_id=str(row.session_id),model_fingerprint=model_fingerprint,
        prediction=float(row.prediction),low_score=float(row.low_probability),
        context_score=float(row.context_probability),model_alert=bool(row.model_alert),context_alert=bool(row.context_alert),calendar_review=bool(row.calendar_review),
        disposition=disposition,note=note,reviewer_identity='not independently authenticated',
        automatic_release=False,classifier_explanation=explanation,context_explanation=context_explanation),ensure_ascii=False,indent=2,allow_nan=False)
