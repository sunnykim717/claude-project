(function () {
  "use strict";
  var STORAGE_KEY = "website-editor:v1";
  var KEY_FILES = {
    site: "config/site.json", nav: "config/navigation.json", theme: "config/theme.json",
    home: "content/home.json", about: "content/about.json", projects: "content/projects.json",
    support: "content/support.json", news: "content/news.json", contact: "content/contact.json"
  };
  var THEME_KEYS = ["primaryColor", "backgroundColor", "textColor", "font", "radius", "spacing", "layout"];
  var PATH_HELP = [
    "site.name / site.description / site.language (ko, en, ja)",
    "theme.primaryColor / theme.backgroundColor / theme.textColor (#RRGGBB), theme.font (system-ui, serif, mono), theme.radius (0~32), theme.spacing (compact, normal, airy), theme.layout (classic, modern, card, minimal)",
    "home.hero.title / home.hero.subtitle / home.hero.buttonText / home.hero.buttonLink, home.intro",
    "about.title / about.body",
    "support.title / support.body / support.notice, support.ways.번호.title / .summary",
    "news.title, news.items.번호.title / .date / .summary / .url",
    "projects.title, projects.items.번호.title / .date / .summary / .url",
    "contact.title / contact.body / contact.email, contact.social.github / .instagram / .youtube",
    "nav.번호.label / nav.번호.path (/, /about, /projects, /contact)"
  ];
  var EXAMPLES = [
    "set site.name 민수의 작업실",
    "set support.notice 기부금 영수증 발급 방법을 적어 주세요.",
    "set home.hero.title 더 나은 내일을 만듭니다",
    "set about.body 기관의 목적과 활동을 적어 주세요.",
    "set contact.email hello@example.com",
    "design warm-orange",
    "add-project 빌더 공개 | 2026-11-03 | 주민 여러분을 초대합니다 | https://example.com",
    "remove-project 1",
    "check"
  ];

  var files = loadFiles();
  var currentPage = "index.html";

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function loadFiles() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && typeof saved === "object") return Object.assign(clone(DEFAULT_FILES), saved);
    } catch (e) { /* 저장된 값을 쓸 수 없으면 처음 상태를 씁니다 */ }
    return clone(DEFAULT_FILES);
  }

  function persist() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(files)); } catch (e) { /* 저장을 못 해도 화면은 동작합니다 */ }
  }

  function say(text, ok) {
    var log = document.getElementById("log");
    log.textContent = text;
    log.className = "log " + (ok === undefined ? "" : ok ? "ok" : "err");
  }

  // 'site.name' 같은 경로를 파일과 항목으로 나눕니다.
  function locate(path) {
    var parts = String(path).split(".");
    var key = parts[0];
    if (!KEY_FILES[key] || parts.length < 2) return null;
    return { file: KEY_FILES[key], keys: parts.slice(1) };
  }

  function parseValue(text) {
    var t = text.trim();
    if (/^(\{|\[|"|-?\d|true$|false$|null$)/.test(t)) {
      try { return JSON.parse(t); } catch (e) { /* 글자로 취급합니다 */ }
    }
    return t;
  }

  function setValue(target, path, value) {
    var parts = path.slice();
    var node = target;
    for (var i = 0; i < parts.length - 1; i++) {
      var step = Array.isArray(node) ? Number(parts[i]) : parts[i];
      if (node[step] === undefined) throw new Error("항목을 찾지 못했습니다: " + parts.slice(0, i + 1).join("."));
      node = node[step];
    }
    var last = parts[parts.length - 1];
    if (Array.isArray(node)) {
      var index = Number(last);
      if (!Number.isInteger(index) || index < 0 || index >= node.length) throw new Error("번호가 맞지 않습니다: " + last);
      node[index] = value;
    } else {
      if (node === null || typeof node !== "object") throw new Error("이 항목에는 값을 넣을 수 없습니다.");
      node[last] = value;
    }
  }

  function validateCurrent() {
    return SiteEngine.validate(files).errors;
  }

  // 바꾼 뒤 검사합니다. 틀리면 바꾸기 전 상태로 되돌립니다.
  function commit(mutator, successText) {
    var before = clone(files);
    try {
      mutator(files);
    } catch (e) {
      files = before;
      return say(e.message, false);
    }
    var errors = validateCurrent();
    if (errors.length) {
      files = before;
      return say("저장하지 않았습니다. 다음을 고쳐 주세요:\n- " + errors.join("\n- "), false);
    }
    persist();
    render();
    if (successText) say(successText, true);
  }

  function setCommand(path, rawValue) {
    var loc = locate(path);
    if (!loc) return say("경로는 site, theme, nav, home, about, projects, contact 로 시작해야 합니다.", false);
    commit(function (f) {
      var data = JSON.parse(f[loc.file]);
      setValue(data, loc.keys, parseValue(rawValue));
      f[loc.file] = JSON.stringify(data, null, 2) + "\n";
    }, path + " 을(를) 바꾸고 저장했습니다.");
  }

  function applyDesign(name) {
    if (!DESIGNS[name]) return say("디자인은 " + Object.keys(DESIGNS).join(", ") + " 중 하나여야 합니다.", false);
    commit(function (f) {
      var theme = JSON.parse(f[KEY_FILES.theme]);
      THEME_KEYS.forEach(function (k) { theme[k] = DESIGNS[name][k]; });
      f[KEY_FILES.theme] = JSON.stringify(theme, null, 2) + "\n";
    }, "디자인 '" + DESIGNS[name].label + "' 을 적용했습니다.");
  }

  function addProject(text) {
    var parts = text.split("|").map(function (p) { return p.trim(); }).filter(Boolean);
    var item = { title: "", date: "", summary: "", url: "" };
    var extra = [];
    parts.forEach(function (part) {
      if (/^https?:\/\//.test(part)) item.url = part;
      else if (/^\d{4}-\d{2}-\d{2}$/.test(part)) item.date = part;
      else if (!item.title) item.title = part;
      else extra.push(part);
    });
    item.summary = extra.join(" ");
    if (!item.title) return say("사업 이름을 적어 주세요. 예: add-project 빌더 공개 | 2026-11-03 | 요약 | https://...", false);
    commit(function (f) {
      var data = JSON.parse(f[KEY_FILES.projects]);
      data.items.push(item);
      f[KEY_FILES.projects] = JSON.stringify(data, null, 2) + "\n";
    }, "사업 '" + item.title + "' 을 추가했습니다.");
  }

  function removeProject(text) {
    var index = Number(text.trim()) - 1;
    commit(function (f) {
      var data = JSON.parse(f[KEY_FILES.projects]);
      if (!Number.isInteger(index) || index < 0 || index >= data.items.length) throw new Error("번호가 맞지 않습니다. 1부터 " + data.items.length + " 사이여야 합니다.");
      var removed = data.items.splice(index, 1)[0];
      f[KEY_FILES.projects] = JSON.stringify(data, null, 2) + "\n";
      say("사업 '" + removed.title + "' 을 지웠습니다.", true);
    }, "");
  }

  function runCommand(line) {
    var text = line.trim();
    if (!text) return say("명령을 적어 주세요. 도움말을 누르면 명령 목록을 볼 수 있습니다.", false);
    var space = text.indexOf(" ");
    var word = space === -1 ? text : text.slice(0, space);
    var rest = space === -1 ? "" : text.slice(space + 1).trim();
    if (word === "set") {
      var sp = rest.indexOf(" ");
      if (sp === -1) return say("사용법: set 경로 값   예: set site.name 민수의 작업실", false);
      return setCommand(rest.slice(0, sp), rest.slice(sp + 1));
    }
    if (word === "design") return applyDesign(rest);
    if (word === "designs") return say(Object.keys(DESIGNS).map(function (k) { return k + " : " + DESIGNS[k].label; }).join("\n"), true);
    if (word === "add-project") return addProject(rest);
    if (word === "remove-project") return removeProject(rest);
    if (word === "check") {
      var errors = validateCurrent();
      return errors.length ? say("다음을 고쳐 주세요:\n- " + errors.join("\n- "), false) : say("검사 통과: 설정과 콘텐츠가 맞습니다.", true);
    }
    if (word === "help" || word === "도움말") return say("명령 목록:\n" + [
      "set 경로 값  - 값 바꾸기 (검사 후 저장)",
      "design 이름  - 디자인 적용 (" + Object.keys(DESIGNS).join(", ") + ")",
      "designs      - 디자인 목록",
      "add-project 이름 | 날짜 | 요약 | 링크  - 사업 추가",
      "remove-project 번호  - 사업 삭제",
      "check        - 검사",
      "",
      "바꿀 수 있는 경로:",
      PATH_HELP.join("\n")
    ].join("\n"), true);
    return say("알 수 없는 명령입니다: " + word + "\n도움말을 누르면 명령 목록을 볼 수 있습니다.", false);
  }

  function render() {
    var result = SiteEngine.build(files);
    var frame = document.getElementById("frame");
    if (result.ok) {
      frame.srcdoc = result.pages[currentPage] || result.pages["index.html"];
    } else {
      frame.srcdoc = "<p style='font-family:system-ui;padding:16px;color:#b91c1c'>설정에 오류가 있어 미리보기를 만들 수 없습니다. 아래 '검사' 명령으로 확인해 주세요.</p>";
    }
    var downloads = document.getElementById("downloads");
    downloads.replaceChildren();
    if (result.ok) {
      Object.keys(result.pages).sort().forEach(function (name) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "secondary";
        btn.textContent = name + " 받기";
        btn.addEventListener("click", function () { download(name, result.pages[name], "text/html;charset=utf-8"); });
        downloads.append(btn);
      });
    }
  }

  function download(name, text, type) {
    var blob = new Blob([text], { type: type });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function init() {
    var examples = document.getElementById("examples");
    EXAMPLES.forEach(function (cmd) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "secondary";
      btn.textContent = cmd;
      btn.addEventListener("click", function () { document.getElementById("command").value = cmd; });
      examples.append(btn);
    });

    var select = document.getElementById("design-select");
    Object.keys(DESIGNS).forEach(function (k) {
      var opt = document.createElement("option");
      opt.value = k;
      opt.textContent = DESIGNS[k].label;
      select.append(opt);
    });
    document.getElementById("btn-design").addEventListener("click", function () { applyDesign(select.value); });

    var pageSelect = document.getElementById("page-select");
    ["index.html", "about.html", "projects.html", "contact.html"].forEach(function (name) {
      var opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      pageSelect.append(opt);
    });
    pageSelect.addEventListener("change", function () { currentPage = pageSelect.value; render(); });

    var command = document.getElementById("command");
    document.getElementById("btn-run").addEventListener("click", function () { runCommand(command.value); render(); });
    command.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runCommand(command.value);
        render();
      }
    });
    document.getElementById("btn-help").addEventListener("click", function () { runCommand("help"); });

    document.getElementById("btn-export").addEventListener("click", function () {
      download("홈페이지-설정.json", JSON.stringify(files, null, 2), "application/json;charset=utf-8");
    });
    document.getElementById("btn-import").addEventListener("click", function () { document.getElementById("file-import").click(); });
    document.getElementById("file-import").addEventListener("change", function (event) {
      var file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var loaded = JSON.parse(reader.result);
          var merged = Object.assign(clone(DEFAULT_FILES), loaded);
          if (!SiteEngine.validate(merged).errors.length) {
            files = merged;
            persist();
            render();
            say("설정을 불러왔습니다.", true);
          } else {
            say("이 파일은 홈페이지 설정이 아니거나 오류가 있습니다.", false);
          }
        } catch (e) {
          say("파일을 읽을 수 없습니다. 이 편집기에서 저장한 설정 파일인지 확인해 주세요.", false);
        }
      };
      reader.readAsText(file);
    });
    document.getElementById("btn-reset").addEventListener("click", function () {
      if (!confirm("지금까지 고친 내용을 모두 지우고 처음 상태로 되돌릴까요?")) return;
      files = clone(DEFAULT_FILES);
      persist();
      render();
      say("처음 상태로 되돌렸습니다.", true);
    });

    render();
  }

  init();
})();
