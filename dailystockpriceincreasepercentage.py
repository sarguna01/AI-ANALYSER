"""
NSE Daily % Change Tracker
----------------------------
Fetches NSE's official daily Bhavcopy (end-of-day price report) which
contains Open/High/Low/Close/Volume for EVERY listed stock (~2,300+),
and calculates the day's percentage change for each one.

Data source: NSE's official daily Bhavcopy CSV (UDiFF format).
This is the same file used by exchanges, brokers, and data vendors.

Usage:
    python nse_daily_change.py                  -> fetches today's bhavcopy
    python nse_daily_change.py 2026-08-05        -> fetches a specific date

Output:
    - bhavcopy_data/bhavcopy_YYYY-MM-DD.csv   -> raw OHLC data for the day
    - top_gainers_YYYY-MM-DD.csv              -> top 20 gainers
    - top_losers_YYYY-MM-DD.csv               -> top 20 losers
    - full_pct_change_YYYY-MM-DD.csv          -> % change for ALL stocks
"""

import requests
import pandas as pd
import os
import sys
from io import BytesIO
from zipfile import ZipFile
from datetime import date, datetime, timedelta

DATA_DIR = "bhavcopy_data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get_session():
    """NSE requires cookies from the homepage before serving data files."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://www.nseindia.com", timeout=10)
    return session


def build_bhavcopy_url(trade_date: date) -> str:
    """
    NSE's current (UDiFF) daily bhavcopy URL format:
    https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip
    """
    date_str = trade_date.strftime("%Y%m%d")
    return (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
    )


def fetch_bhavcopy(trade_date: date) -> pd.DataFrame:
    """Downloads and extracts the bhavcopy for a given date."""
    session = get_session()
    url = build_bhavcopy_url(trade_date)
    response = session.get(url, timeout=15)

    if response.status_code != 200:
        raise ValueError(
            f"Could not fetch bhavcopy for {trade_date} (status {response.status_code}). "
            f"NSE has no data for weekends/holidays, or format may have changed. URL tried: {url}"
        )

    with ZipFile(BytesIO(response.content)) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            df = pd.read_csv(f)

    df.columns = [c.strip() for c in df.columns]
    return df


def calculate_pct_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates % change using columns present in NSE's bhavcopy:
    typically 'ClsPric' (close) and 'PrvsClsgPric' (previous close).
    Falls back gracefully if column names differ.
    """
    close_col = next((c for c in df.columns if "ClsPric" in c or c == "CLOSE"), None)
    prev_close_col = next((c for c in df.columns if "PrvsClsgPric" in c or "PREV_CLOSE" in c), None)
    symbol_col = next((c for c in df.columns if c in ("TckrSymb", "SYMBOL")), None)

    if not all([close_col, prev_close_col, symbol_col]):
        raise ValueError(
            f"Expected columns not found. Available columns: {list(df.columns)}. "
            "NSE may have changed the bhavcopy format — inspect columns and adjust script."
        )

    df["PCT_CHANGE"] = (
        (df[close_col] - df[prev_close_col]) / df[prev_close_col] * 100
    ).round(2)

    result = df[[symbol_col, close_col, prev_close_col, "PCT_CHANGE"]].copy()
    result.columns = ["SYMBOL", "CLOSE", "PREV_CLOSE", "PCT_CHANGE"]
    return result.sort_values("PCT_CHANGE", ascending=False).reset_index(drop=True)


def main():
    # Allow optional date argument, else default to today
    if len(sys.argv) > 1:
        trade_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        trade_date = date.today()

    os.makedirs(DATA_DIR, exist_ok=True)
    date_str = trade_date.isoformat()

    print(f"Fetching NSE bhavcopy for {date_str}...")
    raw_df = fetch_bhavcopy(trade_date)
    raw_path = os.path.join(DATA_DIR, f"bhavcopy_{date_str}.csv")
    raw_df.to_csv(raw_path, index=False)
    print(f"Raw data saved -> {raw_path} ({len(raw_df)} rows)")

    pct_df = calculate_pct_change(raw_df)
    full_path = os.path.join(DATA_DIR, f"full_pct_change_{date_str}.csv")
    pct_df.to_csv(full_path, index=False)
    print(f"Full % change list (all {len(pct_df)} stocks) -> {full_path}")

    top_gainers = pct_df.head(20)
    top_losers = pct_df.tail(20).sort_values("PCT_CHANGE")

    gainers_path = os.path.join(DATA_DIR, f"top_gainers_{date_str}.csv")
    losers_path = os.path.join(DATA_DIR, f"top_losers_{date_str}.csv")
    top_gainers.to_csv(gainers_path, index=False)
    top_losers.to_csv(losers_path, index=False)

    print(f"\nTop 20 gainers -> {gainers_path}")
    print(top_gainers.to_string(index=False))

    print(f"\nTop 20 losers -> {losers_path}")
    print(top_losers.to_string(index=False))


if __name__ == "__main__":
    main()
