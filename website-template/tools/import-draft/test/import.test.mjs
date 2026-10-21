// 실제 kordoc 으로 HWPX 를 만들고 읽는 끝까지 확인합니다. npm install 뒤에만 돌아갑니다.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { mkdtemp, writeFile, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const TOOL = resolve(HERE, "..");
const installed = existsSync(join(TOOL, "node_modules", "kordoc"));

test("HWPX 한 건을 읽어 초안 JSON 을 만든다", { skip: !installed && "npm install 을 먼저 실행하세요" }, async () => {
  const { markdownToHwpx } = await import("kordoc");
  const dir = await mkdtemp(join(tmpdir(), "draft-"));
  const input = join(dir, "소식.hwpx");
  const out = join(dir, "out");
  const md = "# 2026년 복지관 소식\n\n2026-02-03 시작하는 식사 배달입니다.\n\n- 화요일\n";
  await writeFile(input, Buffer.from(await markdownToHwpx(md)));
  execFileSync(process.execPath, [join(TOOL, "import.mjs"), input, "--out", out], { stdio: "pipe" });
  const draft = JSON.parse(await readFile(join(out, "소식.draft.json"), "utf8"));
  assert.equal(draft.format, "hwpx");
  assert.equal(draft.suggestedNewsItem.title, "2026년 복지관 소식");
  assert.equal(draft.suggestedNewsItem.date, "2026-02-03");
  assert.deepEqual(draft.bullets, ["화요일"]);
});
