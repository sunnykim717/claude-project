// 문서 본문(Markdown)을 소식 초안으로 바꾸는 순수 함수입니다.
// kordoc 을 가져오지 않으므로 npm 설치 없이도 테스트할 수 있습니다.

const RRN = /\d{6}-[1-4]\d{6}/;
const PHONE = /0\d{1,2}-\d{3,4}-\d{4}/;
const SUMMARY_MAX = 200;
const TITLE_MAX = 80;

function pad(n) {
  return String(n).padStart(2, "0");
}

function findDate(text) {
  const iso = text.match(/(\d{4})[-./]\s?(\d{1,2})[-./]\s?(\d{1,2})/);
  const korean = text.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일/);
  const m = iso || korean;
  if (!m) return "";
  const month = Number(m[2]);
  const day = Number(m[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) return "";
  return `${m[1]}-${pad(month)}-${pad(day)}`;
}

function cut(text, max) {
  const chars = [...text];
  return chars.length > max ? chars.slice(0, max).join("") + "…" : text;
}

// Markdown 한 줄씩 훑어서 제목, 본문, 목록, 표로 나눕니다.
function splitBlocks(markdown) {
  const headings = [];
  const paragraphs = [];
  const bullets = [];
  const tables = [];
  let table = null;

  for (const raw of markdown.split(/\r?\n/)) {
    const line = raw.trim();
    if (line.startsWith("|")) {
      if (/^\|?\s*:?-{3,}/.test(line)) continue;
      const cells = line.split("|").map((c) => c.trim());
      if (cells[0] === "") cells.shift();
      if (cells.length && cells[cells.length - 1] === "") cells.pop();
      if (!table) {
        table = [];
        tables.push(table);
      }
      table.push(cells);
      continue;
    }
    table = null;
    if (!line) continue;
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading) {
      headings.push(heading[1].trim());
      continue;
    }
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      bullets.push(bullet[1].trim());
      continue;
    }
    paragraphs.push(line);
  }
  return { headings, paragraphs, bullets, tables };
}

// 주민등록번호 모양은 초안 파일에도 남기지 않습니다. 찾으면 가려서 씁니다.
function maskRrn(text) {
  return text.replace(new RegExp(RRN.source, "g"), "******-*******");
}

export function markdownToDraft(markdown, { source, format }) {
  const raw = splitBlocks(markdown);
  const hasRrn = RRN.test(markdown);
  const mask = (list) => list.map((text) => (typeof text === "string" ? maskRrn(text) : text.map(mask)));
  const { headings, paragraphs, bullets, tables } = {
    headings: mask(raw.headings),
    paragraphs: mask(raw.paragraphs),
    bullets: mask(raw.bullets),
    tables: mask(raw.tables)
  };
  const warnings = [];
  const baseName = source.replace(/\.[^.]+$/, "");

  let title = headings[0] || paragraphs[0] || bullets[0] || "";
  if (!title) {
    title = baseName;
    warnings.push("제목을 찾지 못해 파일 이름을 제목으로 썼습니다. 직접 고쳐 주세요.");
  }
  title = cut(title, TITLE_MAX);

  const summarySource = paragraphs.find((p) => p !== title) || bullets[0] || "";
  const summary = cut(summarySource, SUMMARY_MAX);
  if ([...summarySource].length > SUMMARY_MAX) {
    warnings.push(`요약을 ${SUMMARY_MAX}자로 줄였습니다. 전체 내용은 body 에 있습니다.`);
  }

  const everything = [title, ...headings, ...paragraphs, ...bullets, ...tables.flat(2)].join("\n");
  const date = findDate(everything);
  if (!date) warnings.push("날짜를 찾지 못했습니다. date 를 직접 적어 주세요.");
  if (hasRrn) {
    warnings.push("주민등록번호 형태의 숫자가 있습니다. 공개 전에 반드시 지워 주세요. (값은 여기에 적지 않습니다)");
  }
  if (PHONE.test(everything)) {
    warnings.push("전화번호 형태가 있습니다. 공개해도 되는지 확인해 주세요.");
  }
  if (!paragraphs.length && !bullets.length) {
    warnings.push("본문 글을 찾지 못했습니다. 표나 그림으로만 된 문서일 수 있습니다.");
  }

  return {
    source,
    format,
    // content/news.json 의 items 한 칸과 같은 모양입니다. 검토 후 복사해 붙이세요.
    suggestedNewsItem: { title, date, summary, url: "" },
    headings,
    body: paragraphs,
    bullets,
    tables,
    warnings
  };
}
