import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'03、系统应用/代码'))
from i18n import LANGUAGES,TEXT,t,room_display,active_display,shap_display

class LanguageTests(unittest.TestCase):
    def test_complete_catalog_and_fallback(self):
        for key,row in TEXT.items():
            self.assertEqual(len(row),len(LANGUAGES),key)
            self.assertTrue(all(isinstance(x,str) and x.strip() for x in row),key)
        self.assertEqual(t('unknown','title'),t('en','title'))

    def test_business_status_and_unknown_predictions_preserved(self):
        rooms=pd.DataFrame({'room':['A','B','C'],'seats':[10,20,30],
                            'status':['scheduled_conflict','schedule_unknown','timetable_gap_occupancy_unknown'],
                            'verified_available':[False]*3,'reason':['原文']*3})
        original=rooms.copy(deep=True)
        for locale in LANGUAGES:
            f=room_display(rooms,locale)
            self.assertEqual(f[t(locale,'room')].tolist(),['A','B','C'])
            self.assertEqual(f[t(locale,'availability')].tolist(),[t(locale,'unverified')]*3)
            self.assertNotIn('原文',f.to_string())
        pd.testing.assert_frame_equal(rooms,original)
        active=pd.DataFrame({'room':['A'],'course_id':['x'],'course_start':['09:00'],
                             'course_end':['10:00'],'prediction':[float('nan')],
                             'no_show_probability':[float('nan')],'no_show_alert':[float('nan')]})
        for locale in LANGUAGES:
            f=active_display(active,locale)
            self.assertEqual(f[t(locale,'alert')].iloc[0],t(locale,'missing'))

    def test_review_flag_plain_summary_and_text_export(self):
        from i18n import queue_display,flag_text,plain_summary,review_text
        rows=pd.DataFrame({'room':['A','B'],'course_id':['c1','c2'],'course_start':['09:00:00','10:00:00'],'course_end':['10:00:00','11:00:00'],
            'prediction':[.04,.5],'low_alert':[True,False],'model_alert':[True,False],'context_alert':[False,False],'calendar_review':[True,False]})
        for locale in LANGUAGES:
            q=queue_display(rows,locale)
            self.assertEqual(list(q.columns)[0],t(locale,'review_flag'))
            self.assertTrue(q.iloc[0,0].startswith('⚠') and t(locale,'flag_reason_holiday') in q.iloc[0,0])
            self.assertEqual(q.iloc[1,0],t(locale,'flag_no'))
            summary=plain_summary(locale,.9,True,[{'feature':'course_recent_mean3','value':.006,'kind':'percent'},{'feature':'days_since_course','value':7,'kind':'days'}],holiday=True)
            self.assertIn('0.6%',summary);self.assertIn(t(locale,'plain_holiday'),summary)
            self.assertIn(t(locale,'plain_none'),plain_summary(locale,.2,False,[]))
            text=review_text(locale,rows.iloc[0],'2017-10-02',flag_text(rows.iloc[0],locale),summary,t(locale,'review_false'),'')
            self.assertNotIn('**',text);self.assertIn(t(locale,'plain_scope'),text);self.assertIn('A · c1',text)

    def test_shap_all_features_translated(self):
        root=Path(__file__).resolve().parents[2]
        frame=pd.read_csv(root/'02、模型实验/生成产物/revised/shap_feature_ranking.csv')
        for locale in LANGUAGES:
            translated=shap_display(frame,locale)
            self.assertEqual(list(translated[t(locale,'feature')]),[t(locale,key) for key in frame.feature])
            self.assertFalse(translated[t(locale,'direction')].isna().any())
