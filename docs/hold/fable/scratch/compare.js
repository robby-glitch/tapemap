// node scratch/compare.js -> both engines (fable hold.js, opus verdict.js) at the SAME minutes, same trades.
const fs = require('fs'), zlib = require('zlib'), path = require('path');
const F = path.join(__dirname, '..'), O = path.join(__dirname, '..', '..', 'opus');
global.window = {}; new Function(fs.readFileSync(path.join(F, 'data.js'), 'utf8'))();
const H = require(path.join(F, 'hold.js')).HOLD, D = global.window.HOLD_DATA;
const HF = require(path.join(O, 'verdict.js'));
const OD = {};
for (const f of fs.readdirSync(path.join(O, 'scratch')).filter(f => /^facts_.*\.json\.gz$/.test(f))) {
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(O, 'scratch', f))).toString());
  OD[`${d.idx}|${d.day}`] = d;
}
const mm = H.mm, hm = H.hm;
const short = s => (s || '').replace(/\s+/g, ' ').slice(0, 170);

function both(tr, mins) {
  // tr: {idx, day, strike, side, role: buyer|writer, entry_ts, qty}
  const fd = D.days[`${tr.idx}|${tr.day}`], od = OD[`${tr.idx}|${tr.day}`];
  const em = H.readMinute(tr.entry_ts);
  const p0 = (fd.px[`${tr.strike}${tr.side}`] || {})[em];
  const mine = H.read(fd, { ...tr, entry: p0, exit_ts: null, exit: null });
  const theirs = od ? HF.replay({ idx: tr.idx, day: tr.day, k: tr.strike, side: tr.side, role: tr.role === 'buyer' ? 'long' : 'short',
    p0, qty: tr.qty, t0: tr.entry_ts, read_from: em, read_to: '15:29' }, od) : null;
  const tb = theirs ? Object.fromEntries(theirs.map(v => [v.t, v])) : {};
  const mb = Object.fromEntries(mine.rows.map(r => [r.t, r]));
  console.log(`\n### ${tr.day} ${tr.idx} ${tr.strike}${tr.side} ${tr.role} from ${em} (p0 ${p0})`);
  const prem = fd.px[`${tr.strike}${tr.side}`] || {};
  for (const t of mins) {
    const m = mb[t], o = tb[t];
    console.log(`${t} prem ${prem[t] ?? '—'}`);
    console.log(`   FABLE ${m ? m.verdict.padEnd(5) : '—    '} ${m ? short(m.since ? m.foldWhy : m.why) : ''}`);
    if (m) console.log(`         S ${m.structure.state} L ${H.fmt(m.structure.L)} (${m.structure.dist}) · fuel ${m.fuel.state} · flow ${m.flow.state} · trend ${m.trend.state}`);
    console.log(`   OPUS  ${o ? o.word.padEnd(5) : (theirs ? '—    ' : 'no facts')} ${o ? short(o.line) : ''}`);
    if (o && o.facts && !o.blind) console.log(`         for ${o.for.length} [${o.for.map(short).join(' | ').slice(0, 160)}] against ${o.against.length} [${o.against.map(short).join(' | ').slice(0, 160)}]${o.note ? ' · ' + o.note : ''}${o.paidLast ? ' · paidLast ' + o.paidLast + ' quiet ' + o.quietFor : ''}`);
  }
  const mf = mine.fold ? mine.fold.t : null, of = theirs ? (theirs.find(v => v.word === 'FOLD') || {}).t : null;
  console.log(`   first FOLD: fable ${mf || '—'} (${mf ? prem[mf] : ''}) · opus ${of || '—'} (${of ? prem[of] : ''})`);
}

const T = (day, idx, strike, side, role, entry_ts, qty) => ({ day, idx, strike, side, role, entry_ts, qty });
both(T('2026-09-24', 'SENSEX', 74200, 'PE', 'buyer', '09:42:43', 20), ['09:41', '09:46', '10:14', '10:22', '10:37', '11:00', '11:30']);
both(T('2026-09-24', 'SENSEX', 74200, 'PE', 'buyer', '10:19:11', 40), ['10:18', '10:22', '10:37']);
both(T('2026-09-24', 'SENSEX', 74100, 'PE', 'buyer', '12:32:32', 40), ['12:31', '12:32', '13:12', '13:26', '13:50', '14:12', '14:20', '14:35', '14:40']);
both(T('2026-09-24', 'SENSEX', 74000, 'PE', 'buyer', '13:26:41', 20), ['13:25', '13:26', '13:50']);
both(T('2026-09-24', 'SENSEX', 73800, 'PE', 'buyer', '13:54:47', 20), ['13:53', '13:54']);
both(T('2026-09-24', 'SENSEX', 73800, 'PE', 'buyer', '13:57:49', 20), ['13:56', '13:57', '14:12', '14:22', '14:30', '14:35', '14:40']);
both(T('2026-09-23', 'NIFTY', 23450, 'CE', 'buyer', '09:18:03', 65), ['09:17', '09:24', '09:50', '09:57']);
both(T('2026-09-23', 'NIFTY', 23450, 'CE', 'buyer', '10:00:41', 65), ['09:59', '10:00', '10:08']);
both(T('2026-09-23', 'NIFTY', 23450, 'CE', 'buyer', '10:19:52', 65), ['10:18', '10:30', '10:40', '12:47']);
both(T('2026-09-23', 'NIFTY', 23450, 'CE', 'buyer', '10:33:44', 65), ['10:32', '10:39', '10:40', '11:03']);
both(T('2026-09-23', 'NIFTY', 23450, 'CE', 'buyer', '11:07:37', 65), ['11:06', '11:15', '11:37']);
both(T('2026-09-23', 'SENSEX', 74900, 'CE', 'buyer', '11:32:24', 20), ['11:31', '11:39', '12:06', '12:32']);
both(T('2026-09-22', 'NIFTY', 23550, 'PE', 'buyer', '10:32:42', 65), ['10:31', '10:37', '11:14', '11:19']);
both(T('2026-09-22', 'NIFTY', 23500, 'PE', 'buyer', '13:48:38', 65), ['13:47', '13:53', '14:00', '14:14']);
both(T('2026-09-22', 'NIFTY', 23300, 'CE', 'buyer', '09:42:51', 65), ['09:41', '10:19', '10:21', '10:25']);
// writers: mine and theirs, run through both
both(T('2026-09-24', 'SENSEX', 74500, 'CE', 'writer', '11:00:00', 20), ['10:59', '11:07', '11:19', '12:00', '14:00']);
both(T('2026-09-24', 'SENSEX', 74200, 'CE', 'writer', '10:30:00', 20), ['10:29', '10:40', '11:00', '11:30', '13:00']);
both(T('2026-09-24', 'SENSEX', 74200, 'PE', 'writer', '09:45:00', 20), ['09:44', '09:46', '09:50']);
both(T('2026-09-23', 'NIFTY', 23400, 'CE', 'writer', '10:30:00', 65), ['10:29', '10:40', '11:18']);
both(T('2026-09-23', 'NIFTY', 23450, 'CE', 'writer', '11:15:00', 65), ['11:17', '11:18', '12:00', '13:00']);

// entry-read distribution for a fresh trade at every minute (both engines), buyer/writer x up/down
for (const key of ['SENSEX|2026-09-24', 'NIFTY|2026-09-23']) {
  const fd = D.days[key], od = OD[key];
  for (const [role, side] of [['buyer', 'PE'], ['buyer', 'CE'], ['writer', 'CE'], ['writer', 'PE']]) {
    const cf = {}, co = {};
    for (const m of fd.minutes) {
      if (mm(m.t) < mm('09:16')) continue;
      const r = H.read(fd, { idx: fd.idx, day: fd.day, strike: 0, side, role, qty: 1, entry_ts: hm(mm(m.t) + 1) + ':00', exit_ts: null, entry: null });
      const w = r.rows[0].verdict; cf[w] = (cf[w] || 0) + 1;
      if (od) { const v = HF.replay({ idx: fd.idx, day: fd.day, k: 0, side, role: role === 'buyer' ? 'long' : 'short', p0: null, qty: 1, t0: m.t, read_from: m.t, read_to: m.t }, od)[0]; const ww = v ? v.word.replace(' · NOISE', '') : '?'; co[ww] = (co[ww] || 0) + 1; }
    }
    console.log(`\nENTRY-READ ${key} ${role} ${side}: fable ${JSON.stringify(cf)} · opus ${JSON.stringify(co)}`);
  }
}
