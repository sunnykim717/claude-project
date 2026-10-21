#!/usr/bin/env python3
"""홈페이지(index.html)를 데이터 파일(JSON)로부터 자동 생성합니다.

사용법:
    python update_homepage.py
    python update_homepage.py --data data/site.json --output index.html
"""

import argparse
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))

DEFAULT_DATA = Path("data/site.json")
DEFAULT_OUTPUT = Path("index.html")

STYLE = """
  :root { color-scheme: light dark; --accent: #3b82f6; }
  body { margin: 0; font-family: system-ui, sans-serif; line-height: 1.6; }
  main { max-width: 760px; margin: 0 auto; padding: 16px; }
  header h1 { margin-bottom: 0; }
  .subtitle { color: #64748b; margin-top: 4px; }
  article { border-left: 4px solid var(--accent); padding: 4px 12px; margin: 20px 0; }
  article h2 { margin: 0; font-size: 1.15rem; }
  article h2 a { color: inherit; }
  .date { color: #64748b; font-size: 0.9rem; }
  footer { color: #64748b; font-size: 0.85rem; margin: 40px 0 16px; }
"""


def load_site(path):
    """데이터 파일을 읽고 필수 항목을 검사합니다."""
    with Path(path).open(encoding="utf-8") as f:
        site = json.load(f)

    if not site.get("title"):
        raise ValueError(f"{path}: 'title' 항목이 필요합니다.")
    if not isinstance(site.get("items", []), list):
        raise ValueError(f"{path}: 'items' 는 목록이어야 합니다.")
    for item in site.get("items", []):
        if not item.get("title"):
            raise ValueError(f"{path}: 모든 item 에 'title' 이 필요합니다.")
    return site


def render_item(item):
    """소식 항목 하나를 HTML 로 변환합니다."""
    title = html.escape(item["title"])
    if item.get("url"):
        title = f'<a href="{html.escape(item["url"], quote=True)}">{title}</a>'

    parts = [f"<h2>{title}</h2>"]
    if item.get("date"):
        parts.append(f'<p class="date">{html.escape(item["date"])}</p>')
    if item.get("summary"):
        parts.append(f"<p>{html.escape(item['summary'])}</p>")
    return "<article>\n    " + "\n    ".join(parts) + "\n  </article>"


def render_page(site, now):
    """사이트 데이터를 전체 HTML 문서로 변환합니다."""
    title = html.escape(site["title"])
    subtitle = html.escape(site.get("subtitle", ""))
    # 최신 소식이 위로 오도록 날짜 기준 내림차순 정렬 (날짜가 없으면 맨 뒤)
    items = sorted(site.get("items", []), key=lambda i: i.get("date", ""), reverse=True)
    articles = "\n  ".join(render_item(item) for item in items)
    updated = now.strftime("%Y-%m-%d %H:%M (KST)")

    return f"""<!doctype html>
<html lang="{html.escape(site.get('lang', 'ko'))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
<main>
  <header>
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
  </header>
  {articles}
  <footer>마지막 자동 업데이트: {updated}</footer>
</main>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="홈페이지 자동 업데이트")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="입력 JSON 경로")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="출력 HTML 경로")
    args = parser.parse_args(argv)

    site = load_site(args.data)
    page = render_page(site, datetime.now(KST))
    args.output.write_text(page, encoding="utf-8")
    print(f"생성 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
