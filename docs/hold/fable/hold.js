/* hold.js — the HOLD / FOLD engine. RULES.md is the spec; this is its code.
   One implementation, loaded by index.html (the window) and by scratch/report.js (node).
   Inputs: a day record from data.js (built by scratch/build.py from the tool's own readers)
   and a trade. Output: one reading per finished minute from entry to the close.
   Advisory only. No order path. No probabilities. */
(function (root) {
  const mm = t => +t.slice(0, 2) * 60 + +t.slice(3, 5);
  const hm = m => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
  const fmt = x => x == null ? '—' : Math.round(x).toLocaleString('en-IN');

  // the last FINISHED minute before a fill at HH:MM:SS (the board's own rule: the forming minute is never read)
  const readMinute = ts => hm(Math.max(mm(ts) - 1, 9 * 60 + 15));

  // want: +1 the index must go up, -1 down. A writer "wants" the danger direction absent.
  const wantOf = tr => ((tr.side === 'CE') === (tr.role === 'buyer')) ? 1 : -1;

  function trendVote(rows, role, want) {
    const v = ['5m', '15m', '1h'].map(k => rows[k]);
    const forN = v.filter(x => x === want).length, agN = v.filter(x => x === -want).length, forming = v.filter(x => x == null).length;
    let state;
    if (role === 'buyer') state = (forN >= 2 && agN === 0) ? 'for' : agN >= 2 ? 'against' : 'flat';
    else state = agN >= 2 ? 'against' : (agN === 0 && forming === 0) ? 'for' : 'flat';
    const w = { 1: 'UP', '-1': 'DOWN', 0: 'RANGE' };
    const txt = ['5m', '15m', '1h'].map(k => k + ' ' + (rows[k] == null ? 'forming' : w[rows[k]])).join(' · ');
    return { state, forN, agN, fact: txt, tag: 'I' };
  }

  function mergeFlow(cvd, flow) {
    const s = [cvd.state, flow.state];
    const state = s.includes('against') ? 'against' : s.includes('for') ? 'for' : s.every(x => x === 'blind') ? 'blind' : 'flat';
    return { state, fact: [cvd, flow].map(f => f.fact).filter(Boolean).join(' · '), tag: 'I', cvd, flow };
  }

  // STRUCTURE: L at entry, one-way trail, 1-min close break, latch. RULES.md §2.1.
  function structure(day, trade, entryMin) {
    const want = wantOf(trade);
    const bear = want < 0;
    const mins = day.minutes, at = Object.fromEntries(mins.map((m, i) => [m.t, i]));
    const e = at[entryMin];
    if (e == null) return null;
    const px = mins[e].px;
    const known = p => p.kind === (bear ? 'H' : 'L') && mm(p.confirm) <= mm(entryMin);
    const far = (p, c) => bear ? p.price > c : p.price < c;
    const cands = day.pivots.filter(p => known(p) && far(p, px)).sort((a, b) => mm(b.bar) - mm(a.bar));
    let L, src, bar;
    if (cands.length) { L = cands[0].price; bar = cands[0].bar; src = `5m swing ${bear ? 'high' : 'low'} ${bar}`; }
    else {
      const seen = mins.slice(0, e + 1);
      L = bear ? Math.max(...seen.map(m => m.hi)) : Math.min(...seen.map(m => m.lo));
      bar = null; src = `session ${bear ? 'high' : 'low'} so far, no 5m swing ${bear ? 'above' : 'below'} you yet`;
    }
    const out = {}, used = new Set(cands.length ? [cands[0].bar] : []);
    let broken = null;
    for (let i = e; i < mins.length; i++) {
      const m = mins[i];
      if (i > e) {
        // pivots that confirmed at the previous finished minute: trail one way
        for (const p of day.pivots) {
          if (p.kind !== (bear ? 'H' : 'L') || mm(p.confirm) !== mm(m.t) - 1 || used.has(p.bar)) continue;
          used.add(p.bar);
          const prev = mins[i - 1].px;
          const nearer = bear ? p.price < L : p.price > L;
          if (nearer && far(p, prev)) { L = p.price; bar = p.bar; src = `5m swing ${bear ? 'high' : 'low'} ${bar}`; }
        }
        if (!broken && (bear ? m.px > L : m.px < L)) broken = m.t;
      }
      out[m.t] = { L, src, broken: !!broken, brokeAt: broken, dist: Math.round(bear ? L - m.px : m.px - L), px: m.px };
    }
    return out;
  }

  const WORD = {
    fuel: { buyer: { for: 'burning', against: 'out', flat: 'unclear', blind: 'could not check' },
            writer: { for: 'holding', against: 'running', flat: 'unclear', blind: 'could not check' } },
    flow: { for: 'with you', against: 'against you', flat: 'quiet', blind: 'could not check' },
  };

  // opts.variant: RULES.md §10 A + F, post-data proposals, UNREGISTERED, off by default.
  //   A. a wall-side fold within 2 strike-steps of spot in the last 15 min, with no payers' fold nearer, reads FUEL = AGAINST for a buyer
  //   F. FUEL is blind while the OI grid holds fewer than 15 one-minute marks (fronts.SLOPE_MARKS)
  function read(day, trade, opts) {
    opts = opts || {};
    const want = wantOf(trade), role = trade.role, key = role + (want > 0 ? '+' : '-');
    let marks = 0;
    const entryMin = readMinute(trade.entry_ts);
    const exitMin = trade.exit_ts ? readMinute(trade.exit_ts) : null;
    const S = structure(day, trade, entryMin);
    if (!S) return { error: `no finished index minute at ${entryMin}` };
    const pxs = day.px[`${trade.strike}${trade.side}`] || null;
    const idxName = { NIFTY: 'NIFTY', SENSEX: 'SENSEX', BANKNIFTY: 'BANKNIFTY' }[day.idx];
    const rows = [];
    let fold = null;
    for (const m of day.minutes) {
      if (m.spot != null) marks++;
      if (mm(m.t) < mm(entryMin)) continue;
      const st = S[m.t];
      const fam = m.fam[key];
      const fuel = { ...fam.oi, word: WORD.fuel[role][fam.oi.state] };
      if (opts.variant) {
        if (marks < 15) {
          fuel.state = 'blind'; fuel.word = 'could not check';
          fuel.fact = `could not check — fronts forming: the build → stall → unwind sequence needs 15 one-minute marks, ${marks} so far [variant F]`;
        } else if (role === 'buyer' && m.spot != null) {
          const step = day.idx === 'NIFTY' ? 50 : 100, wall = want > 0 ? 'PE' : 'CE', payers = want > 0 ? 'CE' : 'PE';
          const recent = (m.folds || []).filter(f => mm(m.t) - mm(f.t) >= 0 && mm(m.t) - mm(f.t) <= 15);
          const near = f => Math.abs(f.k - m.spot);
          const wf = recent.filter(f => f.side === wall && near(f) <= 2 * step).sort((a, b) => near(a) - near(b))[0];
          const pf = recent.filter(f => f.side === payers).sort((a, b) => near(a) - near(b))[0];
          if (wf && !(pf && near(pf) < near(wf))) {
            fuel.state = 'against'; fuel.word = 'out';
            fuel.fact = `wall folded at spot — winners cashing in: ${wall} ${fmt(wf.k)} folded ${wf.t}, ${Math.round(near(wf))} pts from spot [variant A, unregistered]`;
          }
        }
      }
      const flow = { ...mergeFlow(fam.cvd, fam.flow) }; flow.word = WORD.flow[flow.state];
      const trend = trendVote(m.trend, role, want);
      trend.word = trend.state === 'for' ? `${trend.forN} of 3 with you` : trend.state === 'against' ? `${trend.agN} of 3 against you` : (trend.fact.includes('forming') ? 'forming' : 'mixed');
      const soft = [['fuel', fuel], ['flow', flow], ['trend', trend]];
      const against = soft.filter(([, f]) => f.state === 'against');
      let verdict, why;
      if (st.broken) {
        verdict = 'FOLD';
        why = `${idxName} closed ${fmt(m.px)} ${want < 0 ? 'above' : 'below'} your line ${fmt(st.L)} (${st.src})`;
      } else if (against.length >= 2) {
        verdict = 'FOLD';
        why = against.map(([n, f]) => `${n} against you: ${f.fact}`).join(' — ');
      } else if (against.length === 1) {
        verdict = 'WATCH';
        why = `${against[0][0]} against you: ${against[0][1].fact}`;
      } else {
        verdict = 'HOLD';
        why = `line ${fmt(st.L)} holds (${fmt(st.dist)} pts of room) · fuel ${fuel.word} · flow ${flow.word} · trend ${trend.word}`;
      }
      if (verdict === 'FOLD' && !fold) fold = { t: m.t, why };
      if (fold) { verdict = 'FOLD'; }           // latched for the trade
      const prem = pxs ? pxs[m.t] : null;
      const premWhy = !pxs ? (day.px_why || `no premium record for ${trade.strike}${trade.side}`) : prem == null ? 'strike outside the chain window at this minute' : null;
      const pnl = prem == null || trade.entry == null ? null : (prem - trade.entry) * trade.qty * (role === 'buyer' ? 1 : -1);
      rows.push({ t: m.t, verdict, since: fold ? fold.t : null, foldWhy: fold ? fold.why : null, why,
                  structure: { state: st.broken ? 'broken' : 'intact', ...st, tag: 'M' },
                  fuel, flow, trend, prem, premWhy, pnl, spot: m.px, isEntry: m.t === entryMin, isExit: m.t === exitMin });
    }
    return { trade, want, role, entryMin, exitMin, rows, fold, variant: !!opts.variant };
  }

  root.HOLD = { read, readMinute, wantOf, fmt, mm, hm };
})(typeof module !== 'undefined' ? module.exports : window);
