#!/usr/bin/env python3
"""설정과 콘텐츠로 홈페이지 파일을 만들어 dist/ 폴더에 씁니다. Node 도 AI 도 필요 없습니다.

사용법:
    python scripts/generate.py            # 검사 후 dist/ 에 만들기
    python scripts/generate.py --out 결과  # 다른 폴더에 만들기

만들어지는 파일: index.html, about.html, projects.html, contact.html 과 public/ 의 그림
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate import PAGE_FILES, validate  # noqa: E402

ROOT = HERE.parent
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
FONT_STACK = SCHEMA["fonts"]
SPACING_PX = SCHEMA["spacings"]
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def esc(value):
    return html.escape(str(value or ""), quote=True)


def fill(template, values):
    """{{이름}} 자리에 값을 넣습니다. 값은 이미 안전하게 바뀐 HTML 이어야 합니다. 빠진 값이 있으면 오류입니다."""
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise KeyError(f"템플릿에 없는 자리표시자입니다: {key}")
        return values[key]
    return PLACEHOLDER.sub(replace, template)


def read_part(root, rel):
    return (Path(root) / rel).read_text(encoding="utf-8")


def theme_css(theme):
    """theme.json 의 값을 CSS 변수로 바꿉니다."""
    return (
        ":root {"
        f" --primary: {theme['primaryColor']};"
        f" --bg: {theme['backgroundColor']};"
        f" --text: {theme['textColor']};"
        f" --font: {FONT_STACK[theme['font']]};"
        f" --radius: {theme['radius']}px;"
        f" --gap: {SPACING_PX[theme['spacing']]}px;"
        " --max: 760px;"
        " }"
    )


def link_for(value):
    """설정의 주소를 파일 주소로 바꿉니다. https 주소는 그대로 둡니다."""
    if value.startswith(("https://", "http://")):
        return value
    return PAGE_FILES[value]


def header_html(root, site, nav, current_file):
    links = []
    for entry in nav:
        target = PAGE_FILES[entry["path"]]
        current = ' aria-current="page"' if target == current_file else ""
        links.append(f'<li><a href="{esc(target)}"{current}>{esc(entry["label"])}</a></li>')
    return fill(read_part(root, "src/components/Header.html"), {
        "brand": esc(site["name"]),
        "links": "".join(links),
    })


def hero_html(root, home):
    hero = home["hero"]
    image = ""
    if hero.get("image"):
        src = "public/" + str(hero["image"]).lstrip("/")
        image = f'<img class="hero-photo" src="{esc(src)}" alt="{esc(hero.get("imageAlt"))}">'

    button = ""
    if hero.get("buttonText") and hero.get("buttonLink"):
        button = f'<a class="button" href="{esc(link_for(hero["buttonLink"]))}">{esc(hero["buttonText"])}</a>'
    return fill(read_part(root, "src/components/Hero.html"), {
        "image": image,
        "title": esc(hero["title"]),
        "subtitle": esc(hero.get("subtitle")),
        "button": button,
    })


def photo_html(content):
    """사진 칸이 있을 때만 페이지 맨 위에 사진을 넣습니다."""
    if not content.get("image"):
        return ""
    src = "public/" + str(content["image"]).lstrip("/")
    return f'<figure class="page-photo"><img src="{esc(src)}" alt="{esc(content.get("imageAlt"))}"></figure>'


def footer_html(root, site, contact):
    lines = []
    if contact.get("email"):
        lines.append(f'<p><a href="{esc("mailto:" + contact["email"])}">{esc(contact["email"])}</a></p>')
    social_names = (("github", "GitHub"), ("instagram", "Instagram"), ("youtube", "YouTube"))
    links = [f'<li><a href="{esc(contact["social"][key])}">{name}</a></li>'
             for key, name in social_names if (contact.get("social") or {}).get(key)]
    if links:
        lines.append(f'<ul class="links">{"".join(links)}</ul>')
    lines.append('<p><a href="privacy.html">개인정보 처리방침</a></p>')
    return fill(read_part(root, "src/components/Footer.html"), {
        "name": esc(site["name"]),
        "contact": "".join(lines),
    })


def items_html(items, layout):
    """사업 목록. 카드형 배치에서는 격자로 감쌉니다."""
    body = project_articles(items)
    if layout == "card" and body:
        return f'<div class="cards">{body}</div>'
    return body


def block(title, body_html):
    return f'<section class="block"><h2>{esc(title)}</h2>{body_html}</section>'


def project_articles(items):
    ordered = sorted(items, key=lambda i: i.get("date") or "", reverse=True)
    out = []
    for item in ordered:
        title = esc(item["title"])
        if item.get("url"):
            title = f'<a href="{esc(item["url"])}">{title}</a>'
        date = f'<time datetime="{esc(item["date"])}">{esc(item["date"])}</time>' if item.get("date") else ""
        summary = f'<p>{esc(item["summary"])}</p>' if item.get("summary") else ""
        out.append(f"<article><h3>{title}</h3>{date}{summary}</article>")
    return "".join(out)


def build_pages(root, data):
    """페이지 이름과 전체 HTML 을 돌려줍니다."""
    site, nav, theme = data["site"], data["nav"], data["theme"]
    style = theme_css(theme) + "\n" + read_part(root, "src/styles/site.css")
    pages = {}

    def page(file_name, title, main_html, description, photo=""):
        full_title = site["name"] if file_name == "index.html" else f"{title} | {site['name']}"
        pages[file_name] = fill(read_part(root, "src/pages/page.html"), {
            "lang": esc(site.get("language", "ko")),
            "title": esc(full_title),
            "description": esc(site.get("description")),
            "style": style,
            "header": header_html(root, site, nav, file_name),
            "main": photo + main_html,
            "footer": footer_html(root, site, data["contact"]),
            "layout": esc(theme["layout"]),
            "menu": esc(theme["menu"]),
        })

    home = data["home"]
    preview = items_html(data["projects"].get("items", [])[:3], theme["layout"])
    home_main = (
        hero_html(root, home)
        + block("소개", f'<p class="pre">{esc(home.get("intro"))}</p>')
        + (block(data["projects"]["title"], preview) if preview else "")
    )
    page("index.html", site["name"], home_main, site.get("description", ""))

    page("about.html", data["about"]["title"],
         block(data["about"]["title"], f'<p class="pre">{esc(data["about"]["body"])}</p>'),
         data["about"]["body"], photo_html(data["about"]))
    page("projects.html", data["projects"]["title"],
         block(data["projects"]["title"], items_html(data["projects"].get("items", []), theme["layout"])),
         data["projects"]["title"], photo_html(data["projects"]))
    contact = data["contact"]
    support = data["support"]
    ways = project_articles(support.get("ways", []))
    support_main = block(support["title"], f'<p class="pre">{esc(support["body"])}</p>')
    if ways:
        support_main += block("후원 방법", ways)
    if support.get("notice"):
        support_main += block("안내", f'<p class="pre">{esc(support["notice"])}</p>')
    page("support.html", support["title"], support_main, support["body"], photo_html(support))
    news = data["news"]
    page("news.html", news["title"],
         block(news["title"], project_articles(news.get("items", []))), news["title"], photo_html(news))
    transparency = data["transparency"]
    page("transparency.html", transparency["title"],
         block(transparency["title"], f'<p class="pre">{esc(transparency["body"])}</p>')
         + block("사업 · 재무 자료", project_articles(transparency.get("reports", [])))
         + block("사업비 구성", f'<p class="pre">{esc(transparency["costs"])}</p>')
         + block("외부 확인", f'<p class="pre">{esc(transparency["disclosure"])}</p>'),
         transparency["body"], photo_html(transparency))
    volunteer = data["volunteer"]
    page("volunteer.html", volunteer["title"],
         block(volunteer["title"], f'<p class="pre">{esc(volunteer["body"])}</p>')
         + block("활동 종류", project_articles(volunteer.get("positions", [])))
         + block("신청 방법", f'<p class="pre">{esc(volunteer["apply"])}</p>'),
         volunteer["body"], photo_html(volunteer))
    privacy = data["privacy"]
    page("privacy.html", privacy["title"],
         block(privacy["title"], f'<p class="pre">{esc(privacy["body"])}</p>')
         + block("처리 항목", project_articles(privacy.get("items", []))),
         privacy["body"], photo_html(privacy))
    page("contact.html", contact["title"],
         block(contact["title"], f'<p class="pre">{esc(contact["body"])}</p>'),
         contact["body"], photo_html(contact))
    return pages


def write_site(root, out_dir, pages):
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name, content in pages.items():
        (out / name).write_text(content, encoding="utf-8")
    public = Path(root) / "public"
    if public.exists():
        shutil.copytree(public, out / "public", ignore=shutil.ignore_patterns(".gitkeep"))
    return sorted(pages)


def main(argv=None):
    parser = argparse.ArgumentParser(description="설정으로 홈페이지 파일 만들기")
    parser.add_argument("--root", default=str(ROOT), help="템플릿 폴더 (기본: 이 스크립트의 상위 폴더)")
    parser.add_argument("--out", default=None, help="만들 폴더 (기본: <템플릿 폴더>/dist)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    data, errors = validate(root)
    if errors:
        print("설정을 고쳐 주세요. 아직 아무 파일도 만들지 않았습니다:")
        for e in errors:
            print(f"- {e}")
        return 1
    out = args.out or (root / "dist")
    names = write_site(root, out, build_pages(root, data))
    print(f"홈페이지 파일을 만들었습니다 ({out}): {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
