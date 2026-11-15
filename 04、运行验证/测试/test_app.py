from pathlib import Path
from datetime import time,datetime,timedelta,timezone
import json
import hashlib
import sys
import argparse
import tempfile
import shutil
import logging
from unittest.mock import patch

def main():
    from streamlit.testing.v1 import AppTest
    from streamlit.elements.lib import policies
    time_state_conflicts=[]
    class StateWarningRecorder(logging.Handler):
        def emit(self,record):
            message=record.getMessage()
            if 'start_time' in message and 'Session State API' in message:time_state_conflicts.append(message)
    recorder=StateWarningRecorder();policies._LOGGER.addHandler(recorder)
    policies._shown_default_value_warning=False
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args()
    root=args.project_dir.resolve()
    external=(root/'02、模型实验/生成产物/external_uci/report.json').is_file()
    comparison=(root/'02、模型实验/生成产物/improvement_v5/report.json').is_file()
    cold=(root/'02、模型实验/生成产物/improvement_v8/report.json').is_file()
    unified=(root/'02、模型实验/生成产物/unified/report.json').is_file()
    sys.path.insert(0,str(root/'03、系统应用/代码'))
    from i18n import LANGUAGES,t
    app=AppTest.from_file(str(root/'03、系统应用/代码/app.py'),default_timeout=60).run()
    assert not app.exception,str(app.exception)
    app.selectbox(key='historical_date').select('2017-10-20')
    app.number_input(key='capacity').set_value(497)
    app.run()
    expected=app.dataframe[0].value.iloc[:,:2].to_numpy().tolist()
    assert not app.toggle(key='show_research').value
    assert not any(t('zh','feature') in item.value.columns for item in app.dataframe)
    chosen=app.selectbox(key='selected_room').options[0]
    app.selectbox(key='selected_room').select(chosen).run()
    checked=[]
    for locale in LANGUAGES:
        app.selectbox(key='locale').select(locale).run()
        assert not app.exception,str(app.exception)
        assert app.title[0].value==t(locale,'title')
        assert app.selectbox(key='selected_room').value==chosen
        assert any(item.value==t(locale,'next_steps') for item in app.info)
        assert len(app.get('download_button'))==1
        assert any('497' in item.value and '09:00' in item.value for item in app.markdown)
        app.toggle(key='show_research').set_value(True).run()
        assert not app.exception,str(app.exception)
        assert any(item.value==t(locale,'label_scope') for item in app.caption)
        assert any(item.value==t(locale,'research_separation') for item in app.markdown)
        assert app.selectbox(key='historical_date').value=='2017-10-20'
        assert app.number_input(key='capacity').value==497
        assert app.time_input(key='start_time').value==time(9)
        assert app.dataframe[0].value.iloc[:,:2].to_numpy().tolist()==expected
        assert t(locale,'availability') in app.dataframe[0].value.columns
        assert set(app.dataframe[0].value[t(locale,'availability')]) <= {t(locale,'unverified')}
        assert any(t(locale,'feature') in item.value.columns for item in app.dataframe)
        if external:
            assert any(t(locale,'samples') in item.value.columns and t(locale,'false_empty') in item.value.columns for item in app.dataframe)
        else:
            assert any(item.value==t(locale,'no_external') for item in app.info)
        if comparison:
            table=next(item.value for item in app.dataframe if t(locale,'fp') in item.value.columns)
            assert len(table)==8
            assert t(locale,'fp') in table.columns
        if cold:
            table=next(item.value for item in app.dataframe if 'RMSE' in item.value.columns)
            assert len(table)==9 and t(locale,'room') in table.columns
            assert any(item.value==t(locale,'cold_start_scope') for item in app.markdown)
        assert any('83' in item.value and '89' in item.value for item in app.warning)
        app.selectbox(key='historical_date').select('2017-10-16')
        app.number_input(key='capacity').set_value(10)
        app.run()
        options=app.selectbox(key='explained_session').options
        assert options
        import pandas as pd
        from replay import candidates
        from query_support import EMPTY_PREDICTIONS
        local_sessions=pd.read_csv(root/'01、数据处理/清洗产物/sessions.csv')
        local_attendance=pd.read_csv(root/'01、数据处理/清洗产物/attendance_clean.csv')
        _,_,local_active=candidates(local_sessions,local_attendance,EMPTY_PREDICTIONS,'2017-10-16',time(9),60,10)
        app.selectbox(key='explained_session').select(local_active.session_id.iloc[0]).run()
        assert not app.exception,str(app.exception)
        session=app.selectbox(key='explained_session').value
        detail=next(item.value for item in app.dataframe if t(locale,'local_pp') in item.value.columns)
        assert len(detail)==10 and any(t(locale,'local_scope')==item.value for item in app.caption)
        if unified:
            app.selectbox(key='prediction_mode').select('unified').run()
            assert not app.exception,str(app.exception)
            assert app.selectbox(key='explained_session').value==session
            assert any(t(locale,'local_pp') in item.value.columns for item in app.dataframe)
            app.selectbox(key='prediction_mode').select('current').run()
        app.number_input(key='capacity').set_value(497)
        app.run()
        app.selectbox(key='historical_date').select('2017-10-16').run()
        assert not app.exception,str(app.exception)
        assert app.dataframe[0].value.empty
        assert app.session_state['selected_room'] is None
        assert not app.get('download_button')
        assert any(t(locale,'empty')==item.value for item in app.info)
        app.time_input(key='start_time').set_value(time(23,30)).run()
        assert not app.exception,str(app.exception)
        assert any(t(locale,'midnight')==item.value for item in app.error)
        app.time_input(key='start_time').set_value(time(9))
        app.selectbox(key='historical_date').select('2017-10-20').run()
        if unified:
            app.selectbox(key='prediction_mode').select('unified').run()
            assert not app.exception,str(app.exception)
            assert app.dataframe[0].value.iloc[:,:2].to_numpy().tolist()==expected
            assert app.selectbox(key='historical_date').value=='2017-10-20'
            assert any(item.value==t(locale,'unified_scope') for item in app.markdown)
            assert any(item.value==t(locale,'unified_explain') for item in app.caption)
            assert any(t(locale,'route_label') in item.value.columns for item in app.dataframe)
            route_metrics=json.loads((root/'02、模型实验/生成产物/unified/report.json').read_text(encoding='utf-8'))['rolling']['12']['low']
            tn,fp,fn,tp=route_metrics['confusion_tn_fp_fn_tp']
            expected_warning=[str(tp),str(fp),str(fn),f"{route_metrics['precision']:.1%}",f"{route_metrics['recall']:.1%}"]
            assert any(all(value in item.value for value in expected_warning) for item in app.warning)
            app.selectbox(key='prediction_mode').select('current').run()
        app.toggle(key='show_research').set_value(False).run()
        assert not any(t(locale,'feature') in item.value.columns for item in app.dataframe)
        app.selectbox(key='selected_room').select(chosen).run()
        checked.append({'locale':locale,'title':t(locale,'title'),'status':'passed',
                        'checks':['query state retained','same candidates','translated tables and SHAP',
                                  'unverified availability','empty results','midnight error','no-show reliability',
                                  'query-first view','selected room retained across languages','stale selection cleared',
                                  'localized checklist','research details opt-in','selected class explanation in both modes']
                                  + (['external data panel'] if external else ['external data absent'])
                                  + (['four-week comparison'] if comparison else ['comparison absent'])
                                  + (['separate cold-start research panel'] if cold else ['cold-start panel absent'])
                                  + (['routed research mode, same candidates, explicit misses'] if unified else ['routed mode absent'])})
        print('PASS:',locale,flush=True)
    sys.path.insert(0,str(root/'02、模型实验/代码'))
    from models import revised
    with tempfile.TemporaryDirectory() as folder, patch.object(revised,'ROOT',Path(folder)):
        for locale in LANGUAGES:
            missing=AppTest.from_file(str(root/'03、系统应用/代码/app.py'),default_timeout=60).run()
            missing.selectbox(key='locale').select(locale).run()
            assert not missing.exception,str(missing.exception)
            assert any(item.value==t(locale,'setup_required') for item in missing.error)
            assert not missing.dataframe
    # Search remains usable when models are absent; this is not a fake model success.
    with tempfile.TemporaryDirectory() as folder, patch.object(revised,'ROOT',Path(folder)):
        target=Path(folder)/'01、数据处理/清洗产物';target.mkdir(parents=True)
        for filename in ['sessions.csv','attendance_clean.csv']:
            shutil.copy2(root/'01、数据处理/清洗产物'/filename,target/filename)
        for locale in LANGUAGES:
            data_only=AppTest.from_file(str(root/'03、系统应用/代码/app.py'),default_timeout=60).run()
            data_only.selectbox(key='locale').select(locale).run()
            assert not data_only.exception,str(data_only.exception)
            assert data_only.dataframe
            data_only.toggle(key='show_research').set_value(True).run()
            assert not data_only.exception,str(data_only.exception)
            assert any(x.value==t(locale,'research_unavailable') for x in data_only.info)
            assert data_only.dataframe
    # A later-time button must only change time, preserving requested seats and duration.
    import pandas as pd
    from datetime import time as clock_time
    from query_support import next_gap,EMPTY_PREDICTIONS
    from replay import candidates
    sessions=pd.read_csv(root/'01、数据处理/清洗产物/sessions.csv')
    attendance=pd.read_csv(root/'01、数据处理/清洗产物/attendance_clean.csv')
    found=None
    for date in sorted(sessions.loc[sessions.week.eq(12),'date'].unique()):
        for hour in [9,10,11,12,13,14]:
            begin=clock_time(hour)
            _,top,_=candidates(sessions,attendance,EMPTY_PREDICTIONS,date,begin,60,497)
            later=next_gap(sessions,attendance,date,begin,60,497) if top.empty else None
            if later:found=(date,begin,later['start']);break
        if found:break
    assert found,'Expected a real historical no-result/later-gap example'
    for locale in LANGUAGES:
        app.selectbox(key='locale').select(locale)
        app.selectbox(key='historical_date').select(found[0])
        app.time_input(key='start_time').set_value(found[1]);app.run()
        assert not app.exception,str(app.exception)
        app.button(key='try_later').click().run()
        assert not app.exception,str(app.exception)
        assert app.time_input(key='start_time').value==found[2]
        assert app.number_input(key='capacity').value==497 and app.number_input(key='duration').value==60
        assert app.selectbox(key='historical_date').value==found[0]
        assert not app.dataframe[0].value.empty
    out=root/'02、模型实验/生成产物/system'
    out.mkdir(parents=True,exist_ok=True)
    policies._LOGGER.removeHandler(recorder)
    assert not time_state_conflicts,'Time widget default/session-state conflict: '+str(time_state_conflicts)
    (out/'multilingual_checks.json').write_text(json.dumps({'kind':'automated AppTest; not human trials',
        'time_state_default_conflict':'absent',
        'optional_panels':{'external':external,'comparison':comparison,'cold_start':cold,'unified':unified},
        'missing_setup_four_languages':'passed','data_only_query_four_languages':'passed','later_time_action_four_languages':'passed','languages':checked,'date':datetime.now(timezone(timedelta(hours=9))).date().isoformat(),'sha256':{
            (str(p.relative_to(root)) if p.is_relative_to(root) else str(p)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [root/'03、系统应用/代码/app.py',root/'03、系统应用/代码/i18n.py',root/'03、系统应用/代码/query_support.py',root/'03、系统应用/代码/replay.py',root/'03、系统应用/代码/local_explanation.py',
                      root/'01、数据处理/清洗产物/sessions.csv',root/'01、数据处理/清洗产物/attendance_clean.csv',Path(__file__),root/'02、模型实验/生成产物/external_uci/report.json',
                      root/'02、模型实验/生成产物/improvement_v5/report.json',root/'02、模型实验/生成产物/improvement_v8/report.json',root/'02、模型实验/生成产物/unified/report.json'] if p.is_file()}
        },ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: four-language interactions and scope panel',flush=True)

if __name__=='__main__':main()
