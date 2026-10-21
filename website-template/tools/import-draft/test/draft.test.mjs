import { test } from "node:test";
import assert from "node:assert/strict";
import { markdownToDraft } from "../draft.mjs";

test("첫 제목과 첫 문단으로 소식 항목을 만든다", () => {
  const md = "# 2026년 복지관 소식\n\n2026년 1월 15일에 시작하는 식사 배달 안내입니다.\n\n- 화요일 배달\n";
  const draft = markdownToDraft(md, { source: "소식.hwpx", format: "hwpx" });
  assert.deepEqual(draft.suggestedNewsItem, {
    title: "2026년 복지관 소식",
    date: "2026-01-15",
    summary: "2026년 1월 15일에 시작하는 식사 배달 안내입니다.",
    url: ""
  });
  assert.deepEqual(draft.bullets, ["화요일 배달"]);
  assert.deepEqual(draft.warnings, []);
});

test("날짜 형식 2026.10.5 와 2026-03-07 을 모두 읽는다", () => {
  const a = markdownToDraft("# 제목\n\n행사일: 2026.10.5\n", { source: "a.txt", format: "pdf" });
  const b = markdownToDraft("# 제목\n\n2026-03-07 접수\n", { source: "b.txt", format: "pdf" });
  assert.equal(a.suggestedNewsItem.date, "2026-10-05");
  assert.equal(b.suggestedNewsItem.date, "2026-03-07");
});

test("잘못된 날짜는 건너뛰고 경고한다", () => {
  const draft = markdownToDraft("# 제목\n\n2026-13-40 까지\n", { source: "c.txt", format: "pdf" });
  assert.equal(draft.suggestedNewsItem.date, "");
  assert.ok(draft.warnings.some((w) => w.includes("날짜")));
});

test("표는 행 단위로 나누고 구분선은 버린다", () => {
  const md = "# 안내\n\n| 항목 | 내용 |\n| --- | --- |\n| 장소 | 본관 2층 |\n";
  const draft = markdownToDraft(md, { source: "d.hwpx", format: "hwpx" });
  assert.deepEqual(draft.tables, [[["항목", "내용"], ["장소", "본관 2층"]]]);
});

test("제목이 없으면 파일 이름을 쓰고 경고한다", () => {
  const draft = markdownToDraft("", { source: "빈문서.pdf", format: "pdf" });
  assert.equal(draft.suggestedNewsItem.title, "빈문서");
  assert.ok(draft.warnings.some((w) => w.includes("제목")));
});

test("주민등록번호는 경고만 하고 값은 출력에 넣지 않는다", () => {
  const secret = "900101-1234567";
  const draft = markdownToDraft(`# 신청\n\n주민번호 ${secret}\n`, { source: "e.hwpx", format: "hwpx" });
  assert.ok(draft.warnings.some((w) => w.includes("주민등록번호")));
  assert.ok(!JSON.stringify(draft).includes(secret));
});

test("긴 요약은 200자로 줄이고 알려 준다", () => {
  const long = "가".repeat(250);
  const draft = markdownToDraft(`# 제목\n\n${long}\n`, { source: "f.txt", format: "pdf" });
  assert.equal([...draft.suggestedNewsItem.summary].length, 201);
  assert.ok(draft.warnings.some((w) => w.includes("200자")));
});

test("구조 문서 한 건도 요약에서 빠지지 않는다", () => {
  const draft = markdownToDraft("# 한 줄 제목\n", { source: "g.hwp", format: "hwp" });
  assert.equal(draft.suggestedNewsItem.summary, "");
  assert.ok(draft.warnings.some((w) => w.includes("본문")));
});
