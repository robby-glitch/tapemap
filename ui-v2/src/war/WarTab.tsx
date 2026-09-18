import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { usePalette, rgbOf } from '../theme'
import type { IndexKey } from '../data'

/* ── WAR ──────────────────────────────────────────────────────────────────────
   The OI battlefield drawn OVER TIME, from /api/oihist. Every other OI screen
   in this app shows the book as it stands right now — a ladder, a heat row, a
   pair of bars. A ladder cannot say WHEN a wall was built, and it cannot say
   that a wall is a ruin: a front holding 1.1M that once held 11.5M reads
   identically to a front that never grew past 1.1M. That difference is the
   whole point of this tab.

   Four facts decide the rendering:

   1. `k` IS OI CHANGE SINCE THE OPEN, not OI. So the band's thickness is
      ground TAKEN today, and it can go negative — nine of NIFTY's 34
      strike-sides were below their own open when this was written. A negative
      change is not a thin band, it is no band: the fill clamps at zero and the
      rail says the number.

   2. THE PEAK MUST BE COMPUTED HERE, from the minute series. The payload's
      `peak[]` is peak ABSOLUTE OI (23,300 PE: 4.8M) while `k` is CHANGE
      (16.5M at 14:27) — different units, and `peak[]` carries no time at all.
      Blending the two would draw an outline that means nothing. The outline is
      the RUNNING MAX of the change series, so it never shrinks and it survives
      a hole in the record.

   3. THE AXIS IS THE SESSION, 09:15→15:30, never the record's first minute,
      and a hole in the record is a hole. Measured 2026-09-18, twice, minutes
      apart: at 21:46 the route answered 146 minutes starting 09:50 with three
      holes in the middle (135, 57 and 5 minutes) and nothing rebuilt; at 21:51
      it answered 385 minutes from 09:15 with those same holes filled, 239 of
      them tagged `backfill`. Both readings are correct and the map must be
      correct on either: drawing from the first row would have claimed the
      morning was flat, painting through a hole would have invented 135 minutes
      of wall-building, and blending the rebuilt minutes into the observed ones
      would have hidden which of the two readings you are looking at.

   4. PROVENANCE IS WEIGHT, NEVER HUE. A minute tagged `src:"backfill"` is the
      same measurement with weaker provenance, so it is drawn at reduced alpha
      in its own colour. A second hue would make a rebuilt minute look like a
      different kind of fact.

   Colour follows the app, not this file: CE is the bear hue and PE the bull
   hue, the same pairing GlassBoard's CE/PE split bar and the Chain legend
   already use. Brass stays structure — the named levels and the cursor.

   What this screen refuses: no hit rate, no win rate, no expectancy, no
   confidence — and no direction verdict. "PE building under spot" is a fact;
   what it means for the next hour is the operator's call, not this panel's.
   And every word lives in the rail. The previous war map put its labels on the
   map and became unreadable at fourteen dots.
─────────────────────────────────────────────────────────────────────────────── */

type MinuteRow = {
  spot?: number | null
  k?: Record<string, unknown>
  px?: Record<string, unknown>
  src?: string | null
}
type Payload = {
  ok: boolean
  idx?: string
  why?: string | null
  minutes?: Record<string, MinuteRow> | null
  peak?: unknown[]
  error?: string
}
type WarLevel = { kind?: string; px?: number; tag?: string; label?: string }

const wash = (token: string, alpha: number | string) => `rgba(${rgbOf(token)},${alpha})`

// The session, in minutes past midnight. Fixed: 09:15 open, 15:30 close.
const OPEN = 9 * 60 + 15
const CLOSE = 15 * 60 + 30
const SPAN = CLOSE - OPEN
/** A break of more than this many minutes is a hole in the record, not a
 *  quiet stretch. Painted through, a hole becomes wall-building that never
 *  happened. Same threshold the Flow tab breaks its price line on. */
const GAP = 5

function mins(t: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(t.trim())
  if (!m) return null
  const v = +m[1] * 60 + +m[2]
  return Number.isFinite(v) ? v : null
}
const hhmm = (v: number) => `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`
const inr = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
/** Lakhs / thousands, the same scale App.tsx's ladder prints OI in. Sign-safe:
 *  a strike below its own open reads "−3.2L", never "0". */
function fmtOI(n: number): string {
  const a = Math.abs(n)
  if (a >= 1e5) return `${(n / 1e5).toFixed(1)}L`
  if (a >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return `${Math.round(n)}`
}

// ── Geometry, in the SVG's own coordinate space ──────────────────────────────
// Fixed viewBox scaled to the container, as the Flow tab does: uniform scaling,
// no ResizeObserver, and a band that is half as thick is half as thick at any
// window width.
const VB_W = 1220, VB_H = 820
const PAD_L = 66          // price gutter
const PAD_R = 178         // named-level label gutter
const PAD_T = 16
// 740, not the ~400 a strip chart would take: the band thickness a front can
// reach is a fraction of the row, and the row is a fraction of the plot. At 566
// the largest front on the measured day rendered 14.2px thick and the ruin
// inside it 0.8px, which is legible but cramped; at 740 the same pair is 18.5
// and 1.0. The tab's content area scrolls, and a map is worth a scroll.
const PLOT_H = 740
const AXIS_Y = PAD_T + PLOT_H
const W = VB_W - PAD_L - PAD_R
const xOf = (m: number) => PAD_L + ((m - OPEN) / SPAN) * W

type Side = 'ce' | 'pe'
/** What is HELD, over one stretch that is contiguous in time and uniform in
 *  provenance — provenance splits the fill because weight is how a rebuilt
 *  minute declares itself. */
type Run = { d: string; rebuilt: boolean }
/** The HIGH-WATER MARK over one contiguous stretch. Split only where the record
 *  has a hole, never by provenance: the crest is drawn at one weight whatever
 *  minute set it, so splitting it would only add seams. `wash` is the ground
 *  once held, `edge` the contour alone — two paths, because ONE stroked area
 *  path closes itself down to the spine at both ends and so prints a bright
 *  vertical bar inside the band at every join. Seen at 2.9x in the browser
 *  2026-09-18, nine bars per front: the trench line is the top edge, not a box. */
type Crest = { wash: string; edge: string }
type Front = {
  k: number
  y: number
  side: Side
  runs: Run[]
  crests: Crest[]
  now: number
  peak: number
  peakT: number | null
  off: number            // fraction below the peak, 0 when at it
}

/** Area path from a run's top edge back along the strike's own spine. A
 *  one-minute run still gets a sliver rather than vanishing — a minute of
 *  record is a minute of record. */
function area(pts: Array<[number, number]>, yBase: number): string {
  if (pts.length === 0) return ''
  if (pts.length === 1) {
    const [x, y] = pts[0]
    return `M${(x - 0.7).toFixed(1)},${yBase.toFixed(1)}L${(x - 0.7).toFixed(1)},${y.toFixed(1)}L${(x + 0.7).toFixed(1)},${y.toFixed(1)}L${(x + 0.7).toFixed(1)},${yBase.toFixed(1)}Z`
  }
  const body = pts.map(([x, y]) => `L${x.toFixed(1)},${y.toFixed(1)}`).join('')
  const first = pts[0][0], last = pts[pts.length - 1][0]
  return `M${first.toFixed(1)},${yBase.toFixed(1)}${body}L${last.toFixed(1)},${yBase.toFixed(1)}Z`
}

/** The same edge as an open line — no closing run back to the spine. */
function edge(pts: Array<[number, number]>): string {
  if (pts.length === 0) return ''
  if (pts.length === 1) {
    const [x, y] = pts[0]
    return `M${(x - 0.7).toFixed(1)},${y.toFixed(1)}L${(x + 0.7).toFixed(1)},${y.toFixed(1)}`
  }
  return pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join('')
}

export default function WarTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const [pay, setPay] = useState<Payload | null>(null)
  /** Why nothing could be READ. Distinct from a route that answered with an
   *  empty day — see the branches below. */
  const [why, setWhy] = useState<string | null>(null)
  const [levels, setLevels] = useState<WarLevel[] | null>(null)
  const [levelsWhy, setLevelsWhy] = useState<string | null>(null)
  const [hoverK, setHoverK] = useState<number | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/oihist?idx=${index}`)
        const j: Payload = await r.json()
        if (!alive) return
        if (!j.ok) { setWhy(j.error || j.why || 'the server did not say why'); setPay(null) }
        else { setWhy(null); setPay(j) }
      } catch (e) {
        // The backend not answering is "could not check", not "no war today".
        if (alive) { setWhy(`the backend did not answer (${String(e)})`); setPay(null) }
      }
      // The levels are a second, independent question. The map does not depend
      // on them, so a war map that fails leaves the battlefield standing and
      // says so in the rail.
      try {
        const r = await fetch(`/api/warmap?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        const ls = j?.indices?.[index]?.levels
        if (Array.isArray(ls)) { setLevels(ls as WarLevel[]); setLevelsWhy(null) }
        else { setLevels(null); setLevelsWhy(j?.why || 'the war map returned no levels for this index') }
      } catch (e) {
        if (alive) { setLevels(null); setLevelsWhy(`the war map did not answer (${String(e)})`) }
      }
    }
    // The first read always happens. This component is mounted only while its
    // tab is active, so being here IS the request; the hidden-guard belongs on
    // the REPEAT only. Put on the first load it hangs the panel at "reading…"
    // whenever the page is painted while backgrounded — the bug the Flow tab
    // hit, and the reason this comment exists twice in the tree.
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 30000)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])

  // ── One build per fetch. Hover never re-enters this. ───────────────────────
  const g = useMemo(() => {
    const raw = pay?.minutes ?? {}
    const all = Object.keys(raw)
    const stamped = all
      .map(t => ({ t, m: mins(t) }))
      .filter((r): r is { t: string; m: number } => r.m != null)
    const inSession = stamped.filter(r => r.m >= OPEN && r.m <= CLOSE).sort((a, b) => a.m - b.m)
    const outside = stamped.length - inSession.length
    const unreadable = all.length - stamped.length

    const rebuiltAt = inSession.map(r => raw[r.t]?.src === 'backfill')
    const rebuilt = rebuiltAt.filter(Boolean).length
    const firstObserved = inSession.find((_, i) => !rebuiltAt[i])?.m ?? null

    // Strike universe: every strike the day ever carried, so a strike that
    // stopped being quoted keeps its row instead of silently closing ranks.
    const strikeSet = new Set<number>()
    for (const r of inSession) {
      for (const key of Object.keys(raw[r.t]?.k ?? {})) {
        const n = Number(key)
        if (Number.isFinite(n)) strikeSet.add(n)
      }
    }
    const strikes = [...strikeSet].sort((a, b) => a - b)

    const spots = inSession
      .map(r => raw[r.t]?.spot)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v))

    // Price domain: the strikes and the spot both have to fit, padded by a
    // little over half a strike step so the outermost bands are not clipped.
    const step = strikes.length > 1
      ? Math.min(...strikes.slice(1).map((k, i) => k - strikes[i]).filter(d => d > 0))
      : 50
    const pool = [...strikes, ...spots]
    let lo = pool.length ? Math.min(...pool) : 0
    let hi = pool.length ? Math.max(...pool) : 1
    lo -= step * 0.7; hi += step * 0.7
    if (hi - lo < 1e-9) { lo -= 1; hi += 1 }
    const yOf = (p: number) => PAD_T + ((hi - p) / (hi - lo)) * PLOT_H
    const rowH = (PLOT_H * step) / (hi - lo)
    // 0.46 of the row, so two neighbouring fronts at full strength leave a
    // hairline between them instead of merging into one slab.
    const MAXHALF = Math.max(2, rowH * 0.46)

    // Value at each in-session minute, per strike per side. Missing strike in
    // a minute → null, which breaks the run rather than reading as zero.
    const val: Record<string, Array<number | null>> = {}
    for (const k of strikes) { val[`${k}ce`] = []; val[`${k}pe`] = [] }
    for (const r of inSession) {
      const row = raw[r.t]?.k ?? {}
      for (const k of strikes) {
        const cell = (row as Record<string, unknown>)[String(k)]
        const ok = Array.isArray(cell) && cell.length >= 2
        const ce = ok && typeof cell[0] === 'number' && Number.isFinite(cell[0]) ? (cell[0] as number) : null
        const pe = ok && typeof cell[1] === 'number' && Number.isFinite(cell[1]) ? (cell[1] as number) : null
        val[`${k}ce`].push(ce)
        val[`${k}pe`].push(pe)
      }
    }

    // Scale: one thickness scale for the whole map, taken from the largest
    // high-water mark on it. Per-strike scaling would make every front look
    // equally strong, which is the lie a ladder already tells.
    let vmax = 0
    const runmax: Record<string, number[]> = {}
    for (const key of Object.keys(val)) {
      let run = 0
      runmax[key] = val[key].map(v => { if (v != null && v > run) run = v; return run })
      vmax = Math.max(vmax, run)
    }
    const half = (v: number) => (vmax > 0 ? (Math.max(0, v) / vmax) * MAXHALF : 0)

    const fronts: Front[] = []
    for (const k of strikes) {
      const yBase = yOf(k)
      for (const side of ['ce', 'pe'] as Side[]) {
        const key = `${k}${side}`
        const series = val[key]
        const rm = runmax[key]
        const up = side === 'ce'
        const runs: Run[] = []
        const crests: Crest[] = []
        let fillPts: Array<[number, number]> = []
        let peakPts: Array<[number, number]> = []
        let runRebuilt = rebuiltAt[0] ?? false
        const flushFill = () => {
          if (fillPts.length) runs.push({ d: area(fillPts, yBase), rebuilt: runRebuilt })
          fillPts = []
        }
        const flushCrest = () => {
          if (peakPts.length) crests.push({ wash: area(peakPts, yBase), edge: edge(peakPts) })
          peakPts = []
        }
        for (let i = 0; i < inSession.length; i++) {
          const v = series[i]
          const gapBroke = i > 0 && inSession[i].m - inSession[i - 1].m > GAP
          const provBroke = i > 0 && rebuiltAt[i] !== rebuiltAt[i - 1]
          if (v == null) { flushFill(); flushCrest(); continue }
          if (gapBroke) { flushFill(); flushCrest() }
          else if (provBroke && fillPts.length) {
            // Carry the boundary minute into the next run so the two weights
            // meet exactly instead of leaving a 1px seam. The crest runs
            // straight through — it carries only one weight.
            const tail = fillPts[fillPts.length - 1]
            flushFill()
            fillPts.push(tail)
          }
          if (fillPts.length === 0) runRebuilt = rebuiltAt[i]
          const x = xOf(inSession[i].m)
          const hf = half(v), hp = half(rm[i])
          fillPts.push([x, up ? yBase - hf : yBase + hf])
          peakPts.push([x, up ? yBase - hp : yBase + hp])
        }
        flushFill(); flushCrest()

        // Where it topped out, and how far it has fallen back.
        let peak = 0, peakT: number | null = null, now = 0
        for (let i = 0; i < series.length; i++) {
          const v = series[i]
          if (v == null) continue
          now = v
          if (v > peak) { peak = v; peakT = inSession[i].m }
        }
        fronts.push({ k, y: yBase, side, runs, crests, now, peak, peakT, off: peak > 0 ? 1 - Math.max(0, now) / peak : 0 })
      }
    }

    // Spot, broken on the same holes the fronts are.
    const spotSegs: string[] = []
    let cur: string[] = []
    let holes = 0, longestHole = 0
    for (let i = 0; i < inSession.length; i++) {
      const s = raw[inSession[i].t]?.spot
      const jump = i > 0 ? inSession[i].m - inSession[i - 1].m : 0
      if (jump > GAP) {
        holes++; longestHole = Math.max(longestHole, jump)
        if (cur.length > 1) spotSegs.push(cur.join(' '))
        cur = []
      }
      if (typeof s !== 'number' || !Number.isFinite(s)) { if (cur.length > 1) spotSegs.push(cur.join(' ')); cur = []; continue }
      cur.push(`${xOf(inSession[i].m).toFixed(1)},${yOf(s).toFixed(1)}`)
    }
    if (cur.length > 1) spotSegs.push(cur.join(' '))

    // The two largest high-water marks on the map. Everything else is marked
    // but not named — fourteen anonymous labels is what made the last one
    // unreadable.
    const ranked = [...fronts].filter(f => f.peak > 0).sort((a, b) => b.peak - a.peak)

    return {
      inSession, outside, unreadable, rebuilt, firstObserved, strikes, step, lo, hi, yOf,
      rowH, fronts, ranked, spotSegs, holes, longestHole, vmax,
      spotNow: spots.length ? spots[spots.length - 1] : null,
      first: inSession.length ? inSession[0].m : null,
      last: inSession.length ? inSession[inSession.length - 1].m : null,
    }
  }, [pay])

  // Named levels that actually fall on this map, their gutter labels pushed
  // apart so two rules at neighbouring prices do not print on top of each
  // other. Cheap, and re-run only when the levels or the domain change.
  const rules = useMemo(() => {
    if (!levels) return []
    const picked = levels
      .filter(l => typeof l.px === 'number' && (l.px as number) >= g.lo && (l.px as number) <= g.hi)
      .sort((a, b) => (b.px as number) - (a.px as number))
    let lastY = -Infinity
    return picked.map(l => {
      const y = g.yOf(l.px as number)
      const ly = Math.max(y, lastY + 12.5)
      lastY = ly
      return { y, ly, px: l.px as number, label: l.label || `${l.kind ?? 'level'} ${inr(l.px as number)}`, kind: l.kind ?? '' }
    })
  }, [levels, g.lo, g.hi, g.yOf])

  const card: CSSProperties = { background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12 }
  const note: CSSProperties = { fontSize: 11.5, color: pal.textMuted, lineHeight: 1.55 }
  const hueOf = (s: Side) => (s === 'ce' ? pal.bear : pal.bull)

  // ── Could not check ─────────────────────────────────────────────────────────
  if (why) {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Header index={index} pay={pay} g={null} />
        <div style={{ ...card, border: `1px solid ${pal.caution}`, padding: 20, fontSize: 13, color: pal.caution }}>
          The OI history could not be read — {why}.
          <div style={{ marginTop: 6, fontSize: 12, color: pal.textSecondary }}>
            This is not "no fronts today": nothing was checked. The map is served by{' '}
            <span className="mono">/api/oihist?idx={index}</span>.
          </div>
        </div>
      </div>
    )
  }
  if (!pay) {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Header index={index} pay={pay} g={null} />
        <div style={{ ...card, padding: 20, fontSize: 13, color: pal.textMuted }}>reading the day's OI history…</div>
      </div>
    )
  }

  const empty = g.inSession.length === 0 || g.strikes.length === 0
  const hovered = hoverK == null ? [] : g.fronts.filter(f => f.k === hoverK)
  // Named on the map: the two largest, plus whatever row the cursor is on.
  const namedPeaks = [
    ...g.ranked.slice(0, 2),
    ...hovered.filter(f => f.peak > 0 && !g.ranked.slice(0, 2).some(r => r.k === f.k && r.side === f.side)),
  ].filter(f => f.peakT != null)
  // Drop-line times, spread so three labels in the same ten minutes stay legible.
  const dropLabels: Array<{ x: number; t: number; hue: string }> = []
  for (const f of [...namedPeaks].sort((a, b) => (a.peakT as number) - (b.peakT as number))) {
    let x = xOf(f.peakT as number)
    const prev = dropLabels[dropLabels.length - 1]
    if (prev && x - prev.x < 36) x = prev.x + 36
    dropLabels.push({ x, t: f.peakT as number, hue: hueOf(f.side) })
  }

  const ticks: number[] = [OPEN]
  for (let m = 10 * 60; m < CLOSE; m += 60) ticks.push(m)
  ticks.push(CLOSE)

  return (
    <div style={{ padding: 24, display: 'flex', gap: 14, alignItems: 'flex-start' }}>
      {/* ── The battlefield. No words on it. ──────────────────────────────── */}
      <div style={{ ...card, padding: '12px 10px 8px', flex: '1 1 auto', minWidth: 0 }}>
        <svg viewBox={`0 0 ${VB_W} ${VB_H}`} style={{ width: '100%', height: 'auto', display: 'block' }}
          role="img"
          aria-label={`Open-interest fronts for ${pay.idx ?? index} by price and time, 09:15 to 15:30. Call fronts grow up from each strike, put fronts down; the faint outline is each front's high-water mark.`}
          onMouseLeave={() => setHoverK(null)}>

          {/* strike spines + price gutter */}
          {!empty && g.strikes.map(k => (
            <g key={`k-${k}`}>
              <line x1={PAD_L} y1={g.yOf(k)} x2={VB_W - PAD_R} y2={g.yOf(k)}
                stroke={wash(pal.ink, hoverK === k ? 0.16 : 0.055)} strokeWidth={1} />
              <text x={PAD_L - 8} y={g.yOf(k) + 3.4} textAnchor="end" fontSize={9.5}
                fill={hoverK === k ? pal.accent : pal.textMuted}>{inr(k)}</text>
            </g>
          ))}

          {/* named levels — thin rules, labels in the right gutter with a leader */}
          {!empty && rules.map((r, i) => (
            <g key={`lv-${i}-${r.px}`}>
              <line x1={PAD_L} y1={r.y} x2={VB_W - PAD_R} y2={r.y}
                stroke={pal.accent} strokeWidth={r.kind === 'ROUND' ? 0.6 : 1}
                strokeOpacity={r.kind === 'ROUND' ? 0.22 : 0.45} strokeDasharray="4 5" />
              <line x1={VB_W - PAD_R} y1={r.y} x2={VB_W - PAD_R + 10} y2={r.ly}
                stroke={pal.accent} strokeWidth={0.6} strokeOpacity={0.35} />
              <text x={VB_W - PAD_R + 13} y={r.ly + 3.2} fontSize={9.5} fill={pal.textMuted}>{r.label}</text>
            </g>
          ))}

          {/* time axis */}
          <line x1={PAD_L} y1={AXIS_Y} x2={VB_W - PAD_R} y2={AXIS_Y} stroke={wash(pal.ink, 0.16)} strokeWidth={1} />
          {ticks.map(m => (
            <g key={`t-${m}`}>
              <line x1={xOf(m)} y1={PAD_T} x2={xOf(m)} y2={AXIS_Y} stroke={wash(pal.ink, 0.045)} strokeWidth={1} />
              <text x={xOf(m)} y={AXIS_Y + 15} textAnchor="middle" fontSize={10} fill={pal.textMuted}>{hhmm(m)}</text>
            </g>
          ))}

          {/* ── The fronts. Crest = high-water mark, fill = what is held. ──
              Three passes in this order, so no band can bury a neighbour's
              evidence: all the ground once held, then all the ground held now,
              then every crest line on top. */}
          {g.fronts.map(f => f.crests.map((c, i) => (
            <path key={`cw-${f.k}${f.side}-${i}`} d={c.wash} fill={wash(hueOf(f.side), 0.08)} />
          )))}
          {g.fronts.map(f => f.runs.map((r, i) => (
            <path key={`fl-${f.k}${f.side}-${i}`} d={r.d} fill={wash(hueOf(f.side), r.rebuilt ? 0.24 : 0.58)} />
          )))}
          {g.fronts.map(f => f.crests.map((c, i) => (
            <path key={`ce-${f.k}${f.side}-${i}`} d={c.edge} fill="none" stroke={hueOf(f.side)}
              strokeOpacity={0.5} strokeWidth={0.9} strokeLinejoin="round" strokeLinecap="round" />
          )))}

          {/* peak marks: every front that topped out gets a tick; only the two
              largest and the cursor row get a drop-line and a time */}
          {g.fronts.filter(f => f.peak > 0 && f.peakT != null).map(f => {
            const x = xOf(f.peakT as number)
            const hp = (Math.max(0, f.peak) / (g.vmax || 1)) * Math.max(2, g.rowH * 0.46)
            const y = f.side === 'ce' ? f.y - hp : f.y + hp
            const named = namedPeaks.some(n => n.k === f.k && n.side === f.side)
            return (
              <g key={`pm-${f.k}${f.side}`}>
                {named && <line x1={x} y1={y} x2={x} y2={AXIS_Y} stroke={hueOf(f.side)} strokeWidth={0.7} strokeOpacity={0.35} strokeDasharray="2 3" />}
                <path d={`M${x} ${y - 3}L${x + 2.6} ${y}L${x} ${y + 3}L${x - 2.6} ${y}Z`}
                  fill={hueOf(f.side)} fillOpacity={named ? 0.95 : 0.5} />
              </g>
            )
          })}
          {dropLabels.map((d, i) => (
            <text key={`dl-${i}`} x={d.x} y={AXIS_Y + 42} textAnchor="middle" fontSize={9.5} fill={d.hue} opacity={0.9}>
              {hhmm(d.t)}
            </text>
          ))}

          {/* spot — the contested line */}
          {g.spotSegs.map((pts, i) => (
            <polyline key={`sp-${i}`} points={pts} fill="none" stroke={pal.textPrimary}
              strokeWidth={2} strokeOpacity={0.9} strokeLinejoin="round" strokeLinecap="round" />
          ))}

          {/* where the observed record begins — a caret on the axis, its time
              in the gutter, never on the map */}
          {!empty && g.firstObserved != null && (
            <g>
              <path d={`M${xOf(g.firstObserved)} ${AXIS_Y - 5}L${xOf(g.firstObserved) + 4.5} ${AXIS_Y + 2}L${xOf(g.firstObserved) - 4.5} ${AXIS_Y + 2}Z`}
                fill={pal.textPrimary} fillOpacity={0.75} />
              <text x={xOf(g.firstObserved)} y={AXIS_Y + 28} textAnchor="middle" fontSize={9.5} fill={pal.textSecondary}>
                {hhmm(g.firstObserved)}
              </text>
            </g>
          )}

          {/* hover rows — one rect per strike, so no geometry is rebuilt to
              move the cursor */}
          {!empty && g.strikes.map(k => (
            <rect key={`hv-${k}`} x={PAD_L} y={g.yOf(k) - g.rowH / 2} width={W} height={Math.max(6, g.rowH)}
              fill="transparent" onMouseEnter={() => setHoverK(k)} style={{ cursor: 'default' }}>
              <title>{`${inr(k)} — CE and PE fronts; detail in the rail`}</title>
            </rect>
          ))}

          {/* ── The absence, printed where the map would be ─────────────────
              A route that answered with no minutes and a route whose every
              minute falls outside the session are two different findings. */}
          {empty && (
            <text x={PAD_L} y={PAD_T + PLOT_H / 2} fontSize={13} fill={pal.caution}>
              {g.inSession.length === 0
                ? (Object.keys(pay.minutes ?? {}).length === 0
                    ? `No fronts drawn: ${pay.why ?? 'the route returned no minutes and did not say why'}.`
                    : `No fronts drawn: all ${Object.keys(pay.minutes ?? {}).length} recorded minutes fall outside 09:15–15:30.`)
                : `No fronts drawn: the minutes carry no strikes — ${pay.why ?? 'the route did not say why'}.`}
            </text>
          )}
        </svg>
      </div>

      {/* ── The rail. Every word on this screen lives here. ───────────────── */}
      <div style={{ width: 300, flex: '0 0 300px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Header index={index} pay={pay} g={g} />

        <div style={{ ...card, padding: '12px 14px', minHeight: 132 }}>
          <div className="micro-label" style={{ marginBottom: 8 }}>
            {hoverK == null ? 'Cursor' : `Strike ${inr(hoverK)}`}
          </div>
          {hoverK == null ? (
            <div style={{ ...note }}>
              Hover a strike row for its price, what the writers have added since the open,
              whether that front is building or retreating, and when it topped out.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {(['ce', 'pe'] as Side[]).map(side => {
                const f = hovered.find(x => x.side === side)
                if (!f) return (
                  <div key={side} style={note}>
                    {side.toUpperCase()} — no reading at this strike in today's record.
                  </div>
                )
                return (
                  <div key={side} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: hueOf(side) }}>
                        {side.toUpperCase()}
                      </span>
                      <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: pal.textPrimary }}>
                        {fmtOI(f.now)}
                      </span>
                      <span style={{ fontSize: 11, color: pal.textMuted }}>added since the open</span>
                    </div>
                    <div style={{ fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>
                      {f.peak <= 0
                        ? (f.now < 0
                            ? `This front is ${fmtOI(Math.abs(f.now))} BELOW its own open — it has never held ground today.`
                            : 'This front has added nothing since the open.')
                        : f.off < 0.02
                          ? `Building — at its high-water mark of ${fmtOI(f.peak)}, reached ${hhmm(f.peakT as number)}.`
                          : `Retreating — ${Math.round(f.off * 100)}% off its peak of ${fmtOI(f.peak)}, which it reached at ${hhmm(f.peakT as number)}.`}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {!empty && g.ranked.length > 0 && (
          <div style={{ ...card, padding: '12px 14px' }}>
            <div className="micro-label" style={{ marginBottom: 8 }}>The two largest fronts</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {g.ranked.slice(0, 2).map(f => (
                <div key={`top-${f.k}${f.side}`} style={{ fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>
                  <span className="mono" style={{ color: pal.textPrimary, fontWeight: 600 }}>{inr(f.k)}</span>{' '}
                  <span style={{ color: hueOf(f.side), fontWeight: 700, letterSpacing: '0.06em' }}>{f.side.toUpperCase()}</span>{' '}
                  topped at <span className="mono">{fmtOI(f.peak)}</span> at {hhmm(f.peakT as number)}, holds{' '}
                  <span className="mono">{fmtOI(f.now)}</span>
                  {f.off >= 0.02 ? ` — ${Math.round(f.off * 100)}% given back.` : ' — still at its high.'}
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ ...card, padding: '12px 14px' }}>
          <div className="micro-label" style={{ marginBottom: 8 }}>How to read it</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <line x1={0} y1={8} x2={26} y2={8} stroke={wash(pal.ink, 0.25)} strokeWidth={1} />
                <path d="M2 8 L24 8 L24 2 L2 3 Z" fill={wash(pal.bear, 0.58)} />
              </svg>
              CE fronts grow UP from the strike
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <line x1={0} y1={8} x2={26} y2={8} stroke={wash(pal.ink, 0.25)} strokeWidth={1} />
                <path d="M2 8 L24 8 L24 14 L2 13 Z" fill={wash(pal.bull, 0.58)} />
              </svg>
              PE fronts grow DOWN
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <path d="M2 14 L24 14 L24 2 L2 4 Z" fill={wash(pal.bear, 0.07)} stroke={pal.bear} strokeOpacity={0.42} strokeWidth={0.8} />
                <path d="M2 14 L24 14 L24 10 L2 11 Z" fill={wash(pal.bear, 0.58)} />
              </svg>
              Outline = high-water mark, fill = held now
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <path d="M13 4 L16 8 L13 12 L10 8 Z" fill={pal.textSecondary} fillOpacity={0.9} />
              </svg>
              Where a front topped out
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <line x1={0} y1={8} x2={26} y2={8} stroke={pal.textPrimary} strokeWidth={2} strokeOpacity={0.9} />
              </svg>
              Spot
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <line x1={0} y1={8} x2={26} y2={8} stroke={pal.accent} strokeWidth={1} strokeOpacity={0.45} strokeDasharray="4 5" />
              </svg>
              Named level — labelled in the right gutter
            </Key>
          </div>
        </div>

        <div style={{ ...card, padding: '12px 14px' }}>
          <div className="micro-label" style={{ marginBottom: 8 }}>Provenance</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, ...note }}>
            <span>
              The axis is the SESSION, 09:15–15:30, never the record's first minute.{' '}
              {g.inSession.length > 0
                ? `The record runs ${hhmm(g.first as number)}–${hhmm(g.last as number)}: ${g.inSession.length} minute${g.inSession.length === 1 ? '' : 's'} drawn, ${g.rebuilt} rebuilt and ${g.inSession.length - g.rebuilt} observed.`
                : 'No minutes fall inside it.'}
              {g.rebuilt > 0
                ? ' Rebuilt minutes are drawn lighter in the same colour — the same measurement, weaker provenance.'
                : g.inSession.length > 0
                  ? ` Nothing was rebuilt today, so there is no reconstructed stretch: the record simply begins at ${hhmm(g.first as number)} and nothing before it is claimed.`
                  : ''}
            </span>
            {g.holes > 0 && (
              <span>
                Broken across {g.holes} stretch{g.holes === 1 ? '' : 'es'} where no minute was recorded at all
                (longest {g.longestHole} minutes). A band painted through those would be ground no one took.
              </span>
            )}
            {(g.outside > 0 || g.unreadable > 0) && (
              <span>
                {g.outside > 0 ? `${g.outside} recorded minute${g.outside === 1 ? '' : 's'} fall outside 09:15–15:30 and are not on this axis. ` : ''}
                {g.unreadable > 0 ? `${g.unreadable} timestamp${g.unreadable === 1 ? '' : 's'} could not be read and were dropped rather than placed at the open.` : ''}
              </span>
            )}
            <span>
              {levels
                ? `${rules.length} named level${rules.length === 1 ? '' : 's'} from the war map fall on this price range.`
                : `No named levels — ${levelsWhy ?? 'the war map did not answer'}.`}
            </span>
          </div>
        </div>

        <div style={{ ...note }}>
          Thickness is OI CHANGE since the open, on one scale for the whole map
          {g.vmax > 0 ? ` (full thickness = ${fmtOI(g.vmax)})` : ''}; a front below its own open has no
          band and says so on hover. The high-water mark is computed from these minutes, not from the
          route's <span className="mono">peak</span> field, which is peak absolute OI and carries no time.
          This map describes what the writers did and when. It prints no hit rate, no expectancy and no
          direction — what the fronts mean for the next hour is yours to call.
        </div>
      </div>
    </div>
  )
}

function Key({ children, pal }: { children: ReactNode; pal: ReturnType<typeof usePalette> }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: pal.textSecondary }}>
      {children}
    </span>
  )
}

function Header({ index, pay, g }: { index: IndexKey; pay: Payload | null; g: { first: number | null; last: number | null } | null }) {
  const pal = usePalette()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span className="micro-label">War — the OI battlefield over time</span>
      <span className="mono" style={{ fontSize: 11, color: pal.textMuted }}>
        {pay?.idx ?? index} · 09:15–15:30
        {g && g.first != null && g.last != null ? ` · record ${hhmm(g.first)}–${hhmm(g.last)}` : ''}
      </span>
    </div>
  )
}
