import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { usePalette, rgbOf } from '../theme'
import type { IndexKey } from '../data'
import { read, leanOf, lakh, mm, W as SPD_WIN, FLOW, ACCEL } from '../speed/speed'
import type { Flow, Minutes, Side as SSide } from '../speed/speed'

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

   5. SPEED AND WHO STOPPED (Mary, 29 Oct 2026: "show the speed of change and
      mark the time when there is push in oi ... like board tab who stopped what
      time who started again"). Nothing new is decided here: the Speed tab's
      engine (speed.ts) runs on this same grid, and the pushes are Jarvis's
      (/api/jarvis, handshake-2). On the map:
        - a STRIP on each of the nine near-money spines, CE above and PE below:
          side hue = likh rahe, hatched = chhod rahe, grey = ruke; darker =
          faster. Every change the Speed tab stamps is in it, at once.
        - a MARK (and a chip on the latest) where one of the Board's four walls
          changed state AND HELD it SETTLE minutes. Speed.ts stamps ~30 changes
          per strike-side a day (29 Oct NIFTY: 551 on nine strikes),
          mostly 3-5 minute pauses; drawn whole they bury the map.
        - the SPEED NOW column right of the plot, the PUSH arrows on spot with a
          leader to the strike that answered, NAHI pushes as grey axis ticks,
          and the SPEED LANE under the axis: CALL vs PUT writers' net speed.
      The chips on the map are the one exception to "every word in the rail":
      her standing rule is a Hinglish chip with its number on every symbol.
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
  /** The Board's §1d fronts: the walls that get MARKS (everything near money gets a strip). */
  fronts?: Array<{ k: number; side: SSide }> | null
  fronts_why?: string | null
}
/** One handshake push as /api/jarvis publishes it (jarvis.py PUSH). */
type Push = {
  t: string; m: number; dir: number; lots: number; k: number | null; side: string | null
  ans: string | null; held: string | null; held_m: number | null; am_m: number | null; artifact: boolean
  /** Who opened an add at the wall (TIKI / PHANS): WRITERS / KHAREEDAR / "?". */
  who?: string | null
  /** "band" when the strike said nothing and its ±2 strikes answered (G1, 30 Oct). */
  via?: string | null
}
/** A wall's state change that held SETTLE minutes. */
type Mark = { t: string; m: number; k: number; side: SSide; flow: Flow; word: string }
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
const SPD_W = 104         // the SPEED NOW column between the plot and the level gutter
const VB_W = 1220 + SPD_W
const PAD_L = 66          // price gutter
const PAD_R = 178         // named-level label gutter
const PAD_T = 16
const PLOT_R = VB_W - PAD_R - SPD_W
// 740, not the ~400 a strip chart would take: the band thickness a front can
// reach is a fraction of the row, and the row is a fraction of the plot. At 566
// the largest front on the measured day rendered 14.2px thick and the ruin
// inside it 0.8px, which is legible but cramped; at 740 the same pair is 18.5
// and 1.0. The tab's content area scrolls, and a map is worth a scroll.
const PLOT_H = 740
const AXIS_Y = PAD_T + PLOT_H
// The speed lane sits under the time axis and its labels, on the same x.
const LANE_T = AXIS_Y + 58
const LANE_H = 110
const LANE_MID = LANE_T + LANE_H / 2
/** Minutes after the open the lane's scale ignores (the opening build), drawn clipped instead [I]. */
const LANE_SKIP = 15
const VB_H = LANE_T + LANE_H + 22
const W = PLOT_R - PAD_L
const xOf = (m: number) => PAD_L + ((m - OPEN) / SPAN) * W

/** A wall's change is MARKED once the new state has held this long: three of her
 *  3-minute bars [I]. Shorter pauses stay in the strip, unmarked. */
const SETTLE = 9
const SHORT: Record<Flow, string> = { W: 'likh', R: 'ruke', C: 'chhod' }
/** A strip's darkness, by its speed's quarter of the map's fastest [I]. */
const STRIP_A = [0.35, 0.55, 0.75, 0.95]
const ACC_GLYPH: Record<string, string> = { tez: '▲▲', barabar: '▶', dheema: '▼', palta: '⇄', shuru: '●' }
/** The handshake's answers (handshake.SAID) and what each says at the wall. */
const SAID_WORD: Record<string, string> = { TOOT: 'deewar toot rahi', PHANS: 'writers phanse', TIKI: 'deewar tiki' }
/** G4 (30 Oct): an add at the wall is a defence only when writers opened it; buyers opening it bet the wall breaks. */
const buyersIn = (p: { word: string; who?: string | null }) => p.word === 'TIKI' && p.who === 'KHAREEDAR'
const saidOf = (p: { word: string; who?: string | null }) => (buyersIn(p) ? 'kharidar ghuse (deewar nahi)' : SAID_WORD[p.word])

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
  /** A minute picked from the KRAM rail: drawn as a rule across the map and the lane. */
  const [hoverT, setHoverT] = useState<number | null>(null)
  const [pushes, setPushes] = useState<Push[] | null>(null)
  const [pushWhy, setPushWhy] = useState<string | null>(null)

  // The pushes are a third, independent question: Jarvis builds them (4-10 s cold, cached 20 s server-side), so they
  // are polled slower than the grid, and a failure leaves the map and its strips standing.
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/jarvis?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        if (j?.ok && Array.isArray(j.pushes)) { setPushes(j.pushes as Push[]); setPushWhy(null) }
        else { setPushes(null); setPushWhy(j?.why || j?.error || `HTTP ${r.status}`) }
      } catch (e) {
        if (alive) { setPushes(null); setPushWhy(`Jarvis did not answer (${String(e)})`) }
      }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 60000)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])

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

  // ── Point 5: the Speed tab's engine over this same grid. One build per fetch. ──────────────────────────────────────
  const sp = useMemo(() => {
    const minutes = (pay?.minutes ?? null) as Minutes | null
    const r = read(minutes)
    if (!r || !minutes) return null
    const rows = g.inSession
    const at = new Map(rows.map((x, i) => [x.m, i]))
    const now = mm(r.asof)
    const sides: SSide[] = ['CE', 'PE']

    // Settled changes per near-money strike-side: a Speed-tab run that lasted SETTLE minutes and differs from the state
    // before it. The running state counts once it has lasted SETTLE to now, so a mark lands SETTLE minutes after it starts.
    const settled: Mark[] = []
    const stamps: Record<string, Array<{ m: number; flow: Flow }>> = {}
    for (const k of r.nine) for (const side of sides) {
      const st = r.stamps.filter(s => s.k === k && s.side === side).map(s => ({ t: s.t, m: mm(s.t), flow: s.flow })).sort((a, z) => a.m - z.m)
      stamps[side + k] = st
      let prev: Flow | null = null, wrote = false
      st.forEach((s, i) => {
        const end = i + 1 < st.length ? st[i + 1].m : now
        if (end - s.m < SETTLE || s.flow === prev) return
        prev = s.flow
        settled.push({ t: s.t, m: s.m, k, side, flow: s.flow,
          word: s.flow === 'W' ? (wrote ? 'phir likhne lage' : 'likhne lage') : s.flow === 'R' ? 'ruk gaye' : 'chhodne lage' })
        if (s.flow === 'W') wrote = true
      })
    }

    // The strips: per minute, the state the Speed tab held then [I], darker the faster OI moved over SPD_WIN minutes [M].
    // The darkness is one scale for the whole map, as the bands are.
    const cellAt = (i: number, k: number, si: number) => {
      const c = (minutes[rows[i].t]?.k ?? {})[String(k)]
      return Array.isArray(c) && typeof c[si] === 'number' && Number.isFinite(c[si]) ? (c[si] as number) : null
    }
    const speed: Record<string, Array<number | null>> = {}
    let top = 0
    for (const k of r.nine) sides.forEach((side, si) => {
      speed[side + k] = rows.map((x, i) => {
        const b = at.get(x.m - SPD_WIN)
        const v = cellAt(i, k, si), w = b == null ? null : cellAt(b, k, si)
        if (v == null || w == null) return null
        top = Math.max(top, Math.abs(v - w) / SPD_WIN)
        return (v - w) / SPD_WIN
      })
    })
    const strips = r.nine.flatMap(k => sides.map(side => {
      const st = stamps[side + k], spd = speed[side + k]
      const segs: Array<{ x0: number; x1: number; flow: Flow; a: number }> = []
      let j = -1
      rows.forEach((x, i) => {
        while (j + 1 < st.length && st[j + 1].m <= x.m) j++
        const s = spd[i]
        if (j < 0 || s == null) return
        const flow = st[j].flow
        const a = flow === 'R' ? 0 : Math.min(3, Math.floor((4 * Math.abs(s)) / (top || 1)))
        const x0 = xOf(x.m), x1 = xOf(Math.min(x.m + 1, CLOSE))
        const last = segs[segs.length - 1]
        if (last && last.flow === flow && last.a === a && Math.abs(last.x1 - x0) < 0.01) last.x1 = x1   // contiguous: one rect
        else segs.push({ x0, x1, flow, a })
      })
      return { k, side, segs }
    }))

    // The lane: CALL and PUT writers' net speed at every minute, read() on the grid UP TO that minute, so each point is
    // what the Speed tab's header said then (its nine were the nine nearest THAT minute's spot). O(n²) over ~375 minutes.
    const lane: Array<{ m: number; ce: number | null; pe: number | null }> = []
    const upto: Minutes = {}
    let laneTop = 0, openTop = 0
    for (const x of rows) {
      upto[x.t] = minutes[x.t]
      const n = read(upto)?.net
      const ce = n?.CE.spd ?? null, pe = n?.PE.spd ?? null
      const big = Math.max(Math.abs(ce ?? 0), Math.abs(pe ?? 0))
      // The scale skips the first LANE_SKIP minutes: on 29 Oct the opening build ran +16.8L/m and flattened the rest
      // of the day into a line at zero. The open is still drawn, clipped at the lane's edge.
      if (x.m >= OPEN + LANE_SKIP) laneTop = Math.max(laneTop, big)
      else openTop = Math.max(openTop, big)
      lane.push({ m: x.m, ce, pe })
    }
    if (laneTop === 0) laneTop = openTop

    // The walls that get marks: the Board's §1d fronts, when they are among the nine (they are picked from the nine).
    const walls = new Set((pay?.fronts ?? []).filter(f => r.nine.includes(Number(f.k))).map(f => f.side + Number(f.k)))
    return { r, settled, strips, lane, laneTop, walls }
  }, [pay, g.inSession])

  // Jarvis's pushes, placed on this grid's spot. An artifact (a push dated inside a hole in the record: the laptop
  // asleep, not the market) is counted, never drawn.
  const pz = useMemo(() => {
    if (!pushes) return null
    const raw = pay?.minutes ?? {}
    const spotAt = (m: number) => {
      for (let j = g.inSession.length - 1; j >= 0; j--) {
        const x = g.inSession[j], s = raw[x.t]?.spot
        if (x.m <= m && typeof s === 'number' && Number.isFinite(s)) return s
      }
      return null
    }
    const live = pushes.filter(p => !p.artifact)
    return {
      // held: the handshake-2 word, or 'wapas' (it came back at the next chain minute); null = the hold not read yet
      said: live.filter(p => p.ans != null && SAID_WORD[p.ans]).map(p => ({ ...p, spot: spotAt(p.m), word: p.held ?? `${p.ans}?` })),
      nahi: live.filter(p => p.ans === 'NAHI'),
      unread: live.filter(p => p.ans == null).length,
      artifacts: pushes.length - live.length,
    }
  }, [pushes, pay, g.inSession])

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

  // Point 5 chips, placed so none prints over another. A wall's latest mark always gets one (flipped left of its glyph
  // at the right edge); the cursor row's and the picked minute's get one where it fits, walked right to left. A chip
  // is ~5 units a character and 9 minutes is ~23, so most of a busy row's marks stay glyph-only, their words in the rail.
  const marksShown = sp ? sp.settled.filter(s => sp.walls.has(s.side + s.k) || s.k === hoverK) : []
  const chipOf = (s: Mark) => `${s.word === 'phir likhne lage' ? 'phir likh' : SHORT[s.flow]} ${s.t}`
  const chipAt = new Map<Mark, 'r' | 'l'>()
  for (const key of new Set(marksShown.map(s => s.side + s.k))) {
    let room = PLOT_R - 2
    marksShown.filter(s => s.side + s.k === key).sort((a, z) => z.m - a.m).forEach((s, i) => {
      const x = xOf(s.m), w = chipOf(s).length * 4.9 + 6
      if (i > 0 && s.k !== hoverK && s.m !== hoverT) return
      if (x + w <= room) { chipAt.set(s, 'r'); room = x - 4 }
      else if (i === 0) { chipAt.set(s, 'l'); room = x - w - 4 }
    })
  }
  // Push chips stack in lanes (away from spot) when pushes come minutes apart, as four did at 22,800 on 29 Oct.
  const pushChip = (p: { dir: number; lots: number; k: number | null; word: string; who?: string | null; via?: string | null }) =>
    `${p.dir > 0 ? '▲' : '▼'}${p.lots > 0 ? '+' : '−'}${Math.abs(p.lots)} · ${p.k != null ? `${inr(p.k)}${p.via === 'band' ? '±2' : ''} ` : ''}`
    + (buyersIn(p) ? 'BUYERS IN' : p.word)
  const pushLane = new Map<object, number>()
  for (const up of [true, false]) {
    const ends: number[] = []
    for (const p of (pz?.said ?? []).filter(q => (q.dir > 0) === up).sort((a, z) => a.m - z.m)) {
      const x = xOf(p.m), w = pushChip(p).length * 5.3 + 6
      let lane = ends.findIndex(e => x - w / 2 > e + 3)
      if (lane < 0) { lane = ends.length; ends.push(0) }
      ends[lane] = x + w / 2
      pushLane.set(p, lane)
    }
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

          <defs>
            {(['ce', 'pe'] as Side[]).map(s => (
              <pattern key={s} id={`war-hatch-${s}`} width={3.5} height={3.5} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width={3.5} height={3.5} fill={pal.card} />
                <line x1={0} y1={0} x2={0} y2={3.5} stroke={hueOf(s)} strokeWidth={1.6} />
              </pattern>
            ))}
          </defs>

          {/* strike spines + price gutter */}
          {!empty && g.strikes.map(k => (
            <g key={`k-${k}`}>
              <line x1={PAD_L} y1={g.yOf(k)} x2={PLOT_R} y2={g.yOf(k)}
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
          <line x1={PAD_L} y1={AXIS_Y} x2={PLOT_R} y2={AXIS_Y} stroke={wash(pal.ink, 0.16)} strokeWidth={1} />
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
          {/* point 5: the near-money strips on the spine, CE above and PE below: drawn over the fills, under the crests */}
          {sp && sp.strips.map(s => s.segs.map((sg, i) => {
            const side: Side = s.side === 'CE' ? 'ce' : 'pe'
            return (
              <rect key={`st-${s.side}${s.k}-${i}`} x={sg.x0} y={g.yOf(s.k) + (s.side === 'CE' ? -4 : 0)}
                width={Math.max(0.6, sg.x1 - sg.x0)} height={4}
                fill={sg.flow === 'R' ? wash(pal.ink, 0.2) : sg.flow === 'C' ? `url(#war-hatch-${side})` : hueOf(side)}
                fillOpacity={sg.flow === 'R' ? 1 : STRIP_A[sg.a]} />
            )
          }))}
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

          {/* ── Point 5, over the spot. ────────────────────────────────────────
              The wall marks: a settled change on one of the Board's walls, or on
              the cursor's row. The chip rides the latest per wall (its state
              now), every mark on the cursor's row, and the minute picked in the
              rail. ● likh · ■ ruke · ○ chhod. */}
          {marksShown.map((s, i) => {
            const side: Side = s.side === 'CE' ? 'ce' : 'pe'
            const x = xOf(s.m), y = g.yOf(s.k) + (s.side === 'CE' ? -8.5 : 8.5)
            const at = chipAt.get(s)
            return (
              <g key={`wm-${s.side}${s.k}-${i}`}>
                {s.flow === 'W' && <circle cx={x} cy={y} r={3.3} fill={hueOf(side)} stroke={pal.card} strokeWidth={1} />}
                {s.flow === 'C' && <circle cx={x} cy={y} r={3} fill={pal.card} stroke={hueOf(side)} strokeWidth={1.6} />}
                {s.flow === 'R' && <rect x={x - 3} y={y - 3} width={6} height={6} fill={pal.textMuted} stroke={pal.card} strokeWidth={1} />}
                {at && (
                  <text x={at === 'r' ? x + 5.5 : x - 5.5} y={y + 3} textAnchor={at === 'r' ? 'start' : 'end'} fontSize={8.5} fontWeight={600}
                    fill={hueOf(side)} stroke={pal.card} strokeWidth={2.6} style={{ paintOrder: 'stroke' }}>
                    {chipOf(s)}
                  </text>
                )}
                <title>{`${s.side} ${inr(s.k)} ${s.word} ${s.t} — held ${SETTLE}+ min [I]`}</title>
              </g>
            )
          })}

          {/* the pushes that got an answer: an arrow on spot at the push minute, a
              leader to the strike that answered, at the minute it was read */}
          {pz && pz.said.map((p, i) => {
            if (p.spot == null) return null
            const side: Side = p.side === 'PE' || (p.side == null && p.dir < 0) ? 'pe' : 'ce'
            const hue = SAID_WORD[p.word] ? hueOf(side) : pal.textMuted           // 'wapas' and a pending '?' go grey
            const up = p.dir > 0
            const x = xOf(p.m), y = g.yOf(p.spot) + (up ? -8 : 8)
            const tri = up ? `M${x} ${y - 5}L${x + 4.5} ${y + 3}L${x - 4.5} ${y + 3}Z` : `M${x} ${y + 5}L${x + 4.5} ${y - 3}L${x - 4.5} ${y - 3}Z`
            const ax = xOf(p.held_m ?? p.am_m ?? p.m)
            const lots = `${p.lots > 0 ? '+' : '−'}${Math.abs(p.lots)}`
            return (
              <g key={`pu-${i}`}>
                {p.k != null && (
                  <>
                    <line x1={x} y1={y} x2={ax} y2={g.yOf(p.k)} stroke={hue} strokeWidth={0.9} strokeOpacity={0.6} strokeDasharray="3 3" />
                    <path d={`M${ax} ${g.yOf(p.k) - 3.5}L${ax + 3.5} ${g.yOf(p.k)}L${ax} ${g.yOf(p.k) + 3.5}L${ax - 3.5} ${g.yOf(p.k)}Z`} fill={hue} />
                  </>
                )}
                <path d={tri} fill={p.word === 'TOOT' || p.word === 'PHANS' || buyersIn(p) ? hue : pal.card} stroke={hue} strokeWidth={1.4} />
                <text x={x} y={up ? y - 9 - 11 * (pushLane.get(p) ?? 0) : y + 15 + 11 * (pushLane.get(p) ?? 0)} textAnchor="middle"
                  fontSize={9} fontWeight={700} fill={hue} stroke={pal.card} strokeWidth={3} style={{ paintOrder: 'stroke' }}>
                  {pushChip(p)}
                </text>
                <title>{`PUSH ${p.t}: ${lots} lots ${up ? 'up' : 'down'} · answer at ${p.k ?? '?'} ${p.side ?? ''}${p.via === 'band' ? ' and its ±2 strikes' : ''}: ${saidOf(p) ?? (p.word === 'wapas' ? 'came back at the next chain minute (wapas)' : 'crossed, hold not read yet')}`}</title>
              </g>
            )
          })}
          {/* the pushes OI did not answer: a grey tick on the time axis only */}
          {pz && pz.nahi.map((p, i) => (
            <line key={`na-${i}`} x1={xOf(p.m)} y1={AXIS_Y - 5} x2={xOf(p.m)} y2={AXIS_Y + 5} stroke={pal.textMuted} strokeWidth={1.3} strokeOpacity={0.7}>
              <title>{`PUSH ${p.t}: ${p.lots > 0 ? '+' : '−'}${Math.abs(p.lots)} lots — no OI answer at ${p.k ?? '?'} ${p.side ?? ''} within 4 min (NAHI)`}</title>
            </line>
          ))}

          {/* SPEED NOW: the nine near-money strikes, CE over the spine, PE under */}
          {sp && (
            <g>
              <text x={PLOT_R + 8} y={PAD_T - 4} fontSize={9} fontWeight={700} fill={pal.textMuted}>{`ABHI · ${SPD_WIN} MIN`}</text>
              {sp.r.cells.map(c => (
                <text key={`sc-${c.side}${c.k}`} x={PLOT_R + 8} y={g.yOf(c.k) + (c.side === 'CE' ? -3.5 : 10)} fontSize={9}
                  fontWeight={c.flow === 'W' ? 700 : 500}
                  fill={c.flow == null || c.flow === 'R' ? pal.textMuted : hueOf(c.side === 'CE' ? 'ce' : 'pe')}
                  stroke={pal.card} strokeWidth={2.5} style={{ paintOrder: 'stroke' }}>
                  {c.spd == null ? `${c.side} —` : `${lakh(c.spd, true)}/m ${c.flow ? SHORT[c.flow] : '?'} ${c.accel ? ACC_GLYPH[c.accel] : ''}`}
                  <title>{`${c.side} ${inr(c.k)}: ${c.spd == null ? 'no 5-minute speed yet' : `${lakh(c.spd, true)} per minute over ${SPD_WIN} min [M]`} · ${c.flow ? FLOW[c.flow] : 'no state yet'}${c.since ? ` since ${c.since}` : ''}${c.accel ? ` · ${ACCEL[c.accel]}` : ''}`}</title>
                </text>
              ))}
            </g>
          )}

          {/* THE SPEED LANE: CALL vs PUT writers' net speed, nine strikes, per minute */}
          {sp && sp.laneTop > 0 && (() => {
            const yL = (v: number) => LANE_MID - (Math.max(-1, Math.min(1, v / sp.laneTop))) * (LANE_H / 2 - 8)
            const line = (key: 'ce' | 'pe') => {
              const out: string[] = []
              let cur: string[] = []
              sp.lane.forEach((p, i) => {
                const v = p[key]
                if (v == null || (i > 0 && p.m - sp.lane[i - 1].m > GAP)) { if (cur.length > 1) out.push(cur.join(' ')); cur = [] }
                if (v != null) cur.push(`${xOf(p.m).toFixed(1)},${yL(v).toFixed(1)}`)
              })
              if (cur.length > 1) out.push(cur.join(' '))
              return out
            }
            const lastOf = (key: 'ce' | 'pe') => [...sp.lane].reverse().find(p => p[key] != null)?.[key] ?? null
            return (
              <g>
                <rect x={PAD_L} y={LANE_T} width={W} height={LANE_H} fill={wash(pal.ink, 0.025)} />
                {ticks.map(m => <line key={`lt-${m}`} x1={xOf(m)} y1={LANE_T} x2={xOf(m)} y2={LANE_T + LANE_H} stroke={wash(pal.ink, 0.05)} />)}
                <line x1={PAD_L} y1={LANE_MID} x2={PLOT_R} y2={LANE_MID} stroke={wash(pal.ink, 0.3)} />
                {pz && pz.nahi.map((p, i) => <line key={`ln-${i}`} x1={xOf(p.m)} y1={LANE_T} x2={xOf(p.m)} y2={LANE_T + LANE_H} stroke={pal.textMuted} strokeOpacity={0.22} />)}
                {pz && pz.said.map((p, i) => (
                  <line key={`ls-${i}`} x1={xOf(p.m)} y1={LANE_T} x2={xOf(p.m)} y2={LANE_T + LANE_H}
                    stroke={SAID_WORD[p.word] ? hueOf(p.side === 'PE' ? 'pe' : 'ce') : pal.textMuted} strokeOpacity={0.55} strokeDasharray="3 2" />
                ))}
                {line('ce').map((pts, i) => <polyline key={`lc-${i}`} points={pts} fill="none" stroke={pal.bear} strokeWidth={1.6} strokeLinejoin="round" />)}
                {line('pe').map((pts, i) => <polyline key={`lp-${i}`} points={pts} fill="none" stroke={pal.bull} strokeWidth={1.6} strokeLinejoin="round" />)}
                <text x={PAD_L - 8} y={LANE_T + 10} textAnchor="end" fontSize={8.5} fill={pal.textMuted}>{`+${lakh(sp.laneTop)}/m`}</text>
                <text x={PAD_L - 8} y={LANE_MID + 3} textAnchor="end" fontSize={8.5} fill={pal.textMuted}>0</text>
                <text x={PAD_L - 8} y={LANE_T + LANE_H - 3} textAnchor="end" fontSize={8.5} fill={pal.textMuted}>{`−${lakh(sp.laneTop)}/m`}</text>
                <text x={PAD_L + 6} y={LANE_T + 12} fontSize={9.5} fontWeight={700} fill={pal.textSecondary}>
                  LIKHNE KI RAFTAAR · 9 strikes · upar = likh rahe · neeche = chhod rahe
                </text>
                {(['ce', 'pe'] as const).map(s => {
                  const v = lastOf(s), o = lastOf(s === 'ce' ? 'pe' : 'ce')
                  if (v == null) return null
                  // two line-ends within a label's height: the higher one's label goes up, the other's down
                  const gap = o == null ? 99 : yL(v) - yL(o)
                  const nudge = Math.abs(gap) >= 10 ? 0 : gap < 0 || (gap === 0 && s === 'ce') ? -5 : 5
                  return (
                    <text key={`le-${s}`} x={PLOT_R + 8} y={yL(v) + 3 + nudge} fontSize={9} fontWeight={700} fill={s === 'ce' ? pal.bear : pal.bull}>
                      {`${s === 'ce' ? 'CALL' : 'PUT'} ${lakh(v, true)}/m`}
                    </text>
                  )
                })}
              </g>
            )
          })()}

          {/* the minute picked in the rail, across the map and the lane */}
          {hoverT != null && (
            <line x1={xOf(hoverT)} y1={PAD_T} x2={xOf(hoverT)} y2={LANE_T + LANE_H} stroke={pal.accent} strokeWidth={1} strokeOpacity={0.7} />
          )}

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

        {/* Point 5: the whole board's writing speed now, the Speed tab's header in two lines */}
        <div style={{ ...card, padding: '12px 14px' }}>
          <div className="micro-label" style={{ marginBottom: 8 }}>Abhi · likhne ki raftaar{sp ? ` · ${sp.r.asof}` : ''}</div>
          {!sp ? (
            <div style={note}>Could not check — the grid has no minute with a spot and strikes yet.</div>
          ) : (() => {
            const lean = leanOf(sp.r.net, sp.r.d5, sp.r.step)
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {(['CE', 'PE'] as SSide[]).map(s => {
                  const n = sp.r.net[s]
                  return (
                    <div key={s} style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                      <span style={{ width: 88, fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: hueOf(s === 'CE' ? 'ce' : 'pe') }}>
                        {s === 'CE' ? 'CALL' : 'PUT'} writers
                      </span>
                      <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: pal.textPrimary }}>
                        {n.spd == null ? '—' : `${lakh(n.spd, true)}/m`}
                      </span>
                      <span style={{ fontSize: 11, color: pal.textSecondary }}>{n.accel ? ACCEL[n.accel] : ''}</span>
                    </div>
                  )
                })}
                <div style={{ marginTop: 4, fontSize: 12, fontWeight: 700,
                  color: lean?.dir === 1 ? pal.bull : lean?.dir === -1 ? pal.bear : pal.textSecondary }}>
                  {lean
                    ? `${lean.dir === 1 ? '▲ ' : lean.dir === -1 ? '▼ ' : ''}${lean.word}${lean.result ? ` · ${lean.result}` : ''}`
                    : 'could not check — no 10-minute history yet'}
                </div>
              </div>
            )
          })()}
        </div>

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
                    {sp && (() => {
                      const S = side.toUpperCase() as SSide
                      const c = sp.r.cells.find(x => x.k === hoverK && x.side === S)
                      if (!c) return <div style={note}>Speed: not one of the nine strikes nearest spot now.</div>
                      const story = sp.settled.filter(x => x.k === hoverK && x.side === S)
                      return (
                        <div style={{ fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>
                          <span className="mono" style={{ color: pal.textPrimary }}>{c.spd == null ? '—' : `${lakh(c.spd, true)}/m`}</span>
                          {` · ${c.flow ? FLOW[c.flow] : 'no state yet'}${c.since ? ` since ${c.since}` : ''}${c.accel ? ` · ${ACCEL[c.accel]}` : ''}`}
                          <div style={{ marginTop: 2 }}>
                            {story.length ? story.slice(-6).map(x => `${x.word} ${x.t}`).join(' → ') : `no change has held ${SETTLE} minutes yet`}
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Point 5: KRAM, the Board's word for it. The walls' settled changes and the answered pushes, newest first. */}
        <div style={{ ...card, padding: '12px 14px' }}>
          <div className="micro-label" style={{ marginBottom: 8 }}>Kab kya hua · deewarein + pushes · naya upar</div>
          {(() => {
            type Row = { m: number; t: string; k: number | null; who: ReactNode; what: string; bold: boolean }
            const rows: Row[] = [
              ...(sp ? sp.settled.filter(s => sp.walls.has(s.side + s.k)) : []).map(s => ({
                m: s.m, t: s.t, k: s.k, bold: s.flow === 'W',
                who: <span style={{ color: hueOf(s.side === 'CE' ? 'ce' : 'pe') }}>{s.side} {inr(s.k)}</span>, what: s.word,
              })),
              ...(pz ? pz.said : []).map(p => ({
                m: p.m, t: p.t, k: p.k, bold: p.word === 'TOOT' || p.word === 'PHANS' || buyersIn(p),
                who: <span style={{ color: SAID_WORD[p.word] ? hueOf(p.side === 'PE' ? 'pe' : 'ce') : pal.textMuted }}>
                  PUSH {p.dir > 0 ? '▲' : '▼'} {p.lots > 0 ? '+' : '−'}{Math.abs(p.lots)}</span>,
                what: `→ ${p.k != null ? `${inr(p.k)} ${p.side ?? ''}${p.via === 'band' ? ' ±2' : ''}` : '?'} · ${saidOf(p) ?? (p.word === 'wapas' ? 'wapas aa gaya' : `${p.word} (hold pending)`)}`,
              })),
            ].sort((a, z) => z.m - a.m)
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {rows.length > 0 && (
                  <div style={{ maxHeight: 300, overflowY: 'auto', display: 'grid', gridTemplateColumns: 'auto auto 1fr', columnGap: 10, rowGap: 3, fontSize: 11.5 }}
                    onMouseLeave={() => { setHoverT(null); setHoverK(null) }}>
                    {rows.map((x, i) => [
                      <span key={`t${i}`} className="mono" style={{ color: pal.textPrimary, fontWeight: 600, cursor: 'default' }}
                        onMouseEnter={() => { setHoverT(x.m); setHoverK(x.k) }}>{x.t}</span>,
                      <span key={`w${i}`} className="mono" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}
                        onMouseEnter={() => { setHoverT(x.m); setHoverK(x.k) }}>{x.who}</span>,
                      <span key={`x${i}`} style={{ color: pal.textSecondary, fontWeight: x.bold ? 700 : 400 }}
                        onMouseEnter={() => { setHoverT(x.m); setHoverK(x.k) }}>{x.what}</span>,
                    ])}
                  </div>
                )}
                <div style={{ ...note, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {!sp ? <span>Walls: could not check — the grid has no minute with a spot and strikes yet.</span>
                    : sp.walls.size === 0 ? <span>Walls: none to mark — {pay.fronts_why ?? 'none of the Board\'s fronts is among the nine strikes nearest spot'}. The strips still show every strike.</span>
                    : !sp.settled.some(s => sp.walls.has(s.side + s.k)) ? <span>Walls: checked — no change has held {SETTLE} minutes yet.</span> : null}
                  {!pz ? <span>Pushes: could not check — {pushWhy ?? 'reading Jarvis…'}</span> : (
                    <>
                      {pz.said.length === 0 && <span>Pushes: checked — none got an OI answer yet.</span>}
                      {pz.nahi.length > 0 && <span>{pz.nahi.length} push{pz.nahi.length === 1 ? '' : 'es'} got no OI answer within 4 minutes (NAHI): grey ticks on the time axis.</span>}
                      {pz.unread > 0 && <span>{pz.unread} push{pz.unread === 1 ? '' : 'es'} not read: under 4 minutes old, or no chain minute to read the answer from.</span>}
                      {pz.artifacts > 0 && <span>{pz.artifacts} not drawn: dated inside a hole in the record (the laptop asleep), not the market.</span>}
                    </>
                  )}
                </div>
              </div>
            )
          })()}
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
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <rect x={0} y={6} width={9} height={4} fill={pal.bear} fillOpacity={0.9} />
                <rect x={9} y={6} width={8} height={4} fill={wash(pal.ink, 0.2)} />
                <rect x={17} y={6} width={9} height={4} fill="url(#war-hatch-ce)" />
              </svg>
              Strip on the strike: likh rahe · ruke · chhod rahe; darker = faster
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <circle cx={5} cy={8} r={3.3} fill={pal.bear} />
                <rect x={10} y={5} width={6} height={6} fill={pal.textMuted} />
                <circle cx={21} cy={8} r={3} fill={pal.card} stroke={pal.bear} strokeWidth={1.6} />
              </svg>
              A wall's change that held {SETTLE} min: likh · ruke · chhod
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <path d="M7 3 L11.5 11 L2.5 11 Z" fill={pal.bear} />
                <path d="M19 13 L23.5 5 L14.5 5 Z" fill={pal.card} stroke={pal.bull} strokeWidth={1.4} />
              </svg>
              Push: solid = TOOT / PHANS / BUYERS IN, hollow = TIKI (writers), grey = wapas; ±2 = the band answered
            </Key>
            <Key pal={pal}>
              <svg width={26} height={16} aria-hidden="true">
                <line x1={13} y1={3} x2={13} y2={13} stroke={pal.textMuted} strokeWidth={1.3} />
              </svg>
              Grey axis tick = a push OI did not answer (NAHI)
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
            <span>
              Speed is OI change per minute over the last {SPD_WIN} minutes, from these same minutes [M]. Likh / ruke /
              chhod and their times are the Speed tab's rule (§1d's stall rate, held 3 minutes) [I]; a wall is marked when
              a change held {SETTLE} minutes [I], so a mark lands {SETTLE} minutes after it starts, and the strip shows it
              at once. The speed lane's scale starts at {hhmm(OPEN + LANE_SKIP)}; the opening build is clipped at its edge.
              Pushes and their answers are Jarvis's (handshake-2, /api/jarvis), drawn on this grid's spot.
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
