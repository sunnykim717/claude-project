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

    def test_completion_page_must_come_last(self):
        spec = _spec(pages=[{"name": "완료", "fields": []}, _spec()["pages"][0]])
        self.assertTrue(any("완료 화면보다 앞" in e for e in ba.validate_structure(spec)))

    def test_only_one_completion_page(self):
        spec = _spec(pages=[_spec()["pages"][0], {"name": "a", "fields": []}, {"name": "b", "fields": []}])
        self.assertTrue(any("하나만" in e for e in ba.validate_structure(spec)))

    def test_multiple_input_pages_allowed(self):
        form = _spec()["pages"][0]
        spec = _spec(pages=[form, dict(form, name="두 번째"), {"name": "완료", "fields": []}])
        self.assertEqual(ba.validate_structure(spec), [])

    def test_min_length_only_for_text_types(self):
        spec = _spec()
        number = [f for f in spec["pages"][0]["fields"] if f["type"] == "number"][0]
        number["minLength"] = 2
        self.assertTrue(any("minLength" in e for e in ba.validate_structure(spec)))

    def test_min_length_greater_than_max_rejected(self):
        spec = _spec()
        spec["pages"][0]["fields"][0].update(minLength=10, maxLength=2)
        self.assertTrue(any("minLength" in e and "maxLength" in e for e in ba.validate_structure(spec)))

    def test_checkbox_with_options_rejected(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "동의", "type": "checkbox", "options": ["예"]})
        self.assertTrue(any("checkbox" in e for e in ba.validate_structure(spec)))

    def test_save_must_be_boolean(self):
        self.assertTrue(any("'save'" in e for e in ba.validate_structure(_spec(save="yes"))))

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


class CodePanelTest(unittest.TestCase):
    def test_copy_source_is_page_without_panel(self):
        page = ba.build_html(_spec())
        self.assertIn('id="source"', page)
        # 상자 안의 코드는 상자 자체를 뺀 페이지여야 합니다.
        source = html_unescape(page.split('id="source" readonly rows="8" aria-label="페이지 코드">')[1].split("</textarea>")[0])
        self.assertTrue(source.startswith("<!doctype html>"))
        self.assertNotIn('id="code-panel"', source)
        self.assertNotIn('id="source"', source)

    def test_copy_source_has_no_user_input(self):
        page = ba.build_html(_spec())
        source = html_unescape(page.split('aria-label="페이지 코드">')[1].split("</textarea>")[0])
        self.assertNotIn("홍길동", source)

    def test_download_and_copy_buttons_present(self):
        page = ba.build_html(_spec())
        self.assertIn('id="copy-code"', page)
        self.assertIn('id="download-code"', page)

    def test_github_button_only_when_configured(self):
        self.assertNotIn('id="github-link"', ba.build_html(_spec()))
        github = ba.validate_github("owner-name/repo-name", "main", "index.html")
        self.assertIn('id="github-link"', ba.build_html(_spec(), github))

    def test_github_settings_validated(self):
        with self.assertRaises(ValueError):
            ba.validate_github("bad repo", "main", "index.html")
        with self.assertRaises(ValueError):
            ba.validate_github("a/b", "main; rm", "index.html")
        with self.assertRaises(ValueError):
            ba.validate_github("a/b", "main", "../index.html")
        self.assertIsNone(ba.validate_github(None, "main", "index.html"))

    def test_github_repo_and_path_embedded_as_json(self):
        github = ba.validate_github("a/b", "main", "site/index.html")
        page = ba.build_html(_spec(), github)
        self.assertIn('"repo": "a/b"', page)
        self.assertIn('"path": "site/index.html"', page)


class MultiStepAndSaveTest(unittest.TestCase):
    def _two_step_spec(self, **extra):
        form = _spec()["pages"][0]
        spec = _spec(pages=[form, dict(form, name="두 번째"), {"name": "완료", "fields": []}])
        spec.update(extra)
        return spec

    def test_each_input_page_becomes_a_step(self):
        page = ba.build_html(self._two_step_spec())
        self.assertEqual(page.count('class="step" data-step='), 2)
        self.assertIn("1 / 2 단계", page)
        self.assertIn('<button type="button" class="next">다음</button>', page)
        self.assertIn('<button type="submit">제출</button>', page)

    def test_single_step_has_no_progress_label(self):
        self.assertNotIn('class="progress"', ba.build_html(_spec()))

    def test_save_panel_only_when_enabled(self):
        self.assertNotIn('id="saved-panel"', ba.build_html(_spec()))
        page = ba.build_html(_spec(save=True))
        self.assertIn('id="saved-panel"', page)
        self.assertIn('id="download-csv"', page)
        self.assertIn('id="clear-saved"', page)
        self.assertIn("이 브라우저에만 저장됩니다", page)

    def test_storage_key_is_named_after_page(self):
        page = ba.build_html(_spec(save=True))
        self.assertIn('"vibe-app:방문 신청 페이지"', page)

    def test_new_field_types_render(self):
        spec = _spec()
        spec["pages"][0]["fields"] = [
            {"label": "수업", "type": "radio", "required": True, "options": ["기초", "심화"]},
            {"label": "동의", "type": "checkbox", "required": True},
            {"label": "주소", "type": "url"},
            {"label": "시간", "type": "time"},
        ]
        page = ba.build_html(spec)
        self.assertIn('<fieldset class="field"><legend>수업 *</legend>', page)
        self.assertIn('<input type="radio" name="f1" value="기초">', page)
        self.assertIn('<input type="checkbox" id="f2"', page)
        self.assertIn('<input type="url" id="f3"', page)
        self.assertIn('<input type="time" id="f4"', page)

    def test_radio_requires_options(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "구분", "type": "radio", "required": False})
        self.assertTrue(any("options" in e for e in mb_validate(spec)))

    def test_csv_protection_and_bom_in_script(self):
        page = ba.build_html(_spec(save=True))
        self.assertIn('if (/^[=+\\-@]/.test(text)) text', page)
        self.assertIn("\\uFEFF", page)


class BackupTest(unittest.TestCase):
    def test_backup_controls_only_when_saving(self):
        self.assertNotIn('id="make-backup"', ba.build_html(_spec()))
        page = ba.build_html(_spec(save=True))
        for control in ("make-backup", "share-backup", "restore-backup", "restore-file"):
            self.assertIn(f'id="{control}"', page)

    def test_backup_format_and_duplicate_guard_in_script(self):
        page = ba.build_html(_spec(save=True))
        self.assertIn('format: "vibe-app-backup"', page)
        self.assertIn("const seen = new Set(", page)
        self.assertIn('const APP_NAME = "방문 신청 페이지";', page)


def mb_validate(spec):
    from vibe.make_brief import validate_spec
    return validate_spec(spec)


class AdversarialInputTest(unittest.TestCase):
    def test_min_value_cannot_inject_attributes(self):
        spec = _spec()
        spec["pages"][0]["fields"] = [{"label": "수", "type": "number", "min": '1" onfocus="alert(1)'}]
        errors = ba.validate_structure(spec)
        self.assertTrue(any("숫자" in e for e in errors))

    def test_non_string_name_is_rejected_not_crashed(self):
        self.assertTrue(any("'name'" in e for e in ba.validate_structure(_spec(name=123))))

    def test_bad_option_type_rejected(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "구분", "type": "select", "options": [1, 2]})
        self.assertTrue(any("'options'" in e for e in ba.validate_structure(spec)))

    def test_required_must_be_boolean(self):
        spec = _spec()
        spec["pages"][0]["fields"][0]["required"] = "false"
        self.assertTrue(any("'required'" in e for e in ba.validate_structure(spec)))

    def test_pages_not_dicts_rejected(self):
        self.assertTrue(ba.validate_structure(_spec(pages=["문자열"])))


def html_unescape(text):
    import html as _html
    return _html.unescape(text)


if __name__ == "__main__":
    unittest.main()
