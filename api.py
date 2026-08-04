import time
from datetime import datetime
from nsepython import nsefetch, nse_get_index_quote
import pandas as pd

# ---------- CONFIG ----------
OUTPUT_CSV = "nifty50_minute_data.csv"
INTERVAL_SECONDS = 60  # 1 minute
INDEX_SYMBOL = "NIFTY 50"
# ---------------------------

def get_nifty_index_quote():
    """Fetch the live NIFTY 50 index quote from NSE.

    This function first tries the NSE quote-index endpoint. If that returns
    no price, it falls back to the Nifty live indices feed.
    """
    # First try the NSE quote-index API
    url = f"https://www.nseindia.com/api/quote-index?symbol={INDEX_SYMBOL}"
    data = nsefetch(url)
    info = data.get("priceInfo", {})
    last_price = info.get("lastPrice")
    if last_price is not None:
        return {
            "symbol": INDEX_SYMBOL,
            "lastPrice": last_price,
            "open": info.get("open"),
            "high": info.get("dayHigh"),
            "low": info.get("dayLow"),
            "close": info.get("previousClose"),
            "source": "nse_quote_index",
        }

    # Fallback: try the live indices feed
    try:
        payload = nse_get_index_quote(INDEX_SYMBOL)
        return {
            "symbol": INDEX_SYMBOL,
            "lastPrice": payload.get("lastPrice"),
            "open": payload.get("open"),
            "high": payload.get("high"),
            "low": payload.get("low"),
            "close": payload.get("previousClose"),
            "source": "nifty_live_indices",
        }
    except Exception:
        return {
            "symbol": INDEX_SYMBOL,
            "lastPrice": None,
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "source": "nse_quote_index",
        }

def main():
    print("Fetching NIFTY 50 index price...")
    print(f"Tracking {INDEX_SYMBOL} every {INTERVAL_SECONDS} seconds.")
    print("Press Ctrl+C to stop.\n")

    # Prepare CSV header if file doesn't exist
    try:
        _ = pd.read_csv(OUTPUT_CSV)
    except FileNotFoundError:
        df_empty = pd.DataFrame(columns=["timestamp", "nifty50_price", "source"])
        df_empty.to_csv(OUTPUT_CSV, index=False)

    while True:
        try:
            ts = datetime.now().isoformat()
            print(f"[{ts}] Fetching NIFTY 50 price...")

            quote = get_nifty_index_quote()
            row = {
                "timestamp": ts,
                "nifty50_price": quote["lastPrice"],
            }

            df_new = pd.DataFrame([row])
            df_existing = pd.read_csv(OUTPUT_CSV)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(OUTPUT_CSV, index=False)

            print(f"[{ts}] NIFTY 50 = {quote['lastPrice']}. Saved row. Next fetch in {INTERVAL_SECONDS}s.")

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(5)

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
