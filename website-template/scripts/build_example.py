#!/usr/bin/env python3
"""예시 기관을 템플릿 위에 겹쳐 따로 만듭니다. 템플릿 원본은 바꾸지 않습니다.

사용법:
    python scripts/build_example.py community-welfare          # 임시 폴더에 만들기
    python scripts/build_example.py youth-center --out 결과
    python scripts/build_example.py blank                       # 빈 설정은 오류를 알려 줍니다
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate  # noqa: E402
from validate import validate  # noqa: E402

ROOT = HERE.parent
SKIP = {"dist", "gallery", "examples", "__pycache__"}


def build(example, out=None):
    """(성공 여부, 오류 목록, 출력 폴더) 를 돌려줍니다."""
    source = ROOT / "examples" / example
    if not source.is_dir():
        return False, [f"예시 폴더가 없습니다: {example}"], None
    work = Path(tempfile.mkdtemp()) / "site"
    shutil.copytree(ROOT, work, ignore=lambda folder, names: [n for n in names if n in SKIP])
    for item in source.rglob("*"):
        if item.is_file():
            target = work / item.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
    data, errors = validate(work)
    if errors:
        return False, errors, None
    target = Path(out) if out else work.parent / "dist"
    generate.write_site(work, target, generate.build_pages(work, data))
    return True, [], target


def main(argv=None):
    parser = argparse.ArgumentParser(description="예시 기관 만들기")
    parser.add_argument("example", help="community-welfare, youth-center, blank 중 하나")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    ok, errors, target = build(args.example, args.out)
    if not ok:
        print(f"{args.example} 설정을 고쳐 주세요. 아직 아무 파일도 만들지 않았습니다:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"{args.example} 홈페이지를 만들었습니다: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
