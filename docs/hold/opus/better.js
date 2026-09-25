/* better.js -- BETTER-RULES.md, written once. DRAFT, not registered.
 *
 * Pure: (the three indices' per-minute facts for one day, a finished minute,
 * optionally her trade) -> the better-trade read. Every input is TapeMap's own
 * (trendbox REGIME / STRONG, §1d fronts and folds, grounds' CVD and prints, the
 * contract VWAP bands, the zone rows and the calls log), cut to the minute by
 * scratch/build_facts.py. It counts facts; it never scores, sizes or prices.
 */
(function (root) {
  "use strict";
  const PERSIST = 3, RECENT = 15, STRONG = 0.5, ONE_SIDED = 0.8;
  const IDX = ["NIFTY", "BANKNIFTY", "SENSEX"];
  const mm = (t) => +t.slice(0, 2) * 60 + +t.slice(3, 5);
  const K = (k) => Number(k).toLocaleString("en-IN");
  const DAYW = { "TREND UP": "BUY_UP", "TREND DOWN": "BUY_DOWN", "PIN / CHOP": "SELL" };
  const WORDS = { BUY_UP: "BUYING day — calls", BUY_DOWN: "BUYING day — puts", SELL: "SELLING day", NEITHER: "NEITHER is clean" };

  // PROPOSAL B-11.1 (post-data, NOT registered): the day word from REGIME's PRICE half
  // (5m/15m/1h), with the OI half counted as a fact instead of gating. See BETTER-RULES §11.
  const PRICE = { "TREND UP": "TREND UP", "TREND DOWN": "TREND DOWN", CHOP: "PIN / CHOP" };
  function stableAt(M, i, V) {
    // the REGIME word shown: the latest one that held PERSIST finished minutes (RULES §2)
    const w = (j) => (M[j] && !M[j].blind && M[j].reg ? (V && V.price ? PRICE[M[j].reg[1]] || "NOT AGREED" : M[j].reg[0]) : null);
    for (let j = i; j >= PERSIST - 1; j--) {
      const a = w(j);
      if (a && w(j - 1) === a && w(j - 2) === a) return { word: a, since: M[j - 2].t, changing: w(i) && w(i) !== a ? w(i) : null };
    }
    return { word: null, since: null, changing: w(i) };
  }

  function mirror(D, i, m) {
    const k = Math.round(m.spot / D.step) * D.step, z = {};
    for (const s of ["CE", "PE"]) {
      const l = D.prem[`${k}${s}`];
      const c = l && l.c[i], vw = l && l.vw[i], sd = l && l.sd[i];
      z[s] = c != null && sd ? { z: (c - vw) / sd, c, vw, src: l.src } : null;
    }
    return { k, ...z };
  }

  function oneIndex(D, i, V) {
    const out = { idx: D.idx };
    if (!D.minutes) return { ...out, blind: D.why || `could not check — no record for ${D.idx}` };
    const m = D.minutes[i];
    if (!m) return { ...out, blind: "could not check — no minute" };
    if (m.blind) return { ...out, blind: m.blind, t: m.t };
    if (!m.reg) return { ...out, blind: m.tr_why || "could not check — the trend rows did not load", t: m.t };
    const st = stableAt(D.minutes, i, V);
    const oiw = m.reg[3];
    const day = DAYW[st.word] || "NEITHER";
    const f = [], a = [], b = [];
    const still = (m.folds || []).filter((x) => x.still);
    const mir = mirror(D, i, m);
    const c = m.cvd;
    const sw = m.strong ? m.strong[0] : null;
    const cvdTxt = c ? `CVD ${c.d > 0 ? "+" : ""}${c.d} since ${c.since} (rank ${c.rank.toFixed(2)})` : null;
    const zTxt = (s) => (mir[s] ? `ATM ${s} ${K(mir.k)} ${mir[s].z >= 0 ? "+" : ""}${mir[s].z.toFixed(1)}σ vs its own VWAP` : `ATM ${s} ${K(mir.k)}: could not check — not in the record`);
    if (day === "BUY_UP" || day === "BUY_DOWN") {
      const d = day === "BUY_UP" ? 1 : -1, pay = d > 0 ? "CE" : "PE", hold = d > 0 ? "PE" : "CE";
      // a · STRONG
      if (sw == null) b.push("STRONG: could not check");
      else if (sw === (d > 0 ? "BULLS" : "BEARS")) f.push(`STRONG = ${sw}`); else if (sw !== "NEITHER") a.push(`STRONG = ${sw}`);
      // b · folds
      const pf = still.filter((x) => x.side === pay).slice(-1)[0], hf = still.filter((x) => x.side === hold).slice(-1)[0];
      if (pf) f.push(`${pay} ${K(pf.k)} folded ${pf.t} — the side that pays is being forced`);
      if (hf) a.push(`${hold} ${K(hf.k)} folded ${hf.t} — the side holding the move left`);
      // c · CVD
      if (!c) b.push(m.cvd_why || "CVD: could not check");
      else {
        const div = d > 0 ? c.dt : c.db;
        if (div) a.push(`divergence: ${div}`);
        else if (c.rank >= STRONG && Math.sign(c.d) === d) f.push(`${cvdTxt}, with the day`);
        else if (c.rank >= STRONG && Math.sign(c.d) === -d) a.push(`${cvdTxt}, against the day`);
      }
      // d · mirror
      if (!mir.CE || !mir.PE) b.push(`the ATM mirror: could not check (${!mir.CE ? "CE" : "PE"} ${K(mir.k)} not in the record)`);
      else if (mir[pay].z > 0 && mir[hold].z < 0) f.push(`buyers paying up: ${zTxt(pay)}, ${zTxt(hold)}`);
      else if (mir[pay].z < 0 && mir[hold].z > 0) a.push(`the mirror disagrees: ${zTxt(pay)}, ${zTxt(hold)}`);
      if (V && V.price) {        // e · the OI half, counted (proposal B-11.1)
        if (oiw === (d > 0 ? "TREND UP" : "TREND DOWN")) f.push(`OI agrees: ${m.reg[4]}`);
        else if (oiw === (d > 0 ? "TREND DOWN" : "TREND UP")) a.push(`OI reads the other way: ${m.reg[4]}`);
      }
    } else if (day === "SELL") {
      if (sw == null) b.push("STRONG: could not check");
      else if (sw === "NEITHER") f.push("STRONG = NEITHER"); else a.push(`STRONG = ${sw}`);
      if (still.length) a.push(`${still.slice(-1)[0].side} ${K(still.slice(-1)[0].k)} folded ${still.slice(-1)[0].t} — someone is being forced`);
      else f.push("no fold on either side in 15 min — nobody forced");
      if (!c) b.push(m.cvd_why || "CVD: could not check");
      else if (c.rank >= ONE_SIDED) a.push(`${cvdTxt} — one side pressing`);
      else if (c.rank < STRONG) f.push(`${cvdTxt} — nobody pressing`);
      if (!mir.CE || !mir.PE) b.push(`the ATM mirror: could not check (${!mir.CE ? "CE" : "PE"} ${K(mir.k)} not in the record)`);
      else if (mir.CE.z < 0 && mir.PE.z < 0) f.push(`premium decaying on both sides: ${zTxt("CE")}, ${zTxt("PE")}`);
      else if (mir.CE.z >= 1 || mir.PE.z >= 1) a.push(`premium bid on one side: ${zTxt("CE")}, ${zTxt("PE")}`);
      if (V && V.price) {
        if (oiw === "PIN") f.push(`OI agrees: ${m.reg[4]}`);
        else if (oiw === "TREND UP" || oiw === "TREND DOWN") a.push(`OI reads a trend: ${m.reg[4]}`);
      }
    }
    const bld = (s) => !!(m[s] && m[s].state === "BUILDING" && m[s].built);
    const wall = (s) => (m[s] ? `${s} ${K(m[s].k)} (${Math.round(Math.abs(m[s].k - m.spot))} pts ${m[s].k > m.spot ? "above" : "below"})` : `${s}: not read`);
    let side;
    if (day === "BUY_UP") side = { text: "buy CE", sides: ["CE"], act: "buy" };
    else if (day === "BUY_DOWN") side = { text: "buy PE", sides: ["PE"], act: "buy" };
    else if (day === "SELL") {
      const s = ["CE", "PE"].filter(bld);
      side = s.length ? { text: s.length === 2 ? "write both sides" : `write ${s[0]}`, sides: s, act: "write", walls: s.map(wall).join(" · ") }
                      : { text: "no side is being written", sides: [], act: null };
    } else side = { text: "no side", sides: [], act: null };
    const why = st.word ? `${V && V.price ? "price rows" : "REGIME"} ${st.word}${st.changing ? ` (changing to ${st.changing})` : ""} — price: ${m.reg[1]} (${m.reg[2]}); OI: ${m.reg[3]} (${m.reg[4]})`
                        : `REGIME not yet steady for ${PERSIST} min (now ${m.reg[0]})`;
    return { ...out, t: m.t, spot: m.spot, day, word: WORDS[day], since: st.since, changing: st.changing, why, for: f, against: a, blind: null, cant: b,
             side, bld: { CE: bld("CE"), PE: bld("PE") }, walls: { CE: wall("CE"), PE: wall("PE") }, m };
  }

  function engine(D, i, R) {
    // RULES §5: the zone machine's latest arm/entry in the last RECENT min, its logged gate,
    // agreement with the day, and the engine verdict's grounding (calls log, 09-24 on)
    if (!D.minutes || !D.minutes[i]) return { text: "could not check — no record" };
    const t = D.minutes[i].t;
    const z = (D.zones || []).filter((x) => mm(x.vis) <= mm(t) && mm(t) - mm(x.vis) <= RECENT).slice(-1)[0];
    const eng = D.minutes[i].eng;
    const ver = eng ? eng.find((c) => c[0] === "verdict") || eng[0] : null;
    const g = ver ? { text: ver[1], status: ver[2], fam: `OI ${ver[3]} · CVD ${ver[4]} · FLOW ${ver[5]}`, src: "calls log" }
                  : { text: null, status: null, why: D.calls_why || "could not check — no engine call logged this minute" };
    if (!z) return { none: true, text: `checked, none — no zone arm or entry on ${D.idx} in the last ${RECENT} min`, g };
    const buy = z.side === "BUY";
    let agree = null;
    if (!R || R.blind || R.day === "NEITHER") agree = null;
    else if (R.day === (buy ? "BUY_UP" : "BUY_DOWN")) agree = true;
    else if (R.day === (buy ? "BUY_DOWN" : "BUY_UP")) agree = false;
    else if (R.day === "SELL") agree = R.bld[buy ? "PE" : "CE"] ? true : null;   // RULES §5.2 names only the agreeing case
    const status = g.status;       // RULES §5.3: the calls log only; before 09-24 it is "could not check"
    const bad = z.legal === false || agree === false || status === "CONTRADICTED";
    const good = z.legal === true && agree === true && status && status !== "CONTRADICTED";
    const call = bad ? "a bad call" : good ? "a good call" : "thin";
    const facts = [`zone ${z.side} ${z.band} ${z.kind} ${z.t}`,
                   `§1d gate ${z.legal === true ? "LEGAL" : z.legal === false ? "ILLEGAL" : "not logged"}${z.gate_why ? ` (${z.gate_why})` : ""}`,
                   agree === true ? "agrees with the day" : agree === false ? "against the day" : "the day is not clear",
                   status ? `engine verdict ${status}: ${g.text.slice(0, 60)} (${g.fam})` : g.why];
    return { z, call, facts, g, text: `${call} — ${facts.join(" · ")}` };
  }

  function rank(reads) {
    const ex = [];
    for (const r of reads) {
      if (r.blind || r.day === "NEITHER") continue;
      const base = { idx: r.idx, for: r.for.length, against: r.against.length, cant: r.cant.length, day: r.day };
      if (r.day === "SELL") { if (r.side.sides.length) ex.push({ ...base, act: "write", sides: r.side.sides, primary: true, text: `${r.idx}: ${r.side.text} — ${r.side.walls}` }); }
      else {
        const d = r.day === "BUY_UP" ? 1 : -1, s = d > 0 ? "CE" : "PE", o = d > 0 ? "PE" : "CE";
        ex.push({ ...base, act: "buy", sides: [s], primary: true, text: `${r.idx}: buy ${s}` });
        if (r.bld[o]) ex.push({ ...base, act: "write", sides: [o], primary: false, text: `${r.idx}: write ${o} — ${r.walls[o]} still being written` });
      }
    }
    ex.sort((x, y) => (x.against === 0) !== (y.against === 0) ? (x.against === 0 ? -1 : 1)
      : y.for - x.for || (x.primary === y.primary ? 0 : x.primary ? -1 : 1) || x.cant - y.cant);
    return ex;
  }

  function check(trade, r) {
    // RULES §7: her trade against her index's day word
    if (!r || r.blind) return { word: "COULD NOT CHECK", why: r ? r.blind : "no read" };
    const buyer = trade.role === "long", dT = (trade.side === "CE") === buyer ? 1 : -1;
    const own = trade.side;
    if (r.day === "NEITHER") return { word: "UNCLEAR", why: `today is not clean on ${r.idx}: ${r.why}` };
    if (r.day === "SELL") {
      if (buyer) return { word: "AGAINST", why: `${r.idx} reads a SELLING day and you are a buyer — you are paying time on a writers' day` };
      return r.bld[own] ? { word: "AGREES", why: `a SELLING day and your side's writers are holding (${r.walls[own]})` }
                        : { word: "AGAINST", why: `a SELLING day, but the ${own} writers are not holding (${r.walls[own]})` };
    }
    const d = r.day === "BUY_UP" ? 1 : -1;
    if (buyer) return dT === d ? { word: "AGREES", why: `${r.word} on ${r.idx}, and you bought ${own}` }
                               : { word: "AGAINST", why: `${r.word} on ${r.idx}, and you bought ${own} — the other side` };
    if (dT !== d) return { word: "AGAINST", why: `${r.word} on ${r.idx}, and you wrote ${own} — the side the day is running into` };
    return r.bld[own] ? { word: "AGREES", why: `${r.word} on ${r.idx}; you wrote ${own} and its writers are holding (${r.walls[own]})` }
                      : { word: "UNCLEAR", why: `${r.word} on ${r.idx}; you wrote ${own}, the right side, but its writers are not adding (${r.walls[own]})` };
  }

  // the whole read at one finished minute; `days` = {NIFTY: facts, BANKNIFTY: facts, SENSEX: facts}
  function read(days, t, trade, V) {
    const reads = IDX.map((x) => {
      const D = days[x];
      if (!D) return { idx: x, blind: `could not check — no record for ${x}` };
      if (!D.minutes) return { idx: x, blind: D.why || `could not check — no record for ${x}` };
      const i = mm(t) - mm(D.minutes[0].t);
      const r = oneIndex(D, i, V);
      r.engine = engine(D, i, r);
      return r;
    });
    const clear = reads.filter((r) => !r.blind && r.day !== "NEITHER")
      .sort((x, y) => (x.against.length === 0) !== (y.against.length === 0) ? (x.against.length === 0 ? -1 : 1)
        : y.for.length - x.for.length || x.cant.length - y.cant.length);
    let cleanest;
    if (!clear.length) cleanest = { text: "none is clean right now", idx: null };
    else {
      const top = clear[0], tie = clear.filter((r) => (r.against.length === 0) === (top.against.length === 0) && r.for.length === top.for.length && r.cant.length === top.cant.length);
      cleanest = { idx: top.idx, tie: tie.length > 1 ? tie.map((r) => r.idx) : null, clean: top.against.length === 0,
                   text: `${tie.length > 1 ? tie.map((r) => r.idx).join(" and ") + " (a tie)" : top.idx}: ${top.word}, ${top.for.length} for · ${top.against.length} against${top.against.length ? " — not clean" : ""}` };
    }
    const ex = rank(reads);
    const best = ex[0] || null, second = ex[1] || null;
    const out = { t, reads, cleanest, best, second, ranked: ex,
                  bestText: best ? `${best.text} (${best.for} for · ${best.against} against)` : "no trade is clean right now",
                  secondText: second ? `${second.text} (${second.for} for · ${second.against} against)` : best ? "no second best — only one clean expression" : "—" };
    if (trade) {
      const r = reads.find((x) => x.idx === trade.idx);
      out.check = check(trade, r);
      out.mine = r;
    }
    return out;
  }

  const api = { read, check, IDX, WORDS, PERSIST, RECENT };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.BT = api;
})(typeof window !== "undefined" ? window : globalThis);
