import json
import tempfile
import unittest
from pathlib import Path

from vibe import make_brief as mb

EXAMPLE = Path(__file__).resolve().parent.parent / "vibe" / "examples" / "visit_form.json"


def _spec(**overrides):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec.update(overrides)
    return spec


class ValidateSpecTest(unittest.TestCase):
    def test_example_is_valid(self):
        self.assertEqual(mb.validate_spec(json.loads(EXAMPLE.read_text(encoding="utf-8"))), [])

    def test_missing_name_and_goal_reported(self):
        errors = mb.validate_spec(_spec(name="", goal="  "))
        self.assertTrue(any("'name'" in e for e in errors))
        self.assertTrue(any("'goal'" in e for e in errors))

    def test_no_pages_reported(self):
        errors = mb.validate_spec(_spec(pages=[]))
        self.assertTrue(any("'pages'" in e for e in errors))

    def test_unknown_field_type_reported(self):
        spec = _spec()
        spec["pages"][0]["fields"][0]["type"] = "file"
        errors = mb.validate_spec(spec)
        self.assertTrue(any("'type'" in e for e in errors))

    def test_select_without_options_reported(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "구분", "type": "select", "required": False})
        errors = mb.validate_spec(spec)
        self.assertTrue(any("options" in e for e in errors))

    def test_sensitive_field_refused(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "주민등록번호", "type": "text", "required": True})
        errors = mb.validate_spec(spec)
        self.assertTrue(any("민감한 개인정보" in e for e in errors))

    def test_done_criteria_required(self):
        errors = mb.validate_spec(_spec(done=[]))
        self.assertTrue(any("'done'" in e for e in errors))

    def test_all_errors_collected_together(self):
        errors = mb.validate_spec({"name": "", "goal": "", "pages": [], "done": []})
        self.assertGreaterEqual(len(errors), 4)


class BuildBriefTest(unittest.TestCase):
    def test_brief_contains_spec_sections(self):
        brief = mb.build_brief(_spec())
        self.assertIn("# 방문 신청 페이지 만들기", brief)
        self.assertIn("### 신청", brief)
        self.assertIn("연락 이메일 (email, 필수)", brief)
        self.assertIn("방문 목적 (select, 필수, 선택지: 상담 / 견학 / 기타)", brief)
        self.assertIn("- [ ] 방문 날짜를 어제로 고르면 제출되지 않는다.", brief)

    def test_brief_states_single_file_and_korean_rules(self):
        brief = mb.build_brief(_spec())
        self.assertIn("단일 index.html 파일 하나", brief)
        self.assertIn("모든 화면 문구는 한국어로 씁니다.", brief)
        self.assertIn("추측으로 채우지 마세요.", brief)

    def test_brief_without_rules_still_lists_placeholder(self):
        brief = mb.build_brief(_spec(rules=[]))
        self.assertIn("- (추가 규칙 없음)", brief)


class MainTest(unittest.TestCase):
    def test_main_writes_brief_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "brief.md"
            self.assertEqual(mb.main([str(EXAMPLE), "--out", str(out)]), 0)
            self.assertIn("방문 신청 페이지", out.read_text(encoding="utf-8"))

    def test_main_returns_error_for_invalid_spec(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text(json.dumps({"name": "", "goal": "", "pages": [], "done": []}), encoding="utf-8")
            self.assertEqual(mb.main([str(bad)]), 1)


class SensitiveLabelBypassTest(unittest.TestCase):
    def test_spaced_resident_number_refused(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "주민 등록 번호", "type": "text", "required": True})
        self.assertTrue(any("민감한 개인정보" in e for e in mb.validate_spec(spec)))

    def test_uppercase_english_sensitive_word_refused(self):
        spec = _spec()
        spec["pages"][0]["fields"].append({"label": "SSN", "type": "text", "required": True})
        self.assertTrue(any("민감한 개인정보" in e for e in mb.validate_spec(spec)))

    def test_non_dict_spec_rejected(self):
        self.assertEqual(len(mb.validate_spec(["목록"])), 1)


if __name__ == "__main__":
    unittest.main()
