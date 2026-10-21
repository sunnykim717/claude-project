#!/usr/bin/env python3
"""설정과 콘텐츠 파일이 맞는지 검사합니다. 문제는 모아서 한 번에 알려 줍니다.

사용법:
    python scripts/validate.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 이 템플릿이 만드는 페이지: 주소 -> 파일 이름
PAGE_FILES = {"/": "index.html", "/about": "about.html", "/projects": "projects.html", "/contact": "contact.html"}
ALLOWED_FONTS = {"system-ui", "serif", "mono"}
SPACINGS = {"compact", "normal", "airy"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
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
    return value.startswith(("https://", "http://")) or value in PAGE_FILES


FILES = {
    "site": "config/site.json", "nav": "config/navigation.json", "theme": "config/theme.json",
    "home": "content/home.json", "about": "content/about.json",
    "projects": "content/projects.json", "contact": "content/contact.json",
}


def load_all(root):
    """모든 설정과 콘텐츠를 읽습니다. (데이터, 오류 목록)을 돌려줍니다."""
    errors = []
    data = {key: read_json(root, rel, errors) for key, rel in FILES.items()}
    return data, errors


def validate(root):
    """(데이터, 오류 목록)을 돌려줍니다. 오류가 없으면 목록이 비어 있습니다."""
    data, errors = load_all(root)
    site, nav, theme = data["site"], data["nav"], data["theme"]

    if isinstance(site, dict):
        for key in ("name", "language"):
            if not str(site.get(key, "")).strip():
                errors.append(f"config/site.json: '{key}' 을 적어 주세요.")
        if site.get("language") not in {"ko", "en", "ja"}:
            errors.append("config/site.json: language 은 ko, en, ja 중 하나여야 합니다.")
    elif site is not None:
        errors.append("config/site.json: 최상위 값은 { } 묶음이어야 합니다.")

    if isinstance(nav, list):
        for i, entry in enumerate(nav, start=1):
            if not isinstance(entry, dict) or not entry.get("label"):
                errors.append(f"config/navigation.json {i}번: label 이 필요합니다.")
            elif entry.get("path") not in PAGE_FILES:
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
            errors.append("config/theme.json: spacing 은 compact, normal, airy 중 하나여야 합니다.")

    home = data["home"]
    if isinstance(home, dict):
        hero = home.get("hero") or {}
        if not hero.get("title"):
            errors.append("content/home.json: hero.title 을 적어 주세요.")
        if hero.get("buttonLink") and not is_link_ok(hero["buttonLink"]):
            errors.append(f"content/home.json: buttonLink 은 https:// 주소 또는 페이지 주소여야 합니다 ({hero['buttonLink']}).")

    projects = data["projects"]
    if isinstance(projects, dict):
        for i, item in enumerate(projects.get("items", []), start=1):
            if not isinstance(item, dict) or not item.get("title"):
                errors.append(f"content/projects.json {i}번 사업: title 이 필요합니다.")
                continue
            if item.get("date") and not DATE.match(item["date"]):
                errors.append(f"content/projects.json {i}번 사업: date 는 YYYY-MM-DD 형식이어야 합니다.")
            if item.get("url") and not item["url"].startswith(("https://", "http://")):
                errors.append(f"content/projects.json {i}번 사업: url 은 https:// 로 시작해야 합니다.")

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
