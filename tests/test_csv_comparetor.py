import os
import tempfile
import unittest

import pandas as pd

import csv_comparetor


class CsvComparatorTest(unittest.TestCase):
    def test_compare_two_days_returns_delta_and_trend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            day1_path = os.path.join(tmpdir, "full_pct_change_2026-08-06.csv")
            day2_path = os.path.join(tmpdir, "full_pct_change_2026-08-07.csv")

            pd.DataFrame(
                [
                    {"SYMBOL": "AAA", "PCT_CHANGE": 10.0},
                    {"SYMBOL": "BBB", "PCT_CHANGE": -5.0},
                ]
            ).to_csv(day1_path, index=False)

            pd.DataFrame(
                [
                    {"SYMBOL": "AAA", "PCT_CHANGE": 15.0},
                    {"SYMBOL": "CCC", "PCT_CHANGE": 8.0},
                ]
            ).to_csv(day2_path, index=False)

            result = csv_comparetor.compare_two_days(day1_path, day2_path)

            self.assertEqual(result.loc[0, "SYMBOL"], "AAA")
            self.assertAlmostEqual(result.loc[0, "DELTA_PCT_CHANGE"], 5.0)
            self.assertEqual(result.loc[0, "TREND"], "up")
            self.assertEqual(result.loc[1, "SYMBOL"], "BBB")
            self.assertEqual(result.loc[1, "TREND"], "removed")
            self.assertEqual(result.loc[2, "SYMBOL"], "CCC")
            self.assertEqual(result.loc[2, "TREND"], "added")


if __name__ == "__main__":
    unittest.main()
