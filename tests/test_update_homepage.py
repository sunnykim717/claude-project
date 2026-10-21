import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import update_homepage as uh

KST = timezone(timedelta(hours=9))
FIXED_NOW = datetime(2026, 10, 21, 9, 30, tzinfo=KST)


class LoadSiteTest(unittest.TestCase):
    def _write(self, data):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False)
        json.dump(data, tmp, ensure_ascii=False)
        tmp.close()
        return Path(tmp.name)

    def test_missing_title_raises(self):
        path = self._write({"items": []})
        with self.assertRaises(ValueError):
            uh.load_site(path)

    def test_item_without_title_raises(self):
        path = self._write({"title": "t", "items": [{"date": "2026-01-01"}]})
        with self.assertRaises(ValueError):
            uh.load_site(path)

    def test_javascript_url_raises(self):
        path = self._write({"title": "t", "items": [{"title": "a", "url": "javascript:alert(1)"}]})
        with self.assertRaises(ValueError):
            uh.load_site(path)

    def test_bad_date_raises(self):
        path = self._write({"title": "t", "items": [{"title": "a", "date": "2026/10/21"}]})
        with self.assertRaises(ValueError):
            uh.load_site(path)

    def test_valid_file_loads(self):
        path = self._write({"title": "t", "items": [{"title": "a"}]})
        self.assertEqual(uh.load_site(path)["title"], "t")


class RenderPageTest(unittest.TestCase):
    def test_items_sorted_newest_first(self):
        site = {
            "title": "t",
            "items": [
                {"title": "old", "date": "2026-01-01"},
                {"title": "new", "date": "2026-10-01"},
            ],
        }
        page = uh.render_page(site, FIXED_NOW)
        self.assertLess(page.index("new"), page.index("old"))

    def test_html_is_escaped(self):
        site = {"title": "<script>x</script>", "items": [{"title": "a & b", "summary": "<b>"}]}
        page = uh.render_page(site, FIXED_NOW)
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)
        self.assertIn("a &amp; b", page)
        self.assertIn("&lt;b&gt;", page)

    def test_url_is_escaped_in_href(self):
        site = {"title": "t", "items": [{"title": "a", "url": 'https://x.test/?q="1"'}]}
        page = uh.render_page(site, FIXED_NOW)
        self.assertIn('href="https://x.test/?q=&quot;1&quot;"', page)

    def test_footer_shows_update_time(self):
        page = uh.render_page({"title": "t", "items": []}, FIXED_NOW)
        self.assertIn("마지막 자동 업데이트: 2026-10-21 09:30 (KST)", page)

    def test_main_writes_output(self):
        with tempfile.TemporaryDirectory() as d:
            data = Path(d) / "site.json"
            out = Path(d) / "index.html"
            data.write_text(json.dumps({"title": "홈", "items": []}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(uh.main(["--data", str(data), "--output", str(out)]), 0)
            self.assertIn("<title>홈</title>", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
