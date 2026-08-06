import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional, Set
from xml.etree import ElementTree

# ---------- CONFIG ----------
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
DEFAULT_COMPANIES = ["Reliance", "ITC", "Tata Motors", "HDFC Bank", "Infosys"]
DEFAULT_TOPICS = ["quarterly results", "earnings report", "Trump", "Modi", "stock market impact"]
OUTPUT_CSV = "news_data.csv"
OUTPUT_JSON = "news_data.json"
OUTPUT_REPORT = "news_report.md"
OUTPUT_HTML = "news_view.html"
# ---------------------------

HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: str) -> str:
    return html.unescape(HTML_TAG_RE.sub("", (value or "").strip())).replace("\n", " ").strip()


def parse_pub_date(pub_date: str) -> str:
    raw = (pub_date or "").strip()
    if not raw:
        return ""

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.utcnow().astimezone().tzinfo)
        return dt.isoformat()
    except Exception:
        return raw


def build_search_queries(companies: List[str], topics: List[str]) -> List[Dict[str, str]]:
    queries = []

    for company in companies:
        company = company.strip()
        if not company:
            continue
        queries.append({"query": company, "tag": company})
        queries.append({"query": f"{company} quarterly results", "tag": company})
        queries.append({"query": f"{company} earnings report", "tag": company})
        queries.append({"query": f"{company} stock news", "tag": company})

    for topic in topics:
        topic = topic.strip()
        if topic:
            queries.append({"query": topic, "tag": topic})

    unique = []
    seen: Set[str] = set()
    for item in queries:
        normalized = item["query"].strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(item)
    return unique


def fetch_rss_feed(query: str, retry: int = 2, delay_seconds: float = 1.0) -> Optional[bytes]:
    url = GOOGLE_NEWS_RSS.format(urllib.parse.quote_plus(query))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, retry + 1):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read()
        except Exception as exc:
            if attempt == retry:
                print(f"Failed to fetch RSS for '{query}': {exc}")
                return None
            time.sleep(delay_seconds)
    return None


def parse_google_news_rss(body: bytes, tag: str, query: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        print(f"Unable to parse RSS XML for query '{query}': {exc}")
        return items

    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title") or "")
        link = clean_text(item.findtext("link") or "")
        pub_date = parse_pub_date(item.findtext("pubDate") or "")
        description = clean_text(item.findtext("description") or "")
        source_name = clean_text(item.findtext("source") or "Google News")

        items.append({
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "query": query,
            "tag": tag,
            "title": title,
            "link": link,
            "published": pub_date,
            "description": description,
            "source": source_name,
        })

    return items


def dedupe_news_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique: List[Dict[str, str]] = []
    seen: Set[str] = set()

    for row in rows:
        title = (row.get("title", "") or "").strip().lower()
        link = (row.get("link", "") or "").strip()
        key = f"{title}|{link}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    return unique


def published_datetime(value: str) -> datetime:
    if not value:
        return datetime.min
    try:
        return parsedate_to_datetime(value)
    except Exception:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return datetime.min


def load_existing_news(path: str) -> List[Dict[str, str]]:
    existing: List[Dict[str, str]] = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                existing.append(row)
    except FileNotFoundError:
        pass
    return existing


def save_news_csv(path: str, rows: List[Dict[str, str]]) -> None:
    if not rows:
        print("No news to save.")
        return

    fieldnames = [
        "collected_at",
        "query",
        "tag",
        "title",
        "link",
        "published",
        "source",
        "description",
    ]

    existing = load_existing_news(path)
    seen = {f"{row['title']}|{row['link']}" for row in existing}
    new_rows = [row for row in rows if f"{row['title']}|{row['link']}" not in seen]

    if not new_rows:
        print("Already have the latest news items. No new rows added.")
        return

    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if fh.tell() == 0:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)

    print(f"Saved {len(new_rows)} new news rows to {path}")


def save_news_json(path: str, rows: List[Dict[str, str]]) -> None:
    try:
        existing: List[Dict[str, str]] = []
        with open(path, "r", encoding="utf-8") as fh:
            existing = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    seen = {f"{row['title']}|{row['link']}" for row in existing}
    new_rows = [row for row in rows if f"{row['title']}|{row['link']}" not in seen]
    merged = existing + new_rows

    if not new_rows:
        print(f"Already have the latest news items in {path}. No new entries added.")
        return

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)

    print(f"Saved {len(new_rows)} new news items to {path}")


def save_news_markdown(path: str, rows: List[Dict[str, str]], max_per_tag: int = 5) -> None:
    if not rows:
        print("No news to save to markdown.")
        return

    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["tag"], []).append(row)

    lines = ["# News Report", f"Generated: {datetime.utcnow().isoformat()}Z", ""]
    for tag in sorted(grouped.keys()):
        lines.append(f"## {tag}")
        lines.append("")
        for item in sorted(grouped[tag], key=lambda r: published_datetime(r["published"]), reverse=True)[:max_per_tag]:
            lines.append(f"### {item['title']}")
            lines.append(f"- **Source:** {item['source']}")
            lines.append(f"- **Published:** {item['published']}")
            lines.append(f"- **Query:** {item['query']}")
            lines.append(f"- **Link:** {item['link']}")
            if item["description"]:
                lines.append(f"- **Summary:** {item['description']}")
            lines.append("")
        lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"Saved readable news report to {path}")


def build_html_page(rows: List[Dict[str, str]]) -> str:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["tag"], []).append(row)

    lines = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"UTF-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "  <title>News Viewer</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 24px; background: #fafafa; color: #111; }",
        "    .tag { margin-top: 32px; }",
        "    .card { border: 1px solid #ddd; border-radius: 8px; background: #fff; padding: 18px; margin: 12px 0; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }",
        "    .title { font-size: 1.05rem; margin: 0 0 8px; }",
        "    .meta { color: #555; font-size: 0.90rem; margin-bottom: 12px; }",
        "    .summary { margin: 12px 0; line-height: 1.5; }",
        "    .link { color: #0066cc; text-decoration: none; }",
        "    .link:hover { text-decoration: underline; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>News Viewer</h1>",
        f"  <p>Generated: {datetime.utcnow().isoformat()}Z</p>",
    ]

    for tag in sorted(grouped.keys()):
        lines.append(f"  <section class=\"tag\">")
        lines.append(f"    <h2>{tag}</h2>")
        for item in sorted(grouped[tag], key=lambda r: published_datetime(r["published"]), reverse=True):
            lines.append("    <div class=\"card\">")
            lines.append(f"      <div class=\"title\"><a class=\"link\" href=\"{item['link']}\" target=\"_blank\">{item['title']}</a></div>")
            lines.append(f"      <div class=\"meta\">Source: {item['source']} | Published: {item['published']} | Query: {item['query']}</div>")
            if item["description"]:
                lines.append(f"      <div class=\"summary\">{item['description']}</div>")
            lines.append("    </div>")
        lines.append("  </section>")

    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines)


def save_news_html(path: str, rows: List[Dict[str, str]]) -> None:
    html_text = build_html_page(rows)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    print(f"Saved browser-ready HTML view to {path}")


def open_browser(path: str) -> None:
    try:
        webbrowser.open_new_tab(path)
    except Exception as exc:
        print(f"Unable to open browser automatically: {exc}")


def serve_html(rows: List[Dict[str, str]], host: str = "127.0.0.1", port: int = 8000) -> None:
    html_content = build_html_page(rows).encode("utf-8")

    class NewsHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_content)))
            self.end_headers()
            self.wfile.write(html_content)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = HTTPServer((host, port), NewsHandler)
    print(f"Serving news browser view at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
    if not rows:
        print("No news items to display.")
        return

    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["tag"], []).append(row)

    print("\nNews summary grouped by tag:\n")
    for tag in sorted(grouped.keys()):
        print(f"=== {tag} ===")
        for item in sorted(grouped[tag], key=lambda r: published_datetime(r["published"]), reverse=True)[:max_per_tag]:
            print(f"- {item['title']}" )
            print(f"  source: {item['source']} | published: {item['published']}")
            print(f"  link: {item['link']}")
            if item['description']:
                print(f"  summary: {item['description']}")
        print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect stock and market news from Google News RSS and save organized output."
    )
    parser.add_argument(
        "--companies",
        nargs="*",
        default=DEFAULT_COMPANIES,
        help="Company names or stock tickers to collect news for.",
    )
    parser.add_argument(
        "--topics",
        nargs="*",
        default=DEFAULT_TOPICS,
        help="General news topics to collect, such as earnings, politics, or macro events.",
    )
    parser.add_argument(
        "--csv",
        default=OUTPUT_CSV,
        help="CSV file to write news items to.",
    )
    parser.add_argument(
        "--json",
        default=OUTPUT_JSON,
        help="JSON file to write news items to.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a markdown report file with grouped news summaries.",
    )
    parser.add_argument(
        "--report-max",
        type=int,
        default=5,
        help="Maximum headlines per tag in the markdown report.",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate a browser-friendly HTML view file.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the news view on a local HTTP server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to use when serving the HTML view.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated HTML view in the default browser.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Print a short summary of the latest collected news in the console.",
    )
    parser.add_argument(
        "--max-show",
        type=int,
        default=3,
        help="Maximum headlines per tag shown in the console summary.",
    )

    args = parser.parse_args()

    search_items = build_search_queries(args.companies, args.topics)
    all_rows: List[Dict[str, str]] = []

    print(f"Collecting news for {len(search_items)} queries...")
    for item in search_items:
        query = item["query"]
        tag = item["tag"]
        print(f"Fetching news for: {query}")
        body = fetch_rss_feed(query)
        if body is None:
            continue
        rows = parse_google_news_rss(body, tag, query)
        all_rows.extend(rows)
        time.sleep(0.8)

    all_rows = dedupe_news_rows(all_rows)
    if not all_rows:
        print("No news items collected from the feeds.")
        return

    save_news_csv(args.csv, all_rows)
    save_news_json(args.json, all_rows)

    if args.report:
        save_news_markdown(OUTPUT_REPORT, all_rows, max_per_tag=args.report_max)

    if args.html:
        save_news_html(OUTPUT_HTML, all_rows)
        if args.open:
            open_browser(OUTPUT_HTML)

    if args.serve:
        print("Starting local browser server...")
        serve_html(all_rows, port=args.port)

    if args.show:
        print_summary(all_rows, max_per_tag=args.max_show)

    print("News collection complete.")


if __name__ == "__main__":
    main()
