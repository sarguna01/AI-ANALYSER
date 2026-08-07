"""
Two-day bhavcopy comparison tool.
--------------------------------
Compares two daily percentage-change files from bhavcopy_data and creates a
side-by-side view of how each stock moved between the two days.

Usage:
    python csv_comparetor.py
    python csv_comparetor.py <day1.csv> <day2.csv>

Output:
    - two_day_comparison.csv
"""

import glob
import os

import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def discover_default_files(base_dir: str | None = None) -> tuple[str, str]:
    """Pick the two latest full_pct_change CSV files from bhavcopy_data."""
    data_dir = os.path.join(base_dir or BASE_DIR, "bhavcopy_data")
    files = sorted(glob.glob(os.path.join(data_dir, "full_pct_change_*.csv")))
    if len(files) < 2:
        raise FileNotFoundError(
            f"Expected at least two daily files in {data_dir}, found {len(files)}"
        )
    return files[-2], files[-1]


def load_pct_change_file(csv_path: str) -> pd.DataFrame:
    """Load a daily percent-change export and keep only SYMBOL and PCT_CHANGE."""
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().upper() for c in df.columns]

    if "SYMBOL" not in df.columns or "PCT_CHANGE" not in df.columns:
        raise ValueError(
            f"{csv_path} is missing required columns. Found: {list(df.columns)}"
        )

    return df[["SYMBOL", "PCT_CHANGE"]].copy()


def compare_two_days(day1_path: str, day2_path: str) -> pd.DataFrame:
    """Compare two daily PCT_CHANGE files and return a side-by-side summary."""
    day1_df = load_pct_change_file(day1_path)
    day2_df = load_pct_change_file(day2_path)

    day1_label = os.path.splitext(os.path.basename(day1_path))[0]
    day2_label = os.path.splitext(os.path.basename(day2_path))[0]

    merged = day1_df.rename(columns={"PCT_CHANGE": day1_label}).merge(
        day2_df.rename(columns={"PCT_CHANGE": day2_label}),
        on="SYMBOL",
        how="outer",
    )
    merged = merged.sort_values("SYMBOL").reset_index(drop=True)

    merged["DAY1_PCT_CHANGE"] = merged[day1_label]
    merged["DAY2_PCT_CHANGE"] = merged[day2_label]
    merged = merged.drop(columns=[day1_label, day2_label])

    merged["DELTA_PCT_CHANGE"] = (
        merged["DAY2_PCT_CHANGE"] - merged["DAY1_PCT_CHANGE"]
    )

    def classify_trend(row: pd.Series) -> str:
        day1 = row["DAY1_PCT_CHANGE"]
        day2 = row["DAY2_PCT_CHANGE"]

        if pd.isna(day1) and pd.notna(day2):
            return "added"
        if pd.notna(day1) and pd.isna(day2):
            return "removed"
        if pd.isna(day1) or pd.isna(day2):
            return "unknown"

        delta = row["DELTA_PCT_CHANGE"]
        if delta > 0:
            return "up"
        if delta < 0:
            return "down"
        return "flat"

    merged["TREND"] = merged.apply(classify_trend, axis=1)

    return merged[[
        "SYMBOL",
        "DAY1_PCT_CHANGE",
        "DAY2_PCT_CHANGE",
        "DELTA_PCT_CHANGE",
        "TREND",
    ]]


def main() -> None:
    import sys

    if len(sys.argv) == 3:
        day1_path = sys.argv[1]
        day2_path = sys.argv[2]
    else:
        day1_path, day2_path = discover_default_files()

    comparison = compare_two_days(day1_path, day2_path)
    output_path = os.path.join(BASE_DIR, "two_day_comparison.csv")
    comparison.to_csv(output_path, index=False)

    print(f"Comparing {os.path.basename(day1_path)} vs {os.path.basename(day2_path)}")
    print(comparison.head(20).to_string(index=False))
    print(f"Saved -> {output_path}")


if __name__ == "__main__":
    main()
