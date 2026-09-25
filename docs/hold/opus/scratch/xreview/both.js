// Cross-review: run BOTH engines on the same trades at the same read minutes. Read-only on ../../../fable.
const fs = require("fs"), vm = require("vm"), zlib = require("zlib"), path = require("path");
const FAB = path.resolve(__dirname, "../../../fable");
const ctx = { window: {}, module: undefined }; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(FAB, "data.js"), "utf8"), ctx);
vm.runInContext(fs.readFileSync(path.join(FAB, "hold.js"), "utf8"), ctx);
const FD = ctx.window.HOLD_DATA, FH = ctx.window.HOLD;
const HF = require("../../verdict.js");
const S = path.resolve(__dirname, "..");
const MY = {};
for (const f of fs.readdirSync(S).filter((f) => /^facts_.*\.json\.gz$/.test(f))) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(S, f)))); MY[`${d.idx}_${d.day}`] = d;
}
const T = JSON.parse(fs.readFileSync(path.join(S, "trades.json")));
const mm = HF.mm, hm = HF.hm, i0 = mm("09:15");
// one premium source for judging both: mine ([M] REST where frozen, else [I] chain)
const prem = (idx, day, k, side, t) => { const d = MY[`${idx}_${day}`]; const l = d && d.prem[`${k}${side}`]; return l ? l.c[mm(t) - i0] : null; };
const trades = [];
for (const t of T.mine) trades.push({ id: t.id, day: t.day, idx: t.idx, k: t.k, side: t.side, role: "long", t0: t.t0, tx: t.tx, p0: t.p0, px: t.px, qty: t.qty, exits: t.exits, mine: true });
for (const e of T.examples) {
  const d = MY[`${e.idx}_${e.day}`], m = d.minutes[mm(e.read) - i0], k = Math.round(m.spot / d.step) * d.step;
  trades.push({ id: "OPUS " + e.id.slice(3), day: e.day, idx: e.idx, k, side: e.side, role: e.role, t0: hm(mm(e.read) + 1) + ":00", tx: null, p0: prem(e.idx, e.day, k, e.side, e.read), qty: d.lot, exits: [] });
}
for (const t of FD.trades.filter((t) => t.src !== "tradebook" && t.src !== "orders.csv"))
  trades.push({ id: "FABLE " + t.id, day: t.day, idx: t.idx, k: t.strike, side: t.side, role: t.role === "writer" ? "short" : "long", t0: t.entry_ts, tx: null, p0: t.entry, qty: t.qty, exits: [] });

function runMine(t) {
  const d = MY[`${t.idx}_${t.day}`]; if (!d || !d.minutes) return null;
  const r = HF.replay({ ...t, read_from: hm(mm(t.t0) - 1), read_to: "15:29" }, d);
  return Object.fromEntries(r.map((v) => [v.t, { w: v.word.startsWith("HOLD") ? "HOLD" : v.word, why: v.line }]));
}
function runFable(t) {
  const d = FD.days[`${t.idx}|${t.day}`]; if (!d) return null;
  const R = FH.read(d, { idx: t.idx, day: t.day, strike: t.k, side: t.side, role: t.role === "short" ? "writer" : "buyer", qty: t.qty, entry_ts: t.t0, exit_ts: t.tx, entry: t.p0 });
  if (R.error) return null;
  return Object.fromEntries(R.rows.map((r) => [r.t, { w: r.verdict, why: r.since ? r.foldWhy : r.why }]));
}
const out = [];
for (const t of trades) {
  const A = runMine(t), B = runFable(t), sg = t.role === "long" ? 1 : -1;
  const e = hm(mm(t.t0) - 1), x = t.tx ? hm(mm(t.tx) - 1) : null;
  const firstFold = (M) => M ? Object.keys(M).find((k) => M[k].w === "FOLD") || null : null;
  const fa = firstFold(A), fb = firstFold(B);
  const pts = (tt) => { const p = tt ? prem(t.idx, t.day, t.k, t.side, tt) : null; return p == null || t.p0 == null ? null : +(sg * (p - t.p0)).toFixed(2); };
  // minutes (in-trade, entry..exit) where the two disagree on the verdict class
  const dis = [];
  if (A && B) for (const k of Object.keys(A)) if (B[k] && A[k].w !== B[k].w && (!x || mm(k) <= mm(x))) dis.push(k);
  out.push({ id: t.id, day: t.day, idx: t.idx, k: t.k, side: t.side, role: t.role, p0: t.p0, her_x: t.tx ? t.tx.slice(0, 5) : null, her_pts: t.px != null ? +(sg * (t.px - t.p0)).toFixed(2) : null,
    entry: { t: e, mine: A && A[e], fable: B && B[e] }, exit: x ? { t: x, mine: A && A[x], fable: B && B[x] } : null,
    fold: { mine: fa, mine_pts: pts(fa || (A ? "15:29" : null)), fable: fb, fable_pts: pts(fb || (B ? "15:29" : null)) },
    inTradeDisagree: dis.length, inTradeMinutes: A ? Object.keys(A).filter((k) => !x || mm(k) <= mm(x)).length : 0 });
}
fs.writeFileSync(path.join(__dirname, "both_out.json"), JSON.stringify(out, null, 1));
const s = (v) => (v ? v.w : "—");
for (const o of out) console.log(`${o.id.slice(0, 44).padEnd(44)} | entry ${o.entry.t} ${s(o.entry.mine).padEnd(9)} ${s(o.entry.fable).padEnd(9)} | exit ${o.exit ? o.exit.t + " " + s(o.exit.mine).padEnd(9) + " " + s(o.exit.fable).padEnd(9) : "-".padEnd(26)} | FOLD opus ${String(o.fold.mine).padEnd(5)} (${o.fold.mine_pts}) fable ${String(o.fold.fable).padEnd(5)} (${o.fold.fable_pts}) | her ${o.her_pts}`);
