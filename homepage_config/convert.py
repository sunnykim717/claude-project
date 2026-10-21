"""홈페이지 설정(template.json 형식)을 생성기가 읽는 site.json 형식으로 바꿉니다.

지원하는 항목은 페이지에 반영하고, 지원하지 않는 항목은 경고로 알려 줍니다.
오류가 있으면 만들지 않고 ConfigError 로 모든 오류를 한 번에 알려 줍니다.
"""

import json
import re
from pathlib import Path

from update_homepage import is_safe_link, validate_site

DESIGNS_PATH = Path(__file__).resolve().parent / "designs.json"
SPACINGS = {"compact", "normal", "airy"}


def load_designs():
    """기본 디자인 목록을 읽습니다. 각 디자인은 색, 글꼴, 모서리, 여백을 한 번에 정합니다."""
    return json.loads(DESIGNS_PATH.read_text(encoding="utf-8"))

LANGUAGES = {"ko", "en", "ja"}
HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

# 설정의 글꼴 이름 -> 생성기가 쓰는 글꼴
FONT_MAP = {
    "system-ui": "system-ui, sans-serif",
    "sans-serif": "system-ui, sans-serif",
    "serif": "Georgia, serif",
    "Georgia": "Georgia, serif",
    "monospace": "ui-monospace, monospace",
    "mono": "ui-monospace, monospace",
}

# 설정의 메뉴 주소 -> 이 페이지 안의 섹션
PATH_TO_ANCHOR = {
    "/": "top",
    "/about": "about",
    "/projects": "items",
    "/news": "items",
    "/support": "contact",
    "/contact": "contact",
}

# 설정의 섹션 이름 -> 생성기의 섹션 이름
SECTION_MAP = {
    "introduction": "about",
    "projects": "items",
    "news": "items",
    "support": "contact",
}
DEFAULT_SECTIONS = ["introduction", "projects", "news", "support"]

UNSUPPORTED_FEATURES = {
    "noticeBoard": "게시판",
    "gallery": "갤러리",
    "contactForm": "문의 입력 폼",
    "donationPayment": "후원 결제",
    "memberLogin": "회원 로그인",
    "multilingual": "다국어",
}


class ConfigError(ValueError):
    """설정에 오류가 있을 때. errors 에 모든 오류가 들어 있습니다."""

    def __init__(self, errors):
        super().__init__("\n".join(errors))
        self.errors = errors


def _link_for(path):
    """메뉴나 버튼의 주소를 페이지 안의 이동 주소로 바꿉니다. 알 수 없으면 None 입니다."""
    if not isinstance(path, str):
        return None
    if path.startswith(("https://", "http://")):
        return path
    anchor = PATH_TO_ANCHOR.get(path)
    return f"#{anchor}" if anchor else None


def convert(config):
    """설정을 site.json 형식으로 바꿉니다. (사이트 데이터, 경고 목록)을 돌려줍니다."""
    errors, warnings = [], []
    if not isinstance(config, dict):
        raise ConfigError(["설정은 { } 로 감싼 묶음이어야 합니다."])

    site_cfg = config.get("site") or {}
    name = site_cfg.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("site.name 에 홈페이지 이름을 적어 주세요.")
    language = site_cfg.get("language", "ko")
    if language not in LANGUAGES:
        errors.append(f"site.language 은 ko, en, ja 중 하나여야 합니다 ({language}).")
    for key in ("logo", "domain"):
        if site_cfg.get(key):
            warnings.append(f"site.{key} 은 아직 페이지에 반영되지 않습니다.")

    homepage = config.get("homepage") or {}
    hero = homepage.get("hero") or {}
    subtitle = hero.get("subtitle") or site_cfg.get("description") or ""
    if hero.get("title") and hero.get("title") != name:
        warnings.append("homepage.hero.title 은 아직 쓰이지 않습니다. 페이지 제목은 site.name 을 씁니다.")
    if hero.get("image"):
        warnings.append("homepage.hero.image 는 아직 지원하지 않아 표시되지 않습니다.")

    # 디자인 프리셋을 먼저 깔고, theme 에 직접 적은 값이 있으면 그 값이 이깁니다.
    designs = load_designs()
    design_name = config.get("design")
    base = {}
    if design_name:
        if design_name in designs:
            base = {k: v for k, v in designs[design_name].items() if k != "label"}
        else:
            errors.append(f"design 은 {', '.join(sorted(designs))} 중 하나여야 합니다 ({design_name}).")
    theme_cfg = {**base, **(config.get("theme") or {})}
    theme = {}
    for key, out in (("primaryColor", "accent"), ("backgroundColor", "bg"), ("textColor", "text")):
        value = theme_cfg.get(key)
        if value is None:
            continue
        if isinstance(value, str) and HEX_PATTERN.match(value):
            theme[out] = value
        else:
            errors.append(f"theme.{key} 는 #RRGGBB 형식이어야 합니다 ({value}).")
    font = theme_cfg.get("font")
    if font:
        if font in FONT_MAP:
            theme["font"] = FONT_MAP[font]
        else:
            warnings.append(f"글꼴 '{font}' 은 지원하지 않아 기본 글꼴을 씁니다. (지원: {', '.join(sorted(FONT_MAP))})")
    if "radius" in theme_cfg:
        radius = theme_cfg["radius"]
        if isinstance(radius, int) and not isinstance(radius, bool) and 0 <= radius <= 32:
            theme["radius"] = radius
        else:
            errors.append(f"theme.radius 는 0~32 사이의 정수여야 합니다 ({radius}).")
    if "spacing" in theme_cfg:
        spacing = theme_cfg["spacing"]
        if spacing in SPACINGS:
            theme["spacing"] = spacing
        else:
            errors.append(f"theme.spacing 은 compact, normal, airy 중 하나여야 합니다 ({spacing}).")
    if theme_cfg.get("layout"):
        warnings.append("theme.layout 은 아직 적용되지 않습니다.")

    content = config.get("content") or {}
    items = []
    for key in ("projects", "news"):
        entries = content.get(key) or []
        if not isinstance(entries, list):
            errors.append(f"content.{key} 는 목록이어야 합니다.")
            continue
        items.extend(entry for entry in entries if isinstance(entry, dict) and entry.get("title"))

    nav = []
    for index, entry in enumerate(config.get("navigation") or [], start=1):
        if not isinstance(entry, dict) or not entry.get("label"):
            errors.append(f"navigation {index}번: 이름(label)과 주소(path)가 필요합니다.")
            continue
        href = _link_for(entry.get("path"))
        if href is None:
            warnings.append(f"메뉴 '{entry['label']}' 의 주소 {entry.get('path')} 는 이 페이지에 없어서 건너뜁니다.")
            continue
        nav.append({"label": entry["label"], "href": href})

    order = homepage.get("sections", DEFAULT_SECTIONS)
    if not isinstance(order, list):
        errors.append("homepage.sections 는 목록이어야 합니다.")
        order = []
    sections = []
    for name_ in order:
        if name_ not in SECTION_MAP:
            errors.append(f"homepage.sections 에 알 수 없는 섹션이 있습니다: {name_}")
            continue
        mapped = SECTION_MAP[name_]
        if mapped not in sections:
            sections.append(mapped)

    cta = None
    button_text, button_link = hero.get("buttonText"), hero.get("buttonLink")
    if button_link:
        href = _link_for(button_link)
        if href and is_safe_link(href):
            cta = {"label": button_text or "자세히 보기", "url": href}
            sections.insert(0, "cta")
        else:
            warnings.append(f"버튼 주소 {button_link} 는 이 페이지에 없어서 버튼을 만들지 않습니다.")

    social = {k: v for k, v in (content.get("social") or {}).items() if v}
    if social:
        sections.append("social")

    about = content.get("about", "")
    contact = content.get("contact", "")
    if "about" in sections and not str(about).strip():
        warnings.append("기관소개 섹션이 켜져 있지만 content.about 글이 비어 있습니다.")
    if "contact" in sections and not str(contact).strip():
        warnings.append("후원·문의 섹션이 켜져 있지만 content.contact 글이 비어 있습니다.")
    if "items" in sections and not items:
        warnings.append("주요사업·소식 섹션이 켜져 있지만 항목이 없습니다.")

    features = config.get("features") or {}
    for key, label in UNSUPPORTED_FEATURES.items():
        if features.get(key):
            warnings.append(f"{label} 기능은 아직 만들어지지 않습니다.")

    if config.get("deployment"):
        warnings.append("배포 설정은 이 도구가 하지 않습니다. GitHub Pages 와 자동화 워크플로를 사용하세요.")

    site = {"title": name.strip() if isinstance(name, str) else "", "lang": language}
    if subtitle:
        site["subtitle"] = subtitle
    if about:
        site["about"] = about
    if contact:
        site["contact"] = contact
    if theme:
        site["theme"] = theme
    if items:
        site["items"] = items
    if nav:
        site["nav"] = nav
    site["sections"] = sections
    if cta:
        site["cta"] = cta
    if social:
        site["social"] = social

    if not errors:
        try:
            validate_site(site, "설정")
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise ConfigError(errors)
    return site, warnings
