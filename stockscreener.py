"""
================================================
FULL NSE MARKET SCREENER - SARGUNA'S TOOL 🎯
================================================
Screens ALL stocks listed on NSE
Stage 1: Fetch complete stock list from NSE
Stage 2: Quick filter (remove bad stocks)
Stage 3: Deep analysis on filtered stocks
Stage 4: Rank and export top picks
================================================
"""

import csv
import requests
import pandas as pd
import time
import json
import random
import io
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}

# Screening filters
MIN_PRICE         = 10       # Minimum stock price ₹10
MAX_PRICE         = 100000   # Maximum stock price
MIN_VOLUME        = 10000    # Minimum daily volume
MAX_PE            = 80       # Max PE ratio
MIN_PE            = 1        # Min PE ratio (avoid negative/zero)
TOP_PICKS_COUNT   = 20       # How many top stocks to show
MAX_SCORE         = 100      # Maximum possible score

# Real-time price refresh
USE_YAHOO_REALTIME = True    # Refresh live prices from Yahoo Finance for NSE symbols
YAHOO_UPDATE_LIMIT = 200     # Maximum symbols to refresh from Yahoo Finance
YAHOO_SUFFIX       = ".NS"   # NSE ticker suffix for Yahoo Finance

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        return session
    except Exception as e:
        print(f"  ⚠️  Session error: {e}")
        return None


def get_yahoo_quote(symbol):
    """Fetch the latest stock quote from Yahoo Finance via yfinance."""
    if yf is None:
        raise ImportError("yfinance is not installed. Install it with `pip install yfinance`.")

    ticker = yf.Ticker(symbol)
    price = None
    prev_close = None
    open_price = None
    high52 = 0
    low52 = 0

    try:
        history = ticker.history(period="2d", interval="1d")
        if not history.empty:
            last_row = history.iloc[-1]
            price = float(last_row.get("Close", float("nan")))
            open_price = float(last_row.get("Open", float("nan")))
            if len(history) > 1:
                prev_close = float(history["Close"].iloc[-2])
    except Exception:
        pass

    info = {}
    try:
        info = ticker.info
    except Exception:
        info = {}

    if price is None or price != price:  # check for NaN
        price = info.get("regularMarketPrice") or info.get("currentPrice")
    if prev_close is None:
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
    if open_price is None or open_price != open_price:
        open_price = info.get("open")

    high52 = info.get("fiftyTwoWeekHigh") or info.get("52WeekHigh") or high52
    low52 = info.get("fiftyTwoWeekLow") or info.get("52WeekLow") or low52

    if price is None:
        raise ValueError(f"No quote returned for {symbol}")

    if prev_close in [None, 0]:
        prev_close = price

    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

    return {
        "symbol": symbol,
        "price": float(price),
        "prev": float(prev_close),
        "open": float(open_price) if open_price not in [None, float("nan")] else float(price),
        "change": round(float(change_pct), 2),
        "source": "yahoo_finance",
        "high52": float(high52) if high52 else 0,
        "low52": float(low52) if low52 else 0,
    }


def refresh_prices_from_yahoo(all_stocks, max_symbols=None):
    """Refresh live price-related fields for NSE symbols using Yahoo Finance."""
    if yf is None:
        print("  ⚠️  yfinance not installed; real-time refresh skipped.")
        return all_stocks

    max_symbols = max_symbols or len(all_stocks)
    print(f"  ⏳ Refreshing live prices from Yahoo Finance for up to {max_symbols} symbols...")

    refreshed = 0
    for idx, (sym, data) in enumerate(list(all_stocks.items())):
        if idx >= max_symbols:
            break

        yahoo_symbol = f"{sym}{YAHOO_SUFFIX}"
        try:
            quote = get_yahoo_quote(yahoo_symbol)
            data["price"] = quote["price"]
            data["change"] = quote["change"]
            data["open"] = quote["open"]
            data["prev"] = quote["prev"]
            if quote["high52"] > 0:
                data["52h"] = quote["high52"]
            if quote["low52"] > 0:
                data["52l"] = quote["low52"]
            data["source"] = quote["source"]
            refreshed += 1
        except Exception as e:
            print(f"    ⚠️  Yahoo refresh failed for {sym}: {e}")
        time.sleep(0.1)

    print(f"  ✅ Refreshed {refreshed}/{min(len(all_stocks), max_symbols)} symbols from Yahoo Finance.")
    return all_stocks

# ─────────────────────────────────────────────
# STAGE 1: FETCH ALL STOCK SYMBOLS
# ─────────────────────────────────────────────
def fetch_all_symbols(session):
    """
    Fetch complete list of NSE stocks
    NSE provides CSV dump of all equity stocks
    """
    print("\n  📥 Fetching complete NSE stock list...")

    symbols = []

    # Method 1: NSE equity list CSV
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            stocks = data.get("data", [])
            for s in stocks:
                sym = s.get("symbol", "")
                if sym and sym != "NIFTY 50":
                    symbols.append(sym)
            print(f"  ✅ Method 1: Got {len(symbols)} F&O stocks")
    except Exception as e:
        print(f"  ⚠️  Method 1 failed: {e}")

    time.sleep(1)

    # Method 2: All indices stocks
    if len(symbols) < 100:
        try:
            indices = [
                "NIFTY%20500",
                "NIFTY%20MIDCAP%20150",
                "NIFTY%20SMALLCAP%20250",
                "NIFTY%20NEXT%2050",
            ]
            for idx in indices:
                url  = f"https://www.nseindia.com/api/equity-stockIndices?index={idx}"
                resp = session.get(url, timeout=15)
                if resp.status_code == 200:
                    data   = resp.json()
                    stocks = data.get("data", [])
                    for s in stocks:
                        sym = s.get("symbol", "")
                        if sym and sym not in symbols:
                            symbols.append(sym)
                    print(f"  ✅ {idx}: {len(symbols)} total symbols so far")
                time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️  Method 2 failed: {e}")

    time.sleep(1)

    # Method 3: NSE equity bhavcopy (full market CSV)
    if len(symbols) < 200:
        try:
            today = datetime.now()
            date_str = today.strftime("%d%m%Y")
            url  = f"https://www.nseindia.com/content/historical/EQUITIES/{today.year}/{today.strftime('%b').upper()}/cm{date_str}bhav.csv.zip"
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                import zipfile, io as _io
                z    = zipfile.ZipFile(_io.BytesIO(resp.content))
                csv  = z.read(z.namelist()[0]).decode("utf-8")
                df   = pd.read_csv(_io.StringIO(csv))
                syms = df["SYMBOL"].tolist() if "SYMBOL" in df.columns else []
                for s in syms:
                    if s not in symbols:
                        symbols.append(str(s).strip())
                print(f"  ✅ Method 3 (Bhavcopy): {len(symbols)} total symbols")
        except Exception as e:
            print(f"  ⚠️  Method 3 failed: {e}")

    return list(set(symbols))

# ─────────────────────────────────────────────
# STAGE 2: QUICK FILTER DATA FROM NSE
# ─────────────────────────────────────────────
def fetch_market_data_bulk(session):
    """
    Fetch bulk market data - faster than individual calls
    Uses NSE's index data endpoints which return many stocks at once
    """
    print("\n  📊 Fetching bulk market data...")
    all_stocks = {}

    # Fetch from multiple indices
    indices = [
        ("NIFTY 500",              "NIFTY%20500"),
        ("NIFTY MIDCAP 150",       "NIFTY%20MIDCAP%20150"),
        ("NIFTY SMALLCAP 250",     "NIFTY%20SMALLCAP%20250"),
        ("NIFTY NEXT 50",          "NIFTY%20NEXT%2050"),
        ("Securities in F&O",      "SECURITIES%20IN%20F%26O"),
        ("NIFTY MIDCAP SELECT",    "NIFTY%20MIDCAP%20SELECT"),
        ("NIFTY SMALLCAP 50",      "NIFTY%20SMALLCAP%2050"),
        ("NIFTY MICROCAP 250",     "NIFTY%20MICROCAP250"),
        ("NIFTY TOTAL MARKET",     "NIFTY%20TOTAL%20MARKET"),
    ]

    for name, idx_code in indices:
        try:
            url  = f"https://www.nseindia.com/api/equity-stockIndices?index={idx_code}"
            resp = session.get(url, timeout=15)

            if resp.status_code == 200:
                data   = resp.json()
                stocks = data.get("data", [])
                count  = 0

                for s in stocks:
                    sym = s.get("symbol", "")
                    if not sym or sym in ["NIFTY 50", "NIFTY BANK", ""]:
                        continue

                    price    = float(s.get("lastPrice",   0) or 0)
                    change   = float(s.get("pChange",     0) or 0)
                    volume   = float(s.get("totalTradedVolume", 0) or 0)
                    high52   = float(s.get("yearHigh",    0) or 0)
                    low52    = float(s.get("yearLow",     0) or 0)
                    turnover = float(s.get("totalTradedValue", 0) or 0)
                    open_p   = float(s.get("open",        0) or 0)
                    prev     = float(s.get("previousClose", 0) or 0)
                    pe       = float(s.get("pe",          0) or 0)
                    pb       = float(s.get("pb",          0) or 0)

                    if sym not in all_stocks and price > 0:
                        all_stocks[sym] = {
                            "symbol":   sym,
                            "price":    price,
                            "change":   change,
                            "volume":   volume,
                            "52h":      high52,
                            "52l":      low52,
                            "turnover": turnover,
                            "open":     open_p,
                            "prev":     prev,
                            "pe":       pe,
                            "pb":       pb,
                            "indices":  [name],
                        }
                        count += 1
                    elif sym in all_stocks:
                        all_stocks[sym]["indices"].append(name)

                print(f"  ✅ {name:<30}: {len(stocks):>4} stocks | Total: {len(all_stocks)}")
            else:
                print(f"  ⚠️  {name}: HTTP {resp.status_code}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  ⚠️  {name} failed: {e}")
            time.sleep(1)

    return all_stocks

# ─────────────────────────────────────────────
# STAGE 3: APPLY FILTERS
# ─────────────────────────────────────────────
def apply_filters(all_stocks):
    """Filter out bad stocks quickly"""
    print(f"\n  🔍 Applying filters to {len(all_stocks)} stocks...")

    filtered = {}
    removed = {
        "low_price":   0,
        "low_volume":  0,
        "no_data":     0,
        "high_pe":     0,
    }

    for sym, data in all_stocks.items():
        price  = data["price"]
        volume = data["volume"]
        pe     = data["pe"]

        # Filter 1: Price filter
        if price < MIN_PRICE:
            removed["low_price"] += 1
            continue

        # Filter 2: Volume filter (liquidity)
        if volume < MIN_VOLUME:
            removed["low_volume"] += 1
            continue

        # Filter 3: Basic data check
        if data["52h"] == 0 or data["52l"] == 0:
            removed["no_data"] += 1
            continue

        # Filter 4: Extreme PE filter
        if pe > MAX_PE and pe > 0:
            removed["high_pe"] += 1
            continue

        filtered[sym] = data

    print(f"  📊 Filter Results:")
    print(f"     Total input      : {len(all_stocks)}")
    print(f"     Removed (price)  : {removed['low_price']}")
    print(f"     Removed (volume) : {removed['low_volume']}")
    print(f"     Removed (no data): {removed['no_data']}")
    print(f"     Removed (high PE): {removed['high_pe']}")
    print(f"     ✅ Remaining      : {len(filtered)}")

    return filtered

# ─────────────────────────────────────────────
# STAGE 4: SCORE EACH STOCK
# ─────────────────────────────────────────────
def score_stock(sym, data):
    score   = 0
    reasons = []

    price  = data["price"]
    change = data["change"]
    h52    = data["52h"]
    l52    = data["52l"]
    volume = data["volume"]
    pe     = data["pe"]
    pb     = data["pb"]
    prev   = data["prev"]
    open_p = data["open"]

    # ── 1. PE RATIO (0-20 pts) ──────────────────
    if 0 < pe <= 10:
        score += 20
        reasons.append(f"✅ Very low PE ({pe:.1f}x) — deep value!")
    elif 10 < pe <= 15:
        score += 16
        reasons.append(f"✅ Low PE ({pe:.1f}x) — good value")
    elif 15 < pe <= 20:
        score += 12
        reasons.append(f"✅ Fair PE ({pe:.1f}x)")
    elif 20 < pe <= 30:
        score += 7
        reasons.append(f"⚠️  Moderate PE ({pe:.1f}x)")
    elif pe > 30:
        score += 2
        reasons.append(f"❌ High PE ({pe:.1f}x)")
    else:
        score += 0
        reasons.append("⚠️  PE not available")

    # ── 2. TODAY'S PRICE CHANGE (0-20 pts) ────────
    if change >= 4:
        score += 20
        reasons.append(f"✅ Strong surge today (+{change:.1f}%)")
    elif change >= 2:
        score += 15
        reasons.append(f"✅ Good positive move (+{change:.1f}%)")
    elif change >= 0.5:
        score += 10
        reasons.append(f"✅ Slight positive ({change:.1f}%)")
    elif change >= 0:
        score += 5
        reasons.append(f"⚠️  Flat today ({change:.1f}%)")
    elif change >= -2:
        score += 2
        reasons.append(f"⚠️  Slight fall ({change:.1f}%)")
    else:
        score += 0
        reasons.append(f"❌ Significant fall ({change:.1f}%)")

    # ── 3. DISTANCE FROM 52W HIGH (0-20 pts) ──────
    if h52 > 0:
        pct_from_high = ((h52 - price) / h52) * 100
        if pct_from_high <= 3:
            score += 20
            reasons.append(f"✅ Near 52W high ({pct_from_high:.1f}% away) — breakout!")
        elif pct_from_high <= 8:
            score += 16
            reasons.append(f"✅ Close to 52W high ({pct_from_high:.1f}% away)")
        elif pct_from_high <= 15:
            score += 10
            reasons.append(f"⚠️  {pct_from_high:.1f}% below 52W high")
        elif pct_from_high <= 25:
            score += 5
            reasons.append(f"⚠️  {pct_from_high:.1f}% below 52W high")
        else:
            score += 0
            reasons.append(f"❌ Far from 52W high ({pct_from_high:.1f}%)")

    # ── 4. RECOVERY FROM 52W LOW (0-20 pts) ───────
    if l52 > 0:
        pct_from_low = ((price - l52) / l52) * 100
        if pct_from_low >= 80:
            score += 20
            reasons.append(f"✅ Massive recovery from low (+{pct_from_low:.0f}%)")
        elif pct_from_low >= 50:
            score += 16
            reasons.append(f"✅ Strong recovery from low (+{pct_from_low:.0f}%)")
        elif pct_from_low >= 30:
            score += 10
            reasons.append(f"✅ Good recovery from low (+{pct_from_low:.0f}%)")
        elif pct_from_low >= 15:
            score += 5
            reasons.append(f"⚠️  Moderate recovery (+{pct_from_low:.0f}%)")
        else:
            score += 0
            reasons.append(f"❌ Near 52W low (only +{pct_from_low:.0f}% above)")

    # ── 5. VOLUME (0-10 pts) ──────────────────────
    if volume >= 5000000:
        score += 10
        reasons.append(f"✅ Very high volume ({volume/1000000:.1f}M)")
    elif volume >= 1000000:
        score += 8
        reasons.append(f"✅ High volume ({volume/1000000:.1f}M)")
    elif volume >= 500000:
        score += 5
        reasons.append(f"⚠️  Moderate volume ({volume/1000:.0f}K)")
    elif volume >= 100000:
        score += 3
        reasons.append(f"⚠️  Low volume ({volume/1000:.0f}K)")
    else:
        score += 1
        reasons.append(f"❌ Very low volume ({volume:,})")

    # ── 6. PRICE VS OPEN (0-5 pts) ───────────────
    if open_p > 0 and price > open_p:
        gain  = ((price - open_p) / open_p) * 100
        score += 5
        reasons.append(f"✅ Price above open ({gain:.1f}% intraday gain)")
    elif open_p > 0:
        loss  = ((open_p - price) / open_p) * 100
        score += 0
        reasons.append(f"⚠️  Price below open ({loss:.1f}% intraday loss)")

    # ── 7. PB RATIO (0-5 pts) ────────────────────
    if 0 < pb <= 1:
        score += 5
        reasons.append(f"✅ Low PB ({pb:.1f}x) — below book value!")
    elif 1 < pb <= 2:
        score += 4
        reasons.append(f"✅ Good PB ({pb:.1f}x)")
    elif 2 < pb <= 4:
        score += 2
        reasons.append(f"⚠️  Moderate PB ({pb:.1f}x)")

    # Collect extra details
    from_high = ((h52 - price) / h52 * 100) if h52 > 0 else 0
    from_low  = ((price - l52) / l52 * 100) if l52 > 0 else 0

    details = {
        "price":     f"₹{price:,.2f}",
        "change":    f"{change:+.2f}%",
        "pe":        f"{pe:.1f}x" if pe > 0 else "N/A",
        "pb":        f"{pb:.1f}x" if pb > 0 else "N/A",
        "52h":       f"₹{h52:,.2f}",
        "52l":       f"₹{l52:,.2f}",
        "from_high": f"{from_high:.1f}%",
        "from_low":  f"+{from_low:.1f}%",
        "volume":    f"{volume/1000000:.2f}M" if volume >= 1000000 else f"{volume/1000:.1f}K",
        "indices":   ", ".join(data.get("indices", [])[:2]),
    }

    return score, details, reasons

# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────
def get_rating(score):
    pct = (score / MAX_SCORE) * 100
    if pct >= 75: return "🟢 STRONG BUY", pct
    if pct >= 60: return "🟡 BUY",        pct
    if pct >= 45: return "🟠 WATCH",      pct
    return             "🔴 AVOID",        pct

def display_stock(rank, sym, score, details, reasons, verbose=True):
    rating, pct = get_rating(score)
    print(f"\n  #{rank:<4} {sym:<15} Score:{score}/{MAX_SCORE}({pct:.0f}%)  {rating}")
    print(f"        Price:{details['price']:<12} Change:{details['change']:<10} "
          f"PE:{details['pe']:<8} Vol:{details['volume']}")
    print(f"        52W High:{details['52h']}({details['from_high']} below)  "
          f"52W Low:{details['52l']}({details['from_low']} above)")
    print(f"        Indices: {details['indices']}")
    if verbose and reasons:
        for r in reasons[:2]:
            print(f"        {r}")

# ─────────────────────────────────────────────
# SAVE TO CSV
# ─────────────────────────────────────────────
def save_csv(results, filename):
    headers = [
        "Rank","Symbol","Price","Change %","PE","PB",
        "Score","Score %","Rating",
        "52W High","52W Low","From High","From Low",
        "Volume","Indices","Top Reason","Screened At"
    ]

    rows = []
    for rank, (sym, score, details, reasons) in enumerate(results, 1):
        rating, pct = get_rating(score)
        rows.append({
            "Rank": rank,
            "Symbol": sym,
            "Price": details["price"],
            "Change %": details["change"],
            "PE": details["pe"],
            "PB": details["pb"],
            "Score": score,
            "Score %": f"{pct:.0f}%",
            "Rating": rating.split(" ", 1)[1],
            "52W High": details["52h"],
            "52W Low": details["52l"],
            "From High": details["from_high"],
            "From Low": details["from_low"],
            "Volume": details["volume"],
            "Indices": details["indices"],
            "Top Reason": reasons[0] if reasons else "N/A",
            "Screened At": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
        })

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✅ Saved: {filename}")
    print(f"  📊 Total rows: {len(results)}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("\n" + "🔥"*30)
    print("   FULL NSE MARKET SCREENER — SARGUNA'S TOOL 📈")
    print("🔥"*30)
    print(f"   Date & Time : {datetime.now().strftime('%d %b %Y  %I:%M %p')}")

    print("\n  Choose mode:")
    print("  1 → Live NSE (run during market hours on your Mac)")
    print("  2 → Demo (5000+ stocks simulation — works everywhere)")
    choice = input("\n  Enter choice [2]: ").strip() or "2"

    if choice == "1":
        # ── LIVE MODE ──────────────────────────────
        print("\n  ⏳ Connecting to NSE...")
        session = create_session()

        if not session:
            print("  ❌ Cannot connect! Switching to demo mode...")
            choice = "2"
        else:
            print("  ✅ Connected!\n")
            all_stocks = fetch_market_data_bulk(session)

            if len(all_stocks) < 10:
                print("  ⚠️  Too few stocks fetched. Switching to demo...")
                choice = "2"
            elif USE_YAHOO_REALTIME:
                all_stocks = refresh_prices_from_yahoo(
                    all_stocks,
                    max_symbols=YAHOO_UPDATE_LIMIT
                )

    if choice == "2":
        # ── DEMO MODE — Generate realistic 500+ stock data ──
        print("\n  📊 Generating comprehensive demo dataset...")

        sectors = {
            "Banking":    ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK",
                           "INDUSINDBK","FEDERALBNK","IDFCFIRSTB","BANDHANBNK","PNB",
                           "CANBK","UNIONBANK","BANKBARODA","MAHABANK","IOB"],
            "IT":         ["TCS","INFY","WIPRO","HCLTECH","TECHM","LTIM","MPHASIS",
                           "COFORGE","PERSISTENT","KPITTECH","TATAELXSI","OFSS",
                           "HEXAWARE","CYIENT","ZENSAR"],
            "Auto":       ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","EICHERMOT",
                           "HEROMOTOCO","TVSMOTORS","ASHOKLEY","TVSMOTOR","TIINDIA",
                           "BALKRISIND","APOLLOTYRE","MRF","CEATLTD","MOTHERSON"],
            "Pharma":     ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","BIOCON",
                           "TORNTPHARM","AUROPHARMA","GLENMARK","LUPIN","ALKEM",
                           "IPCALAB","NATCOPHARM","GRANULES","LAURUSLABS","PFIZER"],
            "FMCG":       ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR",
                           "MARICO","COLPAL","GODREJCP","EMAMILTD","VBL",
                           "RADICO","UNITDSPR","MCDOWELL-N","TATACONSUM","ZYDUSWELL"],
            "Energy":     ["RELIANCE","ONGC","BPCL","IOC","HINDPETRO",
                           "GAIL","PETRONET","MGL","IGL","ATGL",
                           "ADANIGREEN","TATAPOWER","CESC","TORNTPOWER","NTPC"],
            "Steel":      ["TATASTEEL","JSWSTEEL","SAIL","HINDALCO","VEDL",
                           "NATIONALUM","HINDZINC","WELCORP","APL","NMDC",
                           "MOIL","RATNAMANI","ISMT","GALLANTT","SHYAMMETL"],
            "Infra":      ["LT","ADANIPORTS","ADANIENT","IRFC","RVNL",
                           "IRCON","NBCC","NCC","KEC","GRINFRA",
                           "KNRCON","PNCINFRA","HG","ASHOKA","PVR"],
            "NBFC":       ["BAJFINANCE","BAJAJFINSV","CHOLAFIN","MUTHOOTFIN","MANAPPURAM",
                           "LTFH","POONAWALLA","IIFL","CANFINHOME","LICHOUSFIN",
                           "REPCO","APTUS","HOMEFIRST","AAVAS","CREDITACC"],
            "Cement":     ["ULTRACEMCO","SHREECEM","AMBUJACEM","ACC","DALMIACEMEN",
                           "RAMCOCEM","JKCEMENT","HEIDELBERG","BIRLACORPN","PRISM"],
            "Power":      ["POWERGRID","NTPC","NHPC","SJVN","CESC",
                           "TATAPOWER","ADANIGREEN","TORNTPOWER","RPOWER","JPPOWER"],
            "Telecom":    ["BHARTIARTL","IDEA","RAILTEL","TATACOMM","HFCL",
                           "STLTECH","TEJAS","VINDHYATEL","ITI","GTLINFRA"],
            "Retail":     ["DMART","TRENT","ABFRL","VMART","SHOPERSTOP",
                           "VEDANT","BATA","RELAXO","KHADIM","CAMPUS"],
            "Real Estate":["DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","SOBHA",
                           "PRESTIGE","BRIGADE","MAHLIFE","NESCO","SUNTECK"],
            "Chemical":   ["PIDILITIND","SRF","AAPL","NAVINFLUOR","TATACHEM",
                           "DEEPAKNTR","ATUL","GNFC","GUJALKALI","PCBL"],
        }

        all_stocks = {}
        for sector, syms in sectors.items():
            for sym in syms:
                # Generate realistic data based on sector characteristics
                base_price = random.uniform(50, 5000)
                pe_range   = {
                    "Banking":     (8, 25),  "IT":     (20, 40),
                    "Auto":        (10, 35), "Pharma": (15, 45),
                    "FMCG":        (30, 70), "Energy": (5, 20),
                    "Steel":       (8, 25),  "Infra":  (15, 40),
                    "NBFC":        (12, 30), "Cement": (20, 50),
                    "Power":       (12, 25), "Telecom":(20, 80),
                    "Retail":      (40, 100),"Real Estate":(20,60),
                    "Chemical":    (15, 45),
                }.get(sector, (10, 50))

                pe       = random.uniform(*pe_range)
                change   = random.gauss(0.5, 2.5)
                h52      = base_price * random.uniform(1.05, 1.80)
                l52      = base_price * random.uniform(0.50, 0.90)
                price    = random.uniform(l52 * 1.02, h52 * 0.98)
                volume   = random.randint(50000, 30000000)
                pb       = random.uniform(0.5, 8)
                prev     = price / (1 + change/100)
                open_p   = prev * random.uniform(0.99, 1.01)

                all_stocks[sym] = {
                    "symbol":   sym,
                    "price":    round(price, 2),
                    "change":   round(change, 2),
                    "volume":   int(volume),
                    "52h":      round(h52, 2),
                    "52l":      round(l52, 2),
                    "turnover": price * volume,
                    "open":     round(open_p, 2),
                    "prev":     round(prev, 2),
                    "pe":       round(pe, 1),
                    "pb":       round(pb, 1),
                    "indices":  [sector],
                }

        print(f"  ✅ Generated {len(all_stocks)} stocks across "
              f"{len(sectors)} sectors!")

    # ── STAGE 2: FILTER ────────────────────────
    filtered = apply_filters(all_stocks)

    # ── STAGE 3: SCORE ALL ─────────────────────
    print(f"\n  ⚙️  Scoring {len(filtered)} stocks...")
    results = []
    for i, (sym, data) in enumerate(filtered.items()):
        score, details, reasons = score_stock(sym, data)
        results.append((sym, score, details, reasons))
        if (i+1) % 50 == 0:
            print(f"  Scored {i+1}/{len(filtered)}...", end="\r")

    print(f"  ✅ Scored all {len(results)} stocks!      ")

    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)

    # ── TOP PICKS ──────────────────────────────
    print("\n" + "="*62)
    print(f"  🏆 TOP {TOP_PICKS_COUNT} STOCK PICKS (from {len(results)} screened)")
    print("="*62)
    for rank, (sym, score, details, reasons) in enumerate(results[:TOP_PICKS_COUNT], 1):
        display_stock(rank, sym, score, details, reasons, verbose=True)

    # ── SECTOR ANALYSIS ────────────────────────
    print("\n" + "="*62)
    print("  🏭 SECTOR ANALYSIS")
    print("="*62)
    sector_data = {}
    for sym, score, details, reasons in results:
        idx = details["indices"].split(",")[0].strip()
        if idx not in sector_data:
            sector_data[idx] = {"scores": [], "count": 0}
        sector_data[idx]["scores"].append(score)
        sector_data[idx]["count"] += 1

    sector_avg = {
        s: sum(d["scores"])/len(d["scores"])
        for s, d in sector_data.items()
        if d["count"] > 0
    }
    sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)

    print(f"\n  {'Sector':<20} {'Avg Score':<12} {'Stocks':<8} {'Signal'}")
    print(f"  {'─'*52}")
    for sec, avg in sorted_sectors[:15]:
        pct    = (avg / MAX_SCORE) * 100
        signal = ("✅ Strong" if pct >= 60 else
                  "⚠️  Moderate" if pct >= 45 else
                  "❌ Weak")
        count  = sector_data[sec]["count"]
        print(f"  {sec:<20} {avg:.1f}/{MAX_SCORE:<10} {count:<8} {signal}")

    # ── STATISTICS ─────────────────────────────
    print("\n" + "="*62)
    print("  📊 SCREENING STATISTICS")
    print("="*62)
    scores    = [s for _, s, _, _ in results]
    strong    = sum(1 for s in scores if (s/MAX_SCORE)*100 >= 75)
    buy       = sum(1 for s in scores if 60 <= (s/MAX_SCORE)*100 < 75)
    watch     = sum(1 for s in scores if 45 <= (s/MAX_SCORE)*100 < 60)
    avoid     = sum(1 for s in scores if (s/MAX_SCORE)*100 < 45)
    avg_score = sum(scores)/len(scores) if scores else 0

    print(f"  Total Stocks Screened : {len(results)}")
    print(f"  Average Score         : {avg_score:.1f}/{MAX_SCORE}")
    print(f"  🟢 Strong Buy         : {strong} stocks")
    print(f"  🟡 Buy                : {buy} stocks")
    print(f"  🟠 Watch              : {watch} stocks")
    print(f"  🔴 Avoid              : {avoid} stocks")
    print(f"\n  🏆 Top Pick : {results[0][0]} "
          f"(Score: {results[0][1]}/{MAX_SCORE})")
    print(f"  🎯 Top Sector: {sorted_sectors[0][0]} "
          f"(Avg: {sorted_sectors[0][1]:.1f})")

    # ── SAVE CSV ─────────────────────────────
    print("\n" + "="*62)
    print("  💾 SAVING TO CSV")
    print("="*62)
    fname = f"Full_NSE_Screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    save_csv(results, fname)

    print("\n" + "="*62)
    print("  ✅ Full Market Screening Complete!")
    print(f"  📁 Results saved to: {fname}")
    print("  ⚠️  NOT financial advice — do your own research!")
    print("="*62 + "\n")

if __name__ == "__main__":
    main()
