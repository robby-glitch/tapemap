// node scratch/side_report.js -> THE SIDE READ (PREREG-merged.md §10) at every minute and at her entries. Description only.
const fs = require('fs'), path = require('path');
const here = path.join(__dirname, '..');
global.window = {};
new Function(fs.readFileSync(path.join(here, 'data.js'), 'utf8'))();
const H = require(path.join(here, 'hold.js')).HOLD;
const D = global.window.HOLD_DATA;
const mm = H.mm;
// expiry per index-day [M from the tradebook's expiry_date for NIFTY 09-22 and SENSEX 09-24; I: BANKNIFTY monthly = last Thursday, 09-24]
const EXPIRY = { 'NIFTY|2026-09-22': 'M', 'SENSEX|2026-09-24': 'M', 'BANKNIFTY|2026-09-24': 'I' };
const IDX = ['NIFTY', 'BANKNIFTY', 'SENSEX'];

function sideRead(rec, key) {
  if (!rec) return { side: 'could not check', why: 'no record' };
  const v = ['5m', '15m', '1h'].map(k => rec.trend[k]);
  if (v.includes(null)) return { side: 'could not check', why: 'a middle row is still forming', v };
  const up = v.filter(x => x === 1).length, dn = v.filter(x => x === -1).length;
  const d = (up >= 2 && dn === 0) ? 1 : (dn >= 2 && up === 0) ? -1 : 0;
  const out = { v, d, side: d > 0 ? 'CALLS' : d < 0 ? 'PUTS' : 'no side', for: [], against: [], blind: [] };
  if (!d) { out.why = `rows ${fmtRows(v)} — no side`; }
  // counted facts, only when a side is named
  const oi = rec.oi_read || ['NOT READ', ''];
  const near = rec.near || {}, ag = rec.aggr || {};
  const payers = d > 0 ? 'CE' : 'PE', holders = d > 0 ? 'PE' : 'CE';
  const P = near[payers], Hh = near[holders];
  const fold = s => (rec.folds || []).filter(f => f.side === s && mm(rec.t) - mm(f.t) >= 0 && mm(rec.t) - mm(f.t) <= 15).slice(-1)[0];
  if (d) {
    if (rec.marks != null && rec.marks < 15) out.blind.push(`OI could not check — fronts forming (${rec.marks} of 15 marks)`);
    else if (oi[0] === 'NOT READ') out.blind.push('OI could not check — ' + (rec.fronts_why || oi[1]));
    else {
      const want = d > 0 ? 'TREND UP' : 'TREND DOWN', opp = d > 0 ? 'TREND DOWN' : 'TREND UP';
      if (oi[0] === want) out.for.push(`OI ${oi[0]} — ${oi[1]}`); else if (oi[0] === opp) out.against.push(`OI ${oi[0]} — ${oi[1]}`); else out.flat = (out.flat || []).concat([`OI ${oi[0]} — ${oi[1]}`]);
      const pf = fold(payers);
      if (P) { if (P.state === 'UNWINDING' || pf) out.for.push(`payers ${payers} ${P.k} ${P.state.toLowerCase()}${pf ? ` · fold ${pf.t}` : ''}`); else if (P.state === 'BUILDING') out.against.push(`payers ${payers} ${P.k} building in its way`); else out.flat = (out.flat || []).concat([`payers ${payers} ${P.k} stalled`]); }
      if (Hh) { if (Hh.state === 'BUILDING') out.for.push(`holders ${holders} ${Hh.k} building`); else if (Hh.state === 'UNWINDING') out.against.push(`holders ${holders} ${Hh.k} leaving`); else out.flat = (out.flat || []).concat([`holders ${holders} ${Hh.k} stalled`]); }
    }
    if (ag.word) { (ag.dir === d ? out.for : out.against).push(`aggression ${ag.word} ${ag.dir > 0 ? 'up' : 'down'}`); }
    else if (ag.fact) out.flat = (out.flat || []).concat(['aggression none']);
    else out.blind.push('flow could not check — ' + (ag.why || 'no ladder'));
  }
  out.expiry = EXPIRY[key] || null;
  return out;
}
const fmtRows = v => ['5m', '15m', '1h'].map((k, i) => k + ' ' + ({ 1: 'UP', '-1': 'DOWN', 0: 'RANGE' }[v[i]] || 'forming')).join(' · ');

console.log('## side minutes per index-day, and the side changes (minute, side, index px)');
for (const key of Object.keys(D.days).sort()) {
  const d = D.days[key], c = {}, changes = [];
  let last = null;
  for (const m of d.minutes) {
    const s = sideRead(m, key); c[s.side] = (c[s.side] || 0) + 1;
    if (s.side !== last) { changes.push(`${m.t} ${s.side} @${Math.round(m.px)}`); last = s.side; }
  }
  console.log(key, JSON.stringify(c));
  console.log('   changes:', changes.join(' | '));
}
console.log('\n## at her entries');
const rows = [];
for (const tr of D.trades) {
  const em = H.readMinute(tr.entry_ts), key = `${tr.idx}|${tr.day}`;
  const rec = D.days[key].minutes.find(m => m.t === em);
  const s = sideRead(rec, key);
  const mine = tr.side === 'CE' ? 'CALLS' : 'PUTS';
  const rel = s.side === 'CALLS' || s.side === 'PUTS' ? (s.side === mine ? (tr.role === 'buyer' ? 'agrees' : 'against (you wrote the read\'s side)') : (tr.role === 'buyer' ? 'against' : 'agrees (you wrote the other side)')) : s.side;
  const others = IDX.filter(i => i !== tr.idx).map(i => { const r = D.days[`${i}|${tr.day}`]; const x = r ? sideRead(r.minutes.find(m => m.t === em), `${i}|${tr.day}`) : { side: 'no record' }; return `${i} ${x.side}`; }).join(', ');
  const row = { id: tr.id, day: tr.day, idx: tr.idx, c: `${tr.strike}${tr.side}`, role: tr.role, entry: tr.entry_ts.slice(0, 5), read: em, side: s.side, rows: s.v ? fmtRows(s.v) : s.why,
    nfor: s.for ? s.for.length : 0, nag: s.against ? s.against.length : 0, nblind: s.blind ? s.blind.length : 0, forF: s.for || [], agF: s.against || [], blindF: s.blind || [], rel, others, expiry: s.expiry,
    taken: tr.exit != null ? Math.round((tr.exit - tr.entry) * tr.qty) : null };
  rows.push(row);
  console.log(`${row.day} ${row.idx.padEnd(6)} ${row.c.padEnd(8)} ${row.role[0]} in ${row.entry} read ${row.read} | ${row.side.padEnd(8)} ${row.nfor} for · ${row.nag} against · ${row.nblind} blind | ${row.rel} | rows ${row.rows}${row.expiry ? ' | 0DTE [' + row.expiry + ']' : ''} | others: ${row.others} | took ${row.taken}`);
  if (row.forF.length || row.agF.length) console.log(`      for: ${row.forF.join('; ')} || against: ${row.agF.join('; ')}${row.blindF.length ? ' || blind: ' + row.blindF.join('; ') : ''}`);
}
fs.writeFileSync(path.join(__dirname, 'side_rows.json'), JSON.stringify(rows, null, 1));
