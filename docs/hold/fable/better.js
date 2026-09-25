/* better.js — the BETTER TRADE read. BETTER-RULES.md is the spec; this is its code.
   Inputs: the day records in data.js (board's oi_read / regime / aggression, nearer fronts,
   folds, the zone setup, the calls log) and, optionally, her trade. Output: five plain
   answers per finished minute — day, side, index, the engine's trade, second-best — and the
   wrong-trade comparison. Advisory. No order, no size, no probability; counts are counts. */
(function (root) {
  const mm = t => +t.slice(0, 2) * 60 + +t.slice(3, 5);
  const fmt = x => x == null ? '?' : Math.round(x).toLocaleString('en-IN');
  const IDX = ['NIFTY', 'BANKNIFTY', 'SENSEX'];
  const CC = 'could not check — ';

  // §2 DAY, one index-minute
  // opts.variant (BETTER-RULES §10 B, post-data, UNREGISTERED): the DAY word comes from the price half
  // alone (5m·15m·1h all one way = BUYING; CHOP = SELLING; MIXED = UNDECIDED); the OI half is a counted fact in sideRead.
  function dayRead(rec, opts) {
    opts = opts || {};
    if (!rec) return { day: 'could not check', why: CC + 'no record for this minute' };
    const rg = rec.regime || {}, oi = rec.oi_read || ['NOT READ', 'fronts not read'];
    if (rec.marks != null && rec.marks < 15) return { day: 'could not check', why: CC + `fronts forming: the build → stall → unwind sequence needs 15 one-minute marks, ${rec.marks} so far` };
    if (oi[0] === 'NOT READ') return { day: 'could not check', why: CC + (rec.fronts_why || oi[1]) };
    if (!rg.word) return { day: 'FORMING', why: CC + (rg.why || 'a middle row is still forming') };
    if (opts.variant) {
      const p = rg.price ? rg.price[0] : 'FORMING';
      if (p === 'FORMING') return { day: 'FORMING', why: CC + rg.price[1] };
      if (p === 'TREND UP' || p === 'TREND DOWN') return { day: 'BUYING', dir: p.endsWith('UP') ? 1 : -1, why: `the price rows agree — ${rg.price[1]}; OI: ${oi[0]} — ${oi[1]} [variant B]` };
      if (p === 'CHOP') return { day: 'SELLING', why: `the rows read range — ${rg.price[1]}; OI: ${oi[0]} — ${oi[1]} [variant B]` };
      return { day: 'UNDECIDED', why: `${rg.price[1]}; OI: ${oi[0]} — ${oi[1]} [variant B]` };
    }
    if (rg.word === 'TREND UP' || rg.word === 'TREND DOWN')
      return { day: 'BUYING', dir: rg.word.endsWith('UP') ? 1 : -1, why: `one side's writers have stopped and the price rows agree — a move is being paid for: ${rg.oi[1]}; ${rg.price[1]}` };
    if (rg.word === 'PIN / CHOP')
      return { day: 'SELLING', why: `both sides are writing and the rows read range — the writers are being paid by time: ${rg.oi[1]}; ${rg.price[1]}` };
    return { day: 'UNDECIDED', why: `price says ${rg.price[0]} (${rg.price[1]}), OI says ${rg.oi[0]} (${rg.oi[1]})` };
  }

  const foldIn15 = (rec, s) => (rec.folds || []).filter(f => f.side === s && mm(rec.t) - mm(f.t) >= 0 && mm(rec.t) - mm(f.t) <= 15).slice(-1)[0] || null;
  const rows = rec => ['5m', '15m', '1h'].map(k => rec.trend[k]);

  // §3 SIDE
  function sideRead(rec, D, opts) {
    opts = opts || {};
    const near = rec.near || {}, ag = rec.aggr || {};
    const oi = rec.oi_read || ['NOT READ', ''];
    const agFact = ag.word ? `${ag.word} ${ag.dir > 0 ? 'up' : 'down'} — ${ag.fact}` : (ag.fact ? `none — ${ag.fact}` : (ag.why || CC + 'no ladder'));
    const agBlind = !ag.word && !ag.fact;
    if (D.day === 'BUYING') {
      const d = D.dir, side = d > 0 ? 'CE' : 'PE', payers = side, holders = d > 0 ? 'PE' : 'CE';
      const P = near[payers], H = near[holders], pf = foldIn15(rec, payers);
      const v = rows(rec);
      const facts = [
        { ok: P ? (P.state === 'UNWINDING' || !!pf) : null, fact: P ? `payers ${payers} ${fmt(P.k)} ${P.state.toLowerCase()}${pf ? ` · ${payers} ${fmt(pf.k)} folded ${pf.t}` : ''}` : CC + 'payers not read', tag: 'M' },
        { ok: H ? H.state === 'BUILDING' : null, fact: H ? `holders ${holders} ${fmt(H.k)} ${H.state.toLowerCase()}` : CC + 'holders not read', tag: 'M' },
        { ok: agBlind ? null : (!!ag.word && ag.dir === d), fact: 'aggression ' + agFact, tag: 'I' },
        { ok: v.includes(null) ? null : v.every(x => x === d), fact: `rows ${['5m', '15m', '1h'].map((k, i) => k + ' ' + ({ 1: 'UP', '-1': 'DOWN', 0: 'RANGE' }[v[i]] || 'forming')).join(' · ')}`, tag: 'I' },
      ];
      if (opts.variant) facts.push({ ok: oi[0] === 'NOT READ' ? null : oi[0] === (d > 0 ? 'TREND UP' : 'TREND DOWN'), fact: `OI half ${oi[0]} — ${oi[1]}`, tag: 'M' });
      return { side, role: 'buy', n: facts.filter(f => f.ok === true).length, of: facts.length, blind: facts.filter(f => f.ok === null).length, facts };
    }
    if (D.day === 'SELLING') {
      const C = near.CE, P = near.PE, dpx = (rec.facts && rec.facts.cvd) ? rec.facts.cvd.dpx : null;
      const ok = (f, toward) => !!f && f.state === 'BUILDING' && (dpx == null || !toward(dpx));
      const ceOk = ok(C, x => x > 0), peOk = ok(P, x => x < 0);
      let side = null, whyNo = null;
      if (ceOk && peOk) side = (C.chg >= P.chg) ? 'CE' : 'PE';
      else if (ceOk) side = 'CE'; else if (peOk) side = 'PE';
      else whyNo = (!C || !P) ? CC + 'a nearer front is not read' : (C.state !== 'BUILDING' && P.state !== 'BUILDING') ? 'neither side is writing' : 'price is pressing toward the only side that is writing';
      const v = rows(rec);
      const facts = [
        { ok: (C && P) ? (C.state === 'BUILDING' && P.state === 'BUILDING') : null, fact: (C && P) ? `CE ${fmt(C.k)} ${C.state.toLowerCase()} · PE ${fmt(P.k)} ${P.state.toLowerCase()}` : CC + 'fronts not read', tag: 'M' },
        { ok: agBlind ? null : !ag.word, fact: 'aggression ' + agFact, tag: 'I' },
        { ok: v.includes(null) ? null : v.filter(x => x === 0).length >= 2, fact: `rows ${['5m', '15m', '1h'].map((k, i) => k + ' ' + ({ 1: 'UP', '-1': 'DOWN', 0: 'RANGE' }[v[i]] || 'forming')).join(' · ')}`, tag: 'I' },
      ];
      if (opts.variant) facts.push({ ok: oi[0] === 'NOT READ' ? null : oi[0] === 'PIN', fact: `OI half ${oi[0]} — ${oi[1]}`, tag: 'M' });
      return { side, role: 'sell', whyNo, n: facts.filter(f => f.ok === true).length, of: facts.length, blind: facts.filter(f => f.ok === null).length, facts,
               dpx: dpx == null ? null : Math.round(dpx) };
    }
    return { side: null, role: null, n: 0, of: 0, blind: 0, facts: [], whyNo: D.day === 'UNDECIDED' ? 'no side until the day decides — a PIN from OI, or the middle rows turning one way' : D.why };
  }

  // §5 the engine's trade
  function engineRead(rec) {
    const c = rec.calls;
    if (c && c.calls && c.calls.length) {
      const list = [...c.calls].sort((a, b) => (a.source === 'verdict' ? -1 : 0) - (b.source === 'verdict' ? -1 : 0));
      const v = list[0];
      const word = { BACKED: 'a good call — OI and flow agree, nothing contradicts', THIN: 'thin — one family for, none against', CONTRADICTED: 'contradicted — the tape says the opposite', 'PATA NAHI': 'could not be grounded' }[v.status] || v.status;
      const against = ['oi', 'cvd', 'flow'].filter(k => v[k] && v[k].state === 'against').map(k => `${k.toUpperCase()}: ${v[k].fact}`);
      const forr = ['oi', 'cvd', 'flow'].filter(k => v[k] && v[k].state === 'for').map(k => `${k.toUpperCase()}: ${v[k].fact}`);
      return { src: 'calls', t: c.t, text: v.text, status: v.status, word, against, for: forr, n: list.length, tag: 'I' };
    }
    if (c && c.why && !rec.setup) return { src: 'none', why: c.why };
    const s = rec.setup || {};
    if (s.why && !s.side) return { src: 'setup', why: s.why + (c && c.why ? ` · ${c.why}` : ''), t: s.t };
    const word = { BACKED: 'a good call — OI and flow agree, nothing contradicts', THIN: 'thin — one family for, none against', CONTRADICTED: 'contradicted — the tape says the opposite', 'PATA NAHI': 'could not be grounded' }[s.status] || s.status;
    const fam = s.fam || {};
    return { src: 'setup', t: s.t, text: `zone ${String(s.side).toUpperCase()} ${s.state}${s.level != null ? ' at ' + fmt(s.level) : ''}${s.visit ? ' · ' + s.visit : ''}`, status: s.status, word,
             against: ['oi', 'cvd', 'flow'].filter(k => fam[k] && fam[k].state === 'against').map(k => `${k.toUpperCase()}: ${fam[k].fact}`),
             for: ['oi', 'cvd', 'flow'].filter(k => fam[k] && fam[k].state === 'for').map(k => `${k.toUpperCase()}: ${fam[k].fact}`), tag: 'I',
             note: c && c.why ? c.why : null };
  }

  // §4 INDEX ranking + §6 wrong trade, at minute t across the three indices
  function read(days, day, t, trade, opts) {
    opts = opts || {};
    const per = {};
    for (const idx of IDX) {
      const D = days[`${idx}|${day}`];
      const rec = D ? D.minutes.find(m => m.t === t) : null;
      const dr = D ? dayRead(rec, opts) : { day: 'could not check', why: CC + `no record for ${idx} on ${day}` };
      const sr = rec ? sideRead(rec, dr, opts) : { side: null, n: 0, of: 0, blind: 3, facts: [], whyNo: dr.why };
      const en = rec ? engineRead(rec) : { src: 'none', why: CC + `no record for ${idx} on ${day}` };
      per[idx] = { idx, day: dr, side: sr, engine: en, rec, since: since(D, t, dr.day, opts),
                   notShown: idx === 'BANKNIFTY' ? 'not showing you — BANKNIFTY option premiums are not in this record; the read is on the index and its chain' : null };
    }
    const decided = x => x.day.day === 'BUYING' || x.day.day === 'SELLING';
    const tier = x => decided(x) ? 2 : x.day.day === 'UNDECIDED' ? 1 : 0;
    const ranked = IDX.map(i => per[i]).sort((a, b) => (tier(b) - tier(a)) || ((b.side.n || 0) - (a.side.n || 0)) || ((a.side.blind || 0) - (b.side.blind || 0)) ||
      ((trade && b.idx === trade.idx) - (trade && a.idx === trade.idx)) || IDX.indexOf(a.idx) - IDX.indexOf(b.idx));
    ranked.forEach((x, i) => { x.rank = i + 1; });
    const named = x => decided(x) && x.side.side ? `${x.idx} ${x.side.side} ${x.side.role} · ${x.side.n} of ${x.side.of} facts` : null;
    const best = ranked.find(named), second = ranked.filter(x => x !== best).find(named);
    const out = { t, per, ranked, variant: !!opts.variant, best: best ? named(best) : 'checked, none — no index has a decided day with a side', second: second ? named(second) : (best ? 'checked, none — the other two read UNDECIDED / forming / no side' : null) };
    if (trade) {
      const me = per[trade.idx];
      const roleOk = me.day.day === 'BUYING' ? (trade.role === 'buyer' ? true : false) : me.day.day === 'SELLING' ? (trade.role === 'writer' ? true : false) : null;
      const sideOk = me.side.side ? (me.side.side === trade.side) : null;
      const idxOk = me.rank === 1 ? true : me.rank === 2 ? 'second' : false;
      const n = [roleOk, sideOk, idxOk].filter(x => x === true).length;
      const mark = x => x === true ? '✓' : x === false ? '✗' : x === 'second' ? 'second' : '?';
      let head;
      if (me.day.day === 'UNDECIDED' || !decided(me)) head = `no read yet for ${trade.idx} — ${me.day.day === 'UNDECIDED' ? 'the day has not decided' : me.day.why}; your trade is neither confirmed nor refused`;
      else if (n <= 1) head = best ? `WRONG TRADE for today's read — the read says ${out.best}`
                                   : `WRONG TRADE for today's read — a ${trade.role === 'buyer' ? 'buyer' : 'writer'} on a ${me.day.day} read; the read names no side yet (${me.side.whyNo || 'no side'})`;
      else head = `your trade agrees with the read (${n} of 3)`;
      out.mine = { head, n, marks: `day ${mark(roleOk)} · side ${mark(sideOk)} · index ${mark(idxOk)}`, roleOk, sideOk, idxOk };
    }
    return out;
  }

  // how long the DAY word has stood, causal
  function since(D, t, word, opts) {
    if (!D) return null;
    let s = t;
    for (let i = D.minutes.length - 1; i >= 0; i--) {
      const m = D.minutes[i];
      if (mm(m.t) > mm(t)) continue;
      if (dayRead(m, opts).day !== word) break;
      s = m.t;
    }
    return s;
  }

  root.BETTER = { read, dayRead, sideRead, engineRead, IDX, mm };
})(typeof module !== 'undefined' ? module.exports : window);
