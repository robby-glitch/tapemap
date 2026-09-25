const fs = require("fs"), vm = require("vm"), zlib = require("zlib"), path = require("path");
const ctx = { window: {} }; vm.createContext(ctx);
vm.runInContext(fs.readFileSync("../../../fable/data.js", "utf8"), ctx); vm.runInContext(fs.readFileSync("../../../fable/hold.js", "utf8"), ctx);
const FD = ctx.window.HOLD_DATA, FH = ctx.window.HOLD, HF = require("../../verdict.js"), mm = HF.mm, hm = HF.hm;
const MY = {}; for (const f of fs.readdirSync("..").filter((f) => /^facts_.*gz$/.test(f))) { const d = JSON.parse(zlib.gunzipSync(fs.readFileSync("../" + f))); MY[`${d.idx}_${d.day}`] = d; }
const T = JSON.parse(fs.readFileSync("../trades.json"));
let tot = { o: 0, f: 0, mins: 0, oW: 0, fW: 0 };
for (const t of T.mine) {
  const d = MY[`${t.idx}_${t.day}`]; if (!d || !d.minutes) continue;
  const A = HF.replay({ ...t, read_to: "15:29" }, d).map((v) => (v.word.startsWith("HOLD") ? "HOLD" : v.word));
  const R = FH.read(FD.days[`${t.idx}|${t.day}`], { idx: t.idx, day: t.day, strike: t.k, side: t.side, role: "buyer", qty: t.qty, entry_ts: t.t0, exit_ts: t.tx, entry: t.p0 });
  const B = R.rows.map((r) => r.verdict);
  const cut = (X) => { const i = X.indexOf("FOLD"); return i < 0 ? X : X.slice(0, i); };   // before any FOLD
  const ch = (X) => X.slice(1).filter((w, i) => w !== X[i]).length;
  const a = cut(A), b = cut(B);
  tot.o += ch(a); tot.f += ch(b); tot.mins += 1; tot.oM = (tot.oM||0) + a.length; tot.fM = (tot.fM||0) + b.length; tot.oW += a.filter((w) => w === "WATCH").length; tot.fW += b.filter((w) => w === "WATCH").length;
}
console.log("her 28 readable trades, from entry to each window's first FOLD:", JSON.stringify(tot));
