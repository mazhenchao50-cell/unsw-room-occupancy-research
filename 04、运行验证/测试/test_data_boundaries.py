"""Malformed input must not be reported as repaired or reach model features."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'01、数据处理/代码'))
import heal_base as H


class DataBoundaryTests(unittest.TestCase):
    def test_clock_ranges_and_non_finite_numbers(self):
        for value in ['24:00:00','12:60:00','12:01:60','99:99:99','bad']:
            self.assertIsNone(H._norm_time(value))
        self.assertEqual(H._norm_time('9:03:04'),'09:03:04')
        self.assertEqual(H._norm_time('23:59:59'),'23:59:59')
        for value in ['inf','-inf','1e999','nan']:
            self.assertIsNone(H._to_num(value))
        self.assertEqual(H._to_num('0'),0)

    def test_invalid_duration_is_never_counted_as_repaired(self):
        for value in ['bad','-1','inf','1e999','00:60:00','00:01:60']:
            self.assertEqual(H._duration_to_min(value),(None,False))
        self.assertEqual(H._duration_to_min('90'),(90.,True))
        self.assertEqual(H._duration_to_min('01:30:00'),(90.,False))
        self.assertEqual(H._duration_to_min('25:00:00'),(1500.,False))


if __name__=='__main__':
    unittest.main()
