// The better-trade read at her real entries, 09-21..09-24, and each day's distribution. Same better.js the page runs.
const fs = require("fs"), zlib = require("zlib"), BT = require("../better.js"), HF = require("../verdict.js");
const F = {};
for (const f of fs.readdirSync(".").filter((f) => /^facts_.*\.json\.gz$/.test(f))) { const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f))); (F[d.day] = F[d.day] || {})[d.idx] = d; }
F["2026-09-21"] = { NIFTY: { idx: "NIFTY", why: "could not check — no chain record for 2026-09-21" }, BANKNIFTY: { idx: "BANKNIFTY", why: "could not check — no chain record for 2026-09-21" }, SENSEX: { idx: "SENSEX", why: "could not check — no chain record for 2026-09-21" } };
const T = JSON.parse(fs.readFileSync("trades.json")), mm = HF.mm, hm = HF.hm, S0 = mm("09:15");
const px = (day, idx, k, side, t) => { const d = F[day][idx]; const l = d && d.prem && d.prem[`${k}${side}`]; return l ? l.c[mm(t) - S0] : null; };
const rows = [];
for (const t of T.mine) {
  const V = process.argv[2] === "price" ? { price: true } : null;
  const rd = hm(mm(t.t0) - 1), R = BT.read(F[t.day], rd, { idx: t.idx, side: t.side, role: "long" }, V);
  const me = R.mine || {};
  // the window's own entry read (the draft), for "entered into a broken setup"
  const D = F[t.day][t.idx], win = D && D.minutes ? HF.replay({ ...t, read_from: rd, read_to: rd }, D)[0] : null;
  // the best suggestion's ATM option, 30 min on, in its own direction
  let bestOut = null;
  const out30 = (E) => { if (!E) return null; const bd = F[t.day][E.idx], m = bd.minutes[mm(rd) - S0], k = Math.round(m.spot / bd.step) * bd.step;
    const t30 = hm(Math.min(mm("15:29"), mm(rd) + 30)); let a = 0, b = 0;
    for (const s of E.sides) { const x = px(t.day, E.idx, k, s, rd), y = px(t.day, E.idx, k, s, t30); if (x == null || y == null) return null; a += x; b += y; }
    return { leg: `${E.idx} ATM ${k} ${E.sides.join("+")} (${E.act})`, pts: +((E.act === "buy" ? 1 : -1) * (b - a)).toFixed(2) }; };
  bestOut = out30(R.best); const secondOut = out30(R.second);
  const a0 = t.p0, a30 = px(t.day, t.idx, t.k, t.side, hm(Math.min(mm("15:29"), mm(rd) + 30)));
  rows.push({ id: t.id, day: t.day, rd, pnl: t.pnl, her30: a30 != null ? +(a30 - a0).toFixed(2) : null,
    dayword: me.blind ? me.blind : `${me.word} (${me.for.length} for · ${me.against.length} against)`, check: R.check,
    win: win ? win.word : "—", cleanest: R.cleanest.text, engine: me.engine ? me.engine.text : "—", best: R.bestText, second: R.secondText, bestOut, secondOut,
    all: R.reads.map((r) => `${r.idx.slice(0, 3)} ${r.blind ? "blind" : r.day}${r.blind ? "" : ` ${r.for.length}/${r.against.length}`}`).join(" · ") });
}
fs.writeFileSync(process.argv[2] === "price" ? "better_out_price.json" : "better_out.json", JSON.stringify(rows, null, 1));
for (const r of rows) console.log(`${r.id.padEnd(26)} | ${r.all.padEnd(52)} | ${String(r.check.word).padEnd(8)} win ${r.win.padEnd(9)} | best ${r.best.slice(0, 60)}`);
// distribution per index-day (stable day word, readable minutes)
const dist = {};
for (const day of ["2026-09-22", "2026-09-23", "2026-09-24"]) for (const idx of BT.IDX) {
  const c = {}; const D = F[day][idx];
  for (const m of D.minutes) { const R = BT.read(F[day], m.t, null, process.argv[2] === "price" ? { price: true } : null); const r = R.reads.find((x) => x.idx === idx); const w = r.blind ? "blind" : r.day; c[w] = (c[w] || 0) + 1; }
  dist[`${idx} ${day}`] = c; console.log(`${idx.padEnd(10)} ${day}`, JSON.stringify(c));
}
fs.writeFileSync(process.argv[2] === "price" ? "better_dist_price.json" : "better_dist.json", JSON.stringify(dist, null, 1));
