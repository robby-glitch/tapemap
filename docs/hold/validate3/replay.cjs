// replay.cjs OUT_DIR ENGINE3 -- rev 2 (OUT_DIR/engine_rev2.js) vs rev 3 (ENGINE3) on the trades in OUT_DIR/trades.json,
// each engine loading the same day payload; rev 3 also gets the DECODE blocks readable at the entry. Prints Markdown.
const fs = require("fs"), vm = require("vm"), path = require("path");
const [out, eng3] = process.argv.slice(2);
const mk = file => { const ctx = {}; vm.createContext(ctx); vm.runInContext(fs.readFileSync(file, "utf8") + ";this.Engine = Engine;", ctx); return ctx.Engine; };
const E2 = mk(path.join(out, "engine_rev2.js")), E3 = mk(eng3);
const trades = JSON.parse(fs.readFileSync(path.join(out, "trades.json"), "utf8"));
const dec = JSON.parse(fs.readFileSync(path.join(out, "decode.json"), "utf8"));
const sec = t => { const [h, m, s] = t.split(":").map(Number); return h * 3600 + m * 60 + (s || 0); };
const AB = { WITH: "W", AGAINST: "A", NEITHER: "·", CNC: "c", NS: "–", PR: "p" };
const NAMES = ["RIGHT NOW", "DAY / TREND", "INSTRUMENT", "WALL BEHIND", "WALL AHEAD", "ORDER FLOW", "VPIN", "CROSS-INDEX", "ROOM", "PAYING"];
let day = null;
const rows = [], detail = [];
for (const t of trades) {
  if (t.day !== day) { const p = JSON.parse(fs.readFileSync(path.join(out, `data_${t.day}.json`), "utf8")); E2.load(p); E3.load(p); day = t.day; }
  const T = sec(t.t), c = Math.floor((T - 60) / 300) * 300, blocks = dec[`${t.day}|${c}`] || {};
  for (const i of Object.keys(blocks)) E3.setDecode(i, blocks[i]);
  const v2 = E2.validate(t.idx, t.K, t.ty, t.side, t.p0, T, T), v3 = E3.validate(t.idx, t.K, t.ty, t.side, t.p0, T, T);
  if (!v2.ok || !v3.ok) { rows.push(`| ${t.day} ${t.t.slice(0, 5)} | ${t.idx} ${t.K} ${t.ty} ${t.side} | ${v2.why || ""} | ${v3.why || ""} |`); continue; }
  const cell = v => NAMES.map(n => { const q = v.checks.find(x => x.name === n); return q ? AB[q.st] || q.st : "?"; }).join(" ");
  const cnt = v => `${v.counts.w}w ${v.counts.a}a ${v.counts.n}n ${v.counts.c}c /${v.counts.of}`;
  const exp = (t.src.match(/exp (\S+)/) || [])[1], cx = E3.data.idx[t.idx].expiry,
        mism = !exp ? "" : !cx ? " ‡" : cx !== exp ? " †" : "";   // † her contract is not the recorded expiry; ‡ the record has no expiry
  rows.push(`| ${t.day.slice(5)} ${t.t.slice(0, 5)} | ${t.idx} ${t.K} ${t.ty} ${t.side} @${t.p0}${mism} | \`${cell(v2)}\` | **${v2.word}** ${cnt(v2)} | \`${cell(v3)}\` | **${v3.word}** ${cnt(v3)} |`);
  const changed = NAMES.map(n => [n, v2.checks.find(x => x.name === n), v3.checks.find(x => x.name === n)]).filter(([, a, b]) => a && b && (a.st !== b.st || a.cell !== b.cell));
  detail.push(`- **${t.day} ${t.t} ${t.idx} ${t.K} ${t.ty} ${t.side}** (${t.src}${exp ? `; chain exp ${E3.data.idx[t.idx].expiry}` : ""}): rev 2 ${v2.word} → rev 3 ${v3.word}`);
  for (const [n, a, b] of changed) detail.push(`  - ${n}: ${a.st} "${a.cell}" → ${b.st} "${b.cell}"${["DAY / TREND", "ORDER FLOW", "PAYING", "WALL BEHIND", "WALL AHEAD"].includes(n) ? `\n    - rev 3 hover: ${b.tip.replace(/\s+/g, " ").slice(0, 600)}` : ""}`);
}
console.log("| entry | trade | rev 2 checks (1–10) | rev 2 word | rev 3 checks (1–10) | rev 3 word |\n|---|---|---|---|---|---|");
console.log(rows.join("\n"));
console.log("\nKey: W with · A against · · neither · c could not check · – not shown (writer #5) · p printed (rev 3 VPIN). Check order: " + NAMES.join(", ") + ".\n");
console.log(detail.join("\n"));
