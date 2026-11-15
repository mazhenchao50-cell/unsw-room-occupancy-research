from pathlib import Path
import sys
import unittest
import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02、模型实验/代码'))
sys.path.insert(0,str(ROOT/'03、系统应用/代码'))
from models.revised import load,predict
from local_explanation import explain_session


class LocalExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'02、模型实验/生成产物/revised'
        cls.bundle=joblib.load(folder/'model.joblib')
        cls.query=load().loc[lambda d:d.week.eq(12)]
        cls.saved=pd.read_csv(folder/'shap_local.csv').set_index('session_id')

    def test_every_test_session_matches_saved_shap_and_prediction(self):
        predictions=predict(self.bundle,self.query)
        self.assertEqual(len(self.query),206)
        for position in range(len(self.query)):
            query=self.query.iloc[[position]]
            result=explain_session(self.bundle,query,float(predictions[position]))
            values=result['table'].set_index('feature').contribution_pp/100
            expected=self.saved.loc[result['session_id'],values.index].to_numpy(dtype=float)
            np.testing.assert_allclose(values.to_numpy(),expected,rtol=0,atol=1e-7)
            self.assertAlmostEqual(result['baseline']+values.sum(),result['raw_prediction'])

    def test_rejects_wrong_prediction_fitted_dates_and_multiple_sessions(self):
        query=self.query.iloc[[0]]
        with self.assertRaises(ValueError):explain_session(self.bundle,query,-999)
        with self.assertRaises(ValueError):explain_session(self.bundle,self.query.iloc[:2],0)
        with self.assertRaises(ValueError):explain_session(self.bundle,self.bundle['reference'].iloc[[0]],0)

    def test_observed_target_is_not_an_explanation_input(self):
        query=self.query.iloc[[0]].copy()
        prediction=float(predict(self.bundle,query)[0])
        before=explain_session(self.bundle,query,prediction)
        query.loc[:,'attendees']=99999
        query.loc[:,'occupancy_rate']=999.0
        after=explain_session(self.bundle,query,prediction)
        pd.testing.assert_frame_equal(before['table'],after['table'])


if __name__=='__main__':unittest.main()
