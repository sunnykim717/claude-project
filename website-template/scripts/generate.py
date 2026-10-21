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
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate import ROUTES, validate  # noqa: E402

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


def background_css(theme):
    """배경 사진이 있으면 배경색 위에 얇은 막을 씌워 글자가 읽히게 합니다."""
    if not theme.get("backgroundImage"):
        return ""
    src = "public/" + str(theme["backgroundImage"]).lstrip("/")
    return (
        f'body {{ background-image: url("{src}"); background-size: cover; background-attachment: fixed; }}\n'
        'body::before { content: ""; position: fixed; inset: 0; z-index: -1; background: var(--bg); opacity: 0.88; }'
    )


def custom_css(root):
    path = Path(root) / "config" / "custom.css"
    return path.read_text(encoding="utf-8") if path.exists() else ""


WIDTHS = SCHEMA["content_widths"]
HERO_CLASS = {"split": "hero-split", "photo": "hero-photo-variant", "info": "hero-info"}
DEFAULT_SECTIONS = ["hero", "quickLinks", "about", "programs", "news", "stories", "impact", "participation", "contact"]


def design_choice(data):
    """design.json 과 presets.json 을 합쳐 이번에 쓸 디자인 값을 돌려줍니다. 프리셋을 고르지 않았으면 None."""
    design = data.get("design") or {}
    presets = data.get("presets") or {}
    name = design.get("preset")
    if not name or name not in presets:
        return None
    preset = presets[name]
    return {
        "name": name,
        "tokens": preset["tokens"],
        "hero": design.get("hero") or preset["defaultHero"],
        "width": WIDTHS[design.get("contentWidth") or "comfortable"],
    }


def theme_css(theme, choice=None):
    """theme.json 의 값을 CSS 변수로 바꿉니다. 디자인 프리셋을 고르면 색, 글꼴, 모서리, 여백은 프리셋을 따릅니다."""
    t = choice["tokens"] if choice else {}
    primary = t.get("primary", theme["primaryColor"])
    bg = t.get("bg", theme["backgroundColor"])
    text = t.get("text", theme["textColor"])
    font = FONT_STACK[t.get("font", theme["font"])]
    radius = t.get("radius", theme["radius"])
    gap = SPACING_PX[t.get("spacing", theme["spacing"])]
    width = choice["width"] if choice else 760
    return (
        ":root {"
        f" --primary: {primary}; --bg: {bg}; --text: {text}; --font: {font};"
        f" --radius: {radius}px; --gap: {gap}px; --max: {width}px;"
        f" --surface: {t.get('surface', '#FFFFFF')}; --muted: {t.get('muted', text)}; --accent: {t.get('accent', primary)};"
        " }"
    )


def link_for(value):
    """설정의 주소를 파일 주소로 바꿉니다. https 주소는 그대로 둡니다."""
    if value.startswith(("https://", "http://")):
        return value
    return ROUTES[value]


def header_html(root, site, nav, current_file):
    links = []
    for entry in nav:
        target = ROUTES[entry["path"]]
        current = ' aria-current="page"' if target == current_file else ""
        links.append(f'<li><a href="{esc(target)}"{current}>{esc(entry["label"])}</a></li>')
    brand = esc(site["name"])
    if site.get("logo"):
        brand = f'<img class="logo" src="{esc("public/" + str(site["logo"]).lstrip("/"))}" alt="">' + brand
    return fill(read_part(root, "src/components/Header.html"), {
        "brand": brand,
        "links": "".join(links),
    })


def hero_html(root, home, variant="split"):
    hero = home["hero"]
    image = ""
    if hero.get("image"):
        src = "public/" + str(hero["image"]).lstrip("/")
        image = f'<img class="hero-photo" src="{esc(src)}" alt="{esc(hero.get("imageAlt"))}">'

    button = ""
    if hero.get("buttonText") and hero.get("buttonLink"):
        button = f'<a class="button" href="{esc(link_for(hero["buttonLink"]))}">{esc(hero["buttonText"])}</a>'
    return fill(read_part(root, "src/components/Hero.html"), {
        "variant": HERO_CLASS[variant],
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


def gallery_html(content):
    """여러 장 넣은 사진을 페이지 끝에 바둑판으로 보입니다."""
    items = content.get("gallery") or []
    if not items:
        return ""
    figures = "".join(
        f'<figure><img src="{esc("public/" + str(item["image"]).lstrip("/"))}" alt="{esc(item.get("alt"))}" loading="lazy"></figure>'
        for item in items
    )
    return f'<div class="gallery">{figures}</div>'


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
    if site.get("sample"):
        lines.append('<p class="sample-note">이 홈페이지의 기관 정보와 글은 가상의 샘플입니다.</p>')
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
        body = f'<details><summary>자세히 보기</summary><p class="pre">{esc(item["body"])}</p></details>' if item.get("body") else ""
        out.append(f"<article><h3>{title}</h3>{date}{summary}{body}</article>")
    return "".join(out)


KST = timezone(timedelta(hours=9))


def today_kst():
    return datetime.now(KST).strftime("%Y-%m-%d")


def drop_unpublished(value, today):
    """publish 날짜가 오늘보다 뒤인 항목은 아직 보이지 않게 뺍니다. 날짜가 없는 항목은 바로 보입니다."""
    if isinstance(value, list):
        return [drop_unpublished(v, today) for v in value
                if not (isinstance(v, dict) and isinstance(v.get("publish"), str) and v["publish"] > today)]
    if isinstance(value, dict):
        return {k: drop_unpublished(v, today) for k, v in value.items()}
    return value


ADMIN_INTRO = "방문자가 올린 글을 확인해서 승인하거나 지우는 화면입니다. 로그인한 관리자만 글을 바꿀 수 있습니다."


def supabase_settings(data):
    cfg = data.get("supabase") or {}
    return str(cfg.get("url") or ""), str(cfg.get("anonKey") or "")


def read_script(root, rel):
    return read_part(root, rel).strip()


def admin_main(root, url, key):
    return fill(read_part(root, "src/components/Admin.html"), {
        "url": esc(url), "key": esc(key), "intro": esc(ADMIN_INTRO),
        "script": read_script(root, "src/admin/admin.js"),
    })


def board_live_html(root, url, key):
    return fill(read_part(root, "src/components/BoardLive.html"), {
        "url": esc(url), "key": esc(key), "script": read_script(root, "src/admin/board.js"),
    })


def generic_body(content):
    """제목, 본문, 목록으로 된 간단한 페이지의 내용입니다."""
    items = content.get("items") or []
    body = block(content["title"], f'<p class="pre">{esc(content.get("body"))}</p>')
    if items:
        body += block(content.get("itemsTitle") or "목록", project_articles(items))
    return body


def news_list(items):
    ordered = sorted(items, key=lambda i: i.get("date") or "", reverse=True)
    rows = []
    for item in ordered:
        title = esc(item["title"])
        if item.get("url"):
            title = f'<a href="{esc(item["url"])}">{title}</a>'
        when = f'<time datetime="{esc(item["date"])}">{esc(item["date"])}</time>' if item.get("date") else ""
        rows.append(f"<li>{when}<span>{title}</span></li>")
    return '<ul class="news-list">' + "".join(rows) + "</ul>"


def section_quick(nav):
    links = [entry for entry in nav if entry["path"] != "/"][:6]
    if not links:
        return ""
    items = "".join(
        f'<li><a class="quick-link" href="{esc(ROUTES[entry["path"]])}">{esc(entry["label"])}</a></li>' for entry in links
    )
    return block("바로 가기", f'<ul class="quick-grid">{items}</ul>')


def section_about(home):
    intro = str(home.get("intro") or "").strip()
    if not intro:
        return ""
    return block("기관 소개", f'<p class="pre">{esc(intro)}</p><p><a class="more" href="about.html">기관 소개 자세히 보기</a></p>')


def section_programs(projects):
    items = projects.get("items") or []
    if not items:
        return ""
    return block(projects["title"], f'<div class="programs">{project_articles(items[:3])}</div>')


def section_news(news):
    items = news.get("items") or []
    if not items:
        return ""
    return block(news["title"], news_list(items[:3]))


def section_stories(stories):
    items = stories.get("items") or []
    if not items:
        return ""
    body = f'<div class="story-lead">{project_articles(items[:1])}</div>'
    if items[1:]:
        body += f'<div class="story-list">{project_articles(items[1:])}</div>'
    return block(stories["title"], body)


def section_impact(impact):
    items = impact.get("items") or []
    if not items:
        return ""
    cells = "".join(
        f'<div><dt>{esc(i["value"])}</dt><dd>{esc(i["label"])}'
        + (f'<br>{esc(i.get("description"))}' if i.get("description") else "")
        + "</dd></div>"
        for i in items
    )
    note = f'<p class="impact-note">{esc(impact.get("period"))}</p>' if impact.get("period") else ""
    return block(impact["title"], f'<dl class="impact">{cells}</dl>{note}')


def section_participation(support, volunteer):
    ways = support.get("ways") or []
    positions = volunteer.get("positions") or []
    if not ways and not positions:
        return ""
    body = project_articles(ways) if ways else ""
    body += (
        '<p class="participation-actions">'
        '<a class="button" href="support.html">후원 안내 보기</a>'
        '<a class="button secondary" href="volunteer.html">자원봉사 안내 보기</a>'
        "</p>"
    )
    return block("참여 방법", body)


def section_contact(contact):
    rows = []
    if contact.get("phone"):
        rows.append(("전화", esc(contact["phone"])))
    if contact.get("email"):
        rows.append(("이메일", f'<a href="{esc("mailto:" + contact["email"])}">{esc(contact["email"])}</a>'))
    if contact.get("address"):
        rows.append(("주소", esc(contact["address"])))
    if contact.get("hours"):
        rows.append(("운영시간", esc(contact["hours"])))
    body = f'<p class="pre">{esc(contact.get("body"))}</p>' if contact.get("body") else ""
    if rows:
        body += '<ul class="contact-list">' + "".join(f"<li><strong>{label}</strong> {value}</li>" for label, value in rows) + "</ul>"
    if not body:
        return ""
    return block(contact["title"], body)


def home_main(root, data, choice):
    """설정의 순서대로 홈 칸을 이어 붙입니다. 데이터가 없는 칸은 빠집니다."""
    home = data["home"]
    parts = {
        "hero": hero_html(root, home, choice["hero"] if choice else "split"),
        "quickLinks": section_quick(data["nav"]),
        "about": section_about(home),
        "programs": section_programs(data["projects"]),
        "news": section_news(data["news"]),
        "stories": section_stories(data["stories"]),
        "impact": section_impact(data["impact"]),
        "participation": section_participation(data["support"], data["volunteer"]),
        "contact": section_contact(data["contact"]),
    }
    order = (data.get("homepage") or {}).get("sections") or DEFAULT_SECTIONS
    return "".join(parts[name] for name in order)


def not_found_main():
    return block("페이지를 찾을 수 없습니다", '<p class="pre">주소가 바뀌었거나 없는 페이지입니다. 메뉴나 홈으로 이동해 주세요.</p>'
                 '<p><a class="button" href="index.html">홈으로 돌아가기</a></p>')


def head_html(site, file_name, full_title, noindex=False):
    """페이지 머리 정보: 색인 제외, 공유용 제목과 설명, 대표 주소(canonical). 주소가 없으면 대표 주소는 넣지 않습니다."""
    lines = []
    if noindex:
        lines.append('<meta name="robots" content="noindex">')
    lines.append(f'<meta property="og:title" content="{esc(full_title)}">')
    lines.append(f'<meta property="og:description" content="{esc(site.get("description"))}">')
    lines.append('<meta property="og:type" content="website">')
    base = str(site.get("url") or "").rstrip("/")
    if base:
        href = base + "/" + ("" if file_name == "index.html" else file_name)
        lines.append(f'<link rel="canonical" href="{esc(href)}">')
        lines.append(f'<meta property="og:url" content="{esc(href)}">')
    return "\n  ".join(lines)


def robots_txt(site):
    base = str(site.get("url") or "").rstrip("/")
    lines = ["User-agent: *", "Disallow: /admin.html", "Disallow: /gallery/"]
    if base:
        lines.append(f"Sitemap: {base}/sitemap.xml")
    return "\n".join(lines) + "\n"


def sitemap_xml(site, page_files):
    base = str(site.get("url") or "").rstrip("/")
    urls = [f"  <url><loc>{esc(base + '/' + ('' if name == 'index.html' else name))}</loc></url>"
            for name in page_files if name not in ("admin.html", "404.html")]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")


def build_pages(root, data, today=None):
    """페이지 이름과 전체 HTML 을 돌려줍니다."""
    data = drop_unpublished(data, today or today_kst())
    site, nav, theme = data["site"], data["nav"], data["theme"]
    choice = design_choice(data)
    style = "\n".join([theme_css(theme, choice), background_css(theme), read_part(root, "src/styles/site.css"), custom_css(root)])
    pages = {}

    def page(file_name, title, main_html, description, content=None, noindex=False):
        if file_name != "index.html":
            # 하위 페이지의 첫 제목은 페이지 제목(h1)입니다. 홈은 첫 화면 제목이 h1 입니다.
            main_html = main_html.replace("<h2>", "<h1>", 1).replace("</h2>", "</h1>", 1)
        top = photo_html(content) if content else ""
        bottom = gallery_html(content) if content else ""
        full_title = site["name"] if file_name == "index.html" else f"{title} | {site['name']}"
        pages[file_name] = fill(read_part(root, "src/pages/page.html"), {
            "lang": esc(site.get("language", "ko")),
            "title": esc(full_title),
            "description": esc(site.get("description")),
            "head": head_html(site, file_name, full_title, noindex),
            "script": read_part(root, "src/scripts/reading.js").strip(),
            "style": style,
            "header": header_html(root, site, nav, file_name),
            "main": top + main_html + bottom,
            "footer": footer_html(root, site, data["contact"]),
            "layout": esc(theme["layout"]),
            "menu": esc(theme["menu"]),
        })

    page("index.html", site["name"], home_main(root, data, choice), site.get("description", ""))

    page("about.html", data["about"]["title"],
         block(data["about"]["title"], f'<p class="pre">{esc(data["about"]["body"])}</p>'),
         data["about"]["body"], data["about"])
    page("projects.html", data["projects"]["title"],
         block(data["projects"]["title"], items_html(data["projects"].get("items", []), theme["layout"])),
         data["projects"]["title"], data["projects"])
    contact = data["contact"]
    support = data["support"]
    ways = project_articles(support.get("ways", []))
    support_main = block(support["title"], f'<p class="pre">{esc(support["body"])}</p>')
    if ways:
        support_main += block("후원 방법", ways)
    if support.get("notice"):
        support_main += block("안내", f'<p class="pre">{esc(support["notice"])}</p>')
    page("support.html", support["title"], support_main, support["body"], support)
    news = data["news"]
    page("news.html", news["title"],
         block(news["title"], project_articles(news.get("items", []))), news["title"], news)
    transparency = data["transparency"]
    page("transparency.html", transparency["title"],
         block(transparency["title"], f'<p class="pre">{esc(transparency["body"])}</p>')
         + block("사업 · 재무 자료", project_articles(transparency.get("reports", [])))
         + block("사업비 구성", f'<p class="pre">{esc(transparency["costs"])}</p>')
         + block("외부 확인", f'<p class="pre">{esc(transparency["disclosure"])}</p>'),
         transparency["body"], transparency)
    volunteer = data["volunteer"]
    page("volunteer.html", volunteer["title"],
         block(volunteer["title"], f'<p class="pre">{esc(volunteer["body"])}</p>')
         + block("활동 종류", project_articles(volunteer.get("positions", [])))
         + block("신청 방법", f'<p class="pre">{esc(volunteer["apply"])}</p>'),
         volunteer["body"], volunteer)
    privacy = data["privacy"]
    page("privacy.html", privacy["title"],
         block(privacy["title"], f'<p class="pre">{esc(privacy["body"])}</p>')
         + block("처리 항목", project_articles(privacy.get("items", []))),
         privacy["body"], privacy)
    page("contact.html", contact["title"],
         block(contact["title"], f'<p class="pre">{esc(contact["body"])}</p>'),
         contact["body"], contact)
    url, key = supabase_settings(data)
    connected = bool(url and key)
    for name in SCHEMA["generic_pages"]:
        content = data[name]
        body = generic_body(content)
        if name == "board" and connected:
            body += board_live_html(root, url, key)
        page(f"{name}.html", content["title"], body, content["body"], content)
    for content in data["custom_pages"]:
        page(f"{content['slug']}.html", content["title"], generic_body(content), content.get("body"), content)
    page("admin.html", "관리자", admin_main(root, url, key), ADMIN_INTRO, noindex=True)
    page("404.html", "페이지를 찾을 수 없습니다", not_found_main(), "요청한 페이지가 없습니다.", noindex=True)
    pages["robots.txt"] = robots_txt(site)
    if str(site.get("url") or "").strip():
        pages["sitemap.xml"] = sitemap_xml(site, list(dict.fromkeys(ROUTES.values())))
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
    parser.add_argument("--today", default=None, help="예약 발행 기준 날짜 YYYY-MM-DD (기본: 오늘, 한국 시간)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    data, errors = validate(root)
    if errors:
        print("설정을 고쳐 주세요. 아직 아무 파일도 만들지 않았습니다:")
        for e in errors:
            print(f"- {e}")
        return 1
    out = args.out or (root / "dist")
    names = write_site(root, out, build_pages(root, data, args.today))
    print(f"홈페이지 파일을 만들었습니다 ({out}): {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
