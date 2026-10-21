#!/usr/bin/env python3
"""AI 와 계정 없이 홈페이지를 만들고 고치는 기본 도구입니다.

사용법 (--root 로 홈페이지 폴더를 고를 수 있습니다. 기본값은 이 파일이 있는 폴더):
    python scripts/site_tool.py designs                          # 디자인 목록
    python scripts/site_tool.py new ../내기관 --name "민수의 작업실" --design warm-orange
    python scripts/site_tool.py set site.name "새 이름"            # 설정 바꾸기 (검사 후 저장)
    python scripts/site_tool.py set home.hero.title "더 나은 내일"
    python scripts/site_tool.py set projects.items.0.title "새 사업"
    python scripts/site_tool.py check                            # 검사
    python scripts/site_tool.py build                            # dist/ 에 페이지 만들기

'set' 의 첫 단어는 파일을 가리킵니다: site, theme, nav, home, about, projects, support, transparency, volunteer, privacy, news, contact
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate  # noqa: E402
from validate import validate  # noqa: E402

ROOT = HERE.parent
FILE_FOR = {
    "site": "config/site.json", "nav": "config/navigation.json", "theme": "config/theme.json",
    "home": "content/home.json", "about": "content/about.json",
    "projects": "content/projects.json", "support": "content/support.json",
    "transparency": "content/transparency.json", "volunteer": "content/volunteer.json",
    "privacy": "content/privacy.json", "news": "content/news.json", "contact": "content/contact.json",
}
THEME_KEYS = ("primaryColor", "backgroundColor", "textColor", "font", "radius", "spacing", "layout")
IGNORE = shutil.ignore_patterns("dist", "__pycache__", ".git")


def load_designs(root):
    return json.loads((Path(root) / "config" / "designs.json").read_text(encoding="utf-8"))


def cmd_designs(args):
    for key, design in load_designs(args.root).items():
        print(f"{key:14} {design['label']}  (강조색 {design['primaryColor']}, 글꼴 {design['font']}, 여백 {design['spacing']})")
    return 0


def _finish(root, what):
    _, errors = validate(root)
    if errors:
        print("설정을 고쳐 주세요:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"검사 통과: {what}")
    return 0


def cmd_new(args):
    target = Path(args.folder).resolve()
    if target.exists():
        print(f"이미 있는 폴더에는 만들지 않습니다: {target}")
        return 1
    shutil.copytree(args.root, target, ignore=IGNORE)
    site_path = target / FILE_FOR["site"]
    site = json.loads(site_path.read_text(encoding="utf-8"))
    if args.name:
        site["name"] = args.name
    site_path.write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.design:
        designs = load_designs(target)
        if args.design not in designs:
            shutil.rmtree(target)
            print(f"디자인은 {', '.join(designs)} 중 하나여야 합니다.")
            return 1
        preset = {k: designs[args.design][k] for k in THEME_KEYS}
        (target / FILE_FOR["theme"]).write_text(json.dumps(preset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _finish(target, f"새 홈페이지 폴더를 만들었습니다: {target}\n다음: cd 해당폴더 && python scripts/site_tool.py build")


def _walk(data, keys):
    """경로를 따라 값을 찾습니다. 목록은 번호(0부터)로 고릅니다."""
    node = data
    for key in keys[:-1]:
        node = node[int(key)] if isinstance(node, list) else node[key]
    last = keys[-1]
    return node, (int(last) if isinstance(node, list) else last)


def cmd_set(args):
    root = Path(args.root)
    parts = args.path.split(".")
    if len(parts) < 2 or parts[0] not in FILE_FOR:
        print(f"경로는 파일이름.항목 형식이어야 합니다. 파일: {', '.join(FILE_FOR)}")
        return 1
    path = root / FILE_FOR[parts[0]]
    original = path.read_text(encoding="utf-8")
    text = " ".join(args.value)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = text
    data = json.loads(original)
    try:
        node, last = _walk(data, parts[1:])
        node[last] = value
    except (KeyError, IndexError, ValueError, TypeError):
        print(f"바꿀 항목을 찾지 못했습니다: {args.path}")
        return 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _, errors = validate(root)
    if errors:
        path.write_text(original, encoding="utf-8")  # 틀린 값은 저장하지 않고 되돌립니다
        print("저장하지 않았습니다. 다음을 고쳐 주세요:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"{args.path} 을(를) 바꾸고 저장했습니다: {value!r}")
    return 0


def cmd_check(args):
    return _finish(args.root, "설정과 콘텐츠가 맞습니다.")


def cmd_build(args):
    return generate.main(["--root", str(args.root)] + (["--out", args.out] if args.out else []))


def build_parser():
    parser = argparse.ArgumentParser(prog="site_tool", description="AI 없이 홈페이지 만들기")
    parser.add_argument("--root", default=str(ROOT), help="홈페이지 폴더 (기본: 이 파일이 있는 폴더)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("designs", help="디자인 목록 보기").set_defaults(func=cmd_designs)
    p = sub.add_parser("new", help="새 홈페이지 폴더 만들기")
    p.add_argument("folder")
    p.add_argument("--name", help="기관 이름")
    p.add_argument("--design", help="디자인 이름 (designs 명령으로 확인)")
    p.set_defaults(func=cmd_new)
    p = sub.add_parser("set", help="설정이나 콘텐츠 값 바꾸기 (검사 후 저장)")
    p.add_argument("path", help="예: site.name, theme.primaryColor, home.hero.title, projects.items.0.title")
    p.add_argument("value", nargs="+", help="새 값. 따옴표 없이 여러 단어를 써도 됩니다")
    p.set_defaults(func=cmd_set)
    sub.add_parser("check", help="설정 검사").set_defaults(func=cmd_check)
    p = sub.add_parser("build", help="dist/ 에 페이지 만들기")
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_build)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
