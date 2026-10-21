(function () {
  var section = document.querySelector("section.live");
  var url = section.getAttribute("data-url");
  var key = section.getAttribute("data-key");
  var list = document.getElementById("live-posts");
  var form = document.getElementById("post-form");
  var message = document.getElementById("post-message");
  if (!url || !key || !window.supabase) {
    list.textContent = "";
    form.hidden = true;
    return;
  }
  var client = window.supabase.createClient(url, key);

  // 방문자가 개인정보를 올리지 않도록 보내기 전에 확인합니다. (서버에서도 한 번 더 막는 것을 권장합니다)
  var PATTERNS = [
    [/\d{6}-?[1-4]\d{6}/, "주민등록번호처럼 보이는 숫자"],
    [/(?:\d[ -]?){13,16}/, "카드번호처럼 보이는 숫자"],
    [/01[016789]-?\d{3,4}-?\d{4}/, "휴대전화 번호"],
    [/\d{2,6}-\d{2,6}-\d{6,8}/, "계좌번호처럼 보이는 숫자"]
  ];

  function personalInfo(text) {
    for (var i = 0; i < PATTERNS.length; i++) {
      if (PATTERNS[i][0].test(text)) return PATTERNS[i][1];
    }
    return "";
  }

  function load() {
    client.from("board_posts").select("id,title,body,author_name,created_at").eq("approved", true)
      .order("created_at", { ascending: false }).limit(50).then(function (res) {
        list.replaceChildren();
        if (res.error) { list.textContent = "글을 불러오지 못했습니다."; return; }
        res.data.forEach(function (post) {
          var item = document.createElement("article");
          var title = document.createElement("h3");
          title.textContent = post.title;
          var meta = document.createElement("p");
          meta.textContent = (post.author_name || "이름 없음") + " · " + post.created_at;
          var details = document.createElement("details");
          var summary = document.createElement("summary");
          summary.textContent = "자세히 보기";
          var body = document.createElement("p");
          body.className = "pre";
          body.textContent = post.body;
          details.append(summary, body);
          item.append(title, meta, details);
          list.append(item);
        });
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var title = form.elements.title.value.trim();
    var body = form.elements.body.value.trim();
    var author = form.elements.author.value.trim();
    var found = personalInfo(title + " " + body + " " + author);
    if (found) {
      message.textContent = "개인정보가 있는 것 같습니다 (" + found + "). 지우고 다시 올려 주세요.";
      return;
    }
    client.from("board_posts").insert({ title: title, body: body, author_name: author || null }).then(function (res) {
      if (res.error) { message.textContent = "올리지 못했습니다. 잠시 후 다시 시도해 주세요."; return; }
      form.reset();
      message.textContent = "글을 보냈습니다. 확인한 뒤에 올라갑니다.";
    });
  });

  load();
})();
