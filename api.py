import time
from datetime import datetime
import yfinance as yf
import pandas as pd

# ---------- CONFIG ----------
OUTPUT_CSV = "stock_minute_data.csv"
INTERVAL_SECONDS = 60  # 1 minute
STOCK_SYMBOL = "tcs.NS"  # Use Yahoo Finance symbol: NSE = .NS, BSE = .BO
# ---------------------------


def get_yahoo_quote():
    """Fetch the current stock quote from Yahoo Finance via yfinance."""
    ticker = yf.Ticker(STOCK_SYMBOL)

    # Try fast history first, then fall back to the info endpoint
    price = None
    try:
        history = ticker.history(period="1d", interval="1m")
        if not history.empty:
            price = float(history["Close"].iloc[-1])
    except Exception:
        price = None

    if price is None:
        info = ticker.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")

    if price is None:
        raise ValueError(f"No quote returned for {STOCK_SYMBOL}")

    return {
        "symbol": STOCK_SYMBOL,
        "price": price,
        "source": "yahoo_finance",
    }


def main():
    print("Fetching stock price from Yahoo Finance...")
    print(f"Tracking {STOCK_SYMBOL} every {INTERVAL_SECONDS} seconds.")
    print("Press Ctrl+C to stop.\n")

    try:
        _ = pd.read_csv(OUTPUT_CSV)
    except FileNotFoundError:
        df_empty = pd.DataFrame(columns=["timestamp", "Stock_Name", "price", "source"])
        df_empty.to_csv(OUTPUT_CSV, index=False)

    while True:
        try:
            ts = datetime.now().isoformat()
            print(f"[{ts}] Fetching price for {STOCK_SYMBOL}...")

            quote = get_yahoo_quote()
            row = {
                "timestamp": ts,
                "Stock_Name": quote["symbol"],
                "price": quote["price"],
                "source": quote["source"],
            }

            df_new = pd.DataFrame([row])
            df_existing = pd.read_csv(OUTPUT_CSV)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(OUTPUT_CSV, index=False)

            print(f"[{ts}] {quote['symbol']} = {quote['price']}. Saved row. Next fetch in {INTERVAL_SECONDS}s.")

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(5)

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
