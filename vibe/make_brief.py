#!/usr/bin/env python3
"""바이브 코딩 명세(JSON)를 검사하고, AI에 그대로 붙여 넣을 요청문(Markdown)을 만듭니다.

사용법:
    python vibe/make_brief.py vibe/examples/visit_form.json
    python vibe/make_brief.py my_spec.json --out brief.md

명세 형식은 vibe/README.md 를 보세요. 외부 서비스를 쓰지 않고 이 저장소 안에서만 동작합니다.
"""

import argparse
import json
import re
from pathlib import Path

FIELD_TYPES = {"text", "textarea", "email", "phone", "date", "number", "select", "radio", "checkbox", "url", "time"}
CHOICE_TYPES = {"select", "radio"}
# 이 도구로는 만들지 않는 정보입니다. 주민등록번호, 계좌번호처럼 민감한 개인정보는 수집하지 않습니다.
FORBIDDEN_LABEL_WORDS = (
    "주민등록", "주민번호", "주민 번호", "계좌", "카드번호", "카드 번호", "비밀번호", "패스워드",
    "여권", "운전면허", "외국인등록", "건강", "진료", "병력", "ssn", "cvc",
)


def _is_sensitive_label(label):
    """띄어쓰기와 대소문자를 무시하고 민감한 표현이 들어 있는지 봅니다."""
    compact = re.sub(r"\s+", "", label).lower()
    return any(re.sub(r"\s+", "", word).lower() in compact for word in FORBIDDEN_LABEL_WORDS)


def validate_spec(spec):
    """명세를 검사합니다. 문제는 모아서 한 번에 돌려줍니다."""
    if not isinstance(spec, dict):
        return ["명세는 { } 로 감싼 설정 묶음이어야 합니다."]
    errors = []

    for key in ("name", "goal"):
        if not str(spec.get(key, "")).strip():
            errors.append(f"'{key}' 가 비어 있습니다. 무엇을 만드는지 한두 문장으로 적어 주세요.")

    pages = spec.get("pages")
    if not isinstance(pages, list) or not pages:
        errors.append("'pages' 에 화면을 한 개 이상 적어 주세요.")
        pages = []

    for p_index, page in enumerate(pages, start=1):
        if not str(page.get("name", "")).strip():
            errors.append(f"화면 {p_index}: 'name'(화면 이름)이 비어 있습니다.")
        fields = page.get("fields", [])
        if not isinstance(fields, list):
            errors.append(f"화면 {p_index}: 'fields' 는 목록이어야 합니다.")
            continue
        for f_index, field in enumerate(fields, start=1):
            label = str(field.get("label", "")).strip()
            where = f"화면 {p_index} 입력칸 {f_index}"
            if not label:
                errors.append(f"{where}: 'label'(입력칸 이름)이 비어 있습니다.")
            if field.get("type") not in FIELD_TYPES:
                errors.append(f"{where}: 'type' 은 {', '.join(sorted(FIELD_TYPES))} 중 하나여야 합니다.")
            if field.get("type") in CHOICE_TYPES and not field.get("options"):
                errors.append(f"{where}: 선택 목록({field.get('type')})에는 'options' 를 적어 주세요.")
            if _is_sensitive_label(label):
                errors.append(f"{where}: '{label}' 은 민감한 개인정보라서 이 도구로 만들 수 없습니다.")

    done = spec.get("done")
    if not isinstance(done, list) or not [d for d in done if str(d).strip()]:
        errors.append("'done' 에 완료 기준을 한 개 이상 적어 주세요. 예: 제출하면 확인 문구가 나온다.")

    rules = spec.get("rules", [])
    if not isinstance(rules, list):
        errors.append("'rules' 는 목록이어야 합니다.")

    return errors


def build_brief(spec):
    """검사를 통과한 명세를 AI 요청문(Markdown)으로 바꿉니다."""
    lines = [
        f"# {spec['name']} 만들기",
        "",
        "아래 명세를 정확히 따라 **단일 index.html 파일 하나**로 만들어 주세요.",
        "외부 라이브러리, 외부 스크립트, 외부 이미지는 쓰지 마세요. 필요한 스타일과 코드는 파일 안에 넣습니다.",
        "",
        "## 1. 목적",
        spec["goal"].strip(),
        "",
        "## 2. 사용자",
        *[f"- {u}" for u in spec.get("users", ["(지정 없음)"])],
        "",
        "## 3. 화면과 입력칸",
    ]

    for page in spec["pages"]:
        lines.append(f"### {page['name']}")
        fields = page.get("fields", [])
        if not fields:
            lines.append("- (입력칸 없음)")
        for field in fields:
            required = "필수" if field.get("required") else "선택"
            options = f", 선택지: {' / '.join(field['options'])}" if field.get("options") else ""
            lines.append(f"- {field['label']} ({field['type']}, {required}{options})")
        lines.append("")

    rule_lines = [f"- {r}" for r in spec.get("rules", [])] or ["- (추가 규칙 없음)"]
    lines += [
        "## 4. 규칙",
        *rule_lines,
        "- 모든 화면 문구는 한국어로 씁니다.",
        "- 입력 형식은 브라우저에서 검사합니다 (이메일, 전화번호, 날짜, 필수 입력).",
        "- 입력한 내용은 서버로 보내지 않고, 화면에서만 처리합니다. 저장 기능은 명세에 있을 때만 넣습니다.",
        "",
        "## 5. 완료 기준",
        *[f"- [ ] {d}" for d in spec["done"]],
        "- [ ] 휴대폰 화면(390px)에서 가로 스크롤이 생기지 않는다.",
        "- [ ] 글자와 배경의 대비가 WCAG AA(4.5:1) 이상이다.",
        "",
        "## 6. 결과 보고",
        "- 만든 파일 내용을 전체로 보여 주세요.",
        "- 명세에 없어서 정하지 못한 부분이 있으면 목록으로 알려 주세요. 추측으로 채우지 마세요.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="바이브 코딩 명세를 AI 요청문으로 변환")
    parser.add_argument("spec", type=Path, help="명세 JSON 파일")
    parser.add_argument("--out", type=Path, help="요청문을 저장할 파일 (없으면 화면에 출력)")
    args = parser.parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    errors = validate_spec(spec)
    if errors:
        print("명세를 고쳐 주세요:")
        for e in errors:
            print(f"- {e}")
        return 1

    brief = build_brief(spec)
    if args.out:
        args.out.write_text(brief, encoding="utf-8")
        print(f"요청문 생성 완료: {args.out}")
    else:
        print(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
