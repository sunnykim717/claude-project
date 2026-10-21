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
  var BASE_ROUTES, ROUTES, FILES, ALLOWED_FONTS, FONT_STACK, SPACINGS, SPACING_PX, LAYOUTS, MENUS, LANGUAGES, IMAGE, PHOTO_PAGES, GALLERY_MAX, GENERIC_PAGES, HOME_SECTIONS, CONTENT_WIDTHS, HERO_VARIANTS, HOMEPAGE_SECTIONS;
  var HEX = /^#[0-9a-fA-F]{6}$/;
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var DATE = /^\d{4}-\d{2}-\d{2}$/;

  function useSchema(schema) {
    BASE_ROUTES = schema.pages;
    ROUTES = schema.pages;
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
    GALLERY_MAX = schema.gallery_max;
    GENERIC_PAGES = schema.generic_pages;
    HOME_SECTIONS = schema.home_sections;
    CONTENT_WIDTHS = schema.content_widths;
    HERO_VARIANTS = schema.hero_variants;
    HOMEPAGE_SECTIONS = schema.homepage_sections;
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
    return startsWith(value, "https://") || startsWith(value, "http://") || Object.prototype.hasOwnProperty.call(ROUTES, value);
  }

  // 사진 칸이 비어 있으면 아무것도 하지 않습니다. 있으면 형식과 파일 존재를 봅니다.
  function checkImage(files, errors, rel, value, field) {
    if (!value) return;
    var image = str(value);
    if (!IMAGE.test(image)) {
      errors.push(rel + ": " + field + " 는 /images/파일이름.jpg (png, webp, gif) 형식이어야 합니다.");
    } else if (!(("public/" + image.replace(/^\/+/, "")) in files)) {
      errors.push(rel + ": 사진 파일이 public 폴더에 없습니다 (" + image + ").");
    }
  }

  function checkPhoto(files, errors, rel, content) {
    checkImage(files, errors, rel, content.image, "image");
    if (content.image && !str(content.imageAlt).trim()) errors.push(rel + ": 사진이 있으면 imageAlt (사진 설명) 을 적어 주세요.");
    var gallery = content.gallery;
    if (gallery === undefined || gallery === null) return;
    if (!Array.isArray(gallery)) {
      errors.push(rel + ": gallery 는 목록이어야 합니다.");
      return;
    }
    if (gallery.length > GALLERY_MAX) errors.push(rel + ": gallery 는 " + GALLERY_MAX + "장까지 넣을 수 있습니다.");
    gallery.forEach(function (item, index) {
      var n = index + 1;
      if (!isObject(item)) {
        errors.push(rel + " " + n + "번 사진: 사진 칸이 올바르지 않습니다.");
        return;
      }
      checkImage(files, errors, rel + " " + n + "번 사진", item.image, "image");
      if ("alt" in item && typeof item.alt !== "string") errors.push(rel + " " + n + "번 사진: alt 는 글자여야 합니다.");
    });
  }

  var FORBIDDEN_CSS = /<|@import|url\s*\(|expression\s*\(|javascript:|behavior\s*:|-moz-binding/gi;

  // 직접 쓰는 CSS 는 바깥 파일을 부르지 못하게 합니다 (Python 검사와 같은 규칙).
  function checkCustomCss(files, errors) {
    var text = files["config/custom.css"];
    if (typeof text !== "string") return;
    if (text.length > 20000) errors.push("config/custom.css: 20,000 글자를 넘을 수 없습니다.");
    var found = (text.match(FORBIDDEN_CSS) || []).map(function (m) { return m.toLowerCase(); });
    found = found.filter(function (m, i) { return found.indexOf(m) === i; }).sort();
    if (found.length) errors.push("config/custom.css: 다음은 쓸 수 없습니다: " + found.join(", "));
  }

  var SLUG = /^[a-z][a-z0-9-]{1,30}$/;
  var SUPABASE_URL = /^https:\/\/[a-z0-9-]+\.supabase\.co\/?$/;

  // 키가 JWT 형식이면 role (anon 또는 service_role) 을 돌려줍니다. 아니면 null.
  function jwtRole(token) {
    var parts = str(token).split(".");
    if (parts.length !== 3) return null;
    var b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4) b64 += "=";
    var payload;
    try { payload = JSON.parse(atob(b64)); } catch (e) { return null; }
    return isObject(payload) ? payload.role : null;
  }

  function checkSupabase(errors, cfg) {
    if (!isObject(cfg)) {
      errors.push("config/supabase.json: 최상위 값은 { } 묶음이어야 합니다.");
      return;
    }
    var url = str(cfg.url), key = str(cfg.anonKey);
    if (!url && !key) return;
    if (!url || !key) {
      errors.push("config/supabase.json: url 과 anonKey 를 둘 다 넣거나 둘 다 비워 두세요.");
      return;
    }
    if (!SUPABASE_URL.test(url)) errors.push("config/supabase.json: url 은 https://프로젝트.supabase.co 형식이어야 합니다.");
    if (startsWith(key, "sb_secret_") || jwtRole(key) === "service_role") {
      errors.push("config/supabase.json: service_role (secret) 키는 공개 페이지에 넣을 수 없습니다. anon 또는 publishable 키를 쓰세요.");
    } else if (!(startsWith(key, "sb_publishable_") || jwtRole(key) === "anon")) {
      errors.push("config/supabase.json: anon 또는 publishable 키를 넣어 주세요 (Settings → API).");
    }
  }

  function checkCustomPages(files, errors, custom) {
    if (!Array.isArray(custom)) {
      errors.push("content/custom-pages.json: 목록이어야 합니다.");
      return;
    }
    var seen = {};
    custom.forEach(function (page, i) {
      var rel = "content/custom-pages.json " + (i + 1) + "번";
      if (!isObject(page)) {
        errors.push(rel + ": 페이지 칸이 올바르지 않습니다.");
        return;
      }
      var slug = page.slug;
      if (typeof slug !== "string" || !SLUG.test(slug)) {
        errors.push(rel + ": slug 는 영문 소문자로 시작하는 2~31자 (소문자, 숫자, -) 여야 합니다.");
        return;
      }
      if (Object.prototype.hasOwnProperty.call(BASE_ROUTES, "/" + slug) || seen[slug]) {
        errors.push(rel + ": 주소 /" + slug + " 가 이미 있습니다.");
        return;
      }
      seen[slug] = true;
      if (!page.title) errors.push(rel + ": title 을 적어 주세요.");
      checkItems(errors, rel, "항목", page.items || []);
      checkPhoto(files, errors, rel, page);
    });
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
      if ("publish" in item && !(typeof item.publish === "string" && DATE.test(item.publish))) {
        errors.push(rel + " " + n + "번 " + label + ": publish 는 YYYY-MM-DD 형식이어야 합니다.");
      }
      if ("body" in item && typeof item.body !== "string") errors.push(rel + " " + n + "번 " + label + ": body 는 글자여야 합니다.");
      if (item.url && !(startsWith(str(item.url), "https://") || startsWith(str(item.url), "http://"))) {
        errors.push(rel + " " + n + "번 " + label + ": url 은 https:// 로 시작해야 합니다.");
      }
    });
  }

  function validate(files) {
    requireSchema();
    ROUTES = Object.assign({}, BASE_ROUTES);
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

    if (Array.isArray(data.custom_pages)) {
      data.custom_pages.forEach(function (page) {
        if (isObject(page) && typeof page.slug === "string" && SLUG.test(page.slug)) {
          if (!Object.prototype.hasOwnProperty.call(ROUTES, "/" + page.slug)) ROUTES["/" + page.slug] = page.slug + ".html";
        }
      });
    }

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
        } else if (!Object.prototype.hasOwnProperty.call(ROUTES, entry.path)) {
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

    if (isObject(site)) checkImage(files, errors, "config/site.json", site.logo, "logo");
    if (isObject(theme)) checkImage(files, errors, "config/theme.json", theme.backgroundImage, "backgroundImage");
    checkCustomCss(files, errors);

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

    GENERIC_PAGES.forEach(function (name) {
      if (!isObject(data[name])) return;
      if (!data[name].title) errors.push("content/" + name + ".json: title 을 적어 주세요.");
      checkItems(errors, "content/" + name + ".json", "항목", data[name].items || []);
    });

    checkCustomPages(files, errors, data.custom_pages);
    checkSupabase(errors, data.supabase);
    checkDesign(errors, data);
    checkHomepage(errors, data);
    checkImpact(errors, data.impact);
    checkContactFields(errors, data.contact);
    checkSiteUrl(errors, data.site);

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


  function linkFor(value) {
    if (startsWith(value, "https://") || startsWith(value, "http://")) return value;
    return ROUTES[value];
  }

  function headerHtml(files, site, nav, currentFile) {
    var links = nav.map(function (entry) {
      var target = ROUTES[entry.path];
      var current = target === currentFile ? ' aria-current="page"' : "";
      return '<li><a href="' + esc(target) + '"' + current + ">" + esc(entry.label) + "</a></li>";
    });
    var brand = esc(site.name);
    if (site.logo) brand = '<img class="logo" src="' + esc("public/" + String(site.logo).replace(/^\/+/, "")) + '" alt="">' + brand;
    return fill(files["src/components/Header.html"], { brand: brand, links: links.join("") });
  }

  function heroHtml(files, home, variant) {
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
      variant: HERO_CLASS[variant], image: image, title: esc(hero.title), subtitle: esc(hero.subtitle), button: button
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
    if (site.sample) lines.push('<p class="sample-note">이 홈페이지의 기관 정보와 글은 가상의 샘플입니다.</p>');
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
      var body = item.body ? '<details><summary>자세히 보기</summary><p class="pre">' + esc(item.body) + "</p></details>" : "";
      return "<article><h3>" + title + "</h3>" + date + summary + body + "</article>";
    }).join("");
  }

  function photoHtml(content) {
    if (!content.image) return "";
    var src = "public/" + String(content.image).replace(/^\/+/, "");
    return '<figure class="page-photo"><img src="' + esc(src) + '" alt="' + esc(content.imageAlt) + '"></figure>';
  }

  // 배경 사진이 있으면 배경색 위에 얇은 막을 씌웁니다 (Python 생성기와 같은 규칙).
  function backgroundCss(theme) {
    if (!theme.backgroundImage) return "";
    var src = "public/" + String(theme.backgroundImage).replace(/^\/+/, "");
    return 'body { background-image: url("' + src + '"); background-size: cover; background-attachment: fixed; }\n' +
      'body::before { content: ""; position: fixed; inset: 0; z-index: -1; background: var(--bg); opacity: 0.88; }';
  }

  function galleryHtml(content) {
    var items = content.gallery || [];
    if (!items.length) return "";
    var figures = items.map(function (item) {
      return '<figure><img src="' + esc("public/" + String(item.image).replace(/^\/+/, "")) + '" alt="' + esc(item.alt) + '" loading="lazy"></figure>';
    }).join("");
    return '<div class="gallery">' + figures + "</div>";
  }

  // 제목, 본문, 목록으로 된 간단한 페이지의 내용입니다 (Python 의 generic_body 와 같음).
  function genericBody(content) {
    var items = content.items || [];
    var body = block(content.title, '<p class="pre">' + esc(content.body) + "</p>");
    if (items.length) body += block(content.itemsTitle || "목록", projectArticles(items));
    return body;
  }

  var ADMIN_INTRO = "방문자가 올린 글을 확인해서 승인하거나 지우는 화면입니다. 로그인한 관리자만 글을 바꿀 수 있습니다.";

  function supabaseSettings(data) {
    var cfg = isObject(data.supabase) ? data.supabase : {};
    return { url: str(cfg.url), key: str(cfg.anonKey) };
  }

  function readScript(files, rel) {
    return strip(files[rel]);
  }

  function adminMain(files, url, key) {
    return fill(files["src/components/Admin.html"], {
      url: esc(url), key: esc(key), intro: esc(ADMIN_INTRO), script: readScript(files, "src/admin/admin.js")
    });
  }

  function boardLiveHtml(files, url, key) {
    return fill(files["src/components/BoardLive.html"], {
      url: esc(url), key: esc(key), script: readScript(files, "src/admin/board.js")
    });
  }

  // ----- 디자인 플랫폼: 프리셋, 첫 화면 변형, 홈 칸 (Python 생성기와 같은 규칙) -----
  var HERO_CLASS = { split: "hero-split", photo: "hero-photo-variant", info: "hero-info" };
  var DEFAULT_SECTIONS = ["hero", "quickLinks", "about", "programs", "news", "stories", "impact", "participation", "contact"];

  function hasKey(obj, key) {
    return isObject(obj) && Object.prototype.hasOwnProperty.call(obj, key);
  }

  function designChoice(data) {
    var design = isObject(data.design) ? data.design : {};
    var presets = isObject(data.presets) ? data.presets : {};
    var name = design.preset;
    if (!name || !hasKey(presets, name)) return null;
    var preset = presets[name];
    return {
      name: name,
      tokens: preset.tokens,
      hero: design.hero || preset.defaultHero,
      width: CONTENT_WIDTHS[design.contentWidth || "comfortable"]
    };
  }

  function themeCss(theme, choice) {
    var t = choice ? choice.tokens : {};
    var primary = hasKey(t, "primary") ? t.primary : theme.primaryColor;
    var bg = hasKey(t, "bg") ? t.bg : theme.backgroundColor;
    var text = hasKey(t, "text") ? t.text : theme.textColor;
    var font = FONT_STACK[hasKey(t, "font") ? t.font : theme.font];
    var radius = hasKey(t, "radius") ? t.radius : theme.radius;
    var gap = SPACING_PX[hasKey(t, "spacing") ? t.spacing : theme.spacing];
    var width = choice ? choice.width : 760;
    var surface = hasKey(t, "surface") ? t.surface : "#FFFFFF";
    var muted = hasKey(t, "muted") ? t.muted : text;
    var accent = hasKey(t, "accent") ? t.accent : primary;
    return ":root {" +
      " --primary: " + primary + "; --bg: " + bg + "; --text: " + text + "; --font: " + font + ";" +
      " --radius: " + radius + "px; --gap: " + gap + "px; --max: " + width + "px;" +
      " --surface: " + surface + "; --muted: " + muted + "; --accent: " + accent + ";" +
      " }";
  }

  function newsList(items) {
    var ordered = items.map(function (item, index) { return { item: item, index: index }; });
    ordered.sort(function (a, b) {
      var da = str(a.item.date), db = str(b.item.date);
      if (da !== db) return da < db ? 1 : -1;
      return a.index - b.index;
    });
    var rows = ordered.map(function (pair) {
      var item = pair.item;
      var title = esc(item.title);
      if (item.url) title = '<a href="' + esc(item.url) + '">' + title + "</a>";
      var when = item.date ? '<time datetime="' + esc(item.date) + '">' + esc(item.date) + "</time>" : "";
      return "<li>" + when + "<span>" + title + "</span></li>";
    });
    return '<ul class="news-list">' + rows.join("") + "</ul>";
  }

  function sectionQuick(nav) {
    var links = nav.filter(function (entry) { return entry.path !== "/"; }).slice(0, 6);
    if (!links.length) return "";
    var items = links.map(function (entry) {
      return '<li><a class="quick-link" href="' + esc(ROUTES[entry.path]) + '">' + esc(entry.label) + "</a></li>";
    }).join("");
    return block("바로 가기", '<ul class="quick-grid">' + items + "</ul>");
  }

  function sectionAbout(home) {
    var intro = str(home.intro).trim();
    if (!intro) return "";
    return block("기관 소개", '<p class="pre">' + esc(intro) + '</p><p><a class="more" href="about.html">기관 소개 자세히 보기</a></p>');
  }

  function sectionPrograms(projects) {
    var items = projects.items || [];
    if (!items.length) return "";
    return block(projects.title, '<div class="programs">' + projectArticles(items.slice(0, 3)) + "</div>");
  }

  function sectionNews(news) {
    var items = news.items || [];
    if (!items.length) return "";
    return block(news.title, newsList(items.slice(0, 3)));
  }

  function sectionStories(stories) {
    var items = stories.items || [];
    if (!items.length) return "";
    var body = '<div class="story-lead">' + projectArticles(items.slice(0, 1)) + "</div>";
    if (items.length > 1) body += '<div class="story-list">' + projectArticles(items.slice(1)) + "</div>";
    return block(stories.title, body);
  }

  function sectionImpact(impact) {
    var items = impact.items || [];
    if (!items.length) return "";
    var cells = items.map(function (i) {
      return "<div><dt>" + esc(i.value) + "</dt><dd>" + esc(i.label) +
        (i.description ? "<br>" + esc(i.description) : "") + "</dd></div>";
    }).join("");
    var note = impact.period ? '<p class="impact-note">' + esc(impact.period) + "</p>" : "";
    return block(impact.title, '<dl class="impact">' + cells + "</dl>" + note);
  }

  function sectionParticipation(support, volunteer) {
    var ways = support.ways || [];
    var positions = volunteer.positions || [];
    if (!ways.length && !positions.length) return "";
    var body = ways.length ? projectArticles(ways) : "";
    body += '<p class="participation-actions">' +
      '<a class="button" href="support.html">후원 안내 보기</a>' +
      '<a class="button secondary" href="volunteer.html">자원봉사 안내 보기</a>' +
      "</p>";
    return block("참여 방법", body);
  }

  function sectionContact(contact) {
    var rows = [];
    if (contact.phone) rows.push(["전화", esc(contact.phone)]);
    if (contact.email) rows.push(["이메일", '<a href="' + esc("mailto:" + contact.email) + '">' + esc(contact.email) + "</a>"]);
    if (contact.address) rows.push(["주소", esc(contact.address)]);
    if (contact.hours) rows.push(["운영시간", esc(contact.hours)]);
    var body = contact.body ? '<p class="pre">' + esc(contact.body) + "</p>" : "";
    if (rows.length) {
      body += '<ul class="contact-list">' + rows.map(function (row) {
        return "<li><strong>" + row[0] + "</strong> " + row[1] + "</li>";
      }).join("") + "</ul>";
    }
    if (!body) return "";
    return block(contact.title, body);
  }

  function homeMain(files, data, choice) {
    var home = data.home;
    var parts = {
      hero: heroHtml(files, home, choice ? choice.hero : "split"),
      quickLinks: sectionQuick(data.nav),
      about: sectionAbout(home),
      programs: sectionPrograms(data.projects),
      news: sectionNews(data.news),
      stories: sectionStories(data.stories),
      impact: sectionImpact(data.impact),
      participation: sectionParticipation(data.support, data.volunteer),
      contact: sectionContact(data.contact)
    };
    var homepage = isObject(data.homepage) ? data.homepage : {};
    var order = homepage.sections && homepage.sections.length ? homepage.sections : DEFAULT_SECTIONS;
    return order.map(function (name) { return parts[name]; }).join("");
  }

  function headHtml(site, fileName, fullTitle, noindex) {
    var lines = [];
    if (noindex) lines.push('<meta name="robots" content="noindex">');
    lines.push('<meta property="og:title" content="' + esc(fullTitle) + '">');
    lines.push('<meta property="og:description" content="' + esc(site.description) + '">');
    lines.push('<meta property="og:type" content="website">');
    var base = str(site.url || "").replace(/\/+$/, "");
    if (base) {
      var href = base + "/" + (fileName === "index.html" ? "" : fileName);
      lines.push('<link rel="canonical" href="' + esc(href) + '">');
      lines.push('<meta property="og:url" content="' + esc(href) + '">');
    }
    return lines.join("\n  ");
  }

  function robotsTxt(site) {
    var base = str(site.url || "").replace(/\/+$/, "");
    var lines = ["User-agent: *", "Disallow: /admin.html", "Disallow: /gallery/"];
    if (base) lines.push("Sitemap: " + base + "/sitemap.xml");
    return lines.join("\n") + "\n";
  }

  function sitemapXml(site, pageFiles) {
    var base = str(site.url || "").replace(/\/+$/, "");
    var urls = pageFiles.filter(function (name) {
      return name !== "admin.html" && name !== "404.html";
    }).map(function (name) {
      return "  <url><loc>" + esc(base + "/" + (name === "index.html" ? "" : name)) + "</loc></url>";
    });
    return '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls.join("\n") + "\n</urlset>\n";
  }

  function notFoundMain() {
    return block("페이지를 찾을 수 없습니다", '<p class="pre">주소가 바뀌었거나 없는 페이지입니다. 메뉴나 홈으로 이동해 주세요.</p>' +
      '<p><a class="button" href="index.html">홈으로 돌아가기</a></p>');
  }

  // ----- 디자인 플랫폼: 검사 (Python 검사와 같은 문장) -----
  function checkDesign(errors, data) {
    var design = data.design;
    if (!isObject(design)) {
      errors.push("config/design.json: 최상위 값은 { } 묶음이어야 합니다.");
      return;
    }
    var presets = isObject(data.presets) ? data.presets : {};
    var name = design.preset;
    if (name === undefined || name === null) return;
    if (!hasKey(presets, name)) {
      errors.push("config/design.json: preset 은 " + Object.keys(presets).join(", ") + " 중 하나여야 합니다.");
      return;
    }
    var hero = design.hero;
    var heroes = presets[name].heroes;
    if (hero !== undefined && hero !== null && (HERO_VARIANTS.indexOf(hero) === -1 || heroes.indexOf(hero) === -1)) {
      errors.push("config/design.json: " + name + " 프리셋의 hero 는 " + heroes.join(", ") + " 중 하나여야 합니다.");
    }
    var width = design.contentWidth;
    if (width !== undefined && width !== null && !hasKey(CONTENT_WIDTHS, width)) {
      errors.push("config/design.json: contentWidth 는 " + Object.keys(CONTENT_WIDTHS).join(", ") + " 중 하나여야 합니다.");
    }
  }

  function checkHomepage(errors, data) {
    var homepage = data.homepage;
    if (!isObject(homepage)) {
      errors.push("config/homepage.json: 최상위 값은 { } 묶음이어야 합니다.");
      return;
    }
    var sections = homepage.sections;
    if (sections === undefined || sections === null) return;
    if (!Array.isArray(sections)) {
      errors.push("config/homepage.json: sections 는 목록이어야 합니다.");
    } else if (sections.some(function (s, i) { return HOMEPAGE_SECTIONS.indexOf(s) === -1 || sections.indexOf(s) !== i; })) {
      errors.push("config/homepage.json: sections 는 " + HOMEPAGE_SECTIONS.join(", ") + " 중에서 한 번씩만 고를 수 있습니다.");
    }
  }

  function checkImpact(errors, impact) {
    if (!isObject(impact)) {
      errors.push("content/impact.json: 최상위 값은 { } 묶음이어야 합니다.");
      return;
    }
    var items = impact.items || [];
    if (!Array.isArray(items)) {
      errors.push("content/impact.json: items 는 목록이어야 합니다.");
      return;
    }
    items.forEach(function (item, i) {
      if (!isObject(item) || !str(item.value || "").trim() || !str(item.label || "").trim()) {
        errors.push("content/impact.json " + (i + 1) + "번: value (숫자)와 label (이름)을 적어 주세요.");
      }
    });
  }

  function checkSiteUrl(errors, site) {
    if (isObject(site) && site.url && !startsWith(str(site.url), "https://")) {
      errors.push("config/site.json: url 은 https:// 로 시작해야 합니다.");
    }
  }

  function checkContactFields(errors, contact) {
    if (!isObject(contact)) return;
    ["address", "phone", "hours"].forEach(function (key) {
      if (key in contact && typeof contact[key] !== "string") errors.push("content/contact.json: " + key + " 는 글자여야 합니다.");
    });
  }

  function buildPages(files, data) {
    var site = data.site, nav = data.nav, theme = data.theme;
    var choice = designChoice(data);
    var style = [themeCss(theme, choice), backgroundCss(theme), files["src/styles/site.css"], files["config/custom.css"] || ""].join("\n");
    var pages = {};

    function page(fileName, title, mainHtml, description, content, noindex) {
      if (fileName !== "index.html") {
        mainHtml = mainHtml.replace("<h2>", "<h1>").replace("</h2>", "</h1>");
      }
      var top = content ? photoHtml(content) : "";
      var bottom = content ? galleryHtml(content) : "";
      var fullTitle = fileName === "index.html" ? site.name : title + " | " + site.name;
      pages[fileName] = fill(files["src/pages/page.html"], {
        lang: esc(site.language || "ko"),
        title: esc(fullTitle),
        description: esc(site.description),
        head: headHtml(site, fileName, fullTitle, noindex),
        script: str(files["src/scripts/reading.js"]).trim(),
        style: style,
        header: headerHtml(files, site, nav, fileName),
        main: top + mainHtml + bottom,
        footer: footerHtml(files, site, data.contact),
        layout: esc(theme.layout),
        menu: esc(theme.menu)
      });
    }

    page("index.html", site.name, homeMain(files, data, choice), site.description || "");

    page("about.html", data.about.title,
      block(data.about.title, '<p class="pre">' + esc(data.about.body) + "</p>"), data.about.body, data.about);
    page("projects.html", data.projects.title,
      block(data.projects.title, itemsHtml(data.projects.items || [], theme.layout)), data.projects.title, data.projects);
    var support = data.support;
    var ways = projectArticles(support.ways || []);
    var supportMain = block(support.title, '<p class="pre">' + esc(support.body) + "</p>");
    if (ways) supportMain += block("후원 방법", ways);
    if (support.notice) supportMain += block("안내", '<p class="pre">' + esc(support.notice) + "</p>");
    page("support.html", support.title, supportMain, support.body, support);
    page("news.html", data.news.title, block(data.news.title, projectArticles(data.news.items || [])), data.news.title, data.news);
    var transparency = data.transparency;
    page("transparency.html", transparency.title,
      block(transparency.title, '<p class="pre">' + esc(transparency.body) + "</p>") +
      block("사업 · 재무 자료", projectArticles(transparency.reports || [])) +
      block("사업비 구성", '<p class="pre">' + esc(transparency.costs) + "</p>") +
      block("외부 확인", '<p class="pre">' + esc(transparency.disclosure) + "</p>"),
      transparency.body, transparency);
    var volunteer = data.volunteer;
    page("volunteer.html", volunteer.title,
      block(volunteer.title, '<p class="pre">' + esc(volunteer.body) + "</p>") +
      block("활동 종류", projectArticles(volunteer.positions || [])) +
      block("신청 방법", '<p class="pre">' + esc(volunteer.apply) + "</p>"),
      volunteer.body, volunteer);
    var privacy = data.privacy;
    page("privacy.html", privacy.title,
      block(privacy.title, '<p class="pre">' + esc(privacy.body) + "</p>") +
      block("처리 항목", projectArticles(privacy.items || [])),
      privacy.body, privacy);
    page("contact.html", data.contact.title,
      block(data.contact.title, '<p class="pre">' + esc(data.contact.body) + "</p>"), data.contact.body, data.contact);
    var connection = supabaseSettings(data);
    var connected = !!(connection.url && connection.key);
    GENERIC_PAGES.forEach(function (name) {
      var content = data[name];
      var body = genericBody(content);
      if (name === "board" && connected) body += boardLiveHtml(files, connection.url, connection.key);
      page(name + ".html", content.title, body, content.body, content);
    });
    (data.custom_pages || []).forEach(function (content) {
      page(content.slug + ".html", content.title, genericBody(content), content.body, content);
    });
    page("admin.html", "관리자", adminMain(files, connection.url, connection.key), ADMIN_INTRO, null, true);
    page("404.html", "페이지를 찾을 수 없습니다", notFoundMain(), "요청한 페이지가 없습니다.", null, true);
    pages["robots.txt"] = robotsTxt(site);
    if (str(site.url || "").trim()) pages["sitemap.xml"] = sitemapXml(site, Object.keys(ROUTES).map(function (r) { return ROUTES[r]; }).filter(function (v, i, a) { return a.indexOf(v) === i; }));
    return pages;
  }

  // 검사를 통과하면 페이지 파일 이름과 내용을 돌려줍니다. 틀리면 오류 목록만 돌려줍니다.
  // 날짜가 오늘보다 뒤인 항목은 뺍니다 (Python 의 drop_unpublished 와 같은 규칙).
  function dropUnpublished(value, today) {
    if (Array.isArray(value)) {
      return value.filter(function (v) {
        return !(isObject(v) && typeof v.publish === "string" && v.publish > today);
      }).map(function (v) { return dropUnpublished(v, today); });
    }
    if (isObject(value)) {
      var out = {};
      Object.keys(value).forEach(function (k) { out[k] = dropUnpublished(value[k], today); });
      return out;
    }
    return value;
  }

  function localToday() {
    var d = new Date();
    var pad = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function build(files, today) {
    requireSchema();
    var checked = validate(files);
    if (checked.errors.length) return { ok: false, errors: checked.errors, pages: {} };
    var data = dropUnpublished(checked.data, today || localToday());
    return { ok: true, errors: [], pages: buildPages(files, data) };
  }

  var api = { useSchema: useSchema, validate: validate, build: build, esc: esc, fill: fill };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.SiteEngine = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
