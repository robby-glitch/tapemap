// "If she had followed the window from her own entry": exit at its first FOLD (read to 15:29).
const fs = require("fs"), zlib = require("zlib"), HF = require("../verdict.js");
const day = {};
for (const f of fs.readdirSync(".").filter((f) => /^facts_.*\.json\.gz$/.test(f))) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f))); day[`${d.idx}_${d.day}`] = d;
}
const T = JSON.parse(fs.readFileSync("trades.json"));
const S = (t) => HF.mm(t) - HF.mm("09:15");
const ex = T.examples.map((e) => { const d = day[`${e.idx}_${e.day}`], m = d.minutes[S(e.read)];
  const k = Math.round(m.spot / d.step) * d.step; return { ...e, k, p0: d.prem[`${k}${e.side}`].c[S(e.read)], qty: d.lot, read_from: e.read, mine: false }; });
const out = [];
for (const tr of [...T.mine, ...ex]) {
  const d = day[`${tr.idx}_${tr.day}`]; if (!d) continue;
  const r = HF.replay({ ...tr, read_to: "15:29" }, d);
  const f = r.find((v) => v.word === "FOLD"), leg = d.prem[`${tr.k}${tr.side}`];
  const at = (t) => (leg ? leg.c[S(t)] : null);
  const sg = tr.role === "long" ? 1 : -1;
  const fx = f ? at(f.t) : at("15:29");
  const row = { id: tr.id, entry: tr.p0, her_exit: tr.px ?? null, her_exit_t: tr.tx ? tr.tx.slice(0, 5) : null,
    window_exit_t: f ? f.t : "15:29 (never folded)", window_exit_px: fx,
    her_pts: tr.px != null ? +(sg * (tr.px - tr.p0)).toFixed(2) : null, window_pts: fx != null ? +(sg * (fx - tr.p0)).toFixed(2) : null,
    kind: f ? f.kind : null };
  out.push(row);
  console.log(`${row.id.padEnd(58)} in ${String(row.entry).padStart(7)} | her out ${row.her_exit_t || "  -  "} ${String(row.her_exit ?? "-").padStart(7)} (${row.her_pts ?? "-"}) | window FOLD ${String(row.window_exit_t).padEnd(20)} ${String(fx).padStart(7)} (${row.window_pts}) ${row.kind || ""}`);
}
fs.writeFileSync("follow_out.json", JSON.stringify(out, null, 1));
