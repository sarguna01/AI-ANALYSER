"""
================================================
NSE STOCK SCREENER - SARGUNA'S TOOL 🎯
================================================
Mode 1: Live NSE API (run on your Mac)
Mode 2: Demo with sample data (for testing)
================================================
"""

import csv
import requests
import json
import time
from datetime import datetime
import random

random.seed(42)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

MAX_SCORE = 80

NIFTY50_STOCKS = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK",
    "HINDUNILVR","ITC","SBIN","BHARTIARTL","KOTAKBANK",
    "LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","WIPRO","ULTRACEMCO","NESTLEIND","TECHM",
    "POWERGRID","NTPC","BAJFINANCE","BAJAJFINSV","HCLTECH",
    "ONGC","COALINDIA","TATAMOTORS","TATASTEEL","JSWSTEEL",
]

# ─────────────────────────────────────────────
# DEMO DATA (realistic sample)
# ─────────────────────────────────────────────
DEMO_DATA = {
    "RELIANCE":   {"price":2980,"pe":26.5,"change":1.2,"52h":3217,"52l":2220,"vwap":2960,"vol":8500000,"sector":"Energy"},
    "TCS":        {"price":4120,"pe":30.2,"change":0.8,"52h":4592,"52l":3311,"vwap":4100,"vol":3200000,"sector":"IT"},
    "HDFCBANK":   {"price":1820,"pe":19.5,"change":2.1,"52h":1880,"52l":1430,"vwap":1810,"vol":12000000,"sector":"Banking"},
    "INFY":       {"price":1650,"pe":24.8,"change":-0.5,"52h":2009,"52l":1358,"vwap":1660,"vol":7800000,"sector":"IT"},
    "ICICIBANK":  {"price":1290,"pe":18.2,"change":3.1,"52h":1361,"52l":1063,"vwap":1275,"vol":15000000,"sector":"Banking"},
    "HINDUNILVR": {"price":2410,"pe":55.3,"change":-1.2,"52h":2975,"52l":2186,"vwap":2430,"vol":1800000,"sector":"FMCG"},
    "ITC":        {"price":468,"pe":28.4,"change":0.9,"52h":520,"52l":401,"vwap":465,"vol":22000000,"sector":"FMCG"},
    "SBIN":       {"price":812,"pe":10.2,"change":2.8,"52h":912,"52l":601,"vwap":805,"vol":25000000,"sector":"Banking"},
    "BHARTIARTL": {"price":1720,"pe":68.5,"change":1.5,"52h":1779,"52l":1276,"vwap":1710,"vol":5500000,"sector":"Telecom"},
    "KOTAKBANK":  {"price":2050,"pe":22.1,"change":-0.8,"52h":2301,"52l":1544,"vwap":2065,"vol":4200000,"sector":"Banking"},
    "LT":         {"price":3680,"pe":35.2,"change":1.9,"52h":3963,"52l":3112,"vwap":3655,"vol":3100000,"sector":"Infra"},
    "AXISBANK":   {"price":1185,"pe":15.8,"change":2.4,"52h":1280,"52l":1014,"vwap":1172,"vol":11000000,"sector":"Banking"},
    "ASIANPAINT": {"price":2280,"pe":48.6,"change":-2.1,"52h":3395,"52l":2198,"vwap":2300,"vol":1500000,"sector":"Paint"},
    "MARUTI":     {"price":12800,"pe":27.4,"change":0.6,"52h":13680,"52l":10200,"vwap":12750,"vol":850000,"sector":"Auto"},
    "TITAN":      {"price":3620,"pe":88.2,"change":-0.3,"52h":3886,"52l":2982,"vwap":3640,"vol":1200000,"sector":"Jewellery"},
    "SUNPHARMA":  {"price":1820,"pe":36.5,"change":1.8,"52h":1960,"52l":1432,"vwap":1808,"vol":3800000,"sector":"Pharma"},
    "WIPRO":      {"price":560,"pe":22.8,"change":0.4,"52h":610,"52l":422,"vwap":558,"vol":6200000,"sector":"IT"},
    "ULTRACEMCO": {"price":11200,"pe":42.1,"change":-1.5,"52h":12350,"52l":9280,"vwap":11260,"vol":620000,"sector":"Cement"},
    "NESTLEIND":  {"price":2350,"pe":68.9,"change":0.2,"52h":2778,"52l":2100,"vwap":2345,"vol":420000,"sector":"FMCG"},
    "TECHM":      {"price":1680,"pe":38.2,"change":2.6,"52h":1762,"52l":1206,"vwap":1665,"vol":2800000,"sector":"IT"},
    "POWERGRID":  {"price":342,"pe":18.6,"change":1.1,"52h":366,"52l":260,"vwap":340,"vol":12500000,"sector":"Power"},
    "NTPC":       {"price":368,"pe":16.2,"change":0.7,"52h":396,"52l":265,"vwap":365,"vol":18000000,"sector":"Power"},
    "BAJFINANCE": {"price":7280,"pe":31.4,"change":3.2,"52h":7989,"52l":6187,"vwap":7220,"vol":2100000,"sector":"NBFC"},
    "BAJAJFINSV": {"price":1820,"pe":19.8,"change":1.6,"52h":2029,"52l":1499,"vwap":1810,"vol":3200000,"sector":"NBFC"},
    "HCLTECH":    {"price":1920,"pe":28.6,"change":2.2,"52h":2012,"52l":1235,"vwap":1908,"vol":4500000,"sector":"IT"},
    "ONGC":       {"price":265,"pe":7.8,"change":1.4,"52h":342,"52l":220,"vwap":263,"vol":28000000,"sector":"Energy"},
    "COALINDIA":  {"price":412,"pe":8.2,"change":0.9,"52h":543,"52l":386,"vwap":410,"vol":15000000,"sector":"Mining"},
    "TATAMOTORS": {"price":1120,"pe":11.5,"change":4.2,"52h":1179,"52l":684,"vwap":1108,"vol":22000000,"sector":"Auto"},
    "TATASTEEL":  {"price":162,"pe":18.9,"change":2.8,"52h":185,"52l":120,"vwap":160,"vol":42000000,"sector":"Steel"},
    "JSWSTEEL":   {"price":980,"pe":22.3,"change":1.9,"52h":1063,"52l":762,"vwap":972,"vol":8500000,"sector":"Steel"},
}

# ─────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────
def score_stock(symbol, data):
    score = 0
    reasons = []

    price  = data["price"]
    pe     = data["pe"]
    change = data["change"]
    h52    = data["52h"]
    l52    = data["52l"]
    vwap   = data["vwap"]
    vol    = data["vol"]

    # 1. PE Ratio (max 15 pts)
    if 0 < pe < 12:
        score += 15
        reasons.append(f"✅ Very low PE ({pe}x) — undervalued!")
    elif 12 <= pe < 20:
        score += 12
        reasons.append(f"✅ Good PE ({pe}x) — fairly valued")
    elif 20 <= pe < 30:
        score += 7
        reasons.append(f"⚠️  Moderate PE ({pe}x)")
    elif pe >= 30:
        score += 2
        reasons.append(f"❌ High PE ({pe}x) — expensive")

    # 2. Today's Price Change (max 15 pts)
    if change >= 3:
        score += 15
        reasons.append(f"✅ Strong rally today (+{change}%)")
    elif change >= 1.5:
        score += 10
        reasons.append(f"✅ Good positive move (+{change}%)")
    elif change >= 0:
        score += 5
        reasons.append(f"⚠️  Slight positive ({change}%)")
    else:
        score += 0
        reasons.append(f"❌ Negative today ({change}%)")

    # 3. Distance from 52W High (max 15 pts)
    pct_from_high = ((h52 - price) / h52) * 100
    if pct_from_high <= 5:
        score += 15
        reasons.append(f"✅ Near 52W high — strong momentum!")
    elif pct_from_high <= 15:
        score += 10
        reasons.append(f"⚠️  {pct_from_high:.1f}% below 52W high")
    elif pct_from_high <= 30:
        score += 5
        reasons.append(f"⚠️  {pct_from_high:.1f}% below 52W high")
    else:
        score += 0
        reasons.append(f"❌ {pct_from_high:.1f}% below 52W high")

    # 4. Recovery from 52W Low (max 15 pts)
    pct_from_low = ((price - l52) / l52) * 100
    if pct_from_low >= 50:
        score += 15
        reasons.append(f"✅ Strong recovery from low (+{pct_from_low:.0f}%)")
    elif pct_from_low >= 30:
        score += 10
        reasons.append(f"✅ Good recovery from low (+{pct_from_low:.0f}%)")
    elif pct_from_low >= 15:
        score += 5
        reasons.append(f"⚠️  Moderate recovery (+{pct_from_low:.0f}%)")
    else:
        score += 2
        reasons.append(f"❌ Near 52W low — weak ({pct_from_low:.0f}% above)")

    # 5. Price vs VWAP (max 10 pts)
    if price > vwap:
        score += 10
        reasons.append(f"✅ Price above VWAP — buyers in control")
    else:
        score += 0
        reasons.append(f"❌ Price below VWAP — sellers in control")

    # 6. Volume (max 10 pts)
    if vol >= 10000000:
        score += 10
        reasons.append(f"✅ Very high volume — strong interest")
    elif vol >= 5000000:
        score += 7
        reasons.append(f"✅ High volume")
    elif vol >= 2000000:
        score += 4
        reasons.append(f"⚠️  Moderate volume")
    else:
        score += 1
        reasons.append(f"⚠️  Low volume")

    pct_from_high_val = ((h52 - price) / h52) * 100
    pct_from_low_val  = ((price - l52) / l52) * 100

    return score, {
        "price":         f"₹{price:,}",
        "pe":            f"{pe}x",
        "change":        f"{change:+.1f}%",
        "52w_high":      f"₹{h52:,}",
        "52w_low":       f"₹{l52:,}",
        "from_high":     f"{pct_from_high_val:.1f}%",
        "from_low":      f"+{pct_from_low_val:.1f}%",
        "vwap":          f"₹{vwap:,}",
        "volume":        f"{vol/1000000:.1f}M",
        "sector":        data["sector"],
    }, reasons

# ─────────────────────────────────────────────
# NSE LIVE FETCH
# ─────────────────────────────────────────────
def try_live_fetch(symbol):
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get("https://www.nseindia.com", timeout=8)
        time.sleep(0.5)
        url  = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
        resp = session.get(url, timeout=8)
        if resp.status_code == 200:
            d = resp.json()
            pi = d.get("priceInfo", {})
            md = d.get("metadata", {})
            ih = d.get("industryInfo", {})
            w  = pi.get("weekHighLow", {})
            return {
                "price":  pi.get("lastPrice", 0),
                "pe":     float(md.get("pdSymbolPe", 0) or 0),
                "change": pi.get("pChange", 0),
                "52h":    w.get("max", 0),
                "52l":    w.get("min", 0),
                "vwap":   pi.get("vwap", 0),
                "vol":    pi.get("totalTradedVolume", 0),
                "sector": ih.get("macro", "N/A"),
            }
    except:
        pass
    return None

# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────
def banner(mode):
    print("\n" + "🔥"*30)
    print("   NSE STOCK SCREENER — SARGUNA'S TOOL 📈")
    print("🔥"*30)
    print(f"   Date & Time : {datetime.now().strftime('%d %b %Y  %I:%M %p')}")
    print(f"   Mode        : {'🌐 LIVE NSE DATA' if mode == 'live' else '📊 DEMO MODE (Sample Data)'}")
    print(f"   Stocks      : {len(NIFTY50_STOCKS)} Nifty 50 stocks\n")

def get_rating(score):
    pct = (score / MAX_SCORE) * 100
    if pct >= 70: return "🟢 STRONG BUY", pct
    if pct >= 55: return "🟡 BUY",        pct
    if pct >= 40: return "🟠 WATCH",      pct
    return            "🔴 AVOID",         pct

def display_result(rank, symbol, score, info, reasons, verbose=False):
    rating, pct = get_rating(score)
    print(f"\n  #{rank:<3} {symbol:<12} {info['price']:<10} "
          f"PE:{info['pe']:<8} Score:{score}/{MAX_SCORE} ({pct:.0f}%)  {rating}")
    print(f"       Change:{info['change']:<8} VWAP:{info['vwap']:<10} "
          f"Vol:{info['volume']}")
    print(f"       52W High:{info['52w_high']}({info['from_high']} below)  "
          f"52W Low:{info['52w_low']}({info['from_low']} above)")
    print(f"       Sector: {info['sector']}")
    if verbose and reasons:
        for r in reasons[:3]:
            print(f"       {r}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("\n  Choose mode:")
    print("  1 → Live NSE API  (requires internet + Indian IP)")
    print("  2 → Demo Mode     (sample data — works everywhere)")
    choice = input("\n  Enter choice [2]: ").strip() or "2"

    mode = "live" if choice == "1" else "demo"
    banner(mode)

    results = []

    if mode == "live":
        print("  ⏳ Fetching live data from NSE...\n")
        for i, sym in enumerate(NIFTY50_STOCKS):
            print(f"  Fetching {sym:<15} ({i+1}/{len(NIFTY50_STOCKS)})", end="\r")
            data = try_live_fetch(sym)
            if data and data["price"] > 0:
                score, info, reasons = score_stock(sym, data)
                results.append((sym, score, info, reasons))
            time.sleep(0.5)
        print(f"\n  ✅ Fetched {len(results)} stocks live!")

        if len(results) == 0:
            print("  ⚠️  NSE blocked our requests. Switching to demo mode...")
            mode = "demo"

    if mode == "demo":
        print("  ⏳ Loading sample data...\n")
        for sym in NIFTY50_STOCKS:
            if sym in DEMO_DATA:
                score, info, reasons = score_stock(sym, DEMO_DATA[sym])
                results.append((sym, score, info, reasons))
        print(f"  ✅ Loaded {len(results)} stocks!\n")

    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)

    # ── TOP 10 PICKS ───────────────────────────
    print("\n" + "="*60)
    print("  🏆 TOP 10 STOCK PICKS")
    print("="*60)
    for rank, (sym, score, info, reasons) in enumerate(results[:10], 1):
        display_result(rank, sym, score, info, reasons, verbose=True)

    # ── BOTTOM 5 ───────────────────────────────
    print("\n" + "="*60)
    print("  ⚠️  STOCKS TO AVOID (Bottom 5)")
    print("="*60)
    for rank, (sym, score, info, reasons) in enumerate(results[-5:], len(results)-4):
        display_result(rank, sym, score, info, reasons)

    # ── FULL TABLE ─────────────────────────────
    print("\n" + "="*60)
    print("  📋 COMPLETE RANKING TABLE")
    print("="*60)
    print(f"\n  {'#':<4} {'Symbol':<12} {'Price':<10} {'PE':<8} "
          f"{'Score':<10} {'Rating':<18} {'Change'}")
    print(f"  {'─'*72}")
    for rank, (sym, score, info, reasons) in enumerate(results, 1):
        rating, pct = get_rating(score)
        print(f"  {rank:<4} {sym:<12} {info['price']:<10} {info['pe']:<8} "
              f"{score}/{MAX_SCORE} ({pct:.0f}%){'':<2} {rating:<18} {info['change']}")

    # ── SECTOR SUMMARY ─────────────────────────
    print("\n" + "="*60)
    print("SECTOR SUMMARY")
    print("="*60)
    sector_scores = {}
    sector_counts = {}
    for sym, score, info, reasons in results:
        s = info["sector"]
        sector_scores[s] = sector_scores.get(s, 0) + score
        sector_counts[s] = sector_counts.get(s, 0) + 1
    sector_avg = {s: sector_scores[s]/sector_counts[s] for s in sector_scores}
    sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
    print(f"\n  {'Sector':<15} {'Avg Score':<12} {'Stocks':<8} {'Signal'}")
    print(f"  {'─'*45}")
    for sec, avg in sorted_sectors:
        signal = "✅ Strong" if avg >= 55 else "⚠️  Moderate" if avg >= 40 else "❌ Weak"
        print(f"  {sec:<15} {avg:.1f}/{MAX_SCORE:<10} {sector_counts[sec]:<8} {signal}")

    # ── SAVE CSV ─────────────────────────────
    print("\n" + "="*60)
    print("  💾 SAVING TO CSV")
    print("="*60)
    try:
        rows = []
        for rank, (sym, score, info, reasons) in enumerate(results, 1):
            rating, pct = get_rating(score)
            rows.append({
                "Rank":          rank,
                "Symbol":        sym,
                "Price":         info["price"],
                "PE Ratio":      info["pe"],
                "Score":         f"{score}/{MAX_SCORE}",
                "Score %":       f"{pct:.0f}%",
                "Rating":        rating.split(" ", 1)[1],
                "Today Change":  info["change"],
                "VWAP":          info["vwap"],
                "Volume":        info["volume"],
                "52W High":      info["52w_high"],
                "52W Low":       info["52w_low"],
                "From High":     info["from_high"],
                "From Low":      info["from_low"],
                "Sector":        info["sector"],
                "Top Reason":    reasons[0] if reasons else "N/A",
                "Screened At":   datetime.now().strftime("%d-%b-%Y %I:%M %p"),
                "Mode":          mode.upper(),
            })
        fname = f"NSE_Screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        with open(fname, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n  ✅ Saved: {fname}")
    except Exception as e:
        print(f"  ⚠️  Save failed: {e}")

    # ── FINAL SUMMARY ──────────────────────────
    buy     = sum(1 for _, s, _, _ in results if (s/MAX_SCORE)*100 >= 70)
    watch   = sum(1 for _, s, _, _ in results if 55 <= (s/MAX_SCORE)*100 < 70)
    neutral = sum(1 for _, s, _, _ in results if 40 <= (s/MAX_SCORE)*100 < 55)
    avoid   = sum(1 for _, s, _, _ in results if (s/MAX_SCORE)*100 < 40)

    print("\n" + "="*60)
    print("  📊 FINAL SUMMARY")
    print("="*60)
    print(f"  Total Screened   : {len(results)} stocks")
    print(f"  🟢 Strong Buy    : {buy} stocks")
    print(f"  🟡 Buy           : {watch} stocks")
    print(f"  🟠 Watch         : {neutral} stocks")
    print(f"  🔴 Avoid         : {avoid} stocks")
    print(f"\n  🏆 Top Pick      : {results[0][0]} "
          f"(Score: {results[0][1]}/{MAX_SCORE})")
    print(f"  🎯 Top Sector    : {sorted_sectors[0][0]} "
          f"(Avg: {sorted_sectors[0][1]:.1f})")

    print("\n" + "="*60)
    print("  ✅ Screening Complete!")
    print("  ⚠️  NOT financial advice — do your own research!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
