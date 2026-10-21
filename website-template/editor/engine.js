/*
 * 홈페이지 엔진 (브라우저와 Node 에서 같이 씁니다). scripts/validate.py 와 scripts/generate.py 를 옮긴 것입니다.
 * 같은 입력에 대해 Python 결과와 글자 단위로 같아야 합니다 (tests/test_editor_parity.py 가 확인합니다).
 *
 * 입력: files = { "config/site.json": "<파일 글자>", ... }  (파일 이름은 템플릿과 같습니다)
 */
(function (root) {
  "use strict";

  var PAGE_FILES = { "/": "index.html", "/about": "about.html", "/projects": "projects.html", "/contact": "contact.html" };
  var ALLOWED_FONTS = ["system-ui", "serif", "mono"];
  var SPACINGS = ["compact", "normal", "airy"];
  var FONT_STACK = { "system-ui": "system-ui, sans-serif", "serif": "Georgia, serif", "mono": "ui-monospace, monospace" };
  var SPACING_PX = { "compact": 12, "normal": 24, "airy": 40 };
  var FILES = {
    site: "config/site.json", nav: "config/navigation.json", theme: "config/theme.json",
    home: "content/home.json", about: "content/about.json",
    projects: "content/projects.json", contact: "content/contact.json"
  };
  var HEX = /^#[0-9a-fA-F]{6}$/;
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var DATE = /^\d{4}-\d{2}-\d{2}$/;

  // Python html.escape(value, quote=True) 와 같은 규칙
  function esc(value) {
    var s = value === null || value === undefined ? "" : String(value);
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }

  function isObject(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
  function isInt(v) { return typeof v === "number" && Number.isInteger(v); }
  function str(v) { return v === null || v === undefined ? "" : String(v); }
  function strip(v) { return str(v).trim(); }
  function startsWith(s, prefix) { return s.slice(0, prefix.length) === prefix; }

  // 파이썬 str.strip() 과 같은 규칙 (공백 문자)
  function pyStrip(v) { return str(v).replace(/^\s+|\s+$/g, ""); }

  function isLinkOk(value) {
    return startsWith(value, "https://") || startsWith(value, "http://") || Object.prototype.hasOwnProperty.call(PAGE_FILES, value);
  }

  function validate(files) {
    var errors = [];
    var data = {};
    Object.keys(FILES).forEach(function (key) {
      var rel = FILES[key];
      var text = files[rel];
      if (text === undefined || text === null) {
        errors.push(rel + " 파일이 없습니다.");
        data[key] = null;
        return;
      }
      try {
        data[key] = JSON.parse(text);
      } catch (e) {
        errors.push(rel + " 의 JSON 형식이 올바르지 않습니다.");
        data[key] = null;
      }
    });

    var site = data.site, nav = data.nav, theme = data.theme;
    if (isObject(site)) {
      ["name", "language"].forEach(function (key) {
        if (!pyStrip(site[key])) errors.push("config/site.json: '" + key + "' 을 적어 주세요.");
      });
      if (["ko", "en", "ja"].indexOf(site.language) === -1) {
        errors.push("config/site.json: language 은 ko, en, ja 중 하나여야 합니다.");
      }
    } else if (site !== null) {
      errors.push("config/site.json: 최상위 값은 { } 묶음이어야 합니다.");
    }

    if (Array.isArray(nav)) {
      nav.forEach(function (entry, i) {
        var n = i + 1;
        if (!isObject(entry) || !entry.label) {
          errors.push("config/navigation.json " + n + "번: label 이 필요합니다.");
        } else if (!Object.prototype.hasOwnProperty.call(PAGE_FILES, entry.path)) {
          errors.push("config/navigation.json " + n + "번: 알 수 없는 페이지 주소입니다 (" + str(entry.path) + ").");
        }
      });
    } else if (nav !== null) {
      errors.push("config/navigation.json: 목록이어야 합니다.");
    }

    if (isObject(theme)) {
      ["primaryColor", "backgroundColor", "textColor"].forEach(function (key) {
        if (!HEX.test(str(theme[key]))) errors.push("config/theme.json: " + key + " 는 #RRGGBB 형식이어야 합니다.");
      });
      if (ALLOWED_FONTS.indexOf(theme.font) === -1) {
        errors.push("config/theme.json: font 은 " + ALLOWED_FONTS.slice().sort().join(", ") + " 중 하나여야 합니다.");
      }
      var radius = theme.radius;
      if (!isInt(radius) || radius < 0 || radius > 32) errors.push("config/theme.json: radius 는 0~32 사이의 정수여야 합니다.");
      if (SPACINGS.indexOf(theme.spacing) === -1) errors.push("config/theme.json: spacing 은 compact, normal, airy 중 하나여야 합니다.");
    }

    var home = data.home;
    if (isObject(home)) {
      var hero = isObject(home.hero) ? home.hero : {};
      if (!hero.title) errors.push("content/home.json: hero.title 을 적어 주세요.");
      if (hero.buttonLink && !isLinkOk(str(hero.buttonLink))) {
        errors.push("content/home.json: buttonLink 은 https:// 주소 또는 페이지 주소여야 합니다 (" + hero.buttonLink + ").");
      }
    }

    var projects = data.projects;
    if (isObject(projects)) {
      var items = Array.isArray(projects.items) ? projects.items : [];
      items.forEach(function (item, i) {
        var n = i + 1;
        if (!isObject(item) || !item.title) {
          errors.push("content/projects.json " + n + "번 사업: title 이 필요합니다.");
          return;
        }
        if (item.date && !DATE.test(str(item.date))) errors.push("content/projects.json " + n + "번 사업: date 는 YYYY-MM-DD 형식이어야 합니다.");
        if (item.url && !(startsWith(str(item.url), "https://") || startsWith(str(item.url), "http://"))) {
          errors.push("content/projects.json " + n + "번 사업: url 은 https:// 로 시작해야 합니다.");
        }
      });
    }

    var contact = data.contact;
    if (isObject(contact)) {
      if (contact.email && !EMAIL.test(str(contact.email))) errors.push("content/contact.json: 이메일 형식이 올바르지 않습니다.");
      var social = isObject(contact.social) ? contact.social : {};
      Object.keys(social).forEach(function (key) {
        var value = str(social[key]);
        if (value && !(startsWith(value, "https://") || startsWith(value, "http://"))) {
          errors.push("content/contact.json: social." + key + " 는 https:// 로 시작해야 합니다.");
        }
      });
    }
    return { data: data, errors: errors };
  }

  // {{이름}} 자리에 값을 넣습니다. 빠진 값이 있으면 오류입니다.
  function fill(template, values) {
    return template.replace(/\{\{(\w+)\}\}/g, function (match, key) {
      if (!Object.prototype.hasOwnProperty.call(values, key)) throw new Error("템플릿에 없는 자리표시자입니다: " + key);
      return values[key];
    });
  }

  function themeCss(theme) {
    return ":root {" +
      " --primary: " + theme.primaryColor + ";" +
      " --bg: " + theme.backgroundColor + ";" +
      " --text: " + theme.textColor + ";" +
      " --font: " + FONT_STACK[theme.font] + ";" +
      " --radius: " + theme.radius + "px;" +
      " --gap: " + SPACING_PX[theme.spacing] + "px;" +
      " --max: 760px;" +
      " }";
  }

  function linkFor(value) {
    if (startsWith(value, "https://") || startsWith(value, "http://")) return value;
    return PAGE_FILES[value];
  }

  function headerHtml(files, site, nav, currentFile) {
    var links = nav.map(function (entry) {
      var target = PAGE_FILES[entry.path];
      var current = target === currentFile ? ' aria-current="page"' : "";
      return '<li><a href="' + esc(target) + '"' + current + ">" + esc(entry.label) + "</a></li>";
    });
    return fill(files["src/components/Header.html"], { brand: esc(site.name), links: links.join("") });
  }

  function heroHtml(files, home) {
    var hero = home.hero;
    var button = "";
    if (hero.buttonText && hero.buttonLink) {
      button = '<a class="button" href="' + esc(linkFor(hero.buttonLink)) + '">' + esc(hero.buttonText) + "</a>";
    }
    return fill(files["src/components/Hero.html"], {
      title: esc(hero.title), subtitle: esc(hero.subtitle), button: button
    });
  }

  function footerHtml(files, site, contact) {
    var lines = [];
    if (contact.email) {
      lines.push('<p><a href="' + esc("mailto:" + contact.email) + '">' + esc(contact.email) + "</a></p>");
    }
    var social = isObject(contact.social) ? contact.social : {};
    var names = [["github", "GitHub"], ["instagram", "Instagram"], ["youtube", "YouTube"]];
    var links = names.filter(function (pair) { return social[pair[0]]; }).map(function (pair) {
      return '<li><a href="' + esc(social[pair[0]]) + '">' + pair[1] + "</a></li>";
    });
    if (links.length) lines.push('<ul class="links">' + links.join("") + "</ul>");
    return fill(files["src/components/Footer.html"], { name: esc(site.name), contact: lines.join("") });
  }

  function block(title, bodyHtml) {
    return '<section class="block"><h2>' + esc(title) + "</h2>" + bodyHtml + "</section>";
  }

  // 날짜가 최신인 것이 위로 옵니다. 날짜가 같으면 원래 순서를 지킵니다.
  function projectArticles(items) {
    var ordered = items.map(function (item, index) { return { item: item, index: index }; });
    ordered.sort(function (a, b) {
      var da = str(a.item.date), db = str(b.item.date);
      if (da !== db) return da < db ? 1 : -1;
      return a.index - b.index;
    });
    return ordered.map(function (pair) {
      var item = pair.item;
      var title = esc(item.title);
      if (item.url) title = '<a href="' + esc(item.url) + '">' + title + "</a>";
      var date = item.date ? '<time datetime="' + esc(item.date) + '">' + esc(item.date) + "</time>" : "";
      var summary = item.summary ? "<p>" + esc(item.summary) + "</p>" : "";
      return "<article><h3>" + title + "</h3>" + date + summary + "</article>";
    }).join("");
  }

  function buildPages(files, data) {
    var site = data.site, nav = data.nav, theme = data.theme;
    var style = themeCss(theme) + "\n" + files["src/styles/site.css"];
    var pages = {};

    function page(fileName, title, mainHtml, description) {
      var fullTitle = fileName === "index.html" ? site.name : title + " | " + site.name;
      pages[fileName] = fill(files["src/pages/page.html"], {
        lang: esc(site.language || "ko"),
        title: esc(fullTitle),
        description: esc(site.description),
        style: style,
        header: headerHtml(files, site, nav, fileName),
        main: mainHtml,
        footer: footerHtml(files, site, data.contact)
      });
    }

    var home = data.home;
    var previewItems = (data.projects.items || []).slice(0, 3);
    var preview = projectArticles(previewItems);
    var homeMain = heroHtml(files, home) +
      block("소개", '<p class="pre">' + esc(home.intro) + "</p>") +
      (preview ? block(data.projects.title, preview) : "");
    page("index.html", site.name, homeMain, site.description || "");

    page("about.html", data.about.title,
      block(data.about.title, '<p class="pre">' + esc(data.about.body) + "</p>"), data.about.body);
    page("projects.html", data.projects.title,
      block(data.projects.title, projectArticles(data.projects.items || [])), data.projects.title);
    page("contact.html", data.contact.title,
      block(data.contact.title, '<p class="pre">' + esc(data.contact.body) + "</p>"), data.contact.body);
    return pages;
  }

  // 검사를 통과하면 페이지 파일 이름과 내용을 돌려줍니다. 틀리면 오류 목록만 돌려줍니다.
  function build(files) {
    var checked = validate(files);
    if (checked.errors.length) return { ok: false, errors: checked.errors, pages: {} };
    return { ok: true, errors: [], pages: buildPages(files, checked.data) };
  }

  var api = { PAGE_FILES: PAGE_FILES, FILES: FILES, validate: validate, build: build, esc: esc, fill: fill };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.SiteEngine = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
