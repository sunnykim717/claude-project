(function () {
  "use strict";
  SiteEngine.useSchema(SCHEMA);
  var STORAGE_KEY = "website-editor:v1";
  var KEY_FILES = SCHEMA.files;
  var THEME_KEYS = SCHEMA.theme_keys;
  var PATH_HELP = SCHEMA.help;
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

  // 저장이 안 되면 false 를 돌려줍니다 (사진이 많으면 브라우저 저장 공간이 찹니다).
  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(files));
      return true;
    } catch (e) {
      return false;
    }
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
    var saved = persist();
    render();
    if (!saved) return say("저장 공간이 부족해 브라우저에 저장하지 못했습니다. 설정 저장(파일)으로 보관해 주세요.", false);
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

  // 메뉴 추가: add-menu 이름 | /주소
  function addMenu(text) {
    var parts = text.split("|").map(function (p) { return p.trim(); }).filter(Boolean);
    if (parts.length < 2) return say("사용법: add-menu 메뉴이름 | /주소   예: add-menu 오시는 길 | /location", false);
    var path = parts[1];
    if (!SCHEMA.pages[path]) return say("주소는 " + Object.keys(SCHEMA.pages).join(", ") + " 중 하나여야 합니다.", false);
    commit(function (f) {
      var nav = JSON.parse(f[KEY_FILES.nav]);
      nav.push({ label: parts[0], path: path });
      f[KEY_FILES.nav] = JSON.stringify(nav, null, 2) + "\n";
    }, "메뉴 '" + parts[0] + "' 을 추가했습니다.");
  }

  // 메뉴 삭제: remove-menu 번호 (메뉴 순서대로 1부터)
  function removeMenu(text) {
    var index = Number(text.trim()) - 1;
    commit(function (f) {
      var nav = JSON.parse(f[KEY_FILES.nav]);
      if (!Number.isInteger(index) || index < 0 || index >= nav.length) throw new Error("번호가 맞지 않습니다. 1부터 " + nav.length + " 사이여야 합니다.");
      var removed = nav.splice(index, 1)[0];
      f[KEY_FILES.nav] = JSON.stringify(nav, null, 2) + "\n";
      say("메뉴 '" + removed.label + "' 을 뺐습니다.", true);
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
    if (word === "add-menu") return addMenu(rest);
    if (word === "remove-menu") return removeMenu(rest);
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
      "add-menu 이름 | /주소  - 메뉴 추가 (예: add-menu 오시는 길 | /location)",
      "remove-menu 번호  - 메뉴 삭제",
      "check        - 검사",
      "",
      "바꿀 수 있는 경로:",
      PATH_HELP.join("\n")
    ].join("\n"), true);
    return say("알 수 없는 명령입니다: " + word + "\n도움말을 누르면 명령 목록을 볼 수 있습니다.", false);
  }

  function render() {
    refreshPhotoStatus();
    refreshCustomCss();
    var result = SiteEngine.build(files);
    var frame = document.getElementById("frame");
    if (result.ok) {
      var html = result.pages[currentPage] || result.pages["index.html"];
      Object.keys(files).forEach(function (name) {
        if (name.indexOf("public/images/") === 0) html = html.split('"' + name + '"').join('"' + files[name] + '"');
      });
      frame.srcdoc = html;
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

  // 사진을 1200px 이하로 줄여 JPEG 데이터로 바꿉니다 (브라우저 안에서만 처리).
  function shrinkPhoto(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        var scale = Math.min(1, 1200 / img.width);
        var canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error("사진을 읽을 수 없습니다.")); };
      img.src = url;
    });
  }

  function bytesOf(dataUrl) {
    var binary = atob(dataUrl.split(",")[1]);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  // 사진을 넣을 곳. 로고와 배경은 설정 파일에, 첫 화면 사진은 home.hero 안에, 나머지 페이지 사진은 페이지 맨 위에 둡니다.
  var PAGE_LABELS = SCHEMA.page_labels;
  var PHOTO_TARGETS = {
    logo: { label: "로고", file: "site", field: "logo" },
    background: { label: "배경", file: "theme", field: "backgroundImage" },
    home: { label: "첫 화면", file: "home", hero: true, field: "image" }
  };
  SCHEMA.photo_pages.forEach(function (key) {
    PHOTO_TARGETS[key] = { label: PAGE_LABELS[key], file: key, field: "image" };
  });
  var PHOTO_ORDER = ["logo", "background", "home"].concat(SCHEMA.photo_pages);

  function slotOf(data, target) {
    if (!target.hero) return data;
    data.hero = data.hero || {};
    return data.hero;
  }

  function imageOf(f, key) {
    var target = PHOTO_TARGETS[key];
    return slotOf(JSON.parse(f[KEY_FILES[target.file]]), target)[target.field] || "";
  }

  function writeImage(f, key, image) {
    var target = PHOTO_TARGETS[key];
    var data = JSON.parse(f[KEY_FILES[target.file]]);
    var slot = slotOf(data, target);
    if (image) slot[target.field] = image;
    else delete slot[target.field];
    f[KEY_FILES[target.file]] = JSON.stringify(data, null, 2) + "\n";
  }

  // 이 사진을 쓰는 곳이 더 없으면 사진 파일도 지웁니다 (로고, 배경, 페이지 사진, 갤러리 모두 확인).
  function dropUnusedImage(f, image) {
    if (!image) return;
    var used = Object.keys(PHOTO_TARGETS).some(function (key) { return imageOf(f, key) === image; }) ||
      SCHEMA.photo_pages.some(function (key) {
        return galleryOf(f, key).some(function (item) { return item.image === image; });
      });
    if (!used) delete f["public/" + image.replace(/^\/+/, "")];
  }

  function setPhoto(key, file) {
    if (file.size > 10 * 1024 * 1024) return say("사진이 너무 큽니다. 10MB 이하의 사진을 골라 주세요.", false);
    shrinkPhoto(file).then(function (dataUrl) {
      var name = "photo-" + Date.now() + ".jpg";
      var old = imageOf(files, key);
      commit(function (f) {
        f["public/images/" + name] = dataUrl;
        writeImage(f, key, "/images/" + name);
        dropUnusedImage(f, old);
      }, PHOTO_TARGETS[key].label + " 사진을 바꿨습니다.");
    }, function (e) { say(e.message, false); });
  }

  function removePhoto(key) {
    var old = imageOf(files, key);
    if (!old) return say(PHOTO_TARGETS[key].label + " 에는 사진이 없습니다.", false);
    commit(function (f) {
      writeImage(f, key, "");
      dropUnusedImage(f, old);
    }, PHOTO_TARGETS[key].label + " 사진을 뺐습니다.");
  }

  function refreshPhotoStatus() {
    var select = document.getElementById("photo-page");
    if (!select.value) return;
    var image = imageOf(files, select.value);
    document.getElementById("photo-status").textContent = image ? "현재 사진: " + image.replace("/images/", "") : "사진 없음";
    refreshGallery();
  }

  // 갤러리: 페이지마다 사진을 여러 장 넣습니다.
  function galleryOf(f, key) {
    var data = JSON.parse(f[KEY_FILES[key]]);
    return Array.isArray(data.gallery) ? data.gallery : [];
  }

  function writeGallery(f, key, list) {
    var data = JSON.parse(f[KEY_FILES[key]]);
    if (list.length) data.gallery = list;
    else delete data.gallery;
    f[KEY_FILES[key]] = JSON.stringify(data, null, 2) + "\n";
  }

  function addGalleryPhotos(key, picked) {
    var max = SCHEMA.gallery_max;
    if (galleryOf(files, key).length + picked.length > max) return say("갤러리는 " + max + "장까지 넣을 수 있습니다.", false);
    if (picked.some(function (file) { return file.size > 10 * 1024 * 1024; })) return say("사진이 너무 큽니다. 한 장당 10MB 이하로 골라 주세요.", false);
    var urls = picked.reduce(function (chain, file) {
      return chain.then(function (done) {
        return shrinkPhoto(file).then(function (dataUrl) { done.push(dataUrl); return done; });
      });
    }, Promise.resolve([]));
    urls.then(function (dataUrls) {
      var stamp = Date.now();
      commit(function (f) {
        var list = galleryOf(f, key).slice();
        dataUrls.forEach(function (dataUrl, i) {
          var name = "gallery-" + stamp + "-" + i + ".jpg";
          f["public/images/" + name] = dataUrl;
          list.push({ image: "/images/" + name, alt: "" });
        });
        writeGallery(f, key, list);
      }, PHOTO_TARGETS[key].label + " 갤러리에 " + dataUrls.length + "장을 더했습니다.");
    }, function (e) { say(e.message, false); });
  }

  function removeGalleryPhoto(key, index) {
    var old = galleryOf(files, key)[index];
    if (!old) return;
    commit(function (f) {
      var next = galleryOf(f, key).slice();
      next.splice(index, 1);
      writeGallery(f, key, next);
      dropUnusedImage(f, old.image);
    }, PHOTO_TARGETS[key].label + " 갤러리 사진을 뺐습니다.");
  }

  function refreshGallery() {
    var box = document.getElementById("gallery-list");
    var key = document.getElementById("photo-page").value;
    box.replaceChildren();
    if (SCHEMA.photo_pages.indexOf(key) === -1) {
      box.textContent = "갤러리는 소개, 사업, 후원 같은 페이지에서 쓸 수 있습니다.";
      return;
    }
    var list = galleryOf(files, key);
    if (!list.length) box.textContent = "갤러리 사진이 없습니다.";
    list.forEach(function (item, index) {
      var row = document.createElement("div");
      row.className = "gallery-row";
      var thumb = document.createElement("img");
      thumb.src = files["public/" + item.image.replace(/^\/+/, "")] || "";
      thumb.width = 56;
      thumb.alt = "";
      var label = document.createElement("span");
      label.textContent = (index + 1) + "번";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "빼기";
      button.addEventListener("click", function () { removeGalleryPhoto(key, index); });
      row.append(thumb, label, button);
      box.append(row);
    });
  }

  // 직접 쓰는 CSS 칸. 입력 중에는 덮어쓰지 않습니다.
  function refreshCustomCss() {
    var box = document.getElementById("custom-css");
    if (document.activeElement !== box) box.value = files["config/custom.css"] || "";
  }

  function setCustomCss() {
    var text = document.getElementById("custom-css").value;
    commit(function (f) { f["config/custom.css"] = text; }, "직접 쓰는 CSS 를 적용했습니다.");
  }

  // 저장소 루트에 그대로 풀 수 있는 폴더 구조로 zip 을 만듭니다.
  function projectEntries() {
    var result = SiteEngine.build(files);
    if (!result.ok) return null;
    var entries = {};
    Object.keys(PROJECT_EXTRA).forEach(function (name) { entries[name] = PROJECT_EXTRA[name]; });
    Object.keys(files).forEach(function (name) { entries[name] = files[name]; });
    Object.keys(result.pages).forEach(function (name) { entries["dist/" + name] = result.pages[name]; });
    Object.keys(files).forEach(function (name) {
      if (name.indexOf("public/images/") === 0) entries["dist/" + name] = files[name];
    });
    return entries;
  }

  function downloadProject() {
    var entries = projectEntries();
    if (!entries) return say("설정에 오류가 있어 내려받을 수 없습니다. 검사 명령으로 확인해 주세요.", false);
    var list = Object.keys(entries).sort().map(function (name) {
      var value = entries[name];
      if (/^data:image\//.test(value)) return { name: name, bytes: bytesOf(value) };
      return { name: name, text: value };
    });
    var bytes = SiteZip.buildZip(list);
    var blob = new Blob([bytes], { type: "application/zip" });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "홈페이지-프로젝트.zip";
    link.click();
    URL.revokeObjectURL(link.href);
    say("zip 을 받았습니다. 압축을 풀어 저장소 맨 위 폴더에 그대로 넣고 올리면 배포 워크플로가 실행됩니다.", true);
  }

  function download(name, text, type) {
    var blob = new Blob([text], { type: type });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // 글 쓰기 칸: 페이지 파일의 글과 목록을 입력 칸으로 보여 줍니다. 줄 바꿈이 필요한 글도 여기서 씁니다.
  var FORM_SKIP = ["image", "imageAlt", "logo", "backgroundImage", "gallery", "sections"];
  var FIELD_LABELS = {
    title: "제목", body: "본문", intro: "소개 글", subtitle: "부제목", buttonText: "버튼 글", buttonLink: "버튼 주소",
    name: "이름", description: "검색용 설명", language: "언어 (ko, en, ja)", email: "이메일",
    notice: "안내", costs: "사업비 구성", disclosure: "외부 확인", apply: "신청 방법",
    label: "메뉴 이름", path: "주소", github: "GitHub 주소", instagram: "Instagram 주소", youtube: "YouTube 주소",
    summary: "설명", date: "날짜 (2026-01-15)", url: "관련 주소 (https:// 로 시작, 없으면 비움)"
  };
  var LONG_FIELDS = ["body", "intro", "notice", "costs", "disclosure", "apply", "summary", "description"];
  var ITEM_KEYS = ["title", "date", "summary", "url"];

  function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function labelOf(key) {
    return FIELD_LABELS[key] || key;
  }

  function getAt(data, path) {
    return path.reduce(function (node, key) { return node[key]; }, data);
  }

  function setAt(data, path, value) {
    getAt(data, path.slice(0, -1))[path[path.length - 1]] = value;
  }

  // 글 칸과 목록 칸을 찾습니다. 숫자나 사진 칸은 건너뜁니다.
  function formNodes(obj, prefix) {
    var nodes = [];
    Object.keys(obj).forEach(function (key) {
      if (FORM_SKIP.indexOf(key) !== -1) return;
      var value = obj[key];
      var path = prefix.concat([key]);
      if (typeof value === "string") {
        nodes.push({ kind: "text", path: path, key: key });
      } else if (Array.isArray(value) && value.every(isPlainObject)) {
        nodes.push({ kind: "list", path: path, key: key });
      } else if (isPlainObject(value)) {
        nodes = nodes.concat(formNodes(value, path));
      }
    });
    return nodes;
  }

  // 한 번에 한 파일을 고치고 검사합니다. 틀리면 저장하지 않고 되돌립니다.
  function editFile(file, mutate, message) {
    commit(function (f) {
      var data = JSON.parse(f[KEY_FILES[file]]);
      mutate(data);
      f[KEY_FILES[file]] = JSON.stringify(data, null, 2) + "\n";
    }, message);
  }

  function inputFor(key, value) {
    var input = LONG_FIELDS.indexOf(key) !== -1 ? document.createElement("textarea") : document.createElement("input");
    if (input.tagName === "INPUT") input.type = "text";
    input.value = typeof value === "string" ? value : "";
    return input;
  }

  function textField(file, data, node) {
    var label = document.createElement("label");
    label.className = "field";
    var caption = document.createElement("span");
    caption.textContent = labelOf(node.key);
    var input = inputFor(node.key, getAt(data, node.path));
    input.addEventListener("change", function () {
      editFile(file, function (d) { setAt(d, node.path, input.value); }, labelOf(node.key) + " 을(를) 고쳤습니다.");
    });
    label.append(caption, input);
    return label;
  }

  function listField(file, data, node) {
    var wrap = document.createElement("div");
    wrap.className = "field";
    var items = getAt(data, node.path);
    var heading = document.createElement("p");
    heading.className = "list-title";
    heading.textContent = labelOf(node.key) + " (" + items.length + "개)";
    wrap.append(heading);
    items.forEach(function (item, index) {
      var box = document.createElement("fieldset");
      box.className = "item";
      var legend = document.createElement("legend");
      legend.textContent = (index + 1) + "번";
      box.append(legend);
      ITEM_KEYS.forEach(function (k) {
        var row = document.createElement("label");
        row.className = "sub";
        var caption = document.createElement("span");
        caption.textContent = labelOf(k);
        var input = inputFor(k, item[k]);
        input.addEventListener("change", function () {
          editFile(file, function (d) { getAt(d, node.path)[index][k] = input.value; }, labelOf(k) + " 을(를) 고쳤습니다.");
        });
        row.append(caption, input);
        box.append(row);
      });
      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary";
      remove.textContent = "이 항목 빼기";
      remove.addEventListener("click", function () {
        editFile(file, function (d) { getAt(d, node.path).splice(index, 1); }, labelOf(node.key) + " 에서 항목을 뺐습니다.");
        renderForm();
      });
      box.append(remove);
      wrap.append(box);
    });
    var add = document.createElement("button");
    add.type = "button";
    add.className = "secondary";
    add.textContent = "항목 더하기";
    add.addEventListener("click", function () {
      editFile(file, function (d) { getAt(d, node.path).push({ title: "새 항목", date: "", summary: "", url: "" }); }, labelOf(node.key) + " 에 항목을 더했습니다.");
      renderForm();
    });
    wrap.append(add);
    return wrap;
  }

  function renderForm() {
    var box = document.getElementById("form-fields");
    var file = document.getElementById("form-page").value;
    box.replaceChildren();
    var data = JSON.parse(files[KEY_FILES[file]]);
    formNodes(data, []).forEach(function (node) {
      box.append(node.kind === "text" ? textField(file, data, node) : listField(file, data, node));
    });
  }

  // 글 칸에 맞는 목록 이름을 채웁니다. 첫 화면과 기관 정보를 포함해 설정 파일 전부를 고를 수 있습니다.
  function fillFormPages() {
    var select = document.getElementById("form-page");
    Object.keys(KEY_FILES).filter(function (key) { return key !== "nav" && key !== "theme"; }).forEach(function (key) {
      select.add(new Option(PAGE_LABELS[key] || key, key));
    });
  }

  // 미리보기 목록: 모든 페이지를 고를 수 있습니다.
  function fillPreviewPages() {
    var select = document.getElementById("page-select");
    select.replaceChildren();
    Object.keys(SCHEMA.pages).forEach(function (route) {
      var file = SCHEMA.pages[route];
      var key = route === "/" ? "home" : route.slice(1);
      select.add(new Option(PAGE_LABELS[key] || file, file));
    });
  }

  // 홈페이지 저장소 폴더를 통째로 불러와 이어서 고칩니다. 쓰는 파일만 골라 읽습니다.
  var IMAGE_NAME = /\.(png|jpe?g|gif|webp)$/i;

  function readFileAs(file, asDataUrl) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(reader.result); };
      reader.onerror = function () { reject(reader.error); };
      if (asDataUrl) reader.readAsDataURL(file);
      else reader.readAsText(file, "utf-8");
    });
  }

  function importFolder(picked) {
    if (!window.confirm("지금 편집 중인 내용을 이 폴더의 내용으로 바꿉니다. 계속할까요?")) return;
    var jobs = [];
    Array.prototype.forEach.call(picked, function (file) {
      var rel = (file.webkitRelativePath || file.name).split("/").slice(1).join("/");
      if (IMAGE_NAME.test(rel) && rel.indexOf("public/images/") === 0) jobs.push({ rel: rel, file: file, asDataUrl: true });
      else if (Object.prototype.hasOwnProperty.call(DEFAULT_FILES, rel)) jobs.push({ rel: rel, file: file, asDataUrl: false });
    });
    if (!jobs.length) return say("이 폴더에서 홈페이지 파일을 찾지 못했습니다. config 와 content 폴더가 들어 있는 저장소 폴더를 골라 주세요.", false);
    Promise.all(jobs.map(function (job) {
      return readFileAs(job.file, job.asDataUrl).then(function (value) { return { rel: job.rel, value: value }; });
    })).then(function (results) {
      var next = clone(DEFAULT_FILES);
      results.forEach(function (r) { next[r.rel] = r.value; });
      files = next;
      var saved = persist();
      var errors = validateCurrent();
      render();
      renderForm();
      var text = "폴더를 불러왔습니다 (" + results.length + "개 파일).";
      if (errors.length) text += "\n고칠 곳:\n- " + errors.join("\n- ");
      if (!saved) text += "\n브라우저 저장 공간이 부족합니다. 설정 저장(파일)을 받아 두세요.";
      say(text, !errors.length && saved);
    }, function () { say("폴더의 파일을 읽지 못했습니다.", false); });
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
    fillPreviewPages();
    pageSelect.addEventListener("change", function () { currentPage = pageSelect.value; render(); });

    fillFormPages();
    document.getElementById("form-page").addEventListener("change", renderForm);
    document.getElementById("btn-folder").addEventListener("click", function () { document.getElementById("file-folder").click(); });
    document.getElementById("file-folder").addEventListener("change", function (event) {
      var picked = Array.prototype.slice.call(event.target.files);
      event.target.value = "";
      if (picked.length) importFolder(picked);
    });

    var command = document.getElementById("command");
    document.getElementById("btn-run").addEventListener("click", function () { runCommand(command.value); render(); renderForm(); });
    command.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runCommand(command.value);
        render();
        renderForm();
      }
    });
    document.getElementById("btn-help").addEventListener("click", function () { runCommand("help"); });

    document.getElementById("btn-project").addEventListener("click", downloadProject);
    var pageSelect = document.getElementById("photo-page");
    PHOTO_ORDER.forEach(function (key) { pageSelect.add(new Option(PHOTO_TARGETS[key].label, key)); });
    pageSelect.addEventListener("change", refreshPhotoStatus);
    document.getElementById("btn-photo").addEventListener("click", function () { document.getElementById("file-photo").click(); });
    document.getElementById("btn-photo-remove").addEventListener("click", function () { removePhoto(pageSelect.value); });
    document.getElementById("file-photo").addEventListener("change", function (event) {
      var file = event.target.files[0];
      event.target.value = "";
      if (file) setPhoto(pageSelect.value, file);
    });
    document.getElementById("btn-css").addEventListener("click", setCustomCss);
    document.getElementById("btn-gallery").addEventListener("click", function () { document.getElementById("file-gallery").click(); });
    document.getElementById("file-gallery").addEventListener("change", function (event) {
      var picked = Array.prototype.slice.call(event.target.files);
      event.target.value = "";
      if (picked.length) addGalleryPhotos(pageSelect.value, picked);
    });
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
            renderForm();
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
      renderForm();
      say("처음 상태로 되돌렸습니다.", true);
    });

    render();
  }

  init();
})();
