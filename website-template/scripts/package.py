#!/usr/bin/env python3
"""검증을 통과한 설정으로 홈페이지를 만들고, 글꼴 파일과 라이선스까지 담은 zip 을 만듭니다 (표준 라이브러리만 씁니다).

사용법:
    python scripts/package.py                 # site.zip 만들기
    python scripts/package.py --out 결과.zip

zip 안: 홈페이지 파일 전부, fonts/ (쓰는 글꼴 파일), LICENSES/ (글꼴 라이선스 파일).
검증에 실패하면 zip 을 만들지 않고 기존 파일도 건드리지 않습니다.
"""

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate  # noqa: E402
from validate import validate  # noqa: E402

ROOT = HERE.parent


def package(root, out_zip):
    data, errors = validate(root)
    if errors:
        return False, errors
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        generate.write_site(root, site, generate.build_pages(root, data))
        out_zip = Path(out_zip)
        partial = out_zip.with_suffix(".partial")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(site.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(site).as_posix())
            licenses = root / "fonts" / "licenses"
            if licenses.is_dir():
                for path in sorted(licenses.glob("*.txt")):
                    archive.write(path, "LICENSES/" + path.name)
        partial.replace(out_zip)
    return True, []


def main(argv=None):
    parser = argparse.ArgumentParser(description="홈페이지와 글꼴을 담은 zip 만들기")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="site.zip")
    args = parser.parse_args(argv)
    ok, errors = package(Path(args.root), args.out)
    if not ok:
        print("설정을 고쳐 주세요. zip 을 만들지 않았습니다:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"zip 을 만들었습니다: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
