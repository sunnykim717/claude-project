#!/usr/bin/env python3
"""명세(JSON)를 읽어 바로 동작하는 index.html 을 만듭니다. AI 채팅이 필요 없습니다.

사용법:
    python vibe/build_app.py vibe/examples/visit_form.json --out vibe/examples/visit_form.html

만들어지는 페이지:
- 첫 번째 화면: 명세의 입력칸으로 만든 입력 폼 (필수, 형식, 최소·최대, 과거 날짜 금지를 검사)
- 두 번째 화면(있을 때): 제출에 성공하면 보이는 완료 화면. 입력한 내용을 요약해서 보여 줍니다.

입력 내용은 서버로 보내지 않고 브라우저 안에서만 처리합니다. 저장이 필요하면 명세에 적고 별도로 설계해야 합니다.
"""

import argparse
import html
import json
import sys
from pathlib import Path

try:
    from .make_brief import validate_spec
except ImportError:  # 파일을 직접 실행한 경우
    from make_brief import validate_spec

INPUT_TYPES = {
    "text": "text",
    "email": "email",
    "phone": "tel",
    "date": "date",
    "number": "number",
}
NUMBER_KEYS = ("min", "max")


def validate_structure(spec):
    """코드로 만들 수 있는 구조인지 검사합니다. validate_spec 과 함께 씁니다."""
    errors = []
    pages = spec.get("pages", [])
    if len(pages) > 2:
        errors.append("화면은 2개(입력 화면, 완료 화면)까지 만들 수 있습니다.")

    form_page = pages[0] if pages else {"fields": []}
    for index, field in enumerate(form_page.get("fields", []), start=1):
        label = field.get("label", "")
        where = f"입력칸 {index} ('{label}')"
        if field.get("type") != "number" and any(k in field for k in NUMBER_KEYS):
            errors.append(f"{where}: min, max 는 number 입력칸에만 쓸 수 있습니다.")
        if field.get("type") != "date" and field.get("minToday"):
            errors.append(f"{where}: minToday 는 date 입력칸에만 쓸 수 있습니다.")
        if "min" in field and "max" in field and field["min"] > field["max"]:
            errors.append(f"{where}: min 이 max 보다 클 수 없습니다.")
    return errors


def unenforced_rules(spec):
    """rules 는 자유 문장이라 코드로 검사할 수 없습니다. 화면 안내와 확인 목록으로만 씁니다.

    실제 검사는 입력칸의 required, 형식, min, max, minToday 로만 적용됩니다.
    """
    return [r for r in spec.get("rules", []) if r.strip()]


def _field_config(field, index):
    return {
        "id": f"f{index}",
        "label": field["label"],
        "type": field["type"],
        "required": bool(field.get("required")),
        "options": field.get("options", []),
        "min": field.get("min"),
        "max": field.get("max"),
        "minToday": bool(field.get("minToday")),
    }


def _json_for_script(value):
    """스크립트 안에 넣어도 태그가 깨지지 않도록 특수 문자를 이스케이프합니다."""
    text = json.dumps(value, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _input_html(config):
    fid, label = config["id"], html.escape(config["label"])
    required = " required" if config["required"] else ""
    common = f'id="{fid}" name="{fid}" aria-describedby="{fid}-err"{required}'
    if config["type"] == "textarea":
        control = f'<textarea {common} rows="3"></textarea>'
    elif config["type"] == "select":
        options = "".join(f"<option value=\"{html.escape(o)}\">{html.escape(o)}</option>" for o in config["options"])
        control = f'<select {common}><option value="">선택하세요</option>{options}</select>'
    else:
        input_type = INPUT_TYPES[config["type"]]
        extra = ""
        if config["type"] == "number":
            if config["min"] is not None:
                extra += f' min="{config["min"]}"'
            if config["max"] is not None:
                extra += f' max="{config["max"]}"'
        control = f'<input type="{input_type}" {common}{extra}>'
    mark = " *" if config["required"] else ""
    return (
        f'<div class="field"><label for="{fid}">{label}{mark}</label>\n'
        f"      {control}\n"
        f'      <p class="err" id="{fid}-err" role="alert"></p></div>'
    )


def build_html(spec):
    """검사를 통과한 명세로 index.html 문서를 만듭니다."""
    pages = spec["pages"]
    form_fields = pages[0].get("fields", [])
    configs = [_field_config(f, i) for i, f in enumerate(form_fields, start=1)]
    done_title = pages[1]["name"] if len(pages) > 1 else "제출 완료"
    rules = unenforced_rules(spec)

    title = html.escape(spec["name"])
    goal = html.escape(spec["goal"].strip())
    fields_html = "\n    ".join(_input_html(c) for c in configs)
    rules_items = "".join(f"<li>{html.escape(r)}</li>" for r in rules)
    rules_block = f'<ul class="rules">{rules_items}</ul>' if rules_items else ""

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light dark; --accent: #2563eb; --err: #b91c1c; --muted: #64748b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; line-height: 1.6; background: #ffffff; color: #0f172a; }}
    main {{ max-width: 560px; margin: 0 auto; padding: 16px; }}
    h1 {{ font-size: 1.5rem; margin: 12px 0 4px; }}
    .goal {{ color: var(--muted); margin: 0 0 16px; }}
    .field {{ margin-bottom: 14px; }}
    label {{ display: block; font-weight: 600; margin-bottom: 4px; }}
    input, select, textarea {{ width: 100%; padding: 9px; font: inherit; border: 1px solid #94a3b8; border-radius: 6px; background: #ffffff; color: #0f172a; }}
    input:focus, select:focus, textarea:focus, button:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; }}
    .err {{ color: var(--err); font-size: 0.9rem; margin: 4px 0 0; min-height: 0; }}
    .err:empty {{ display: none; }}
    button {{ padding: 10px 18px; font: inherit; font-weight: 700; border: 0; border-radius: 6px; background: var(--accent); color: #ffffff; cursor: pointer; }}
    .rules {{ color: var(--muted); font-size: 0.9rem; padding-left: 18px; }}
    dl {{ margin: 12px 0; }}
    dt {{ font-weight: 600; margin-top: 8px; }}
    dd {{ margin: 2px 0 0 0; }}
    [hidden] {{ display: none !important; }}
  </style>
</head>
<body>
<main>
  <section id="form-view">
    <h1>{title}</h1>
    <p class="goal">{goal}</p>
    <form id="form" novalidate>
    {fields_html}
      <button type="submit">제출</button>
    </form>
    {rules_block}
  </section>

  <section id="done-view" hidden>
    <h1>{html.escape(done_title)}</h1>
    <p class="goal">제출되었습니다. 입력한 내용은 이 브라우저 화면에서만 보입니다.</p>
    <dl id="summary"></dl>
    <button type="button" id="again">다시 입력</button>
  </section>
</main>

<script>
  const FIELDS = {_json_for_script(configs)};
  const form = document.getElementById("form");
  const EMAIL = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
  const PHONE = /^[0-9+\\-() ]{{7,20}}$/;
  const DATE = /^\\d{{4}}-\\d{{2}}-\\d{{2}}$/;

  function todayIso() {{
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${{d.getFullYear()}}-${{pad(d.getMonth() + 1)}}-${{pad(d.getDate())}}`;
  }}

  function messageFor(field, raw) {{
    const value = raw.trim();
    if (!value) return field.required ? "필수 입력입니다." : "";
    if (field.type === "email" && !EMAIL.test(value)) return "이메일 형식이 올바르지 않습니다.";
    if (field.type === "phone" && !PHONE.test(value)) return "전화번호 형식이 올바르지 않습니다. 숫자와 하이픈을 사용해 주세요.";
    if (field.type === "date") {{
      if (!DATE.test(value)) return "날짜는 YYYY-MM-DD 형식으로 입력해 주세요.";
      if (field.minToday && value < todayIso()) return "오늘보다 이전 날짜는 고를 수 없습니다.";
    }}
    if (field.type === "number") {{
      const n = Number(value);
      if (Number.isNaN(n)) return "숫자를 입력해 주세요.";
      if (field.min !== null && n < field.min) return `${{field.min}} 이상이어야 합니다.`;
      if (field.max !== null && n > field.max) return `${{field.max}} 이하여야 합니다.`;
    }}
    return "";
  }}

  function valueOf(el) {{
    return el.value;
  }}

  form.addEventListener("submit", (event) => {{
    event.preventDefault();
    let firstInvalid = null;
    for (const field of FIELDS) {{
      const el = document.getElementById(field.id);
      const message = messageFor(field, valueOf(el));
      document.getElementById(field.id + "-err").textContent = message;
      el.setAttribute("aria-invalid", message ? "true" : "false");
      if (message && !firstInvalid) firstInvalid = el;
    }}
    if (firstInvalid) {{
      firstInvalid.focus();
      return;
    }}
    showSummary();
  }});

  function showSummary() {{
    const summary = document.getElementById("summary");
    summary.replaceChildren();
    for (const field of FIELDS) {{
      const value = valueOf(document.getElementById(field.id)).trim();
      const dt = document.createElement("dt");
      dt.textContent = field.label;
      const dd = document.createElement("dd");
      dd.textContent = value || "-";
      summary.append(dt, dd);
    }}
    document.getElementById("form-view").hidden = true;
    document.getElementById("done-view").hidden = false;
    document.getElementById("done-view").querySelector("h1").focus?.();
  }}

  document.getElementById("again").addEventListener("click", () => {{
    form.reset();
    document.querySelectorAll(".err").forEach((el) => {{ el.textContent = ""; }});
    document.getElementById("done-view").hidden = true;
    document.getElementById("form-view").hidden = false;
  }});
</script>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="명세로 바로 동작하는 index.html 만들기")
    parser.add_argument("spec", type=Path, help="명세 JSON 파일")
    parser.add_argument("--out", type=Path, default=Path("index.html"), help="만들 HTML 경로")
    args = parser.parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    errors = validate_spec(spec) + validate_structure(spec)
    if errors:
        print("명세를 고쳐 주세요:")
        for e in errors:
            print(f"- {e}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_html(spec), encoding="utf-8")
    print(f"페이지 생성 완료: {args.out}")

    rules = unenforced_rules(spec)
    if rules:
        print("명세의 규칙은 안내 문구로만 들어갑니다. 입력칸 설정(필수, 형식, min, max, minToday)으로 이미 막히는지 확인해 주세요:")
        for r in rules:
            print(f"- {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
