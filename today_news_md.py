#!/usr/bin/env python3
"""Write Drishti IAS daily news analysis to an Obsidian-friendly Markdown note.

Fetches today's page, falling back to the latest page from the previous few days when
today's is not published yet. A day whose note already exists is not downloaded again
unless --refresh is given, except today's and yesterday's, which Drishti is still
filling in and are fetched again. Each note gets a topic index and previous/next links, and
the folder's hub note lists every day. Uses only the standard library so it runs from
Obsidian with the system python3.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import quote as url_quote, urlencode, urljoin

PAGE_URL = "https://www.drishtiias.com/current-affairs-news-analysis-editorials/news-analysis/{}"
DEFAULT_OUT_DIR = os.path.join(os.path.expanduser("~"), "notes", "Daily News")
USER_AGENT = "Mozilla/5.0 (DailyNews today_news_md)"
FALLBACK_DAYS = 3
# Drishti keeps adding topics to a day's page into the next day, so saved notes this
# recent are downloaded again rather than reused.
RECHECK_DAYS = 1
HUB_NOTE = "Daily News.md"
HUB_DAYS_WITH_TOPICS = 30
NOTE_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
NAV_MARK = "%%nav%%"

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
FAQ_HEADING = re.compile(r"^#{3,5} .*frequently asked questions", re.I)
PYQ_HEADING = re.compile(r"^#{3,5} .*previous year question", re.I)
GS_TAG = re.compile(r"^GS Paper\s*-?\s*(\d)$", re.I)
YOUTUBE_EMBED = re.compile(r"youtube(?:-nocookie)?\.com/embed/([\w-]{6,})")
SOURCE_LINK = re.compile(r"\[Source:\s*([^\]]+?)\]\((\S+?)\)", re.I)
# Drishti's series labels; they repeat the topic's category, so they are not keywords.
SERIES_TAGS = {
    "rapid fire ca", "rapid fire", "quick facts for prelims", "important facts for prelims",
    "facts for upsc mains", "prelims facts", "mains facts",
}
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_ARTICLE = "https://en.wikipedia.org/wiki/{}"
WIKI_SEARCH = "https://en.wikipedia.org/wiki/Special:Search?{}"
WIKI_BATCH = 50
DRISHTI_LINK = re.compile(
    r"(?<!!)\[([^\]]+)\]\((https?://(?:www\.)?(?:drishtiias\.com/|google\.com/search\?)[^)\s]*)\)"
)
# Bare clause titles such as "Article 19(1)(a)" match unrelated articles, so they are searched.
CONSTITUTION_ARTICLE = re.compile(r"^Articles? \d", re.I)
IMAGE_URL = re.compile(r"/images/|\.(?:png|jpe?g|gif|webp|svg|pdf)(?:\?|$)", re.I)
GENERIC_LINK_TEXT = re.compile(r"^(?:read more|click here|here|link|more|source|drishti(?: ias)?)$", re.I)
ACRONYM = re.compile(r"(?=(?:.*[A-Z]){2})[A-Z][A-Za-z0-9&.-]{1,11}")


class Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.hidden = False

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def find_all(self, predicate):
        for child in self.children:
            if isinstance(child, Node):
                if predicate(child):
                    yield child
                yield from child.find_all(predicate)

    def find(self, predicate):
        return next(self.find_all(predicate), None)


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

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
        node.hidden
        or node.tag in SKIP_TAGS
        or node.classes & SKIP_CLASSES
        or node.attrs.get("id") in SKIP_IDS
        or node.attrs.get("type") == "hidden"
    )


def plain_text(node):
    if isinstance(node, str):
        return node
    if skipped(node):
        return ""
    return "".join(plain_text(child) for child in node.children)


def clean_text(text):
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def heading_text(title):
    """Heading text that Obsidian can link to with [[#...]]."""
    return clean_text(re.sub(r"[#|^\[\]]", " ", title))


def heading_ref(title):
    return clean_text(re.sub(r"[#|^:%\[\]]", " ", title))


def quote(text, depth=1):
    prefix = ">" * depth
    return "\n".join(f"{prefix} {line}".rstrip() for line in text.split("\n"))


def callout(kind, title, body, folded=False):
    head = f"> [!{kind}]{'-' if folded else ''} {title}".rstrip()
    return head + ("\n" + quote(body) if body else "")


class MarkdownRenderer:
    def __init__(self, base_url):
        self.base_url = base_url

    def link(self, href):
        return urljoin(self.base_url, href.strip()).replace(" ", "%20").replace(")", "%29")

    def inline(self, node):
        if isinstance(node, str):
            return re.sub(r"\s+", " ", node.replace("\xa0", " "))
        if node.tag == "iframe" and not node.hidden:
            video = YOUTUBE_EMBED.search(node.attrs.get("src", ""))
            # Obsidian embeds a playable YouTube video for image syntax on a watch URL.
            return f"<br>![](https://www.youtube.com/watch?v={video.group(1)})<br>" if video else ""
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
            lead, inner, trail = re.match(r"^((?:\s|<br>)*)(.*?)((?:\s|<br>)*)$", text, re.S).groups()
            if (
                not re.search(r"\w", inner)
                or inner.startswith(mark) and inner.endswith(mark)
                or re.fullmatch(r"(?:!\[[^\]]*\]\([^)]*\)|\s|<br>)+", inner)
            ):
                return text
            # "**phrase,**" -> "**phrase**," so emphasis ends at the word.
            inner, punct = re.match(r"^(.*?)([,.;]*)$", inner, re.S).groups()
            return f"{lead}{mark}{inner}{mark}{punct}{trail}"
        if tag == "a":
            href = node.attrs.get("href", "")
            lead, inner, trail = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S).groups()
            if not inner or not href or href.startswith(("javascript:", "#")):
                return text
            if re.fullmatch(r"!\[[^\]]*\]\([^)]*\)", inner):
                return inner
            # Links are already coloured; bold or italic link text reads as shouting.
            inner, punct = re.match(r"^(.*?)([,.;]*)$", re.sub(r"\*+", "", inner).strip(), re.S).groups()
            return f"{lead}[{inner}]({self.link(href)}){punct}{trail}"
        if tag == "u" or "underline" in node.attrs.get("style", ""):
            lead, inner, trail = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S).groups()
            return f"{lead}<u>{inner}</u>{trail}" if re.search(r"\w", inner) else text
        return text

    def flow(self, node, skip=()):
        """Inline text of a list item or table cell, keeping its paragraph breaks as <br>."""
        parts = []
        for child in node.children:
            if isinstance(child, Node) and child.tag in skip:
                continue
            if isinstance(child, Node) and child.tag in BLOCK_TAGS and not skipped(child):
                if child.tag in ("ul", "ol"):
                    text = "<br>".join(
                        "• " + self.flow(li) for li in child.children
                        if isinstance(li, Node) and li.tag == "li" and not skipped(li)
                    )
                else:
                    text = self.flow(child)
                parts.append(f"<br>{text}<br>")
            else:
                parts.append(self.inline(child))
        text = self.tidy("".join(parts)).replace("  \n", "<br>").replace("\n", " ")
        text = re.sub(r"(?:\s*<br>\s*)+", "<br>", text)
        return re.sub(r"^(?:<br>)+|(?:<br>)+$", "", text).strip()

    def tidy(self, text):
        text = text.replace("****", "").replace("<br>", "  \n")
        # Drishti splits one bold phrase across tags: "**31st** **October**" -> "**31st October**".
        text = re.sub(r"(?<=\w)\*\* \*\*(?=\w)", " ", text)
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
        if "border-bg" in node.classes:
            inner = []
            self.blocks(node, inner)
            if not inner:
                return
            body = "\n\n".join(inner)
            if body.lstrip("*").lower().startswith("for prelims"):
                out.append(callout("abstract", "Syllabus", body))
            elif re.match(r"^#{3,5} Summary$", inner[0], re.I):
                out.append(callout("summary", "Summary", "\n\n".join(inner[1:])))
            elif inner[0].startswith("#"):
                out.extend(inner)
            else:
                out.append(callout("note", "", body))
        elif tag in HEADING_LEVEL:
            text = self.tidy(self.inline(node)).replace("  \n", " ")
            if text:
                out.append(f"{'#' * HEADING_LEVEL[tag]} {text}")
        elif tag == "h6":
            text = self.tidy(self.inline(node))
            if text:
                out.append(f"*{text}*")
        elif tag == "figcaption":
            text = self.flow(node)
            if text:
                out.append(f"*{text.strip('*')}*")
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
                out.append(quote("\n\n".join(inner)))
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
            nested = []
            for child in li.children:
                if isinstance(child, Node) and child.tag in ("ul", "ol"):
                    nested.extend(self.list_lines(child, depth + 1))
                elif isinstance(child, Node) and child.tag == "table":
                    table = self.table(child)
                    if table:
                        nested.extend("    " * (depth + 1) + line for line in table.split("\n"))
            text = self.flow(li, skip=("ul", "ol", "table"))
            if text or nested:
                lines.append(f"{'    ' * depth}{marker} {text}".rstrip())
                lines.extend(nested)
        return lines

    def table(self, node):
        rows = []
        cell_nodes = [
            [cell for cell in tr.children if isinstance(cell, Node) and cell.tag in ("td", "th")]
            for tr in node.find_all(lambda n: n.tag == "tr")
        ]
        cell_nodes = [row for row in cell_nodes if row]
        if not cell_nodes:
            return ""
        if max(len(row) for row in cell_nodes) == 1:
            # Drishti uses one-cell tables as callout boxes (practice questions, "Read more"),
            # so their cells keep full block formatting.
            blocks = []
            for row in cell_nodes:
                self.blocks(row[0], blocks)
            body = "\n\n".join(blocks)
            plain = re.sub(r"</?u>|[*\s]", "", body).lower()
            # The callout title repeats Drishti's label, so drop it from the body.
            label = r"^(?:[*\s:]|</?u>)*{}(?:[*\s:]|</?u>)*"
            if "mains" in plain and "question" in plain:
                body = re.sub(label.format(r"Drishti Mains (?:Practice )?Question"), "", body, flags=re.I)
                return callout("question", "Mains practice question", body)
            if plain.startswith("readmore"):
                body = re.sub(label.format(r"Read more"), "", body, flags=re.I)
                return callout("tip", "Read more", body)
            return callout("note", "", body) if body else ""
        rows = []
        for row in cell_nodes:
            cells = [self.flow(cell).replace("|", "\\|") for cell in row]
            if any(cells):
                rows.append(cells)
        if not rows:
            return ""
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
        lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
        return "\n".join(lines)


def fold_question_sections(blocks):
    """Collapse the trailing FAQ and previous-year-question sections into folded callouts."""
    out = []
    section = None
    for block in blocks:
        kind = "faq" if FAQ_HEADING.match(block) else "pyq" if PYQ_HEADING.match(block) else None
        if kind:
            if section:
                out.append(section)
            section = {"kind": kind, "body": []}
            continue
        if section is None:
            out.append(block)
            continue
        heading = re.match(r"^#{3,6} (.*)$", block)
        label = re.sub(r"</?u>", "", heading.group(1)).strip("* ") if heading else ""
        section["body"].append(f"**{label}**" if heading else block)
    if section:
        out.append(section)
    return [
        callout(
            "faq" if item["kind"] == "faq" else "example",
            "FAQs" if item["kind"] == "faq" else "UPSC previous year questions",
            "\n\n".join(item["body"]),
            folded=True,
        )
        if isinstance(item, dict) else item
        for item in out
    ]


class Topic:
    def __init__(self, title, url, category, stars, tags, body):
        self.title = title
        self.url = url
        self.category = category
        self.stars = stars
        self.tags = tags
        self.sources, self.body = split_sources(body)

    @property
    def gs_papers(self):
        return sorted({f"GS{m.group(1)}" for m in (GS_TAG.match(t) for t in self.tags) if m})

    @property
    def keywords(self):
        return [t for t in self.tags if not GS_TAG.match(t) and t.lower() not in SERIES_TAGS]

    def markdown(self):
        meta = [f"**{self.category}**"] if self.category else []
        if self.stars:
            meta.append("★" * self.stars + "☆" * (5 - self.stars))
        meta.extend(f"#{gs}" for gs in self.gs_papers)
        if self.url:
            meta.append(f"[Drishti]({self.url})")
        meta.extend(f"[Source: {name}]({url})" for name, url in self.sources)
        lines = [f"## {heading_text(self.title)}", "", " · ".join(meta)]
        if self.keywords:
            lines.append(f"<small>{html.escape(', '.join(self.keywords))}</small>")
        return "\n".join(lines + [""] + ["\n\n".join(self.body)])


def split_sources(body):
    """Pull Drishti's "Source: TH" paragraphs out of the body for the topic header."""
    sources = []
    rest = []
    for block in body:
        found = SOURCE_LINK.findall(block)
        if found and not SOURCE_LINK.sub("", block).strip(" ,|"):
            sources.extend((name.strip(), url) for name, url in found)
        else:
            rest.append(block)
    return sources, rest


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


def parse_topic(renderer, category, detail):
    h1 = detail.find(lambda n: n.tag == "h1")
    title = clean_text(plain_text(h1)) if h1 else ""
    if not title:
        return None
    anchor = h1.find(lambda n: n.tag == "a" and n.attrs.get("href"))
    stars_node = detail.find(lambda n: "starRating" in n.classes)
    tags_node = detail.find(lambda n: "tags-new" in n.classes)
    stars = len(list(stars_node.find_all(lambda n: "checked" in n.classes))) if stars_node else 0
    tags = [clean_text(plain_text(li)) for li in tags_node.find_all(lambda n: n.tag == "li")] if tags_node else []
    for node in (h1, stars_node, tags_node):
        if node is not None:
            node.hidden = True
    body = []
    renderer.blocks(detail, body)
    return Topic(
        title=title,
        url=renderer.link(anchor.attrs["href"]) if anchor else "",
        category=clean_text(plain_text(category)) if category is not None else "",
        stars=stars,
        tags=[t for t in tags if t],
        body=fold_question_sections(body),
    )


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def sentence_case(text):
    words = text.split(" ")
    return " ".join(
        [words[0]] + [w if w.isupper() or re.search(r"\d", w) else w.lower() for w in words[1:]]
    )


def wiki_candidates(text):
    """Likely Wikipedia titles for a link's text, best first."""
    text = re.sub(r"</?u>|\*+|\\", "", text)
    text = re.sub(r"\s*[-|:]\s*Drishti(?: IAS)?$", "", text, flags=re.I)
    text = clean_text(text.replace("_", " ")).strip(" ,.;:")
    while text.endswith(")") and text.count(")") > text.count("("):
        text = text[:-1].rstrip(" ,")
    if CONSTITUTION_ARTICLE.match(text):
        return []
    # Only parentheticals after a space are asides; "Article 15(3)" keeps its clause.
    bare = clean_text(re.sub(r"\s+\([^)]*\)", " ", re.sub(r"['’]s\b", "", text))).strip(" ,")
    names = [text, bare, bare.split(",")[0].strip()]
    names += [inner for inner in re.findall(r"\(([^)]+)\)", text) if ACRONYM.fullmatch(inner)]
    names += [sentence_case(name) for name in names]
    return [n for n in dict.fromkeys(names) if n and not re.search(r"[#<>\[\]{}|]", n)]


def wikipedia_titles(names):
    """Map each name to the article it resolves to, following redirects and skipping disambiguation pages."""
    found = {}
    names = list(dict.fromkeys(names))
    for start in range(0, len(names), WIKI_BATCH):
        batch = names[start:start + WIKI_BATCH]
        query = urlencode({
            "action": "query", "format": "json", "formatversion": 2, "redirects": 1,
            "prop": "pageprops", "ppprop": "disambiguation", "titles": "|".join(batch),
        })
        try:
            result = json.loads(fetch(f"{WIKI_API}?{query}")).get("query", {})
        except Exception as err:
            print(f"Wikipedia lookup failed: {type(err).__name__}: {err}", file=sys.stderr)
            continue
        normalized = {r["from"]: r["to"] for r in result.get("normalized", [])}
        redirects = {r["from"]: (r["to"], r.get("tofragment")) for r in result.get("redirects", [])}
        articles = {
            page["title"] for page in result.get("pages", [])
            if not page.get("missing") and not page.get("invalid")
            and "disambiguation" not in page.get("pageprops", {})
        }
        for name in batch:
            title, fragment = normalized.get(name, name), None
            for _ in range(5):
                if title not in redirects:
                    break
                title, fragment = redirects[title]
            if title in articles:
                found[name] = (title, fragment)
    return found


def wikipedia_url(title, fragment=None):
    url = WIKI_ARTICLE.format(url_quote(title.replace(" ", "_"), safe="_,:/'"))
    return url + (f"#{url_quote(fragment.replace(' ', '_'), safe='_.:')}" if fragment else "")


def link_to_wikipedia(topics):
    """Point the body's links to other Drishti articles at Wikipedia instead.

    A link whose text names no Wikipedia article opens a Wikipedia search for it.
    Image links and generic text such as "Read more" keep their Drishti target.
    """
    def wanted(match):
        return not IMAGE_URL.search(match.group(2)) and not GENERIC_LINK_TEXT.match(match.group(1).strip("* "))

    texts = {
        m.group(1) for topic in topics for block in topic.body
        for m in DRISHTI_LINK.finditer(block) if wanted(m)
    }
    options = {text: wiki_candidates(text) for text in texts}
    found = wikipedia_titles(name for names in options.values() for name in names)

    def replace(match):
        if not wanted(match):
            return match.group(0)
        text = match.group(1)
        hit = next((found[name] for name in options[text] if name in found), None)
        if hit:
            return f"[{text}]({wikipedia_url(*hit)})"
        search = (options[text] or [clean_text(re.sub(r"\*+", "", text)).strip(" ,.;:")])[0]
        if CONSTITUTION_ARTICLE.match(search) and "constitution" not in search.lower():
            search += " Constitution of India"
        return f"[{text}]({WIKI_SEARCH.format(urlencode({'search': search, 'go': 'Go'}))})"

    for topic in topics:
        topic.body = [DRISHTI_LINK.sub(replace, block) for block in topic.body]


def drishti_topics(day):
    url = PAGE_URL.format(day.strftime("%d-%m-%Y"))
    root = parse_html(fetch(url))
    container = root.find(lambda n: "list-category" in n.classes)
    renderer = MarkdownRenderer(url)
    topics = []
    if container is not None:
        for category, detail in topics_with_category(container):
            topic = parse_topic(renderer, category, detail)
            if topic:
                topics.append(topic)
    link_to_wikipedia(topics)
    return url, topics


def render_note(day, topics):
    index = "\n".join(
        f"{n}. [[#{heading_ref(t.title)}|{heading_text(t.title)}]]"
        + (f" · {'★' * t.stars}" if t.stars else "")
        + (f" · *{t.category}*" if t.category else "")
        for n, t in enumerate(topics, 1)
    )
    parts = [
        f"# Drishti IAS: {day.strftime('%A, %d %B %Y')}",
        NAV_MARK,
        callout("summary", f"{len(topics)} topics", index),
    ]
    for topic in topics:
        parts += ["---", topic.markdown()]
    return "\n\n".join(parts) + "\n"


def note_days(out_dir):
    days = []
    for name in os.listdir(out_dir):
        match = NOTE_NAME.match(name)
        if match:
            days.append(match.group(1))
    return sorted(days)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write_if_changed(path, text):
    if os.path.exists(path) and read(path) == text:
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def short_day(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%a %d %b")


def update_navigation(out_dir, days):
    hub = os.path.splitext(HUB_NOTE)[0]
    for i, day in enumerate(days):
        path = os.path.join(out_dir, f"{day}.md")
        text = read(path)
        links = []
        if i > 0:
            links.append(f"[[{days[i - 1]}|← {short_day(days[i - 1])}]]")
        links.append(f"[[{hub}|All days]]")
        if i + 1 < len(days):
            links.append(f"[[{days[i + 1]}|{short_day(days[i + 1])} →]]")
        nav = f"{NAV_MARK} " + " · ".join(links)
        lines = text.split("\n")
        for n, line in enumerate(lines):
            if line.startswith(NAV_MARK):
                lines[n] = nav
                write_if_changed(path, "\n".join(lines))
                break


def note_topics(text):
    titles = []
    for line in text.split("\n"):
        if line.startswith("## "):
            title = re.sub(r"^\[(.*)\]\(.*\)$", r"\1", line[3:].strip())
            titles.append(heading_text(title))
    return titles


def update_hub(out_dir, days):
    lines = [
        "# Daily News",
        "",
        "Drishti IAS daily news analysis, newest first. Press `Space o n` in Obsidian (or run "
        "\"Fetch Drishti IAS news analysis into Daily News\" from the command palette) to fetch "
        "the latest day. This note is regenerated on every fetch.",
        "",
        "Source: `~/.config/Tools/DailyNews/today_news_md.py`",
    ]
    recent = list(reversed(days))
    for day in recent[:HUB_DAYS_WITH_TOPICS]:
        topics = note_topics(read(os.path.join(out_dir, f"{day}.md")))
        lines += ["", f"## [[{day}|{datetime.strptime(day, '%Y-%m-%d').strftime('%A, %d %B %Y')}]]", ""]
        lines += [f"- [[{day}#{heading_ref(t)}|{t}]]" for t in topics] or ["- (no topics)"]
    older = recent[HUB_DAYS_WITH_TOPICS:]
    if older:
        lines += ["", "## Older", ""] + [f"- [[{day}|{short_day(day)} {day[:4]}]]" for day in older]
    write_if_changed(os.path.join(out_dir, HUB_NOTE), "\n".join(lines) + "\n")


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
        help="folder for the YYYY-MM-DD.md notes (default: %(default)s)",
    )
    parser.add_argument("--date", type=parse_day, help="fetch this date only (YYYY-MM-DD)")
    parser.add_argument(
        "--refresh", action="store_true", help="re-download even if the day's note already exists"
    )
    args = parser.parse_args()

    today = date.today()
    # Drishti publishes later in the day and skips Sundays, so fall back a few days.
    candidates = [args.date] if args.date else [today - timedelta(days=n) for n in range(FALLBACK_DAYS + 1)]

    # Newest first: an older saved note is used as is; missing and recent days are
    # downloaded, keeping the saved note when the download fails or comes back empty.
    for day in candidates:
        path = os.path.join(args.out_dir, f"{day.isoformat()}.md")
        saved = os.path.exists(path)
        if saved and not args.refresh and (today - day).days > RECHECK_DAYS:
            print(path)
            return 0
        try:
            url, topics = drishti_topics(day)
        except Exception as err:
            print(f"{day}: {type(err).__name__}: {err}", file=sys.stderr)
            topics = []
            url = None
        if topics:
            break
        if saved:
            print(path)
            return 0
        if url:
            print(f"{day}: no Drishti IAS news analysis published yet ({url})", file=sys.stderr)
    else:
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    write_if_changed(path, render_note(day, topics))
    days = note_days(args.out_dir)
    update_navigation(args.out_dir, days)
    update_hub(args.out_dir, days)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
