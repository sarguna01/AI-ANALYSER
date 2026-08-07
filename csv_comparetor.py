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


def compare_two_days(day1_path: str, day2_path: str, threshold: float = 1.0) -> dict[str, pd.DataFrame]:
    """Compare two daily PCT_CHANGE files and return threshold-based groupings."""
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

    common_above_threshold = merged[
        (merged["DAY1_PCT_CHANGE"].notna())
        & (merged["DAY2_PCT_CHANGE"].notna())
        & (merged["DAY1_PCT_CHANGE"] > threshold)
        & (merged["DAY2_PCT_CHANGE"] > threshold)
    ].copy()

    day1_only_above_threshold = merged[
        (merged["DAY1_PCT_CHANGE"].notna())
        & (merged["DAY2_PCT_CHANGE"].isna() | (merged["DAY2_PCT_CHANGE"] <= threshold))
        & (merged["DAY1_PCT_CHANGE"] > threshold)
    ].copy()

    day2_new_above_threshold = merged[
        (merged["DAY2_PCT_CHANGE"].notna())
        & (merged["DAY1_PCT_CHANGE"].isna())
        & (merged["DAY2_PCT_CHANGE"] > threshold)
    ].copy()

    for df in [common_above_threshold, day1_only_above_threshold, day2_new_above_threshold]:
        if not df.empty:
            df["TREND"] = df["DAY2_PCT_CHANGE"] - df["DAY1_PCT_CHANGE"]
            df["TREND_LABEL"] = df["TREND"].apply(lambda v: "up" if v > 0 else "down" if v < 0 else "flat")
            df.reset_index(drop=True, inplace=True)

    return {
        "common_above_threshold": common_above_threshold[[
            "SYMBOL",
            "DAY1_PCT_CHANGE",
            "DAY2_PCT_CHANGE",
            "DELTA_PCT_CHANGE",
            "TREND_LABEL",
        ]].rename(columns={"TREND_LABEL": "TREND"}) if not common_above_threshold.empty else common_above_threshold,
        "day1_only_above_threshold": day1_only_above_threshold[[
            "SYMBOL",
            "DAY1_PCT_CHANGE",
            "DAY2_PCT_CHANGE",
            "DELTA_PCT_CHANGE",
            "TREND_LABEL",
        ]].rename(columns={"TREND_LABEL": "TREND"}) if not day1_only_above_threshold.empty else day1_only_above_threshold,
        "day2_new_above_threshold": day2_new_above_threshold[[
            "SYMBOL",
            "DAY1_PCT_CHANGE",
            "DAY2_PCT_CHANGE",
            "DELTA_PCT_CHANGE",
            "TREND_LABEL",
        ]].rename(columns={"TREND_LABEL": "TREND"}) if not day2_new_above_threshold.empty else day2_new_above_threshold,
    }


def main() -> None:
    import sys

    if len(sys.argv) == 3:
        day1_path = sys.argv[1]
        day2_path = sys.argv[2]
    else:
        day1_path, day2_path = discover_default_files()

    grouped = compare_two_days(day1_path, day2_path)

    print(f"Comparing {os.path.basename(day1_path)} vs {os.path.basename(day2_path)}")
    print(f"Threshold: > 1%")

    for label, df in grouped.items():
        print(f"\n=== {label} ===")
        if df.empty:
            print("No stocks found")
        else:
            print(df.head(20).to_string(index=False))

    with pd.ExcelWriter(os.path.join(BASE_DIR, "two_day_comparison.xlsx")) as writer:
        for label, df in grouped.items():
            df.to_excel(writer, sheet_name=label[:31], index=False)

    for label, df in grouped.items():
        output_path = os.path.join(BASE_DIR, f"{label}.csv")
        df.to_csv(output_path, index=False)
        print(f"Saved -> {output_path}")

    print(f"Saved -> {os.path.join(BASE_DIR, 'two_day_comparison.xlsx')}")


if __name__ == "__main__":
    main()
