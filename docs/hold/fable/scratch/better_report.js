// node scratch/better_report.js -> what the BETTER TRADE read said at each of her entries, and the day-word counts
const fs = require('fs'), path = require('path');
const here = path.join(__dirname, '..');
global.window = {};
new Function(fs.readFileSync(path.join(here, 'data.js'), 'utf8'))();
const H = require(path.join(here, 'hold.js')).HOLD;
const B = require(path.join(here, 'better.js')).BETTER;
const D = global.window.HOLD_DATA;
const OPTS = { variant: process.argv.includes('--variant') };
console.log('VARIANT B:', OPTS.variant);
const short = s => (s || '').replace(/\s+/g, ' ').slice(0, 140);

console.log('## day-word counts per index-day (minutes)');
for (const key of Object.keys(D.days).sort()) {
  const d = D.days[key], c = {};
  for (const m of d.minutes) { const w = B.dayRead(m, OPTS).day; c[w] = (c[w] || 0) + 1; }
  // side on BUYING minutes
  const sides = {};
  for (const m of d.minutes) { const dr = B.dayRead(m, OPTS); if (dr.day === 'BUYING' || dr.day === 'SELLING') { const s = B.sideRead(m, dr, OPTS); const k = `${dr.day} ${s.side || 'no side'}`; sides[k] = (sides[k] || 0) + 1; } }
  console.log(key, JSON.stringify(c), JSON.stringify(sides));
}
console.log('\n## at her entries');
const rows = [];
for (const tr of D.trades) {
  const em = H.readMinute(tr.entry_ts);
  const R = B.read(D.days, tr.day, em, tr, OPTS);
  const me = R.per[tr.idx];
  const row = { id: tr.id, day: tr.day, idx: tr.idx, c: `${tr.strike}${tr.side}`, role: tr.role, entry: tr.entry_ts.slice(0, 5), read: em,
    dayWord: me.day.day, since: me.since, dayWhy: short(me.day.why), side: me.side.side, n: me.side.n, of: me.side.of, blind: me.side.blind, rank: me.rank,
    best: R.best, second: R.second, engine: me.engine.status ? `${me.engine.status}: ${short(me.engine.text)}` : short(me.engine.why),
    mine: R.mine ? `${R.mine.head} · ${R.mine.marks}` : '', taken: tr.exit != null ? Math.round((tr.exit - tr.entry) * tr.qty) : null,
    ranking: R.ranked.map(x => `${x.rank} ${x.idx} ${x.day.day}${x.side.side ? ' ' + x.side.side : ''} ${x.side.n}/${x.side.of}`).join(' · ') };
  rows.push(row);
  console.log(`${row.day} ${row.idx.padEnd(6)} ${row.c.padEnd(8)} ${row.role[0]} in ${row.entry} read ${row.read} | ${row.dayWord} since ${row.since} · side ${row.side} ${row.n}/${row.of} (blind ${row.blind}) · rank ${row.rank} | ${row.mine} | engine ${row.engine} | took ${row.taken}`);
  console.log(`      ranking: ${row.ranking} | best ${row.best} | second ${row.second}`);
}
fs.writeFileSync(path.join(__dirname, OPTS.variant ? 'better_rows_variant.json' : 'better_rows.json'), JSON.stringify(rows, null, 1));
// the DAY word at 10:30 and 15:00 per index-day (P1 / falsifier shape)
console.log('\n## DAY at 10:30 / 12:30 / 15:00');
for (const key of Object.keys(D.days).sort()) {
  const d = D.days[key];
  const at = t => { const m = d.minutes.find(x => x.t === t); const r = B.dayRead(m, OPTS); const s = (r.day === 'BUYING' || r.day === 'SELLING') ? B.sideRead(m, r, OPTS) : null; return `${r.day}${s && s.side ? ' ' + s.side + ' ' + s.n + '/' + s.of : ''}`; };
  console.log(key, '10:30', at('10:30'), '| 12:30', at('12:30'), '| 15:00', at('15:00'));
}
