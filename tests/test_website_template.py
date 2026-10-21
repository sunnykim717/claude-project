import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "website-template"
sys.path.insert(0, str(ROOT / "scripts"))

import generate  # noqa: E402
import validate  # noqa: E402



class _Copy:
    """테스트마다 템플릿을 임시 폴더에 복사해서 고쳐 봅니다."""

    def __enter__(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp) / "site"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("dist"))
        return self.root

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp)


def _edit(root, rel, change):
    path = root / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class ValidateTest(unittest.TestCase):
    def test_template_is_valid(self):
        _, errors = validate.validate(ROOT)
        self.assertEqual(errors, [])

    def test_bad_color_and_font_reported_together(self):
        with _Copy() as root:
            _edit(root, "config/theme.json", lambda d: d.update(primaryColor="blue", font="Comic"))
            _, errors = validate.validate(root)
            self.assertTrue(any("primaryColor" in e for e in errors))
            self.assertTrue(any("font" in e for e in errors))

    def test_unknown_navigation_page_rejected(self):
        with _Copy() as root:
            _edit(root, "config/navigation.json", lambda d: d.append({"label": "소식", "path": "/news"}))
            _, errors = validate.validate(root)
            self.assertTrue(any("/news" in e for e in errors))

    def test_javascript_link_rejected(self):
        with _Copy() as root:
            _edit(root, "content/home.json", lambda d: d["hero"].update(buttonLink="javascript:alert(1)"))
            _, errors = validate.validate(root)
            self.assertTrue(any("buttonLink" in e for e in errors))

    def test_bad_date_and_email_rejected(self):
        with _Copy() as root:
            _edit(root, "content/projects.json", lambda d: d["items"][0].update(date="2026/01/15"))
            _edit(root, "content/contact.json", lambda d: d.update(email="not-an-email"))
            _, errors = validate.validate(root)
            self.assertTrue(any("date" in e for e in errors))
            self.assertTrue(any("이메일" in e for e in errors))

    def test_missing_file_reported(self):
        with _Copy() as root:
            (root / "content" / "about.json").unlink()
            _, errors = validate.validate(root)
            self.assertTrue(any("about.json" in e for e in errors))


class GenerateTest(unittest.TestCase):
    def test_builds_all_pages_with_navigation(self):
        with _Copy() as root:
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            for name in ("index.html", "about.html", "projects.html", "contact.html"):
                self.assertTrue((out / name).exists(), name)
            about = (out / "about.html").read_text(encoding="utf-8")
            self.assertIn('href="projects.html"', about)
            self.assertIn('aria-current="page"', about)
            self.assertIn("<title>기관 소개 | 새로운 기관</title>", about)

    def test_hero_button_points_to_page_file(self):
        with _Copy() as root:
            out = root / "dist"
            generate.main(["--root", str(root), "--out", str(out)])
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="button" href="about.html"', index)

    def test_user_text_is_escaped(self):
        with _Copy() as root:
            _edit(root, "content/about.json", lambda d: d.update(body="<script>alert(1)</script>"))
            out = root / "dist"
            generate.main(["--root", str(root), "--out", str(out)])
            about = (out / "about.html").read_text(encoding="utf-8")
            self.assertNotIn("<script>alert(1)</script>", about)
            self.assertIn("&lt;script&gt;", about)

    def test_invalid_config_writes_nothing(self):
        with _Copy() as root:
            _edit(root, "config/theme.json", lambda d: d.update(radius=99))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 1)
            self.assertFalse(out.exists())

    def test_public_images_are_copied(self):
        with _Copy() as root:
            (root / "public" / "images" / "logo.png").write_bytes(b"png")
            out = root / "dist"
            generate.main(["--root", str(root), "--out", str(out)])
            self.assertTrue((out / "public" / "images" / "logo.png").exists())

    def test_theme_values_become_css_variables(self):
        with _Copy() as root:
            _edit(root, "config/theme.json", lambda d: d.update(primaryColor="#0F766E", font="serif", radius=14))
            out = root / "dist"
            generate.main(["--root", str(root), "--out", str(out)])
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("--primary: #0F766E;", index)
            self.assertIn("--font: Georgia, serif;", index)
            self.assertIn("--radius: 14px;", index)


class SiteToolTest(unittest.TestCase):
    """모든 명령은 임시 폴더를 대상으로 합니다. 저장소의 원본 템플릿은 건드리지 않습니다."""

    def setUp(self):
        import site_tool
        self.tool = site_tool
        self.tmp = tempfile.mkdtemp()
        self.target = Path(self.tmp) / "new"
        self.tool.main(["new", str(self.target)])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, *args):
        return self.tool.main(["--root", str(self.target), *args])

    def test_new_site_applies_name_and_design(self):
        dest = Path(self.tmp) / "named"
        self.assertEqual(self.tool.main(["new", str(dest), "--name", "민수의 작업실", "--design", "warm-orange"]), 0)
        site = json.loads((dest / "config" / "site.json").read_text(encoding="utf-8"))
        theme = json.loads((dest / "config" / "theme.json").read_text(encoding="utf-8"))
        self.assertEqual(site["name"], "민수의 작업실")
        self.assertEqual(theme["primaryColor"], "#C2410C")
        self.assertEqual(theme["font"], "serif")

    def test_new_refuses_existing_folder_and_unknown_design(self):
        self.assertEqual(self.tool.main(["new", str(self.target)]), 1)
        other = Path(self.tmp) / "other"
        self.assertEqual(self.tool.main(["new", str(other), "--design", "없는-디자인"]), 1)
        self.assertFalse(other.exists())

    def test_set_nested_and_list_values_then_build(self):
        self.assertEqual(self._run("set", "home.hero.title", "새 제목"), 0)
        self.assertEqual(self._run("set", "projects.items.0.title", "새 사업"), 0)
        self.assertEqual(self._run("build"), 0)
        self.assertIn("새 제목", (self.target / "dist" / "index.html").read_text(encoding="utf-8"))
        self.assertIn("새 사업", (self.target / "dist" / "projects.html").read_text(encoding="utf-8"))

    def test_set_rejects_bad_value_and_keeps_old_file(self):
        path = self.target / "config" / "theme.json"
        before = path.read_text(encoding="utf-8")
        self.assertEqual(self._run("set", "theme.primaryColor", '"blue"'), 1)
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_set_unknown_path_is_reported(self):
        self.assertEqual(self._run("set", "site.없는항목.x", "1"), 1)
        self.assertEqual(self._run("set", "nosuchfile.key", "1"), 1)

    def test_repository_template_is_not_changed_by_tests(self):
        before = (ROOT / "content" / "home.json").read_text(encoding="utf-8")
        self._run("set", "home.hero.title", "테스트용 제목")
        self.assertEqual((ROOT / "content" / "home.json").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
