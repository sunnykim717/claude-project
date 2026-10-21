#!/usr/bin/env python3
"""편집기 파일(editor/index.html)을 만듭니다. 템플릿 파일, 엔진, 화면 코드, 디자인 목록을 한 파일에 담습니다.

사용법:
    python scripts/bundle_editor.py          # editor/index.html 다시 만들기
    python scripts/bundle_editor.py --check  # 지금 파일이 최신인지만 확인
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EDITOR = ROOT / "editor"
TEXT_FILES = [
    "config/site.json", "config/navigation.json", "config/theme.json",
    "content/home.json", "content/about.json", "content/projects.json", "content/support.json",
    "content/transparency.json", "content/volunteer.json", "content/privacy.json",
    "content/news.json", "content/contact.json",
    "src/components/Header.html", "src/components/Hero.html", "src/components/Footer.html",
    "src/pages/page.html", "src/styles/site.css",
]


# 프로젝트 zip 에만 들어가는 파일 (배포와 도구를 저장소에서 바로 쓰기 위해)
PROJECT_EXTRA_FILES = [
    "scripts/validate.py", "scripts/generate.py", "scripts/site_tool.py", "config/designs.json",
    ".github/workflows/deploy.yml", "README.md", ".gitignore",
]


def _script_safe(text):
    """<script> 안에 넣어도 태그가 깨지지 않도록 바꿉니다."""
    return text.replace("</script", "<\\/script")


def _json_safe(value):
    return json.dumps(value, ensure_ascii=False, indent=2).replace("</", "<\\/")


def build(root=ROOT):
    root = Path(root)
    editor = root / "editor"
    files = {rel: (root / rel).read_text(encoding="utf-8") for rel in TEXT_FILES}
    designs = json.loads((root / "config" / "designs.json").read_text(encoding="utf-8"))
    extra = {rel: (root / rel).read_text(encoding="utf-8") for rel in PROJECT_EXTRA_FILES}
    extra["public/images/.gitkeep"] = ""
    shell = (editor / "app.html").read_text(encoding="utf-8")
    return (
        shell.replace("__ENGINE__", _script_safe((editor / "engine.js").read_text(encoding="utf-8")))
        .replace("__APP__", _script_safe((editor / "app.js").read_text(encoding="utf-8")))
        .replace("__DEFAULT_FILES__", _json_safe(files))
        .replace("__DESIGNS__", _json_safe(designs))
        .replace("__ZIP__", _script_safe((editor / "zip.js").read_text(encoding="utf-8")))
        .replace("__PROJECT_EXTRA__", _json_safe(extra))
    )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = build()
    target = EDITOR / "index.html"
    if "--check" in argv:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != text:
            print("편집기 파일이 오래되었습니다. python scripts/bundle_editor.py 로 다시 만드세요.")
            return 1
        print("편집기 파일이 최신입니다.")
        return 0
    target.write_text(text, encoding="utf-8")
    print(f"편집기 파일을 만들었습니다: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
