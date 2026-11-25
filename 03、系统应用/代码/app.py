from pathlib import Path
from datetime import time as default_time
import json
import hashlib
import sys
PROJECT_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT/'02、模型实验/代码'))
sys.path.insert(0,str(PROJECT_ROOT/'03、系统应用/代码'))
import streamlit as st
import pandas as pd
import joblib
from replay import candidates,replay_predictions,load_slot_history,LISTED
from query_support import EMPTY_PREDICTIONS,next_gap,query_summary,brief,basis
from local_explanation import explain_session
from serving_policy import initial_mode
from models.revised import ROOT
from review_workflow import review_queue,classifier_evidence,explain_classifier,explain_context,export_review,plain_reasons
from i18n import LANGUAGES,TEXT,t,room_display,active_display,routed_display,shap_display,queue_display,plain_summary,flag_text,review_text

st.set_page_config(page_title='Campus Room Replay',layout='wide')
locale=st.sidebar.selectbox('Language / 언어 / 语言 / 言語',list(LANGUAGES),format_func=LANGUAGES.get,key='locale')
tr=lambda key:t(locale,key)
st.set_page_config(page_title=tr('title'),layout='wide')   # heuristic review F11: localized browser tab title
show_research=st.sidebar.toggle(tr('research_toggle'),value=False,key='show_research')
st.title(tr('title'))
st.caption(tr('intro'))

def available(names):
    return all((ROOT/name).is_file() and (ROOT/name).stat().st_size for name in names)

data_paths=['01、数据处理/清洗产物/sessions.csv','01、数据处理/清洗产物/attendance_clean.csv']
sensor_path='01、数据处理/清洗产物/clean_computed.csv'
if not available(data_paths+[sensor_path]):
    st.error(tr('setup_required'));st.stop()

@st.cache_data(show_spinner=False)
def data_resources(root,stamps):
    return tuple(pd.read_csv(Path(root)/p) for p in data_paths)

@st.cache_data(show_spinner=False)
def slot_resources(root,stamp):
    # Experiment-19 labels of unscheduled weekday room-hours; the rule reads strictly earlier days only.
    return load_slot_history(Path(root))

@st.cache_resource
def model_resources(root,stamps):
    folder=Path(root)/'02、模型实验/生成产物/revised'
    return joblib.load(folder/'model.joblib'),joblib.load(folder/'no_show.joblib')


def formal_fingerprint():
    from models.unified import required_artifacts
    names=sorted(required_artifacts()|{'02、模型实验/生成产物/unified/report.json'})
    return hashlib.sha256(''.join(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names).encode()).hexdigest()


@st.cache_resource(show_spinner=False)
def formal_resources(root,fingerprint,week):
    from models.unified import load_verified,predict_bundle
    _,report=load_verified(Path(root))
    bundle=joblib.load(Path(root)/f'02、模型实验/生成产物/unified/fold_models/rolling_{week}.joblib')
    source=pd.read_csv(Path(root)/'01、数据处理/清洗产物/sessions.csv')
    prediction=predict_bundle(bundle,source[source.week.eq(week)])
    return bundle,report,prediction


def read_report(path,required):
    try:
        report=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(report,dict) or not set(required)<=set(report):raise ValueError('Invalid report schema')
        return report
    except (ValueError,OSError,TypeError):
        st.info(tr('optional_invalid'));return None

with st.spinner(tr('loading')):   # heuristic review F14
    s,a=data_resources(str(ROOT),tuple((ROOT/p).stat().st_mtime_ns for p in data_paths))
    slots=slot_resources(str(ROOT),(ROOT/sensor_path).stat().st_mtime_ns)
st.subheader(tr('needs_title'))
inputs=st.columns([1.5,1,1,1])
dates=sorted(s.loc[s.week.isin([8,10,11,12]),'date'].unique())
from models.calendar_context import STATEWIDE_PUBLIC_HOLIDAYS
week_of=s.drop_duplicates('date').set_index('date').week
def date_label(value):   # heuristic review F9
    stamp=pd.Timestamp(value)
    text=tr('date_label').format(date=value,weekday=tr(f'weekday_{stamp.weekday()}'),week=int(week_of[value]))
    return text+(tr('holiday_mark') if value in STATEWIDE_PUBLIC_HOLIDAYS else '')
with inputs[0]:day=st.selectbox(tr('date'),dates,key='historical_date',format_func=date_label)
# Heuristic review F4: a 15-minute dropdown cannot show an uncommitted typed time (same step as the later-start search).
TIMES=[default_time(m//60,m%60) for m in range(0,24*60,15)]
if st.session_state.get('start_time') not in TIMES:
    st.session_state['start_time']=default_time(9,0)
with inputs[1]:start=st.selectbox(tr('start'),TIMES,key='start_time',format_func=lambda value:value.strftime('%H:%M'))
with inputs[2]:minutes=st.number_input(tr('duration'),min_value=15,max_value=240,value=60,step=15,key='duration')
with inputs[3]:capacity=st.number_input(tr('capacity'),min_value=1,max_value=497,value=10,key='capacity')
st.caption(tr('time_basis'))
# Heuristic review F3: an interval crossing midnight only blocks the candidate search, never the class review queue.
valid_interval=start.hour*60+start.minute+minutes<=24*60
selected_week=int(s.loc[s.date.eq(day),'week'].iloc[0])
st.subheader(tr('review_title'))
st.write(tr('review_scope'))
try:
    fingerprint=formal_fingerprint()
    with st.spinner(tr('loading')):
        formal_bundle,formal_report,formal_predictions=formal_resources(str(ROOT),fingerprint,selected_week)
    queue=review_queue(s,formal_predictions,day)
except (ValueError,OSError,KeyError,TypeError,EOFError,AssertionError):
    formal_bundle=None
    st.error(tr('unified_unavailable'))
else:
    # Heuristic review F1: the primary queue shows one readable flag first; all model scores stay one click away.
    st.dataframe(queue_display(queue,locale),hide_index=True,key='review_queue',height='content')
    with st.expander(tr('all_scores')):
        st.dataframe(routed_display(queue,locale),hide_index=True,key='review_scores',height='content')
    review_ids=queue.session_id.tolist();labels=queue.set_index('session_id')
    if st.session_state.get('review_session') not in review_ids:st.session_state['review_session']=None
    selected_review=st.selectbox(tr('review_select'),review_ids,index=None,key='review_session',placeholder=tr('review_placeholder'),
        format_func=lambda key:('⚠ ' if bool(labels.loc[key,'low_alert']) else '')+f"{labels.loc[key,'room']} · {labels.loc[key,'course_id']} · {labels.loc[key,'course_start']}")
    if selected_review:
        selected_query=queue[queue.session_id.eq(selected_review)];row=selected_query.iloc[0]
        evidence=classifier_evidence(formal_bundle,selected_query).drop(columns='session_id')
        for name in ('course_recent_mean3','course_recent_low3'):evidence[name]=evidence[name].map(lambda x:f'{x:.1%}')   # heuristic review F12
        for name in ('logistic_score','tree_score','ensemble_score'):evidence[name]=evidence[name].map(lambda x:f'{x:.2f}')
        evidence['course_seen']=evidence.course_seen.map(lambda x:tr('yes_label') if x else tr('no_label'))
        evidence.columns=[tr(name) for name in evidence.columns]
        st.caption(tr('review_evidence'));st.dataframe(evidence,hide_index=True,key='review_signals')
        explanation=explain_classifier(formal_bundle,selected_query,float(row.low_probability))
        with st.expander(tr('classifier_explain')):
            # Heuristic review F2: plain conclusion and readable reasons before the log-odds reconstruction.
            flagged=explanation['ensemble_score']>=explanation['threshold']
            conclusion=plain_summary(locale,explanation['ensemble_score'],flagged,plain_reasons(explanation['table'],flagged),
                holiday=explanation['calendar_review'],context=bool(row.context_alert))
            st.markdown(conclusion)
            st.caption(tr('plain_scope'))
            st.markdown('**'+tr('technical_details')+'**')
            st.write(tr('classifier_scope'))
            st.caption(tr('classifier_reconstruct').format(logistic=explanation['logistic_score'],tree=explanation['tree_score'],score=explanation['ensemble_score'],threshold=explanation['threshold'],logistic_base=explanation['logistic_base'],tree_base=explanation['tree_base']))
            contributions=explanation['table'].copy()
            contributions['feature']=contributions.feature.map(lambda name:tr(name) if name in TEXT else name)
            contributions.columns=[tr(name) for name in ('feature','local_value','logistic_log_odds','tree_log_odds')]
            st.dataframe(contributions,hide_index=True,key='classifier_contributions',height='content')
        explanation={**explanation,'table':explanation['table'].to_dict('records')}
        context_explanation=explain_context(formal_bundle,selected_query,float(row.context_probability))
        with st.expander(tr('context_explain')):
            st.write(tr('context_scope'))
            st.caption(tr('context_reconstruct').format(**context_explanation))
            contextual=context_explanation['table'].copy()
            contextual['feature']=contextual.feature.map(lambda name:tr(name) if name in TEXT else name)
            contextual.columns=[tr(name) for name in ('feature','local_value','logistic_log_odds','tree_log_odds','forest_probability_points')]
            st.dataframe(contextual,hide_index=True,key='context_contributions',height='content')
        context_explanation={**context_explanation,'table':context_explanation['table'].to_dict('records')}
        action_labels={'pending':'review_pending','historical_label_checked':'review_checked','suspected_false_alert':'review_false'}
        if st.session_state.get('annotated_session')!=selected_review:
            st.session_state['annotated_session']=selected_review
            st.session_state['review_action']='pending';st.session_state['review_note']=''
        action=st.selectbox(tr('review_action'),list(action_labels),format_func=lambda value:tr(action_labels[value]),key='review_action')
        note=st.text_area(tr('review_note'),key='review_note')
        columns=st.columns(2)
        with columns[0]:
            st.download_button(tr('review_download'),export_review(row,fingerprint,action,note,explanation,context_explanation).encode('utf-8'),
                file_name='historical-review.json',mime='application/json',key='download_review')
        with columns[1]:   # heuristic review F10: a text summary a reviewer can read and forward
            st.download_button(tr('review_download_text'),review_text(locale,row,date_label(day),flag_text(row,locale),conclusion,tr(action_labels[action]),note).encode('utf-8-sig'),
                file_name='historical-review.txt',mime='text/plain; charset=utf-8',key='download_review_text')
        st.caption(tr('export_note'))
def apply_later(value):
    st.session_state['start_time']=value
    st.session_state['selected_room']=None


def render_candidates():
    """Heuristic review F5: results or the actionable suggestion first; the rule explanation is folded away."""
    st.subheader(tr('top'))
    if not valid_interval:
        st.error(tr('midnight'));return
    try:
        rooms,top,_=candidates(s,a,EMPTY_PREDICTIONS,day,start,minutes,capacity,slot_history=slots)
    except ValueError:
        st.error(tr('query_error'));return
    st.markdown('**'+tr('active_query').format(summary=query_summary(locale,day,start,minutes,capacity))+'**')
    if top.empty:
        st.warning(tr('empty'))
        later=next_gap(s,a,day,start,minutes,capacity,slot_history=slots)
        if later is not None:
            value=later['start'];label=value.strftime('%H:%M')
            st.success(tr('later_found').format(time=label,count=later['candidates']))
            st.button(tr('try_later').format(time=label),key='try_later',on_click=apply_later,args=(value,),type='primary')
        else:st.caption(tr('no_later'))
    else:
        display=room_display(top,locale)[[tr('room'),tr('seats'),tr('history_rate'),tr('availability')]].copy()
        display.insert(2,tr('spare_seats'),(top.seats-capacity).to_numpy())
        st.dataframe(display,hide_index=True,width='stretch')
        st.caption(tr('ranking'))
    counts=rooms.status.value_counts()
    st.caption(tr('result_counts').format(eligible=len(rooms),gaps=int(sum(counts.get(k,0) for k in LISTED)),
        used=int(counts.get('history_rule_likely_used',0)),conflicts=int(counts.get('scheduled_conflict',0)),unknown=int(counts.get('schedule_unknown',0))))
    with st.expander(tr('rule_expander')):
        st.info(tr('history_rule_scope'))
    with st.expander(tr('filter_details')):
        st.dataframe(room_display(rooms,locale),hide_index=True,width='stretch')
    options=top.room.tolist()
    if st.session_state.get('selected_room') not in options:st.session_state['selected_room']=None
    if options:
        selected=st.selectbox(tr('select_candidate'),options,index=None,placeholder=tr('select_placeholder'),key='selected_room')
        if selected:
            row=top[top.room.eq(selected)].iloc[0]
            st.subheader(tr('next_title'))
            st.write(tr('selected_summary').format(room=selected,seats=int(row.seats),spare=int(row.seats-capacity)))
            st.write(basis(locale,row))
            st.info(tr('next_steps'))
            st.download_button(tr('save_brief'),brief(top,selected,locale,day,start,minutes,capacity).encode('utf-8-sig'),
                file_name='historical-room-checklist.txt',mime='text/plain; charset=utf-8',key='download_brief')


render_candidates()


def render_research():
    st.write(tr('research_separation'))
    names=['02、模型实验/生成产物/revised/'+name for name in ['model.joblib','no_show.joblib','report.json','shap_feature_ranking.csv']]
    unified_available=available(['02、模型实验/生成产物/unified/'+name for name in ['model.joblib','report.json']])
    mode=st.selectbox(tr('prediction_mode'),['current','unified'],index=1 if initial_mode(st.session_state.get('research_model'))=='unified' else 0,
        format_func=lambda value:tr('system_'+value),key='prediction_mode')
    st.session_state['research_model']=mode
    if not valid_interval:   # the interval drives the active-class list; say why instead of reporting a model fault
        st.error(tr('midnight'));return
    try:
        if mode=='unified':
            if formal_bundle is None:st.error(tr('unified_unavailable'));return
            unified,unified_report,display_predictions=formal_bundle,formal_report,formal_predictions
        else:
            if not available(names[:3]):st.info(tr('research_unavailable'));return
            if selected_week!=12:st.info(tr('research_unavailable'));return
            b,ns=model_resources(str(ROOT),tuple((ROOT/p).stat().st_mtime_ns for p in names[:2]))
            display_predictions=replay_predictions(s,b,ns)
        _,_,active=candidates(s,a,display_predictions,day,start,minutes,capacity)
    except (ValueError,OSError,KeyError,EOFError):
        st.error(tr('unified_unavailable') if mode=='unified' else tr('research_unavailable'));return
    st.subheader(tr('unified_title' if mode=='unified' else 'active_title'))
    st.write(tr('unified_scope' if mode=='unified' else 'definitions'))
    st.caption(tr('label_scope'))
    if mode=='unified':
        risk=unified_report['rolling'][str(selected_week)]['low'];tn,fp,fn,tp=risk['confusion_tn_fp_fn_tp']
        st.caption(tr('unified_cutoff').format(date=str(unified['cutoff'].date())))
        st.caption(tr('weekly_metrics'))
        weekly=[]
        for week,result in unified_report['rolling'].items():
            m=result['low'];_,fp_week,fn_week,_=m['confusion_tn_fp_fn_tp']
            weekly.append({tr('week'):int(week),tr('precision'):f"{m['precision']:.1%}",tr('recall'):f"{m['recall']:.1%}",
                           'F1':round(m['f1'],4),tr('fp'):fp_week,tr('fn'):fn_week})
        st.dataframe(pd.DataFrame(weekly),hide_index=True)

        st.warning(tr('unified_risk').format(week=selected_week,tp=tp,fp=fp,fn=fn,precision=f"{risk['precision']:.1%}",recall=f"{risk['recall']:.1%}"))
    else:
        primary_report=read_report(ROOT/'02、模型实验/生成产物/revised/report.json',['no_show'])
        if primary_report is None:return
        try:risk=primary_report['no_show']['metrics'];risk['predicted_positive'];risk['confusion_tn_fp_fn_tp'][3];risk['precision']
        except (KeyError,TypeError,IndexError):st.info(tr('optional_invalid'));return
        st.warning(tr('risk_reliability').format(alerts=risk['predicted_positive'],
            true=risk['confusion_tn_fp_fn_tp'][3],false=risk['confusion_tn_fp_fn_tp'][1],precision=f"{risk['precision']:.1%}"))
    if len(active):
        st.dataframe(routed_display(active,locale) if mode=='unified' else active_display(active,locale),hide_index=True)
    else:
        st.info(tr('no_active'))
    st.subheader(tr('explain'))
    rank=ROOT/'02、模型实验/生成产物/revised/shap_feature_ranking.csv'
    if rank.exists():
        st.dataframe(shap_display(pd.read_csv(rank),locale),hide_index=True)
    st.caption(tr('shap_note'))
    if mode=='unified':st.caption(tr('unified_explain'))
    if len(active):
        st.subheader(tr('local_title'))
        eligible=active if mode=='current' else active[active.prediction_route.eq('known')]
        options=eligible.session_id.tolist()
        if st.session_state.get('explained_session') not in options:
            st.session_state['explained_session']=None
        if options:
            rows=eligible.set_index('session_id')
            session_labels={key:f"{row.room} · {row.course_id} · {row.course_start}–{row.course_end}" for key,row in rows.iterrows()}
            selected=st.selectbox(tr('local_select'),options,index=None,key='explained_session',
                format_func=session_labels.get)
            if selected:
                try:
                    # v6: unified mode explains the conditional (held) regression and checks it against its saved output.
                    bundle=b if mode=='current' else unified['cond']
                    expected=rows.loc[selected,'prediction'] if mode=='current' else rows.loc[selected,'held_prediction']
                    explanation=explain_session(bundle,eligible[eligible.session_id.eq(selected)],float(expected))
                except (ValueError,KeyError,TypeError):
                    st.warning(tr('local_unavailable'))
                else:
                    st.write(tr('local_summary').format(base=f"{explanation['baseline']:.1%}",
                        delta=f"{(explanation['raw_prediction']-explanation['baseline'])*100:+.1f}",
                        raw=f"{explanation['raw_prediction']:.1%}",prediction=f"{explanation['prediction']:.1%}"))
                    detail=explanation['table'].copy()
                    detail['feature']=detail.feature.map(lambda key:tr(key))
                    detail.columns=[tr('feature'),tr('local_value'),tr('local_pp')]
                    st.dataframe(detail,hide_index=True,width='stretch',key='local_contributions')
                    st.caption(tr('local_scope'))
        else:
            st.info(tr('local_unavailable'))

    with st.expander(tr('evidence')):
        st.write(tr('primary_data'))
        st.write(tr('external_data'))
        st.markdown(f"[{tr('source')} · UCI Occupancy Detection](https://archive.ics.uci.edu/dataset/357/occupancy+detection)")
        report_path=ROOT/'02、模型实验/生成产物/external_uci/report.json'
        if report_path.exists():
            report=read_report(report_path,['models','test_n'])
            if report is None:return
            scores=report['models']['logistic_regression']['empty_detection']
            st.dataframe(pd.DataFrame([{tr('samples'):report['test_n'],
                tr('empty_precision'):f"{scores['precision']:.1%}",
                tr('empty_recall'):f"{scores['recall']:.1%}",tr('empty_f1'):f"{scores['f1']:.1%}",
                tr('false_empty'):scores['confusion_tn_fp_fn_tp'][1]}]),hide_index=True)
        else:
            st.info(tr('no_external'))

    cold_path=ROOT/'02、模型实验/生成产物/improvement_v8/report.json'
    if cold_path.exists():
        with st.expander(tr('cold_start_experiment')):
            cold=read_report(cold_path,['macro_rmse','random','rooms'])
            if cold is None:return
            st.write(tr('cold_start_scope'))
            st.write(tr('cold_start_summary').format(rmse=f"{cold['macro_rmse']:.4f}",random=f"{cold['random']['metrics']['rmse']:.4f}"))
            st.dataframe(pd.DataFrame([{tr('room'):room,'RMSE':round(item['metrics']['rmse'],4)} for room,item in cold['rooms'].items()]),hide_index=True)

    comparison_path=ROOT/'02、模型实验/生成产物/improvement_v5/report.json'
    if comparison_path.exists():
        with st.expander(tr('noshow_comparison')):
            st.write(tr('comparison_note'))
            comparison=read_report(comparison_path,['folds'])
            if comparison is None:return
            rows=[]
            for week,fold in comparison['folds'].items():
                for method,label in [('old','original_model'),('new','candidate_model')]:
                    m=fold[method]
                    rows.append({tr('week'):int(week),tr('model'):tr(label),tr('precision'):f"{m['precision']:.1%}",
                        tr('recall'):f"{m['recall']:.1%}",tr('fp'):m['confusion_tn_fp_fn_tp'][1],
                        tr('fn'):m['confusion_tn_fp_fn_tp'][2]})
            st.dataframe(pd.DataFrame(rows),hide_index=True)


if show_research:
    try:render_research()
    except (ValueError,KeyError,TypeError,IndexError,OSError,EOFError):st.info(tr('optional_invalid'))
