#!/usr/bin/env python3
"""대표색 하나로 버튼·링크·배경·글자 색을 규칙으로 제안합니다. AI 나 무작위 조합을 쓰지 않습니다.

규칙
1. 대표색이 흰 글자와 4.5:1 이상이면 그대로 버튼색(primary)으로 씁니다. 부족하면 같은 색상을 검은 쪽으로 5%씩 섞어 맞춥니다.
2. 링크·강조색은 버튼색과 같습니다 (흰 배경에서 4.5:1 이상).
3. 본문 글자는 짙은 회색, 보조 글자는 더 옅은 회색이되 배경과 4.5:1 이상을 지킵니다.
4. 배경은 흰색, 강조 면(accent)은 대표색을 85% 흰색과 섞은 옅은 색입니다.
5. 원래 대표색은 장식(decorative)으로만 쓰도록 따로 돌려줍니다.

사용법: python scripts/palette.py #2F5D46
"""

import json
import re
import sys

WHITE = "#FFFFFF"
DARK = "#1A1A1A"
MUTED_START = "#4B4B4B"
HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize(value):
    match = HEX.match(str(value).strip())
    if not match:
        raise ValueError("색은 #RGB 또는 #RRGGBB 형식이어야 합니다.")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return "#" + digits.upper()


def channels(color):
    n = int(color[1:], 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255]


def to_hex(rgb):
    return "#" + "".join(f"{round(c):02X}" for c in rgb)


def luminance(color):
    values = []
    for c in channels(color):
        c = c / 255
        values.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast(a, b):
    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def mix(color, other, amount):
    """color 를 other 쪽으로 amount(0~1) 만큼 섞습니다."""
    return to_hex([c + (o - c) * amount for c, o in zip(channels(color), channels(other))])


def darken_until(color, background, minimum=4.5):
    """색을 검은 쪽으로 5%씩 섞어 배경과 대비가 minimum 이상이 될 때까지 진하게 만듭니다."""
    current = color
    for step in range(0, 21):
        candidate = mix(color, "#000000", step * 0.05)
        current = candidate
        if contrast(candidate, background) >= minimum:
            return candidate
    return current


def suggest(color):
    base = normalize(color)
    primary = base if contrast(base, WHITE) >= 4.5 else darken_until(base, WHITE)
    button_text = WHITE if contrast(WHITE, primary) >= contrast(DARK, primary) else DARK
    accent = mix(base, WHITE, 0.85)
    text = DARK
    muted = MUTED_START
    if contrast(muted, accent) < 4.5:
        muted = DARK
    palette = {
        "primaryColor": primary,
        "buttonText": button_text,
        "linkColor": primary,
        "backgroundColor": WHITE,
        "accentColor": accent,
        "textColor": text,
        "mutedText": muted,
        "focusColor": primary,
        "decorativeColor": base,
    }
    checks = {
        "본문/배경": contrast(text, WHITE),
        "버튼 글자/버튼": contrast(button_text, primary),
        "링크/배경": contrast(primary, WHITE),
        "보조 글자/강조 면": contrast(muted, accent),
    }
    palette["checks"] = {k: round(v, 2) for k, v in checks.items()}
    palette["passes"] = all(v >= 4.5 for v in checks.values())
    return palette


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("사용법: python scripts/palette.py #RRGGBB")
        return 2
    try:
        result = suggest(argv[0])
    except ValueError as error:
        print(str(error))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passes"] else 1


if __name__ == "__main__":
    sys.exit(main())
