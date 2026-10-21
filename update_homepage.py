#!/usr/bin/env python3
"""홈페이지(index.html)를 데이터 파일(JSON)로부터 자동 생성합니다.

사용법:
    python update_homepage.py
    python update_homepage.py --data data/site.json --output index.html
"""

import argparse
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))

DEFAULT_DATA = Path("data/site.json")
DEFAULT_OUTPUT = Path("index.html")

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
THEME_COLOR_KEYS = ("accent", "text", "bg")
ALLOWED_FONTS = {"system-ui, sans-serif", "Georgia, serif", "ui-monospace, monospace"}
SPACING_PX = {"compact": 12, "normal": 24, "airy": 40}

# 섹션 목록이 없을 때 쓰는 기본 순서 (기존 동작과 같습니다)
DEFAULT_SECTIONS = ["about", "items", "contact"]
ALLOWED_SECTIONS = ("about", "items", "cta", "social", "contact")
SOCIAL_LABELS = (("github", "GitHub"), ("instagram", "Instagram"), ("youtube", "YouTube"))

STYLE = """
  :root { color-scheme: light dark; --accent: #3b82f6; --radius: 8px; --gap: 16px; }
  body { margin: 0; font-family: system-ui, sans-serif; line-height: 1.6; }
  main { max-width: var(--max, 760px); margin: 0 auto; padding: var(--gap); }
  header h1 { margin-bottom: 0; }
  .subtitle { color: #64748b; margin-top: 4px; }
  section { margin: 32px 0 0; }
  section h2 { font-size: 1.1rem; color: var(--accent); margin: 0 0 8px; }
  .pre { white-space: pre-line; }
  article { border-left: 4px solid var(--accent); padding: 4px 12px; margin: 20px 0; border-radius: 0 var(--radius) var(--radius) 0; }
  article h2 { margin: 0; font-size: 1.15rem; }
  article h2 a { color: inherit; }
  .date { color: #64748b; font-size: 0.9rem; }
  .btn { display: inline-block; padding: 10px 18px; border-radius: var(--radius); background: var(--accent); color: var(--bg, #ffffff); text-decoration: none; font-weight: 700; }
  .links { list-style: none; display: flex; gap: 14px; flex-wrap: wrap; padding: 0; margin: 0; }
  .links a { color: var(--accent); }
  footer { color: #64748b; font-size: 0.85rem; margin: 40px 0 16px; }
"""


def is_http_url(value):
    """http(s) 주소만 허용해서 javascript: 같은 주소를 막습니다."""
    return value.startswith(("https://", "http://"))


def validate_theme(theme, path):
    """빌더에서 고른 색상, 글꼴, 모서리, 여백을 검사합니다. 허용되지 않은 값은 거부합니다."""
    for key, value in theme.items():
        if key in THEME_COLOR_KEYS:
            if not HEX_COLOR_PATTERN.match(str(value)):
                raise ValueError(f"{path}: theme.{key} 는 #RRGGBB 형식이어야 합니다 ({value}).")
        elif key == "font":
            if value not in ALLOWED_FONTS:
                raise ValueError(f"{path}: theme.font 은 허용된 글꼴 중 하나여야 합니다 ({value}).")
        elif key == "radius":
            if not isinstance(value, int) or not 0 <= value <= 32:
                raise ValueError(f"{path}: theme.radius 는 0~32 사이의 정수여야 합니다 ({value}).")
        elif key == "maxWidth":
            if not isinstance(value, int) or not 560 <= value <= 960:
                raise ValueError(f"{path}: theme.maxWidth 는 560~960 사이의 정수여야 합니다 ({value}).")
        elif key == "spacing":
            if value not in SPACING_PX:
                raise ValueError(f"{path}: theme.spacing 은 compact, normal, airy 중 하나여야 합니다 ({value}).")
        else:
            raise ValueError(f"{path}: theme 에 알 수 없는 항목이 있습니다 ({key}).")


def validate_social(social, path):
    """SNS 링크를 검사합니다. 주소는 http(s), 이메일은 이메일 형식이어야 합니다."""
    for key, value in social.items():
        if not value:
            continue
        if key == "email":
            if not EMAIL_PATTERN.match(value):
                raise ValueError(f"{path}: social.email 형식이 올바르지 않습니다 ({value}).")
        elif key in dict(SOCIAL_LABELS):
            if not is_http_url(value):
                raise ValueError(f"{path}: social.{key} 는 http(s):// 로 시작해야 합니다.")
        else:
            raise ValueError(f"{path}: social 에 알 수 없는 항목이 있습니다 ({key}).")


def load_site(path):
    """데이터 파일을 읽고 필수 항목을 검사합니다."""
    with Path(path).open(encoding="utf-8") as f:
        site = json.load(f)

    if not site.get("title"):
        raise ValueError(f"{path}: 'title' 항목이 필요합니다.")
    if not isinstance(site.get("items", []), list):
        raise ValueError(f"{path}: 'items' 는 목록이어야 합니다.")
    for key in ("about", "contact"):
        if not isinstance(site.get(key, ""), str):
            raise ValueError(f"{path}: '{key}' 는 문자열이어야 합니다.")
    if site.get("theme"):
        validate_theme(site["theme"], path)
    if site.get("social"):
        validate_social(site["social"], path)
    if site.get("cta") and site["cta"].get("url") and not is_http_url(site["cta"]["url"]):
        raise ValueError(f"{path}: cta.url 은 http(s):// 로 시작해야 합니다.")
    if "sections" in site:
        sections = site["sections"]
        if not isinstance(sections, list) or len(set(sections)) != len(sections):
            raise ValueError(f"{path}: 'sections' 는 중복 없는 목록이어야 합니다.")
        unknown = [s for s in sections if s not in ALLOWED_SECTIONS]
        if unknown:
            raise ValueError(f"{path}: 알 수 없는 섹션이 있습니다 -> {', '.join(map(str, unknown))}")

    for item in site.get("items", []):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: 각 item 은 {{ }} 로 감싼 설정 묶음이어야 합니다.")
        if not item.get("title"):
            raise ValueError(f"{path}: 모든 item 에 'title' 이 필요합니다.")
        if item.get("url") and not is_http_url(item["url"]):
            raise ValueError(f"{path}: '{item['title']}' 의 url 은 http(s):// 로 시작해야 합니다.")
        if item.get("date") and not DATE_PATTERN.match(item["date"]):
            raise ValueError(f"{path}: '{item['title']}' 의 date 는 YYYY-MM-DD 형식이어야 합니다.")
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


def render_theme(theme):
    """빌더에서 고른 색상, 글꼴, 모서리, 여백을 CSS 로 바꿉니다. 없으면 빈 문자열입니다."""
    if not theme:
        return ""
    values = {
        "accent": "#3b82f6", "text": "#0f172a", "bg": "#ffffff",
        "font": "system-ui, sans-serif", "radius": 8, "spacing": "normal", **theme,
    }
    return (
        f"\n  :root {{ --accent: {values['accent']}; --radius: {values['radius']}px; "
        f"--gap: {SPACING_PX[values['spacing']]}px; }}"
        f"\n  body {{ background: {values['bg']}; color: {values['text']}; font-family: {values['font']}; }}"
    )


def render_text_section(title, text):
    """소개나 연락처처럼 글 하나로 된 섹션을 HTML 로 변환합니다."""
    text = text.strip()
    if not text:
        return ""
    return f'<section>\n    <h2>{title}</h2>\n    <p class="pre">{html.escape(text)}</p>\n  </section>'


def render_cta(cta):
    """버튼 섹션을 HTML 로 변환합니다. 링크가 없으면 만들지 않습니다."""
    if not cta or not cta.get("url"):
        return ""
    label = html.escape(cta.get("label") or "문의하기")
    return f'<section class="cta">\n    <a class="btn" href="{html.escape(cta["url"], quote=True)}">{label}</a>\n  </section>'


def render_social(social):
    """SNS 링크 섹션을 HTML 로 변환합니다. 입력된 항목만 보입니다."""
    social = social or {}
    links = [
        f'<li><a href="{html.escape(social[key], quote=True)}">{name}</a></li>'
        for key, name in SOCIAL_LABELS if social.get(key)
    ]
    if social.get("email"):
        links.append(f'<li><a href="{html.escape("mailto:" + social["email"], quote=True)}">이메일</a></li>')
    if not links:
        return ""
    return f'<section>\n    <h2>SNS</h2>\n    <ul class="links">{"".join(links)}</ul>\n  </section>'


def render_sections(site):
    """섹션을 순서대로 HTML 로 변환합니다. 'sections' 가 없으면 기본 순서를 씁니다."""
    order = site.get("sections", DEFAULT_SECTIONS)
    # 최신 소식이 위로 오도록 날짜 기준 내림차순 정렬 (날짜가 없으면 맨 뒤)
    items = sorted(site.get("items", []), key=lambda i: i.get("date", ""), reverse=True)

    parts = []
    for name in order:
        if name == "about":
            parts.append(render_text_section("소개", site.get("about", "")))
        elif name == "items":
            if items:
                parts.append("\n  ".join(render_item(item) for item in items))
        elif name == "cta":
            parts.append(render_cta(site.get("cta")))
        elif name == "social":
            parts.append(render_social(site.get("social")))
        elif name == "contact":
            parts.append(render_text_section("연락처", site.get("contact", "")))
    return "\n  ".join(part for part in parts if part)


def render_page(site, now):
    """사이트 데이터를 전체 HTML 문서로 변환합니다."""
    title = html.escape(site["title"])
    subtitle = html.escape(site.get("subtitle", ""))
    sections = render_sections(site)
    max_width = site.get("theme", {}).get("maxWidth", 760)
    updated = now.strftime("%Y-%m-%d %H:%M (KST)")

    return f"""<!doctype html>
<html lang="{html.escape(site.get('lang', 'ko'))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}{render_theme(site.get("theme"))}
  main {{ max-width: {int(max_width)}px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
  </header>
  {sections}
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
