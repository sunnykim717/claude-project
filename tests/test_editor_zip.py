"""편집기의 zip 만들기(zip.js)가 Python 의 zipfile 로 바르게 열리는지 확인합니다. Node 가 없으면 건너뜁니다."""
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ZIP_JS = Path(__file__).resolve().parent.parent / "website-template" / "editor" / "zip.js"


def _has_node():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


@unittest.skipUnless(_has_node(), "Node 가 없어서 건너뜁니다")
class ZipWriterTest(unittest.TestCase):
    def _make(self, entries):
        script = (
            "const z = require(process.argv[1]);"
            "const entries = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));"
            "const bytes = z.buildZip(entries, new Date(2026, 9, 21, 10, 30, 0));"
            "process.stdout.write(Buffer.from(bytes).toString('base64'));"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(entries, f, ensure_ascii=False)
            path = f.name
        out = subprocess.run(["node", "-e", script, str(ZIP_JS), path], capture_output=True, text=True, check=True)
        Path(path).unlink()
        import base64
        return base64.b64decode(out.stdout)

    def test_zip_opens_and_keeps_folders_and_text(self):
        entries = [
            {"name": "config/site.json", "text": '{"name": "민수의 작업실"}\n'},
            {"name": "content/home.json", "text": "{\"intro\": \"안녕하세요 \\u0026 <b>\"}"},
            {"name": "public/images/.gitkeep", "text": ""},
            {"name": "dist/index.html", "text": "<!doctype html>\n" * 500},
        ]
        data = self._make(entries)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "site.zip"
            path.write_bytes(data)
            with zipfile.ZipFile(path) as zf:
                self.assertIsNone(zf.testzip())
                self.assertEqual(sorted(zf.namelist()), sorted(e["name"] for e in entries))
                for e in entries:
                    self.assertEqual(zf.read(e["name"]).decode("utf-8"), e["text"], e["name"])

    def test_empty_archive_is_valid(self):
        data = self._make([])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "empty.zip"
            path.write_bytes(data)
            with zipfile.ZipFile(path) as zf:
                self.assertEqual(zf.namelist(), [])


if __name__ == "__main__":
    unittest.main()
