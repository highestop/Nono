#!/usr/bin/env node
/* List or safely replace existing Dota 2 local replay titles in a VBKV index. */

const fs = require("fs");

function usage() {
  console.error("Usage:\n  node replay_notes.js list <downloaded_replays_info.dat>\n  node replay_notes.js title <downloaded_replays_info.dat> <match-id> <new-title> [--write]");
  process.exit(2);
}

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value >>> 1) ^ (value & 1 ? 0xedb88320 : 0);
    }
  }
  return (value ^ 0xffffffff) >>> 0;
}

function readIndex(indexPath) {
  const data = fs.readFileSync(indexPath);
  if (data.subarray(0, 4).toString("ascii") !== "VBKV") {
    throw new Error("Not a VBKV replay index.");
  }
  const expected = data.readUInt32LE(4);
  const actual = crc32(data.subarray(8));
  if (expected !== actual) {
    throw new Error(`VBKV CRC-32 mismatch: header ${expected.toString(16)}, calculated ${actual.toString(16)}.`);
  }
  return data;
}

function records(data) {
  const marker = /download(\d+)\0/g;
  const latin1 = data.toString("latin1");
  const offsets = [];
  let found;
  while ((found = marker.exec(latin1))) offsets.push({ number: Number(found[1]), start: found.index });

  return offsets.map((record, index) => {
    const end = index + 1 < offsets.length ? offsets[index + 1].start : data.length;
    const section = data.subarray(record.start, end);
    const matchKey = section.indexOf(Buffer.from("match_id\0"));
    if (matchKey < 0 || matchKey + 17 > section.length) return { ...record, end, matchId: null, title: null };
    const matchId = section.readBigUInt64LE(matchKey + 9).toString();
    const titleKey = section.indexOf(Buffer.from("title\0"));
    const titleStart = titleKey < 0 ? -1 : titleKey + 6;
    const titleEnd = titleStart < 0 ? -1 : section.indexOf(0, titleStart);
    return {
      ...record,
      end,
      matchId,
      title: titleStart < 0 || titleEnd < 0 ? null : section.subarray(titleStart, titleEnd).toString("utf8"),
      titleStart: titleStart < 0 ? -1 : record.start + titleStart,
      titleEnd: titleEnd < 0 ? -1 : record.start + titleEnd,
    };
  });
}

function backupPath(indexPath) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `${indexPath}.bak-${stamp}`;
}

const [command, indexPath, matchId, newTitle, ...options] = process.argv.slice(2);
if (!command || !indexPath || !["list", "title"].includes(command)) usage();

try {
  const data = readIndex(indexPath);
  const entries = records(data);

  if (command === "list") {
    for (const entry of entries) {
      if (entry.matchId) console.log(`${entry.matchId}\t${entry.title ?? "(no title)"}`);
    }
    process.exit(0);
  }

  if (!matchId || newTitle === undefined) usage();
  if (newTitle.includes("\0")) throw new Error("A title cannot contain a NUL character.");
  const entry = entries.find((candidate) => candidate.matchId === matchId);
  if (!entry) throw new Error(`No record found for match ID ${matchId}.`);
  if (entry.titleStart < 0) throw new Error(`Match ID ${matchId} has no existing title field; refusing to alter the binary structure.`);

  const replacement = Buffer.from(`${newTitle}\0`, "utf8");
  const output = Buffer.concat([data.subarray(0, entry.titleStart), replacement, data.subarray(entry.titleEnd + 1)]);
  output.writeUInt32LE(crc32(output.subarray(8)), 4);
  const write = options.includes("--write");
  console.log(`Match ${matchId}: ${entry.title || "(empty title)"} -> ${newTitle}`);
  if (!write) {
    console.log("Dry run. Add --write to create a backup and apply the change.");
    process.exit(0);
  }

  const backup = backupPath(indexPath);
  fs.copyFileSync(indexPath, backup, fs.constants.COPYFILE_EXCL);
  fs.writeFileSync(indexPath, output);
  readIndex(indexPath);
  console.log(`Updated ${indexPath}`);
  console.log(`Backup: ${backup}`);
} catch (error) {
  console.error(`Error: ${error.message}`);
  process.exit(1);
}
