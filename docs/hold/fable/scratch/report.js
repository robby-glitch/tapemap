// node scratch/report.js  -> prints the per-trade table used by REPORT.md (and asserts the engine's invariants)
const path = require('path');
const fs = require('fs');
const here = path.join(__dirname, '..');
global.window = {};
new Function(fs.readFileSync(path.join(here, 'data.js'), 'utf8'))();
const HOLD = require(path.join(here, 'hold.js')).HOLD;
const D = global.window.HOLD_DATA;

const tag = r => r.verdict === 'FOLD' ? 'FOLD' : r.verdict;
const short = s => (s || '').replace(/\s+/g, ' ').slice(0, 150);
const rows = [];
let checks = 0;
for (const tr of D.trades) {
  const day = D.days[`${tr.idx}|${tr.day}`];
  const R = HOLD.read(day, tr);
  if (R.error) { console.log(tr.id, R.error); continue; }
  const byT = Object.fromEntries(R.rows.map(r => [r.t, r]));
  const en = byT[R.entryMin], ex = R.exitMin ? byT[R.exitMin] : null;
  // invariants: latch, structure monotone, the entry row exists
  let seenFold = false, lastL = null;
  for (const r of R.rows) {
    if (r.verdict === 'FOLD') seenFold = true; else if (seenFold) throw new Error('latch broken ' + tr.id + ' ' + r.t);
    if (lastL != null && (R.want < 0 ? r.structure.L > lastL : r.structure.L < lastL)) throw new Error('L moved away ' + tr.id + ' ' + r.t);
    lastL = r.structure.L;
    checks++;
  }
  const foldRow = R.fold ? byT[R.fold.t] : null;
  const close = R.rows[R.rows.length - 1];
  const next30 = ex ? R.rows.filter(r => HOLD.mm(r.t) > HOLD.mm(R.exitMin) && HOLD.mm(r.t) <= HOLD.mm(R.exitMin) + 30 && r.prem != null) : [];
  const mfe = next30.length ? (tr.role === 'buyer' ? Math.max(...next30.map(r => r.prem)) : Math.min(...next30.map(r => r.prem))) : null;
  const mae = next30.length ? (tr.role === 'buyer' ? Math.min(...next30.map(r => r.prem)) : Math.max(...next30.map(r => r.prem))) : null;
  const afterFold = R.fold ? R.rows.filter(r => HOLD.mm(r.t) > HOLD.mm(R.fold.t) && HOLD.mm(r.t) <= HOLD.mm(R.fold.t) + 30 && r.prem != null) : [];
  const fav = a => a.length ? (tr.role === 'buyer' ? Math.max(...a.map(r => r.prem)) : Math.min(...a.map(r => r.prem))) : null;
  const adv = a => a.length ? (tr.role === 'buyer' ? Math.min(...a.map(r => r.prem)) : Math.max(...a.map(r => r.prem))) : null;
  const foldFav30 = fav(afterFold), foldAdv30 = adv(afterFold);
  const firstWatch = R.rows.find(r => r.verdict === 'WATCH');
  const nFold = R.rows.filter(r => r.verdict === 'FOLD').length, nWatch = R.rows.filter(r => r.verdict === 'WATCH').length, nHold = R.rows.filter(r => r.verdict === 'HOLD').length;
  const held = ex ? R.rows.filter(r => HOLD.mm(r.t) >= HOLD.mm(R.entryMin) && HOLD.mm(r.t) <= HOLD.mm(R.exitMin)) : [];
  rows.push({
    id: tr.id, day: tr.day, idx: tr.idx, c: `${tr.strike}${tr.side}`, role: tr.role, qty: tr.qty,
    entry_ts: tr.entry_ts, exit_ts: tr.exit_ts, entry: tr.entry, exit: tr.exit,
    taken: ex && tr.exit != null ? Math.round((tr.exit - tr.entry) * tr.qty) : null,
    entryMin: R.entryMin, entryVerdict: en ? en.verdict : '?', entryWhy: en ? short(en.why) : '',
    entryReads: en ? `S ${en.structure.state} L ${HOLD.fmt(en.structure.L)} (${en.structure.dist}) · fuel ${en.fuel.state} · flow ${en.flow.state} · trend ${en.trend.state}` : '',
    exitMin: R.exitMin, exitVerdict: ex ? ex.verdict : null, exitWhy: ex ? short(ex.why) : '',
    exitReads: ex ? `S ${ex.structure.state} L ${HOLD.fmt(ex.structure.L)} (${ex.structure.dist}) · fuel ${ex.fuel.state} · flow ${ex.flow.state} · trend ${ex.trend.state}` : '',
    heldVerdicts: held.map(r => r.verdict[0]).join(''),
    firstFold: R.fold ? R.fold.t : null, firstFoldWhy: R.fold ? short(R.fold.why) : null,
    premAtFold: foldRow ? foldRow.prem : null, premAtClose: close.prem, premAtExit: ex ? ex.prem : null,
    mfe30: mfe, mae30: mae, nHold, nWatch, nFold, foldFav30, foldAdv30, firstWatch: firstWatch ? firstWatch.t : null,
    spotAtEntry: en ? en.spot : null, spotAtExit: ex ? ex.spot : null, lineAtEntry: en ? en.structure.L : null, roomAtEntry: en ? en.structure.dist : null,
  });
}
console.log('engine checks', checks);
console.log(JSON.stringify(rows, null, 1));
fs.writeFileSync(path.join(__dirname, 'report_rows.json'), JSON.stringify(rows, null, 1));
