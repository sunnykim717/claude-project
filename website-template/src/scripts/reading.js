(function () {
  // 방문자 읽기 설정: 글자 크기, 고대비, 움직임 줄이기. 이 브라우저에만 저장하며 저장소가 막혀도 기본 화면은 그대로 나옵니다.
  var root = document.documentElement;
  var KEY = "reading-settings";
  var SIZES = ["small", "normal", "large", "xlarge"];

  function load() {
    var base = { size: "normal", contrast: false, motion: false };
    try {
      var saved = JSON.parse(localStorage.getItem(KEY));
      if (saved && typeof saved === "object") {
        if (SIZES.indexOf(saved.size) !== -1) base.size = saved.size;
        base.contrast = saved.contrast === true;
        base.motion = saved.motion === true;
      }
    } catch (e) { /* 저장된 값을 읽지 못하면 기본값을 씁니다 */ }
    return base;
  }

  function save(state) {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* 저장하지 못해도 이번 화면에는 적용됩니다 */ }
  }

  function apply(state) {
    root.setAttribute("data-text-size", state.size);
    if (state.contrast) root.setAttribute("data-contrast", "high"); else root.removeAttribute("data-contrast");
    if (state.motion) root.setAttribute("data-motion", "reduce"); else root.removeAttribute("data-motion");
  }

  var state = load();
  apply(state);

  var bar = document.querySelector("[data-reading]");
  if (!bar) return;
  bar.hidden = false;

  function refresh() {
    bar.querySelector('[data-read="contrast"]').setAttribute("aria-pressed", String(state.contrast));
    bar.querySelector('[data-read="motion"]').setAttribute("aria-pressed", String(state.motion));
  }

  bar.addEventListener("click", function (event) {
    var button = event.target.closest("[data-read]");
    if (!button || !bar.contains(button)) return;
    var action = button.getAttribute("data-read");
    var index = SIZES.indexOf(state.size);
    if (action === "smaller") state.size = SIZES[Math.max(0, index - 1)];
    if (action === "larger") state.size = SIZES[Math.min(SIZES.length - 1, index + 1)];
    if (action === "contrast") state.contrast = !state.contrast;
    if (action === "motion") state.motion = !state.motion;
    if (action === "reset") state = { size: "normal", contrast: false, motion: false };
    apply(state);
    save(state);
    refresh();
  });

  refresh();
})();
