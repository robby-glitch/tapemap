/* verdict.js -- RULES.md sections 2-5, written once. DRAFT, not registered.
 *
 * Pure: (trade, one index-day of per-minute facts) -> one read per finished minute.
 * The facts are TapeMap's own (fronts / board / grounds / trendbox, cut to each
 * minute by scratch/build_facts.py). Nothing here reads a premium candle to decide:
 * the premium only feeds the NOISE tag, P&L and the context line.
 * Used by the prototype page and by scratch/replay.js (the report's tables).
 */
(function (root) {
  "use strict";
  const PERSIST = 3, RECENT = 15, REASON_GONE = 15;   // RULES.md §8, fixed
  const STRONG = 0.5;                                  // grounds.STRONG, reused

  const mm = (t) => +t.slice(0, 2) * 60 + +t.slice(3, 5);
  const hm = (n) => String(Math.floor(n / 60)).padStart(2, "0") + ":" + String(n % 60).padStart(2, "0");
  const L = (x) => (x / 1e5).toFixed(1) + "L";
  const K = (k) => Number(k).toLocaleString("en-IN");
  const dom = (a, b) => a >= 2 && a >= 2 * b;

  function thesis(side, role) {
    const d = (side === "CE") === (role === "long") ? 1 : -1;
    return { d, buyer: role === "long", Q: d > 0 ? "CE" : "PE", R: d > 0 ? "PE" : "CE" };
  }

  function frontWords(f) {
    if (!f) return "not read";
    if (!f.built) return "never built today";
    const off = (f.peak - f.chg) / Math.max(Math.abs(f.peak), 1);
    if (f.state === "BUILDING")
      return off >= 0.15 ? `adding again, still ${L(f.peak - f.chg)} under its ${f.peak_at} high` : `still adding (+${L(f.chg)})`;
    if (f.state === "STALLED") return `stopped adding at ${f.peak_at}`;
    if (off >= 1) return `gave back its whole ${f.peak_at} build (now ${f.chg < 0 ? "−" : "+"}${L(Math.abs(f.chg))} vs the open)`;
    return `giving back, ${Math.round(off * 100)}% off its ${f.peak_at} high`;
  }

  // one minute's facts, read for this thesis (RULES §4), before persistence
  function raw(m, th) {
    const o = { t: m.t, spot: m.spot };
    if (m.blind) { o.blind = m.blind; return o; }
    const q = m[th.Q], r = m[th.R];
    o.q = q; o.r = r;
    o.both = !!(q && r && q.state === "UNWINDING" && r.state === "UNWINDING");
    o.qPays = !o.both && !!q && q.state === "UNWINDING";
    o.qFold = o.both ? null : (m.folds || []).filter((f) => f.side === th.Q).slice(-1)[0] || null;
    o.qBuild = !!q && q.state === "BUILDING" && q.built;
    o.rHold = !!r && r.state === "BUILDING" && r.built;
    o.rUnw = !o.both && !!r && r.state === "UNWINDING";
    o.rFold = o.both ? null : (m.folds || []).filter((f) => f.side === th.R && f.still).slice(-1)[0] || null;
    if (m.cvd) {
      const c = m.cvd, sg = Math.sign(c.d), strong = c.rank >= STRONG;
      const div = th.buyer ? (th.d > 0 ? c.dt : c.db) : null;
      o.cvd = c; o.div = div || null;
      o.cvdPays = strong && sg === th.d && !div;
      o.cvdAgainst = (strong && sg === -th.d) || !!div;
    } else o.cvdWhy = m.cvd_why;
    const fl = m.flow;
    if (fl && !(fl.rw && !fl.b && !fl.s)) {
      const nd = th.d > 0 ? fl.b : fl.s, no = th.d > 0 ? fl.s : fl.b;
      o.flow = fl; o.flowPays = dom(nd, no); o.flowAgainst = dom(no, nd);
    } else o.flowWhy = fl ? `fill runs could not be read — ${fl.rw}` : m.flow_why;
    o.pays = o.qPays || !!o.qFold || !!o.cvdPays || !!o.flowPays;
    return o;
  }

  function held(rs, i, key) {
    for (let j = i; j > i - PERSIST; j--) if (j < 0 || !rs[j] || rs[j].blind || !rs[j][key]) return false;
    return true;
  }

  function sideName(s) { return s === "CE" ? "call writers" : "put writers"; }

  // PROPOSAL 9.4 (post-data, NOT registered): Fable's STRUCTURE line, ported rule for
  // rule from docs/hold/fable/hold.js -- the last confirmed 5-min swing beyond the
  // index at entry (else the session extreme), trailing one way, broken by a 1-min
  // index close beyond it, buffer 0. Off unless trade.variants.structure.
  function structureLine(day, th, e, to) {
    const M = day.minutes, bear = th.d < 0, kind = bear ? "H" : "L", P = day.pivots || [];
    if (!M[e] || !M[e].ix) return null;
    const far = (p, c) => (bear ? p > c : p < c), side = bear ? "high" : "low";
    const known = P.filter((p) => p.kind === kind && mm(p.confirm) <= mm(M[e].t) && far(p.price, M[e].ix[0]))
                   .sort((a, b) => mm(b.bar) - mm(a.bar));
    let L, src; const used = new Set();
    if (known.length) { L = known[0].price; src = `5m swing ${side} ${known[0].bar}`; used.add(known[0].bar); }
    else { const seen = M.slice(0, e + 1).filter((m) => m.ix); L = bear ? Math.max(...seen.map((m) => m.ix[1])) : Math.min(...seen.map((m) => m.ix[2]));
           src = `session ${side} so far, no 5m swing ${bear ? "above" : "below"} yet`; }
    const out = {}; let broken = null;
    for (let i = e; i <= to; i++) {
      const m = M[i];
      if (!m.ix) { out[i] = { L, src, broken, why: "could not check — no index candle this minute" }; continue; }
      if (i > e) {
        for (const p of P) {
          if (p.kind !== kind || mm(p.confirm) !== mm(m.t) - 1 || used.has(p.bar)) continue;
          used.add(p.bar);
          const prev = M[i - 1].ix ? M[i - 1].ix[0] : m.ix[0];
          if ((bear ? p.price < L : p.price > L) && far(p.price, prev)) { L = p.price; src = `5m swing ${side} ${p.bar}`; }
        }
        if (!broken && (bear ? m.ix[0] > L : m.ix[0] < L)) broken = m.t;
      }
      out[i] = { L, src, broken, room: Math.round(bear ? L - m.ix[0] : m.ix[0] - L), px: m.ix[0], bear };
    }
    return out;
  }

  // the whole replay for one trade: reads from the entry minute to `to`
  function replay(trade, day) {
    const th = thesis(trade.side, trade.role);
    const M = day.minutes, idx0 = mm(M[0].t);
    const at = (t) => mm(t) - idx0;
    const e = Math.max(0, at(trade.read_from)), to = Math.min(M.length - 1, at(trade.read_to));
    const rs = M.map((m) => raw(m, th));
    const prem = (day.prem || {})[`${trade.k}${trade.side}`] || null;
    const V = trade.variants || {};
    const SL = V.structure ? structureLine(day, th, e, to) : null;
    const out = [];
    let latch = null, readable = [];
    for (let i = e; i <= to; i++) {
      const x = rs[i], m = M[i];
      const v = { t: m.t, spot: m.spot, th, facts: x, for: [], against: [], watch: null, struct: SL ? SL[i] : null };
      if (SL && SL[i] && SL[i].broken && !latch) {
        const b = SL[i];
        latch = { t: m.t, kind: "structure", line: `Structure broken: ${day.idx} closed ${Math.round(M[at(b.broken)].ix[0]).toLocaleString("en-IN")} ${b.bear ? "above" : "below"} your line ${Math.round(b.L).toLocaleString("en-IN")} (${b.src}) (${b.broken})` };
      }
      // premium context [M] REST or [I] chain record; never an input to the verdict
      if (prem && prem.c[i] != null) {
        const c = prem.c[i], o = prem.o[i], sg = th.buyer ? 1 : -1;
        v.prem = { c, o, vw: prem.vw[i], sd: prem.sd[i], src: prem.src,
                   z: prem.sd[i] ? (c - prem.vw[i]) / prem.sd[i] : null,
                   pnl: (c - trade.p0) * trade.qty * sg, pct: (c / trade.p0 - 1) * 100,
                   adverse: sg * (c - trade.p0) < 0 || sg * (c - o) < 0 };
      } else v.prem = { why: prem ? "no print for this contract in this minute" : "could not check — this contract is not in the record" };
      v.tr = m.tr; v.trWhy = m.tr_why;
      if (x.blind) {
        v.word = latch ? "FOLD" : "PATA NAHI"; v.kind = latch ? latch.kind : "blind"; v.line = latch ? latch.line : x.blind;
        v.blind = x.blind; v.latch = latch; out.push(v); continue;
      }
      readable.push(i);
      const qA = held(rs, i, "qBuild"), rA = held(rs, i, "rUnw");
      // for / against, in words (the face prints these; a count, never odds)
      if (x.qPays) v.for.push(`${sideName(th.Q)} paying: ${th.Q} ${K(x.q.k)} ${frontWords(x.q)}`);
      if (x.qFold) v.for.push(`${th.Q} ${K(x.qFold.k)} folded ${x.qFold.t}`);
      if (x.rHold) v.for.push(`${sideName(th.R)} holding: ${th.R} ${K(x.r.k)} ${frontWords(x.r)}`);
      if (x.cvdPays) v.for.push(`CVD ${x.cvd.d > 0 ? "+" : ""}${x.cvd.d} since ${x.cvd.since}, your way (rank ${x.cvd.rank.toFixed(2)})`);
      if (x.flowPays) v.for.push(`prints your way: ${x.flow.s} sell / ${x.flow.b} buy`);
      if (x.rFold && V.ceiling && x.rHold) v.for.push(`${th.R} ${K(x.rFold.k)} folded ${x.rFold.t}, but ${th.R} ${K(x.r.k)} is still being written — the wall moved (proposal 9.5)`);
      else if (x.rFold) v.against.push(`${th.R} ${K(x.rFold.k)} folded ${x.rFold.t} — the ${sideName(th.R)} holding your trade left`);
      if (qA) v.against.push(`${th.Q} ${K(x.q.k)} ${frontWords(x.q)} — writers adding in its way`);
      if (rA) v.against.push(`${th.R} ${K(x.r.k)} ${frontWords(x.r)} — the side holding your trade is leaving`);
      if (x.cvdAgainst) v.against.push(x.div ? `divergence: ${x.div}` : `CVD ${x.cvd.d > 0 ? "+" : ""}${x.cvd.d} since ${x.cvd.since}, against you (rank ${x.cvd.rank.toFixed(2)})`);
      if (x.flowAgainst) v.against.push(`prints against you: ${x.flow.s} sell / ${x.flow.b} buy`);
      if (x.both) v.note = "both sides' writers leaving — OI cannot say which way; order flow decides";
      // paid-last clock (buyers), over readable minutes since entry only (RULES 9.2)
      const lastPaid = [...readable].reverse().find((j) => rs[j].pays);
      v.paidLast = lastPaid != null ? M[lastPaid].t : null;
      const quiet = readable.length >= REASON_GONE && readable.slice(-REASON_GONE).every((j) => !rs[j].pays);
      v.quietFor = lastPaid != null ? readable.filter((j) => j > lastPaid).length : readable.length;
      // RULES §5, in order
      // PROPOSAL 9.5 (post-data, NOT registered; RULES 9.3 candidate i): an R-fold is the
      // ceiling MOVING, not vanishing, while the nearer R front still reads BUILDING
      const rF = x.rFold && !(V.ceiling && x.rHold) ? x.rFold : null;
      const A = rF && (qA || x.cvdAgainst || x.flowAgainst);
      const B = qA && rA;
      v.flags = { qA, rA, A: !!A, B: !!B, quiet, rF: !!rF };
      let word, kind, line;
      if (latch) {
        word = "FOLD"; kind = latch.kind;
        const healed = latch.kind === "broken" ? !(A || B) : latch.kind === "gone" ? x.pays : false;
        line = latch.line + (healed ? ` · the break has healed since — a re-entry is a new trade` : "");
      } else if (V.merged && (A || B) && !(x.cvdAgainst || x.flowAgainst)) {
        // PROPOSAL 9.6 (post-data, in-sample, NOT registered): positioning alone no longer
        // folds; it needs the tape (CVD or prints) against too, or the structure line (9.4)
        word = "WATCH"; kind = "watch";
        v.watch = `positioning says broken; FOLD when CVD or prints turn against you, or the line breaks`;
        line = `Watch, not an exit: ${v.against[0]}`;
      } else if (A || B) {
        word = "FOLD"; kind = "broken";
        line = A ? `Thesis broken: ${th.R} ${K(rF.k)} folded ${rF.t}, and ${qA ? `${th.Q} writers are adding in its way` : x.cvdAgainst ? (x.div ? "the move is not being paid for (CVD divergence)" : "CVD turned against you") : "the prints turned against you"}`
                 : `Thesis broken: positioning flipped — ${th.Q} writers adding, ${th.R} writers leaving`;
      } else if (th.buyer && quiet) {
        word = "FOLD"; kind = "gone";
        line = `Reason gone: nothing has paid for this trade in ${REASON_GONE} min — nobody forced, nobody pressing your way`;
      } else if (rF || qA || rA || (x.cvdAgainst && x.flowAgainst)) {
        // a lone CVD or a lone print count is listed against, but is not WATCH (RULES 5.5)
        word = "WATCH"; kind = "watch";
        v.watch = rF ? `FOLD if ${th.Q} writers add, or CVD / prints turn against you` :
                  qA ? `FOLD if the ${sideName(th.R)} start leaving or fold` :
                  rA ? `FOLD if the ${sideName(th.Q)} start adding` :
                  `order flow alone never folds a trade — it needs an OI fact`;
        line = `Watch, not an exit: ${v.against[0]}`;
      } else {
        word = "HOLD"; kind = "hold";
        if (!v.for.length) {
          // RULES 9.3: never call it noise when no fact is holding the trade
          v.tag = "nothing paying";
          line = th.buyer ? `Nothing is paying and nothing is against you — ${v.quietFor} quiet min of ${REASON_GONE}`
                          : "Nothing against you — time is paying the writer";
        } else if (v.prem.adverse) {
          v.tag = "noise"; word = "HOLD · NOISE";
          line = "Noise — what holds this trade has not changed: " + v.for.slice(0, 2).join(" · ");
        } else line = "Reason intact: " + v.for.slice(0, 2).join(" · ");
      }
      if (word === "FOLD" && !latch) latch = { t: m.t, kind, line: `${line} (${m.t})` };
      Object.assign(v, { word, kind, line, latch });
      out.push(v);
    }
    return out;
  }

  const api = { thesis, replay, frontWords, sideName, K, mm, hm, structureLine, PERSIST, RECENT, REASON_GONE };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.HF = api;
})(typeof window !== "undefined" ? window : globalThis);
