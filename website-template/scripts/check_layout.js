// 생성된 페이지를 360·768·1440px 화면에서 열어 가로 넘침과 빈 제목 구조를 확인합니다.
// 사용법: node scripts/check_layout.js <사이트 폴더> [페이지 ...]
// 실행에는 Playwright 가 필요합니다 (Chromium 경로는 PLAYWRIGHT_CHROMIUM 환경변수로 지정할 수 있습니다).
const path = require("path");
const fs = require("fs");

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  console.error("Playwright 가 없습니다. npm install playwright 후 다시 실행하세요.");
  process.exit(2);
}

const dir = path.resolve(process.argv[2] || "dist");
const pages = process.argv.slice(3).length ? process.argv.slice(3) : ["index.html", "about.html"];
const widths = [360, 768, 1440];

(async () => {
  const launch = { args: ["--no-sandbox"] };
  if (process.env.PLAYWRIGHT_CHROMIUM) launch.executablePath = process.env.PLAYWRIGHT_CHROMIUM;
  const browser = await chromium.launch(launch);
  let failures = 0;
  const rows = [];
  for (const page of pages) {
    if (!fs.existsSync(path.join(dir, page))) {
      rows.push(`${page}: 파일이 없습니다`);
      failures += 1;
      continue;
    }
    for (const width of widths) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const tab = await context.newPage();
      const errors = [];
      tab.on("pageerror", (e) => errors.push(e.message));
      await tab.goto("file://" + path.join(dir, page));
      const result = await tab.evaluate(() => {
        const overflow = document.documentElement.scrollWidth - window.innerWidth;
        const headings = Array.from(document.querySelectorAll("h1, h2, h3")).length;
        const h1 = document.querySelectorAll("h1").length;
        return { overflow, headings, h1 };
      });
      const ok = result.overflow <= 0 && result.h1 === 1 && errors.length === 0;
      if (!ok) failures += 1;
      rows.push(`${ok ? "통과" : "실패"}  ${page} @${width}px  가로 넘침 ${Math.max(0, result.overflow)}px  제목 h1 ${result.h1}개${errors.length ? "  오류: " + errors.join("; ") : ""}`);
      await context.close();
    }
  }
  await browser.close();
  console.log(rows.join("\n"));
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
