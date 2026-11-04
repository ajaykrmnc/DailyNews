#!/usr/bin/env python3
"""Write today's headlines from the DailyNews RSS sources to a Markdown note.

Uses only the standard library so it runs from Obsidian with the system python3.
"""

import argparse
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime

FEEDS = [
    ("The Hindu: National", "https://www.thehindu.com/news/national/feeder/default.rss"),
    ("The Hindu: International", "https://www.thehindu.com/news/international/feeder/default.rss"),
    ("The Hindu: Business", "https://www.thehindu.com/business/feeder/default.rss"),
    ("The Hindu: Opinion", "https://www.thehindu.com/opinion/feeder/default.rss"),
    ("Drishti IAS", "https://www.drishtiias.com/rss.rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("YourStory", "https://yourstory.com/feed"),
]
DEFAULT_OUT_DIR = os.path.join(os.path.expanduser("~"), "notes", "Daily News")
SUMMARY_CHARS = 280
USER_AGENT = "Mozilla/5.0 (DailyNews today_news_md)"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def plain_text(fragment):
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_CHARS:
        text = text[:SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def published_local(item):
    raw = item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date")
    if not raw:
        return None
    try:
        stamp = parsedate_to_datetime(raw.strip())
    except (TypeError, ValueError):
        try:
            stamp = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return stamp.astimezone() if stamp.tzinfo else stamp


def todays_items(source, url, today):
    try:
        root = ET.fromstring(fetch(url))
    except Exception as err:
        return source, None, f"{type(err).__name__}: {err}"
    items = []
    seen = set()
    for item in root.iter("item"):
        when = published_local(item)
        link = (item.findtext("link") or "").strip()
        if not when or when.date() != today or link in seen:
            continue
        seen.add(link)
        items.append({
            "title": plain_text(item.findtext("title")) or link,
            "link": link,
            "time": when.strftime("%H:%M"),
            "summary": plain_text(item.findtext("description")),
        })
    items.sort(key=lambda entry: entry["time"], reverse=True)
    return source, items, None


def markdown_link_text(text):
    return text.replace("[", "\\[").replace("]", "\\]")


def render(today, results):
    total = sum(len(items or []) for _, items, _ in results)
    lines = [
        "---",
        f"date: {today.isoformat()}",
        f"fetched: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"stories: {total}",
        "tags: [daily-news]",
        "---",
        "",
        f"# Daily News: {today.strftime('%A, %d %B %Y')}",
        "",
    ]
    for source, items, error in results:
        lines.append(f"## {source}")
        lines.append("")
        if error:
            lines.append(f"_Could not fetch this feed ({error})._")
        elif not items:
            lines.append("_No stories published today yet._")
        for entry in items or []:
            title = markdown_link_text(entry["title"])
            lines.append(f"- **{entry['time']}** [{title}]({entry['link']})")
            if entry["summary"]:
                lines.append(f"    - {entry['summary']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=os.environ.get("DAILY_NEWS_DIR", DEFAULT_OUT_DIR),
        help="folder for the YYYY-MM-DD.md note (default: %(default)s)",
    )
    args = parser.parse_args()

    today = datetime.now().astimezone().date()
    with ThreadPoolExecutor(max_workers=len(FEEDS)) as pool:
        results = list(pool.map(lambda feed: todays_items(feed[0], feed[1], today), FEEDS))

    if all(error for _, _, error in results):
        for source, _, error in results:
            print(f"{source}: {error}", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"{today.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as note:
        note.write(render(today, results))
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
