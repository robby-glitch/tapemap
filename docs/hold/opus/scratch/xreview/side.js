const fs = require("fs"), vm = require("vm"), zlib = require("zlib"), path = require("path");
const FAB = path.resolve(__dirname, "../../../fable");
const ctx = { window: {} }; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(FAB, "data.js"), "utf8"), ctx); vm.runInContext(fs.readFileSync(path.join(FAB, "hold.js"), "utf8"), ctx);
const FD = ctx.window.HOLD_DATA, FH = ctx.window.HOLD, HF = require("../../verdict.js");
const S = path.resolve(__dirname, ".."), mm = HF.mm, hm = HF.hm;
const [idx, day, k, side, role, t0, from, to] = process.argv.slice(2);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(S, `facts_${idx}_${day}.json.gz`))));
const leg = d.prem[`${k}${side}`], p = (t) => leg ? leg.c[mm(t) - mm("09:15")] : null;
const read = hm(mm(t0) - 1), p0 = p(read);
const A = HF.replay({ idx, day, k: +k, side, role, p0, qty: 1, read_from: read, read_to: "15:29" }, d);
const R = FH.read(FD.days[`${idx}|${day}`], { idx, day, strike: +k, side, role: role === "short" ? "writer" : "buyer", qty: 1, entry_ts: t0 + ":00", entry: p0 });
const B = Object.fromEntries(R.rows.map((r) => [r.t, r]));
let la = "", lb = "";
for (const v of A) {
  if (mm(v.t) < mm(from) || mm(v.t) > mm(to)) continue;
  const b = B[v.t], wa = v.word.startsWith("HOLD") ? "HOLD" : v.word, wb = b ? b.verdict : "-";
  const ra = wa !== la ? v.line.slice(0, 80) : "", rb = wb !== lb && b ? (b.since ? b.foldWhy : b.why).slice(0, 80) : "";
  console.log(`${v.t} ${String(p(v.t)).padStart(7)} spot ${Math.round(v.spot)} | O ${wa.padEnd(9)} | F ${wb.padEnd(9)} ${wa !== wb ? "≠" : " "} ${ra ? "O: " + ra : ""}${rb ? "  F: " + rb : ""}`);
  la = wa; lb = wb;
}
