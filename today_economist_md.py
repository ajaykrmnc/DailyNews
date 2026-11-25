#!/usr/bin/env python3
"""Save The Economist's public latest-articles RSS previews as dated Obsidian notes.

Only headlines, summaries and source links are fetched; full articles may require
a subscription. --date selects an Indian publication date still in the RSS feed.
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from rss_notes import NAV_MARK, update_index
from today_news_md import (
    clean_text, fetch, heading_ref, heading_text, note_days, parse_day, parse_html,
    plain_text, write_if_changed,
)

FEED_URL = "https://www.economist.com/latest/rss.xml"
FOLDER = "The Economist"
IST = timezone(timedelta(hours=5, minutes=30))


def feed_entries(text):
    entries, seen = [], set()
    for item in ET.fromstring(text).findall("./channel/item"):
        url = (item.findtext("link") or "").strip()
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if (parsed.scheme != "https" or parsed.hostname not in {"www.economist.com", "economist.com"}
                or parsed.username or parsed.password
                or not re.match(r"^/[^/]+/\d{4}/\d{2}/\d{2}/[^/]+", parsed.path)):
            continue
        title = clean_text(item.findtext("title") or "")
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            day = published.astimezone(IST).date()
        except (ValueError, TypeError, OverflowError):
            continue
        if not title or url in seen:
            continue
        seen.add(url)
        summary = clean_text(plain_text(parse_html(item.findtext("description") or "")))
        entries.append(dict(title=title, url=url, day=day, summary=summary))
    return entries


def render_note(day, entries):
    parts = [f"# The Economist: {day.strftime('%A, %d %B %Y')}", NAV_MARK,
             "> [!info] RSS previews\n> Headlines and summaries from The Economist's latest-articles feed. "
             "Open the source links to read the full articles; a subscription may be required."]
    parts.append("\n".join(f"{i}. [[#{heading_ref(e['title'])}|{heading_text(e['title'])}]]"
                           for i, e in enumerate(entries, 1)))
    for entry in entries:
        parts.extend(["---", f"## {heading_text(entry['title'])}",
                      entry["summary"] or "No summary provided in the RSS feed.",
                      f"[Read at The Economist]({entry['url']})"])
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=os.path.expanduser(f"~/notes/{FOLDER}"))
    parser.add_argument("--date", type=parse_day, help="date still available in the rolling RSS feed")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    today = datetime.now(IST).date()
    requested = args.date or today
    target = os.path.join(args.out_dir, f"{requested.isoformat()}.md")
    if os.path.isfile(target) and not args.refresh and (today - requested).days > 1:
        print(os.path.abspath(target))
        return 0
    try:
        entries = feed_entries(fetch(FEED_URL))
        candidates = [e for e in entries if e["day"] == requested] if args.date else [
            e for e in entries if today - timedelta(days=7) <= e["day"] <= today
        ]
        if not candidates:
            raise ValueError(f"No The Economist articles available in the RSS feed for {requested}")
        day = max(e["day"] for e in candidates)
        target = os.path.join(args.out_dir, f"{day.isoformat()}.md")
        if not os.path.isfile(target) or args.refresh or (today - day).days <= 1:
            os.makedirs(args.out_dir, exist_ok=True)
            write_if_changed(target, render_note(day, [e for e in candidates if e["day"] == day]))
            update_index(args.out_dir, FOLDER,
                         "Press `Space o E` to fetch the latest articles. Use the command palette's "
                         "\"Refresh The Economist articles\" to refresh. Dates use Indian Standard Time.")
    except Exception as err:
        print(f"The Economist fetch failed: {type(err).__name__}: {err}", file=sys.stderr)
        saved = note_days(args.out_dir) if os.path.isdir(args.out_dir) else []
        saved = [d for d in saved if d == requested.isoformat()] if args.date else [
            d for d in saved if d <= today.isoformat()
        ]
        if not saved:
            return 1
        target = os.path.join(args.out_dir, f"{saved[-1]}.md")
    print(os.path.abspath(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
