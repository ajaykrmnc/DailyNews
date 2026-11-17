#!/usr/bin/env python3
"""Fetch The Hindu's editorial RSS into dated Markdown notes (standard library only).

Use --refresh to download a saved day again, or --date YYYY-MM-DD for a date
still present in the rolling RSS feed. Only publicly returned content is saved.
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from today_news_md import (
    MarkdownRenderer, clean_text, fetch, heading_ref, heading_text, note_days,
    parse_day, parse_html, plain_text, read, write_if_changed,
)

FEED_URL = "https://www.thehindu.com/opinion/editorial/feeder/default.rss"
IST = timezone(timedelta(hours=5, minutes=30))
FOLDER = "The Hindu Editorial"
NAV_MARK = "%%nav%%"


def editorial_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.hostname in {"www.thehindu.com", "thehindu.com"}
            and parsed.path.startswith("/opinion/editorial/") and parsed.path.endswith(".ece"))


def feed_entries(text):
    entries = []
    seen = set()
    for item in ET.fromstring(text).findall("./channel/item"):
        url = (item.findtext("link") or "").strip()
        title = clean_text(item.findtext("title") or "")
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
            day = published.astimezone(IST).date()
        except (ValueError, TypeError, OverflowError):
            continue
        if not title or not editorial_url(url) or url in seen:
            continue
        seen.add(url)
        description = parse_html(item.findtext("description") or "")
        entries.append(dict(url=url, title=title, day=day,
                            summary=clean_text(plain_text(description))))
    return entries


def article_markdown(text, url):
    root = parse_html(text)
    body = root.find(lambda n: n.attrs.get("itemprop") == "articleBody"
                     or n.attrs.get("id", "").startswith("content-body-"))
    if body is None:
        return ""
    content = body.find(lambda n: "schemaDiv" in n.classes)
    if content is not None:
        body = content
    # Keep article text and formatting, excluding inline ads and recommendations.
    for node in body.find_all(lambda n: n.tag in {"div", "aside"}):
        marker = (node.attrs.get("id", "") + " " + node.attrs.get("class", "")).lower()
        if any(word in marker for word in ("advert", "related", "recommend", "artproduct", "paywall", "print-hide")):
            node.hidden = True
    blocks = []
    MarkdownRenderer(url).blocks(body, blocks)
    return "\n\n".join(blocks)


def render_note(day, entries):
    parts = [f"# The Hindu Editorial: {day.strftime('%A, %d %B %Y')}", NAV_MARK]
    parts.append("\n".join(f"{i}. [[#{heading_ref(e['title'])}|{heading_text(e['title'])}]]"
                           for i, e in enumerate(entries, 1)))
    for entry in entries:
        body = ""
        try:
            body = article_markdown(fetch(entry["url"]), entry["url"])
        except Exception as err:
            print(f"Article unavailable: {type(err).__name__}: {err}", file=sys.stderr)
        parts.extend(["---", f"## {heading_text(entry['title'])}", f"[Read at The Hindu]({entry['url']})"])
        if body:
            parts.append(body)
        else:
            parts.append(entry["summary"] or "No preview provided in the RSS feed.")
            parts.append(
                "> [!info] RSS preview\n> Article text could not be retrieved. "
                "Use the source link to read it; a subscription may be required."
            )
    return "\n\n".join(parts) + "\n"


def update_index(out_dir):
    days = note_days(out_dir)
    # Include the folder in links: Drishti notes use the same date filenames.
    folder = os.path.basename(os.path.normpath(out_dir))
    for i, day in enumerate(days):
        links = []
        if i:
            links.append(f"[[{folder}/{days[i - 1]}|← {days[i - 1]}]]")
        links.append(f"[[{folder}/{FOLDER}|All days]]")
        if i + 1 < len(days):
            links.append(f"[[{folder}/{days[i + 1]}|{days[i + 1]} →]]")
        target = os.path.join(out_dir, f"{day}.md")
        lines = read(target).split("\n")
        lines = [NAV_MARK + " " + " · ".join(links) if line.startswith(NAV_MARK) else line for line in lines]
        write_if_changed(target, "\n".join(lines))
    lines = [f"# {FOLDER}", "", "Press `Space o h` to fetch the latest editorials; `Space o H` to refresh.", ""]
    lines += [f"- [[{folder}/{day}|{day}]]" for day in reversed(days)]
    write_if_changed(os.path.join(out_dir, f"{FOLDER}.md"), "\n".join(lines) + "\n")


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
        print(target)
        return 0
    try:
        entries = feed_entries(fetch(FEED_URL))
        candidates = [e for e in entries if e["day"] == requested] if args.date else [
            e for e in entries if today - timedelta(days=7) <= e["day"] <= today
        ]
        if not candidates:
            raise ValueError(f"No The Hindu editorials available in the RSS feed for {requested}")
        day = max(e["day"] for e in candidates)
        target = os.path.join(args.out_dir, f"{day.isoformat()}.md")
        if not os.path.isfile(target) or args.refresh or (today - day).days <= 1:
            text = render_note(day, [e for e in candidates if e["day"] == day])
            os.makedirs(args.out_dir, exist_ok=True)
            write_if_changed(target, text)
            update_index(args.out_dir)
    except Exception as err:
        print(f"The Hindu fetch failed: {type(err).__name__}: {err}", file=sys.stderr)
        # A network failure must not prevent opening a previously saved note.
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
