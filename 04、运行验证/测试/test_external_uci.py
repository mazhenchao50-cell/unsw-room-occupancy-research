import sys
import os
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'02、模型实验/代码/models'))
import external_uci as U

class ExternalDataTests(unittest.TestCase):
    @unittest.skipIf(os.environ.get('PROJECT_TEST_PROFILE')=='core','UCI artifact check belongs to extended profile')
    def test_chronology_and_test_label_isolation(self):
        parts=U.load_parts();train=parts['datatraining.txt'][0];test=parts['datatest2.txt'][0]
        self.assertEqual(sum(len(d) for d,_ in parts.values()),20560)
        model,p,base=U.fit_predict(train,test)
        changed=test.copy();changed['Occupancy']=1-changed.Occupancy
        other,q,other_base=U.fit_predict(train,changed)
        np.testing.assert_array_equal(p,q)
        np.testing.assert_array_equal(base,other_base)
        np.testing.assert_allclose(model[0].mean_,train[U.FEATURES].mean())
        with self.assertRaises(ValueError): U.fit_predict(train,parts['datatest.txt'][0])
