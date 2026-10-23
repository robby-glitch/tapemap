// tapemap/tools/gen_push_expected.mjs
// Runs the EXTENSION'S OWN v2.js flowState and market.js vwapSeries over its recorded test days (orderflow-desk/test:
// session-<day>.ofd.json with that day's rank_ref_NIFTY_<day>.json) and writes every closed bar's flow state, so
// test_hold2.py can pin hold2.py's PUSH port against it (HOLD-V2-PREREG: "the TapeMap port must give the same answers on
// the same bars"). Generated once and committed; re-run only if the extension's engine changes (the commit says why).
//   node tools/gen_push_expected.mjs     -> test/fixtures/push_expected.json
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const OFD = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk/';
const DAYS = ['2026-10-09', '2026-10-12', '2026-10-13', '2026-10-16', '2026-10-19', '2026-10-21'];
const { flowState, V2 } = await import(pathToFileURL(OFD + 'src/engine/v2.js').href);
const { vwapSeries } = await import(pathToFileURL(OFD + 'src/engine/market.js').href);

const out = { build: V2.BUILD, days: {} };
for (const day of DAYS) {
  const fx = `${OFD}test/session-${day}.ofd.json`, rf = `${OFD}test/rank_ref_NIFTY_${day}.json`;
  if (!existsSync(fx) || !existsSync(rf)) { console.error('missing', fx, rf); process.exit(1); }
  const bars = JSON.parse(readFileSync(fx, 'utf8')).bars, ref = JSON.parse(readFileSync(rf, 'utf8')), vw = vwapSeries(bars);
  out.days[day] = { ref: ref.id, bars: bars.map((b, i) => {
    const f = flowState(bars, i, ref), sg = vw[i] && vw[i].sigma > 0 ? vw[i].sigma : 0;
    return { t: b.t, state: f.state, dir: f.dir ?? null, U: b.o == null ? null : Math.max(sg, 0.001 * b.o) };
  }) };
  console.log(day, bars.length, 'bars,', out.days[day].bars.filter((x) => x.state === 'PUSH').length, 'PUSH');
}
writeFileSync('test/fixtures/push_expected.json', JSON.stringify(out));
