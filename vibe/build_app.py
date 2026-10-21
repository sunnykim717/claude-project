#!/usr/bin/env python3
"""명세(JSON)를 읽어 바로 동작하는 index.html 을 만듭니다. AI 채팅이 필요 없습니다.

사용법:
    python vibe/build_app.py vibe/examples/visit_form.json --out vibe/examples/visit_form.html
    python vibe/build_app.py 명세.json --out 결과/index.html --github 아이디/저장소 --path index.html

만들어지는 페이지:
- 입력 화면: 입력칸이 있는 화면을 차례로 진행합니다 (단계별 검사, 이전/다음).
- 완료 화면: 입력칸이 없는 화면이 있으면 그것을 완료 화면으로 씁니다. 입력 내용을 요약해서 보여 줍니다.
- save: true 이면 제출 내용을 이 기기(브라우저)에 저장하고, 목록을 보거나 CSV 로 내려받을 수 있습니다.
- 코드 가져가기: 페이지 코드를 복사하거나 내려받거나, GitHub 새 파일 화면으로 넘깁니다.

입력 내용은 서버로 보내지 않습니다. 저장은 이 기기의 브라우저 안에서만 이루어집니다.
"""

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

try:
    from .make_brief import FIELD_TYPES, validate_spec
except ImportError:  # 파일을 직접 실행한 경우
    from make_brief import FIELD_TYPES, validate_spec

INPUT_TYPES = {
    "text": "text",
    "email": "email",
    "phone": "tel",
    "date": "date",
    "number": "number",
    "url": "url",
    "time": "time",
}
TEXT_TYPES = {"text", "textarea", "email", "phone", "url"}
CHOICE_TYPES = {"select", "radio"}

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GIT_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_.-][A-Za-z0-9_./-]*$")
# GitHub 주소에 실을 수 있는 코드 길이의 기준입니다. 이보다 길면 복사해서 붙여 넣도록 안내합니다.
GITHUB_LINK_LIMIT = 7000


def _is_input_page(page):
    return bool(page.get("fields"))


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _type_errors(spec):
    """값의 종류(글자, 숫자, 참거짓, 목록)를 검사합니다. 잘못된 종류는 화면에 넣기 전에 거부합니다."""
    errors = []
    for key in ("name", "goal"):
        if key in spec and not isinstance(spec[key], str):
            errors.append(f"'{key}' 는 글자로 적어 주세요.")
    for key in ("users", "rules", "done"):
        value = spec.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"'{key}' 는 글자 목록이어야 합니다.")
    if not isinstance(spec.get("pages", []), list):
        return errors + ["'pages' 는 목록이어야 합니다."]
    for page_index, page in enumerate(spec.get("pages", []), start=1):
        if not isinstance(page, dict):
            errors.append(f"화면 {page_index}: 화면은 이름과 입력칸으로 적어 주세요.")
            continue
        if not isinstance(page.get("name", ""), str):
            errors.append(f"화면 {page_index}: 화면 이름은 글자로 적어 주세요.")
        fields = page.get("fields", [])
        if not isinstance(fields, list):
            errors.append(f"화면 {page_index}: 'fields' 는 목록이어야 합니다.")
            continue
        for field_index, field in enumerate(fields, start=1):
            if not isinstance(field, dict):
                errors.append(f"화면 {page_index} 입력칸 {field_index}: 입력칸은 설정 묶음으로 적어 주세요.")
                continue
            where = f"화면 {page_index} 입력칸 {field_index}"
            if not isinstance(field.get("label", ""), str):
                errors.append(f"{where}: 'label' 은 글자로 적어 주세요.")
            for key in ("required", "minToday"):
                if key in field and not isinstance(field[key], bool):
                    errors.append(f"{where}: '{key}' 는 true 또는 false 여야 합니다.")
            for key in ("min", "max", "minLength", "maxLength"):
                if key in field and not _is_number(field[key]):
                    errors.append(f"{where}: '{key}' 는 숫자여야 합니다.")
            options = field.get("options", [])
            if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
                errors.append(f"{where}: 'options' 는 글자 목록이어야 합니다.")
    return errors


def validate_structure(spec):
    """코드로 만들 수 있는 구조인지 검사합니다. validate_spec 과 함께 씁니다."""
    errors = _type_errors(spec)
    if errors:
        return errors
    pages = spec.get("pages", [])

    if not any(_is_input_page(p) for p in pages):
        errors.append("입력칸이 있는 화면이 하나 이상 필요합니다.")
    seen_done = False
    for index, page in enumerate(pages, start=1):
        if not _is_input_page(page):
            if seen_done:
                errors.append(f"화면 {index}: 입력칸이 없는 완료 화면은 하나만 둘 수 있습니다.")
            seen_done = True
        elif seen_done:
            errors.append(f"화면 {index}: 입력칸이 있는 화면은 완료 화면보다 앞에 두어야 합니다.")

    if "save" in spec and not isinstance(spec["save"], bool):
        errors.append("'save' 는 true 또는 false 여야 합니다.")

    for page_index, page in enumerate(pages, start=1):
        for field_index, field in enumerate(page.get("fields", []), start=1):
            label = field.get("label", "")
            where = f"화면 {page_index} 입력칸 {field_index} ('{label}')"
            kind = field.get("type")
            if kind not in FIELD_TYPES:
                continue  # 종류 오류는 validate_spec 이 알려 줍니다.
            if kind != "number" and any(k in field for k in ("min", "max")):
                errors.append(f"{where}: min, max 는 number 입력칸에만 쓸 수 있습니다.")
            if kind != "date" and field.get("minToday"):
                errors.append(f"{where}: minToday 는 date 입력칸에만 쓸 수 있습니다.")
            if "min" in field and "max" in field and field["min"] > field["max"]:
                errors.append(f"{where}: min 이 max 보다 클 수 없습니다.")
            if kind not in TEXT_TYPES and any(k in field for k in ("minLength", "maxLength")):
                errors.append(f"{where}: minLength, maxLength 는 글자를 적는 입력칸에만 쓸 수 있습니다.")
            if "minLength" in field and "maxLength" in field and field["minLength"] > field["maxLength"]:
                errors.append(f"{where}: minLength 가 maxLength 보다 클 수 없습니다.")
            if kind == "checkbox" and field.get("options"):
                errors.append(f"{where}: 동의 체크(checkbox) 칸에는 options 를 쓸 수 없습니다.")
    return errors


def validate_github(github, branch, path):
    """GitHub 연결 정보를 검사합니다. 값이 없으면 None 을 돌려줍니다."""
    if github is None:
        return None
    if not REPO_PATTERN.match(github):
        raise ValueError("--github 는 '아이디/저장소' 형식이어야 합니다. 예: 내아이디/내저장소")
    if not re.match(r"^[A-Za-z0-9._/-]+$", branch) or ".." in branch:
        raise ValueError("--branch 에는 영문, 숫자, 점, 밑줄, 하이픈, 슬래시만 쓸 수 있습니다.")
    if not GIT_PATH_PATTERN.match(path) or ".." in path:
        raise ValueError("--path 는 저장소 안의 상대 경로여야 합니다. 예: index.html")
    return {"repo": github, "branch": branch, "path": path}


def unenforced_rules(spec):
    """rules 는 자유 문장이라 코드로 검사할 수 없습니다. 화면 안내와 확인 목록으로만 씁니다."""
    return [r for r in spec.get("rules", []) if r.strip()]


def _field_config(field, index, step):
    return {
        "id": f"f{index}",
        "step": step,
        "label": field["label"],
        "type": field["type"],
        "required": bool(field.get("required")),
        "options": field.get("options", []),
        "min": field.get("min"),
        "max": field.get("max"),
        "minToday": bool(field.get("minToday")),
        "minLength": field.get("minLength"),
        "maxLength": field.get("maxLength"),
    }


def _json_for_script(value):
    """스크립트 안에 넣어도 태그가 깨지지 않도록 특수 문자를 이스케이프합니다."""
    text = json.dumps(value, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _input_html(config):
    fid, label = config["id"], html.escape(config["label"])
    mark = " *" if config["required"] else ""
    required = " required" if config["required"] else ""

    if config["type"] == "checkbox":
        return (
            f'<div class="field"><label class="choice" for="{fid}">'
            f'<input type="checkbox" id="{fid}" name="{fid}" aria-describedby="{fid}-err"{required}> '
            f"{label}{mark}</label>\n"
            f'      <p class="err" id="{fid}-err" role="alert"></p></div>'
        )

    if config["type"] == "radio":
        choices = "".join(
            f'<label class="choice"><input type="radio" name="{fid}" value="{html.escape(o)}"> {html.escape(o)}</label>'
            for o in config["options"]
        )
        return (
            f'<fieldset class="field"><legend>{label}{mark}</legend>\n'
            f"      {choices}\n"
            f'      <p class="err" id="{fid}-err" role="alert"></p></fieldset>'
        )

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
    return (
        f'<div class="field"><label for="{fid}">{label}{mark}</label>\n'
        f"      {control}\n"
        f'      <p class="err" id="{fid}-err" role="alert"></p></div>'
    )


def _steps_html(input_pages, configs_by_step):
    """입력 화면을 단계별 블록으로 만듭니다. 첫 단계만 보이고 나머지는 숨깁니다."""
    total = len(input_pages)
    blocks = []
    for i, page in enumerate(input_pages):
        progress = f'<p class="progress">{i + 1} / {total} 단계</p>' if total > 1 else ""
        fields = "\n      ".join(_input_html(c) for c in configs_by_step[i])
        prev_btn = '<button type="button" class="secondary prev">이전</button>' if i > 0 else ""
        if i == total - 1:
            action = '<button type="submit">제출</button>'
        else:
            action = '<button type="button" class="next">다음</button>'
        hidden = "" if i == 0 else " hidden"
        blocks.append(
            f'<div class="step" data-step="{i}"{hidden}>\n'
            f"      {progress}\n"
            f'      <h2 class="step-title">{html.escape(page["name"])}</h2>\n'
            f"      {fields}\n"
            f'      <div class="nav">{prev_btn}{action}</div>\n'
            f"    </div>"
        )
    return "\n    ".join(blocks)


def _panel_css():
    return """
    .code-panel { margin-top: 32px; border-top: 1px solid #cbd5e1; padding-top: 12px; }
    .code-panel summary, .saved-panel summary { cursor: pointer; font-weight: 600; }
    .code-panel textarea { width: 100%; font-family: ui-monospace, monospace; font-size: 0.8rem; margin-top: 8px; }
    .saved-panel { margin-top: 24px; }
    .saved-panel table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }
    .saved-panel th, .saved-panel td { border: 1px solid #cbd5e1; padding: 4px 6px; text-align: left; vertical-align: top; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .secondary { background: #ffffff; color: var(--accent); border: 1px solid var(--accent); }
    .nav { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
    .progress { color: var(--muted); font-size: 0.9rem; margin: 0 0 4px; }
    .choice { display: inline-flex; align-items: center; gap: 6px; font-weight: 400; margin: 4px 0; }
    .choice input { width: auto; }
    fieldset { border: 0; padding: 0; margin: 0 0 14px; }
    legend { font-weight: 600; margin-bottom: 4px; }
    .hint { color: var(--muted); font-size: 0.9rem; }"""


def _panel_html(source, github):
    """코드 가져가기 영역입니다. source 는 복사될 페이지 코드(이 영역을 뺀 것)입니다."""
    github_button = (
        '<button type="button" id="github-link" class="secondary">GitHub 에서 새 파일로 열기</button>'
        if github else ""
    )
    return f"""
  <details id="code-panel" class="code-panel">
    <summary>코드 가져가기</summary>
    <p class="hint">아래 코드를 복사해서 <code>index.html</code> 로 저장하면 이 페이지가 그대로 동작합니다. 입력 내용은 들어 있지 않습니다.</p>
    <textarea id="source" readonly rows="8" aria-label="페이지 코드">{html.escape(source)}</textarea>
    <div class="actions">
      <button type="button" id="copy-code">코드 복사</button>
      <button type="button" id="download-code" class="secondary">index.html 로 내려받기</button>
      {github_button}
    </div>
    <p id="code-msg" class="hint" role="status"></p>
  </details>"""


def _saved_html(save):
    """저장 목록 영역입니다. save 가 꺼져 있으면 아무것도 넣지 않습니다."""
    if not save:
        return ""
    return """
  <details id="saved-panel" class="saved-panel">
    <summary>이 기기에 저장된 신청 보기</summary>
    <p class="hint">이 기록은 이 브라우저에만 저장됩니다. 다른 기기와는 공유되지 않습니다.</p>
    <p id="saved-count" class="hint"></p>
    <div id="saved-list"></div>
    <div class="actions">
      <button type="button" id="download-csv" class="secondary">CSV 로 내려받기</button>
      <button type="button" id="clear-saved" class="secondary">저장 목록 모두 지우기</button>
    </div>
    <div class="actions">
      <button type="button" id="make-backup" class="secondary">백업 파일 만들기</button>
      <button type="button" id="share-backup" class="secondary">백업 파일 보내기</button>
      <button type="button" id="restore-backup" class="secondary">백업 파일 불러오기</button>
      <input type="file" id="restore-file" accept="application/json,.json" hidden>
    </div>
    <p class="hint">백업 파일은 이 기기의 기록을 모두 담은 파일입니다. 다른 기기에서 불러오면 기록이 합쳐집니다. 같은 기록은 한 번만 들어갑니다.</p>
    <p id="saved-msg" class="hint" role="status"></p>
  </details>"""


def _panel_js(github):
    return f"""
  const copyBtn = document.getElementById("copy-code");
  const source = document.getElementById("source");
  const codeMsg = document.getElementById("code-msg");
  const GITHUB = {_json_for_script(github)};

  copyBtn.addEventListener("click", async () => {{
    try {{
      await navigator.clipboard.writeText(source.value);
      codeMsg.textContent = "코드를 복사했습니다. index.html 파일에 붙여 넣어 저장하세요.";
    }} catch (err) {{
      source.focus();
      source.select();
      const ok = document.execCommand("copy");
      codeMsg.textContent = ok
        ? "코드를 복사했습니다. index.html 파일에 붙여 넣어 저장하세요."
        : "복사하지 못했습니다. 코드 상자를 눌러 직접 선택한 뒤 복사해 주세요.";
    }}
  }});

  document.getElementById("download-code").addEventListener("click", () => {{
    const blob = new Blob([source.value], {{ type: "text/html;charset=utf-8" }});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "index.html";
    link.click();
    URL.revokeObjectURL(link.href);
    codeMsg.textContent = "index.html 을 내려받았습니다. GitHub 에 올릴 때는 '파일 추가 → 파일 업로드'를 쓰세요.";
  }});

  const githubBtn = document.getElementById("github-link");
  if (githubBtn && GITHUB) {{
    githubBtn.addEventListener("click", () => {{
      const url = `https://github.com/${{GITHUB.repo}}/new/${{GITHUB.branch}}`
        + `?filename=${{encodeURIComponent(GITHUB.path)}}&value=${{encodeURIComponent(source.value)}}`;
      if (url.length > {GITHUB_LINK_LIMIT}) {{
        codeMsg.textContent = "코드가 길어 링크로 보낼 수 없습니다. '코드 복사'를 누른 뒤 GitHub 에서 붙여 넣어 주세요.";
        return;
      }}
      window.open(url, "_blank", "noopener");
      codeMsg.textContent = "GitHub 새 파일 화면을 열었습니다. 그 화면에서 Commit 을 눌러 저장하세요.";
    }});
  }}"""


def _saved_js(save):
    if not save:
        return ""
    return """
  const savedList = document.getElementById("saved-list");
  const savedCount = document.getElementById("saved-count");
  const savedMsg = document.getElementById("saved-msg");

  let recordNotice = "";

  function loadRecords() {
    let raw = null;
    try {
      raw = localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return [];
    }
    if (raw === null) return [];
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    } catch (err) { /* 아래에서 따로 보관합니다 */ }
    // 읽을 수 없는 기록은 지우지 않고 다른 칸에 그대로 보관한 뒤, 빈 목록으로 보여 줍니다.
    try {
      localStorage.setItem(STORAGE_KEY + ":broken:" + Date.now(), raw);
      localStorage.removeItem(STORAGE_KEY); // 같은 보관본이 반복해서 만들어지지 않도록 원래 칸을 비웁니다
      recordNotice = "저장된 기록을 읽을 수 없어 따로 보관했습니다. 새 신청은 정상적으로 저장됩니다.";
    } catch (err) {
      recordNotice = "저장된 기록을 읽을 수 없고 보관도 되지 않았습니다. 백업 파일을 먼저 받아 두세요.";
    }
    return [];
  }

  function storeRecords(records) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
      return true;
    } catch (err) {
      return false;
    }
  }

  function renderRecords() {
    const records = loadRecords();
    savedCount.textContent = `저장된 신청 ${records.length}건`;
    if (recordNotice) savedMsg.textContent = recordNotice;
    const table = document.createElement("table");
    const head = document.createElement("tr");
    for (const text of ["저장 시각", ...FIELDS.map((f) => f.label)]) {
      const th = document.createElement("th");
      th.textContent = text;
      head.append(th);
    }
    table.append(head);
    for (const record of records) {
      const tr = document.createElement("tr");
      for (const text of [formatTime(record.at), ...FIELDS.map((f) => record.data[f.id] || "-")]) {
        const td = document.createElement("td");
        td.textContent = text;
        tr.append(td);
      }
      table.append(tr);
    }
    savedList.replaceChildren(table);
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("ko-KR");
  }

  function saveRecord() {
    const records = loadRecords();
    records.push({ at: new Date().toISOString(), data: currentRecord() });
    savedMsg.textContent = storeRecords(records)
      ? "이 기기에 저장했습니다."
      : "이 브라우저에서는 저장할 수 없습니다. CSV 로 내려받아 보관해 주세요.";
    renderRecords();
  }

  function csvCell(value) {
    let text = String(value ?? "");
    if (/^[=+\\-@]/.test(text)) text = "'" + text;
    return `"${text.replace(/"/g, '""')}"`;
  }

  document.getElementById("download-csv").addEventListener("click", () => {
    const records = loadRecords();
    const header = ["저장 시각", ...FIELDS.map((f) => f.label)].map(csvCell).join(",");
    const rows = records.map((r) => [r.at, ...FIELDS.map((f) => r.data[f.id] || "")].map(csvCell).join(","));
    const blob = new Blob(["\\uFEFF" + [header, ...rows].join("\\r\\n")], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "신청목록.csv";
    link.click();
    URL.revokeObjectURL(link.href);
    savedMsg.textContent = `${records.length}건을 내려받았습니다.`;
  });

  document.getElementById("clear-saved").addEventListener("click", () => {
    if (!confirm("이 기기에 저장된 신청 기록을 모두 지울까요? 되돌릴 수 없습니다.")) return;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (err) { /* 저장소를 쓸 수 없으면 지울 것도 없습니다 */ }
    savedMsg.textContent = "저장 목록을 지웠습니다.";
    renderRecords();
  });

  function backupFile() {
    const text = JSON.stringify({
      format: "vibe-app-backup",
      version: 1,
      app: APP_NAME,
      exportedAt: new Date().toISOString(),
      records: loadRecords(),
    }, null, 2);
    const name = `${APP_NAME}-백업-${new Date().toISOString().slice(0, 10)}.json`;
    return new File([text], name, { type: "application/json" });
  }

  document.getElementById("make-backup").addEventListener("click", () => {
    const file = backupFile();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(file);
    link.download = file.name;
    link.click();
    URL.revokeObjectURL(link.href);
    savedMsg.textContent = "백업 파일을 내려받았습니다. 이 파일을 보내거나 다른 기기에서 불러오세요.";
  });

  document.getElementById("share-backup").addEventListener("click", async () => {
    const file = backupFile();
    if (!navigator.canShare || !navigator.canShare({ files: [file] })) {
      savedMsg.textContent = "이 브라우저에서는 바로 보내기를 쓸 수 없습니다. '백업 파일 만들기'로 받은 뒤 직접 보내 주세요.";
      return;
    }
    try {
      await navigator.share({ files: [file], title: file.name });
      savedMsg.textContent = "백업 파일을 보냈습니다.";
    } catch (err) {
      if (err && err.name === "AbortError") return; // 사용자가 보내기를 취소한 경우
      savedMsg.textContent = "보내지 못했습니다. '백업 파일 만들기'로 받은 뒤 직접 보내 주세요.";
    }
  });

  document.getElementById("restore-backup").addEventListener("click", () => {
    document.getElementById("restore-file").click();
  });

  document.getElementById("restore-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      savedMsg.textContent = "백업 파일이 너무 큽니다. 2MB 이하의 백업 파일만 불러올 수 있습니다.";
      return;
    }
    let backup = null;
    try {
      backup = JSON.parse(await file.text());
    } catch (err) {
      savedMsg.textContent = "백업 파일을 읽을 수 없습니다. 이 페이지에서 만든 백업 파일인지 확인해 주세요.";
      return;
    }
    if (!backup || backup.format !== "vibe-app-backup" || !Array.isArray(backup.records)) {
      savedMsg.textContent = "이 페이지의 백업 파일이 아닙니다.";
      return;
    }
    if (backup.records.length > 5000) {
      savedMsg.textContent = "백업 파일의 기록이 5,000건을 넘습니다. 나누어 불러와 주세요.";
      return;
    }
    const current = loadRecords();
    const seen = new Set(current.map((r) => r.at + JSON.stringify(r.data)));
    let added = 0;
    for (const r of backup.records) {
      if (!r || typeof r.at !== "string" || !r.data || typeof r.data !== "object") continue;
      const key = r.at + JSON.stringify(r.data);
      if (seen.has(key)) continue;
      seen.add(key);
      current.push({ at: r.at, data: r.data });
      added++;
    }
    const note = backup.app && backup.app !== APP_NAME ? " (다른 신청 페이지의 백업입니다)" : "";
    savedMsg.textContent = storeRecords(current)
      ? `${added}건을 불러와 합쳤습니다.${note}`
      : "이 브라우저에서는 저장할 수 없어 불러오지 못했습니다.";
    renderRecords();
  });

  renderRecords();"""


def _render(spec, panel_source=None, github=None):
    """명세를 HTML 문서로 바꿉니다. panel_source 가 있으면 코드 가져가기 영역을 함께 넣습니다."""
    pages = spec["pages"]
    input_pages = [p for p in pages if _is_input_page(p)]
    done_pages = [p for p in pages if not _is_input_page(p)]
    done_title = done_pages[0]["name"] if done_pages else "제출 완료"
    save = bool(spec.get("save"))

    configs_by_step = []
    all_configs = []
    counter = 0
    for step, page in enumerate(input_pages):
        step_configs = []
        for field in page["fields"]:
            counter += 1
            config = _field_config(field, counter, step)
            step_configs.append(config)
            all_configs.append(config)
        configs_by_step.append(step_configs)

    steps = [{"name": p["name"], "fieldIds": [c["id"] for c in configs_by_step[i]]} for i, p in enumerate(input_pages)]
    rules = unenforced_rules(spec)
    rules_items = "".join(f"<li>{html.escape(r)}</li>" for r in rules)
    rules_block = f'<ul class="rules">{rules_items}</ul>' if rules_items else ""

    title = html.escape(spec["name"])
    goal = html.escape(spec["goal"].strip())
    steps_html = _steps_html(input_pages, configs_by_step)

    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]

    panel_css = _panel_css() if panel_source is not None else ""
    panel_block = _panel_html(panel_source, github) if panel_source is not None else ""
    panel_script = _panel_js(github) if panel_source is not None else ""
    saved_block = _saved_html(save)
    saved_script = _saved_js(save)

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
    h2.step-title {{ font-size: 1.15rem; margin: 8px 0 12px; }}
    .goal {{ color: var(--muted); margin: 0 0 16px; }}
    .field {{ margin-bottom: 14px; }}
    label {{ display: block; font-weight: 600; margin-bottom: 4px; }}
    input:not([type=radio]):not([type=checkbox]), select, textarea {{ width: 100%; padding: 9px; font: inherit; border: 1px solid #94a3b8; border-radius: 6px; background: #ffffff; color: #0f172a; }}
    input:focus, select:focus, textarea:focus, button:focus-visible, summary:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; }}
    .err {{ color: var(--err); font-size: 0.9rem; margin: 4px 0 0; min-height: 0; }}
    .err:empty {{ display: none; }}
    button {{ padding: 10px 18px; font: inherit; font-weight: 700; border: 0; border-radius: 6px; background: var(--accent); color: #ffffff; cursor: pointer; }}
    .rules {{ color: var(--muted); font-size: 0.9rem; padding-left: 18px; }}
    dl {{ margin: 12px 0; }}
    dt {{ font-weight: 600; margin-top: 8px; }}
    dd {{ margin: 2px 0 0 0; }}
    [hidden] {{ display: none !important; }}{panel_css}
  </style>
</head>
<body>
<main>
  <section id="form-view">
    <h1>{title}</h1>
    <p class="goal">{goal}</p>
    <form id="form" novalidate>
    {steps_html}
    </form>
    {rules_block}
  </section>

  <section id="done-view" hidden>
    <h1>{html.escape(done_title)}</h1>
    <p class="goal">제출되었습니다. 입력한 내용은 화면에서만 보입니다.</p>
    <dl id="summary"></dl>
    <button type="button" id="again">다시 입력</button>
  </section>
  {saved_block}
  {panel_block}
</main>

<script>
  const FIELDS = {_json_for_script(all_configs)};
  const STEPS = {_json_for_script(steps)};
  const STORAGE_KEY = {_json_for_script("vibe-app:" + spec_hash)};
  const APP_NAME = {_json_for_script(spec["name"])};
  const form = document.getElementById("form");
  const EMAIL = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
  const PHONE = /^[0-9+\\-() ]{{7,20}}$/;
  const URL_PATTERN = /^https?:\\/\\/\\S+$/;
  const TIME = /^\\d{{2}}:\\d{{2}}$/;
  const DATE = /^\\d{{4}}-\\d{{2}}-\\d{{2}}$/;
  let current = 0;

  function todayIso() {{
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${{d.getFullYear()}}-${{pad(d.getMonth() + 1)}}-${{pad(d.getDate())}}`;
  }}

  function valueOf(field) {{
    if (field.type === "radio") {{
      const checked = document.querySelector(`input[name="${{field.id}}"]:checked`);
      return checked ? checked.value : "";
    }}
    if (field.type === "checkbox") return document.getElementById(field.id).checked ? "예" : "";
    return document.getElementById(field.id).value;
  }}

  function displayOf(field) {{
    const value = valueOf(field);
    if (field.type === "checkbox") return value || "아니오";
    return value.trim() || "-";
  }}

  function messageFor(field, raw) {{
    if (field.type === "checkbox") {{
      return field.required && !raw ? "동의해야 진행할 수 있습니다." : "";
    }}
    const value = String(raw).trim();
    if (!value) return field.required ? "필수 입력입니다." : "";
    if (field.minLength !== null && value.length < field.minLength) return `${{field.minLength}}자 이상 입력해 주세요.`;
    if (field.maxLength !== null && value.length > field.maxLength) return `${{field.maxLength}}자 이하로 입력해 주세요.`;
    if (field.type === "email" && !EMAIL.test(value)) return "이메일 형식이 올바르지 않습니다.";
    if (field.type === "phone" && !PHONE.test(value)) return "전화번호 형식이 올바르지 않습니다. 숫자와 하이픈을 사용해 주세요.";
    if (field.type === "url" && !URL_PATTERN.test(value)) return "https:// 로 시작하는 주소를 입력해 주세요.";
    if (field.type === "time" && !TIME.test(value)) return "시간은 HH:MM 형식으로 입력해 주세요.";
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

  function focusTarget(field) {{
    if (field.type === "radio") return document.querySelector(`input[name="${{field.id}}"]`);
    return document.getElementById(field.id);
  }}

  // 단계의 입력칸을 검사하고, 첫 번째 잘못된 칸을 돌려줍니다.
  function validateStep(index) {{
    let firstInvalid = null;
    for (const id of STEPS[index].fieldIds) {{
      const field = FIELDS.find((f) => f.id === id);
      const message = messageFor(field, field.type === "checkbox" ? document.getElementById(id).checked : valueOf(field));
      document.getElementById(id + "-err").textContent = message;
      if (message && !firstInvalid) firstInvalid = focusTarget(field);
    }}
    return firstInvalid;
  }}

  function showStep(index) {{
    current = index;
    document.querySelectorAll(".step").forEach((el) => {{ el.hidden = Number(el.dataset.step) !== index; }});
  }}

  document.querySelectorAll(".next").forEach((btn) => btn.addEventListener("click", () => {{
    const bad = validateStep(current);
    if (bad) {{ bad.focus(); return; }}
    showStep(current + 1);
  }}));
  document.querySelectorAll(".prev").forEach((btn) => btn.addEventListener("click", () => showStep(current - 1)));

  form.addEventListener("submit", (event) => {{
    event.preventDefault();
    // Enter 키로 제출해도 마지막 단계가 아니면 다음 단계로 갑니다.
    if (current < STEPS.length - 1) {{
      const bad = validateStep(current);
      if (bad) {{ bad.focus(); return; }}
      showStep(current + 1);
      return;
    }}
    for (let i = 0; i < STEPS.length; i++) {{
      const bad = validateStep(i);
      if (bad) {{ showStep(i); bad.focus(); return; }}
    }}
    saveIfEnabled();
    showSummary();
  }});

  function currentRecord() {{
    const data = {{}};
    for (const f of FIELDS) data[f.id] = valueOf(f);
    return data;
  }}

  function saveIfEnabled() {{
    if (typeof saveRecord === "function") saveRecord();
  }}

  function showSummary() {{
    const summary = document.getElementById("summary");
    summary.replaceChildren();
    for (const field of FIELDS) {{
      const dt = document.createElement("dt");
      dt.textContent = field.label;
      const dd = document.createElement("dd");
      dd.textContent = displayOf(field);
      summary.append(dt, dd);
    }}
    document.getElementById("form-view").hidden = true;
    document.getElementById("done-view").hidden = false;
  }}

  document.getElementById("again").addEventListener("click", () => {{
    form.reset();
    document.querySelectorAll(".err").forEach((el) => {{ el.textContent = ""; }});
    document.getElementById("done-view").hidden = true;
    document.getElementById("form-view").hidden = false;
    showStep(0);
  }});
{saved_script}
{panel_script}

  showStep(0);
</script>
</body>
</html>
"""


def build_html(spec, github=None):
    """검사를 통과한 명세로 index.html 문서를 만듭니다.

    복사되는 코드는 코드 가져가기 영역을 뺀 페이지입니다. 그 코드만으로도 그대로 동작합니다.
    """
    plain = _render(spec)
    return _render(spec, panel_source=plain, github=github)


def main(argv=None):
    parser = argparse.ArgumentParser(description="명세로 바로 동작하는 index.html 만들기")
    parser.add_argument("spec", type=Path, help="명세 JSON 파일")
    parser.add_argument("--out", type=Path, default=Path("index.html"), help="만들 HTML 경로")
    parser.add_argument("--github", help="GitHub 저장소 (아이디/저장소). 주면 GitHub 새 파일 버튼이 생깁니다.")
    parser.add_argument("--branch", default="main", help="GitHub 에서 저장할 브랜치 (기본: main)")
    parser.add_argument("--path", default="index.html", help="GitHub 저장소 안의 파일 경로 (기본: index.html)")
    args = parser.parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    errors = validate_spec(spec) + validate_structure(spec)
    try:
        github = validate_github(args.github, args.branch, args.path)
    except ValueError as e:
        errors.append(str(e))
        github = None
    if errors:
        print("명세를 고쳐 주세요:")
        for e in errors:
            print(f"- {e}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_html(spec, github), encoding="utf-8")
    print(f"페이지 생성 완료: {args.out}")

    rules = unenforced_rules(spec)
    if rules:
        print("명세의 규칙은 안내 문구로만 들어갑니다. 입력칸 설정(필수, 형식, min, max, minToday, minLength, maxLength)으로 막히는지 확인해 주세요:")
        for r in rules:
            print(f"- {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
