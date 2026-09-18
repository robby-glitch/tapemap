import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { usePalette, rgbOf } from '../theme'
import type { IndexKey } from '../data'

/* ── FLOW ─────────────────────────────────────────────────────────────────────
   The day's ORDER FLOW on a time axis, served by /api/day/record (record_read.py
   streams data/frame/frame_<day>.jsonl). Nothing else in this app draws the
   events against the clock: Events lists them, Trade balloons the recent ones on
   the chart, and neither shows the SHAPE of a session.

   Two facts decide the whole rendering:

   1. THE AXIS IS THE SESSION, NOT THE RECORD. The extension replays GoCharting's
      loaded footprint when the tab opens late, so a file whose first frame landed
      at 09:50 still carries events stamped 09:15 (measured 2026-09-18: 2,060
      rows from 09:50, 40 events from 09:15). Drawing from the first row's time
      would silently amputate the morning. The axis is fixed 09:15→15:30 and the
      price line starts where the record starts, with that gap named in words.

   2. AGREEMENT WITH A LEVEL IS THE STRONGEST THING THIS BRAIN CAN SAY. An event
      with `at` non-null happened AT a named level; it is drawn in brass — the
      palette's one structure hue — larger, and stemmed to the axis. An event
      with no level is ink. Kind is carried by SHAPE, so no reader has to hold a
      colour key in their head, and no hue picks up a second meaning.

   What this screen refuses: no hit rate, no win rate, no expectancy, no
   confidence — and no direction verdict. A cluster of events is a cluster of
   events; whether it is bullish is not a thing this panel is allowed to say, so
   `bull`/`bear` are never reached for here. The three absences stay three
   sentences: could-not-read, read-and-empty-rows, read-and-empty-events.
─────────────────────────────────────────────────────────────────────────────── */

type EventKind = 'absorption' | 'exhaustion' | 'trap' | 'climax' | 'vacuum' | 'initiative'

type FlowEvent = { t: string; kind: string; p: number | null; at: string | null }
type FlowRecRow = {
  t: string | null
  state: string | null
  fire: boolean
  signal: string | null
  visit: string | null
  gate: string | null
  z: number | null
  px: number | null
  missing: string[]
}
type Payload = {
  ok: boolean
  day?: string
  idx?: string
  rows?: FlowRecRow[]
  events?: FlowEvent[]
  rows_why?: string | null
  events_why?: string | null
  error?: string
}

const wash = (token: string, alpha: number | string) => `rgba(${rgbOf(token)},${alpha})`

// The session, in minutes past midnight. Fixed: 09:15 open, 15:30 close.
const OPEN = 9 * 60 + 15
const CLOSE = 15 * 60 + 30
const SPAN = CLOSE - OPEN

/** "HH:MM" → minutes, or null. A time this cannot read is dropped, never
 *  coerced to 0 — an event at midnight would land on the open. */
function mins(t: string | null | undefined): number | null {
  if (!t) return null
  const m = /^(\d{1,2}):(\d{2})$/.exec(t.trim())
  if (!m) return null
  const v = +m[1] * 60 + +m[2]
  return Number.isFinite(v) ? v : null
}

const hhmm = (v: number) => `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`
const px1 = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 1 })

// ── Geometry, in the SVG's own coordinate space ──────────────────────────────
// A fixed viewBox scaled to the container: uniform, so a square stays square at
// any width, and no ResizeObserver is needed to keep the marks honest.
const VB_W = 1200, VB_H = 400
const PAD_L = 58, PAD_R = 16, PAD_T = 16
const PLOT_H = 264
const AXIS_Y = PAD_T + PLOT_H              // the time axis
const BAND_Y = AXIS_Y + 44                 // the machine band, under the axis
const BAND_H = 18
const W = VB_W - PAD_L - PAD_R

const xOf = (m: number) => PAD_L + ((m - OPEN) / SPAN) * W

/** The six kinds, each a shape. Order is the legend's order. */
const KINDS: EventKind[] = ['absorption', 'exhaustion', 'trap', 'climax', 'vacuum', 'initiative']

/** One marker. Shape carries the kind; colour carries only whether the event
 *  landed on a named level. `s` is the half-size. */
function Mark({ kind, x, y, s, color, strong }: {
  kind: string; x: number; y: number; s: number; color: string; strong: boolean
}) {
  const sw = strong ? 1.6 : 1.2
  switch (kind) {
    case 'absorption':                                   // square — a wall that ate it
      return <rect x={x - s} y={y - s} width={s * 2} height={s * 2} fill={color} />
    case 'exhaustion':                                   // filled circle
      return <circle cx={x} cy={y} r={s} fill={color} />
    case 'vacuum':                                       // hollow circle — nothing there
      return <circle cx={x} cy={y} r={s} fill="none" stroke={color} strokeWidth={sw} />
    case 'trap':                                         // diamond
      return <path d={`M${x} ${y - s * 1.25}L${x + s * 1.25} ${y}L${x} ${y + s * 1.25}L${x - s * 1.25} ${y}Z`} fill={color} />
    case 'climax':                                       // asterisk — three crossed strokes
      return (
        <g stroke={color} strokeWidth={sw} strokeLinecap="round">
          <line x1={x - s * 1.3} y1={y} x2={x + s * 1.3} y2={y} />
          <line x1={x - s * 0.65} y1={y - s * 1.13} x2={x + s * 0.65} y2={y + s * 1.13} />
          <line x1={x - s * 0.65} y1={y + s * 1.13} x2={x + s * 0.65} y2={y - s * 1.13} />
        </g>
      )
    case 'initiative':                                   // plus
      return (
        <g stroke={color} strokeWidth={sw * 1.4} strokeLinecap="round">
          <line x1={x - s * 1.2} y1={y} x2={x + s * 1.2} y2={y} />
          <line x1={x} y1={y - s * 1.2} x2={x} y2={y + s * 1.2} />
        </g>
      )
    default:                                             // a kind this build has never seen
      return <circle cx={x} cy={y} r={s * 0.7} fill="none" stroke={color} strokeWidth={sw} strokeDasharray="1.5 1.5" />
  }
}

/** How far along the machine was, as ink alpha. Deliberately hueless: green and
 *  red are direction and brass is structure, and "the tool was ARMED" is
 *  neither. A state this build does not know (PATA NAHI included) is hatched
 *  instead of shaded — not knowing is not a low reading. */
const STATE_INK: Record<string, number> = {
  WAITING: 0.10, ARMED: 0.30, TRIGGERED: 0.62, IN_TRADE: 0.42,
}

export default function FlowTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const [pay, setPay] = useState<Payload | null>(null)
  /** Why nothing could be read, in the source's own words. Distinct from an
   *  empty record: see the branches below. */
  const [why, setWhy] = useState<string | null>(null)
  const [hover, setHover] = useState<FlowEvent | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/day/record?idx=${index}`)
        const j: Payload = await r.json()
        if (!alive) return
        if (!j.ok) { setWhy(j.error || 'the server did not say why'); setPay(null); return }
        setWhy(null); setPay(j)
      } catch (e) {
        // The backend not answering is "could not check", not "no flow today".
        if (alive) { setWhy(`the backend did not answer (${String(e)})`); setPay(null) }
      }
    }
    // The first read always happens: this component is mounted only while its
    // tab is the active one, so being here IS the request. The guard belongs on
    // the REPEAT only — put on the first load it hangs the panel at "reading…"
    // whenever the page is painted while backgrounded (measured: a preview pane
    // reports document.hidden true the whole time).
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 30000)
    // Cleared here, and the tab unmounting is what calls this — App renders
    // FlowTab only while Flow is the active tab, so no poll outlives the view.
    return () => { alive = false; window.clearInterval(id) }
  }, [index])

  const rows = pay?.rows ?? []
  const events = pay?.events ?? []

  const g = useMemo(() => {
    // In-session only. The record keeps being written after the close (rows ran
    // to 21:00 on 2026-09-18), and those rows belong to no point on this axis.
    const inRow = rows.filter(r => { const m = mins(r.t); return m != null && m >= OPEN && m <= CLOSE })
    const outRow = rows.length - inRow.length
    const inEv = events.filter(e => { const m = mins(e.t); return m != null && m >= OPEN && m <= CLOSE })
    const outEv = events.length - inEv.length

    const prices = [
      ...inRow.map(r => r.px).filter((v): v is number => typeof v === 'number'),
      ...inEv.map(e => e.p).filter((v): v is number => typeof v === 'number'),
    ]
    // Events are priced too, so the domain covers them: an event drawn off the
    // top of the plot is an event the operator cannot see.
    let lo = prices.length ? Math.min(...prices) : 0
    let hi = prices.length ? Math.max(...prices) : 1
    if (hi - lo < 1e-9) { lo -= 1; hi += 1 }
    const pad = (hi - lo) * 0.06
    lo -= pad; hi += pad
    const yOf = (p: number) => PAD_T + ((hi - p) / (hi - lo)) * PLOT_H

    // ONE POINT PER MINUTE, the last price recorded in it. The record is written
    // per signature change, so a busy minute holds many rows — measured
    // 2026-09-18: 1,957 in-session rows across 152 distinct minutes, up to 49 in
    // one minute, spread as wide as 34 points. Drawn raw at minute resolution
    // those stack into vertical hairballs and the SHAPE of the day disappears
    // behind them, which is the one thing this line is here for.
    const perMin = new Map<number, number>()
    for (const r of inRow) {
      const m = mins(r.t)
      if (m == null || typeof r.px !== 'number') continue
      perMin.set(m, r.px)                      // file order, so the last wins
    }
    const pts = [...perMin.entries()].sort((a, b) => a[0] - b[0])
    // Broken wherever the record has no frame for a while — measured on the same
    // day, two holes of 38 and 36 minutes. A straight line across those would be
    // a price this file invented.
    const GAP = 5
    const segs: string[] = []
    let cur: string[] = []
    let holes = 0, longestHole = 0
    for (let i = 0; i < pts.length; i++) {
      const [m, p] = pts[i]
      const jump = i > 0 ? m - pts[i - 1][0] : 0
      if (jump > GAP) {
        holes++
        longestHole = Math.max(longestHole, jump)
        if (cur.length > 1) segs.push(cur.join(' '))
        cur = []
      }
      cur.push(`${xOf(m).toFixed(1)},${yOf(p).toFixed(1)}`)
    }
    if (cur.length > 1) segs.push(cur.join(' '))

    // Consecutive same-state rows coalesced into runs — 1,957 rects would be
    // 1,957 DOM nodes for 20 visible blocks.
    type Run = { state: string | null; a: number; b: number }
    const runs: Run[] = []
    for (const r of inRow) {
      const m = mins(r.t)
      if (m == null) continue
      const last = runs[runs.length - 1]
      if (last && last.state === r.state) last.b = m
      else runs.push({ state: r.state, a: m, b: m })
    }
    // Each run reaches the next one's start, so the band has no false gaps.
    for (let i = 0; i < runs.length - 1; i++) runs[i].b = Math.max(runs[i].b, runs[i + 1].a)

    const firstRowT = inRow.find(r => mins(r.t) != null)?.t ?? null

    return { inRow, outRow, inEv, outEv, lo, hi, yOf, segs, runs, firstRowT, minutes: pts.length, holes, longestHole }
  }, [rows, events])

  // Hour ticks plus both ends of the session.
  const ticks = useMemo(() => {
    const out = [OPEN]
    for (let m = 10 * 60; m < CLOSE; m += 60) out.push(m)
    out.push(CLOSE)
    return out
  }, [])

  const priceTicks = useMemo(() => {
    const out: number[] = []
    for (let i = 0; i <= 4; i++) out.push(g.lo + ((g.hi - g.lo) * i) / 4)
    return out
  }, [g.lo, g.hi])

  const card: CSSProperties = {
    background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
  }
  const note: CSSProperties = { fontSize: 11.5, color: pal.textMuted, lineHeight: 1.55 }

  // ── Could not check ────────────────────────────────────────────────────────
  if (why) {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Header index={index} pay={pay} />
        <div style={{ ...card, border: `1px solid ${pal.caution}`, padding: 20, fontSize: 13, color: pal.caution }}>
          The day's record could not be read — {why}.
          <div style={{ marginTop: 6, fontSize: 12, color: pal.textSecondary }}>
            This is not "no flow today": nothing was checked. The record is{' '}
            <span className="mono">data/frame/frame_&lt;day&gt;.jsonl</span>, served by{' '}
            <span className="mono">/api/day/record</span>.
          </div>
        </div>
      </div>
    )
  }
  if (!pay) {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Header index={index} pay={pay} />
        <div style={{ ...card, padding: 20, fontSize: 13, color: pal.textMuted }}>reading the day's record…</div>
      </div>
    )
  }

  const noRows = g.inRow.length === 0
  const noEvents = g.inEv.length === 0
  const hatch = `flowHatch-${index}`

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <Header index={index} pay={pay} />

      {/* ── Hover readout — time, kind, price, level ──────────────────────── */}
      <div style={{
        ...card, padding: '8px 14px', minHeight: 34, display: 'flex', alignItems: 'center',
        gap: 14, fontSize: 12.5, color: hover ? pal.textPrimary : pal.textMuted,
      }}>
        {hover ? (
          <>
            <span className="mono" style={{ fontWeight: 600 }}>{hover.t}</span>
            <span style={{ fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{hover.kind}</span>
            <span className="mono">{typeof hover.p === 'number' ? px1(hover.p) : '—'}</span>
            <span style={{ color: hover.at ? pal.accent : pal.textMuted }}>
              {hover.at ?? 'no named level — the record logged none for this event'}
            </span>
          </>
        ) : (
          <span>Hover an event for its time, kind, price and level.</span>
        )}
      </div>

      {/* ── The drawing ──────────────────────────────────────────────────── */}
      <div style={{ ...card, padding: '14px 10px 10px' }}>
        <svg viewBox={`0 0 ${VB_W} ${VB_H}`} style={{ width: '100%', height: 'auto', display: 'block' }}
          role="img" aria-label={`Order flow for ${pay.idx ?? index} on ${pay.day ?? 'today'}, 09:15 to 15:30`}>
          <defs>
            <pattern id={hatch} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke={wash(pal.ink, 0.22)} strokeWidth="1.6" />
            </pattern>
          </defs>

          {/* price gridlines + labels */}
          {(!noRows || !noEvents) && priceTicks.map((p, i) => (
            <g key={`py-${i}`}>
              <line x1={PAD_L} y1={g.yOf(p)} x2={VB_W - PAD_R} y2={g.yOf(p)}
                stroke={wash(pal.ink, 0.05)} strokeWidth={1} />
              <text x={PAD_L - 8} y={g.yOf(p) + 3.5} textAnchor="end" fontSize={10} fill={pal.textMuted}>
                {px1(Math.round(p * 10) / 10)}
              </text>
            </g>
          ))}

          {/* time axis */}
          <line x1={PAD_L} y1={AXIS_Y} x2={VB_W - PAD_R} y2={AXIS_Y} stroke={wash(pal.ink, 0.14)} strokeWidth={1} />
          {ticks.map(m => (
            <g key={`t-${m}`}>
              <line x1={xOf(m)} y1={PAD_T} x2={xOf(m)} y2={AXIS_Y} stroke={wash(pal.ink, 0.05)} strokeWidth={1} />
              <text x={xOf(m)} y={AXIS_Y + 16} textAnchor="middle" fontSize={10} fill={pal.textMuted}>{hhmm(m)}</text>
            </g>
          ))}

          {/* price line — context behind the events, never a chart replacement */}
          {g.segs.map((pts, i) => (
            <polyline key={`seg-${i}`} points={pts} fill="none" stroke={pal.textPrimary}
              strokeWidth={1} strokeOpacity={0.55} strokeLinejoin="round" />
          ))}

          {/* events */}
          {g.inEv.map((e, i) => {
            const m = mins(e.t)
            if (m == null || typeof e.p !== 'number') return null
            const x = xOf(m), y = g.yOf(e.p)
            const level = !!e.at
            const color = level ? pal.accent : pal.textSecondary
            return (
              <g key={`e-${i}-${e.t}-${e.kind}`}
                onMouseEnter={() => setHover(e)} onMouseLeave={() => setHover(null)}
                style={{ cursor: 'default' }}>
                {/* A stem to the axis: an event that agreed with a named level
                    is the strongest read here, so it carries weight a bare mark
                    cannot. */}
                {level && <line x1={x} y1={y} x2={x} y2={AXIS_Y} stroke={pal.accent} strokeWidth={0.8} strokeOpacity={0.35} />}
                <Mark kind={e.kind} x={x} y={y} s={level ? 6 : 4} color={color} strong={level} />
                {/* Generous invisible hit area — the marks are small on purpose. */}
                <circle cx={x} cy={y} r={10} fill="transparent" />
                <title>{`${e.t} · ${e.kind} · ${px1(e.p)}${e.at ? ` · ${e.at}` : ' · no named level'}`}</title>
              </g>
            )
          })}

          {/* machine band */}
          <text x={PAD_L - 8} y={BAND_Y + BAND_H / 2 + 3.5} textAnchor="end" fontSize={10} fill={pal.textMuted}>machine</text>
          <rect x={PAD_L} y={BAND_Y} width={W} height={BAND_H} fill="none" stroke={wash(pal.ink, 0.10)} strokeWidth={1} />
          {g.runs.map((r, i) => {
            const a = xOf(r.a)
            const w = Math.max(1.2, xOf(r.b) - a)
            const ink = r.state ? STATE_INK[r.state] : undefined
            const label = r.state ?? 'no state recorded'
            return (
              <g key={`run-${i}`}>
                <rect x={a} y={BAND_Y} width={w} height={BAND_H}
                  fill={ink == null ? `url(#${hatch})` : wash(pal.ink, ink)} />
                {w > 52 && (
                  <text x={a + w / 2} y={BAND_Y + BAND_H / 2 + 3.5} textAnchor="middle" fontSize={9}
                    fill={ink != null && ink > 0.45 ? pal.card : pal.textSecondary}
                    letterSpacing="0.06em">
                    {label}
                  </text>
                )}
                <title>{`${hhmm(r.a)}–${hhmm(r.b)} · ${label}`}</title>
              </g>
            )
          })}

          {/* ── The absences, printed where the drawing would be ───────────
              A record with no rows and a record whose every row falls after
              the close are two different findings, and the second one is not
              rare: the frame file keeps being written all evening. Collapsing
              them into "no rows" would be this panel's own invention, since
              the backend's `rows_why` is correctly null when rows exist. */}
          {noRows && (
            <text x={PAD_L + 10} y={PAD_T + PLOT_H / 2 - 8} fontSize={13} fill={pal.caution}>
              {rows.length === 0
                ? `No price line: ${pay.rows_why ?? 'the record returned no rows and did not say why'}.`
                : `No price line: all ${rows.length} recorded row${rows.length === 1 ? '' : 's'} fall outside 09:15–15:30.`}
            </text>
          )}
          {noEvents && (
            <text x={PAD_L + 10} y={PAD_T + PLOT_H / 2 + (noRows ? 16 : -8)} fontSize={13} fill={pal.caution}>
              {events.length === 0
                ? `No events: ${pay.events_why ?? 'the record returned no events and did not say why'}.`
                : `No events on this axis: all ${events.length} recorded event${events.length === 1 ? '' : 's'} fall outside 09:15–15:30.`}
            </text>
          )}
          {noRows && (
            <text x={PAD_L + 10} y={BAND_Y + BAND_H / 2 + 3.5} fontSize={11} fill={pal.textMuted}>
              no machine state recorded for this day
            </text>
          )}
        </svg>
      </div>

      {/* ── Legend: shape → kind, and what brass means ───────────────────── */}
      <div style={{ ...card, padding: '12px 14px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 18 }}>
        {KINDS.map(k => (
          <span key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 11.5, color: pal.textSecondary }}>
            <svg width={18} height={18} viewBox="0 0 18 18" aria-hidden="true">
              <Mark kind={k} x={9} y={9} s={5} color={pal.textSecondary} strong={false} />
            </svg>
            {k}
          </span>
        ))}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 11.5, color: pal.accent, marginLeft: 'auto' }}>
          <svg width={18} height={18} viewBox="0 0 18 18" aria-hidden="true">
            <line x1={9} y1={8} x2={9} y2={17} stroke={pal.accent} strokeWidth={0.9} strokeOpacity={0.5} />
            <Mark kind="exhaustion" x={9} y={8} s={6} color={pal.accent} strong />
          </svg>
          brass + stem = it happened AT a named level
        </span>
      </div>

      {/* ── What the drawing does and does not claim ─────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, ...note }}>
        <span>
          The axis is the SESSION, 09:15–15:30 — never the record's own first row. The extension
          replays the chart's loaded footprint, so events reach back before this process started.
          {g.firstRowT && (mins(g.firstRowT) ?? OPEN) > OPEN
            ? ` The price line starts at ${g.firstRowT}, the first frame on file; there is no recorded price before it and none is drawn.`
            : ''}
        </span>
        <span>
          {g.inEv.length} event{g.inEv.length === 1 ? '' : 's'} drawn, {g.inEv.filter(e => e.at).length} of them at a named level.
          {g.outEv > 0 ? ` ${g.outEv} fell outside 09:15–15:30 and are not on this axis.` : ''}
          {g.outRow > 0 ? ` ${g.outRow} record row${g.outRow === 1 ? '' : 's'} sit outside the session window and are not drawn.` : ''}
        </span>
        {g.minutes > 0 && <span>
          The line is the LAST price recorded in each minute — {g.minutes} minute
          {g.minutes === 1 ? '' : 's'} out of {g.inRow.length} row{g.inRow.length === 1 ? '' : 's'}, because the record is
          written per signature change and a busy minute holds dozens.
          {g.holes > 0
            ? ` It is broken across ${g.holes} stretch${g.holes === 1 ? '' : 'es'} where no frame was recorded at all (longest ${g.longestHole} minutes); a line drawn through those would be invented.`
            : ''}
        </span>}
        <span>
          The band is what the MACHINE was saying, not what the flow meant. No hit rate, win rate or
          expectancy is shown here, and no direction is read off a cluster — this panel draws what
          happened and when, and stops there.
        </span>
      </div>
    </div>
  )
}

function Header({ index, pay }: { index: IndexKey; pay: Payload | null }) {
  const pal = usePalette()
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
      <span className="micro-label">Flow — the day's order flow on the clock</span>
      <span className="mono" style={{ fontSize: 11, color: pal.textMuted }}>
        {pay?.idx ?? index} · {pay?.day ?? 'today'} · 09:15–15:30
      </span>
    </div>
  )
}
