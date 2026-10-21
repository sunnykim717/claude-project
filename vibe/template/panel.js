  const copyBtn = document.getElementById("copy-code");
  const source = document.getElementById("source");
  const codeMsg = document.getElementById("code-msg");
  const GITHUB = __GITHUB_JSON__;

  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(source.value);
      codeMsg.textContent = "코드를 복사했습니다. index.html 파일에 붙여 넣어 저장하세요.";
    } catch (err) {
      source.focus();
      source.select();
      const ok = document.execCommand("copy");
      codeMsg.textContent = ok
        ? "코드를 복사했습니다. index.html 파일에 붙여 넣어 저장하세요."
        : "복사하지 못했습니다. 코드 상자를 눌러 직접 선택한 뒤 복사해 주세요.";
    }
  });

  document.getElementById("download-code").addEventListener("click", () => {
    const blob = new Blob([source.value], { type: "text/html;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "index.html";
    link.click();
    URL.revokeObjectURL(link.href);
    codeMsg.textContent = "index.html 을 내려받았습니다. GitHub 에 올릴 때는 '파일 추가 → 파일 업로드'를 쓰세요.";
  });

  const githubBtn = document.getElementById("github-link");
  if (githubBtn && GITHUB) {
    githubBtn.addEventListener("click", () => {
      const url = `https://github.com/${GITHUB.repo}/new/${GITHUB.branch}`
        + `?filename=${encodeURIComponent(GITHUB.path)}&value=${encodeURIComponent(source.value)}`;
      if (url.length > __GITHUB_LINK_LIMIT__) {
        codeMsg.textContent = "코드가 길어 링크로 보낼 수 없습니다. '코드 복사'를 누른 뒤 GitHub 에서 붙여 넣어 주세요.";
        return;
      }
      window.open(url, "_blank", "noopener");
      codeMsg.textContent = "GitHub 새 파일 화면을 열었습니다. 그 화면에서 Commit 을 눌러 저장하세요.";
    });
  }
