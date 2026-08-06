"""
NSE Stock List Tracker
-----------------------
Fetches the official, up-to-date list of all equities listed on NSE
(National Stock Exchange, India) and detects newly added stocks
(e.g. from recent IPOs) compared to the previous run.

Data source: NSE's own official CSV feed (not HTML scraping).
This is the same file NSE publishes for its "Equity List" download.

Usage:
    python nse_stock_tracker.py

Output:
    - nse_equity_list_YYYY-MM-DD.csv   -> full current list, snapshot for today
    - new_stocks_YYYY-MM-DD.csv        -> only the newly added symbols (if any)
    - Prints a summary to the console
"""

import requests
import pandas as pd
import os
from datetime import date

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
NSE_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_HOME_URL = "https://www.nseindia.com"
DATA_DIR = "nse_data"  # folder to store historical snapshots for diffing

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def get_session():
    """
    NSE requires a valid session/cookie obtained by first hitting the
    homepage before you can pull data files, otherwise requests get
    blocked (403).
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    # First hit homepage to collect cookies
    session.get(NSE_HOME_URL, timeout=10)
    return session


def fetch_nse_equity_list() -> pd.DataFrame:
    """Downloads the current NSE equity list as a DataFrame."""
    session = get_session()
    response = session.get(NSE_EQUITY_LIST_URL, timeout=15)
    response.raise_for_status()

    from io import StringIO
    df = pd.read_csv(StringIO(response.text))
    df.columns = [c.strip() for c in df.columns]  # clean column names
    return df


def save_snapshot(df: pd.DataFrame) -> str:
    """Saves today's snapshot to disk and returns the filepath."""
    os.makedirs(DATA_DIR, exist_ok=True)
    today_str = date.today().isoformat()
    filepath = os.path.join(DATA_DIR, f"nse_equity_list_{today_str}.csv")
    df.to_csv(filepath, index=False)
    return filepath


def get_previous_snapshot(exclude_file: str):
    """
    Finds the most recent previous snapshot in DATA_DIR (other than
    today's), so we can compare and detect new listings.
    """
    if not os.path.isdir(DATA_DIR):
        return None

    files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.startswith("nse_equity_list_") and f.endswith(".csv") and f != os.path.basename(exclude_file)
    )
    if not files:
        return None

    latest_previous = files[-1]  # most recent before today (alphabetical = chronological here)
    return os.path.join(DATA_DIR, latest_previous)


def find_new_stocks(today_df: pd.DataFrame, previous_path: str) -> pd.DataFrame:
    """Compares today's list against the previous snapshot to find new symbols."""
    prev_df = pd.read_csv(previous_path)
    prev_df.columns = [c.strip() for c in prev_df.columns]

    symbol_col = "SYMBOL" if "SYMBOL" in today_df.columns else today_df.columns[0]

    old_symbols = set(prev_df[symbol_col])
    new_symbols = set(today_df[symbol_col]) - old_symbols

    return today_df[today_df[symbol_col].isin(new_symbols)]


def main():
    print("Fetching latest NSE equity list...")
    df = fetch_nse_equity_list()
    print(f"Total stocks currently listed on NSE: {len(df)}")

    today_path = save_snapshot(df)
    print(f"Saved today's snapshot -> {today_path}")

    previous_path = get_previous_snapshot(today_path)

    if previous_path:
        new_stocks = find_new_stocks(df, previous_path)
        if not new_stocks.empty:
            new_path = os.path.join(DATA_DIR, f"new_stocks_{date.today().isoformat()}.csv")
            new_stocks.to_csv(new_path, index=False)
            print(f"\n{len(new_stocks)} NEW stock(s) found since last run:")
            print(new_stocks.to_string(index=False))
            print(f"\nSaved -> {new_path}")
        else:
            print("\nNo new stocks since the last run.")
    else:
        print("\nNo previous snapshot found — this is the first run. "
              "Run this script again tomorrow (or after the next trading day) "
              "to start detecting newly listed stocks.")


if __name__ == "__main__":
    main()