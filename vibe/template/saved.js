  const savedList = document.getElementById("saved-list");
  const savedCount = document.getElementById("saved-count");
  const savedMsg = document.getElementById("saved-msg");
  let recordNotice = "";

  function loadRecords() {
    let raw = null;
    try {
      raw = localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return [];
    }
    if (raw === null) return [];
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    } catch (err) { /* 아래에서 따로 보관합니다 */ }
    // 읽을 수 없는 기록은 지우지 않고 다른 칸에 그대로 보관한 뒤, 빈 목록으로 보여 줍니다.
    try {
      localStorage.setItem(STORAGE_KEY + ":broken:" + Date.now(), raw);
      localStorage.removeItem(STORAGE_KEY); // 같은 보관본이 반복해서 만들어지지 않도록 원래 칸을 비웁니다
      recordNotice = "저장된 기록을 읽을 수 없어 따로 보관했습니다. 새 신청은 정상적으로 저장됩니다.";
    } catch (err) {
      recordNotice = "저장된 기록을 읽을 수 없고 보관도 되지 않았습니다. 백업 파일을 먼저 받아 두세요.";
    }
    return [];
  }

  function storeRecords(records) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
      return true;
    } catch (err) {
      return false;
    }
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("ko-KR");
  }

  function renderRecords() {
    const records = loadRecords();
    savedCount.textContent = `저장된 신청 ${records.length}건`;
    if (recordNotice) savedMsg.textContent = recordNotice;
    const table = document.createElement("table");
    const head = document.createElement("tr");
    for (const text of ["저장 시각", ...FIELDS.map((f) => f.label)]) {
      const th = document.createElement("th");
      th.textContent = text;
      head.append(th);
    }
    table.append(head);
    for (const record of records) {
      const tr = document.createElement("tr");
      for (const text of [formatTime(record.at), ...FIELDS.map((f) => record.data[f.id] || "-")]) {
        const td = document.createElement("td");
        td.textContent = text;
        tr.append(td);
      }
      table.append(tr);
    }
    savedList.replaceChildren(table);
  }

  function saveRecord() {
    const records = loadRecords();
    records.push({ at: new Date().toISOString(), data: currentRecord() });
    savedMsg.textContent = storeRecords(records)
      ? "이 기기에 저장했습니다."
      : "이 브라우저에서는 저장할 수 없습니다. CSV 로 내려받아 보관해 주세요.";
    renderRecords();
  }

  function csvCell(value) {
    let text = String(value ?? "");
    if (/^[=+\-@]/.test(text)) text = "'" + text;
    return `"${text.replace(/"/g, '""')}"`;
  }

  document.getElementById("download-csv").addEventListener("click", () => {
    const records = loadRecords();
    const header = ["저장 시각", ...FIELDS.map((f) => f.label)].map(csvCell).join(",");
    const rows = records.map((r) => [r.at, ...FIELDS.map((f) => r.data[f.id] || "")].map(csvCell).join(","));
    const blob = new Blob(["﻿" + [header, ...rows].join("\r\n")], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "신청목록.csv";
    link.click();
    URL.revokeObjectURL(link.href);
    savedMsg.textContent = `${records.length}건을 내려받았습니다.`;
  });

  document.getElementById("clear-saved").addEventListener("click", () => {
    if (!confirm("이 기기에 저장된 신청 기록을 모두 지울까요? 되돌릴 수 없습니다.")) return;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (err) { /* 저장소를 쓸 수 없으면 지울 것도 없습니다 */ }
    savedMsg.textContent = "저장 목록을 지웠습니다.";
    renderRecords();
  });

  function backupFile() {
    const text = JSON.stringify({
      format: "vibe-app-backup",
      version: 1,
      app: APP_NAME,
      exportedAt: new Date().toISOString(),
      records: loadRecords(),
    }, null, 2);
    const name = `${APP_NAME}-백업-${new Date().toISOString().slice(0, 10)}.json`;
    return new File([text], name, { type: "application/json" });
  }

  document.getElementById("make-backup").addEventListener("click", () => {
    const file = backupFile();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(file);
    link.download = file.name;
    link.click();
    URL.revokeObjectURL(link.href);
    savedMsg.textContent = "백업 파일을 내려받았습니다. 이 파일을 보내거나 다른 기기에서 불러오세요.";
  });

  document.getElementById("share-backup").addEventListener("click", async () => {
    const file = backupFile();
    if (!navigator.canShare || !navigator.canShare({ files: [file] })) {
      savedMsg.textContent = "이 브라우저에서는 바로 보내기를 쓸 수 없습니다. '백업 파일 만들기'로 받은 뒤 직접 보내 주세요.";
      return;
    }
    try {
      await navigator.share({ files: [file], title: file.name });
      savedMsg.textContent = "백업 파일을 보냈습니다.";
    } catch (err) {
      if (err && err.name === "AbortError") return; // 사용자가 보내기를 취소한 경우
      savedMsg.textContent = "보내지 못했습니다. '백업 파일 만들기'로 받은 뒤 직접 보내 주세요.";
    }
  });

  document.getElementById("restore-backup").addEventListener("click", () => {
    document.getElementById("restore-file").click();
  });

  document.getElementById("restore-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      savedMsg.textContent = "백업 파일이 너무 큽니다. 2MB 이하의 백업 파일만 불러올 수 있습니다.";
      return;
    }
    let backup = null;
    try {
      backup = JSON.parse(await file.text());
    } catch (err) {
      savedMsg.textContent = "백업 파일을 읽을 수 없습니다. 이 페이지에서 만든 백업 파일인지 확인해 주세요.";
      return;
    }
    if (!backup || backup.format !== "vibe-app-backup" || !Array.isArray(backup.records)) {
      savedMsg.textContent = "이 페이지의 백업 파일이 아닙니다.";
      return;
    }
    if (backup.records.length > 5000) {
      savedMsg.textContent = "백업 파일의 기록이 5,000건을 넘습니다. 나누어 불러와 주세요.";
      return;
    }
    const current = loadRecords();
    const seen = new Set(current.map((r) => r.at + JSON.stringify(r.data)));
    let added = 0;
    for (const r of backup.records) {
      if (!r || typeof r.at !== "string" || !r.data || typeof r.data !== "object") continue;
      const key = r.at + JSON.stringify(r.data);
      if (seen.has(key)) continue;
      seen.add(key);
      current.push({ at: r.at, data: r.data });
      added++;
    }
    const note = backup.app && backup.app !== APP_NAME ? " (다른 신청 페이지의 백업입니다)" : "";
    savedMsg.textContent = storeRecords(current)
      ? `${added}건을 불러와 합쳤습니다.${note}`
      : "이 브라우저에서는 저장할 수 없어 불러오지 못했습니다.";
    renderRecords();
  });

  renderRecords();
