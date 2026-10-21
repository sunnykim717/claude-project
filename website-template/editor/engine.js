/*
 * 홈페이지 엔진 (브라우저와 Node 에서 같이 씁니다). scripts/validate.py 와 scripts/generate.py 를 옮긴 것입니다.
 * 같은 입력에 대해 Python 결과와 글자 단위로 같아야 합니다 (tests/test_editor_parity.py 가 확인합니다).
 *
 * 입력: files = { "config/site.json": "<파일 글자>", ... }  (파일 이름은 템플릿과 같습니다)
 */
(function (root) {
  "use strict";

  // 설정 항목 목록은 schema.json 에서만 옵니다. useSchema() 로 한 번 넣어 주세요.
  var loaded = false;
  var PAGE_FILES, FILES, ALLOWED_FONTS, FONT_STACK, SPACINGS, SPACING_PX, LAYOUTS, MENUS, LANGUAGES, IMAGE, PHOTO_PAGES;
  var HEX = /^#[0-9a-fA-F]{6}$/;
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var DATE = /^\d{4}-\d{2}-\d{2}$/;

  function useSchema(schema) {
    PAGE_FILES = schema.pages;
    FILES = schema.files;
    FONT_STACK = schema.fonts;
    ALLOWED_FONTS = Object.keys(schema.fonts);
    SPACING_PX = schema.spacings;
    SPACINGS = Object.keys(schema.spacings);
    LAYOUTS = schema.layouts;
    MENUS = schema.menus;
    LANGUAGES = schema.languages;
    IMAGE = new RegExp("^/images/[A-Za-z0-9._-]+\\.(" + schema.image_extensions.join("|") + ")$");
    PHOTO_PAGES = schema.photo_pages;
    loaded = true;
  }

  function requireSchema() {
    if (!loaded) throw new Error("schema.json 을 먼저 useSchema() 로 넣어 주세요.");
  }

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

  // 사진 칸이 비어 있으면 아무것도 하지 않습니다. 있으면 형식과 파일 존재를 봅니다.
  function checkPhoto(files, errors, rel, content) {
    if (!content.image) return;
    var image = str(content.image);
    if (!IMAGE.test(image)) {
      errors.push(rel + ": image 는 /images/파일이름.jpg (png, webp, gif) 형식이어야 합니다.");
    } else if (!(("public/" + image.replace(/^\/+/, "")) in files)) {
      errors.push(rel + ": 사진 파일이 public 폴더에 없습니다 (" + image + ").");
    }
  }

  function checkItems(errors, rel, label, items) {
    if (!Array.isArray(items)) {
      errors.push(rel + ": 목록이어야 합니다.");
      return;
    }
    items.forEach(function (item, i) {
      var n = i + 1;
      if (!isObject(item) || !item.title) {
        errors.push(rel + " " + n + "번 " + label + ": title 이 필요합니다.");
        return;
      }
      if (item.date && !DATE.test(str(item.date))) errors.push(rel + " " + n + "번 " + label + ": date 는 YYYY-MM-DD 형식이어야 합니다.");
      if (item.url && !(startsWith(str(item.url), "https://") || startsWith(str(item.url), "http://"))) {
        errors.push(rel + " " + n + "번 " + label + ": url 은 https:// 로 시작해야 합니다.");
      }
    });
  }

  function validate(files) {
    requireSchema();
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
      if (LANGUAGES.indexOf(site.language) === -1) {
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
      if (SPACINGS.indexOf(theme.spacing) === -1) errors.push("config/theme.json: spacing 은 " + SPACINGS.join(", ") + " 중 하나여야 합니다.");
      if (LAYOUTS.indexOf(theme.layout) === -1) errors.push("config/theme.json: layout 은 " + LAYOUTS.join(", ") + " 중 하나여야 합니다.");
      if (MENUS.indexOf(theme.menu) === -1) errors.push("config/theme.json: menu 는 " + MENUS.join(", ") + " 중 하나여야 합니다.");
    }

    var home = data.home;
    if (isObject(home)) {
      var hero = isObject(home.hero) ? home.hero : {};
      if (!hero.title) errors.push("content/home.json: hero.title 을 적어 주세요.");
      checkPhoto(files, errors, "content/home.json", hero);
      if (hero.buttonLink && !isLinkOk(str(hero.buttonLink))) {
        errors.push("content/home.json: buttonLink 은 https:// 주소 또는 페이지 주소여야 합니다 (" + hero.buttonLink + ").");
      }
    }

    PHOTO_PAGES.forEach(function (name) {
      if (isObject(data[name])) checkPhoto(files, errors, "content/" + name + ".json", data[name]);
    });

    var projects = data.projects;
    if (isObject(projects)) checkItems(errors, "content/projects.json", "사업", projects.items);
    var news = data.news;
    if (isObject(news)) checkItems(errors, "content/news.json", "소식", news.items);
    var support = data.support;
    if (isObject(support)) checkItems(errors, "content/support.json", "후원 방법", support.ways);
    var transparency = data.transparency;
    if (isObject(transparency)) checkItems(errors, "content/transparency.json", "자료", transparency.reports);
    var volunteer = data.volunteer;
    if (isObject(volunteer)) checkItems(errors, "content/volunteer.json", "활동", volunteer.positions);
    var privacy = data.privacy;
    if (isObject(privacy)) checkItems(errors, "content/privacy.json", "항목", privacy.items);

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
    var image = "";
    if (hero.image) {
      var src = "public/" + String(hero.image).replace(/^\/+/, "");
      image = '<img class="hero-photo" src="' + esc(src) + '" alt="' + esc(hero.imageAlt) + '">';
    }
    var button = "";
    if (hero.buttonText && hero.buttonLink) {
      button = '<a class="button" href="' + esc(linkFor(hero.buttonLink)) + '">' + esc(hero.buttonText) + "</a>";
    }
    return fill(files["src/components/Hero.html"], {
      image: image, title: esc(hero.title), subtitle: esc(hero.subtitle), button: button
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
    lines.push('<p><a href="privacy.html">개인정보 처리방침</a></p>');
    return fill(files["src/components/Footer.html"], { name: esc(site.name), contact: lines.join("") });
  }

  function itemsHtml(items, layout) {
    var body = projectArticles(items);
    if (layout === "card" && body) return '<div class="cards">' + body + "</div>";
    return body;
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

  function photoHtml(content) {
    if (!content.image) return "";
    var src = "public/" + String(content.image).replace(/^\/+/, "");
    return '<figure class="page-photo"><img src="' + esc(src) + '" alt="' + esc(content.imageAlt) + '"></figure>';
  }

  function buildPages(files, data) {
    var site = data.site, nav = data.nav, theme = data.theme;
    var style = themeCss(theme) + "\n" + files["src/styles/site.css"];
    var pages = {};

    function page(fileName, title, mainHtml, description, photo) {
      var fullTitle = fileName === "index.html" ? site.name : title + " | " + site.name;
      pages[fileName] = fill(files["src/pages/page.html"], {
        lang: esc(site.language || "ko"),
        title: esc(fullTitle),
        description: esc(site.description),
        style: style,
        header: headerHtml(files, site, nav, fileName),
        main: (photo || "") + mainHtml,
        footer: footerHtml(files, site, data.contact),
        layout: esc(theme.layout),
        menu: esc(theme.menu)
      });
    }

    var home = data.home;
    var previewItems = (data.projects.items || []).slice(0, 3);
    var preview = itemsHtml(previewItems, theme.layout);
    var homeMain = heroHtml(files, home) +
      block("소개", '<p class="pre">' + esc(home.intro) + "</p>") +
      (preview ? block(data.projects.title, preview) : "");
    page("index.html", site.name, homeMain, site.description || "");

    page("about.html", data.about.title,
      block(data.about.title, '<p class="pre">' + esc(data.about.body) + "</p>"), data.about.body, photoHtml(data.about));
    page("projects.html", data.projects.title,
      block(data.projects.title, itemsHtml(data.projects.items || [], theme.layout)), data.projects.title, photoHtml(data.projects));
    var support = data.support;
    var ways = projectArticles(support.ways || []);
    var supportMain = block(support.title, '<p class="pre">' + esc(support.body) + "</p>");
    if (ways) supportMain += block("후원 방법", ways);
    if (support.notice) supportMain += block("안내", '<p class="pre">' + esc(support.notice) + "</p>");
    page("support.html", support.title, supportMain, support.body, photoHtml(support));
    page("news.html", data.news.title, block(data.news.title, projectArticles(data.news.items || [])), data.news.title, photoHtml(data.news));
    var transparency = data.transparency;
    page("transparency.html", transparency.title,
      block(transparency.title, '<p class="pre">' + esc(transparency.body) + "</p>") +
      block("사업 · 재무 자료", projectArticles(transparency.reports || [])) +
      block("사업비 구성", '<p class="pre">' + esc(transparency.costs) + "</p>") +
      block("외부 확인", '<p class="pre">' + esc(transparency.disclosure) + "</p>"),
      transparency.body, photoHtml(transparency));
    var volunteer = data.volunteer;
    page("volunteer.html", volunteer.title,
      block(volunteer.title, '<p class="pre">' + esc(volunteer.body) + "</p>") +
      block("활동 종류", projectArticles(volunteer.positions || [])) +
      block("신청 방법", '<p class="pre">' + esc(volunteer.apply) + "</p>"),
      volunteer.body, photoHtml(volunteer));
    var privacy = data.privacy;
    page("privacy.html", privacy.title,
      block(privacy.title, '<p class="pre">' + esc(privacy.body) + "</p>") +
      block("처리 항목", projectArticles(privacy.items || [])),
      privacy.body, photoHtml(privacy));
    page("contact.html", data.contact.title,
      block(data.contact.title, '<p class="pre">' + esc(data.contact.body) + "</p>"), data.contact.body, photoHtml(data.contact));
    return pages;
  }

  // 검사를 통과하면 페이지 파일 이름과 내용을 돌려줍니다. 틀리면 오류 목록만 돌려줍니다.
  function build(files) {
    requireSchema();
    var checked = validate(files);
    if (checked.errors.length) return { ok: false, errors: checked.errors, pages: {} };
    return { ok: true, errors: [], pages: buildPages(files, checked.data) };
  }

  var api = { useSchema: useSchema, validate: validate, build: build, esc: esc, fill: fill };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.SiteEngine = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
