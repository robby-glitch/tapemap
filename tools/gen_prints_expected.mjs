// tapemap/tools/gen_prints_expected.mjs
// Runs the EXTENSION'S OWN decode.js / market.js / board.js over a recorded day
// and writes what they say, so test_prints.py can pin prints.py against it.
// Generated ONCE and committed; re-run only if the extension's engine changes
// (then the commit that re-runs it says why).
//   node tools/gen_prints_expected.mjs        -> row size 5 (the chart's own)
//   node tools/gen_prints_expected.mjs 1      -> row size 1 (decode.js's DEFAULTS)
// The row-1 file exists because at row 5 this day has ZERO stacks and ZERO
// unfinished auctions, so the parity pin proved only true-negatives for those
// two fields. At row 1 the same day has stacks, and they are pinned too.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const ENG = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk/src/engine/';
const FIX = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk/test/session-2026-09-11.ofd.json';
const ROW = Number(process.argv[2] || 5), ANCHOR = 0;
if (!Number.isFinite(ROW) || ROW <= 0) { console.error(`bad row size: ${process.argv[2]}`); process.exit(1); }
// row 5 keeps the original name, so the committed fixture and every test that
// names it are untouched by this parameterisation.
const OUT = ROW === 5 ? 'test/fixtures/prints_expected_2026-09-11.json'
                      : `test/fixtures/prints_expected_2026-09-11_row${ROW}.json`;

const { rebin, readBar, DEFAULTS } = await import(pathToFileURL(ENG + 'decode.js').href);
const { profile } = await import(pathToFileURL(ENG + 'market.js').href);
const { board } = await import(pathToFileURL(ENG + 'board.js').href);

const j = JSON.parse(readFileSync(FIX, 'utf8'));
const bars = j.bars.filter((b) => Array.isArray(b.ladder) && b.ladder.length).sort((a, b) => a.t - b.t);
const cfg = { ...DEFAULTS, rowSize: ROW, rowAnchor: ANCHOR };
// readBar's `base` only shapes sizeClass/lopsided, which are not pinned; poc, stacks and the
// unfinished flags do not read it.
const perBar = bars.map((b) => {
  const r = readBar(b, null, { medVol: b.vol || 1, medRange: 0, p75Lop: 0 }, cfg);
  return { t: b.t, rows: rebin(b.ladder, ROW, ANCHOR), stacks: r.stacks, poc: r.poc,
           unfinished_high: r.unfinishedHigh, unfinished_low: r.unfinishedLow };
});
const pr = profile(bars);
const B = board(bars, { rowSize: ROW });
mkdirSync('test/fixtures', { recursive: true });
writeFileSync(OUT, JSON.stringify({
  source: 'orderflow-desk/test/session-2026-09-11.ofd.json', rowSize: ROW, rowAnchor: ANCHOR,
  bars: perBar, profile: { poc: pr.poc, vah: pr.vah, val: pr.val, total: pr.total }, nodes: B.nodes,
}));
const stacks = perBar.reduce((n, b) => n + b.stacks.length, 0);
const unf = perBar.filter((b) => b.unfinished_high || b.unfinished_low).length;
console.log(`wrote ${OUT}: row ${ROW}, ${perBar.length} bars, profile poc ${pr.poc} vah ${pr.vah} val ${pr.val}, ${B.nodes.length} nodes, ${stacks} stacks, ${unf} unfinished bars`);
