"""End-to-end checks of the four-language historical review workflow."""
from pathlib import Path
from datetime import time,datetime,timezone
import json,hashlib,sys,tempfile,shutil,argparse
import time as timer
from unittest.mock import patch
import numpy as np
import pandas as pd


def main():
    started_at=datetime.now(timezone.utc)
    from streamlit.testing.v1 import AppTest
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[2])
    root=parser.parse_args().project_dir.resolve()
    sys.path.insert(0,str(root/'03、系统应用/代码'))
    sys.path.insert(0,str(root/'02、模型实验/代码'))
    from i18n import LANGUAGES,t
    from models import unified as U,revised as R
    source=pd.read_csv(root/'01、数据处理/清洗产物/sessions.csv')
    dates=sorted(source.loc[source.week.isin([8,10,11,12]),'date'].unique())
    path=str(root/'03、系统应用/代码/app.py')
    samples=[];checked=[]
    started=timer.perf_counter();app=AppTest.from_file(path,default_timeout=120).run()
    cold_seconds=timer.perf_counter()-started
    assert not app.exception,str(app.exception)
    options=app.selectbox(key='historical_date').options   # heuristic review F9: weekday, week and holiday shown
    assert len(options)==len(dates) and all(o.startswith(d+'（') for o,d in zip(options,dates)),options[:3]
    assert [o[:10] for o in options if t('zh','holiday_mark') in o]==['2017-10-02']
    assert not app.toggle(key='show_research').value
    for locale in LANGUAGES:
        started=timer.perf_counter()
        app.selectbox(key='locale').select(locale)
        app.selectbox(key='historical_date').select('2017-10-16').run()
        samples.append(timer.perf_counter()-started)
        assert not app.exception,str(app.exception)
        assert app.title[0].value==t(locale,'title')
        assert any(x.value==t(locale,'review_scope') for x in app.markdown)
        assert any(x.value==t(locale,'history_rule_scope') for x in app.info)
        queue=app.dataframe[0].value
        # Heuristic review F1: readable flag first in the primary queue; all scores in the research expander.
        assert list(queue.columns)[0]==t(locale,'review_flag') and t(locale,'low_score') not in queue.columns
        scores=[x.value for x in app.dataframe if t(locale,'low_score') in x.value.columns and t(locale,'calendar_review') in x.value.columns]
        assert len(scores)==1
        flags=queue[t(locale,'review_flag')].str.startswith('⚠').to_numpy();alerts=scores[0][t(locale,'low_alert')].eq(t(locale,'alert_yes')).to_numpy()
        assert alerts.any() and (flags==alerts).all()
        assert len(queue)==int(source.date.eq('2017-10-16').sum())
        selected=source.loc[source.date.eq('2017-10-16'),'session_id'].iloc[0]
        app.selectbox(key='review_session').select(selected).run()
        assert not app.exception,str(app.exception)
        assert any(t(locale,'logistic_score') in x.value.columns for x in app.dataframe)
        assert any(t(locale,'tree_log_odds') in x.value.columns for x in app.dataframe)
        assert any(t(locale,'forest_probability_points') in x.value.columns for x in app.dataframe)
        assert any(t(locale,'context_alert') in x.value.columns for x in app.dataframe)
        # Heuristic review F2: a plain conclusion precedes the technical reconstruction.
        assert any(x.value.startswith(t(locale,'plain_flagged').split('{')[0]) or x.value.startswith(t(locale,'plain_not_flagged').split('{')[0]) for x in app.markdown)
        assert any(x.value==t(locale,'plain_scope') for x in app.caption)
        assert sorted(b.label for b in app.get('download_button'))==sorted([t(locale,'review_download'),t(locale,'review_download_text')])   # F10
        signals=[x.value for x in app.dataframe if t(locale,'course_recent_mean3') in x.value.columns]
        assert len(signals)==1 and str(signals[0][t(locale,'course_recent_mean3')].iloc[0]).endswith('%')   # F12
        app.selectbox(key='review_action').select('suspected_false_alert')
        app.text_area(key='review_note').set_value('TEST_ONLY synthetic interaction').run()
        other=source.loc[source.date.eq('2017-10-16'),'session_id'].iloc[1]
        app.selectbox(key='review_session').select(other).run()
        assert app.selectbox(key='review_action').value=='pending'
        assert app.text_area(key='review_note').value==''
        app.toggle(key='show_research').set_value(True).run()
        assert not app.exception,str(app.exception)
        assert app.selectbox(key='prediction_mode').value=='unified'
        assert any(t(locale,'route_label') in x.value.columns for x in app.dataframe)
        app.selectbox(key='prediction_mode').select('current').run()
        assert not app.exception,str(app.exception)
        app.selectbox(key='prediction_mode').select('unified').run()
        app.selectbox(key='start_time').select(time(23,30)).run()
        assert not app.exception,str(app.exception)
        assert any(x.value==t(locale,'midnight') for x in app.error)
        # Heuristic review F3: the class review queue stays available when only the candidate interval is invalid.
        assert list(app.dataframe[0].value.columns)[0]==t(locale,'review_flag') and len(app.dataframe[0].value)==int(source.date.eq('2017-10-16').sum())
        assert not any(t(locale,'spare_seats') in x.value.columns for x in app.dataframe)
        app.selectbox(key='start_time').select(time(9)).run()
        app.toggle(key='show_research').set_value(False).run()
        for week in (8,10,11,12):
            date=source.loc[source.week.eq(week),'date'].min()
            app.selectbox(key='historical_date').select(date).run()
            assert not app.exception,str(app.exception)
            assert len(app.dataframe[0].value)==int(source.date.eq(date).sum())
            assert app.session_state['review_session'] is None
        # Historical slot rule (experiment 19): a known week-12 evening query lists three rooms.
        app.selectbox(key='historical_date').select('2017-10-18')
        app.selectbox(key='start_time').select(time(18));app.number_input(key='duration').set_value(90)
        app.number_input(key='capacity').set_value(30).run()
        assert not app.exception,str(app.exception)
        listed=[x.value for x in app.dataframe if t(locale,'spare_seats') in x.value.columns]
        assert len(listed)==1 and listed[0][t(locale,'room')].tolist()==['BUS 105','MathewsThD','MathewsThB'],listed
        assert listed[0][t(locale,'availability')].eq(t(locale,'unverified')).all()
        app.selectbox(key='selected_room').select('BUS 105').run()
        assert not app.exception,str(app.exception)
        assert any(x.value.startswith(t(locale,'history_basis').split('{')[0]) for x in app.markdown)
        assert any(button.label==t(locale,'save_brief') for button in app.get('download_button'))
        # Trial task T4 (trial_v7_20261124): no candidate at 13:00 for 100 seats, the suggested later start lists one.
        app.selectbox(key='historical_date').select('2017-10-16')
        app.selectbox(key='start_time').select(time(13));app.number_input(key='duration').set_value(60)
        app.number_input(key='capacity').set_value(100).run()
        assert not app.exception,str(app.exception)
        assert any(x.value==t(locale,'later_found').format(time='16:00',count=1) for x in app.success)
        reasons=[x.value for x in app.dataframe if t(locale,'reason') in x.value.columns and t(locale,'status') in x.value.columns]
        prefix=t(locale,'conflict_detail_reason').split('{')[0]
        assert len(reasons)==1 and reasons[0][t(locale,'reason')].map(lambda r:r.startswith(prefix)).any()   # F8
        app.button(key='try_later').click().run()
        assert not app.exception,str(app.exception)
        assert app.selectbox(key='start_time').value==time(16)
        listed=[x.value for x in app.dataframe if t(locale,'spare_seats') in x.value.columns]
        assert len(listed)==1 and len(listed[0])==1,listed
        app.selectbox(key='historical_date').select('2017-10-16')
        app.selectbox(key='start_time').select(time(9));app.number_input(key='duration').set_value(60)
        app.number_input(key='capacity').set_value(10).run()
        assert not app.exception,str(app.exception)
        checked.append(dict(locale=locale,status='passed',checks=[
            'all four evaluation weeks','formal model queue in primary view','classifier/calendar separation',
            'signals and export','no annotation carry-over','explicit baseline selection',
            'historical slot-rule candidates and checklist','later-start suggestion (trial task T4)','midnight validation keeps review queue','plain-language reasons','dated labels, readable export, conflict times','language/query state']))
        print('PASS:',locale,flush=True)
    with tempfile.TemporaryDirectory() as folder:
        target=Path(folder)
        for name in U.required_artifacts()|{'02、模型实验/生成产物/unified/report.json'}:
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,dest)
        for name in ('external_uci','improvement_v8','improvement_v5'):
            dest=target/f'02、模型实验/生成产物/{name}/report.json'
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('{broken',encoding='utf-8')
        with patch.object(R,'ROOT',target):
            for locale in LANGUAGES:
                isolated=AppTest.from_file(path,default_timeout=120).run()
                isolated.selectbox(key='locale').select(locale)
                isolated.toggle(key='show_research').set_value(True).run()
                assert not isolated.exception,str(isolated.exception)
                assert isolated.selectbox(key='prediction_mode').value=='unified'
                assert any(t(locale,'low_score') in x.value.columns for x in isolated.dataframe)
                assert any(x.value==t(locale,'optional_invalid') for x in isolated.info)
            (target/'02、模型实验/生成产物/unified/model.joblib').unlink()
            missing=AppTest.from_file(path,default_timeout=120).run()
            missing.toggle(key='show_research').set_value(True).run()
            assert not missing.exception,str(missing.exception)
            assert missing.selectbox(key='prediction_mode').value=='unified'
            assert any(x.value==t('zh','unified_unavailable') for x in missing.error)
    with tempfile.TemporaryDirectory() as folder,patch.object(R,'ROOT',Path(folder)):
        for locale in LANGUAGES:
            absent=AppTest.from_file(path,default_timeout=120).run()
            absent.selectbox(key='locale').select(locale).run()
            assert not absent.exception,str(absent.exception)
            assert any(x.value==t(locale,'setup_required') for x in absent.error)
    out=root/'02、模型实验/生成产物/system';out.mkdir(parents=True,exist_ok=True)
    finished_at=datetime.now(timezone.utc)
    record=dict(kind='Automated AppTest; no invented human trials',date=finished_at.date().isoformat(),
        started_at_utc=started_at.isoformat(),finished_at_utc=finished_at.isoformat(),
        languages=checked,standard_default_verified=True,missing_setup_four_languages='passed',
        formal_without_legacy_artifacts='passed',malformed_optional_reports='passed',no_silent_baseline_fallback='passed',
        runtime=dict(first_render_seconds=cold_seconds,warm_rerender_seconds=samples,
            p50_seconds=float(np.quantile(samples,.5)),p95_seconds=float(np.quantile(samples,.95)),
            note='Four measured local rerenders; not a load or user study.'),
        sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [root/'03、系统应用/代码'/name for name in ('app.py','i18n.py','review_workflow.py','replay.py','query_support.py')]+[Path(__file__)]})
    (out/'multilingual_checks.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: four-language historical review workflow',flush=True)


if __name__=='__main__':main()

