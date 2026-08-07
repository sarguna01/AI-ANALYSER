import os
import tempfile
import unittest

import pandas as pd

import csv_comparetor


class CsvComparatorTest(unittest.TestCase):
    def test_compare_two_days_returns_threshold_groups(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            day1_path = os.path.join(tmpdir, "full_pct_change_2026-08-06.csv")
            day2_path = os.path.join(tmpdir, "full_pct_change_2026-08-07.csv")

            pd.DataFrame(
                [
                    {"SYMBOL": "AAA", "PCT_CHANGE": 10.0},
                    {"SYMBOL": "BBB", "PCT_CHANGE": 2.0},
                    {"SYMBOL": "CCC", "PCT_CHANGE": 0.5},
                ]
            ).to_csv(day1_path, index=False)

            pd.DataFrame(
                [
                    {"SYMBOL": "AAA", "PCT_CHANGE": 15.0},
                    {"SYMBOL": "CCC", "PCT_CHANGE": 2.0},
                    {"SYMBOL": "DDD", "PCT_CHANGE": 3.0},
                ]
            ).to_csv(day2_path, index=False)

            result = csv_comparetor.compare_two_days(day1_path, day2_path, threshold=1.0)

            self.assertIn("common_above_threshold", result)
            self.assertIn("day1_only_above_threshold", result)
            self.assertIn("day2_new_above_threshold", result)

            common = result["common_above_threshold"]
            self.assertEqual(common.loc[0, "SYMBOL"], "AAA")
            self.assertAlmostEqual(common.loc[0, "DELTA_PCT_CHANGE"], 5.0)

            day1_only = result["day1_only_above_threshold"]
            self.assertEqual(day1_only.loc[0, "SYMBOL"], "BBB")

            day2_new = result["day2_new_above_threshold"]
            self.assertEqual(day2_new.loc[0, "SYMBOL"], "DDD")


if __name__ == "__main__":
    unittest.main()
