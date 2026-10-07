import unittest
import numpy as np
from assess import metrics, check_dates, DATES


class MetricsTests(unittest.TestCase):
    def test_identity(self):
        m=metrics([1,2,3,4],[1,2,3,4])
        for name in ['NSE','KGE2009','R2','r','alpha','beta']:
            self.assertAlmostEqual(m[name],1)
        self.assertEqual(m['RMSE'],0)

    def test_scale_not_hidden_by_r_squared(self):
        m=metrics([1,2,3],[2,4,6])
        self.assertAlmostEqual(m['R2'],1)
        self.assertAlmostEqual(m['KGE2009'],1-np.sqrt(2))
        self.assertAlmostEqual(m['NSE'],-6)
        self.assertAlmostEqual(m['bias_percent'],100)

    def test_offset(self):
        m=metrics([1,2,3],[2,3,4])
        self.assertAlmostEqual(m['NSE'],-.5)
        self.assertAlmostEqual(m['KGE2009'],.5)

    def test_zero_reference_and_constant_are_explicit(self):
        m=metrics([0,0],[0,1])
        for name in ['NSE','KGE2009','R2','beta','bias_percent']:
            self.assertIsNone(m[name])
        self.assertEqual(m['positive_reference_n'],0)

    def test_invalid_inputs(self):
        for x,y in [([1],[1]),([1,2],[1,2,3]),([1,2],[1,float('nan')])]:
            with self.assertRaises(ValueError):metrics(x,y)

    def test_complete_dates(self):
        check_dates(DATES)
        for index in [DATES[:-1],DATES[::-1],DATES.insert(0,DATES[0])]:
            with self.assertRaises(ValueError):check_dates(index)


if __name__=='__main__':unittest.main()
