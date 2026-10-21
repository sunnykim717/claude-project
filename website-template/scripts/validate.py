#!/usr/bin/env python3
"""설정과 콘텐츠 파일이 맞는지 검사합니다. 문제는 모아서 한 번에 알려 줍니다.

사용법:
    python scripts/validate.py
"""

import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOT_DIR = Path(__file__).resolve().parent.parent
# 설정 항목 목록은 schema.json 에서만 관리합니다 (편집기와 도구가 같은 파일을 씁니다)
SCHEMA = json.loads((ROOT_DIR / "schema.json").read_text(encoding="utf-8"))
PAGE_FILES = SCHEMA["pages"]
# 주소 목록: 기본 페이지 + 직접 추가한 페이지. validate() 가 채웁니다 (생성기와 함께 씀).
ROUTES = dict(PAGE_FILES)
SLUG = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
DATE_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILES = SCHEMA["files"]
ALLOWED_FONTS = set(SCHEMA["fonts"])
SPACINGS = set(SCHEMA["spacings"])
LAYOUTS = set(SCHEMA["layouts"])
MENUS = set(SCHEMA["menus"])
GALLERY_MAX = SCHEMA["gallery_max"]
LANGUAGES = set(SCHEMA["languages"])
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
IMAGE = re.compile(r"^/images/[A-Za-z0-9._-]+\.(" + "|".join(SCHEMA["image_extensions"]) + ")$")
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_json(root, rel, errors):
    path = Path(root) / rel
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{rel} 파일이 없습니다.")
    except json.JSONDecodeError as e:
        errors.append(f"{rel} 의 JSON 형식이 올바르지 않습니다 ({e.lineno}줄).")
    return None


def is_link_ok(value):
    """외부 주소(https)이거나 이 사이트의 페이지 주소만 허용합니다."""
    return value.startswith(("https://", "http://")) or value in ROUTES




def load_all(root):
    """모든 설정과 콘텐츠를 읽습니다. (데이터, 오류 목록)을 돌려줍니다."""
    errors = []
    data = {key: read_json(root, rel, errors) for key, rel in FILES.items()}
    return data, errors


def check_image(errors, root, rel, value, field="image"):
    """사진 칸이 비어 있으면 아무것도 하지 않습니다. 있으면 형식과 파일 존재를 봅니다."""
    if not value:
        return
    image = str(value)
    if not IMAGE.match(image):
        errors.append(f"{rel}: {field} 는 /images/파일이름.jpg (png, webp, gif) 형식이어야 합니다.")
    elif not (Path(root) / "public" / image.lstrip("/")).exists():
        errors.append(f"{rel}: 사진 파일이 public 폴더에 없습니다 ({image}).")


def check_photo(errors, root, rel, content):
    check_image(errors, root, rel, content.get("image"))
    gallery = content.get("gallery")
    if gallery is None:
        return
    if not isinstance(gallery, list):
        errors.append(f"{rel}: gallery 는 목록이어야 합니다.")
        return
    if len(gallery) > GALLERY_MAX:
        errors.append(f"{rel}: gallery 는 {GALLERY_MAX}장까지 넣을 수 있습니다.")
    for i, item in enumerate(gallery, start=1):
        if not isinstance(item, dict):
            errors.append(f"{rel} {i}번 사진: 사진 칸이 올바르지 않습니다.")
            continue
        check_image(errors, root, f"{rel} {i}번 사진", item.get("image"), "image")
        if "alt" in item and not isinstance(item["alt"], str):
            errors.append(f"{rel} {i}번 사진: alt 는 글자여야 합니다.")


FORBIDDEN_CSS = re.compile(r"<|@import|url\s*\(|expression\s*\(|javascript:|behavior\s*:|-moz-binding", re.IGNORECASE)


def check_custom_css(errors, root):
    """직접 쓰는 CSS 는 배경 사진 말고는 바깥 파일을 부르지 못하게 합니다."""
    path = Path(root) / "config" / "custom.css"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if len(text) > 20000:
        errors.append("config/custom.css: 20,000 글자를 넘을 수 없습니다.")
    found = sorted({m.group(0).lower() for m in FORBIDDEN_CSS.finditer(text)})
    if found:
        errors.append("config/custom.css: 다음은 쓸 수 없습니다: " + ", ".join(found))


def check_items(errors, rel, label, items):
    """사업, 소식, 후원 방법처럼 제목과 선택 항목이 있는 목록을 검사합니다."""
    if not isinstance(items, list):
        errors.append(f"{rel}: 목록이어야 합니다.")
        return
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict) or not item.get("title"):
            errors.append(f"{rel} {i}번 {label}: title 이 필요합니다.")
            continue
        if item.get("date") and not DATE.match(item["date"]):
            errors.append(f"{rel} {i}번 {label}: date 는 YYYY-MM-DD 형식이어야 합니다.")
        if "publish" in item and not (isinstance(item["publish"], str) and DATE_TEXT.match(item["publish"])):
            errors.append(f"{rel} {i}번 {label}: publish 는 YYYY-MM-DD 형식이어야 합니다.")
        if "body" in item and not isinstance(item["body"], str):
            errors.append(f"{rel} {i}번 {label}: body 는 글자여야 합니다.")
        if item.get("url") and not item["url"].startswith(("https://", "http://")):
            errors.append(f"{rel} {i}번 {label}: url 은 https:// 로 시작해야 합니다.")


SUPABASE_URL = re.compile(r"^https://[a-z0-9-]+\.supabase\.co/?$")


def jwt_role(token):
    """키가 JWT 형식이면 role (anon 또는 service_role) 을 돌려줍니다. 아니면 None."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    padded = parts[1].replace("-", "+").replace("_", "/")
    padded += "=" * (-len(padded) % 4)
    try:
        payload = json.loads(base64.b64decode(padded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return payload.get("role") if isinstance(payload, dict) else None


def check_supabase(errors, cfg):
    """Supabase 연결 정보. 둘 다 비워 두면 연결하지 않은 것입니다. 비밀 키는 공개 페이지에 넣을 수 없습니다."""
    if not isinstance(cfg, dict):
        errors.append("config/supabase.json: 최상위 값은 { } 묶음이어야 합니다.")
        return
    url, key = str(cfg.get("url") or ""), str(cfg.get("anonKey") or "")
    if not url and not key:
        return
    if not url or not key:
        errors.append("config/supabase.json: url 과 anonKey 를 둘 다 넣거나 둘 다 비워 두세요.")
        return
    if not SUPABASE_URL.match(url):
        errors.append("config/supabase.json: url 은 https://프로젝트.supabase.co 형식이어야 합니다.")
    if key.startswith("sb_secret_") or jwt_role(key) == "service_role":
        errors.append("config/supabase.json: service_role (secret) 키는 공개 페이지에 넣을 수 없습니다. anon 또는 publishable 키를 쓰세요.")
    elif not (key.startswith("sb_publishable_") or jwt_role(key) == "anon"):
        errors.append("config/supabase.json: anon 또는 publishable 키를 넣어 주세요 (Settings → API).")


def check_custom_pages(errors, root, custom):
    """직접 추가한 페이지: 주소(slug)는 영문 소문자로 시작하고 기본 페이지와 겹치지 않아야 합니다."""
    if not isinstance(custom, list):
        errors.append("content/custom-pages.json: 목록이어야 합니다.")
        return
    seen = set()
    for i, page in enumerate(custom, start=1):
        rel = f"content/custom-pages.json {i}번"
        if not isinstance(page, dict):
            errors.append(f"{rel}: 페이지 칸이 올바르지 않습니다.")
            continue
        slug = page.get("slug")
        if not isinstance(slug, str) or not SLUG.match(slug):
            errors.append(f"{rel}: slug 는 영문 소문자로 시작하는 2~31자 (소문자, 숫자, -) 여야 합니다.")
            continue
        if f"/{slug}" in PAGE_FILES or slug in seen:
            errors.append(f"{rel}: 주소 /{slug} 가 이미 있습니다.")
            continue
        seen.add(slug)
        if not page.get("title"):
            errors.append(f"{rel}: title 을 적어 주세요.")
        check_items(errors, rel, "항목", page.get("items", []))
        check_photo(errors, root, rel, page)


def validate(root):
    """(데이터, 오류 목록)을 돌려줍니다. 오류가 없으면 목록이 비어 있습니다."""
    data, errors = load_all(root)
    ROUTES.clear()
    ROUTES.update(PAGE_FILES)
    custom = data.get("custom_pages")
    if isinstance(custom, list):
        for page in custom:
            if isinstance(page, dict) and isinstance(page.get("slug"), str) and SLUG.match(page["slug"]):
                ROUTES.setdefault(f"/{page['slug']}", f"{page['slug']}.html")
    site, nav, theme = data["site"], data["nav"], data["theme"]

    if isinstance(site, dict):
        for key in ("name", "language"):
            if not str(site.get(key, "")).strip():
                errors.append(f"config/site.json: '{key}' 을 적어 주세요.")
        if site.get("language") not in LANGUAGES:
            errors.append("config/site.json: language 은 ko, en, ja 중 하나여야 합니다.")
    elif site is not None:
        errors.append("config/site.json: 최상위 값은 { } 묶음이어야 합니다.")

    if isinstance(nav, list):
        for i, entry in enumerate(nav, start=1):
            if not isinstance(entry, dict) or not entry.get("label"):
                errors.append(f"config/navigation.json {i}번: label 이 필요합니다.")
            elif entry.get("path") not in ROUTES:
                errors.append(f"config/navigation.json {i}번: 알 수 없는 페이지 주소입니다 ({entry.get('path')}).")
    elif nav is not None:
        errors.append("config/navigation.json: 목록이어야 합니다.")

    if isinstance(theme, dict):
        for key in ("primaryColor", "backgroundColor", "textColor"):
            if not HEX.match(str(theme.get(key, ""))):
                errors.append(f"config/theme.json: {key} 는 #RRGGBB 형식이어야 합니다.")
        if theme.get("font") not in ALLOWED_FONTS:
            errors.append(f"config/theme.json: font 은 {', '.join(sorted(ALLOWED_FONTS))} 중 하나여야 합니다.")
        radius = theme.get("radius")
        if not isinstance(radius, int) or isinstance(radius, bool) or not 0 <= radius <= 32:
            errors.append("config/theme.json: radius 는 0~32 사이의 정수여야 합니다.")
        if theme.get("spacing") not in SPACINGS:
            errors.append(f"config/theme.json: spacing 은 {', '.join(SCHEMA['spacings'])} 중 하나여야 합니다.")
        if theme.get("layout") not in LAYOUTS:
            errors.append(f"config/theme.json: layout 은 {', '.join(SCHEMA['layouts'])} 중 하나여야 합니다.")
        if theme.get("menu") not in MENUS:
            errors.append(f"config/theme.json: menu 는 {', '.join(SCHEMA['menus'])} 중 하나여야 합니다.")

    if isinstance(site, dict):
        check_image(errors, root, "config/site.json", site.get("logo"), "logo")
    if isinstance(theme, dict):
        check_image(errors, root, "config/theme.json", theme.get("backgroundImage"), "backgroundImage")
    check_custom_css(errors, root)

    home = data["home"]
    if isinstance(home, dict):
        hero = home.get("hero") or {}
        if not hero.get("title"):
            errors.append("content/home.json: hero.title 을 적어 주세요.")
        check_photo(errors, root, "content/home.json", hero)
        if hero.get("buttonLink") and not is_link_ok(hero["buttonLink"]):
            errors.append(f"content/home.json: buttonLink 은 https:// 주소 또는 페이지 주소여야 합니다 ({hero['buttonLink']}).")
        sections = home.get("sections")
        if sections is not None:
            if not isinstance(sections, list):
                errors.append("content/home.json: sections 는 목록이어야 합니다.")
            elif len(set(map(str, sections))) != len(sections) or any(s not in SCHEMA["home_sections"] for s in sections):
                errors.append(f"content/home.json: sections 는 {', '.join(SCHEMA['home_sections'])} 중에서 한 번씩만 고를 수 있습니다.")

    for name in SCHEMA["photo_pages"]:
        if isinstance(data[name], dict):
            check_photo(errors, root, f"content/{name}.json", data[name])
    for name in SCHEMA["generic_pages"]:
        if isinstance(data[name], dict):
            if not data[name].get("title"):
                errors.append(f"content/{name}.json: title 을 적어 주세요.")
            check_items(errors, f"content/{name}.json", "항목", data[name].get("items", []))
    check_custom_pages(errors, root, data["custom_pages"])
    check_supabase(errors, data["supabase"])

    projects = data["projects"]
    if isinstance(projects, dict):
        check_items(errors, "content/projects.json", "사업", projects.get("items", []))
    news = data["news"]
    if isinstance(news, dict):
        check_items(errors, "content/news.json", "소식", news.get("items", []))
    support = data["support"]
    if isinstance(support, dict):
        check_items(errors, "content/support.json", "후원 방법", support.get("ways", []))
    transparency = data["transparency"]
    if isinstance(transparency, dict):
        check_items(errors, "content/transparency.json", "자료", transparency.get("reports", []))
    volunteer = data["volunteer"]
    if isinstance(volunteer, dict):
        check_items(errors, "content/volunteer.json", "활동", volunteer.get("positions", []))
    privacy = data["privacy"]
    if isinstance(privacy, dict):
        check_items(errors, "content/privacy.json", "항목", privacy.get("items", []))

    contact = data["contact"]
    if isinstance(contact, dict):
        if contact.get("email") and not EMAIL.match(contact["email"]):
            errors.append("content/contact.json: 이메일 형식이 올바르지 않습니다.")
        for key, value in (contact.get("social") or {}).items():
            if value and not value.startswith(("https://", "http://")):
                errors.append(f"content/contact.json: social.{key} 는 https:// 로 시작해야 합니다.")

    return data, errors


def main(root=ROOT):
    _, errors = validate(root)
    if errors:
        print("설정을 고쳐 주세요:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("검사 통과: 설정과 콘텐츠가 맞습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
