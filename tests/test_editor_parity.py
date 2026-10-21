"""브라우저 편집기 엔진(engine.js)이 Python 생성기와 같은 결과를 내는지 확인합니다. Node 가 없으면 건너뜁니다."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "website-template"
ENGINE = ROOT / "editor" / "engine.js"
sys.path.insert(0, str(ROOT / "scripts"))

import generate  # noqa: E402
import validate  # noqa: E402

TEXT_FILES = [
    "config/site.json", "config/navigation.json", "config/theme.json",
    "content/home.json", "content/about.json", "content/projects.json", "content/support.json",
    "content/transparency.json", "content/volunteer.json", "content/privacy.json",
    "content/news.json", "content/contact.json",
    "src/components/Header.html", "src/components/Hero.html", "src/components/Footer.html",
    "src/pages/page.html", "src/styles/site.css",
]


def _read_files(root):
    return {rel: (Path(root) / rel).read_text(encoding="utf-8") for rel in TEXT_FILES}


def _node(files):
    script = (
        "const e = require(process.argv[1]);"
        "const input = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));"
        "process.stdout.write(JSON.stringify(e.build(input)));"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
        json.dump(files, f, ensure_ascii=False)
        path = f.name
    try:
        result = subprocess.run(["node", "-e", script, str(ENGINE), path], capture_output=True, text=True, check=True)
    finally:
        Path(path).unlink()
    return json.loads(result.stdout)


def _has_node():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


@unittest.skipUnless(_has_node(), "Node 가 없어서 건너뜁니다")
class EngineParityTest(unittest.TestCase):
    def _compare(self, root):
        files = _read_files(root)
        js = _node(files)
        self.assertTrue(js["ok"], js.get("errors"))
        out = Path(tempfile.mkdtemp())
        try:
            data, errors = validate.validate(root)
            self.assertEqual(errors, [])
            py_pages = generate.build_pages(root, data)
            self.assertEqual(sorted(js["pages"]), sorted(py_pages))
            for name, html in py_pages.items():
                self.assertEqual(js["pages"][name], html, f"{name} 가 Python 결과와 다릅니다")
        finally:
            shutil.rmtree(out)

    def test_template_pages_match_python(self):
        self._compare(ROOT)

    def test_changed_content_matches_python(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            copy = tmp / "site"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("dist", "__pycache__", "editor"))
            projects = json.loads((copy / "content" / "projects.json").read_text(encoding="utf-8"))
            projects["items"].append({"title": "A & B <b>", "date": "2026-03-01", "summary": "요약 'x'", "url": "https://example.com/?a=1&b=2"})
            projects["items"].append({"title": "날짜 없음", "summary": "", "url": ""})
            (copy / "content" / "projects.json").write_text(json.dumps(projects, ensure_ascii=False), encoding="utf-8")
            theme = json.loads((copy / "config" / "theme.json").read_text(encoding="utf-8"))
            theme.update(font="serif", radius=0, spacing="airy", primaryColor="#C2410C")
            (copy / "config" / "theme.json").write_text(json.dumps(theme), encoding="utf-8")
            self._compare(copy)
        finally:
            shutil.rmtree(tmp)

    def test_bad_input_gives_same_errors_and_no_pages(self):
        files = _read_files(ROOT)
        files["config/theme.json"] = json.dumps({**json.loads(files["config/theme.json"]), "radius": 99})
        js = _node(files)
        self.assertFalse(js["ok"])
        self.assertEqual(js["pages"], {})
        self.assertTrue(any("radius" in e for e in js["errors"]))


class EditorBundleTest(unittest.TestCase):
    def test_editor_page_is_up_to_date(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import bundle_editor
        built = bundle_editor.build(ROOT)
        current = (ROOT / "editor" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(current, built, "editor/index.html 이 오래되었습니다. python website-template/scripts/bundle_editor.py 를 실행하세요.")


if __name__ == "__main__":
    unittest.main()
