#!/usr/bin/env python3
"""Write Drishti IAS daily news analysis to a Markdown note.

Fetches today's page, falling back to the latest page from the previous few days when
today's is not published yet.
Uses only the standard library so it runs from Obsidian with the system python3.
"""

import argparse
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin

PAGE_URL = "https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{}"
DEFAULT_OUT_DIR = os.path.join(os.path.expanduser("~"), "notes", "Daily News")
USER_AGENT = "Mozilla/5.0 (DailyNews today_news_md)"
FALLBACK_DAYS = 3

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
SKIP_TAGS = {"script", "style", "iframe", "noscript", "input", "button", "svg", "form", "select"}
SKIP_CLASSES = {
    "next-post", "social-shares", "banner-static", "slider", "btn-group",
    "desktop-ad-banner", "mobile-ad-banner", "recommendations-layout", "article-meta-pdf-btn",
}
SKIP_IDS = {"disqus_thread", "articlemsg"}
BLOCK_TAGS = {
    "p", "div", "section", "article", "ul", "ol", "li", "table", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "figure", "figcaption",
}
HEADING_LEVEL = {"h1": 2, "h2": 3, "h3": 4, "h4": 5, "h5": 5}


class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def find_all(self, predicate):
        for child in self.children:
            if isinstance(child, Node):
                if predicate(child):
                    yield child
                yield from child.find_all(predicate)


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text):
    builder = TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


def skipped(node):
    return (
        node.tag in SKIP_TAGS
        or node.classes & SKIP_CLASSES
        or node.attrs.get("id") in SKIP_IDS
        or node.attrs.get("type") == "hidden"
    )


class MarkdownRenderer:
    def __init__(self, base_url):
        self.base_url = base_url

    def link(self, href):
        return urljoin(self.base_url, href.strip()).replace(" ", "%20").replace(")", "%29")

    def inline(self, node):
        if isinstance(node, str):
            return re.sub(r"\s+", " ", node.replace("\xa0", " "))
        if skipped(node):
            return ""
        tag = node.tag
        if tag == "br":
            return "<br>"
        if tag == "img":
            src = node.attrs.get("src")
            return f"![{node.attrs.get('alt', '').strip()}]({self.link(src)})" if src else ""
        text = "".join(self.inline(child) for child in node.children)
        if tag in ("b", "strong", "i", "em"):
            mark = "**" if tag in ("b", "strong") else "*"
            inner = text.strip()
            if not re.search(r"\w", inner) or inner.startswith(mark) and inner.endswith(mark):
                return text
            lead = " " if text[:1].isspace() else ""
            trail = " " if text[-1:].isspace() else ""
            return f"{lead}{mark}{inner}{mark}{trail}"
        if tag == "a":
            href = node.attrs.get("href", "")
            inner = text.strip()
            if not inner or not href or href.startswith(("javascript:", "#")):
                return text
            if re.fullmatch(r"!\[[^\]]*\]\([^)]*\)", inner):
                return inner
            return f"[{inner}]({self.link(href)})"
        return text

    def tidy(self, text):
        text = text.replace("****", "").replace("<br>", "  \n")
        text = re.sub(r"[ \t]+", " ", text)
        return "\n".join(line.strip() for line in text.split("\n")).strip()

    def blocks(self, node, out):
        pending = []

        def flush():
            text = self.tidy("".join(pending))
            if text:
                out.append(text)
            pending.clear()

        for child in node.children:
            if isinstance(child, str) or child.tag not in BLOCK_TAGS:
                pending.append(self.inline(child))
                continue
            if skipped(child):
                continue
            flush()
            self.block(child, out)
        flush()

    def block(self, node, out):
        tag = node.tag
        classes = node.classes
        if "starRating" in classes:
            stars = sum(1 for n in node.find_all(lambda n: "checked" in n.classes))
            if stars:
                out.append(f"Importance: {'★' * stars}{'☆' * (5 - stars)}")
        elif "tags-new" in classes:
            tags = [self.tidy(self.inline(li)) for li in node.find_all(lambda n: n.tag == "li")]
            if tags:
                out.append("Tags: " + ", ".join(t for t in tags if t))
        elif tag in HEADING_LEVEL:
            text = self.tidy(self.inline(node)).replace("  \n", " ")
            if text:
                out.append(f"{'#' * HEADING_LEVEL[tag]} {text}")
        elif tag == "h6":
            text = self.tidy(self.inline(node))
            if text:
                out.append(f"*{text}*")
        elif tag in ("ul", "ol"):
            lines = self.list_lines(node, 0)
            if lines:
                out.append("\n".join(lines))
        elif tag == "table":
            table = self.table(node)
            if table:
                out.append(table)
        elif tag == "blockquote":
            inner = []
            self.blocks(node, inner)
            if inner:
                out.append("\n".join("> " + line for line in "\n\n".join(inner).split("\n")))
        elif tag != "hr":
            self.blocks(node, out)

    def list_lines(self, node, depth):
        lines = []
        index = 0
        for li in node.children:
            if not isinstance(li, Node) or li.tag != "li" or skipped(li):
                continue
            index += 1
            marker = f"{index}." if node.tag == "ol" else "-"
            text_parts = []
            nested = []
            for child in li.children:
                if isinstance(child, Node) and child.tag in ("ul", "ol"):
                    nested.extend(self.list_lines(child, depth + 1))
                elif isinstance(child, Node) and child.tag == "table":
                    table = self.table(child)
                    if table:
                        nested.extend("    " * (depth + 1) + line for line in table.split("\n"))
                else:
                    text_parts.append(self.inline(child))
            text = self.tidy("".join(text_parts)).replace("\n", " ")
            if text or nested:
                lines.append(f"{'    ' * depth}{marker} {text}".rstrip())
                lines.extend(nested)
        return lines

    def table(self, node):
        rows = []
        for tr in node.find_all(lambda n: n.tag == "tr"):
            cells = [
                self.tidy(self.inline(cell)).replace("\n", " ").replace("|", "\\|")
                for cell in tr.children
                if isinstance(cell, Node) and cell.tag in ("td", "th")
            ]
            if any(cells):
                rows.append(cells)
        if not rows:
            return ""
        width = max(len(row) for row in rows)
        if width == 1:
            # Drishti uses one-cell tables as callout boxes (practice questions, "Read more").
            return "\n>\n".join("> " + row[0] for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
        lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
        return "\n".join(lines)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def topics_with_category(node, category=None):
    """Yield (category h6, article-detail) pairs in page order; skips the page sidebar."""
    for child in node.children:
        if not isinstance(child, Node) or skipped(child):
            continue
        if child.tag == "h6":
            category = child
        elif "article-detail" in child.classes:
            yield category, child
        else:
            for pair in topics_with_category(child, category):
                category = pair[0]
                yield pair


def drishti_markdown(day):
    url = PAGE_URL.format(day.strftime("%d-%m-%Y"))
    root = parse_html(fetch(url))
    container = next(root.find_all(lambda n: "list-category" in n.classes), None)
    if container is None:
        return None, url
    renderer = MarkdownRenderer(url)
    out = []
    count = 0
    for category, topic in topics_with_category(container):
        if not any(renderer.inline(h1).strip() for h1 in topic.find_all(lambda n: n.tag == "h1")):
            continue
        count += 1
        out.append("---")
        if category is not None:
            renderer.block(category, out)
        renderer.blocks(topic, out)
    if not count:
        return None, url
    return "\n\n".join(out), url, count


def parse_day(value):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD or DD-MM-YYYY, got {value!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=os.environ.get("DAILY_NEWS_DIR", DEFAULT_OUT_DIR),
        help="folder for the YYYY-MM-DD.md note (default: %(default)s)",
    )
    parser.add_argument("--date", type=parse_day, help="fetch this date only (YYYY-MM-DD)")
    args = parser.parse_args()

    today = date.today()
    # Drishti publishes later in the day and skips Sundays, so fall back a few days.
    candidates = [args.date] if args.date else [today - timedelta(days=n) for n in range(FALLBACK_DAYS + 1)]
    for day in candidates:
        try:
            result = drishti_markdown(day)
        except Exception as err:
            print(f"{day}: {type(err).__name__}: {err}", file=sys.stderr)
            continue
        if result[0] is None:
            print(f"{day}: no Drishti IAS news analysis published yet ({result[1]})", file=sys.stderr)
            continue
        body, url, count = result
        break
    else:
        return 1

    header = "\n".join([
        "---",
        f"date: {day.isoformat()}",
        f"source: {url}",
        f"fetched: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"topics: {count}",
        "tags: [daily-news, drishti-ias]",
        "---",
        "",
        f"# Drishti IAS News Analysis: {day.strftime('%A, %d %B %Y')}",
        "",
        "",
    ])
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"{day.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as note:
        note.write(header + body + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
