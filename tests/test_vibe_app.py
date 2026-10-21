import json
import tempfile
import unittest
from pathlib import Path

from vibe import build_app as ba

EXAMPLE = Path(__file__).resolve().parent.parent / "vibe" / "examples" / "visit_form.json"


def _spec(**overrides):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec.update(overrides)
    return spec


class StructureTest(unittest.TestCase):
    def test_example_structure_is_valid(self):
        self.assertEqual(ba.validate_structure(json.loads(EXAMPLE.read_text(encoding="utf-8"))), [])

    def test_more_than_two_pages_rejected(self):
        spec = _spec(pages=[{"name": "a", "fields": []}, {"name": "b", "fields": []}, {"name": "c", "fields": []}])
        self.assertTrue(any("2개" in e for e in ba.validate_structure(spec)))

    def test_min_max_only_for_number(self):
        spec = _spec()
        spec["pages"][0]["fields"][0]["min"] = 1
        self.assertTrue(any("number" in e for e in ba.validate_structure(spec)))

    def test_min_today_only_for_date(self):
        spec = _spec()
        spec["pages"][0]["fields"][0]["minToday"] = True
        self.assertTrue(any("date" in e for e in ba.validate_structure(spec)))

    def test_min_greater_than_max_rejected(self):
        spec = _spec()
        number = [f for f in spec["pages"][0]["fields"] if f["type"] == "number"][0]
        number["min"], number["max"] = 30, 10
        self.assertTrue(any("min" in e and "max" in e for e in ba.validate_structure(spec)))


class BuildHtmlTest(unittest.TestCase):
    def test_page_has_all_fields_and_constraints(self):
        page = ba.build_html(_spec())
        self.assertIn('<input type="date" id="f4"', page)
        self.assertIn('max="20"', page)
        self.assertIn('min="1"', page)
        self.assertIn('<select id="f6"', page)
        self.assertIn('<input type="tel" id="f3"', page)
        self.assertIn('<h1>방문 신청 페이지</h1>', page)

    def test_no_external_resources(self):
        page = ba.build_html(_spec())
        self.assertNotIn("src=\"http", page)
        self.assertNotIn("href=\"http", page)

    def test_user_text_is_escaped_in_markup_and_script(self):
        spec = _spec(name="<img src=x onerror=alert(1)>", goal="<script>bad()</script>")
        spec["pages"][0]["fields"][0]["label"] = "</script><b>x</b>"
        page = ba.build_html(spec)
        self.assertNotIn("<img src=x", page)
        self.assertNotIn("<script>bad()", page)
        self.assertNotIn("</script><b>", page)
        self.assertIn("\\u003c/script\\u003e", page)

    def test_rules_shown_as_list(self):
        page = ba.build_html(_spec(rules=["인원은 1~20명"]))
        self.assertIn('<ul class="rules"><li>인원은 1~20명</li></ul>', page)

    def test_done_page_title_from_second_page(self):
        page = ba.build_html(_spec())
        self.assertIn('<h1>접수 완료</h1>', page)

    def test_single_page_gets_default_done_title(self):
        page = ba.build_html(_spec(pages=[_spec()["pages"][0]]))
        self.assertIn("<h1>제출 완료</h1>", page)


class MainTest(unittest.TestCase):
    def test_main_writes_html_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sub" / "index.html"
            self.assertEqual(ba.main([str(EXAMPLE), "--out", str(out)]), 0)
            self.assertIn("<!doctype html>", out.read_text(encoding="utf-8"))

    def test_main_rejects_invalid_spec(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text(json.dumps(_spec(name="", pages=[])), encoding="utf-8")
            self.assertEqual(ba.main([str(bad), "--out", str(Path(d) / "x.html")]), 1)


if __name__ == "__main__":
    unittest.main()
