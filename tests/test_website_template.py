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
            _edit(root, "config/navigation.json", lambda d: d.append({"label": "블로그", "path": "/blog"}))
            _, errors = validate.validate(root)
            self.assertTrue(any("/blog" in e for e in errors))

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
            for name in ("index.html", "about.html", "projects.html", "support.html", "transparency.html",
                         "news.html", "volunteer.html", "contact.html", "privacy.html"):
                self.assertTrue((out / name).exists(), name)
            about = (out / "about.html").read_text(encoding="utf-8")
            self.assertIn('href="projects.html"', about)
            self.assertIn('aria-current="page"', about)
            self.assertIn("<title>기관 소개 | ○○ 비영리 단체</title>", about)

    def test_hero_button_points_to_page_file(self):
        with _Copy() as root:
            out = root / "dist"
            generate.main(["--root", str(root), "--out", str(out)])
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="button" href="support.html"', index)

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

    def test_page_photo_is_shown_at_top_of_page(self):
        with _Copy() as root:
            (root / "public" / "images" / "about.jpg").write_bytes(b"jpg")
            _edit(root, "content/about.json", lambda d: d.update(image="/images/about.jpg", imageAlt="사무실 사진"))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            about = (out / "about.html").read_text(encoding="utf-8")
            self.assertIn('<figure class="page-photo"><img src="public/images/about.jpg" alt="사무실 사진">', about)
            self.assertLess(about.index("page-photo"), about.index('<section class="block">'))
            self.assertNotIn('class="page-photo"', (out / "news.html").read_text(encoding="utf-8"))

    def test_gallery_shows_every_photo_at_page_end(self):
        with _Copy() as root:
            for name in ("g1.jpg", "g2.jpg"):
                (root / "public" / "images" / name).write_bytes(b"jpg")
            _edit(root, "content/projects.json", lambda d: d.update(gallery=[
                {"image": "/images/g1.jpg", "alt": "첫 사진"}, {"image": "/images/g2.jpg", "alt": "둘째 사진"}]))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            page = (out / "projects.html").read_text(encoding="utf-8")
            self.assertEqual(page.count('<figure><img src="public/images/g'), 2)
            self.assertIn('alt="둘째 사진" loading="lazy"', page)
            self.assertLess(page.index('<div class="gallery">'), page.index("</main>"))
            self.assertNotIn('class="gallery"', (out / "about.html").read_text(encoding="utf-8"))

    def test_gallery_limit_and_bad_items_are_rejected(self):
        with _Copy() as root:
            many = [{"image": "/images/x.jpg"}] * (validate.GALLERY_MAX + 1)
            _edit(root, "content/about.json", lambda d: d.update(gallery=many))
            _, errors = validate.validate(root)
            self.assertTrue(any("12장" in e for e in errors))
        with _Copy() as root:
            _edit(root, "content/about.json", lambda d: d.update(gallery=[{"image": "/images/없음.jpg"}]))
            _, errors = validate.validate(root)
            self.assertTrue(any("about.json 1번 사진" in e for e in errors))

    def test_new_pages_are_built_and_listed_in_schema(self):
        with _Copy() as root:
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            for name in ("greetings", "history", "events", "stories", "library", "faq", "location"):
                page = (out / f"{name}.html").read_text(encoding="utf-8")
                self.assertIn("<h2>", page, name)
            self.assertIn("<h2>연도별 기록</h2>", (out / "history.html").read_text(encoding="utf-8"))
            self.assertNotIn("<h2>연도별 기록</h2>", (out / "greetings.html").read_text(encoding="utf-8"))

    def test_home_sections_change_order_and_reject_unknown(self):
        with _Copy() as root:
            _edit(root, "content/home.json", lambda d: d.update(sections=["news", "intro"]))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertLess(index.index("<h2>소식</h2>"), index.index("<h2>소개</h2>"))
            self.assertNotIn("<h2>주요사업</h2>", index)
        with _Copy() as root:
            _edit(root, "content/home.json", lambda d: d.update(sections=["intro", "video"]))
            _, errors = validate.validate(root)
            self.assertTrue(any("sections" in e for e in errors))

    def test_board_post_body_is_expandable_and_escaped(self):
        with _Copy() as root:
            _edit(root, "content/board.json", lambda d: d["items"][0].update(body="<b>줄 1</b>\n줄 2"))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            board = (out / "board.html").read_text(encoding="utf-8")
            self.assertIn("<details><summary>자세히 보기</summary>", board)
            self.assertIn("&lt;b&gt;줄 1&lt;/b&gt;", board)
            self.assertNotIn("<b>줄 1</b>", board)

    def test_board_post_body_must_be_text(self):
        with _Copy() as root:
            _edit(root, "content/board.json", lambda d: d["items"][0].update(body=["목록"]))
            _, errors = validate.validate(root)
            self.assertTrue(any("board.json" in e and "body" in e for e in errors))

    def test_custom_page_is_built_and_can_be_linked(self):
        with _Copy() as root:
            _edit(root, "content/custom-pages.json", lambda d: d.extend([
                {"slug": "open-house", "title": "열린 행사", "body": "가족 행사입니다.",
                 "itemsTitle": "일정", "items": [{"title": "토요일 오후", "date": "2026-11-07", "summary": "", "url": ""}]}]))
            _edit(root, "config/navigation.json", lambda d: d.append({"label": "열린 행사", "path": "/open-house"}))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            page = (out / "open-house.html").read_text(encoding="utf-8")
            self.assertIn("<h2>열린 행사</h2>", page)
            self.assertIn('href="open-house.html"', (out / "about.html").read_text(encoding="utf-8"))

    def test_custom_page_slug_rules(self):
        for slug in ("About", "1st", "news", "a", "with space"):
            with _Copy() as root:
                _edit(root, "content/custom-pages.json", lambda d, slug=slug: d.append({"slug": slug, "title": "t", "body": ""}))
                _, errors = validate.validate(root)
                self.assertTrue(any("slug" in e or "이미 있습니다" in e for e in errors), slug)

    def test_scheduled_item_appears_only_on_its_day(self):
        with _Copy() as root:
            _edit(root, "content/news.json", lambda d: d["items"].append(
                {"title": "예약 소식", "date": "2026-11-01", "summary": "", "url": "", "publish": "2026-11-01"}))
            data, errors = validate.validate(root)
            self.assertEqual(errors, [])
            before = generate.build_pages(root, data, today="2026-10-31")
            on_day = generate.build_pages(root, data, today="2026-11-01")
            self.assertNotIn("예약 소식", before["news.html"])
            self.assertIn("예약 소식", on_day["news.html"])

    def test_bad_publish_date_is_rejected(self):
        with _Copy() as root:
            _edit(root, "content/news.json", lambda d: d["items"][0].update(publish="2026/11/01"))
            _, errors = validate.validate(root)
            self.assertTrue(any("publish" in e for e in errors))

    def test_generic_page_needs_a_title(self):
        with _Copy() as root:
            _edit(root, "content/faq.json", lambda d: d.update(title=""))
            _, errors = validate.validate(root)
            self.assertTrue(any("faq.json" in e and "title" in e for e in errors))

    def test_page_photo_missing_file_is_rejected(self):
        with _Copy() as root:
            _edit(root, "content/news.json", lambda d: d.update(image="/images/missing.jpg"))
            _, errors = validate.validate(root)
            self.assertTrue(any("news.json" in e and "public" in e for e in errors))

    def test_page_photo_bad_path_is_rejected(self):
        with _Copy() as root:
            _edit(root, "content/privacy.json", lambda d: d.update(image="../secret.jpg"))
            _, errors = validate.validate(root)
            self.assertTrue(any("privacy.json" in e and "image" in e for e in errors))

    def test_logo_and_background_photo_are_used(self):
        with _Copy() as root:
            (root / "public" / "images" / "logo.png").write_bytes(b"png")
            (root / "public" / "images" / "bg.jpg").write_bytes(b"jpg")
            _edit(root, "config/site.json", lambda d: d.update(logo="/images/logo.png"))
            _edit(root, "config/theme.json", lambda d: d.update(backgroundImage="/images/bg.jpg"))
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('<img class="logo" src="public/images/logo.png" alt="">', index)
            self.assertIn('background-image: url("public/images/bg.jpg")', index)

    def test_custom_css_is_added_last_and_unsafe_css_is_rejected(self):
        with _Copy() as root:
            (root / "config" / "custom.css").write_text(".hero h1 { letter-spacing: 0.1em; }", encoding="utf-8")
            out = root / "dist"
            self.assertEqual(generate.main(["--root", str(root), "--out", str(out)]), 0)
            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn(".hero h1 { letter-spacing: 0.1em; }", index)
            self.assertLess(index.index(".site-header {"), index.index("letter-spacing: 0.1em"))
            (root / "config" / "custom.css").write_text("body { background: url(http://x.test/a.png); }", encoding="utf-8")
            _, errors = validate.validate(root)
            self.assertTrue(any("custom.css" in e and "url(" in e for e in errors))

    def test_logo_path_must_be_a_real_image(self):
        with _Copy() as root:
            _edit(root, "config/site.json", lambda d: d.update(logo="/images/없는.png"))
            _edit(root, "config/theme.json", lambda d: d.update(backgroundImage="../bg.jpg"))
            _, errors = validate.validate(root)
            self.assertTrue(any("site.json" in e and "logo" in e for e in errors))
            self.assertTrue(any("theme.json" in e and "backgroundImage" in e for e in errors))

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

    def test_set_accepts_unquoted_multi_word_value(self):
        self.assertEqual(self._run("set", "site.name", "○○", "복지", "재단"), 0)
        site = json.loads((self.target / "config" / "site.json").read_text(encoding="utf-8"))
        self.assertEqual(site["name"], "○○ 복지 재단")

    def test_new_accepts_unquoted_multi_word_name(self):
        dest = Path(self.tmp) / "multi"
        self.assertEqual(self.tool.main(["new", str(dest), "--name", "희망", "나눔", "복지재단"]), 0)
        site = json.loads((dest / "config" / "site.json").read_text(encoding="utf-8"))
        self.assertEqual(site["name"], "희망 나눔 복지재단")

    def test_add_and_remove_menu(self):
        self.assertEqual(self._run("add-menu", "오시는", "길", "/location"), 0)
        nav = json.loads((self.target / "config" / "navigation.json").read_text(encoding="utf-8"))
        self.assertEqual(nav[-1], {"label": "오시는 길", "path": "/location"})
        self.assertEqual(self._run("remove-menu", str(len(nav))), 0)
        self.assertEqual(len(json.loads((self.target / "config" / "navigation.json").read_text(encoding="utf-8"))), len(nav) - 1)

    def test_add_menu_rejects_unknown_page_and_bad_number(self):
        self.assertEqual(self._run("add-menu", "이상한", "/nope"), 1)
        self.assertEqual(self._run("remove-menu", "99"), 1)

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


class DesignAndSchemaTest(unittest.TestCase):
    """디자인 프리셋과 설정 목록(schema.json)이 서로 맞는지 확인합니다."""

    def test_choices_are_wide_enough(self):
        schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
        designs = json.loads((ROOT / "config" / "designs.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(designs), 24)
        self.assertGreaterEqual(len(schema["fonts"]), 9)
        self.assertGreaterEqual(len(schema["spacings"]), 5)
        self.assertGreaterEqual(len(schema["layouts"]), 6)
        self.assertEqual(schema["menus"], ["row", "center", "buttons", "stack"])
        for name, design in designs.items():
            self.assertIn(design["menu"], schema["menus"], name)
            self.assertIn(design["font"], schema["fonts"], name)
            self.assertIn(design["layout"], schema["layouts"], name)
            self.assertIn(design["spacing"], schema["spacings"], name)

    def test_menu_must_be_a_known_style(self):
        with _Copy() as root:
            _edit(root, "config/theme.json", lambda d: d.update(menu="sidebar"))
            _, errors = validate.validate(root)
            self.assertTrue(any("menu" in e for e in errors))

    @staticmethod
    def _luminance(hex_color):
        n = int(hex_color[1:], 16)
        channels = []
        for shift in (16, 8, 0):
            c = ((n >> shift) & 255) / 255
            channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def _contrast(self, a, b):
        hi, lo = sorted([self._luminance(a), self._luminance(b)], reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    def test_every_design_is_readable_and_uses_known_values(self):
        schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
        designs = json.loads((ROOT / "config" / "designs.json").read_text(encoding="utf-8"))
        for name, d in designs.items():
            with self.subTest(design=name):
                self.assertGreaterEqual(self._contrast(d["textColor"], d["backgroundColor"]), 4.5)
                self.assertGreaterEqual(self._contrast(d["backgroundColor"], d["primaryColor"]), 4.5)
                self.assertIn(d["font"], schema["fonts"])
                self.assertIn(d["spacing"], schema["spacings"])
                self.assertIn(d["layout"], schema["layouts"])

    def test_schema_pages_match_files_and_navigation(self):
        schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
        nav = json.loads((ROOT / "config" / "navigation.json").read_text(encoding="utf-8"))
        for entry in nav:
            self.assertIn(entry["path"], schema["pages"])
        for rel in schema["files"].values():
            self.assertTrue((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
