(function () {
  var section = document.querySelector("section.admin");
  var box = document.getElementById("admin-app");
  var url = section.getAttribute("data-url");
  var key = section.getAttribute("data-key");
  if (!url || !key || !window.supabase) {
    box.textContent = "Supabase 가 아직 연결되지 않았습니다. 편집기의 Supabase 연결 칸에 주소와 키를 넣고 다시 내려받으세요.";
    return;
  }
  var client = window.supabase.createClient(url, key);

  function el(tag, text) {
    var node = document.createElement(tag);
    node.textContent = text;
    return node;
  }

  function showLogin(message) {
    box.replaceChildren();
    var form = document.createElement("form");
    var email = document.createElement("input");
    email.type = "email"; email.required = true; email.autocomplete = "username"; email.name = "email";
    var password = document.createElement("input");
    password.type = "password"; password.required = true; password.autocomplete = "current-password"; password.name = "password";
    var button = document.createElement("button");
    button.type = "submit"; button.textContent = "로그인";
    var status = el("p", message || "");
    form.append(el("label", "이메일"), email, el("label", "비밀번호"), password, button, status);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      status.textContent = "로그인하는 중입니다...";
      client.auth.signInWithPassword({ email: email.value, password: password.value }).then(function (result) {
        if (result.error) status.textContent = "로그인하지 못했습니다. 이메일과 비밀번호를 확인하세요.";
        else showPosts();
      });
    });
    box.append(form);
  }

  function showPosts() {
    client.auth.getSession().then(function (result) {
      if (!result.data.session) return showLogin();
      box.replaceChildren();
      var top = document.createElement("div");
      var logout = document.createElement("button");
      logout.type = "button"; logout.textContent = "로그아웃";
      logout.addEventListener("click", function () { client.auth.signOut().then(function () { showLogin("로그아웃했습니다."); }); });
      top.append(el("p", "관리자로 로그인했습니다. 아래 글을 확인해 승인하거나 지우세요."), logout);
      var list = document.createElement("div");
      box.append(top, el("h3", "승인 대기 글"), list);
      client.from("board_posts").select("id,title,body,author_name,created_at").eq("approved", false)
        .order("created_at", { ascending: false }).then(function (res) {
          if (res.error) { list.textContent = "글을 불러오지 못했습니다: " + res.error.message; return; }
          if (!res.data.length) { list.textContent = "승인을 기다리는 글이 없습니다."; return; }
          res.data.forEach(function (post) {
            var item = document.createElement("article");
            var approve = document.createElement("button");
            approve.type = "button"; approve.textContent = "승인";
            var remove = document.createElement("button");
            remove.type = "button"; remove.className = "secondary"; remove.textContent = "삭제";
            approve.addEventListener("click", function () {
              client.from("board_posts").update({ approved: true }).eq("id", post.id).then(showPosts);
            });
            remove.addEventListener("click", function () {
              client.from("board_posts").delete().eq("id", post.id).then(showPosts);
            });
            item.append(el("h3", post.title), el("p", (post.author_name || "이름 없음") + " · " + post.created_at), el("p", post.body), approve, remove);
            list.append(item);
          });
        });
    });
  }

  showPosts();
})();
