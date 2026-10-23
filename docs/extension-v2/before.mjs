// before.mjs -- TODAY's extension rules on the same bars, for the "before" count. Runs the extension's own engine
// (board.js + decoder.js, unchanged, imported from orderflow-desk) the way main.js does (board per closed bar, marks
// placed once; decoder over the closed bars), then counts what overlay.js would draw: every shown decoder glyph, every
// trap mark (P), lost floors of the last hour (X), and its lines (one level per side of price: open BADA print, held
// wall, yesterday's H/L/C). Reads one JSON on stdin, writes one JSON on stdout. Nothing is written to disk.
import { pathToFileURL } from 'node:url';
const SRC = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk/src/engine/';
const { board } = await import(pathToFileURL(SRC + 'board.js').href);
const { decode } = await import(pathToFileURL(SRC + 'decoder.js').href);

const inp = JSON.parse(await new Promise((r) => { let s = ''; process.stdin.on('data', (c) => (s += c)); process.stdin.on('end', () => r(s)); }));
const { bars, prior, winStart, T } = inp;
const ROW = 5, MARK_KINDS = ['trap', 'climax', 'absorption', 'exhaustion'];
const hm = (t) => new Date(t + 19800000).toISOString().slice(11, 16);
const levels = [['PDH', prior.h], ['PDL', prior.l], ['PDC', prior.c]].filter(([, p]) => p != null).map(([type, price]) => ({ type, price }));
const marks = [], marked = new Set();
let B = null;
for (let i = 0; i < bars.length; i++) {
  B = board(bars.slice(0, i + 1), { prior: levels, rowSize: ROW });
  for (const e of B.events.filter((x) => x.t <= bars[i].t && MARK_KINDS.includes(x.kind))) {
    const key = e.t + '|' + e.kind + '|' + e.p + '|' + e.side; if (marked.has(key)) continue; marked.add(key);
    marks.push({ t: e.t, time: e.time, kind: e.kind, side: e.kind === 'trap' ? -e.side : e.side, logged_side: e.side, p: e.p, size: e.size });
  }
}
const NAME = { PDH: 'Kal ka high', PDL: 'Kal ka low', PDC: 'Kal ka close' };
const priors = levels.map((L) => ({ p: L.price, name: NAME[L.type] }));
const dec = decode(bars.filter((b) => b.c != null && b.o != null), { lot: 65, levels: priors.map((L) => ({ name: L.name, p: L.p })) });
const lastT = bars[bars.length - 1].t, price = bars[bars.length - 1].c;
const inWin = (t) => t >= winStart;
// ---- glyphs (overlay.js step 3/4: every glyph whose bar is on screen)
const glyphs = [];
for (const e of dec.events) if (e.shown && inWin(e.t)) glyphs.push({ src: 'decoder', kind: e.kind, time: e.time, p: e.p, side: e.side, lots: e.lots ?? null, chip: e.chip, state: e.state });
for (const m of marks) if (m.kind === 'trap' && inWin(m.t)) glyphs.push({ src: 'board', kind: 'P', time: m.time, p: m.p, side: m.side, lots: m.size });
const heldL = (L) => L.side && !L.broken && ((L.role === 'defended' && !L.under) || L.role === 'wall');
for (const L of B.levels) if (L.brokenT && lastT - L.brokenT <= 3600000) glyphs.push({ src: 'board', kind: 'X', time: hm(L.brokenT), p: L.price, side: L.side });
// ---- lines (overlay.js step 2): one level per side of price
const cands = [];
for (const e of dec.events) if (e.kind === 'E1' && e.state === 'BAAKI') cands.push({ cls: 0, p: e.p, t: e.t, why: 'print' });
for (const L of B.levels) if (heldL(L) && L.role === 'wall') cands.push({ cls: 1, p: L.price, why: 'wall' });
for (const q of priors) cands.push({ cls: 2, p: q.p, why: q.name });
const owners = []; for (const c of cands.sort((a, b) => a.cls - b.cls)) if (!owners.some((x) => Math.abs(x.p - c.p) <= ROW)) owners.push(c);
const pick = (above) => { const side = owners.filter((c) => (above ? c.p > price : c.p <= price));
  const pr = side.filter((c) => c.cls === 0).sort((a, b) => b.t - a.t);
  return pr[0] || side.filter((c) => c.cls > 0).sort((a, b) => Math.abs(a.p - price) - Math.abs(b.p - price) || a.cls - b.cls)[0] || null; };
const lines = [pick(true), pick(false)].filter(Boolean);
const chips = Math.min(6, lines.length + glyphs.length);
process.stdout.write(JSON.stringify({
  T, n_bars: bars.length, marks, glyphs, lines,
  decoder_events: dec.events.map((e) => ({ kind: e.kind, time: e.time, p: e.p, side: e.side, lots: e.lots ?? null, shown: !!e.shown, state: e.state, at: e.at ? e.at.name : null, chip: e.chip })),
  drawn: { glyphs: glyphs.length, lines: lines.length, chips, objects: glyphs.length + lines.length },
}));
