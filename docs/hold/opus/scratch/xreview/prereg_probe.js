// A reviewer's probe of docs/hold/PREREG-merged.md: its §3 map implemented AS WRITTEN,
// literally, on my frozen facts, to see how its rules interact. In-sample, zero evidential
// weight -- this checks the text, not the market. Ambiguities are resolved the literal way
// and flagged in PREREG-REVIEW.md.
const fs = require("fs"), zlib = require("zlib"), path = require("path"), HF = require("../../verdict.js");
const S = path.resolve(__dirname, ".."), mm = HF.mm, hm = HF.hm;
const DAY = {};
for (const f of fs.readdirSync(S).filter((f) => /^facts_.*gz$/.test(f))) { const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(S, f)))); DAY[`${d.idx}_${d.day}`] = d; }
const T = JSON.parse(fs.readFileSync(path.join(S, "trades.json")));
const dom = (a, b) => a >= 2 && a >= 2 * b;

function prereg(tr, D, opt = {}) {
  const th = HF.thesis(tr.side, tr.role), M = D.minutes, i0 = mm(M[0].t);
  const e = mm(tr.read_from) - i0, to = M.length - 1;
  const SL = HF.structureLine(D, th, e, to);
  const out = []; let latch = null, readable = []; const paidAt = {};
  const st = (m, s) => m[s] && m[s].state;
  for (let i = e; i <= to; i++) {
    const m = M[i], L = SL && SL[i];
    const lineBlind = !L || L.why;
    // §3.1 as written comes BEFORE the latch: a blind line is PATA NAHI even after a FOLD
    if (lineBlind && !(opt.latchFirst && latch)) { out.push({ t: m.t, w: "PATA NAHI" }); continue; }
    if (latch) { out.push({ t: m.t, w: "FOLD", k: latch.k }); continue; }
    const oiBlind = !!m.blind;
    const Q = th.Q, R = th.R, q = m[Q], r = m[R];
    const both = !oiBlind && st(m, Q) === "UNWINDING" && st(m, R) === "UNWINDING";
    const qPays = !oiBlind && !both && st(m, Q) === "UNWINDING";
    const qFold = !oiBlind && !both && (m.folds || []).some((f) => f.side === Q && f.still);
    const held = (key) => { for (let j = i; j > i - 3; j--) { const x = M[j]; if (!x || x.blind) return false;
      const bb = st(x, Q) === "UNWINDING" && st(x, R) === "UNWINDING";
      if (key === "qA" && !(st(x, Q) === "BUILDING" && x[Q].built)) return false;
      if (key === "rA" && !(st(x, R) === "UNWINDING" && !bb)) return false; } return true; };
    let qA = !oiBlind && held("qA"), rA = !oiBlind && held("rA");
    if (!th.buyer && !opt.writerQ) qA = false;       // §4: payers adding is "not a WATCH for a writer" (literal: it counts nowhere)
    if (!th.buyer && rA) rA = m.cvd ? Math.sign(m.cvd.dpx) === -th.d : (opt.rev2 ? false : rA);   // rev 3 S-a: no dpx -> own side could not check, rule 4 unavailable   // §4 own-side clause: against only while price moves toward her strike
    const rFold = !oiBlind && !both && (m.folds || []).some((f) => f.side === R && f.still);
    // strict flow (board.aggression): CVD strong AND prints dominant the same way
    let fWith = false, fAg = false;
    const thin = m.flow && m.flow.rw && !m.flow.b && !m.flow.s;
    if (m.cvd && m.flow && !thin && m.cvd.rank >= 0.5) {
      const sg = Math.sign(m.cvd.d), nd = th.d > 0 ? m.flow.b : m.flow.s, no = th.d > 0 ? m.flow.s : m.flow.b;
      fWith = sg === th.d && dom(nd, no); fAg = sg === -th.d && dom(no, nd);
    }
    const tw = m.tr ? ["5m", "15m", "1h"].map((k) => m.tr[k]) : [];
    const up = tw.filter((w) => w === "UP").length, dn = tw.filter((w) => w === "DOWN").length;
    const tAg = th.buyer ? (th.d > 0 ? dn >= 2 : up >= 2) : (th.d > 0 ? dn >= 2 : up >= 2);   // writer: >=2 toward danger (= -d)
    const paid = qPays || qFold || fWith;
    const countable = opt.bothUnreadable ? !oiBlind && !both : !oiBlind;
    if (countable) readable.push(i);
    paidAt[i] = paid;
    const quiet = th.buyer && readable.length >= 15 && readable.slice(-15).every((j) => !paidAt[j]);
    let w, k;
    if (L.broken) { w = "FOLD"; k = "line"; }
    else if (qA && rA) { w = "FOLD"; k = "flipped"; }
    else if (quiet) { w = "FOLD"; k = "quiet"; }
    else if ([qA, fAg, tAg].filter(Boolean).length >= 2) { w = "FOLD"; k = "two"; }
    else if ((th.buyer && qA) || rA || rFold || fAg || tAg) { w = "WATCH"; }
    else w = "HOLD";
    if (w === "FOLD") latch = { t: m.t, k };
    out.push({ t: m.t, w, k });
  }
  return out;
}

const S0 = mm("09:15");
const px = (D, tr, t) => { const l = D.prem[`${tr.k}${tr.side}`]; return l ? l.c[mm(t) - S0] : null; };
const ex = T.examples.map((e) => { const D = DAY[`${e.idx}_${e.day}`], m = D.minutes[mm(e.read) - S0], k = Math.round(m.spot / D.step) * D.step;
  return { ...e, k, p0: D.prem[`${k}${e.side}`].c[mm(e.read) - S0], qty: D.lot, read_from: e.read, exits: [] }; });
const res = [];
for (const opt of (process.argv[2] === 'rev2' ? [{ latchFirst: true, writerQ: true, rev2: true }] : [{}, { latchFirst: true, bothUnreadable: true }, { writerQ: true }])) {
  console.log(opt.latchFirst ? "\n== with the two fixes (latch before PATA NAHI; both-leaving minutes not counted by the clock)" : "== the text as written");
  for (const tr of [...T.mine, ...ex]) {
    const D = DAY[`${tr.idx}_${tr.day}`]; if (!D || !D.minutes) continue;
    const r = prereg({ ...tr, read_from: tr.read_from || hm(mm(tr.t0) - 1) }, D, opt);
    const f = r.find((x) => x.w === "FOLD"), sg = tr.role === "long" ? 1 : -1;
    const flips = r.slice(1).filter((x, j) => x.w !== r[j].w).length;
    const pataAfterFold = f ? r.filter((x) => mm(x.t) > mm(f.t) && x.w === "PATA NAHI").length : 0;
    const p = f ? px(D, tr, f.t) : null;
    const row = { id: tr.id, entry: r[0].w, fold: f ? `${f.t} ${f.k}` : "none", pts: p != null ? +(sg * (p - tr.p0)).toFixed(1) : null, pataAfterFold, flips };
    res.push({ opt: opt.latchFirst ? "fixed" : "text", ...row });
    console.log(`${tr.id.slice(0, 44).padEnd(44)} entry ${row.entry.padEnd(9)} first FOLD ${row.fold.padEnd(14)} (${row.pts}) ${pataAfterFold ? "· PATA NAHI after FOLD ×" + pataAfterFold : ""}`);
  }
}
fs.writeFileSync(path.join(__dirname, process.argv[2] === "rev2" ? "prereg_probe_rev2.json" : "prereg_probe.json"), JSON.stringify(res, null, 1));
