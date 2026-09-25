// node replay.js -> the report's tables, from the SAME verdict.js the page runs.
const fs = require("fs"), zlib = require("zlib"), path = require("path");
const HF = require("../verdict.js");
const here = __dirname;
const day = {};
for (const f of fs.readdirSync(here).filter((f) => /^facts_.*\.json\.gz$/.test(f))) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(here, f))).toString());
  day[`${d.idx}_${d.day}`] = d;
}
const T = JSON.parse(fs.readFileSync(path.join(here, "trades.json")));
const mm = HF.mm, hm = HF.hm;

function resolveExample(e) {
  const d = day[`${e.idx}_${e.day}`], i = mm(e.read) - mm("09:15"), m = d.minutes[i];
  const k = Math.round(m.spot / d.step) * d.step, leg = d.prem[`${k}${e.side}`];
  return { ...e, k, p0: leg ? leg.c[i] : null, qty: d.lot * e.lots, t0: e.read, read_from: e.read,
           exit_read: null, exits: [], read_to: "15:29", mine: false };
}

function premAt(d, tr, t) {
  const leg = d.prem[`${tr.k}${tr.side}`];
  if (!leg) return null;
  return leg.c[mm(t) - mm("09:15")];
}

const rows = [];
for (const tr of [...T.mine, ...T.examples.map(resolveExample)]) {
  const d = day[`${tr.idx}_${tr.day}`];
  if (!d || !d.minutes) { rows.push({ id: tr.id, blind: (d && d.why) || `could not check — no chain record for ${tr.idx} on ${tr.day}` }); continue; }
  const r = HF.replay(tr, d);
  const by = Object.fromEntries(r.map((v) => [v.t, v]));
  const firstW = r.find((v) => v.word === "WATCH"), firstF = r.find((v) => v.word === "FOLD");
  const ex = tr.exits.map((t) => by[t]);
  const after = tr.exit_read ? r.filter((v) => mm(v.t) > mm(tr.exit_read)) : [];
  const sgn = tr.role === "long" ? 1 : -1;
  const pexit = tr.exit_read ? premAt(d, tr, tr.exit_read) : null;
  const leg = d.prem[`${tr.k}${tr.side}`];
  const i0 = tr.exit_read ? mm(tr.exit_read) - mm("09:15") : null;
  const next30 = leg && i0 != null ? leg.c.slice(i0 + 1, i0 + 31).filter((x) => x != null) : [];
  rows.push({
    id: tr.id, mine: tr.mine, role: tr.role, side: tr.side, k: tr.k, p0: tr.p0, px: tr.px, pnl: tr.pnl, qty: tr.qty,
    entry: r[0] && { t: r[0].t, word: r[0].word, line: r[0].line, n_for: r[0].for.length, n_against: r[0].against.length },
    exits: ex.map((v) => v && { t: v.t, word: v.word, line: v.line, for: v.for, against: v.against,
                                  paidLast: v.paidLast, quietFor: v.quietFor, prem: v.prem }),
    firstWatch: firstW && { t: firstW.t, line: firstW.line },
    firstFold: firstF && { t: firstF.t, kind: firstF.kind, line: firstF.line, prem: premAt(d, tr, firstF.t) },
    afterExit: after.length ? { words: [...new Set(after.map((v) => v.word))], firstFold: (after.find((v) => v.word === "FOLD") || {}).t || null } : null,
    premExit: pexit, next30Best: next30.length ? (sgn > 0 ? Math.max(...next30) : Math.min(...next30)) : null,
    next30Worst: next30.length ? (sgn > 0 ? Math.min(...next30) : Math.max(...next30)) : null,
    close: leg ? leg.c.filter((x) => x != null).slice(-1)[0] : null,
    path: r.map((v) => `${v.t} ${v.word}`).filter((s, i, a) => i === 0 || s.split(" ").slice(1).join(" ") !== a[i - 1].split(" ").slice(1).join(" ")),
  });
}
fs.writeFileSync(path.join(here, "replay_out.json"), JSON.stringify(rows, null, 1));
for (const x of rows) {
  if (x.blind) { console.log(`${x.id}: ${x.blind}`); continue; }
  const e = x.exits.map((v) => v ? `${v.t} ${v.word}` : "?").join(", ");
  console.log(`${x.id.padEnd(58)} entry ${x.entry.t} ${x.entry.word.padEnd(12)} | exit ${e.padEnd(22)} | 1st FOLD ${x.firstFold ? x.firstFold.t + " " + x.firstFold.kind : "-"}`);
}
