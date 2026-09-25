// Post-data proposals 9.4 / 9.5 against the baseline, same trades, same minutes. NOT evidence.
const fs = require("fs"), zlib = require("zlib"), HF = require("../verdict.js");
const day = {}; for (const f of fs.readdirSync(".").filter((f) => /^facts_.*gz$/.test(f))) { const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f))); day[`${d.idx}_${d.day}`] = d; }
const T = JSON.parse(fs.readFileSync("trades.json")), S = (t) => HF.mm(t) - HF.mm("09:15");
const ex = T.examples.map((e) => { const d = day[`${e.idx}_${e.day}`], m = d.minutes[S(e.read)], k = Math.round(m.spot / d.step) * d.step;
  return { ...e, k, p0: d.prem[`${k}${e.side}`].c[S(e.read)], qty: d.lot, read_from: e.read, exits: [] }; });
const V = { base: {}, "9.4 structure": { structure: true }, "9.5 ceiling": { ceiling: true }, "both": { structure: true, ceiling: true }, "9.6 merged": { structure: true, merged: true } };
const out = [];
for (const tr of [...T.mine, ...ex]) {
  const d = day[`${tr.idx}_${tr.day}`]; if (!d || !d.minutes) continue;
  const leg = d.prem[`${tr.k}${tr.side}`], sg = tr.role === "long" ? 1 : -1, row = { id: tr.id };
  for (const [n, v] of Object.entries(V)) {
    const r = HF.replay({ ...tr, read_to: "15:29", variants: v }, d);
    const f = r.find((x) => x.word === "FOLD"), ft = f ? f.t : "15:29", px = leg ? leg.c[S(ft)] : null;
    const exitRead = tr.exits && tr.exits.length ? tr.exits[tr.exits.length - 1] : null;
    const atx = exitRead ? r.find((x) => x.t === exitRead) : null;
    row[n] = `${f ? f.t + " " + f.kind.slice(0, 5) : "none"} (${px != null ? (sg * (px - tr.p0)).toFixed(1) : "?"})${atx ? " x:" + (atx.word.startsWith("HOLD") ? "HOLD" : atx.word) : ""}`;
  }
  out.push(row);
  console.log(`${tr.id.slice(0, 40).padEnd(40)} | ${Object.keys(V).map((n) => row[n].padEnd(24)).join(" | ")}`);
}
fs.writeFileSync("variants_out.json", JSON.stringify(out, null, 1));
