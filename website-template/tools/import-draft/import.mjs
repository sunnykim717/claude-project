#!/usr/bin/env node
// 문서 파일을 읽어 소식 초안(JSON)을 만듭니다. 홈페이지 파일(content/)은 바꾸지 않습니다.
// 사용: node import.mjs 파일1 파일2 ... [--out 폴더]
// 기본 출력 폴더는 website-template/drafts 입니다 (저장소에 올라가지 않도록 .gitignore 에 있습니다).

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "kordoc";
import { markdownToDraft } from "./draft.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const DEFAULT_OUT = resolve(HERE, "../../drafts");

function parseArgs(argv) {
  const files = [];
  let out = DEFAULT_OUT;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--out") {
      out = resolve(argv[++i] || "");
    } else {
      files.push(argv[i]);
    }
  }
  return { files, out };
}

async function importOne(file, outDir) {
  const name = basename(file);
  const buf = await readFile(file);
  const result = await parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  if (!result.success) {
    console.error(`건너뜀 ${name}: ${result.error}`);
    return false;
  }
  const draft = markdownToDraft(result.markdown, { source: name, format: result.fileType });
  const target = join(outDir, `${name.replace(/\.[^.]+$/, "")}.draft.json`);
  await writeFile(target, JSON.stringify(draft, null, 2) + "\n", "utf8");
  console.log(`${name} → ${target} (경고 ${draft.warnings.length}건)`);
  for (const warning of draft.warnings) console.log(`  - ${warning}`);
  return true;
}

async function main() {
  const { files, out } = parseArgs(process.argv.slice(2));
  if (!files.length) {
    console.error("사용: node import.mjs 파일1 [파일2 ...] [--out 폴더]");
    process.exit(2);
  }
  await mkdir(out, { recursive: true });
  let failed = 0;
  for (const file of files) {
    if (!(await importOne(file, out))) failed++;
  }
  if (failed) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
