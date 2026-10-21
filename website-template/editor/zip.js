/*
 * 아주 작은 zip 만들기 (압축 없이 담기). 브라우저와 Node 에서 같이 씁니다.
 * entries: [{ name: "config/site.json", text: "..." }, ...]  -> Uint8Array (zip 파일 내용)
 */
(function (root) {
  "use strict";

  var CRC_TABLE = (function () {
    var table = [];
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
      table[n] = c >>> 0;
    }
    return table;
  })();

  function crc32(bytes) {
    var c = 0xFFFFFFFF;
    for (var i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  function buildZip(entries, when) {
    var enc = new TextEncoder();
    var d = when || new Date();
    var dosTime = (d.getHours() << 11) | (d.getMinutes() << 5) | Math.floor(d.getSeconds() / 2);
    var dosDate = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    var parts = [], central = [], offset = 0;

    entries.forEach(function (entry) {
      var name = enc.encode(entry.name);
      var data = enc.encode(entry.text);
      var crc = crc32(data);

      var local = new Uint8Array(30 + name.length);
      var lv = new DataView(local.buffer);
      lv.setUint32(0, 0x04034b50, true);
      lv.setUint16(4, 20, true);
      lv.setUint16(6, 0x0800, true);          // 파일 이름은 UTF-8
      lv.setUint16(8, 0, true);               // 압축 없음
      lv.setUint16(10, dosTime, true);
      lv.setUint16(12, dosDate, true);
      lv.setUint32(14, crc, true);
      lv.setUint32(18, data.length, true);
      lv.setUint32(22, data.length, true);
      lv.setUint16(26, name.length, true);
      lv.setUint16(28, 0, true);
      local.set(name, 30);
      parts.push(local, data);

      var cen = new Uint8Array(46 + name.length);
      var cv = new DataView(cen.buffer);
      cv.setUint32(0, 0x02014b50, true);
      cv.setUint16(4, 20, true);
      cv.setUint16(6, 20, true);
      cv.setUint16(8, 0x0800, true);
      cv.setUint16(10, 0, true);
      cv.setUint16(12, dosTime, true);
      cv.setUint16(14, dosDate, true);
      cv.setUint32(16, crc, true);
      cv.setUint32(20, data.length, true);
      cv.setUint32(24, data.length, true);
      cv.setUint16(28, name.length, true);
      cv.setUint16(30, 0, true);
      cv.setUint16(32, 0, true);
      cv.setUint16(34, 0, true);
      cv.setUint16(36, 0, true);
      cv.setUint32(38, 0, true);
      cv.setUint32(42, offset, true);
      cen.set(name, 46);
      central.push(cen);
      offset += local.length + data.length;
    });

    var cenSize = central.reduce(function (sum, part) { return sum + part.length; }, 0);
    var end = new Uint8Array(22);
    var ev = new DataView(end.buffer);
    ev.setUint32(0, 0x06054b50, true);
    ev.setUint16(8, entries.length, true);
    ev.setUint16(10, entries.length, true);
    ev.setUint32(12, cenSize, true);
    ev.setUint32(16, offset, true);

    var all = parts.concat(central, [end]);
    var total = all.reduce(function (sum, part) { return sum + part.length; }, 0);
    var out = new Uint8Array(total);
    var pos = 0;
    all.forEach(function (part) { out.set(part, pos); pos += part.length; });
    return out;
  }

  var api = { buildZip: buildZip, crc32: crc32 };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.SiteZip = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
