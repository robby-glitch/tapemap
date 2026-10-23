/* engine.js — replay clock + the VALIDATE reads, as prototype logic over data.json.
   Every input number is [M] from the recorder; every state word here is [I] prototype logic that mirrors
   DESIGN.md §2–§6 (fronts.py thresholds, fold.py's chips, daytype's IB, xindex's TOOK/FAILED) without the
   live engine. Pure: no DOM, no network. */
const Engine = (() => {
  const OPEN = 9 * 3600 + 15 * 60, CLOSE = 15 * 3600 + 30 * 60, IB_END = 10 * 3600 + 15 * 60, PRACTICE = 15 * 3600;
  const IDX = ["NIFTY", "BANKNIFTY", "SENSEX"];
  const THIN = { SENSEX: true };                                  // witness, thin tape
  const UNWIND = 0.15, STALL = 0.05, MARKS = 15, NOISE_N = 15, BLEED = 0.10;   // fronts.py / fold.py
  const ONE_SIDED = 0.30, VPIN_N = 10;                             // prototype: |b−s|/V ≥ .30 = one-sided bucket
  const RUN_IN = 3, TOL = 0.25, DEEP_ITM = 0.85;
  const STRUCT = ["RIGHT NOW", "DAY / TREND", "INSTRUMENT", "WALL BEHIND", "WALL AHEAD", "ORDER FLOW", "CROSS-INDEX"];
  const HI = { WITH: "saath", AGAINST: "khilaaf", NEITHER: "kuch nahi", CNC: "check nahi", NS: "nahi dikha",
               GO: "le lo", WAIT: "ruko", NO: "mat lo", HOLD: "ruko", FOLD: "nikal lo", "PAST GIVE-UP": "zone gaya",
               "GAVE UP": "chhod diya", OUT: "nikal gaye", PULLBACK: "pullback", UNDECIDED: "tay nahi",
               BUILDING: "likh rahe", UNWINDING: "bhag rahe", STALLED: "ruke hue", QUIET: "shaant" };
  let D = null; const X = {};
  const memo = new Map();

  const secOfHms = v => { const [h, m, x] = String(v).split(":").map(Number); return h * 3600 + m * 60 + (x || 0); };
  const hm = s => `${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}`;
  const hms = s => hm(s) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
  const lastLE = (arr, v) => { let lo = 0, hi = arr.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m] <= v) { r = m; lo = m + 1; } else hi = m - 1; } return r; };
  const med = a => { if (!a.length) return 0; const s = [...a].sort((p, q) => p - q), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const L = v => v == null ? "—" : (v / 100).toFixed(1) + "L";          // OI thousands → lakh
  const L0 = v => v == null ? "—" : Math.round(v / 100) + "L";          // whole lakh, for ≤ 6-word cells
  const fmt = (v, dp = 0) => v == null || !isFinite(v) ? "—" : v.toLocaleString("en-IN", { minimumFractionDigits: dp, maximumFractionDigits: dp });
  const sgn = v => { v = v || 0; return (v > 0 ? "+" : "") + fmt(v); };
  const pct = v => v == null ? "—" : (v * 100).toFixed(1) + " %";

  // ---------- load + precompute ----------
  function load(data) {
    D = data; memo.clear();
    for (const idx of IDX) prep(idx);
    return D;
  }
  // a live delta (GET /api/v2/data?since=): v2feed.merge()'s rule, then the per-row precomputes again (≈ 5 ms per index)
  function apply(delta) {
    for (const idx of IDX) {
      const d = delta.idx[idx], x = D.idx[idx]; if (!d) continue;
      if ((d.gen || 0) !== (x.gen || 0)) return "reload";
      const { i0, d0 } = d;
      for (const f of ["t", "spot", "atm"]) { x[f].length = Math.min(x[f].length, i0); x[f].push(...d[f]); }
      for (const leg of ["ce", "pe"]) { for (const f of ["oi", "ltp"]) { x[leg][f].length = Math.min(x[leg][f].length, i0); x[leg][f].push(...d[leg][f]); } for (const f of ["d", "avg"]) { x[leg][f].length = Math.min(x[leg][f].length, d0); x[leg][f].push(...d[leg][f]); } }
      if (d.bars.length) { const t0 = d.bars[0][0]; let n = x.bars.length; while (n > 0 && x.bars[n - 1][0] >= t0) n--; x.bars.length = n; x.bars.push(...d.bars); }
      if (d.futoi.length) { const m0 = d.futoi[0][0]; let n = x.futoi.length; while (n > 0 && x.futoi[n - 1][0] >= m0) n--; x.futoi.length = n; x.futoi.push(...d.futoi); }
      const grew = d.t.length || d.bars.length;
      if (grew) { const ev = x.events, evAt = x.eventsAt; prep(idx); if (ev && delta.now - (evAt || 0) < 30) { x.events = ev; x.eventsAt = evAt; } }
    }
    if (delta.vpin.length) { const s0 = delta.vpin[0][0]; D.vpin = D.vpin.filter(v => v[0] < s0).concat(delta.vpin); }
    for (const k of [...memo.keys()]) if (!/^(tp|e|ft)\|/.test(k)) memo.delete(k);
    return "ok";
  }
  function prep(idx) {
    const x = D.idx[idx], n = x.t.length, nk = x.ks.length;
    x.idx = idx; x.n = n; x.nk = nk; x.dte = dte(x.expiry);
    for (const leg of ["ce", "pe"]) {
      const Lg = x[leg]; Lg.peakV = new Array(n); Lg.peakI = new Array(n); Lg.upd = new Array(n);
      let pv = new Array(nk).fill(0), pi = new Array(nk).fill(0), up = new Array(nk).fill(0);
      for (let i = 0; i < n; i++) {
        const row = Lg.oi[i], prev = i ? Lg.oi[i - 1] : null;
        pv = pv.slice(); pi = pi.slice(); up = up.slice();
        for (let k = 0; k < nk; k++) { const v = row[k]; if (v == null) continue; if (v >= pv[k]) { pv[k] = v; pi[k] = i; up[k] = 0; } else if (prev && prev[k] !== v) up[k]++; }
        Lg.peakV[i] = pv; Lg.peakI[i] = pi; Lg.upd[i] = up;
      }
    }
    // spot session hi/lo so far
    x.sHi = new Array(n); x.sHiI = new Array(n); x.sLo = new Array(n); x.sLoI = new Array(n);
    let h = -1e9, hi = 0, l = 1e9, li = 0;
    for (let i = 0; i < n; i++) { const s = x.spot[i]; if (s > h) { h = s; hi = i; } if (s < l) { l = s; li = i; } x.sHi[i] = h; x.sHiI[i] = hi; x.sLo[i] = l; x.sLoI[i] = li; }
    // 1-s bars: cumulative CVD, VWAP, hi/lo
    const B = x.bars, nb = B.length; x.bt = B.map(b => b[0]);
    x.cvd = new Float64Array(nb); x.vwap = new Float64Array(nb); x.fHi = new Float64Array(nb); x.fHiI = new Int32Array(nb); x.fLo = new Float64Array(nb); x.fLoI = new Int32Array(nb);
    let cv = 0, pv = 0, vv = 0; h = -1e9; hi = 0; l = 1e9; li = 0;
    for (let j = 0; j < nb; j++) { const [t, p10, v, buy] = B[j], p = p10 / 10; cv += buy - (v - buy); pv += p * v; vv += v; x.cvd[j] = cv; x.vwap[j] = vv ? pv / vv : p; if (p > h) { h = p; hi = j; } if (p < l) { l = p; li = j; } x.fHi[j] = h; x.fHiI[j] = hi; x.fLo[j] = l; x.fLoI[j] = li; }
    // minute and 5-minute bars
    x.m1 = group(B, 60); x.m5 = group(B, 300);
    for (const m of x.m5) { const j = lastLE(x.bt, m.t + 299); m.vwapAtClose = j >= 0 ? x.vwap[j] : m.c; m.cvdAtClose = j >= 0 ? x.cvd[j] : 0; }
    // running one-candle range B per minute (median 1-min range so far; the engine's PRIOR_B stands in for the first 15)
    x.Bm = new Map(); const rs = [];
    for (const m of x.m1) { rs.push(m.h - m.l); x.Bm.set(m.t, rs.length >= 15 ? med(rs) : Math.max(med(rs), 0.0004 * m.c)); }
    x.futoiT = x.futoi.map(a => a[0]);
    x.s5 = []; let c5 = null;
    for (let i = 0; i < n; i++) { const b = x.t[i] - (x.t[i] % 300), v = x.spot[i]; if (!c5 || c5.t !== b) { c5 = { t: b, h: v, l: v }; x.s5.push(c5); } c5.h = Math.max(c5.h, v); c5.l = Math.min(c5.l, v); }
    x.events = null;
  }
  function group(B, w) {
    const out = []; let cur = null;
    for (const [t, p10, v, buy] of B) { const p = p10 / 10, b = t - (t % w); if (!cur || cur.t !== b) { cur = { t: b, o: p, h: p, l: p, c: p, v: 0, buy: 0, pv: 0 }; out.push(cur); } cur.c = p; cur.h = Math.max(cur.h, p); cur.l = Math.min(cur.l, p); cur.v += v; cur.buy += buy; cur.pv += p * v; }
    for (const m of out) m.vw = m.v ? m.pv / m.v : m.c;
    return out;
  }
  function dte(exp) { if (!exp) return null; const [y, m, d] = exp.split("-").map(Number), [Y, M, Dd] = D.day.split("-").map(Number); return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(Y, M - 1, Dd)) / 864e5); }

  // ---------- snapshot of one index at T ----------
  function Bat(x, T) { const m = T - (T % 60); let b = x.Bm.get(m); if (b == null) { for (const mm of x.m1) { if (mm.t > m) break; b = x.Bm.get(mm.t); } } return b || 0.0004 * (x.spot[0] || 1); }
  function snap(idx, T, feedT) {
    const key = `s|${idx}|${T}|${feedT}`; if (memo.has(key)) return memo.get(key);
    const x = D.idx[idx], tf = Math.min(T, feedT);
    const i = lastLE(x.t, tf), j = lastLE(x.bt, tf);
    const s = { idx, x, T, i, j, ok: i >= 0 && j >= 0, lot: x.lot, step: x.step, dte: x.dte, expiry: x.expiry, thin: !!THIN[idx] };
    s.ages = { chain: i >= 0 ? T - x.t[i] : null, book: j >= 0 ? T - x.bt[j] : null };
    if (!s.ok) { memo.set(key, s); return s; }
    s.spot = x.spot[i]; s.atm = x.atm[i]; s.fut = x.bars[j][1] / 10; s.basis = s.fut - s.spot;
    s.vwap = x.vwap[j]; s.cvd = x.cvd[j];
    const j15 = lastLE(x.bt, tf - 900); s.cvd15 = s.cvd - (j15 >= 0 ? x.cvd[j15] : 0);
    const p15 = j15 >= 0 ? x.bars[j15][1] / 10 : s.fut; s.px15 = s.fut - p15;
    s.fHi = x.fHi[j]; s.fHiT = x.bt[x.fHiI[j]]; s.fLo = x.fLo[j]; s.fLoT = x.bt[x.fLoI[j]];
    s.sHi = x.sHi[i]; s.sHiT = x.t[x.sHiI[i]]; s.sLo = x.sLo[i]; s.sLoT = x.t[x.sLoI[i]];
    s.B = Bat(x, tf);
    const fo = lastLE(x.futoiT, tf); s.futOi = fo >= 0 ? x.futoi[fo][1] : null; s.futOi0 = x.futoi[0][1];
    const fo30 = lastLE(x.futoiT, tf - 1800); s.futOi30 = fo30 >= 0 ? x.futoi[fo30][1] : s.futOi0;
    // CVD day path: peak so far & when, lower-high after
    let cvMax = -1e18, cvMaxT = 0; for (let q = 0; q <= j; q += 5) if (x.cvd[q] > cvMax) { cvMax = x.cvd[q]; cvMaxT = x.bt[q]; }
    s.cvdPeak = cvMax; s.cvdPeakT = cvMaxT; s.cvdSincePeak = s.cvd - cvMax;
    s.m5 = closed5(x, tf); s.day = daytype(x, s.m5, tf); s.fights = fights(x, s.m5, tf); s.last = s.fights.length ? s.fights[s.fights.length - 1] : null;
    s.push = pushOf(x, s.m5, tf, s.B);
    s.ib = ibOf(s.m5, x, tf);
    s.box = boxOf(x.s5.filter(m => m.t + 300 <= tf), s.basis);
    s.fronts = { ce: sideFronts(x, i, "ce", true, s.spot), pe: sideFronts(x, i, "pe", false, s.spot) };
    s.pin = pinOf(x, i, s.atm); s.pcr = pcr9(x, i, tf);
    s.vpin = idx === "NIFTY" ? vpinAt(tf) : null;
    s.whose = whoseDay(s.fights);
    s.bf = x.bf || 0; s.bfFrom = x.bfFrom || null; s.bfTo = x.bfTo || null; s.chainFrom = x.chainFrom || null; s.flowFrom = x.flowFrom || null;
    s.inBf = s.bf > 0 && i < s.bf;                                 // this very row is a rebuilt minute [I]
    s.lateFlow = !!(s.flowFrom && secOfHms(s.flowFrom) > OPEN + 180);   // the futures ticks began after the open: CVD / VWAP / fights from then
    s.vwapSide = s.fut >= s.vwap ? 1 : -1; s.vwapSince = vwapSince(x, j, s.vwapSide);
    memo.set(key, s); return s;
  }
  function closed5(x, T) { const out = []; for (const m of x.m5) { if (m.t + 300 <= T) out.push(m); else break; } return out; }
  function ibOf(m5, x, T) { const ib = m5.filter(m => m.t < IB_END); if (!ib.length) return null; const hi = Math.max(...ib.map(m => m.h)), lo = Math.min(...ib.map(m => m.l)); return { hi, lo, built: ib[ib.length - 1].t + 300 >= IB_END }; }
  function boxOf(s5, basis) {       // prototype, on SPOT: walk back from now while the running range stays ≤ 0.6 × the IB range, min 6 bars
    const ib = s5.filter(m => m.t < IB_END); if (ib.length < 10 || s5.length < 6) return null;
    const lim = 0.6 * (Math.max(...ib.map(m => m.h)) - Math.min(...ib.map(m => m.l))); let hi = -1e9, lo = 1e9, k = s5.length - 1, since = null;
    for (; k >= 0; k--) { const h = Math.max(hi, s5[k].h), l = Math.min(lo, s5[k].l); if (h - l > lim) break; hi = h; lo = l; since = s5[k].t; }
    if (s5.length - 1 - k < 6) return null; return { spotHi: Math.round(hi), spotLo: Math.round(lo), since, hi: Math.round(hi + basis), lo: Math.round(lo + basis) };
  }
  function daytype(x, m5, T) {        // daytype.py in miniature: EARLY → TREND (≥ RUN_IN closes one side of VWAP and beyond the IB) / PIN-CHOP / TWO-SIDED
    const key = `d|${x.idx}|${m5.length}`; if (memo.has(key)) return memo.get(key);
    let cur = { type: "EARLY", dir: 0, since: OPEN }, block = null; const ib = { hi: -1e9, lo: 1e9 };
    for (let b = 0; b < m5.length; b++) {
      const m = m5[b]; if (m.t < IB_END) { ib.hi = Math.max(ib.hi, m.h); ib.lo = Math.min(ib.lo, m.l); }
      if (m.t + 300 < IB_END + 300) { continue; }
      const last = m5.slice(Math.max(0, b - RUN_IN + 1), b + 1);
      const up = last.length >= RUN_IN && last.every(q => q.c > q.vwapAtClose) && m.c > ib.hi;
      const dn = last.length >= RUN_IN && last.every(q => q.c < q.vwapAtClose) && m.c < ib.lo;
      let next = cur;
      if (cur.type === "TREND") {
        cur.ext = cur.dir > 0 ? Math.max(cur.ext, m.h) : Math.min(cur.ext, m.l);
        const half = cur.ext - cur.dir * (Math.abs(cur.ext - cur.from) / 2);
        const alive = cur.dir > 0 ? (m.c > m.vwapAtClose && m.c > ib.hi && m.c > half) : (m.c < m.vwapAtClose && m.c < ib.lo && m.c < half);
        if (!alive) { block = { dir: cur.dir, ext: cur.ext }; const why = cur.dir > 0 ? (m.c <= m.vwapAtClose ? "back below VWAP" : m.c <= ib.hi ? "back inside the IB" : `gave back half the leg from ${fmt(cur.from)}`) : (m.c >= m.vwapAtClose ? "back above VWAP" : m.c >= ib.lo ? "back inside the IB" : `gave back half the leg from ${fmt(cur.from)}`);
          next = { type: "TWO-SIDED", dir: 0, since: m.t + 300, why: `trend khatam · ${why} · ext ${fmt(cur.ext)} fut` }; }
      } else {
        const okUp = up && !(block && block.dir > 0 && m.c <= block.ext), okDn = dn && !(block && block.dir < 0 && m.c >= block.ext);
        if (okUp) next = { type: "TREND", dir: 1, since: m.t + 300, ext: m.h, from: last[0].o, why: `${RUN_IN} closes above VWAP, above IB ${fmt(ib.hi)} fut` };
        else if (okDn) next = { type: "TREND", dir: -1, since: m.t + 300, ext: m.l, from: last[0].o, why: `${RUN_IN} closes below VWAP, below IB ${fmt(ib.lo)} fut` };
        else {
          const w = m5.slice(Math.max(0, b - 11), b + 1), rng = Math.max(...w.map(q => q.h)) - Math.min(...w.map(q => q.l));
          const pin = w.length >= 12 && rng <= 0.5 * (ib.hi - ib.lo);
          const t = pin ? "PIN/CHOP" : "TWO-SIDED";
          if (cur.type !== t) next = { type: t, dir: 0, since: m.t + 300, why: pin ? `last 60 min range ${fmt(rng)} ≤ half the IB` : (cur.type === "EARLY" ? "IB built, no leg" : "range widened past half the IB") };
        }
      }
      cur = next;
    }
    cur.ib = ib.hi > -1e9 ? { hi: ib.hi, lo: ib.lo } : null; memo.set(key, cur); return cur;
  }
  function fights(x, m5, T) {        // prototype of fold's runs: a 5-min bucket with one-sided volume ≥ 1.5 × its median
    const key = `f|${x.idx}|${m5.length}`; if (memo.has(key)) return memo.get(key);
    const out = [], nets = [];
    for (const m of m5) {
      const net = m.buy - (m.v - m.buy); const mdn = nets.length >= 6 ? med(nets.map(Math.abs)) : null; nets.push(net);
      if (mdn == null || Math.abs(net) < 1.5 * mdn || mdn === 0) continue;
      const side = net > 0 ? 1 : -1, disp = m.c - m.o, Bv = Bat(x, m.t);
      const res = disp * side >= Bv / 2 ? "INITIATIVE" : disp * side <= -Bv / 2 ? "ABSORBED" : "PRESSING";
      const winner = res === "ABSORBED" ? -side : side;
      out.push({ t: m.t + 300, side, winner, res, vw: Math.round(m.vw), zone: Math.round(winner > 0 ? m.l : m.h), lots: Math.round(Math.abs(net) / (x.lot || 1)), who: winner > 0 ? "buyers" : "sellers" });
    }
    memo.set(key, out); return out;
  }
  function whoseDay(f) { const b = f.filter(q => q.winner > 0).length, s = f.length - b; return { b, s, text: b === s ? `even, ${b}–${s}` : b > s ? `buyers' day ${b}–${s}` : `sellers' day ${s}–${b}` }; }
  function pushOf(x, m5, T, B) {      // xindex X2 in miniature: zigzag on 5-min bars, latest push vs its own previous extreme
    if (m5.length < 4) return null;
    const ruler = Math.max(1.5 * med(m5.map(m => m.h - m.l)), 2 * B);
    const piv = []; let dir = 0, ext = m5[0].h, extT = m5[0].t, ext2 = m5[0].l, ext2T = m5[0].t;
    for (const m of m5) {
      if (dir >= 0) { if (m.h > ext) { ext = m.h; extT = m.t; } if (ext - m.l >= ruler) { piv.push({ type: "H", px: ext, t: extT }); dir = -1; ext2 = m.l; ext2T = m.t; continue; } }
      if (dir <= 0) { if (m.l < ext2) { ext2 = m.l; ext2T = m.t; } if (m.h - ext2 >= ruler) { piv.push({ type: "L", px: ext2, t: ext2T }); dir = 1; ext = m.h; extT = m.t; } }
      if (dir === 0 && m.h > ext) { ext = m.h; extT = m.t; }
    }
    if (dir === 0) return null;
    const up = dir > 0, to = up ? ext : ext2, at = up ? extT : ext2T, prev = [...piv].reverse().find(p => p.type === (up ? "H" : "L"));
    if (!prev) return { dir, to, at, status: "NONE", prev: null, ruler };
    const gap = up ? to - prev.px : prev.px - to; const status = gap > TOL * ruler ? "TOOK" : gap < -TOL * ruler ? "FAILED" : "EQUAL";
    return { dir, to, at, status, prev: prev.px, prevT: prev.t, gap: Math.round(gap), ruler };
  }
  function vwapSince(x, j, side) { let q = j; while (q > 0 && ((x.bars[q][1] / 10 >= x.vwap[q]) ? 1 : -1) === side) q -= 10; return x.bt[Math.min(j, Math.max(0, q + 10))]; }

  // ---------- OI: fronts, walls, pin, PCR ----------
  function front(x, leg, i, k) {
    const Lg = x[leg], oi = Lg.oi[i][k]; if (oi == null) return null;
    const peak = Lg.peakV[i][k], peakI = Lg.peakI[i][k], upd = Lg.upd[i][k], slope = oi - Lg.oi[Math.max(0, i - MARKS)][k];
    const off = peak ? (peak - oi) / peak : 0;
    const state = (off >= UNWIND && slope < 0) ? "UNWINDING" : Math.abs(slope) <= STALL * peak ? "STALLED" : slope > 0 ? "BUILDING" : "UNWINDING";
    const bleed = off >= BLEED && upd >= NOISE_N;                       // the slow leak the z/√n event misses (DESIGN §5.5)
    return { k: x.ks[k], ki: k, leg, oi, peak, peakT: x.t[peakI], off, upd, slope, state, bleed, ltp: ltpAt(x, leg, i, k), delta: deltaAt(x, leg, i, k), avg: avgAt(x, leg, i, k) };
  }
  const ltpAt = (x, leg, i, k) => { const v = x[leg].ltp[i][k]; return v == null ? null : v / 20; };
  const deltaAt = (x, leg, i, k) => { const r = x[leg].d[Math.min(x[leg].d.length - 1, Math.floor(i / x.slowEvery))]; const v = r && r[k]; return v == null ? null : v / 100; };
  const avgAt = (x, leg, i, k) => { const r = x[leg].avg[Math.min(x[leg].avg.length - 1, Math.floor(i / x.slowEvery))]; const v = r && r[k]; return v == null ? null : v; };
  function sideFronts(x, i, leg, above, spot) {   // top-2 fronts on that side of spot, ranked by PEAK OI (fronts.py)
    const c = []; for (let k = 0; k < x.nk; k++) { const K = x.ks[k]; if (above ? K > spot : K < spot) { const f = front(x, leg, i, k); if (f) c.push(f); } }
    c.sort((p, q) => q.peak - p.peak); return c.slice(0, 2);
  }
  function wallNearest(x, i, leg, beyond, spot) {  // nearest strike beyond price with OI ≥ ½ of that side's largest
    let mx = 0; const c = [];
    for (let k = 0; k < x.nk; k++) { const K = x.ks[k]; if (beyond > 0 ? K > spot : K < spot) { const v = x[leg].oi[i][k]; if (v != null) { mx = Math.max(mx, v); c.push(k); } } }
    const ok = c.filter(k => x[leg].oi[i][k] >= 0.5 * mx); if (!ok.length) return null;
    const k = beyond > 0 ? ok[0] : ok[ok.length - 1]; return front(x, leg, i, k);
  }
  function pinOf(x, i, atm) {        // §2.4: largest CE+PE inside the nine where both legs ≥ ½ their side's largest
    const ks = []; for (let k = 0; k < x.nk; k++) if (Math.abs(x.ks[k] - atm) <= 4 * x.step) ks.push(k);
    let mc = 0, mp = 0; for (const k of ks) { mc = Math.max(mc, x.ce.oi[i][k] || 0); mp = Math.max(mp, x.pe.oi[i][k] || 0); }
    let best = null; for (const k of ks) { const c = x.ce.oi[i][k] || 0, p = x.pe.oi[i][k] || 0; if (c >= mc / 2 && p >= mp / 2 && (!best || c + p > best.sum)) best = { k: x.ks[k], ki: k, ce: c, pe: p, sum: c + p }; }
    return best;
  }
  function pcr9(x, i, T) {
    const at = ii => { if (ii < 0) return null; const atm = x.atm[ii]; let c = 0, p = 0; for (let k = 0; k < x.nk; k++) if (Math.abs(x.ks[k] - atm) <= 4 * x.step) { c += x.ce.oi[ii][k] || 0; p += x.pe.oi[ii][k] || 0; } return { r: c ? p / c : null, c, p }; };
    return { now: at(i), h1: at(lastLE(x.t, T - 3600)), open: at(lastLE(x.t, 9 * 3600 + 30 * 60)), t1400: at(lastLE(x.t, 14 * 3600)) };
  }
  function vpinAt(T) {
    const rows = D.vpin.filter(r => r[0] <= T); if (!rows.length) return { n: 0 };
    const last = rows.slice(-VPIN_N), one = last.filter(r => Math.abs(r[2]) >= ONE_SIDED);
    const b = one.filter(r => r[2] > 0).length, s = one.length - b;
    return { n: rows.length, at: rows[rows.length - 1][0], pct: rows[rows.length - 1][4], vpin: rows[rows.length - 1][3], one: one.length, b, s, lean: b > s ? 1 : s > b ? -1 : 0, age: T - rows[rows.length - 1][0] };
  }

  // ---------- expression (prototype of expression.py's word) ----------
  function expression(s, d) {
    const dirFacts = [s.day.type === "TREND" && s.day.dir === d, s.last && s.last.winner === d && s.T - s.last.t <= 1800, Math.sign(s.cvd15) === d, s.push && s.push.dir === d, s.vpin && s.vpin.lean === d].filter(Boolean).length;
    if (!dirFacts) return { word: "STAND ASIDE", buy: 0, sell: 0 };
    const pay = d > 0 ? s.fronts.ce : s.fronts.pe;
    const buy = [s.day.type === "TREND" && s.day.dir === d, s.push && s.push.dir === d && s.push.status === "TOOK", pay.some(f => f.state === "UNWINDING"), s.vpin && s.vpin.lean === d && s.vpin.one >= 3].filter(Boolean).length;
    const sell = [s.day.type === "PIN/CHOP" || s.day.type === "TWO-SIDED", s.dte === 0 && s.T >= 12 * 3600, pay.length && pay.every(f => f.state === "BUILDING"), !s.last || s.T - s.last.t > 1800].filter(Boolean).length;
    const net = buy - sell; const word = net >= 2 ? "BUY" : net === 1 ? "LEANS BUY" : net === 0 ? "EITHER" : net === -1 ? "LEANS SELL" : "SELL";
    return { word, buy, sell };
  }

  // ---------- a trade's geometry: direction, walls, zone, engine-now ----------
  function zoneFight(s, d, fut) { return [...s.fights].reverse().find(f => f.winner === d && d * (fut - f.zone) >= s.B && s.T - f.t <= 7200) || null; }
  function accepted(s, d, G) {        // prototype of fold's lot tally: ≥ 70 % of the last 10 min of volume traded beyond G, and price beyond it now
    let accVol = 0, tot = 0; const x = s.x;
    for (let q = s.j; q >= 0 && x.bt[q] >= s.T - 600; q--) { const [, p10, v] = x.bars[q]; tot += v; if (d * (p10 / 10 - G) < 0) accVol += v; }
    return { acc: tot > 0 && accVol >= 0.7 * tot && d * (s.fut - G) < 0, share: tot ? accVol / tot : 0 };
  }
  function geom(s, K, ty, side, p0, g0) {   // g0: a sticky {W, G, Gwhy} carried by an open trade
    const x = s.x, i = s.i, d = (ty === "CE") === (side === "BUY") ? 1 : -1, role = side === "BUY" ? "buy" : "sell";
    const ki = x.ks.indexOf(K), leg = ty.toLowerCase();
    const own = ki >= 0 ? front(x, leg, i, ki) : null, other = ki >= 0 ? front(x, leg === "ce" ? "pe" : "ce", i, ki) : null;
    const ltp = own ? own.ltp : null, delta = own ? own.delta : null, px = p0 || ltp;
    const defLeg = d > 0 ? "pe" : "ce", payLeg = d > 0 ? "ce" : "pe";
    const W = g0 && g0.W ? g0.W : wallNearest(x, i, defLeg, -d, s.spot), A = role === "buy" ? wallNearest(x, i, payLeg, d, s.spot) : null;
    const payers = d > 0 ? s.fronts.ce : s.fronts.pe;
    let G, Gwhy;
    if (role === "buy") {
      const z = zoneFight(s, d, s.fut);
      if (z) { G = z.zone; Gwhy = `${z.who} won ${hm(z.t)} from ${fmt(z.zone)}`; }
      else if (W) { G = Math.round(W.k + s.basis - d * s.B / 2); Gwhy = `where the ${W.k} ${W.leg.toUpperCase()} writers stand`; }
      else { G = d > 0 ? Math.round(s.fLo - s.B / 2) : Math.round(s.fHi + s.B / 2); Gwhy = `the day's ${d > 0 ? "low" : "high"} ± half a candle`; }
    } else { G = Math.round((ty === "CE" ? K + (px || 0) : K - (px || 0)) + s.basis); Gwhy = `breakeven ${fmt(ty === "CE" ? K + (px || 0) : K - (px || 0))} spot + basis`; }
    if (g0 && g0.G != null) { G = g0.G; Gwhy = g0.Gwhy; }
    const toG = Math.round(Math.abs(s.fut - G)), toA = A ? Math.round(Math.abs(A.k + s.basis - s.fut)) : null;
    // engine-now proxy: beyond G? accepted = ≥ 60 % of the last 3 min of volume traded beyond G
    const beyond = d * (s.fut - G) < 0; const ac = accepted(s, d, G), acc = ac.acc;
    const now = acc ? "FOLD" : beyond ? "PAST GIVE-UP" : "HOLD";
    const chips = {
      ZONE: beyond ? "AGAINST" : toG > s.B ? "WITH" : "QUIET",
      FLOW: !s.last || s.T - s.last.t > 1800 ? "QUIET" : s.last.winner === d ? "WITH" : "AGAINST",
      OI: !W ? "QUIET" : W.state === "BUILDING" ? "WITH" : W.state === "UNWINDING" ? "AGAINST" : "QUIET",
      VPIN: !s.vpin ? "CNC" : s.vpin.n < VPIN_N ? "CNC" : s.vpin.one === 0 ? "QUIET" : s.vpin.lean === d ? "WITH" : s.vpin.lean === -d ? "AGAINST" : "QUIET",
    };
    const intrinsic = delta == null ? null : Math.max(0, ty === "CE" ? s.spot - K : K - s.spot), tv = ltp != null && intrinsic != null ? ltp - intrinsic : null;
    return { d, role, K, ty, side, leg, ki, own, other, ltp, delta, px, W, A, payers, G, Gwhy, toG, toA, now, chips, beyond, acc, intrinsic, tv, deep: delta != null && Math.abs(delta) >= DEEP_ITM };
  }
  const premAt = (g, s, spotTarget) => { if (g.ltp == null || g.delta == null) return null; const intr = Math.max(0, g.ty === "CE" ? spotTarget - g.K : g.K - spotTarget); return Math.max(intr, 0.05, g.ltp + g.delta * (spotTarget - s.spot)); };

  // ---------- the ten checks + the word ----------
  function validate(idx, K, ty, side, p0, T, feedT, g0) {
    const s = snap(idx, T, feedT);
    if (!s.ok) return { ok: false, idx, K, ty, side, word: "—", why: "no chain row yet", checks: [], counts: { w: 0, a: 0, n: 0, c: 10 } };
    const g = geom(s, K, ty, side, p0, g0), d = g.d, her = d > 0 ? "up" : "down";
    const C = [];
    const row = (name, st, cell, tip, extra) => C.push(Object.assign({ name, st, cell, tip: tip + ` · ${HI[st] || ""}` }, extra));
    // 1 RIGHT NOW
    row("RIGHT NOW", g.now === "HOLD" ? "WITH" : "AGAINST", `${g.now} · out if ${fmt(g.G)}f`, `engine-now proxy for a mark made now [I]: ${g.now}; give-up ${fmt(g.G)} fut (${g.Gwhy}); chips Z ${g.chips.ZONE} · F ${g.chips.FLOW} · O ${g.chips.OI} · V ${g.chips.VPIN}`, { chips: g.chips });
    // 2 DAY / TREND
    const dy = s.day; let st2 = "NEITHER";
    if (dy.type === "TREND") st2 = dy.dir === d ? "WITH" : "AGAINST"; else if (dy.type === "PIN/CHOP") st2 = g.role === "sell" ? "WITH" : "NEITHER";
    row("DAY / TREND", st2, `${dy.type}${dy.type === "TREND" ? (dy.dir > 0 ? " ▲" : " ▼") : ""} since ${hm(dy.since)}`, `daytype [I]: ${dy.type} since ${hm(dy.since)} (${dy.why || "IB building"}); ${s.whose.text}; a buyer needs a leg, a seller sells with the trend or into a pin`);
    // 3 INSTRUMENT (expression word + moneyness)
    const ex = expression(s, d), exo = expression(s, -d); let st3 = "NEITHER", c3 = "", t3 = "";
    if (g.role === "buy" && g.deep) { st3 = "AGAINST"; c3 = `δ ${g.delta.toFixed(2)} · TV ${fmt(g.tv, 1)} of ${fmt(g.ltp, 2)}`; t3 = `deep ITM: a futures position in option's clothing — delta ${g.delta.toFixed(2)}, intrinsic ${fmt(g.intrinsic, 1)}, time value ${fmt(g.tv, 1)} [I]; the expression word was ${ex.word}`; }
    else if (ex.word === "EITHER" || (g.role === "buy" && /BUY/.test(ex.word)) || (g.role === "sell" && /SELL/.test(ex.word))) { st3 = "WITH"; c3 = `${ex.word} ${her} · δ ${g.delta == null ? "—" : g.delta.toFixed(2)}`; t3 = `expression [I] for ${her}: ${ex.word} (${ex.buy} buy · ${ex.sell} sell facts) matches your ${g.role}; delta ${g.delta == null ? "—" : g.delta.toFixed(2)}, time value ${fmt(g.tv, 1)}`; }
    else if (ex.word === "STAND ASIDE") { if (exo.word !== "STAND ASIDE") { st3 = "AGAINST"; c3 = `leans other way · ${exo.word}`; t3 = `expression [I]: your way (${her}) STAND ASIDE, the other way reads ${exo.word} (${exo.buy} buy · ${exo.sell} sell facts) — the engine leans the other way`; } else { c3 = "STAND ASIDE both ways"; t3 = "expression [I]: no direction has a fact behind it"; } }
    else { st3 = "AGAINST"; c3 = `engine says ${ex.word}, you ${g.side}`; t3 = `expression [I] for ${her}: ${ex.word} (${ex.buy} buy · ${ex.sell} sell facts) — the other role is the better expression`; }
    row("INSTRUMENT", st3, c3, t3, { expr: ex, exprOther: exo });
    // 4 WALL BEHIND
    if (!g.W) row("WALL BEHIND", "NEITHER", "no front behind you", "no strike behind price holds ≥ ½ of its side's largest OI [M]");
    else { const W = g.W, st4 = W.state === "BUILDING" ? "WITH" : W.state === "UNWINDING" ? "AGAINST" : "NEITHER";
      row("WALL BEHIND", st4, `${W.k} ${W.leg.toUpperCase()} ${L0(W.oi)} ${W.state === "BUILDING" ? "building" : W.state === "STALLED" ? "flat" : "leaving"}${W.bleed ? ` −${(W.off * 100).toFixed(0)}%` : ""}`, `${W.k} ${W.leg.toUpperCase()} writers ${L(W.oi)}, ${W.state} (peak ${L(W.peak)} at ${hm(W.peakT)}, ${pct(W.off)} off, ${W.upd} updates since)${W.bleed ? " · W-BLEED: the slow leak, amber, not a fold" : ""} [M]; they defend you — if they leave nobody holds the ${d > 0 ? "floor" : "ceiling"}`, { front: W, flag: W.bleed ? "a" : null }); }
    // 5 WALL AHEAD (buyer only)
    if (g.role === "sell") row("WALL AHEAD", "NS", "not shown — time is your target", "a writer has no next wall; time is her target", {});
    else if (!g.A) row("WALL AHEAD", "NEITHER", "no front ahead inside ±8", "no strike ahead holds ≥ ½ of its side's largest OI [M]");
    else { const A = g.A, near = g.toA <= 2 * s.B, st5 = A.state === "UNWINDING" ? "WITH" : A.state === "BUILDING" && near ? "AGAINST" : "NEITHER";
      row("WALL AHEAD", st5, `${A.k} ${A.leg.toUpperCase()} ${L0(A.oi)} ${A.state === "BUILDING" ? "building" : A.state === "STALLED" ? "flat" : "leaving"} · ${g.toA} pts`, `${A.k} ${A.leg.toUpperCase()} writers ${L(A.oi)}, ${A.state} (peak ${L(A.peak)} at ${hm(A.peakT)}, ${pct(A.off)} off), ${g.toA} pts ahead (fut) [M]; the next wall caps the move, writers leaving there pay you`, { front: A }); }
    // 6 ORDER FLOW
    const lf = s.last, fresh = lf && s.T - lf.t <= 1800;
    if (!fresh) row("ORDER FLOW", "NEITHER", `quiet · CVD15 ${sgn(Math.round(s.cvd15))}`, `no fight inside 30 min [I]; CVD over 15 min ${sgn(Math.round(s.cvd15))} with price ${sgn(Math.round(s.px15))}`);
    else row("ORDER FLOW", lf.winner === d ? "WITH" : "AGAINST", `${lf.who} won ${hm(lf.t)} @${fmt(lf.vw)}f`, `${lf.who} won at ${fmt(lf.vw)} ${hm(lf.t)} (${lf.res.toLowerCase()}, ${fmt(lf.lots)} lots) [M lots / I side]; CVD 15 min ${sgn(Math.round(s.cvd15))}, day peak ${hm(s.cvdPeakT)}`, { fight: lf });
    // 7 VPIN
    const v = s.vpin;
    if (!v || v.n < VPIN_N) row("VPIN", "CNC", v ? `${v.n} of ${VPIN_N} buckets` : "NIFTY-only gauge", v ? `could not check: ${v.n} of ${VPIN_N} buckets so far (shadow)` : "could not check: VPIN runs on NIFTY futures only");
    else { const st7 = v.one === 0 ? "NEITHER" : v.lean === d ? "WITH" : v.lean === -d ? "AGAINST" : "NEITHER";
      row("VPIN", st7, `${v.one}/${VPIN_N} one-sided · pct ${v.pct == null ? "—" : v.pct.toFixed(2)}`, `${v.one} of ${VPIN_N} buckets one-sided (${v.b} buyers · ${v.s} sellers), toxicity pct ${v.pct == null ? "—" : v.pct.toFixed(2)} of today (shadow) [I]`, { vpin: v }); }
    // 8 CROSS-INDEX
    const xi = xindex(T, feedT, idx);
    if (!xi.push) row("CROSS-INDEX", "CNC", "no push yet", "could not check: no swing on the 5-min bars yet");
    else { const withHer = xi.push.dir === d, took = xi.took; const st8 = (withHer && took >= 2) || (!withHer && took === 0) ? "WITH" : (withHer && took === 0) || (!withHer && took >= 2) ? "AGAINST" : "NEITHER";
      row("CROSS-INDEX", st8, `push ${xi.push.dir > 0 ? "▲" : "▼"} ${hm(xi.push.at)} · ${took}/3 took`, `${idx} latest push ${xi.push.dir > 0 ? "UP" : "DOWN"} to ${fmt(xi.push.to)} at ${hm(xi.push.at)} (${withHer ? "with you" : "against you"}) · ${took} of 3 took their prior swing: ${xi.per.map(p => `${p.idx} ${p.status}${p.prev ? " " + fmt(p.prev) : ""}`).join(" · ")} [M stamps / I meaning]${xi.per.some(p => p.thin) ? " · SENSEX thin: witness" : ""}`, { x: xi }); }
    // 9 ROOM
    if (g.G == null) row("ROOM", "CNC", "no give-up yet", "could not check: no give-up level yet");
    else { const st9 = g.toG > s.B && (g.toA == null || g.toA >= g.toG) ? "WITH" : "AGAINST";
      row("ROOM", st9, `−${g.toG} stop${g.toA != null ? ` · +${g.toA} wall` : ""} · B ${fmt(s.B)}`, `invalid at ${fmt(g.G)} fut (${g.toG} pts; one candle B = ${fmt(s.B, 1)})${g.toA != null ? ` · next wall ${g.toA} pts` : ""} [M]; the stop must be outside one candle and the target at least as far`); }
    // 10 PAYING
    const pay = g.payers;
    if (!pay.length) row("PAYING", "NEITHER", "no payers' front", "no front on the payers' side inside ±8 [M]");
    else { const st10 = pay.some(f => f.state === "UNWINDING") ? "WITH" : pay.every(f => f.state === "BUILDING") ? "AGAINST" : "NEITHER";
      row("PAYING", st10, pay.map(f => `${f.k} ${f.state === "UNWINDING" ? "leaving" : f.state === "BUILDING" ? "building" : "flat"}`).join(" · "), pay.map(f => `${f.leg.toUpperCase()} ${f.k} ${f.state} (peak ${L(f.peak)} at ${hm(f.peakT)}, ${pct(f.off)} off)`).join(" · ") + " [M]; the move needs somebody forced to pay for it", { fronts: pay }); }
    // counts + word
    const counted = C.filter(c => c.st !== "NS");
    const w = counted.filter(c => c.st === "WITH").length, a = counted.filter(c => c.st === "AGAINST").length, n = counted.filter(c => c.st === "NEITHER").length, c = counted.filter(c => c.st === "CNC").length;
    const structA = C.filter(q => STRUCT.includes(q.name) && q.st === "AGAINST").length;
    const rn = C[0].st;
    const word = rn === "AGAINST" || structA >= 2 ? "NO" : (rn === "WITH" && a === 0 && c <= 1 && w >= 6) ? "GO" : "WAIT";
    const againstRows = C.filter(q => q.st === "AGAINST");
    const strongest = againstRows.length ? againstRows[0] : null;
    const why = word === "NO" ? (rn === "AGAINST" ? "the engine would throw you out at the door" : `${structA} structural against`) : word === "GO" ? `${w} with, nothing against` : a ? `${a} against: ${againstRows.map(q => q.name).join(", ")}` : `${n} not there yet`;
    // levels
    const lv = levels(s, g);
    const printed = {
      moneyness: g.delta == null ? null : { delta: g.delta, intrinsic: g.intrinsic, tv: g.tv, deep: g.deep },
      clock: { T, dte: s.dte, expiry: s.expiry, tv: g.tv },
      pain: [g.own, g.other, g.W, g.A].filter(Boolean).map(f => ({ k: f.k, leg: f.leg.toUpperCase(), ltp: f.ltp, avg: f.avg, word: f.avg == null || f.ltp == null ? "—" : f.ltp >= 1.3 * f.avg ? "under water" : f.ltp <= 0.8 * f.avg ? "comfortable" : "near their avg" })),
      pcr: s.pcr,
    };
    return { ok: true, idx, K, ty, side, px: g.px, ltp: g.ltp, d, role: g.role, word, why, counts: { w, a, n, c, of: counted.length }, checks: C, strongest, levels: lv, printed, g, s, hi: HI[word] };
  }
  function levels(s, g) {
    const sp = f => f - s.basis, out = [];
    out.push({ name: "STOP", fut: g.G, spot: Math.round(sp(g.G)), prem: premAt(g, s, sp(g.G)), why: g.Gwhy, who: g.W ? `${g.W.k} ${g.W.leg.toUpperCase()} writers` : null, pts: -g.toG });
    if (g.role === "buy") {
      if (g.A) out.push({ name: "T1", fut: Math.round(g.A.k + s.basis), spot: g.A.k, prem: premAt(g, s, g.A.k), why: `${g.A.k} ${g.A.leg.toUpperCase()} wall · ${g.A.state.toLowerCase()}`, pts: g.toA, cond: g.A.state === "BUILDING" ? `only if ${g.A.k} ${g.A.leg.toUpperCase()} comes off its peak` : null });
      else out.push({ name: "T1", fut: null, spot: null, prem: null, why: "no wall ahead inside ±8", absence: "checked" });
      const beyond = g.payers.find(f => g.A && (g.d > 0 ? f.k > g.A.k : f.k < g.A.k));
      if (beyond) out.push({ name: "T2", fut: Math.round(beyond.k + s.basis), spot: beyond.k, prem: premAt(g, s, beyond.k), why: `${beyond.k} ${beyond.leg.toUpperCase()} · ${beyond.state.toLowerCase()}`, pts: Math.round(Math.abs(beyond.k + s.basis - s.fut)), cond: beyond.state === "BUILDING" ? `only if ${beyond.k} comes off its peak` : null });
      else out.push({ name: "T2", fut: null, spot: null, prem: null, why: "no second front beyond T1", absence: "checked" });
    } else {
      const be = g.ty === "CE" ? g.K + (g.px || 0) : g.K - (g.px || 0);
      out.push({ name: "KEEP ALL", fut: Math.round(g.K + s.basis), spot: g.K, prem: 0, why: `close ${g.ty === "CE" ? "≤" : "≥"} ${fmt(g.K)} spot`, pts: Math.round(Math.abs(g.K + s.basis - s.fut)) });
      out.push({ name: "BREAKEVEN", fut: Math.round(be + s.basis), spot: Math.round(be), prem: g.px, why: "the credit is gone", pts: Math.round(Math.abs(be + s.basis - s.fut)) });
    }
    return out;
  }
  function xindex(T, feedT, focus) {
    const key = `x|${T}|${feedT}|${focus}`; if (memo.has(key)) return memo.get(key);
    const per = IDX.map(i => { const s = snap(i, T, feedT); return { idx: i, thin: !!THIN[i], push: s.ok ? s.push : null, status: s.ok && s.push ? s.push.status : "NAHI", prev: s.ok && s.push ? s.push.prev : null }; });
    const f = per.find(p => p.idx === focus); const took = per.filter(p => p.status === "TOOK").length;
    const r = { push: f && f.push, per, took, first: per.filter(p => p.push).sort((a, b) => a.push.at - b.push.at)[0] };
    memo.set(key, r); return r;
  }

  // ---------- the board ----------
  function board(T, feedT, hers) {
    const cands = [];
    for (const idx of IDX) { const s = snap(idx, T, feedT); if (!s.ok) continue; const A = s.atm, st = s.step;
      for (const [K, ty, side, m] of [[A, "CE", "BUY", "ATM"], [A, "PE", "SELL", "ATM"], [A, "PE", "BUY", "ATM"], [A, "CE", "SELL", "ATM"], [A + st, "PE", "SELL", "ITM"], [A - st, "CE", "SELL", "ITM"]]) {
        const v = validate(idx, K, ty, side, null, T, feedT); if (v.ok) cands.push(Object.assign(v, { m })); } }
    const rank = v => [{ GO: 0, WAIT: 1, NO: 2 }[v.word], -v.counts.w, v.counts.a, v.counts.c, IDX.indexOf(v.idx), v.m === "ATM" ? 0 : 1];
    const cmp = (p, q) => { const a = rank(p), b = rank(q); for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; };
    cands.sort(cmp);
    let herRank = null, better = null, slots = null;
    if (hers && hers.ok) {
      herRank = 1 + cands.filter(c => cmp(c, hers) < 0).length;
      better = cands.find(c => cmp(c, hers) < 0) || null;
      const same = cands.find(c => c.idx === hers.idx && c.d === hers.d && c.role !== hers.role);
      const opp = cands.find(c => c.idx === hers.idx && c.d === -hers.d);
      const oth = cands.find(c => c.idx !== hers.idx);
      slots = { same, opp, oth };
    }
    const top = cands[0];
    const verdict = !top ? "no board" : (top.word === "NO" || (top.word === "WAIT" && top.counts.w < 5)) ? "nothing clean — stand aside" : herRank === 1 ? "your trade is the best on the board" : better ? `better: ${better.side} ${better.idx} ${better.K} ${better.ty}` : "";
    return { cands, herRank, better, slots, top, verdict };
  }
  const reason = v => { const a = v.checks.filter(c => c.st === "AGAINST"); return v.word === "GO" ? `${v.counts.w} with, nothing against` : a.length ? `${a.map(c => c.name.toLowerCase()).slice(0, 2).join(", ")} against` : `${v.counts.n} not there yet`; };

  // ---------- the market read ----------
  function read(idx, T, feedT) {
    const s = snap(idx, T, feedT); if (!s.ok) return { ok: false, word: "NO CHAIN YET", rows: [], levels: [] };
    const x = s.x, dy = s.day, lf = s.last, fresh = lf && s.T - lf.t <= 1800;
    const pressing = fresh && Math.sign(s.cvd15) === lf.winner ? lf.winner : 0;
    let word, sub;
    if (dy.type === "EARLY") { word = "EARLY"; sub = "IB building"; }
    else if (dy.type === "TREND") { word = dy.dir > 0 ? "TREND UP" : "TREND DOWN"; sub = `since ${hm(dy.since)}`; }
    else if (s.box && s.pin && s.pin.k >= s.box.spotLo - s.step && s.pin.k <= s.box.spotHi + s.step) { word = `RANGE → PIN ${fmt(s.pin.k)}`; sub = pressing ? `${pressing > 0 ? "buyers" : "sellers"} pressing since ${hm(lf.t)}` : `boxed since ${hm(s.box.since)}`; }
    else if (pressing) { word = pressing > 0 ? "BUYERS PRESSING" : "SELLERS PRESSING"; sub = `${dy.type} since ${hm(dy.since)}`; }
    else { word = dy.type; sub = `since ${hm(dy.since)}`; }
    const R = [];
    const r = (k, pill, cells, tip, abs) => R.push({ k, pill, cells, tip, abs, cell: [pill && pill.t, ...cells].filter(Boolean).join(" · ") });
    const P = (t, tone = "n") => ({ t, tone });
    const fr = f => ({ text: `${f.k} ${f.leg.toUpperCase()} ${L0(f.oi)}`, pill: P(f.state === "UNWINDING" ? "leaving" : f.state === "BUILDING" ? "building" : "flat", f.state === "UNWINDING" ? "a" : "n"), tip: `${f.k} ${f.leg.toUpperCase()} ${L(f.oi)} ${f.state}, peak ${L(f.peak)} ${hm(f.peakT)}, ${pct(f.off)} off, ${f.upd} updates since [M] · ${HI[f.state]}` });
    const bfCell = s.bf ? `${s.bfFrom}–${s.bfTo} from backfill [I]` : null, flowCell = s.lateFlow ? `flow from ${s.flowFrom.slice(0, 5)}` : null;
    r("DAY", P(`${dy.type}${dy.type === "TREND" ? (dy.dir > 0 ? " ▲" : " ▼") : ""}`), [`since ${hm(dy.since)}`, s.whose.text, flowCell].filter(Boolean), `daytype [I] ${dy.type} since ${hm(dy.since)}: ${dy.why || "IB building"} · fights won ${s.whose.b} buyers / ${s.whose.s} sellers [I]`);
    r("SHAPE", P(s.box ? "boxed" : "range"), (s.box ? [`${fmt(s.box.spotLo)}–${fmt(s.box.spotHi)} spot`, `since ${hm(s.box.since)}`] : [`${fmt(s.sLo)}–${fmt(s.sHi)} spot`, `${hm(s.sLoT)}–${hm(s.sHiT)}`]).concat(bfCell ? [bfCell] : []), s.box ? `box ${fmt(s.box.lo)}–${fmt(s.box.hi)} fut (${fmt(s.box.spotLo)}–${fmt(s.box.spotHi)} spot) since ${hm(s.box.since)} [I: ≤ 0.6 × IB] · day range ${fmt(s.sLo)} (${hm(s.sLoT)}) – ${fmt(s.sHi)} (${hm(s.sHiT)}) spot` : `day range ${fmt(s.sLo)} ${hm(s.sLoT)} – ${fmt(s.sHi)} ${hm(s.sHiT)} spot · fut ${fmt(s.fLo)}–${fmt(s.fHi)} [M]`);
    const xi = xindex(T, feedT, idx);
    if (xi.push) r("SYNC", P(`${xi.took}/3 took`, xi.took === 0 && T - xi.push.at <= 900 ? "a" : "n"), [`push ${xi.push.dir > 0 ? "▲" : "▼"} ${hm(xi.push.at)}`, `to ${fmt(xi.push.to)} fut`], xi.per.map(p => `${p.idx} ${p.status}${p.prev ? " vs " + fmt(p.prev) : ""}${p.thin ? " (witness)" : ""}`).join(" · ") + ` [M stamps]${xi.first ? ` · ${xi.first.idx} moved first ${hm(xi.first.push.at)}` : ""}`);
    else r("SYNC", P("can't check", "CNC"), ["no push yet"], "could not check: no swing yet on 5-min bars", "cnc");
    r("PIN", s.pin ? P(fmt(s.pin.k)) : P("none", "g"), s.pin ? [`CE ${L0(s.pin.ce)}`, `PE ${L0(s.pin.pe)}`] : ["no strike has both legs ≥ ½"], s.pin ? `the strike inside the nine with the largest CE+PE where both legs ≥ ½ their side's largest [M] · ${s.dte === 0 ? "expiry today: the magnet" : `${s.dte} DTE`}` : "checked: no strike has both legs ≥ ½ their side's largest", s.pin ? null : "checked");
    const ce = s.fronts.ce, pe = s.fronts.pe;
    R.push({ k: "CEILING", fronts: ce.map(fr), cells: [], cell: ce.map(f => `${f.k} ${f.state}`).join(" · "), tip: ce.length ? "the top-2 CE fronts above spot by peak OI [M]" : "checked: no CE front above spot inside ±8", abs: ce.length ? null : "checked" });
    R.push({ k: "FLOOR", fronts: pe.map(fr), cells: [], cell: pe.map(f => `${f.k} ${f.state}`).join(" · "), tip: pe.length ? "the top-2 PE fronts below spot by peak OI [M]" : "checked: no PE front below spot inside ±8", abs: pe.length ? null : "checked" });
    r("FLOW", fresh ? P(`${lf.who} won`, pressing ? "a" : "n") : P("quiet", "g"), (fresh ? [`${hm(lf.t)} @${fmt(lf.vw)} fut`, `CVD15 ${sgn(Math.round(s.cvd15))}`] : [`30 min`, `CVD15 ${sgn(Math.round(s.cvd15))}`]).concat(flowCell ? [flowCell] : []), `${fresh ? `${lf.who} won at ${fmt(lf.vw)} ${hm(lf.t)} (${lf.res.toLowerCase()}, ${fmt(lf.lots)} lots) · ` : "no fight inside 30 min · "}CVD day peak ${hm(s.cvdPeakT)}, ${sgn(Math.round(s.cvdSincePeak))} since · 15 min ${sgn(Math.round(s.cvd15))} with price ${sgn(Math.round(s.px15))} [M lots / I side]`);
    r("VWAP", P(s.vwapSide > 0 ? "above" : "below"), [`${fmt(s.vwap)} fut`, `${fmt(s.vwap - s.basis)} spot`, `since ${hm(s.vwapSince)}`].concat(flowCell ? [flowCell] : []), `session VWAP ${fmt(s.vwap, 1)} fut (${fmt(s.vwap - s.basis)} spot) · price ${s.vwapSide > 0 ? "above" : "below"} since ${hm(s.vwapSince)} [M]`);
    const v = s.vpin;
    if (!v) r("VPIN", P("can't check", "CNC"), ["NIFTY-only gauge"], "could not check: VPIN runs on NIFTY futures only", "cnc");
    else if (v.n < VPIN_N) r("VPIN", P("can't check", "CNC"), [`${v.n} of ${VPIN_N} buckets`], "could not check: fewer than 10 buckets (shadow)", "cnc");
    else r("VPIN", P(`${v.one}/10 ${v.lean > 0 ? "buyers" : v.lean < 0 ? "sellers" : "even"}`, v.one >= 4 ? "a" : "n"), [`pct ${v.pct == null ? "—" : v.pct.toFixed(2)}`], `toxicity ${v.vpin.toFixed(3)}, pct ${v.pct == null ? "—" : v.pct.toFixed(2)} of today (shadow) · ${v.one} of 10 buckets one-sided: ${v.b} buyers, ${v.s} sellers [I]`);
    const p = s.pcr;
    r("PCR(9)", p.now && p.now.r != null ? P(p.now.r.toFixed(2)) : P("can't check", "CNC"), p.now ? [p.t1400 && p.t1400.r != null && T >= 14 * 3600 ? `${p.t1400.r.toFixed(2)} @14:00` : p.h1 && p.h1.r != null ? `${p.h1.r.toFixed(2)} 1h ago` : "—", p.open && p.open.r != null ? `${p.open.r.toFixed(2)} @09:30` : "—"] : ["no nine yet"], p.now ? `PE ${L(p.now.p)} / CE ${L(p.now.c)} over the nine around ATM [M]${p.h1 && p.h1.r != null ? ` · an hour ago ${p.h1.r.toFixed(2)}` : ""}${p.t1400 && p.t1400.r != null ? ` · at 14:00 ${p.t1400.r.toFixed(2)} (PE ${L(p.t1400.p)})` : ""}` : "could not check");
    const straddle = s.pin && s.pin.ki >= 0 ? (ltpAt(x, "ce", s.i, s.pin.ki) || 0) + (ltpAt(x, "pe", s.i, s.pin.ki) || 0) : null;
    const prac = T >= 14 * 3600 + 45 * 60 && T < PRACTICE;
    r("CLOCK", P(s.dte === 0 ? "0DTE" : `${s.dte} DTE`, prac ? "a" : "n"), [`${Math.max(0, Math.round((CLOSE - T) / 60))} min`, `straddle ${straddle == null ? "—" : fmt(straddle, 1)}`, prac ? `15:00 in ${Math.round((PRACTICE - T) / 60)}` : null].filter(Boolean), `${hms(T)} · expiry ${s.expiry}${s.dte === 0 ? " — today: the pin straddle's time value burns to 0 by 15:30 [I]" : ""} · ${T >= PRACTICE ? "past your 15:00 practice" : `your 15:00 practice in ${Math.round((PRACTICE - T) / 60)} min`} (reminder, blocks nothing)`);
    // levels to watch: ≤ 4, two above two below, nearest first
    const cand = [];
    const add = (spot, fut, what, conf, deny, kind) => cand.push({ spot: Math.round(spot), fut: Math.round(fut), what, conf, deny, kind });
    for (const f of ce) add(f.k, f.k + s.basis, `${f.k} CE ${L0(f.oi)} ceiling`, f.state === "UNWINDING" ? ["trending-up", "writers leaving"] : ["eye", "needs CE off"], f.state === "BUILDING" ? ["shield", "CE building"] : ["shield", "CE holds"], "wall");
    for (const f of pe) add(f.k, f.k + s.basis, `${f.k} PE ${L0(f.oi)} floor`, f.state === "UNWINDING" ? ["trending-down", "writers leaving"] : ["eye", "needs PE off"], f.state === "BUILDING" ? ["shield", "PE building"] : ["shield", "PE holds"], "wall");
    add(s.sHi, s.fHi, `day high ${hm(s.sHiT)}`, ["zap", "lots accepted"], ["undo-2", "back below"], "hi");
    add(s.sLo, s.fLo, `day low ${hm(s.sLoT)}`, ["zap", "lots accepted"], ["undo-2", "back above"], "lo");
    add(s.vwap - s.basis, s.vwap, "VWAP", ["activity", "minute opens there"], ["activity", "rejects"], "vwap");
    if (fresh) add(lf.vw - s.basis, lf.vw, `${lf.who} won ${hm(lf.t)}`, ["swords", "fight re-won"], ["swords", "fight lost"], "fight");
    const above = cand.filter(c => c.spot > s.spot).sort((a, b) => a.spot - b.spot), below = cand.filter(c => c.spot <= s.spot).sort((a, b) => b.spot - a.spot);
    const dedup = arr => { const o = []; for (const c of arr) if (!o.some(q => Math.abs(q.spot - c.spot) < s.B)) o.push(c); return o; };
    const lv = [...dedup(above).slice(0, 2).reverse(), ...dedup(below).slice(0, 2)];
    // falsifiers
    const fals = [];
    for (const f of [...ce, ...pe].slice(0, 2)) fals.push(f.state === "UNWINDING" ? `${f.k} ${f.leg.toUpperCase()} rebuilt above ${L(f.peak)}` : `${f.k} ${f.leg.toUpperCase()} off its ${hm(f.peakT)} peak by 15 %`);
    if (fresh) fals.push(`${lf.winner > 0 ? "sellers" : "buyers"} win a fight ${lf.winner > 0 ? "below" : "above"} ${fmt(lf.vw)} fut`);
    return { ok: true, idx, word, sub, rows: R, levels: lv, falsifiers: fals.slice(0, 3), s };
  }

  // ---------- in trade ----------
  function entrySnap(trade, feedT) {
    const key = `e|${trade.id}`; if (memo.has(key)) return memo.get(key);
    const v = validate(trade.idx, trade.K, trade.ty, trade.side, trade.px, trade.t0, Math.max(trade.t0, feedT));
    const s = v.s, g = v.g;
    const own = g.own, under = g.other;
    const e = { t0: trade.t0, fut: s.fut, spot: s.spot, W: g.W ? { k: g.W.k, leg: g.W.leg, oi: g.W.oi, peak: g.W.peak } : null, A: g.A ? { k: g.A.k, leg: g.A.leg, oi: g.A.oi } : null,
      under: own ? { k: own.k, leg: own.leg, oi: own.oi } : null, pcr: s.pcr.now && s.pcr.now.r, cvd: s.cvd, vwapSide: s.vwapSide, fights: s.fights.length, vpin: s.vpin && s.vpin.pct, prem: trade.px || g.ltp, ltp0: g.ltp, chips: g.chips, day: s.day.type, G: g.G, word: v.word, counts: v.counts, checks: v.checks.map(c => ({ name: c.name, st: c.st, cell: c.cell })) };
    memo.set(key, e); return e;
  }
  // the trade's path: walked minute by minute from the mark; W and G are sticky like fold's (DESIGN §5.1 plumbing in miniature)
  //   W switches only when a BUILDING front at its peak forms between price and W on the defending leg; G moves only when her side wins again
  function tradePath(trade, feedT, T) {
    const key = `tp|${trade.id}`; let P = memo.get(key);
    const tf = Math.min(T, feedT);
    if (!P) { const v0 = validate(trade.idx, trade.K, trade.ty, trade.side, trade.px, trade.t0, Math.max(trade.t0, feedT)); if (!v0.ok) return null;
      P = { minutes: [], W: v0.g.W, G: v0.g.G, Gwhy: v0.g.Gwhy, lastG: trade.t0, fold: null, upto: trade.t0, d: v0.g.d, bleedOn: false, pb: null }; memo.set(key, P); }
    for (let t = P.upto + 60 - (P.upto % 60); t <= tf && t <= CLOSE; t += 60) {
      if (P.fold) break;
      if (trade.exitT && t >= trade.exitT) { P.fold = { t: trade.exitT, G: P.G, exit: true }; P.minutes.push({ t: trade.exitT, ev: "OUT", text: trade.exitWhy || "closed" }); break; }
      const s = snap(trade.idx, t, Math.max(t, feedT)); if (!s.ok) continue;
      const x = s.x, d = P.d, defLeg = d > 0 ? "pe" : "ce";
      // refresh W's numbers; switch if a front formed between price and W
      if (P.W) { const ki = x.ks.indexOf(P.W.k); P.W = front(x, defLeg, s.i, ki) || P.W; }
      let mx = 0; for (let k = 0; k < x.nk; k++) mx = Math.max(mx, x[defLeg].oi[s.i][k] || 0);
      for (let k = 0; k < x.nk; k++) { const K = x.ks[k]; const between = P.W ? (d > 0 ? K < s.spot && K > P.W.k : K > s.spot && K < P.W.k) : (d > 0 ? K < s.spot : K > s.spot);
        if (!between) continue; const f = front(x, defLeg, s.i, k); if (f && f.oi >= 0.5 * mx && f.state === "BUILDING" && f.off <= 0.02) { P.W = f; P.minutes.push({ t, ev: "W", text: `wall behind you → ${f.k} ${defLeg.toUpperCase()} ${L(f.oi)}` }); break; } }
      // G: a new own-side win beyond price resets the give-up
      const z = zoneFight(s, d, s.fut); if (z && z.t > P.lastG && z.t > trade.t0 && d * (s.fut - z.zone) >= 2 * s.B && d * (P.G - z.zone) > 0) { P.G = z.zone; P.Gwhy = `${z.who} won ${hm(z.t)} from ${fmt(z.zone)}`; P.lastG = z.t; P.minutes.push({ t, ev: "G", text: `your side won again · give-up → ${fmt(z.zone)} fut` }); }
      const ac = accepted(s, d, P.G); if (ac.acc && !P.protoFold) { P.protoFold = { t, G: P.G }; P.minutes.push({ t, ev: "FOLD", text: `prototype: ${fmt(P.G)} accepted — the engine's word decides` }); }
      if (P.W && P.W.bleed && !P.bleedOn) { P.bleedOn = true; P.minutes.push({ t, ev: "BLEED", text: `W-bleed · ${P.W.k} ${defLeg.toUpperCase()} ${pct(P.W.off)} off its ${L(P.W.peak)} peak, ${P.W.upd} updates` }); } if (P.W && !P.W.bleed) P.bleedOn = false;
      P.upto = t;
    }
    return P;
  }
  function inTrade(trade, T, feedT) {
    const P = tradePath(trade, feedT, T); if (!P) return { ok: false };
    const e = entrySnap(trade, feedT);
    const g0 = { W: P.W, G: P.G, Gwhy: P.Gwhy };
    const v = validate(trade.idx, trade.K, trade.ty, trade.side, trade.px, T, feedT, g0);
    if (!v.ok) return { ok: false };
    const s = v.s, g = v.g, d = g.d;
    const W = g.W ? front(s.x, g.W.leg, s.i, g.W.ki) || g.W : null;
    const folded = !!P.fold && P.fold.t <= T, foldT = P.fold ? P.fold.t : null, protoFold = !!P.protoFold && P.protoFold.t <= T;
    const now = folded ? "OUT" : protoFold ? "FOLD" : g.now;
    const off = W ? (W.state === "UNWINDING" || W.bleed) : false;
    const wrongSide = d * (s.fut - e.fut) < 0;
    const against = s.fights.filter(f => f.t > e.t0 && f.winner === -d), withF = s.fights.filter(f => f.t > e.t0 && f.winner === d);
    const recentAgainst = against.filter(f => s.T - f.t <= 3000);
    let pb = null;
    if (!folded && wrongSide) pb = off ? "GAVE UP" : recentAgainst.length && recentAgainst[recentAgainst.length - 1].res !== "ABSORBED" ? "UNDECIDED" : "PULLBACK";
    const word = folded ? "OUT" : protoFold ? "FOLD" : pb === "GAVE UP" ? "GAVE UP" : now === "PAST GIVE-UP" ? "PAST GIVE-UP" : "HOLD";
    const chips = Object.assign({}, g.chips, { OI: !W ? "QUIET" : W.state === "BUILDING" ? "WITH" : W.state === "UNWINDING" ? "AGAINST" : "QUIET" });
    const zoneAlone = !folded && chips.ZONE === "WITH" && chips.FLOW !== "WITH" && chips.OI !== "WITH";
    const prem = folded ? premAtTime(trade, foldT, feedT) : g.ltp, peakP = premPeak(trade, feedT, folded ? foldT : T);
    const Ld = [];
    const row = (fact, entry, now, st, tip) => Ld.push({ fact, entry, now, st, tip });
    const mv = Math.round(s.fut - e.fut);
    row("fut / spot", `${fmt(e.fut)} / ${fmt(e.spot)}`, `${fmt(s.fut)} / ${fmt(s.spot)} (${sgn(mv)})`, mv === 0 ? "NEITHER" : d * mv > 0 ? "WITH" : "AGAINST", "price since entry, fut and spot [M]");
    if (W) row("W · wall behind you", e.W ? `${e.W.k} ${e.W.leg.toUpperCase()} ${L(e.W.oi)}` : "—", `${W.k} ${W.leg.toUpperCase()} ${L(W.oi)} · ${pct(W.off)} off ${L(W.peak)} peak · ${W.upd} upd`, W.state === "BUILDING" ? "WITH" : off ? "AGAINST" : "NEITHER", `${W.k} ${W.leg.toUpperCase()} writers: peak ${L(W.peak)} at ${hm(W.peakT)}, ${W.state}, ${W.upd} updates since the peak${W.bleed ? " · W-BLEED (slow leak, amber)" : ""} [M]${e.W && e.W.k !== W.k ? ` · at entry the wall was ${e.W.k} ${e.W.leg.toUpperCase()}` : ""}`);
    else row("W · wall behind you", "—", "no front behind", "NEITHER", "checked: no front behind price");
    if (g.own) row(`${g.K} ${g.ty} writers ${g.role === "buy" ? "against" : "with"} you`, e.under ? L(e.under.oi) : "—", `${L(g.own.oi)} (${sgn(Math.round((g.own.oi - (e.under ? e.under.oi : g.own.oi)) / 100))}L)`, !e.under ? "NEITHER" : g.role === "buy" ? (g.own.oi > e.under.oi * 1.02 ? "AGAINST" : g.own.oi < e.under.oi * 0.98 ? "WITH" : "NEITHER") : (g.own.oi > e.under.oi * 1.02 ? "WITH" : g.own.oi < e.under.oi * 0.98 ? "AGAINST" : "NEITHER"), `OI at your strike on your leg: the writers on the other side of your ${g.role} [M]`);
    row("fights since entry", "—", `${d > 0 ? "buyers" : "sellers"} ${withF.length} · ${d > 0 ? "sellers" : "buyers"} ${against.length}`, withF.length === against.length ? "NEITHER" : withF.length > against.length ? "WITH" : "AGAINST", [...withF, ...against].sort((a, b) => a.t - b.t).map(f => `${f.who} ${hm(f.t)} @${fmt(f.vw)}`).join(" · ") || "no fight since entry [I]");
    row("VWAP side", e.vwapSide > 0 ? "above" : "below", s.vwapSide > 0 ? `above ${fmt(s.vwap)}` : `below ${fmt(s.vwap)}`, s.vwapSide === d ? "WITH" : "AGAINST", `fut vs session VWAP ${fmt(s.vwap, 1)} [M]`);
    row("premium", fmt(e.prem, 2), `${fmt(prem, 2)} · peak ${fmt(peakP.v, 2)} ${hm(peakP.t)} · gave back ${fmt(peakP.v - prem, 2)}`, "NEITHER", "your option's LTP [M] — not a read, a fact");
    row("zone · give-up", fmt(e.G), `${fmt(g.G)} fut · ${g.Gwhy}`, chips.ZONE === "WITH" ? "WITH" : chips.ZONE === "AGAINST" ? "AGAINST" : "NEITHER", "where your side last won; out if accepted [I]");
    const pcrNow = s.pcr.now && s.pcr.now.r, dc = Math.round(s.cvd - e.cvd);
    row("PCR(9) · CVD since entry", `${e.pcr == null ? "—" : e.pcr.toFixed(2)} · 0`, `${pcrNow == null ? "—" : pcrNow.toFixed(2)} · ${sgn(dc)}`, dc === 0 ? "NEITHER" : Math.sign(dc) === d ? "WITH" : "AGAINST", "PCR over the nine around ATM [M] · CVD of the futures since your mark [I side]");
    if (s.vpin) row("VPIN pct", e.vpin == null ? "—" : e.vpin.toFixed(2), s.vpin.pct == null ? "—" : `${s.vpin.pct.toFixed(2)} · ${s.vpin.one}/10 ${s.vpin.lean > 0 ? "buyers" : s.vpin.lean < 0 ? "sellers" : "even"}`, chips.VPIN === "WITH" ? "WITH" : chips.VPIN === "AGAINST" ? "AGAINST" : "NEITHER", "toxicity percentile of today (shadow) [I]");
    const theta = s.dte === 0 && g.tv != null ? g.tv / Math.max(1, (CLOSE - T) / 900) : null;
    return { ok: true, trade, e, v, word, now, pb, zoneAlone, folded, foldT, W, off, prem, peakP, ledger: Ld, dist: { fut: Math.abs(s.fut - g.G), spot: Math.abs(s.spot - (g.G - s.basis)), G: g.G, Gspot: Math.round(g.G - s.basis) }, chips, theta, tInTrade: T - e.t0, hi: HI[word], s, g, path: P };
  }
  function premAtTime(trade, t, feedT) { const x = D.idx[trade.idx], ki = x.ks.indexOf(trade.K), i = lastLE(x.t, Math.min(t, feedT)); const p = i >= 0 ? x[trade.ty.toLowerCase()].ltp[i][ki] : null; return p == null ? null : p / 20; }
  function premPeak(trade, feedT, T) {
    const x = D.idx[trade.idx], ki = x.ks.indexOf(trade.K), leg = trade.ty.toLowerCase(); let v = -1, t = trade.t0;
    const i0 = lastLE(x.t, trade.t0), i1 = lastLE(x.t, Math.min(T, feedT));
    for (let i = Math.max(0, i0); i <= i1; i++) { const p = x[leg].ltp[i][ki]; if (p != null && p / 20 > v) { v = p / 20; t = x.t[i]; } }
    return { v: v < 0 ? null : v, t };
  }

  // ---------- events for the console / timeline (precomputed once per index) ----------
  function events(idx) {
    const x = D.idx[idx]; if (x.events) return x.events;
    const ev = [];
    const m5 = x.m5, all = fights(x, m5, CLOSE + 1);
    for (const f of all) ev.push({ t: f.t, idx, kind: "fight", text: `${f.who} won @${fmt(f.vw)} · ${fmt(f.lots)} lots ${f.res.toLowerCase()}`, tone: "n", icon: "swords" });
    // walls: a front turning UNWINDING / a new peak ≥ 10 % over the previous print of that strike, only for fronts ≥ ½ side max
    for (const leg of ["ce", "pe"]) { const Lg = x[leg]; const lastState = new Array(x.nk).fill(null); const lastPeakEv = new Array(x.nk).fill(0), lastLeave = new Array(x.nk).fill(-1e9);
      for (let i = MARKS; i < x.n; i += 3) { let mx = 0; for (let k = 0; k < x.nk; k++) mx = Math.max(mx, Lg.oi[i][k] || 0);
        for (let k = 0; k < x.nk; k++) { const f = front(x, leg, i, k); if (!f || f.oi < 0.5 * mx) { lastState[k] = null; continue; }
          if (lastState[k] && lastState[k] !== f.state) { if (f.state === "UNWINDING" && x.t[i] - lastLeave[k] > 1200) { lastLeave[k] = x.t[i]; ev.push({ t: x.t[i], idx, kind: "wall", text: `${f.k} ${leg.toUpperCase()} writers leaving · ${pct(f.off)} off ${hm(f.peakT)} peak`, tone: "a", icon: "door-open" }); } if (f.state === "BUILDING" && lastState[k] === "UNWINDING") ev.push({ t: x.t[i], idx, kind: "wall", text: `${f.k} ${leg.toUpperCase()} rebuilding · ${L(f.oi)}`, tone: "n", icon: "brick-wall" }); }
          if (f.peakT === x.t[i] && f.peak >= 1.1 * (Lg.oi[Math.max(0, i - MARKS)][k] || 1) && x.t[i] - lastPeakEv[k] > 1200) { lastPeakEv[k] = x.t[i]; ev.push({ t: x.t[i], idx, kind: "wall", text: `wall built · ${f.k} ${leg.toUpperCase()} new peak ${L(f.peak)}`, tone: "n", icon: "brick-wall" }); }
          lastState[k] = f.state; } } }
    // BADA PRINT = the GoCharting decoder's E1 rule (orderflow-desk src/engine/decoder.js printCells, DEC): per CLOSED 5-min
    // bar, the largest one-price cell whose one side is >= 50x the session's median cell (bars 0..i), >= 25 % of the bar's
    // volume and >= 80 % one-sided, after 6 warm-up bars. Cells are built from the Upstox 1-s bars (each second's volume at
    // its last price, its buy share as recorded) [I] -- an approximation of her GoCharting ladder, never a top-N.
    { const P = { CELL_X: 50, CELL_SHARE: 0.25, ONE_SIDED: 0.8, WARM: 6 }, last = x.bars.length ? x.bars[x.bars.length - 1][0] : 0, B5 = new Map();
      for (const b of x.bars) { if (!(b[2] > 0)) continue; const k = Math.floor(b[0] / 300); let B = B5.get(k); if (!B) B5.set(k, B = { t: k * 300, vol: 0, cells: new Map() });
        B.vol += b[2]; let c = B.cells.get(b[1]); if (!c) B.cells.set(b[1], c = { b: 0, s: 0 }); const bu = Math.min(b[2], Math.max(0, b[3] || 0)); c.b += bu; c.s += b[2] - bu; }
      const all = []; let n = 0;
      for (const B of [...B5.values()].sort((a, b) => a.t - b.t)) {
        if (B.t + 300 > last) break;                                            // the open bar never prints (decoder: closed bars only)
        for (const c of B.cells.values()) all.push(c.b + c.s);
        if (n++ < P.WARM) continue;
        const m = med(all); if (!m) continue; let best = null;
        for (const [p, c] of B.cells) { const tot = c.b + c.s, size = Math.max(c.b, c.s);
          if (size >= P.CELL_X * m && size >= P.CELL_SHARE * B.vol && size / tot >= P.ONE_SIDED && (!best || size > best.size)) best = { p, size, buy: c.b > c.s }; }
        if (best) ev.push({ t: B.t + 300, idx, kind: "print", text: `BADA ${best.buy ? "BUYER" : "SELLER"} ${best.size >= 1e4 ? Math.round(best.size / 1000) + "K" : (best.size / 1000).toFixed(1) + "K"} (${fmt(Math.round(best.size / (x.lot || 1)))} lots) @${fmt(best.p / 10)} · ${Math.round(best.size / m)}× median cell`, tone: "a", icon: "zap" });
      } }
    // daytype changes
    let prev = null; for (let b = 1; b <= m5.length; b++) { const dy = daytype(x, m5.slice(0, b), m5[b - 1].t + 300); const sig = dy.type + dy.dir + dy.since; if (sig !== prev) { prev = sig; if (dy.type !== "EARLY") ev.push({ t: dy.since, idx, kind: "read", text: `day read → ${dy.type}${dy.type === "TREND" ? (dy.dir > 0 ? " ▲" : " ▼") : ""} · ${dy.why || ""}`, tone: "a", icon: "compass" }); } }
    // pin changes
    let pp = null; for (let i = 0; i < x.n; i += 6) { const p = pinOf(x, i, x.atm[i]); const k = p ? p.k : null; if (k !== pp) { pp = k; if (k) ev.push({ t: x.t[i], idx, kind: "oi", text: `pin → ${fmt(k)} · CE ${L(p.ce)} · PE ${L(p.pe)}`, tone: "n", icon: "magnet" }); } }
    // VPIN one-sided buckets (NIFTY)
    if (idx === "NIFTY") for (const r of D.vpin) if (Math.abs(r[2]) >= 0.5) ev.push({ t: r[0], idx, kind: "vpin", text: `VPIN bucket ${r[1]} one-sided ${r[2] > 0 ? "buyers" : "sellers"} · imb ${Math.abs(r[2]).toFixed(2)}`, tone: "n", icon: "radio" });
    ev.sort((a, b) => a.t - b.t); x.events = ev; x.eventsAt = x.t.length ? x.t[x.t.length - 1] : 0; return ev;
  }
  function tradeEvents(trade, feedT) {
    const P = tradePath(trade, feedT, CLOSE); if (!P) return [];
    const key = `te|${trade.id}|${P.upto}`; if (memo.has(key)) return memo.get(key);
    const ev = [{ t: trade.t0, idx: trade.idx, kind: "trade", text: `marked ${trade.side} ${trade.idx} ${trade.K} ${trade.ty} @${fmt(trade.px, 2)}`, tone: "b", icon: "flag" }];
    for (const m of P.minutes) ev.push({ t: m.t, idx: trade.idx, kind: "trade", text: m.text, tone: m.ev === "FOLD" || m.ev === "OUT" ? "r" : m.ev === "BLEED" ? "a" : "n", icon: m.ev === "FOLD" ? "octagon-x" : m.ev === "OUT" ? "flag-off" : m.ev === "BLEED" ? "droplets" : m.ev === "W" ? "shield" : "flag" });
    let lastPb = null;
    for (let t = trade.t0 + 60; t <= (P.fold ? P.fold.t : CLOSE); t += 60) { const r = inTrade(trade, t, Math.max(feedT, CLOSE)); if (!r.ok) continue;
      if (r.pb !== lastPb && r.pb && (r.pb === "GAVE UP" || lastPb == null)) ev.push({ t, idx: trade.idx, kind: "trade", text: `${r.pb} · fut ${sgn(Math.round(r.s.fut - r.e.fut))} vs entry${r.pb === "GAVE UP" ? " · the wall behind you is off" : ""}`, tone: r.pb === "GAVE UP" ? "r" : "a", icon: r.pb === "GAVE UP" ? "flag-off" : "undo-2" }); if (r.pb) lastPb = r.pb; }
    ev.sort((a, b) => a.t - b.t); memo.set(key, ev); return ev;
  }

  return { load, apply, snap, validate, board, read, inTrade, entrySnap, tradePath, events, tradeEvents, premAtTime, xindex, reason, premAt, hm, hms, fmt, sgn, pct, L, L0, IDX, OPEN, CLOSE, PRACTICE, HI, get data() { return D; } };
})();
