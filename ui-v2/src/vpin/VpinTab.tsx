import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { usePalette, rgbOf } from '../theme'
import type { IndexKey } from '../data'
import { useTape } from '../trade/tape'

/* ── VPIN ─────────────────────────────────────────────────────────────────────
   Ordered 2026-09-23: "vpin ka ek tab daal de ... when move happens with good
   flow it really tells if the move is sustaining."

   THAT SENTENCE IS THE BRIEF, and it is not what the old toolb panel drew.
   toolb showed toxicity ALONE — a gauge, four bands, a percentile line. But
   "is this move sustaining" is a question about TWO series: what price did,
   and whether one-sided informed flow was behind it. A VPIN reading with no
   price beside it cannot answer it, and a trader reading the gauge on its own
   has to hold the price in their head and pair the two by eye.

   So this tab draws both on one clock and says which of four things the pair
   is doing. Every one of those readings is [I] and is a DESCRIPTION OF TWO
   MEASURED SERIES — never a prediction, never an instruction:

     price moving + VPIN rising  -> one-sided flow is behind the move
     price moving + VPIN flat    -> the move is running without flow behind it
     price flat   + VPIN rising  -> pressure building, nothing has broken yet
     price flat   + VPIN low     -> two-sided, quiet

   WHAT THIS TAB MUST NEVER DO. VPIN here is SHADOW and `[I]` — the module
   stamps both on every row it writes, and a 30-session kill clock is still
   running on it. toolb's panel printed "Desk Gate rule: NO NEW RISK" off a
   high reading; that is the seller's gate's word, the gate is a different
   object with its own inputs, and a shadow module must not impersonate it.
   Nothing here refuses anything or sizes anything.

   ONLY NIFTY-FUT CARRIES A GAUGE. The other two indices get a sentence saying
   so, not an empty chart.

   THE REBUILT MORNING IS NEVER BLENDED. `/api/vpin` puts backfilled buckets in
   front, cut off at the first live bucket, because these are VOLUME-time
   buckets and buckets counted off 1-minute bars do not align with buckets
   counted off 0.5 s frames. They are drawn faint and dashed and counted apart.
─────────────────────────────────────────────────────────────────────────────── */

type Point = { t: string | null; imb: number | null; vpin: number | null; pct: number | null; backfill?: boolean; src?: string | null }
type State = { vpin: number | null; pct: number | null; buckets: number; fill: number; resets: number; bucket_v: number; window: number; tag?: string; shadow?: boolean }
type Reply = {
  ok: boolean
  day?: string
  inst?: string
  /** null = the log could not be read. [] = read, no completed bucket yet. */
  series?: Point[] | null
  state?: Record<string, State>
  tag?: string
  shadow?: boolean
  seeded_from_backfill?: boolean
  backfill?: { n: number; why: string | null; method: string; note: string }
  /** THE FAST LINE: the same tape through a smaller volume bucket, its own
   *  gauge, its own log, its own population. Percentiles from the two are
   *  comparable as SHAPES and not as numbers — see vpin.FAST_BUCKET_V. */
  fast_inst?: string
  fast_bucket_v?: number
  fast_series?: Point[] | null
  fast_why?: string | null
}

/** The gauge only exists for this instrument; vpin.py attaches to one. */
const GAUGED = 'NIFTY'
/** A percentile needs a population; below this the module refuses to rank. */
const WARM_BUCKETS = 10
/** The window the sustaining read is taken over. Minutes. */
const LOOK_MIN = 30
/** Price has to have gone somewhere to be called "moving": a fraction of the
 *  day's own range, so NIFTY and BANKNIFTY read alike without a per-index
 *  table nobody would maintain.
 *  ponytail: the day's range GROWS, so this bar rises through the session — a
 *  40-pt half-hour reads as "moving" at 10:00 and as ordinary at 14:00. On
 *  2026-09-22 that put the 14:00 leg (-42 pts against a 47-pt bar) on the
 *  quiet side of the line. Deliberate for now: a fixed points threshold would
 *  need one number per index and would drift with volatility instead. Revisit
 *  with a rolling 30-minute range percentile if she says it reads wrong. */
const MOVE_FRAC = 0.25
/** VPIN percentile has to have travelled this far to be called "rising". */
const RISE_PCT = 0.15

const mins = (t: string | null | undefined) => { const m = /^(\d{1,2}):(\d{2})/.exec(t ?? ''); return m ? +m[1] * 60 + +m[2] : null }
const hhmm = (v: number) => `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`
const tHM = (ms: number) => { const s = (Math.floor(ms / 1000) + 19800) % 86400; return hhmm(Math.floor(s / 60)) }
const pctTxt = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)}%`)
const n4 = (v: number | null | undefined) => (v == null ? '—' : v.toFixed(4))
const compact = (v: number | null | undefined) => (v == null ? '—' : v >= 1e5 ? `${(v / 1e5).toFixed(1)}L` : v.toLocaleString('en-IN'))

export default function VpinTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const wash = (token: string, a: number) => `rgba(${rgbOf(token)},${a})`
  const hot = '#E86A5A', calm = '#3CC8A8'
  // The fast line needs its own hue, and hue here means LINE, not side — the
  // side convention belongs to the Board. Lavender is used nowhere else.
  const fastCol = '#9B8CE8'

  const [rep, setRep] = useState<Reply | null>(null)
  const [why, setWhy] = useState<string | null>('abhi padha ja raha hai')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/vpin?idx=${index}`); const j = await r.json()
        if (!alive) return
        setRep(j as Reply); setWhy(null)
      } catch (e) { if (alive) { setRep(null); setWhy(`backend ne jawab nahi diya (${String(e)})`) } }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 15000)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])

  const tape = useTape(index)
  const gcBars = tape.reply?.bars ?? []
  const uxBars = (tape.reply?.ux?.bars ?? []) as unknown as typeof gcBars
  const bars = gcBars.length ? gcBars : uxBars
  const priceSrc = gcBars.length ? 'GoCharting [M]' : uxBars.length ? 'Upstox tape [I]' : null

  const st: State | null = rep?.state ? (rep.state[rep.inst ?? 'NIFTY-FUT'] ?? null) : null
  const stFast: State | null = rep?.state && rep.fast_inst ? (rep.state[rep.fast_inst] ?? null) : null
  const series: Point[] | null | undefined = rep?.series
  const pts = useMemo(() => (series ?? []).filter(p => p.pct != null && mins(p.t) != null), [series])
  const fastPts = useMemo(() => (rep?.fast_series ?? []).filter(p => p.pct != null && mins(p.t) != null), [rep?.fast_series])
  const live = pts.filter(p => !p.backfill)
  const bf = pts.filter(p => !!p.backfill)
  // The read leans on whichever line HAS a rank, and says which. Early in the
  // session that is the fast one; that is the whole point of it existing.
  const readPts = fastPts.length ? fastPts : pts
  const readSt = fastPts.length ? stFast : st
  const readName = fastPts.length ? `fast (${compact(rep?.fast_bucket_v)})` : `slow (${compact(st?.bucket_v)})`

  // ── the four-way read: what the two series did over the last LOOK_MIN ─────
  const sustain = useMemo(() => {
    if (index !== GAUGED) return null
    if (!readPts.length || !bars.length) return null
    const now = readPts[readPts.length - 1]
    const nowM = mins(now.t)!
    const then = [...readPts].reverse().find(p => (mins(p.t) ?? 0) <= nowM - LOOK_MIN) ?? readPts[0]
    const dPct = (now.pct ?? 0) - (then.pct ?? 0)

    const inWin = bars.filter(b => (mins(tHM(b.t)) ?? 0) >= nowM - LOOK_MIN)
    if (inWin.length < 2) return null
    const dPx = inWin[inWin.length - 1].c - inWin[0].o
    const dayHi = Math.max(...bars.map(b => b.h)), dayLo = Math.min(...bars.map(b => b.l))
    const range = Math.max(dayHi - dayLo, 1e-9)
    const moved = Math.abs(dPx) >= MOVE_FRAC * range
    const rising = dPct >= RISE_PCT
    const high = (now.pct ?? 0) >= 0.65
    const dir = dPx > 0 ? 'up' : 'down'

    const head = moved
      ? (rising || high ? 'FLOW IS BEHIND THIS MOVE' : 'MOVE WITHOUT FLOW BEHIND IT')
      : (rising || high ? 'PRESSURE BUILDING, NOTHING BROKEN YET' : 'TWO-SIDED AND QUIET')
    const body = moved
      ? (rising || high
        ? `Price ${dir} ${Math.abs(dPx).toFixed(0)} pts in ${LOOK_MIN}m and toxicity ${rising ? `rose ${pctTxt(dPct)}` : `is high at ${pctTxt(now.pct)}`}. One-sided aggression is paying up to get filled, and the people quoting are on the wrong side of it.`
        : `Price ${dir} ${Math.abs(dPx).toFixed(0)} pts in ${LOOK_MIN}m while toxicity ${dPct < -RISE_PCT ? `fell ${pctTxt(-dPct)}` : 'barely moved'} and sits at ${pctTxt(now.pct)}. Nobody informed is paying for this one.`)
      : (rising || high
        ? `Price has gone ${Math.abs(dPx).toFixed(0)} pts in ${LOOK_MIN}m — nothing — while toxicity ${rising ? `rose ${pctTxt(dPct)}` : `sits at ${pctTxt(now.pct)}`}. Size is being worked into a level that is still holding.`
        : `Price ${Math.abs(dPx).toFixed(0)} pts in ${LOOK_MIN}m and toxicity at ${pctTxt(now.pct)}. Both sides are being served.`)
    return { head, body, tone: moved && (rising || high) ? hot : !moved && !(rising || high) ? calm : pal.accent }
  }, [readPts, bars, index, pal.accent])

  // ── band for the gauge; the same four the module's own percentile implies ──
  const band = (p: number | null | undefined) =>
    p == null ? { word: 'PATA NAHI', col: pal.textMuted }
      : p >= 0.80 ? { word: 'HIGH', col: hot }
        : p >= 0.65 ? { word: 'ELEVATED', col: pal.accent }
          : p <= 0.35 ? { word: 'CALM', col: calm }
            : { word: 'NORMAL', col: pal.textSecondary }

  // ── geometry: percentile and price on one clock ───────────────────────────
  const W = 1000, H = 260, PL = 8, PR = 62, PT = 10, PH = 190
  const OPEN = 9 * 60 + 15, CLOSE = 15 * 60 + 30
  const X = (m: number) => PL + (m - OPEN) / (CLOSE - OPEN) * (W - PL - PR)
  const YP = (v: number) => PT + (1 - v) * PH                       // percentile 0..1
  const lo = bars.length ? Math.min(...bars.map(b => b.l)) : 0
  const hi = bars.length ? Math.max(...bars.map(b => b.h)) : 1
  const YX = (p: number) => PT + (hi - p) / Math.max(hi - lo, 1e-9) * PH

  const line = `1px solid ${pal.border}`
  const S: Record<string, CSSProperties> = {
    root: { display: 'grid', gridTemplateRows: 'auto auto 1fr', height: 'calc(100vh - 96px)', minHeight: 640, color: pal.textPrimary, fontSize: 13 },
    rail: { display: 'flex', alignItems: 'center', gap: 16, padding: '6px 14px', borderBottom: line, fontSize: 11, color: pal.textMuted },
    lbl: { fontSize: 11, color: pal.textMuted, letterSpacing: '.06em', textTransform: 'uppercase' },
    panel: { padding: '10px 14px', borderBottom: line, minHeight: 0 },
    hole: { color: pal.textMuted },
    kv: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px 18px', fontSize: 11, marginTop: 8 },
  }
  const kv = (k: string, v: string, tag?: 'M' | 'I') => (
    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: line, padding: '2px 0' }}>
      <span style={{ color: pal.textMuted }}>{k}</span>
      <span>{v}{tag ? <span style={{ color: pal.textMuted, fontSize: 9 }}> [{tag}]</span> : null}</span>
    </div>)

  // ── the absences, one sentence each, never collapsed ──────────────────────
  const absence =
    index !== GAUGED ? `${index} pe VPIN naapa hi nahi jaata — gauge sirf ${GAUGED}-FUT par lagi hai.`
      : !rep ? (why ?? 'jawab nahi aaya')
        : series === null && rep.fast_series === null ? 'dono forward log padhe nahi ja sake — yeh "check nahi kar paye" hai, "koi bucket nahi" nahi.'
          : !readPts.length && readSt && (readSt.pct == null || readSt.vpin == null)
            ? `dono line garam ho rahi hain — fast ${stFast?.buckets ?? 0}/${WARM_BUCKETS}, slow ${st?.buckets ?? 0}/${WARM_BUCKETS}. Rank karne ke liye itne bucket chahiye.`
            : !readPts.length ? 'log padhe gaye, aaj abhi tak ek bhi poora bucket nahi bana.'
              : null

  const b = band(st?.pct)
  const bf2 = band(stFast?.pct)

  /** One gauge column. Two of these sit side by side so the fast line and the
   *  slow line are read as two measurements, never as one number. */
  const gauge = (title: string, sub: string, s: State | null, col: { word: string; col: string }) => (
    <div>
      <div style={S.lbl}>{title}</div>
      <div style={{ fontSize: 34, fontWeight: 600, lineHeight: 1.05, color: col.col, fontVariantNumeric: 'tabular-nums' }}>
        {s?.pct == null ? '—' : `${Math.round(s.pct * 100)}%`}
      </div>
      <div style={{ fontSize: 11, color: col.col, fontWeight: 500, letterSpacing: '.06em' }}>{col.word}</div>
      <div style={{ height: 5, background: wash(pal.textPrimary, 0.08), marginTop: 6 }}>
        <div style={{ height: '100%', width: `${Math.min(100, (s?.pct ?? 0) * 100)}%`, background: col.col }} />
      </div>
      <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 4 }}>
        {sub}{s?.pct == null ? ` · ${s?.buckets ?? 0}/${WARM_BUCKETS} buckets` : ` · ${s.buckets} buckets · fill ${pctTxt(s.fill)}`}
      </div>
    </div>)

  return (
    <div style={S.root}>
      <div style={S.rail}>
        <span style={{ fontSize: 15, color: pal.textPrimary, fontFamily: 'Roboto Mono, monospace' }}>{rep?.inst ?? `${GAUGED}-FUT`} · {rep?.day ?? '—'}</span>
        <span style={{ border: `1px dashed ${pal.textMuted}`, padding: '0 5px' }}>{rep?.tag ?? '[I]'} SHADOW — kuch rokta nahi, koi size nahi deta</span>
        <span>bucket {compact(st?.bucket_v)} contracts · window {st?.window ?? '—'}</span>
        <span>resets {st?.resets ?? '—'}</span>
        <span style={{ marginLeft: 'auto' }}>
          rank population: {rep?.seeded_from_backfill ? 'live + rebuilt buckets' : 'live buckets only'}
          {bf.length ? ` · ${bf.length} rebuilt point${bf.length > 1 ? 's' : ''} drawn apart` : ''}
        </span>
      </div>

      <div style={{ ...S.panel, display: 'grid', gridTemplateColumns: '190px 190px 1fr', gap: 18, alignItems: 'start' }}>
        {gauge('FAST · percentile', `bucket ${compact(rep?.fast_bucket_v)}`, stFast, bf2)}
        {gauge('SLOW · percentile', `bucket ${compact(st?.bucket_v)}`, st, b)}

        <div>
          <div style={S.lbl}>Move sustain kar raha hai? · last {LOOK_MIN}m · [I]</div>
          {absence ? <div style={{ ...S.hole, marginTop: 4 }}>{absence}</div>
            : sustain ? (
              <>
                <div style={{ fontSize: 20, fontWeight: 600, margin: '2px 0 4px', color: sustain.tone }}>{sustain.head}</div>
                <div style={{ fontSize: 12, color: pal.textSecondary, lineHeight: 1.45 }}>{sustain.body}</div>
                <div style={{ fontSize: 11, color: pal.textMuted, marginTop: 6 }}>
                  Padha gaya <b style={{ color: pal.textSecondary, fontWeight: 500 }}>{readName}</b> line par. Yeh do naapi hui series ka varnan hai, bhavishyavani nahi. Price {priceSrc ?? 'source nahi'} se, toxicity {rep?.tag ?? '[I]'} shadow gauge se. Koi trade nahi bol raha.
                </div>
              </>
            ) : <div style={S.hole}>price aur toxicity dono ka {LOOK_MIN}m window abhi nahi bana</div>}
        </div>
      </div>

      <div style={{ ...S.panel, borderBottom: 0, overflow: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 }}>
          <span style={{ ...S.lbl, marginRight: 'auto' }}>Toxicity aur price, ek hi ghadi par</span>
          <span style={{ fontSize: 10, color: fastCol }}>— fast {compact(rep?.fast_bucket_v)} [I]</span>
          <span style={{ fontSize: 10, color: pal.accent }}>— slow {compact(st?.bucket_v)} [I]</span>
          <span style={{ fontSize: 10, color: pal.textSecondary }}>— price {priceSrc ?? '(nahi)'}</span>
          {bf.length ? <span style={{ fontSize: 10, color: pal.textMuted }}>- - rebuilt buckets, alag gine gaye</span> : null}
        </div>
        {!pts.length && !fastPts.length ? <div style={{ ...S.hole, padding: 12 }}>{absence ?? 'abhi koi point nahi'}</div> : (
          <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={230} style={{ fontFamily: 'Roboto Mono, monospace', fontSize: 10 }}>
            {[0.35, 0.65, 0.8].map(y => (
              <g key={y}>
                <line x1={PL} x2={W - PR} y1={YP(y)} y2={YP(y)} stroke={wash(pal.textPrimary, 0.08)} strokeDasharray="2 4" />
                <text x={W - PR + 4} y={YP(y) + 3} fill={pal.textMuted} fontSize={9}>{y}</text>
              </g>))}
            {bars.length > 0 && (
              <polyline points={bars.map(x => `${X(mins(tHM(x.t))!)},${YX(x.c)}`).join(' ')}
                fill="none" stroke={pal.textSecondary} strokeWidth={1.1} opacity={0.75} />
            )}
            {bf.length > 0 && (
              <polyline points={bf.map(p => `${X(mins(p.t)!)},${YP(p.pct!)}`).join(' ')}
                fill="none" stroke={pal.accent} strokeWidth={1.2} strokeDasharray="3 3" opacity={0.5} />
            )}
            {live.length > 0 && (
              <polyline points={live.map(p => `${X(mins(p.t)!)},${YP(p.pct!)}`).join(' ')}
                fill="none" stroke={pal.accent} strokeWidth={1.6} />
            )}
            {fastPts.length > 0 && (
              <polyline points={fastPts.map(p => `${X(mins(p.t)!)},${YP(p.pct!)}`).join(' ')}
                fill="none" stroke={fastCol} strokeWidth={1.1} opacity={0.9} />
            )}
            {live.filter(p => (p.pct ?? 0) >= 0.8).map((p, i) => (
              <circle key={i} cx={X(mins(p.t)!)} cy={YP(p.pct!)} r={2.2} fill={hot} />
            ))}
            {['09:15', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '15:30'].map(h => (
              <text key={h} x={X(mins(h)!)} y={PT + PH + 14} fill={pal.textMuted} fontSize={9} textAnchor="middle">{h}</text>
            ))}
            {bars.length > 0 && <text x={W - PR + 4} y={YX(bars[bars.length - 1].c) + 3} fill={pal.textSecondary} fontSize={9}>{bars[bars.length - 1].c}</text>}
          </svg>)}

        <div style={S.kv}>
          {kv('VPIN fast', n4(stFast?.vpin), 'I')}
          {kv('VPIN slow', n4(st?.vpin), 'I')}
          {kv('fast points', `${fastPts.length}`, 'M')}
          {kv('slow points', `${live.length} live${bf.length ? ` · ${bf.length} rebuilt` : ''}`, 'M')}
          {kv('fast last imb', n4(fastPts.length ? fastPts[fastPts.length - 1].imb : null), 'M')}
          {kv('slow last imb', n4(pts.length ? pts[pts.length - 1].imb : null), 'M')}
          {kv('last mark', (fastPts.length ? fastPts[fastPts.length - 1].t : pts.length ? pts[pts.length - 1].t : null) ?? '—', 'M')}
          {kv('seeded into rank', rep?.seeded_from_backfill ? 'yes' : 'no', 'M')}
        </div>
        {rep?.fast_why ? <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 6 }}>fast line: {rep.fast_why}</div> : null}
        <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 6 }}>
          Do alag population hain. Fast bucket {compact(rep?.fast_bucket_v)}, slow {compact(st?.bucket_v)} — percentile aapas mein number ke taur par mat milana, sirf shakal milana. Fast jaldi bolti hai aur zyada shor karti hai; slow der se bolti hai aur sthir hai.
        </div>
        {rep?.backfill?.why ? <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 6 }}>rebuilt morning: {rep.backfill.why} · {rep.backfill.method} · {rep.backfill.note}</div> : null}
        <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 6 }}>
          VPIN shadow hai aur uska kill clock abhi chal raha hai. Yeh panel kuch block nahi karta, koi size nahi deta, koi rate nahi chhapta.
        </div>
      </div>
    </div>
  )
}
