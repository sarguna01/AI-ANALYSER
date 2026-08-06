# AI-ANALYSER

This repository currently stores stock price data and adds a news collection utility for stock-impacting headlines.

## Added news collector

- `news_collector.py`: collects Google News RSS results for company names and market topics
- Saves output to `news_data.csv` and `news_data.json`

## Usage

Collect news for default companies and topics:

```bash
python news_collector.py --show
```

Collect news for specific companies or topics:

```bash
python news_collector.py --companies Reliance ITC Tesla --topics "quarterly results" Modi Trump --show
```

The output files are:
- `news_data.csv`
- `news_data.json`

You can also change or extend the company and topic lists in `news_collector.py`.

# AI-ANALYSER