from pathlib import Path
from datetime import time as default_time
import json
import sys
PROJECT_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT/'02、模型实验/代码'))
sys.path.insert(0,str(PROJECT_ROOT/'03、系统应用/代码'))
import streamlit as st
import pandas as pd
import joblib
from replay import candidates,replay_predictions
from query_support import EMPTY_PREDICTIONS,next_gap,query_summary,brief
from local_explanation import explain_session
from models.revised import ROOT
from i18n import LANGUAGES,t,room_display,active_display,routed_display,shap_display

st.set_page_config(page_title='Campus Room Replay',layout='wide')
locale=st.sidebar.selectbox('Language / 언어 / 语言 / 言語',list(LANGUAGES),format_func=LANGUAGES.get,key='locale')
tr=lambda key:t(locale,key)
show_research=st.sidebar.toggle(tr('research_toggle'),value=False,key='show_research')
st.title(tr('title'))
st.caption(tr('intro'))

def available(names):
    return all((ROOT/name).is_file() and (ROOT/name).stat().st_size for name in names)

data_paths=['01、数据处理/清洗产物/sessions.csv','01、数据处理/清洗产物/attendance_clean.csv']
if not available(data_paths):
    st.error(tr('setup_required'));st.stop()

@st.cache_data
def data_resources(root,stamps):
    return tuple(pd.read_csv(Path(root)/p) for p in data_paths)

@st.cache_resource
def model_resources(root,stamps):
    folder=Path(root)/'02、模型实验/生成产物/revised'
    return joblib.load(folder/'model.joblib'),joblib.load(folder/'no_show.joblib')

s,a=data_resources(str(ROOT),tuple((ROOT/p).stat().st_mtime_ns for p in data_paths))
st.subheader(tr('needs_title'))
inputs=st.columns([1.5,1,1,1])
dates=sorted(s.loc[s.week.eq(12),'date'].unique())
with inputs[0]:day=st.selectbox(tr('date'),dates,key='historical_date')
if 'start_time' not in st.session_state:
    st.session_state['start_time']=default_time(9,0)
with inputs[1]:start=st.time_input(tr('start'),key='start_time')
with inputs[2]:minutes=st.number_input(tr('duration'),min_value=15,max_value=240,value=60,step=15,key='duration')
with inputs[3]:capacity=st.number_input(tr('capacity'),min_value=1,max_value=497,value=10,key='capacity')
st.caption(tr('time_basis'))
if start.hour*60+start.minute+minutes>24*60:
    st.error(tr('midnight'));st.stop()
try:
    rooms,top,_=candidates(s,a,EMPTY_PREDICTIONS,day,start,minutes,capacity)
except ValueError:
    st.error(tr('query_error'));st.stop()
st.subheader(tr('top'))
st.write(query_summary(locale,day,start,minutes,capacity))
counts=rooms.status.value_counts()
st.caption(tr('result_counts').format(eligible=len(rooms),gaps=int(counts.get('timetable_gap_occupancy_unknown',0)),
    conflicts=int(counts.get('scheduled_conflict',0)),unknown=int(counts.get('schedule_unknown',0))))
st.write(tr('ranking'))
if top.empty:st.info(tr('empty'))
display=room_display(top,locale)[[tr('room'),tr('seats'),tr('availability')]].copy()
display.insert(2,tr('spare_seats'),(top.seats-capacity).to_numpy())
st.dataframe(display,hide_index=True,width='stretch')
if top.empty:
    later=next_gap(s,a,day,start,minutes,capacity)
    if later is not None:
        value=later['start'];label=value.strftime('%H:%M')
        st.info(tr('later_found').format(time=label,count=later['candidates']))
        def apply_later(value):
            st.session_state['start_time']=value
            st.session_state['selected_room']=None
        st.button(tr('try_later').format(time=label),key='try_later',on_click=apply_later,args=(value,))
    else:st.caption(tr('no_later'))
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
        st.write(tr('candidate_basis'))
        st.info(tr('next_steps'))
        st.download_button(tr('save_brief'),brief(top,selected,locale,day,start,minutes,capacity).encode('utf-8-sig'),
            file_name='historical-room-checklist.txt',mime='text/plain; charset=utf-8',key='download_brief')


def render_research():
    st.write(tr('research_separation'))
    names=['02、模型实验/生成产物/revised/'+name for name in ['model.joblib','no_show.joblib','report.json','shap_feature_ranking.csv']]
    if not available(names):
        st.info(tr('research_unavailable'));return
    unified_available=available(['02、模型实验/生成产物/unified/'+name for name in ['model.joblib','report.json']])
    mode=st.selectbox(tr('prediction_mode'),['current','unified'],index=1 if st.session_state.get('research_model')=='unified' else 0,
        format_func=lambda value:tr('system_'+value),key='prediction_mode') if unified_available else 'current'
    st.session_state['research_model']=mode
    try:
        if mode=='unified':
            from models.unified import load_verified,predict_bundle
            unified,unified_report=load_verified(ROOT)
            display_predictions=predict_bundle(unified,s[s.week.eq(12)])
        else:
            b,ns=model_resources(str(ROOT),tuple((ROOT/p).stat().st_mtime_ns for p in names[:2]))
            display_predictions=replay_predictions(s,b,ns)
        _,_,active=candidates(s,a,display_predictions,day,start,minutes,capacity)
    except (ValueError,OSError,KeyError,EOFError):
        st.error(tr('unified_unavailable') if mode=='unified' else tr('research_unavailable'));return
    st.subheader(tr('unified_title' if mode=='unified' else 'active_title'))
    st.write(tr('unified_scope' if mode=='unified' else 'definitions'))
    st.caption(tr('label_scope'))
    primary_report=json.loads((ROOT/'02、模型实验/生成产物/revised/report.json').read_text(encoding='utf-8'))
    risk=primary_report['no_show']['metrics']
    if mode=='unified':
        risk=unified_report['rolling']['12']['low'];tn,fp,fn,tp=risk['confusion_tn_fp_fn_tp']
        st.caption(tr('unified_cutoff').format(date=str(unified['cutoff'].date())))
        st.warning(tr('unified_risk').format(tp=tp,fp=fp,fn=fn,precision=f"{risk['precision']:.1%}",recall=f"{risk['recall']:.1%}"))
    else:
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
                    bundle=b if mode=='current' else unified['warm']
                    explanation=explain_session(bundle,eligible[eligible.session_id.eq(selected)],float(rows.loc[selected,'prediction']))
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
            report=json.loads(report_path.read_text(encoding='utf-8'))
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
            cold=json.loads(cold_path.read_text(encoding='utf-8'))
            st.write(tr('cold_start_scope'))
            st.write(tr('cold_start_summary').format(rmse=f"{cold['macro_rmse']:.4f}",random=f"{cold['random']['metrics']['rmse']:.4f}"))
            st.dataframe(pd.DataFrame([{tr('room'):room,'RMSE':round(item['metrics']['rmse'],4)} for room,item in cold['rooms'].items()]),hide_index=True)

    comparison_path=ROOT/'02、模型实验/生成产物/improvement_v5/report.json'
    if comparison_path.exists():
        with st.expander(tr('noshow_comparison')):
            st.write(tr('comparison_note'))
            comparison=json.loads(comparison_path.read_text(encoding='utf-8'))
            rows=[]
            for week,fold in comparison['folds'].items():
                for method,label in [('old','original_model'),('new','candidate_model')]:
                    m=fold[method]
                    rows.append({tr('week'):int(week),tr('model'):tr(label),tr('precision'):f"{m['precision']:.1%}",
                        tr('recall'):f"{m['recall']:.1%}",tr('fp'):m['confusion_tn_fp_fn_tp'][1],
                        tr('fn'):m['confusion_tn_fp_fn_tp'][2]})
            st.dataframe(pd.DataFrame(rows),hide_index=True)


if show_research:
    render_research()
