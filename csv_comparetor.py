"""
Multi-Day Stock Momentum Comparator
--------------------------------------
Takes multiple daily CSV files (each with SYMBOL, CLOSE, PREV_CLOSE, PCT_CHANGE)
and finds stocks that show CONSECUTIVE positive % change across days
(Day1 -> Day2 -> Day3 -> ...).

This helps spot momentum stocks that keep moving up day after day,
rather than a one-off spike.

FOLDER SETUP:
Put your daily CSVs in a folder, named so they sort in date order, e.g.:
    daily_csvs/2026-08-04.csv
    daily_csvs/2026-08-05.csv
    daily_csvs/2026-08-06.csv

Each CSV must have these columns (matches your bhavcopy script output):
    SYMBOL,CLOSE,PREV_CLOSE,PCT_CHANGE

Usage:
    python momentum_comparator.py daily_csvs/

Output:
    - consecutive_gainers.csv  -> stocks that gained EVERY single day across all files
    - streak_summary.csv       -> for every stock, how many consecutive up-days (as of the last file)
    - Console printout of both, sorted by strongest momentum
"""

import pandas as pd
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATHS = [
    os.path.join(BASE_DIR, "bhavcopy_data", "full_pct_change_2026-08-06.csv"),
    os.path.join(BASE_DIR, "bhavcopy_data", "top_gainers_2026-08-06.csv"),
    os.path.join(BASE_DIR, "bhavcopy_data", "top_losers_2026-08-06.csv"),
]


def load_all_days(csv_paths: list[str] | None = None) -> dict:
    """
    Loads the hardcoded CSV files and returns a dict with one entry per file.
    You can keep 2, 3, or 4 files by editing CSV_PATHS above.
    Returns a dict: {filename_without_ext: DataFrame}
    """
    files_to_load = CSV_PATHS if csv_paths is None else csv_paths
    if not isinstance(files_to_load, list):
        files_to_load = list(files_to_load)

    days = {}
    for csv_path in files_to_load:
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"File not found: {csv_path}")

        day_label = os.path.splitext(os.path.basename(csv_path))[0]
        df = pd.read_csv(csv_path)
        df.columns = [c.strip().upper() for c in df.columns]

        required = {"SYMBOL", "PCT_CHANGE"}
        if not required.issubset(df.columns):
            raise ValueError(
                f"{csv_path} is missing required columns. Found: {list(df.columns)}. "
                f"Need at least: {required}"
            )

        days[day_label] = df
        print(f"Loaded {day_label}: {len(df)} stocks")

    return days


def build_pct_change_matrix(days: dict) -> pd.DataFrame:
    """
    Builds a wide table: rows = SYMBOL, columns = each day's PCT_CHANGE.
    Missing values mean that stock wasn't in that day's file
    (e.g. didn't trade, got delisted, or is a new IPO).
    """
    day_labels = list(days.keys())
    merged = None

    for label, df in days.items():
        sub = df[["SYMBOL", "PCT_CHANGE"]].rename(columns={"PCT_CHANGE": label})
        merged = sub if merged is None else merged.merge(sub, on="SYMBOL", how="outer")

    return merged, day_labels


def find_consecutive_gainers(matrix: pd.DataFrame, day_labels: list) -> pd.DataFrame:
    """
    Finds stocks with a positive PCT_CHANGE on EVERY single day in the
    provided range (i.e. present and gaining in day1 AND day2 AND day3...).
    """
    condition = pd.Series([True] * len(matrix))
    for day in day_labels:
        condition &= matrix[day].notna() & (matrix[day] > 0)

    result = matrix[condition].copy()
    result["TOTAL_STREAK_DAYS"] = len(day_labels)
    result["AVG_DAILY_PCT_CHANGE"] = result[day_labels].mean(axis=1).round(2)
    return result.sort_values("AVG_DAILY_PCT_CHANGE", ascending=False)


def compute_streaks(matrix: pd.DataFrame, day_labels: list) -> pd.DataFrame:
    """
    For every stock, computes the CURRENT consecutive up-day streak,
    counting backwards from the most recent day. This catches stocks
    that are currently on a hot streak even if they had a down day earlier
    in the dataset.
    """
    streaks = []
    for _, row in matrix.iterrows():
        streak = 0
        for day in reversed(day_labels):  # walk backwards from most recent
            val = row[day]
            if pd.notna(val) and val > 0:
                streak += 1
            else:
                break
        streaks.append(streak)

    matrix = matrix.copy()
    matrix["CURRENT_UP_STREAK"] = streaks
    return matrix.sort_values("CURRENT_UP_STREAK", ascending=False)


def main():
    days = load_all_days()
    matrix, day_labels = build_pct_change_matrix(days)

    print(f"\nComparing {len(day_labels)} days: {day_labels}")

    # 1. Stocks that gained on EVERY single day provided
    consecutive_gainers = find_consecutive_gainers(matrix, day_labels)
    consecutive_gainers.to_csv("consecutive_gainers.csv", index=False)

    print(f"\n=== Stocks that gained on ALL {len(day_labels)} days ===")
    if consecutive_gainers.empty:
        print("None found — no stock gained on every single day provided.")
    else:
        print(consecutive_gainers.to_string(index=False))
    print("Saved -> consecutive_gainers.csv")

    # 2. Current up-streak for every stock (more useful as days grow)
    streak_df = compute_streaks(matrix, day_labels)
    streak_df.to_csv("streak_summary.csv", index=False)

    print(f"\n=== Top 20 stocks by current consecutive up-streak ===")
    print(streak_df.head(20).to_string(index=False))
    print("Saved -> streak_summary.csv")


if __name__ == "__main__":
    main()
