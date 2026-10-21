#!/usr/bin/env python3
"""모든 디자인 프리셋을 같은 기관 데이터로 만들어 비교 갤러리(gallery/)를 씁니다.

사용법:
    python scripts/gallery.py            # gallery/ 폴더에 만들기
    python scripts/gallery.py --out 결과  # 다른 폴더에 만들기

갤러리는 검색 색인에서 제외됩니다 (robots.txt 와 noindex). 실제 홈페이지 출력에는 들어가지 않습니다.
"""

import argparse
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate  # noqa: E402
from validate import validate  # noqa: E402

ROOT = HERE.parent


def card(name, preset):
    return (
        '<article class="card">'
        f'<h2>{html.escape(preset["label"])}</h2>'
        f'<p class="target">대상: {html.escape(preset["target"])}</p>'
        f'<p>{html.escape(preset["character"])}</p>'
        f'<p class="links"><a href="{name}/index.html">홈 보기</a> · <a href="{name}/about.html">기관 소개 보기</a></p>'
        f'<iframe src="{name}/index.html" title="{html.escape(preset["label"])} 미리보기" loading="lazy"></iframe>'
        "</article>"
    )


def gallery_index(presets):
    cards = "\n".join(card(name, preset) for name, preset in presets.items())
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>디자인 프리셋 비교 (샘플)</title>
  <style>
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #F4F4F2; color: #1A1A1A; font-size: 17px; line-height: 1.6; }}
    header {{ padding: 24px 20px; background: #FFFFFF; border-bottom: 1px solid #DDD; }}
    h1 {{ margin: 0 0 6px; font-size: 1.5rem; }}
    .note {{ margin: 0; color: #444; }}
    .grid {{ display: grid; gap: 24px; padding: 24px 20px; grid-template-columns: 1fr; }}
    @media (min-width: 900px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
    .card {{ background: #FFFFFF; border: 1px solid #DDD; border-radius: 8px; padding: 18px; min-width: 0; }}
    .card h2 {{ margin: 0 0 6px; font-size: 1.2rem; }}
    .card p {{ margin: 6px 0; }}
    .target {{ color: #444; font-size: 0.95rem; }}
    .links a {{ min-height: 44px; display: inline-flex; align-items: center; }}
    iframe {{ width: 100%; height: 520px; border: 1px solid #CCC; border-radius: 6px; margin-top: 10px; }}
    a:focus-visible {{ outline: 3px solid #1A1A1A; outline-offset: 2px; }}
  </style>
</head>
<body>
<header>
  <h1>디자인 프리셋 비교 (샘플)</h1>
  <p class="note">모든 프리셋을 같은 가상 기관 데이터로 만들었습니다. 각 화면을 눌러 홈과 기관 소개 페이지를 확인하세요. 360px·768px·1440px 확인은 scripts/check_layout.js 로 합니다.</p>
</header>
<main class="grid">
{cards}
</main>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="디자인 프리셋 비교 갤러리 만들기")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default=None, help="만들 폴더 (기본: <템플릿 폴더>/gallery)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    data, errors = validate(root)
    if errors:
        print("설정을 고쳐 주세요. 갤러리를 만들지 않았습니다:")
        for e in errors:
            print(f"- {e}")
        return 1
    out = Path(args.out or root / "gallery")
    out.mkdir(parents=True, exist_ok=True)
    for name, preset in data["presets"].items():
        variant = dict(data)
        variant["design"] = {"preset": name}
        generate.write_site(root, out / name, generate.build_pages(root, variant))
    (out / "index.html").write_text(gallery_index(data["presets"]), encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    print(f"프리셋 {len(data['presets'])}개 갤러리를 만들었습니다: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
