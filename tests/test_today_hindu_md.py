import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import today_hindu_md as hindu


def rss(day, section="editorial"):
    return f"""<rss><channel><item><title>Today's editorial</title>
    <link>https://www.thehindu.com/opinion/{section}/test/article123.ece</link>
    <pubDate>{day.strftime('%a, %d %b %Y')} 01:00:00 +0530</pubDate>
    <description>&lt;p&gt;A short preview.&lt;/p&gt;</description></item></channel></rss>"""


class HinduTests(unittest.TestCase):
    def test_editorial_filter_and_indian_publication_date(self):
        day = datetime(2026, 11, 14).date()
        self.assertEqual(hindu.feed_entries(rss(day))[0]["day"], day)
        self.assertEqual(hindu.feed_entries(rss(day, "op-ed")), [])
        for url in ("https://www.thehindu.com.evil.test/opinion/editorial/a.ece",
                    "https://example.com/opinion/editorial/a.ece"):
            self.assertFalse(hindu.editorial_url(url))

    def test_body_keeps_formatting_and_omits_page_chrome(self):
        page = '<nav>Navigation</nav><div itemprop="articleBody"><p>Public <b>text</b>.</p>' \
               '<div class="related-articles"><p>Unrelated</p></div><script>bad()</script></div>'
        body = hindu.article_markdown(page, "https://www.thehindu.com/")
        self.assertIn("Public **text**.", body)
        for unwanted in ("Navigation", "Unrelated", "bad()"):
            self.assertNotIn(unwanted, body)

    def test_schema_body_excludes_sharing_controls(self):
        page = '<div itemprop="articleBody"><div class="schemaDiv"><p>Editorial</p></div>' \
               '<div class="comments-shares"><p>Copy link</p></div></div>'
        self.assertEqual(hindu.article_markdown(page, hindu.FEED_URL), "Editorial")

    def test_unavailable_article_is_labeled_as_preview(self):
        entry = hindu.feed_entries(rss(datetime.now(hindu.IST).date()))[0]
        with patch.object(hindu, "fetch", return_value="<p>Subscribe</p>"):
            text = hindu.render_note(entry["day"], [entry])
        self.assertIn("RSS preview", text)
        self.assertIn("A short preview.", text)
        self.assertIn(entry["url"], text)
        self.assertNotIn("<p>Subscribe</p>", text)

    def test_latest_published_day_and_folder_qualified_index(self):
        yesterday = datetime.now(hindu.IST).date() - timedelta(days=1)
        with tempfile.TemporaryDirectory() as temp:
            out = os.path.join(temp, hindu.FOLDER)
            output = io.StringIO()
            with patch.object(hindu, "fetch", side_effect=[rss(yesterday), '<div itemprop="articleBody"><p>Article</p></div>']), contextlib.redirect_stdout(output):
                self.assertEqual(hindu.main(["--out-dir", out]), 0)
            note = Path(output.getvalue().strip())
            self.assertEqual(note.name, f"{yesterday}.md")
            self.assertIn("Article", note.read_text())
            self.assertIn(f"[[{hindu.FOLDER}/{yesterday}|", (Path(out) / f"{hindu.FOLDER}.md").read_text())

    def test_network_failure_preserves_saved_note(self):
        day = datetime.now(hindu.IST).date()
        with tempfile.TemporaryDirectory() as temp:
            note = Path(temp) / f"{day}.md"
            note.write_text("My saved content")
            output = io.StringIO()
            with patch.object(hindu, "fetch", side_effect=OSError("offline")), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(hindu.main(["--out-dir", temp, "--refresh"]), 0)
            self.assertEqual(note.read_text(), "My saved content")
            self.assertEqual(output.getvalue().strip(), str(note))

    def test_explicit_date_reuses_archive_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            note = Path(temp) / "2025-01-01.md"
            note.write_text("Archived")
            with patch.object(hindu, "fetch") as fetch, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(hindu.main(["--out-dir", temp, "--date", "2025-01-01"]), 0)
            fetch.assert_not_called()

    def test_missing_day_fails_without_writing_a_note(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(hindu, "fetch", return_value="<rss><channel/></rss>"), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(hindu.main(["--out-dir", temp, "--date", "2025-01-01"]), 1)
            self.assertEqual(os.listdir(temp), [])


if __name__ == "__main__":
    unittest.main()
