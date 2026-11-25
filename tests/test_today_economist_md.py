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
import today_economist_md as economist


def item(day, slug="article", title="An article", published=None):
    stamp = published or day.strftime("%a, %d %b %Y 10:00:00 +0000")
    return f"""<item><title>{title}</title>
    <link>https://www.economist.com/leaders/{day:%Y/%m/%d}/{slug}</link>
    <pubDate>{stamp}</pubDate><description>&lt;p&gt;A public preview.&lt;/p&gt;</description></item>"""


def rss(*items):
    return "<rss><channel>" + "".join(items) + "</channel></rss>"


class EconomistTests(unittest.TestCase):
    def run_fetch(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = economist.main(list(args))
        return code, output.getvalue().strip()

    def test_feed_keeps_all_unique_articles_and_groups_by_indian_date(self):
        day = datetime(2026, 11, 16).date()
        first = item(day, published="Mon, 16 Nov 2026 23:00:00 +0000")
        entries = economist.feed_entries(rss(first, first, item(day, "second")))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["day"].isoformat(), "2026-11-17")
        self.assertEqual(entries[1]["day"], day)
        self.assertEqual(entries[0]["summary"], "A public preview.")

    def test_invalid_dates_foreign_urls_and_credentials_are_skipped(self):
        day = datetime(2026, 11, 16).date()
        good = item(day)
        bad = [item(day, published="not a date"), good.replace("www.economist.com", "evil.test"),
               good.replace("www.economist.com", "www.economist.com.evil.test"),
               good.replace("https://", "https://user:password@"),
               good.replace("https://www.economist.com", "http://["),
               item(day, title="")]
        self.assertEqual(economist.feed_entries(rss(*bad)), [])

    def test_latest_day_saves_every_article_as_a_labeled_preview_with_one_request(self):
        day = datetime.now(economist.IST).date() - timedelta(days=1)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(economist, "fetch", return_value=rss(
                item(day), item(day, "second", "Another article"), item(day - timedelta(days=1), "older")
            )) as fetch:
                code, output = self.run_fetch("--out-dir", temp)
            self.assertEqual(code, 0)
            note = Path(output)
            self.assertEqual(note.name, f"{day}.md")
            text = note.read_text()
            self.assertIn("RSS previews", text)
            self.assertIn("## An article", text)
            self.assertIn("## Another article", text)
            self.assertEqual(text.count("[Read at The Economist]"), 2)
            self.assertNotIn("/older", text)
            fetch.assert_called_once_with(economist.FEED_URL)

    def test_archive_reuse_and_refresh(self):
        day = datetime(2025, 1, 1).date()
        with tempfile.TemporaryDirectory() as temp:
            note = Path(temp) / f"{day}.md"
            note.write_text("Saved")
            with patch.object(economist, "fetch") as fetch:
                code, _ = self.run_fetch("--out-dir", temp, "--date", str(day))
                self.assertEqual(code, 0)
                fetch.assert_not_called()
            with patch.object(economist, "fetch", return_value=rss(item(day))):
                code, _ = self.run_fetch("--out-dir", temp, "--date", str(day), "--refresh")
            self.assertEqual(code, 0)
            self.assertIn("RSS previews", note.read_text())

    def test_network_failure_preserves_saved_notes(self):
        day = datetime.now(economist.IST).date()
        with tempfile.TemporaryDirectory() as temp:
            note = Path(temp) / f"{day}.md"
            note.write_text("Saved content")
            with patch.object(economist, "fetch", side_effect=OSError("offline")):
                code, output = self.run_fetch("--out-dir", temp, "--refresh")
            self.assertEqual(code, 0)
            self.assertEqual(output, str(note))
            self.assertEqual(note.read_text(), "Saved content")

    def test_unpublished_date_fails_without_creating_an_empty_note(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(economist, "fetch", return_value=rss()):
                code, _ = self.run_fetch("--out-dir", temp, "--date", "2026-11-01")
            self.assertEqual(code, 1)
            self.assertEqual(os.listdir(temp), [])

    def test_navigation_links_are_qualified_by_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / economist.FOLDER
            for iso in ("2026-11-12", "2026-11-13"):
                day = datetime.strptime(iso, "%Y-%m-%d").date()
                with patch.object(economist, "fetch", return_value=rss(item(day))):
                    code, _ = self.run_fetch("--out-dir", str(out), "--date", iso)
                    self.assertEqual(code, 0)
            first = (out / "2026-11-12.md").read_text()
            second = (out / "2026-11-13.md").read_text()
            self.assertIn("[[The Economist/2026-11-13|", first)
            self.assertIn("[[The Economist/2026-11-12|", second)
            self.assertIn("[[The Economist/The Economist|All days]]", first)
            hub = (out / "The Economist.md").read_text()
            self.assertLess(hub.index("2026-11-13"), hub.index("2026-11-12"))


if __name__ == "__main__":
    unittest.main()
