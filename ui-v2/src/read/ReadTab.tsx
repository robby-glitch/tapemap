// THE READ (read.py via GET /api/read): one HELD read per index, OI first. The first tab and her main screen.
//
// Mary, 2026-10-08: "the day where almost no put writing and almost whole day is call writing its a trend day ...
// it lacks intelligence ... make this tool a 10 on 10." The day test (docs/review/DAY-TEST-2026-10-08.md) found nine
// voices re-deciding every 3 minutes. This screen shows ONE word per index that stands until its own FLIP line
// breaks, the lines in spot AND fut, why (who is writing, price, flow, where), the trade her way, what happened,
// and the engine's own voice -- greyed when it argues against the read. A terminal, not an essay: one row per
// index, the same columns on all three, cells and numbers. Light only. [M] measured / [I] inferred in each header.
import { useEffect, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import type { IndexKey, Read as EngineRead } from '../data'
import { usePalette, rgbOf } from '../theme'
import type { Palette } from '../theme'

export interface ReadLine { k: string; spot: number; fut: number | null; gap: number; note: string }
export interface ReadChip { k: string; v: string | null; dir: number; tag: string }
export interface ReadLeg { act: 'BUY' | 'SELL'; side: 'CE' | 'PE'; k: number; ltp: number | null; why: string }
export interface ReadEvent { t: string; kind: string; text: string; dir: number }
export interface ReadSeg { word: string; dir: number; from: string; to: string; move: number; since: string }
// RANK (decode-loop Phase 1, rank.py): every measured number carries its rank against recorded days at the same
// clock. pct = size, pct_sign = direction (shown in the title, gates nothing), n = reference DAYS.
export interface RankL {
  raw?: number | null; unit?: string | null; pct: number | null; pct_sign?: number | null; n: number; tag: string
  prov?: boolean | null; thin?: boolean | null; single?: string | null; capped?: string | null; src?: string | null
  why?: string | null; t?: string; min?: number; lots?: number; px?: number; word?: string
}
export interface ReadRanks {
  kind?: string; mark?: string; why?: string | null; open_t?: string
  ce?: RankL; pe?: RankL; A?: RankL; ce30?: RankL; pe30?: RankL; cvd?: RankL; vol?: RankL; open?: RankL
  bar?: RankL; cvd40?: RankL; x?: RankL; bvol?: RankL; foi40?: RankL; likhna?: { word: string; gated: boolean }
  scale?: { iv?: number; sigma_d?: number; range_sd?: number; moved30?: number; why?: string }
}
// COVERAGE (§5.1): the three absences are three kinds and never one rendering
export interface CovRow { src: string; kind: 'ok' | 'none' | 'cnc' | 'hidden'; text: string; tag: string }
export interface BasisBand { v: number | null; expected: number | null; lo: number | null; hi: number | null
  dte: number | null; parity: number | null; unusual: boolean; ok: boolean; why: string | null }
interface HL { hi: number; hi_t: string; lo: number; lo_t: string; src: string }
interface WbSide { word: string; res: number | null }
export interface ReadCard {
  ok: boolean; why?: string
  t?: string; word?: string; dir?: number; arrow?: string; since?: string | null; agree?: number | null
  spot?: number; spot_at?: string; basis?: number | null; warn?: string[]; beyond?: boolean
  lines?: ReadLine[]; chips?: ReadChip[]; votes?: { writers: number | null; price: number | null; flow: number | null }
  trade?: ReadLeg[]; against?: string; late?: boolean; day?: ReadSeg[]; changes?: number
  expr?: { word: string; t: string } | null; events?: ReadEvent[]; blind?: string[]
  w?: { cls?: string; ce?: number | null; pe?: number | null; ce30?: number | null; pe30?: number | null; why?: string | null; edge?: number | null }
  f?: { cvd?: number | null; buy?: number | null; sell?: number | null; vol?: number | null; gc?: string | null; why?: string | null }
  ranks?: ReadRanks; coverage?: CovRow[]; basis_band?: BasisBand; hl?: { spot?: HL | null; fut?: HL | null }
  wb?: { ce?: WbSide | null; pe?: WbSide | null; why?: string | null }
  // READ-2 (docs/read/READ-2-PREREG.md): a held LEAN that FUEL and LEG FLOW back reads TREND · flow+fuel; JAGAH [I]
  src?: 'writers' | 'flow+fuel' | null; word_r1?: string; jagah?: { text: string | null } | null
  decode?: Decode | null; decode_why?: string | null
}
// THE DECODE block (decode.py; the contract shared with the extension): the trajectories, then ONE call -- a COUNT of
// the signs present, never a %. Display only. [I]
// state: after an entry, FADE-D reads its HOLD v2 state instead of MATCH (N2): "line 73,612 · +0.4R", "lock …",
// "gave up @10:57 −0.1R", "out @10:34 −1.0R"
export interface DecodeSetup { name: 'FADE' | 'RIDE' | 'FADE-D'; side: 'BUY' | 'SELL'; checks: Record<string, boolean | null>
  state: 'ARMED' | 'MATCH' | '—' | string; thin?: string }     // A25: SENSEX FADE-D "patla (med 15 lot/5m)", display only
export interface Decode {
  call: { text: string; kind: 'THAK' | 'JAARI' | 'MILA' | 'SAAF_NAHI'; d: number; c: number; of: 7; signs: string[] }
  lines: string[]; setups: DecodeSetup[]; t: string | null; tag: 'I'
  leg: { d: -1 | 1; start: { t: string; fut: number; spot: number | null }; ext: { t: string; fut: number; spot: number | null } } | null
  onesided?: OneSided | null; age_s?: number | null       // A23 (onesided.py, §1o) · A13: now − the close it reads
}
// THE ONE-SIDED METER (§1o, display only, UNTESTED): 7 votes per closed 5-min bar, one-sided at 5+; the day type is a
// COUNT, never a probability. type null = could not check (`why`). strip: ▲ ▼ one-sided · mila-jula ? data missing.
export interface OneSided {
  type: 'TREND ▲' | 'TREND ▼' | 'PIN' | 'CHOP' | 'MIXED' | null; why: string | null
  up: number | null; down: number | null; mix: number | null; unk: number | null; dom: number | null
  flips: number | null; crosses: number | null; range_pct: number | null; last: string | null; strip: string | null; tag: 'I'
  thin?: number | null; lots_med?: number | null           // N6: bars under 20 lots (one lot swings the delta vote)
}
const DIN_CHIP: Record<string, string> = { 'TREND ▲': 'upar ka din', 'TREND ▼': 'neeche ka din', PIN: 'atka hua din',
  CHOP: 'do-tarfa · stop khatra', MIXED: 'saaf nahi' }
const STALE_S = 360                                         // A13: the call's time turns amber past 6 min
const FF = (c?: ReadCard) => (c?.src === 'flow+fuel' ? ' · flow+fuel' : '')     // never a plain writers' TREND
export interface ReadReply { ok: boolean; why?: string; day?: string; live?: boolean; asof?: string | null; rev?: string
  indices?: Partial<Record<IndexKey, ReadCard>> }

// One poll for every reader of the READ (this tab and the ANSWER band): a module store, one timer.
type ReadState = { data: ReadReply | null; err: string | null }
let last: ReadState = { data: null, err: null }
const subs = new Set<(x: ReadState) => void>()
let timer: number | null = null
const OLD = 'server purana hai — /api/read naya hai: server restart karein'
const pull = () => fetch('/api/read').then(async (r) => {
  if (r.status === 404) throw new Error(OLD)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const j = await r.json().catch(() => { throw new Error(OLD) })
  return j as ReadReply
}).then((data) => { last = { data, err: data.ok ? null : (data.why ?? 'no reason given') } })
  .catch((e) => { last = { data: last.data, err: String(e?.message ?? e) } })
  .finally(() => subs.forEach((f) => f(last)))

export function useRead(): ReadState {
  const [s, set] = useState(last)
  useEffect(() => {
    subs.add(set)
    if (timer == null) { pull(); timer = window.setInterval(pull, 5000) }
    return () => { subs.delete(set); if (!subs.size && timer != null) { clearInterval(timer); timer = null } }
  }, [])
  return s
}

/** The engine call's implied direction (an exhaust of a leg implies the other way), against the READ's. */
export function engineVsRead(g: EngineRead['ground'], dir: number | undefined): 'khilaaf' | 'saath' | null {
  if (!g || !dir) return null
  const d = (g.dir === 'up' ? 1 : g.dir === 'down' ? -1 : 0) * (g.kind === 'exhaust' ? -1 : 1)
  return d === 0 ? null : d === dir ? 'saath' : 'khilaaf'
}

const wash = (hex: string, a: number) => `rgba(${rgbOf(hex)},${a})`
const fmt = (n: number | null | undefined, d = 0) =>
  n == null ? '—' : n.toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })
const ORDER: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']
const GLOSS: Record<string, [string, string]> = {         // word -> [Hinglish chip, what to do]
  'TREND -1': ['neeche ka din', 'bounce bechna · PE ya CE-sell'],
  'TREND 1': ['upar ka din', 'dip kharidna · CE ya PE-sell'],
  'LEAN -1': ['jhukav neeche · OI peeche nahi', 'chhota size · OI ka intezaar'],
  'LEAN 1': ['jhukav upar · OI peeche nahi', 'chhota size · OI ka intezaar'],
  'RANGE 0': ['box ke andar', 'deewar pe bechna'],
  'WAIT 0': ['saaf nahi', 'ruko'],
  'BAN RAHA 0': ['09:45 tak padh rahe', 'ruko'],
}

function tone(pal: Palette, word?: string, dir?: number) {
  const side = (dir ?? 0) < 0 ? pal.bear : pal.bull
  if (word === 'TREND') return { fg: '#FFFFFF', bg: side, line: side }
  if (word === 'LEAN') return { fg: side, bg: wash(side, 0.1), line: side }
  if (word === 'RANGE') return { fg: pal.accent, bg: wash(pal.accent, 0.12), line: pal.accent }
  return { fg: pal.textSecondary, bg: pal.inset, line: pal.border }
}
const dirCol = (pal: Palette, d: number | null | undefined) =>
  d == null ? pal.textMuted : d < 0 ? pal.bear : d > 0 ? pal.bull : pal.textSecondary

function Head({ children, pal, tag, title, tone }: { children: string; pal: Palette; tag?: string; title?: string; tone?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2,
      borderBottom: `1px solid ${pal.border}`, paddingBottom: 1, gap: 8 }}>
      <span className="micro-label">{children}</span>
      {tag && <span className="mono" title={title} style={{ fontSize: 9.5, color: tone ?? pal.textMuted, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{tag}</span>}
    </div>)
}

/** D6: "basis +75 · carry 76 ✓" / "basis +3 · carry 47 · opt +14 ✓" (the options confirm an unusual basis) /
 *  "basis +3 ? · carry 47 · fut ?" (implausible: no fut level is printed). */
function basisTag(c: ReadCard): string {
  const b = c.basis_band
  const v = sg(c.basis)
  if (!b) return `basis ${v} [M]`
  const carry = b.expected == null ? '' : ` · carry ${fmt(b.expected)}`
  return !b.ok ? `basis ${v} ?${carry} · fut ?` : b.unusual ? `basis ${v}${carry} · opt ${b.parity == null ? '' : sg(b.parity)} ✓`
    : `basis ${v}${carry} ✓`
}

function Votes({ v, pal }: { v: ReadCard['votes']; pal: Palette }) {
  const one = (k: string, x: number | null | undefined) => (
    <span key={k} title={x == null ? `${k}: could not check` : `${k}: ${x < 0 ? 'neeche' : x > 0 ? 'upar' : 'kisi taraf nahi'}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: pal.textSecondary }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, display: 'inline-block',
        background: x == null ? 'transparent' : dirCol(pal, x), border: `1.5px solid ${x == null ? pal.textMuted : dirCol(pal, x)}` }} />
      {k}
    </span>)
  return <span style={{ display: 'inline-flex', gap: 8 }}>{one('OI', v?.writers)}{one('PRICE', v?.price)}{one('FLOW', v?.flow)}</span>
}

const clip: CSSProperties = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }

// read.lakh: OI in thousands -> lakh contracts; signed lots
const lakh = (th: number | null | undefined) => th == null ? '—'
  : (th > 0 ? '+' : th < 0 ? '−' : '') + (Math.abs(th) / 100 >= 100 ? (Math.abs(th) / 100).toFixed(0) : (Math.abs(th) / 100).toFixed(1)) + 'L'
const sg = (n: number | null | undefined, d = 0) => n == null ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + fmt(Math.abs(n), d)

/** One rank beside its number: "p94 · N=17" (N while provisional, < 30 days), grey "noise" below p70, "BAHUT KAM"
 *  at or under p10, "RECORD 7d" above every reference day; "?" when it could not be ranked (the title says why). */
export function Rk({ r, pal }: { r?: RankL | null; pal: Palette }) {
  if (!r) return null
  const title = [r.pct != null ? `p${Math.round(r.pct)} (size)` : '?', r.pct_sign != null ? `p${Math.round(r.pct_sign)} (sign, no gate)` : null,
    `N=${r.n} din`, r.src, r.capped ? `capped at notable: ${r.capped}` : null, r.thin ? 'thin bar' : null, r.why].filter(Boolean).join(' · ')
  let txt = `p${Math.round(r.pct ?? 0)}`, col = pal.textSecondary, w = 500
  if (r.tag === '?') { txt = '?'; col = pal.textMuted }
  else if (r.tag === 'noise') { txt = 'noise'; col = pal.textMuted }
  else if (r.tag === 'BAHUT KAM') { txt = 'BAHUT KAM'; col = pal.accent; w = 800 }
  else if (r.tag === 'RECORD') { txt = `RECORD ${r.n}d`; col = pal.textPrimary; w = 800 }
  else if (r.tag === 'BADA') { col = pal.textPrimary; w = 800 }
  const extra = [r.prov && r.tag !== '?' && r.tag !== 'noise' && r.tag !== 'RECORD' ? `N=${r.n}` : null,
    r.single ? (r.single === 'GC' ? 'GC only' : '1 src') : null, r.src === 'sources disagree' ? 'sources disagree' : null,
    r.thin ? 'thin' : null].filter(Boolean)
  return <span title={title} style={{ fontSize: 9, color: col, fontWeight: w, marginLeft: 3, whiteSpace: 'nowrap' }}>
    {txt}{extra.length ? <span style={{ color: pal.textMuted, fontWeight: 400 }}>·{extra.join('·')}</span> : null}</span>
}

/** The KYUN rows with their ranks (a server with rank.py); null on an older server -> the plain chips. */
function rankedRows(c: ReadCard, pal: Palette): { k: string; dir: number; title: string; node: ReactNode }[] | null {
  const R = c.ranks
  if (!R || !c.w || !c.f) return null
  const w = c.w, f = c.f, chip = (k: string) => (c.chips ?? []).find((x) => x.k === k)
  const rows: { k: string; dir: number; title: string; node: ReactNode }[] = []
  if (w.cls === 'BLIND') rows.push({ k: 'LIKHNA', dir: 0, title: w.why ?? '', node: w.why ?? '—' })
  else rows.push({ k: 'LIKHNA', dir: R.likhna?.gated ? 0 : (c.votes?.writers ?? 0), title: 'aaj likha, nine strikes [M] · rank vs same time, other days',
    node: w.cls === 'PUT'                        // the read's own side first, so its rank is the one never clipped
      ? <>{R.likhna?.word ?? w.cls} · PE {lakh(w.pe)}<Rk r={R.pe} pal={pal} /> · CE {lakh(w.ce)}<Rk r={R.ce} pal={pal} /></>
      : <>{R.likhna?.word ?? w.cls} · CE {lakh(w.ce)}<Rk r={R.ce} pal={pal} /> · PE {lakh(w.pe)}<Rk r={R.pe} pal={pal} /></> })
  if (w.edge != null && rows.length) rows[0] = { ...rows[0], title: `the chain window's edge: the nine are read on ATM ±${w.edge} only`,
    node: <><span style={{ color: pal.caution }}>ATM±{w.edge} ? </span>{rows[0].node}</> }
  if (w.ce30 != null) {
    const d2 = (['ce', 'pe'] as const).map((s) => (c.wb?.[s] && !['?', 'naya OI nahi'].includes(c.wb[s]!.word)) ? `${s.toUpperCase()} ${c.wb[s]!.word} [I]` : null).filter(Boolean)
    rows.push({ k: '30 MIN', dir: Math.sign((w.pe30 ?? 0) - (w.ce30 ?? 0)), title: 'nine strikes, 30-min OI change [M]; writing vs buying = IV residual [I]',
      node: <>CE {lakh(w.ce30)}<Rk r={R.ce30} pal={pal} /> · PE {lakh(w.pe30)}<Rk r={R.pe30} pal={pal} />{d2.length ? ` · ${d2.join(' · ')}` : ''}</> })
  }
  const pr = chip('PRICE')
  if (pr) rows.push({ k: 'PRICE', dir: pr.dir, title: pr.v ?? '', node: pr.v ?? '—' })
  rows.push({ k: 'FLOW', dir: c.votes?.flow ?? 0, title: f.why ?? `CVD since the first tick [M]${f.gc ? `; to ${f.gc} GoCharting bars` : ''} · rank vs Upstox, same time`,
    node: f.cvd == null ? (f.why ?? '—') : <>CVD {sg(f.cvd)}<Rk r={R.cvd} pal={pal} /> · bech {fmt(f.sell)} / kharid {fmt(f.buy)}<Rk r={R.vol} pal={pal} />{f.gc ? ` · ${f.gc} tak GC` : ''}</> })
  const b = R.bar, o = R.foi40
  rows.push({ k: 'ABHI', dir: Math.sign(b?.raw ?? 0), title: `last closed ${b?.min ?? 5}-min bar's delta · 40-min CVD · 40-min futures OI [M]; delta needs GC and Upstox both ≥ p70, same sign`,
    node: <>{b?.min ?? 5}m Δ {sg(b?.raw)}<Rk r={b} pal={pal} /> · 40m {sg(R.cvd40?.raw)}<Rk r={R.cvd40} pal={pal} /> · OI {o?.raw == null ? '—' : `${o.raw > 0 ? '+' : ''}${o.raw.toFixed(2)}%`}{o?.word && o.word !== 'OI flat' ? ` ${o.word}` : ''}<Rk r={o} pal={pal} /></> })
  rows.push({ k: 'AAJ', dir: Math.sign(R.open?.raw ?? 0), title: `opening CVD ${R.open_t ?? ''} · VWAP crosses since 09:30 · the bar's volume [M]`,
    node: <>KHULA {sg(R.open?.raw)}<Rk r={R.open} pal={pal} /> · cross {R.x?.raw ?? '—'}<Rk r={R.x} pal={pal} /> · vol {fmt(R.bvol?.raw)}<Rk r={R.bvol} pal={pal} /></> })
  const jg = chip('JAGAH')
  if (c.jagah?.text) rows.push({ k: 'JAGAH', dir: c.dir ?? 0, node: c.jagah.text,
    title: `room ahead · obstacle behind · fuel · flow [I] — display only, never a probability${jg?.v ? ` · ${jg.v}` : ''}` })
  else if (jg) rows.push({ k: 'JAGAH', dir: jg.dir, title: jg.v ?? '', node: jg.v ?? '—' })
  return rows
}

/** COVERAGE in three typographies: "?" could not check (amber), "—" not shown (grey italic), "✓" checked, nothing. */
function Coverage({ rows, pal }: { rows?: CovRow[]; pal: Palette }) {
  const order = { cnc: 0, hidden: 1, none: 2, ok: 3 } as const
  const SRC = ['GC', 'CHAIN', 'FUT', 'UX', 'BASIS', 'RANK', 'D2', 'LEVELS', 'QUIT']     // what costs her most first
  const pri = (r: CovRow) => order[r.kind] * 100 + (SRC.indexOf(r.src) + 1 || 99)
  const shown = (rows ?? []).filter((r) => r.kind !== 'ok').sort((a, b) => pri(a) - pri(b))
  const all = (rows ?? []).map((r) => `${r.kind === 'cnc' ? '?' : r.kind === 'hidden' ? '—' : r.kind === 'none' ? '✓' : '·'} ${r.src}: ${r.text} [${r.tag}]`).join('\n')
  const strip = (t: string) => t.replace(/^could not check -- /, '').replace(/^not shown -- /, '')
  return (
    <span className="mono" title={all || 'coverage: nothing reported'} style={{ minWidth: 0, flex: '1 1 34%', ...clip }}>
      <span className="micro-label" style={{ marginRight: 6 }}>Coverage</span>
      {shown.length === 0 ? <span style={{ color: pal.textMuted }}>sab dikh raha</span> : shown.map((r, n) => (
        <span key={r.src + r.text} style={r.kind === 'cnc' ? { color: pal.caution } : r.kind === 'hidden'
          ? { color: pal.textMuted, fontStyle: 'italic' } : { color: pal.textMuted }}>
          {n ? ' · ' : ''}{r.kind === 'cnc' ? '? ' : r.kind === 'hidden' ? '— ' : '✓ '}{strip(r.text)}</span>))}
    </span>)
}

/** DIN, the One-Sided Meter (§1o): "DIN · TREND ▼ · neeche ka din · ▲3 ▼21 · mila-jula 18 · disha 88% · palte 1 ·
 *  VWAP cross 1", then one character per closed 5-min bar. "?" with the reason when it could not check. */
function DinRow({ o, pal }: { o?: OneSided | null; pal: Palette }) {
  if (o === undefined) return null                           // an older server: no meter yet
  const head = <span className="micro-label" style={{ marginRight: 6 }}>Din</span>
  if (!o || !o.type) return (
    <div className="mono" style={{ fontSize: 10.5, color: pal.caution, ...clip }}>{head}? — {o?.why ?? 'could not check'}</div>)
  const col = o.type === 'TREND ▲' ? pal.bull : o.type === 'TREND ▼' ? pal.bear : o.type === 'MIXED' ? pal.textSecondary : pal.accent
  const ch = (c: string) => (c === '▲' ? pal.bull : c === '▼' ? pal.bear : c === '?' ? pal.caution : pal.textMuted)
  return (
    <div className="mono" style={{ display: 'flex', alignItems: 'baseline', gap: 8, fontSize: 10.5, color: pal.textSecondary, minWidth: 0 }}
      title="THE ONE-SIDED METER (§1o, display only, UNTESTED): 7 votes per closed 5-min bar (delta · CVD 15m · VWAP · writers · writers 15m on one strike set · fut OI × price · peers), one-sided at 5+ · a COUNT, never a probability [I]">
      {head}
      <span style={{ fontWeight: 800, color: col, whiteSpace: 'nowrap' }}>{o.type}</span>
      <span style={{ fontSize: 9.5, padding: '0 5px', borderRadius: 3, border: `1px solid ${pal.border}`, background: pal.inset,
        color: pal.textPrimary, whiteSpace: 'nowrap' }}>{DIN_CHIP[o.type]}</span>
      <span style={{ whiteSpace: 'nowrap' }}>
        ▲{o.up} ▼{o.down} · mila-jula {o.mix}{o.unk ? ` · ? ${o.unk}` : ''} · disha {o.dom ?? '—'}{o.dom == null ? '' : '%'} · palte {o.flips} · VWAP cross {o.crosses}</span>
      {o.thin ? <span style={{ color: pal.caution, whiteSpace: 'nowrap' }}
        title="fut bars under 20 lots: one lot can swing a bar's delta vote — display only, the votes are unchanged">
        patla · {o.thin} bar &lt;20 lot · med {o.lots_med}</span> : null}
      <span style={{ letterSpacing: '-0.5px', minWidth: 0, ...clip }} title={`one per closed 5-min bar, 09:15 → ${o.last ?? '?'}: ▲ ▼ one-sided · · mila-jula · ? data missing`}>
        {(o.strip ?? '').split('').map((c, n) => <span key={n} style={{ color: ch(c) }}>{c}</span>)}</span>
    </div>)
}

/** DECODE, first in each card: the call line biggest, its signs as chips (the other side's muted), the <= 6 lines (A44: EFFORT last),
 *  the setups' live checks. "?" = could not check, never a zero. */
function DecodeBlock({ d, why, pal }: { d?: Decode | null; why?: string | null; pal: Palette }) {
  if (!d) return (
    <div className="mono" style={{ fontSize: 11, color: pal.textMuted, marginBottom: 3 }}>
      <span className="micro-label" style={{ marginRight: 8 }}>Decode</span>? — {why ?? 'server purana hai: restart karein'}</div>)
  const k = d.call.kind, ld = d.leg?.d ?? 0
  const col = k === 'THAK' ? dirCol(pal, -ld) : k === 'JAARI' ? dirCol(pal, ld) : k === 'MILA' ? pal.textSecondary : pal.textMuted
  const lg = d.leg
  const pt = (p: { t: string; fut: number; spot: number | null }) => `${fmt(p.spot)}s|${fmt(p.fut)}f ${p.t}`
  const chip: CSSProperties = { fontSize: 9.5, padding: '0 5px', borderRadius: 3, whiteSpace: 'nowrap', border: `1px solid ${pal.border}` }
  const tick = (v: boolean | null) => (v ? '✓' : v === false ? '✗' : '?')
  return (
    <div style={{ marginBottom: 3, paddingBottom: 2, borderBottom: `1px dashed ${pal.border}` }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <span className="micro-label">Decode</span>
        <span style={{ fontSize: 15, fontWeight: 800, color: col, whiteSpace: 'nowrap' }} title="a COUNT of the signs present, never a % [I]">{d.call.text}</span>
        {d.call.signs.map((x) => {
          const other = x.startsWith('jaari · ') || x.startsWith('thak · ')
          return <span key={x} className="mono" style={{ ...chip, color: other && k !== 'MILA' ? pal.textMuted : pal.textPrimary,
            background: other && k !== 'MILA' ? 'transparent' : pal.inset }}>{x}</span>
        })}
        <span className="mono" style={{ fontSize: 9.5, color: pal.textMuted, marginLeft: 'auto', whiteSpace: 'nowrap' }}
          title="the leg: start → extreme, spot|fut (spot = fut − the READ's basis [I])">
          {lg ? `leg ${lg.d > 0 ? '▲' : '▼'} ${pt(lg.start)} → ${pt(lg.ext)} · ` : ''}
          <span style={(d.age_s ?? 0) > STALE_S ? { color: pal.caution, fontWeight: 800 } : undefined}
            title={d.age_s == null ? undefined : `${Math.round(d.age_s / 60)} min purana`}>@{d.t ?? '?'}</span> [{d.tag}]</span>
      </div>
      <DinRow o={d.onesided} pal={pal} />
      <div className="mono" style={{ display: 'flex', flexWrap: 'wrap', columnGap: 14, fontSize: 10.5, color: pal.textSecondary, lineHeight: 1.4 }}>
        {d.lines.map((x) => <span key={x} style={{ whiteSpace: 'nowrap' }}>{x}</span>)}
        {d.setups.map((u) => (
          <span key={u.name} style={{ whiteSpace: 'nowrap', fontWeight: u.state === 'MATCH' || /^(line|lock) /.test(u.state) ? 800 : 500,
            color: u.state === '—' || /^(out|gave up) /.test(u.state) ? pal.textMuted : u.side === 'BUY' ? pal.bull : pal.bear }}
            title={u.state === 'MATCH' ? 'MATCH: the registered entry fired in this window · checks = the current close (display only)'
              : u.state === 'ARMED' ? 'ARMED: the location is live · checks = the current close'
              : u.state === '—' ? 'no live location: checks = the leg read now'
              : 'the entry under HOLD v2 at this close: line / lock = still held · out / gave up = exited, R on the stop (display only)'}>
            {u.name} {u.side}{Object.entries(u.checks).map(([kk, v]) => ` ${kk}${tick(v)}`).join('')} {u.state}
            {u.thin ? <span style={{ color: pal.caution }}> · {u.thin}</span> : null}</span>))}
      </div>
    </div>)
}

function Card({ idx, c, eng, pal }: { idx: IndexKey; c?: ReadCard; eng?: EngineRead; pal: Palette }) {
  // One ROW per index, the same columns on all three -- WORD | LINES | KYUN | TRADE + HUA -- so the three indices
  // line up cell for cell (she reads all three together), and the whole board fits 1245 x 720 without a scroll.
  const box: CSSProperties = { background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 6, minWidth: 0,
    padding: '4px 11px 3px' }
  if (!c || !c.ok) return (
    <div style={box}>
      {c && <DecodeBlock d={c.decode} why={c.decode_why} pal={pal} />}
      <div style={{ display: 'flex', gap: 14, alignItems: 'baseline' }}>
        <span style={{ fontWeight: 700, fontSize: 13 }}>{idx}</span>
        <span style={{ fontSize: 12, color: pal.textMuted }}>{c?.why ?? 'could not check — no read for this index'}</span>
      </div>
    </div>)
  const t = tone(pal, c.word, c.dir)
  const [gloss, todo] = GLOSS[`${c.word} ${c.dir}`] ?? ['', '']
  const vs = engineVsRead(eng?.ground, c.dir)
  const cell: CSSProperties = { padding: '1px 0', whiteSpace: 'nowrap' }
  const col: CSSProperties = { minWidth: 0 }
  const pd = (c.lines ?? []).filter((l) => l.k.startsWith('PD'))
  const futOk = c.basis_band ? c.basis_band.ok : true             // D6: an implausible basis prints no fut level
  const ranked = rankedRows(c, pal)
  return (
    <div style={{ ...box, borderLeft: `4px solid ${t.line}` }}>
      <DecodeBlock d={c.decode} why={c.decode_why} pal={pal} />
      <div style={{ display: 'grid', gridTemplateColumns: '214px 268px minmax(0, 1.4fr) minmax(0, 1fr)', gap: 14 }}>
        <div style={col}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
            <span style={{ fontWeight: 700, fontSize: 13, letterSpacing: '0.04em' }}>{idx}</span>
            <span className="mono" style={{ fontSize: 16, fontWeight: 600 }}>{fmt(c.spot, 1)}</span>
            <span className="mono" style={{ fontSize: 10, color: pal.textMuted, marginLeft: 'auto' }}>{c.spot_at}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <span style={{ fontSize: 21, fontWeight: 800, letterSpacing: '0.03em', padding: '2px 10px', borderRadius: 4, whiteSpace: 'nowrap',
              color: t.fg, background: t.bg, border: `1px solid ${t.line}` }}>{c.word}{c.arrow ? ` ${c.arrow}` : ''}
              {FF(c) && <span style={{ fontSize: 11, fontWeight: 700 }} title={`read-1.1: ${c.word_r1 ?? '?'} · FUEL + LEG FLOW saath`}>{FF(c)}</span>}</span>
            <div className="mono" style={{ fontSize: 10.5, color: pal.textSecondary, lineHeight: 1.35 }}>
              <div>since <b>{c.since ?? '—'}</b></div>
              <div>{c.agree != null ? `${c.agree}/3 saath · ` : ''}{c.changes ?? 0} badlav</div>
            </div>
          </div>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: t.line === pal.border ? pal.textSecondary : t.line, marginTop: 3, ...clip }}>{gloss}</div>
          <div style={{ fontSize: 11, color: pal.textSecondary, ...clip }}>{todo}</div>
          <div className="mono" style={{ fontSize: 10.5, marginTop: 2 }}><Votes v={c.votes} pal={pal} /></div>
        </div>

        <div style={col}>
          <Head pal={pal} tag={basisTag(c)} title={c.basis_band?.why ?? undefined}
            tone={c.basis_band && !c.basis_band.ok ? pal.caution : undefined}>LINES</Head>
          <table className="mono" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5, tableLayout: 'fixed' }}>
            <colgroup><col style={{ width: 38 }} /><col style={{ width: 56 }} /><col style={{ width: 56 }} /><col style={{ width: 36 }} /><col /></colgroup>
            <thead><tr style={{ color: pal.textMuted, fontSize: 9, textAlign: 'right' }}>
              <th></th><th style={{ fontWeight: 500 }}>SPOT</th><th style={{ fontWeight: 500 }}>FUT</th>
              <th style={{ fontWeight: 500 }}>DOOR</th><th></th>
            </tr></thead>
            <tbody>{(c.lines ?? []).filter((l) => !l.k.startsWith('PD')).map((l) => (
              <tr key={l.k} style={{ color: l.k === 'FLIP' ? pal.accent : pal.textPrimary }}>
                <td style={{ ...cell, fontWeight: 700 }}>{l.k}</td>
                <td style={{ ...cell, textAlign: 'right' }}>{fmt(l.spot)}</td>
                <td style={{ ...cell, textAlign: 'right', color: pal.textMuted }}
                  title={futOk ? undefined : c.basis_band?.why ?? undefined}>{futOk ? fmt(l.fut) : '?'}</td>
                <td style={{ ...cell, textAlign: 'right' }}>{l.gap}</td>
                <td style={{ ...cell, ...clip, paddingLeft: 6, fontSize: 10, color: pal.textMuted }} title={l.note}>{l.note}</td>
              </tr>))}</tbody>
          </table>
          {pd.length > 0 && (
            <div className="mono" style={{ fontSize: 10.5, color: pal.textSecondary, marginTop: 1, ...clip }}
              title="yesterday's high / low / close, index prices [M]">
              <span className="micro-label" style={{ marginRight: 6 }}>KAL</span>{pd.map((l) => `${l.k.slice(2)} ${fmt(l.spot)}`).join(' · ')}
            </div>)}
          {(c.hl?.spot || c.hl?.fut) && (
            <div className="mono" style={{ fontSize: 10.5, color: pal.textSecondary, marginTop: 1, ...clip }}
              title={`day high ${c.hl?.spot?.hi_t ?? '?'} / low ${c.hl?.spot?.lo_t ?? '?'} (spot: ${c.hl?.spot?.src ?? '?'}; fut: ${c.hl?.fut?.src ?? 'no ticks'}) [M] · range ÷ IV-priced day σ [I]`}>
              <span className="micro-label" style={{ marginRight: 6 }}>DIN</span>
              H {fmt(c.hl?.spot?.hi)}s|{fmt(c.hl?.fut?.hi)}f · L {fmt(c.hl?.spot?.lo)}s|{fmt(c.hl?.fut?.lo)}f
              {c.ranks?.scale?.range_sd != null && <> · {c.ranks.scale.range_sd.toFixed(1)}σd [I]</>}
            </div>)}
          {c.beyond && <div style={{ marginTop: 2, fontSize: 11, fontWeight: 700, color: pal.caution }}>spot FLIP ke paar — 5m close dekho</div>}
          {(c.warn ?? []).map((w) => <div key={w} style={{ marginTop: 1, fontSize: 10.5, color: pal.caution, ...clip }} title={w}>⚠ {w}</div>)}
        </div>

        <div style={col}>
          <Head pal={pal} tag={ranked ? `rank vs ${c.ranks?.kind === 'NORMAL' ? 'aam' : c.ranks?.kind} din, same time [M] · PRICE [I]`
            : 'LIKHNA · FLOW · JAGAH [M] · PRICE [I]'}>KYUN</Head>
          {ranked ? ranked.map((x) => (
            <div key={x.k} style={{ display: 'flex', gap: 8, fontSize: 11.5, lineHeight: 1.42 }}>
              <span className="micro-label" style={{ width: 50, flexShrink: 0 }}>{x.k}</span>
              <span className="mono" style={{ color: dirCol(pal, x.dir), ...clip }} title={x.title}>{x.node}</span>
            </div>)) : (c.chips ?? []).map((x) => (
            <div key={x.k} style={{ display: 'flex', gap: 8, fontSize: 11.5, lineHeight: 1.45 }}>
              <span className="micro-label" style={{ width: 50, flexShrink: 0 }}>{x.k}</span>
              <span className="mono" style={{ color: dirCol(pal, x.dir), ...clip }} title={x.v ?? ''}>{x.v ?? '—'}</span>
            </div>))}
        </div>

        <div style={col}>
          <Head pal={pal} tag={c.late ? '15:00 ke baad naya trade nahi' : 'LTP [M] · pick [I]'}>TRADE</Head>
          {(c.trade ?? []).length === 0
            ? <div style={{ fontSize: 11.5, color: pal.textMuted }}>koi trade nahi — {c.word === 'BAN RAHA' ? 'read ban raha hai' : 'read saaf hone do'}</div>
            : (c.trade ?? []).map((g) => (
              <div key={g.act + g.side + g.k} className="mono" style={{ display: 'flex', gap: 7, fontSize: 12, padding: '0.5px 0', alignItems: 'baseline' }}>
                <span style={{ width: 32, fontWeight: 800, color: g.act === 'BUY' ? pal.bull : pal.bear }}>{g.act}</span>
                <span style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>{fmt(g.k)} {g.side}</span>
                <span style={{ width: 52, textAlign: 'right' }}>{g.ltp == null ? '—' : g.ltp.toFixed(2)}</span>
                <span style={{ fontSize: 10, color: pal.textMuted, ...clip }} title={g.why}>{g.why}</span>
              </div>))}
          <div style={{ fontSize: 10.5, display: 'flex', gap: 8, ...clip }}>
            {c.expr && <span style={{ color: pal.textSecondary }}><span className="micro-label">EXPR</span> <b>{c.expr.word}</b></span>}
            {c.against && <span style={{ color: pal.bear }} title={c.against}>✕ {c.against}</span>}
          </div>
          <div style={{ marginTop: 2 }}><Head pal={pal} tag="[M] / [I]">HUA</Head></div>
          {(c.events ?? []).length === 0 ? <div style={{ fontSize: 11, color: pal.textMuted }}>checked, abhi tak kuch nahi hua</div>
            : (c.events ?? []).slice(-2).reverse().map((e) => (
              <div key={e.t + e.text} style={{ display: 'flex', gap: 7, fontSize: 11, padding: '0.5px 0' }}>
                <span className="mono" style={{ color: pal.textMuted, flexShrink: 0 }}>{e.t}</span>
                <span style={{ color: e.kind === 'QUIT' ? dirCol(pal, -e.dir) : e.kind === 'BREAK' ? pal.caution : pal.textPrimary, ...clip }}
                  title={e.text}>{e.text}</span>
              </div>))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 14, marginTop: 3, paddingTop: 2, borderTop: `1px dashed ${pal.border}`, fontSize: 10.5 }}>
        <span style={{ display: 'flex', gap: 6, minWidth: 0, flex: c.coverage ? '1 1 30%' : '1 1 50%', color: vs === 'khilaaf' ? pal.textMuted : pal.textSecondary }}
          title="the engine's grounded call -- [I], never the read">
          <span className="micro-label" style={{ flexShrink: 0 }}>Engine</span>
          {eng?.ground ? <>
            <span style={{ ...clip, opacity: vs === 'khilaaf' ? 0.6 : 1 }} title={eng.ground.text}>{eng.ground.text}</span>
            {vs && <b style={{ flexShrink: 0, color: vs === 'khilaaf' ? pal.textMuted : dirCol(pal, c.dir) }}>
              {vs === 'khilaaf' ? '· read ke khilaaf · chup' : '· read ke saath'}</b>}
          </> : <span>engine ka call nahi aaya</span>}
        </span>
        <span className="mono" style={{ minWidth: 0, flex: c.coverage ? '1 1 36%' : '1 1 50%', color: pal.textSecondary, ...clip }}
          title={(c.blind ?? []).join(' · ') || 'the held words today and the spot move inside each'}>
          <span className="micro-label" style={{ marginRight: 6 }}>Din</span>
          {(c.day ?? []).map((s, n) => (
            <span key={s.from + s.word}>{n ? ' · ' : ''}{s.from} <b style={{ color: dirCol(pal, s.dir) }}>{s.word}</b> {s.move > 0 ? '+' : ''}{s.move}</span>))}
        </span>
        {c.coverage && <Coverage rows={c.coverage} pal={pal} />}
      </div>
    </div>)
}

export default function ReadTab({ reads }: { reads: Partial<Record<IndexKey, EngineRead>> }) {
  const pal = usePalette()
  const { data, err } = useRead()
  return (
    <div style={{ padding: '5px 16px 0' }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'baseline', marginBottom: 3, fontSize: 10.5, color: pal.textSecondary }}>
        <span style={{ fontWeight: 800, letterSpacing: '0.06em', color: pal.textPrimary }}>THE READ</span>
        <span>ek read, jab tak FLIP na toote · OI pehle, phir price, phir flow</span>
        <span className="mono" style={{ marginLeft: 'auto', color: pal.textMuted }}>
          {data?.live ? `live ${data.asof}` : data?.day ?? ''}{data?.rev ? ` · ${data.rev}` : ''}</span>
      </div>
      {err && <div style={{ marginBottom: 6, fontSize: 12, fontWeight: 600, color: pal.caution, background: wash(pal.caution, 0.1),
        padding: '4px 9px', borderRadius: 4 }}>could not check — {err}</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {ORDER.map((i) => <Card key={i} idx={i} c={data?.indices?.[i]} eng={reads[i]} pal={pal} />)}
      </div>
    </div>)
}

/** The ANSWER band's top line on every other tab: the held read in one row. */
export function ReadLine({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const { data, err } = useRead()
  const c = data?.indices?.[index]
  if (!c || !c.ok) return (
    <div style={{ fontSize: 12, color: pal.textMuted, marginBottom: 6 }}><span className="micro-label" style={{ marginRight: 8 }}>The read</span>
      could not check — {err ?? c?.why ?? 'no read yet'}</div>)
  const t = tone(pal, c.word, c.dir)
  const flip = (c.lines ?? []).find((l) => l.k === 'FLIP' || l.k === 'TOP')
  const t1 = (c.lines ?? []).find((l) => l.k === 'T1' || l.k === 'BOTTOM')
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 12.5, marginBottom: 6 }}>
      <span className="micro-label">The read</span>
      <span style={{ fontWeight: 800, padding: '1px 9px', borderRadius: 3, color: t.fg, background: t.bg, border: `1px solid ${t.line}` }}>
        {c.word}{c.arrow ? ` ${c.arrow}` : ''}{FF(c)}</span>
      <span className="mono" style={{ color: pal.textSecondary }}>since {c.since ?? '—'}</span>
      {flip && <span className="mono">{flip.k} <b style={{ color: pal.accent }}>{fmt(flip.spot)}</b> <span style={{ color: pal.textMuted }}>fut {fmt(flip.fut)}</span></span>}
      {t1 && <span className="mono">{t1.k} <b>{fmt(t1.spot)}</b> <span style={{ color: pal.textMuted }}>fut {fmt(t1.fut)}</span></span>}
      {c.beyond && <span style={{ color: pal.caution, fontWeight: 700 }}>FLIP ke paar — 5m close dekho</span>}
      {c.ranks && (() => {                           // the read's evidence with its size (rank.py), on every tab
        const R = c.ranks, side = c.w?.cls === 'CALL' ? R.ce : c.w?.cls === 'PUT' ? R.pe : null
        return <span className="mono" style={{ fontSize: 11, color: pal.textSecondary }}
          title="rank vs other days at the same time [M] · details on the Read tab">
          {R.likhna?.word ?? ''}{side && <Rk r={side} pal={pal} />}
          {' · '}{R.bar?.min ?? 5}m Δ {sg(R.bar?.raw)}<Rk r={R.bar} pal={pal} />
          {' · '}KHULA {sg(R.open?.raw)}<Rk r={R.open} pal={pal} />
        </span>
      })()}
    </div>)
}
